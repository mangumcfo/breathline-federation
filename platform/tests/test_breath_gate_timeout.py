"""Section 8.8 — Breath-gate timeout failure mode.

Closes the previously-deferred ⏸ item under Section 8.8:

    "Breath gate timeout fails the request closed (no implicit approval)."

Per IMPLEMENTATION_PLAN.md Section 3:
    "Breath-gating is a runtime invariant — not a prompt input. The
    operator's breath is a structural prerequisite for major decisions,
    not an advisory cue."

Per Section 3.4 contract: when the operator does not confirm within the
timeout window, ``BreathGate.request_confirmation`` MUST raise
``BreathGateTimeout``. There is no implicit approval. There is no
fallback that bypasses the gate.

These tests use ``BreathGate``'s injected ``input_fn`` / ``sleep_fn`` /
``clock_fn`` parameters (already present for testability) to simulate
the timeout deterministically — no real wall-clock waiting required.
"""
from __future__ import annotations

from typing import Any

import pytest

from kernel.breath_gate import (
    BreathGate,
    BreathGateRefused,
    BreathGateTimeout,
    MINIMUM_BREATH_DURATION_SECONDS,
)


class _FakeClock:
    """Deterministic monotonic clock for testing time-based behavior."""

    def __init__(self, start: float = 0.0) -> None:
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def _silent_output(*_args: Any, **_kwargs: Any) -> None:
    """Suppress UI output during tests."""


# -----------------------------------------------------------------------------
# Section 8.8 — timeout fails closed (no implicit approval)
# -----------------------------------------------------------------------------
def test_breath_gate_timeout_fails_closed() -> None:
    """Operator silence beyond timeout → BreathGateTimeout raised, no approval."""
    clock = _FakeClock()

    # Sleep advances the clock. After the minimum-duration sleep, the operator
    # never types anything — but the clock keeps advancing, eventually past
    # the timeout deadline. The input loop must terminate with a timeout.
    def fake_sleep(seconds: float) -> None:
        clock.advance(seconds)

    # Empty input → loop iterates; we advance the clock past the deadline on
    # each attempt to guarantee deterministic exit.
    def fake_input(_prompt: str = "") -> str:
        clock.advance(60.0)  # each "no response" iteration advances by 60s
        return ""

    gate = BreathGate(
        minimum_duration_seconds=30,
        timeout_seconds=120,
        input_fn=fake_input,
        output_fn=_silent_output,
        sleep_fn=fake_sleep,
        clock_fn=clock,
    )

    with pytest.raises(BreathGateTimeout, match="timed out after 120s"):
        gate.request_confirmation(
            proposal_id="test-timeout-001",
            proposal_summary="A proposal that the operator will not confirm.",
        )


def test_breath_gate_timeout_does_not_grant_implicit_approval() -> None:
    """The exception path must NOT return a BreathConfirmation by any route."""
    clock = _FakeClock()

    def fake_sleep(seconds: float) -> None:
        clock.advance(seconds)

    def fake_input(_prompt: str = "") -> str:
        clock.advance(60.0)
        return ""

    gate = BreathGate(
        timeout_seconds=90,
        input_fn=fake_input,
        output_fn=_silent_output,
        sleep_fn=fake_sleep,
        clock_fn=clock,
    )

    with pytest.raises(BreathGateTimeout):
        result = gate.request_confirmation(
            proposal_id="test-no-implicit-001",
            proposal_summary="No implicit approval test",
        )
        # Defense in depth: even if the exception machinery were bypassed,
        # nothing on the success path should run.
        assert False, f"BreathGate returned {result!r} instead of timing out"


def test_breath_gate_decline_fails_closed() -> None:
    """Explicit operator decline raises BreathGateRefused (no approval)."""
    clock = _FakeClock()

    def fake_sleep(seconds: float) -> None:
        clock.advance(seconds)

    inputs = iter(["decline"])

    def fake_input(_prompt: str = "") -> str:
        return next(inputs)

    gate = BreathGate(
        input_fn=fake_input,
        output_fn=_silent_output,
        sleep_fn=fake_sleep,
        clock_fn=clock,
    )

    with pytest.raises(BreathGateRefused, match="Operator declined"):
        gate.request_confirmation(
            proposal_id="test-decline-001",
            proposal_summary="A proposal the operator declines.",
        )


def test_breath_gate_records_method_and_duration_on_success() -> None:
    """Sanity counterpoint: when confirmed properly, metadata is recorded."""
    clock = _FakeClock()

    def fake_sleep(seconds: float) -> None:
        clock.advance(seconds)

    inputs = iter(["i have breathed and i confirm"])

    def fake_input(_prompt: str = "") -> str:
        return next(inputs)

    gate = BreathGate(
        minimum_duration_seconds=30,
        timeout_seconds=300,
        input_fn=fake_input,
        output_fn=_silent_output,
        sleep_fn=fake_sleep,
        clock_fn=clock,
    )

    confirmation = gate.request_confirmation(
        proposal_id="test-success-001",
        proposal_summary="A proposal the operator confirms after breathing.",
    )

    assert confirmation.confirmed is True
    assert confirmation.breath_duration_seconds >= MINIMUM_BREATH_DURATION_SECONDS
    metadata = confirmation.to_audit_metadata()
    assert metadata["breath_protocol_invoked"] is True
    assert metadata["breath_confirmation_method"] == "ui_timed_ritual"


# ∞Δ∞ Section 8.8 partial sealed — breath-gate timeout fails closed ∞Δ∞
