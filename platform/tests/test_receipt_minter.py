"""Tests for receipt_minter — default-deny + rate limiting + batching + degraded mode."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from platform_layer.receipt_minter import (
    ReceiptID,
    ReceiptMinter,
    ReceiptMintRefused,
)


@dataclass
class _StubResponse:
    """Stand-in for httpx.Response."""

    status_code: int
    body: dict[str, Any]

    def json(self) -> dict[str, Any]:
        return self.body


class _FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def _success_post(receipt_id: str = "rcpt-abc123"):
    def post(url: str, json: dict[str, Any], timeout: int) -> _StubResponse:
        return _StubResponse(status_code=200, body={"receipt_id": receipt_id})

    return post


def _degraded_post():
    def post(url: str, json: dict[str, Any], timeout: int) -> _StubResponse:
        return _StubResponse(status_code=503, body={"status": "transitioning"})

    return post


@pytest.fixture
def taxonomy_path(seed_dir: Path) -> Path:
    return seed_dir / "receipt_worthy_events.yaml"


# -----------------------------------------------------------------------------
# Default-deny enforcement
# -----------------------------------------------------------------------------
def test_minter_loads_allowed_events_from_taxonomy(taxonomy_path: Path) -> None:
    minter = ReceiptMinter(
        taxonomy_path=taxonomy_path,
        post_fn=_success_post(),
    )
    # Always-mint events from the locked v0.1 taxonomy
    assert "kernel_boot" in minter.allowed_events
    assert "layer_elevation" in minter.allowed_events
    assert "human_approval_gate" in minter.allowed_events
    assert "external_commitment_proposal" in minter.allowed_events
    assert "cost_ceiling_breach_attempt" in minter.allowed_events


def test_minter_excludes_default_off_configurable_events(taxonomy_path: Path) -> None:
    """Configurable events default to OFF and must not appear in allowed_events."""
    minter = ReceiptMinter(
        taxonomy_path=taxonomy_path,
        post_fn=_success_post(),
    )
    assert "role_output_acted_on" not in minter.allowed_events
    assert "workforce_spawn_with_external_calls" not in minter.allowed_events


def test_minter_default_deny_on_unknown_event(taxonomy_path: Path) -> None:
    minter = ReceiptMinter(
        taxonomy_path=taxonomy_path,
        post_fn=_success_post(),
    )
    with pytest.raises(ReceiptMintRefused, match="not on the receipt-worthy taxonomy"):
        minter.mint(event="totally_invented_event", principal_id="kmangum")


def test_minter_default_deny_on_disabled_configurable(taxonomy_path: Path) -> None:
    """A configurable event with default=off must default-deny mint."""
    minter = ReceiptMinter(
        taxonomy_path=taxonomy_path,
        post_fn=_success_post(),
    )
    with pytest.raises(ReceiptMintRefused):
        minter.mint(event="role_output_acted_on", principal_id="kmangum")


# -----------------------------------------------------------------------------
# Successful mint
# -----------------------------------------------------------------------------
def test_minter_mints_for_allowed_event(taxonomy_path: Path) -> None:
    minter = ReceiptMinter(
        taxonomy_path=taxonomy_path,
        post_fn=_success_post(receipt_id="rcpt-success-001"),
    )
    result = minter.mint(event="kernel_boot", principal_id="kmangum")
    assert result.minted is True
    assert result.receipt_id == ReceiptID("rcpt-success-001")
    assert result.pending is False
    assert result.batched_count == 0


def test_minter_metadata_contains_receipt_id(taxonomy_path: Path) -> None:
    minter = ReceiptMinter(
        taxonomy_path=taxonomy_path,
        post_fn=_success_post(receipt_id="rcpt-meta-001"),
    )
    result = minter.mint(event="layer_elevation", principal_id="kmangum")
    metadata = result.to_metadata()
    assert metadata["minted"] is True
    assert metadata["receipt_id"] == "rcpt-meta-001"
    assert "receipt_pending" not in metadata


# -----------------------------------------------------------------------------
# Degraded mode (SIX-SOV returns 503 — Phase 2 transition placeholder)
# -----------------------------------------------------------------------------
def test_minter_degraded_mode_logs_pending(taxonomy_path: Path) -> None:
    """When SIX-SOV returns 503, mint records receipt_pending; cylinder seal
    still happens (the auditor is upstream of this; tested elsewhere)."""
    minter = ReceiptMinter(
        taxonomy_path=taxonomy_path,
        degraded_mode_ok=True,
        post_fn=_degraded_post(),
    )
    result = minter.mint(event="permission_spec_change", principal_id="kmangum")
    assert result.minted is False
    assert result.receipt_id is None
    assert result.pending is True
    assert result.to_metadata()["receipt_pending"] is True


def test_minter_degraded_mode_off_raises_when_unreachable(taxonomy_path: Path) -> None:
    """If degraded_mode_ok is False, network errors should propagate."""
    def raises_post(url: str, json: dict[str, Any], timeout: int) -> _StubResponse:
        raise ConnectionError("simulated network failure")

    minter = ReceiptMinter(
        taxonomy_path=taxonomy_path,
        degraded_mode_ok=False,
        post_fn=raises_post,
    )
    with pytest.raises(ConnectionError):
        minter.mint(event="kernel_boot", principal_id="kmangum")


# -----------------------------------------------------------------------------
# Rate limiting + batching
# -----------------------------------------------------------------------------
def test_minter_rate_limit_triggers_batching(taxonomy_path: Path) -> None:
    """Per Section 7.3: 'burst behavior: batch with count'."""
    clock = _FakeClock(start=1000.0)
    minter = ReceiptMinter(
        taxonomy_path=taxonomy_path,
        clock=clock,
        post_fn=_success_post(),
    )
    event = "cost_ceiling_breach_attempt"  # has rate_limit override max_per_minute=10

    # Mint up to the cap (10 per minute for this class)
    for i in range(10):
        result = minter.mint(event=event, principal_id="kmangum")
        assert result.minted is True

    # The 11th in the same minute should batch
    result = minter.mint(event=event, principal_id="kmangum")
    assert result.minted is False
    assert result.batched_count >= 1


def test_minter_flush_batch_returns_count(taxonomy_path: Path) -> None:
    clock = _FakeClock(start=2000.0)
    minter = ReceiptMinter(
        taxonomy_path=taxonomy_path,
        clock=clock,
        post_fn=_success_post(receipt_id="batch-1"),
    )
    event = "cost_ceiling_breach_attempt"
    # Fill cap
    for _ in range(10):
        minter.mint(event=event, principal_id="kmangum")
    # Add three more to the batch
    for _ in range(3):
        result = minter.mint(event=event, principal_id="kmangum")
        assert result.batched_count >= 1

    flushed = minter.flush_batch(event)
    assert flushed is not None
    assert flushed.batched_count == 3
    assert flushed.minted is True
    assert flushed.receipt_id == ReceiptID("batch-1")


def test_minter_rate_limit_resets_after_window(taxonomy_path: Path) -> None:
    clock = _FakeClock(start=3000.0)
    minter = ReceiptMinter(
        taxonomy_path=taxonomy_path,
        clock=clock,
        post_fn=_success_post(),
    )
    event = "cost_ceiling_breach_attempt"
    # Fill cap
    for _ in range(10):
        minter.mint(event=event, principal_id="kmangum")
    # 11th batches
    assert minter.mint(event=event, principal_id="kmangum").batched_count >= 1
    # Advance past the window
    clock.advance(70.0)
    # New mint succeeds (rate limit window has rolled)
    result = minter.mint(event=event, principal_id="kmangum")
    assert result.minted is True
