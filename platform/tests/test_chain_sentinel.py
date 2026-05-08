"""Q13 / Section 8.8 — Chain integrity sentinel runtime tests.

Closes the final open Section 8.8 acceptance item:

    "Audit-chain integrity violation halts the platform"

The sentinel runs at three points:

  1. boot_check()     — at runtime construction; captures baseline,
                        fails closed on any pre-existing freeform/
                        traceback cylinder.
  2. on_seal()        — invoked after every successful seal via the
                        AuditAdapter post_seal_hook; triggers verify()
                        every N seals.
  3. verify()         — on-demand check vs baseline; fails closed on
                        degradation.

Tests cover:

  - Baseline capture against synthetic clean chain
  - boot_check halts on freeform > 0
  - boot_check halts on tracebacks > 0
  - verify() passes when chain only grows with hash-linked cylinders
  - verify() halts when new freeform appears
  - verify() halts when new hash break appears beyond baseline
  - verify() halts when chain shrinks
  - on_seal() counter triggers verify() at threshold
  - Real-chain integration: boot_check passes against live Tiger chain
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from platform_layer.chain_sentinel import (
    ChainBaseline,
    ChainIntegrityViolation,
    ChainSentinel,
)


TIGER_CYLINDERS = Path("/home/kmangum/Tiger_1a/cylinders")


# -----------------------------------------------------------------------------
# Synthetic chain helpers (mirror test_audit_chain_replay's pattern)
# -----------------------------------------------------------------------------
def _make_cylinder_text(
    *,
    timestamp: str,
    payload: str,
    prev_hash: str | None,
    agent_id: str = "test",
) -> tuple[str, str]:
    """Return (file_text, full_hash)."""
    six1_body = "SIX1:" + payload
    full_hash = hashlib.sha256(six1_body.encode("utf-8")).hexdigest()
    chain_field = "GENESIS" if prev_hash is None else prev_hash[:16]
    text = (
        f"# ∞Δ∞ SIX-Cylinder — {agent_id.upper()} ∞Δ∞\n"
        f"# Timestamp: {timestamp}\n"
        f"# Cylinder Hash: {full_hash[:16]}...{full_hash[-8:]}\n"
        f"# Chain: {chain_field}\n"
        f"# Size: {len(six1_body)} bytes\n"
        f"\n"
        f"{six1_body}\n"
        f"\n"
        f"# ∞Δ∞ Sovereign memory encoded ∞Δ∞\n"
    )
    return text, full_hash


def _seed_chain(dir_: Path, count: int, payload_prefix: str = "p") -> str:
    """Build a strictly-linked chain in dir_; return tip's full hash."""
    prev_hash: str | None = None
    for i in range(count):
        text, full_hash = _make_cylinder_text(
            timestamp=f"2026-05-07T10:{i:02d}:00Z",
            payload=f"{payload_prefix}-{i:032d}",
            prev_hash=prev_hash,
        )
        (dir_ / f"capture_20260507_10{i:02d}00.cyl").write_text(text)
        prev_hash = full_hash
    return prev_hash or ""


# -----------------------------------------------------------------------------
# boot_check — baseline capture & pre-existing violations
# -----------------------------------------------------------------------------
def test_boot_check_captures_baseline_on_clean_chain(tmp_path: Path) -> None:
    """Healthy synthetic chain: boot_check returns a frozen baseline snapshot."""
    _seed_chain(tmp_path, count=3)
    sentinel = ChainSentinel(tmp_path)
    baseline = sentinel.boot_check()

    assert isinstance(baseline, ChainBaseline)
    assert baseline.total == 3
    assert baseline.encoded == 3
    assert baseline.freeform == 0
    assert baseline.tracebacks == 0
    assert baseline.hash_break_seqs == frozenset()
    assert baseline.tip_hash_prefix != ""
    # Idempotency: re-boot raises (single-baseline contract)
    with pytest.raises(RuntimeError, match="boot_check called twice"):
        sentinel.boot_check()


def test_boot_check_halts_on_pre_existing_freeform(tmp_path: Path) -> None:
    """Freeform cylinder at boot → ChainIntegrityViolation."""
    _seed_chain(tmp_path, count=2)
    # Add a freeform (no SIX1: prefix) cylinder
    (tmp_path / "capture_20260507_999999.cyl").write_text(
        "# ∞Δ∞ SIX-Cylinder — TEST ∞Δ∞\n"
        "# Timestamp: 2026-05-07T99:99:99Z\n"
        "# This cylinder has no SIX1: line — freeform\n"
    )

    sentinel = ChainSentinel(tmp_path)
    with pytest.raises(ChainIntegrityViolation, match="freeform"):
        sentinel.boot_check()


def test_boot_check_halts_on_traceback(tmp_path: Path) -> None:
    """Cylinder containing a Python Traceback → halt at boot."""
    _seed_chain(tmp_path, count=2)
    # Add a cylinder polluted with a traceback
    text, _ = _make_cylinder_text(
        timestamp="2026-05-07T99:99:99Z",
        payload="poisoned-payload",
        prev_hash=None,
    )
    poisoned = text + "\nTraceback (most recent call last):\n  File ...\n"
    (tmp_path / "capture_20260507_999998.cyl").write_text(poisoned)

    sentinel = ChainSentinel(tmp_path)
    with pytest.raises(ChainIntegrityViolation, match="traceback"):
        sentinel.boot_check()


# -----------------------------------------------------------------------------
# verify — post-baseline degradation halts the platform
# -----------------------------------------------------------------------------
def test_verify_passes_when_chain_only_grows_clean(tmp_path: Path) -> None:
    """Clean chain growth: baseline boot, then add hash-linked cylinder, verify ok."""
    tip_hash = _seed_chain(tmp_path, count=2)
    sentinel = ChainSentinel(tmp_path)
    sentinel.boot_check()

    # Append one hash-linked cylinder post-baseline
    text, _ = _make_cylinder_text(
        timestamp="2026-05-07T11:00:00Z",
        payload="post-baseline-001",
        prev_hash=tip_hash,
    )
    (tmp_path / "capture_20260507_110000.cyl").write_text(text)

    report = sentinel.verify()
    assert report.total == 3
    assert report.freeform == 0
    assert report.tracebacks == 0
    assert sentinel.verify_count == 1


def test_verify_halts_on_new_freeform(tmp_path: Path) -> None:
    """Freeform appearing post-baseline → halt."""
    _seed_chain(tmp_path, count=2)
    sentinel = ChainSentinel(tmp_path)
    sentinel.boot_check()

    # Inject a freeform post-baseline
    (tmp_path / "capture_20260507_999990.cyl").write_text(
        "# Freeform post-baseline — no SIX1\n"
    )

    with pytest.raises(ChainIntegrityViolation, match="freeform count increased"):
        sentinel.verify()


def test_verify_halts_on_new_hash_break(tmp_path: Path) -> None:
    """A new mid-chain hash discontinuity post-baseline → halt."""
    tip_hash = _seed_chain(tmp_path, count=3)
    sentinel = ChainSentinel(tmp_path)
    sentinel.boot_check()

    # Append a cylinder whose prev_hash does NOT match the real tip
    text, _ = _make_cylinder_text(
        timestamp="2026-05-07T11:00:00Z",
        payload="break-injection",
        prev_hash="0000000000000000",   # fabricated, doesn't match tip_hash[:16]
    )
    (tmp_path / "capture_20260507_110000.cyl").write_text(text)

    with pytest.raises(ChainIntegrityViolation, match="new hash-break"):
        sentinel.verify()


def test_verify_halts_on_chain_shrinkage(tmp_path: Path) -> None:
    """Cylinder deletion post-baseline → halt (chain only grows contract)."""
    _seed_chain(tmp_path, count=3)
    sentinel = ChainSentinel(tmp_path)
    sentinel.boot_check()

    # Delete one cylinder
    next(tmp_path.glob("capture_*.cyl")).unlink()

    with pytest.raises(ChainIntegrityViolation, match="chain shrunk"):
        sentinel.verify()


def test_verify_before_boot_raises(tmp_path: Path) -> None:
    """Calling verify before boot_check is a programming error."""
    _seed_chain(tmp_path, count=1)
    sentinel = ChainSentinel(tmp_path)
    with pytest.raises(RuntimeError, match="before boot_check"):
        sentinel.verify()


# -----------------------------------------------------------------------------
# on_seal counter — periodic verify trigger
# -----------------------------------------------------------------------------
def test_on_seal_increments_counter_only(tmp_path: Path) -> None:
    """on_seal called below threshold doesn't run verify."""
    _seed_chain(tmp_path, count=1)
    sentinel = ChainSentinel(tmp_path, every_n_seals=10)
    sentinel.boot_check()

    for _ in range(9):
        sentinel.on_seal()
    assert sentinel.seal_counter == 9
    assert sentinel.verify_count == 0


def test_on_seal_triggers_verify_at_threshold(tmp_path: Path) -> None:
    """on_seal at the threshold runs verify; passes on clean chain."""
    _seed_chain(tmp_path, count=2)
    sentinel = ChainSentinel(tmp_path, every_n_seals=3)
    sentinel.boot_check()

    sentinel.on_seal()
    sentinel.on_seal()
    sentinel.on_seal()   # 3rd call → triggers verify
    assert sentinel.seal_counter == 3
    assert sentinel.verify_count == 1


def test_on_seal_propagates_violation(tmp_path: Path) -> None:
    """Periodic verify halts the platform on degradation."""
    _seed_chain(tmp_path, count=2)
    sentinel = ChainSentinel(tmp_path, every_n_seals=2)
    sentinel.boot_check()

    # Inject freeform between seals
    sentinel.on_seal()
    (tmp_path / "capture_20260507_999999.cyl").write_text("# freeform\n")

    with pytest.raises(ChainIntegrityViolation):
        sentinel.on_seal()   # threshold hit → verify → halt


def test_invalid_every_n_rejected(tmp_path: Path) -> None:
    """every_n_seals must be > 0."""
    with pytest.raises(ValueError, match="must be > 0"):
        ChainSentinel(tmp_path, every_n_seals=0)
    with pytest.raises(ValueError, match="must be > 0"):
        ChainSentinel(tmp_path, every_n_seals=-5)


# -----------------------------------------------------------------------------
# Real Tiger chain — sentinel passes against live operational state
# -----------------------------------------------------------------------------
@pytest.mark.skipif(
    not TIGER_CYLINDERS.exists(),
    reason="Tiger chain not present on this host",
)
def test_real_tiger_chain_boot_check_passes() -> None:
    """The real chain has 0 freeform / 0 tracebacks at boot — sentinel passes.

    Legacy hash discontinuities (~49) are accepted as the baseline floor.
    """
    sentinel = ChainSentinel(TIGER_CYLINDERS, every_n_seals=1000)
    baseline = sentinel.boot_check()

    assert baseline.freeform == 0
    assert baseline.tracebacks == 0
    assert baseline.total >= 171
    assert baseline.tip_hash_prefix != ""
    # Re-running verify against the same chain should pass (chain only grows)
    sentinel.verify()


# ∞Δ∞ Q13 / Section 8.8 sealed — chain sentinel halts platform on violation ∞Δ∞
