"""Section 8.3 — Constitutional integrity at runtime (chain replay).

Verifies the platform's core security claim: every audit cylinder from
genesis to tip is SIX1-encoded, traceback-free, and (for synthetic chains
under our control) hash-linked. The test exercises ``replay_chain`` from
``platform_layer.audit_adapter`` against:

    1. A purpose-built 3-cylinder synthetic chain (strict continuity).
    2. The real Tiger cylinder chain at ``/home/kmangum/Tiger_1a/cylinders/``
       (count-based gate matching what ``seal.sh --audit`` itself checks).

Per IMPLEMENTATION_PLAN.md Section 8.3, the acceptance criteria are
freeform == 0, tracebacks == 0, has genesis, has tip. Hash-continuity
breaks are tracked informationally; the real Tiger chain has 49 legacy
discontinuities from pre-strict-linking history (verified separately;
the count-based gate is what governs constitutional integrity).
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

# Make six_cylinder importable for synthetic-chain construction.
SIX_CYLINDER_DIR = Path("/home/kmangum/Tiger_1a/cylinders")
if str(SIX_CYLINDER_DIR) not in sys.path:
    sys.path.insert(0, str(SIX_CYLINDER_DIR))

from platform_layer.audit_adapter import (  # noqa: E402
    ChainReplayError,
    ChainReplayReport,
    CylinderRef,
    replay_chain,
)


TIGER_CYLINDERS = Path("/home/kmangum/Tiger_1a/cylinders")
SEAL_SH = TIGER_CYLINDERS / "seal.sh"


# -----------------------------------------------------------------------------
# Synthetic chain — purpose-built, strict continuity guaranteed
# -----------------------------------------------------------------------------
def _build_synthetic_cylinder_file(
    *,
    agent_id: str,
    timestamp: str,
    payload: str,
    prev_hash: str | None,
) -> tuple[str, str]:
    """Construct a cylinder file body and return (file_text, full_hash).

    Matches the operator-side format produced by
    ``six_cylinder.format_cylinder_file``:
      - Five header lines (∞Δ∞, Timestamp, Cylinder Hash, Chain, Size)
      - Blank line
      - SIX1: encoded payload
      - Blank line + sovereign-memory footer
    """
    # Deterministic SIX1 surrogate: real encoder requires yaml import which is
    # already pulled in via audit_adapter; we synthesize a SIX1: line whose
    # body content does not need to round-trip through decode (replay_chain
    # only checks for the SIX1: prefix presence, not decode validity).
    six1_body = "SIX1:" + payload
    full_hash = hashlib.sha256(six1_body.encode("utf-8")).hexdigest()
    hash_first16 = full_hash[:16]
    hash_last8 = full_hash[-8:]
    chain_field = "GENESIS" if prev_hash is None else prev_hash[:16]
    size = len(six1_body.encode("utf-8"))

    file_text = (
        f"# ∞Δ∞ SIX-Cylinder — {agent_id.upper()} ∞Δ∞\n"
        f"# Timestamp: {timestamp}\n"
        f"# Cylinder Hash: {hash_first16}...{hash_last8}\n"
        f"# Chain: {chain_field}\n"
        f"# Size: {size} bytes\n"
        f"\n"
        f"{six1_body}\n"
        f"\n"
        f"# ∞Δ∞ Sovereign memory encoded ∞Δ∞\n"
    )
    return file_text, full_hash


@pytest.fixture
def synthetic_chain(tmp_path: Path) -> Path:
    """Build a strictly-linked 3-cylinder synthetic chain in tmp_path."""
    # Genesis
    g_text, g_hash = _build_synthetic_cylinder_file(
        agent_id="test",
        timestamp="2026-05-07T10:00:00Z",
        payload="genesis-payload-aaaaaaaaaaaaaaaa",
        prev_hash=None,
    )
    (tmp_path / "capture_20260507_100000.cyl").write_text(g_text)

    # Cylinder 2 — links to genesis
    c2_text, c2_hash = _build_synthetic_cylinder_file(
        agent_id="test",
        timestamp="2026-05-07T10:00:01Z",
        payload="second-payload-bbbbbbbbbbbbbbbbbb",
        prev_hash=g_hash,
    )
    (tmp_path / "capture_20260507_100001.cyl").write_text(c2_text)

    # Cylinder 3 — links to cylinder 2
    c3_text, _ = _build_synthetic_cylinder_file(
        agent_id="test",
        timestamp="2026-05-07T10:00:02Z",
        payload="third-payload-ccccccccccccccccc",
        prev_hash=c2_hash,
    )
    (tmp_path / "capture_20260507_100002.cyl").write_text(c3_text)

    return tmp_path


def test_synthetic_chain_replay_genesis_to_tip(synthetic_chain: Path) -> None:
    """Strict-linked synthetic chain: zero hash breaks, zero seq gaps."""
    report = replay_chain(synthetic_chain)

    assert isinstance(report, ChainReplayReport)
    assert report.total == 3
    assert report.encoded == 3
    assert report.freeform == 0
    assert report.tracebacks == 0
    assert report.hash_breaks == []
    assert report.seq_gaps == []
    assert report.genesis_seq == 0
    assert report.tip_seq == 2
    assert len(report.cylinders_in_order) == 3


def test_synthetic_chain_no_freeform_no_tracebacks(synthetic_chain: Path) -> None:
    """Constitutional integrity: every cylinder is SIX1-encoded."""
    report = replay_chain(synthetic_chain)
    assert report.freeform == 0
    assert report.tracebacks == 0
    assert all(c.is_encoded for c in report.cylinders_in_order)
    assert not any(c.has_traceback for c in report.cylinders_in_order)


def test_synthetic_chain_genesis_anchor(synthetic_chain: Path) -> None:
    """First cylinder must anchor with GENESIS marker (no predecessor link)."""
    report = replay_chain(synthetic_chain)
    genesis = report.cylinders_in_order[0]
    assert genesis.prev_hash_prefix == "GENESIS"
    # Subsequent cylinders link forward
    for i in range(1, len(report.cylinders_in_order)):
        assert report.cylinders_in_order[i].prev_hash_prefix != "GENESIS"


def test_synthetic_chain_max_cylinders_safety_cap(tmp_path: Path) -> None:
    """G polish #1: replay_chain refuses directories beyond max_cylinders."""
    # Build 5 trivial synthetic cylinders, set cap to 3 → must raise
    for i in range(5):
        text, _ = _build_synthetic_cylinder_file(
            agent_id="test",
            timestamp=f"2026-05-07T11:00:0{i}Z",
            payload=f"payload-{i:032d}",
            prev_hash=None,
        )
        (tmp_path / f"capture_20260507_11000{i}.cyl").write_text(text)

    with pytest.raises(ChainReplayError, match="exceeds max_cylinders"):
        replay_chain(tmp_path, max_cylinders=3)


# -----------------------------------------------------------------------------
# Real Tiger chain — count-based gate (matches seal.sh --audit's check)
# -----------------------------------------------------------------------------
@pytest.mark.skipif(
    not TIGER_CYLINDERS.exists(),
    reason="Tiger chain not present on this host",
)
def test_real_tiger_chain_replay_passes() -> None:
    """Section 8.3 acceptance gate against the real Tiger chain.

    Asserts the count-based integrity criteria that ``seal.sh --audit``
    itself enforces. Hash discontinuities (~49) exist as legacy artifacts
    from pre-strict-linking Tiger history; they're tracked but not failing.
    G polish #2: explicit monotonic-sequence guard via filename uniqueness.
    """
    report = replay_chain(TIGER_CYLINDERS, max_cylinders=1000)

    # Constitutional integrity (Section 8.3 hard gates)
    assert report.freeform == 0, f"chain has {report.freeform} freeform entries"
    assert report.tracebacks == 0, f"chain has {report.tracebacks} traceback entries"
    assert report.encoded == report.total, (
        f"encoded ({report.encoded}) != total ({report.total})"
    )
    assert report.total >= 171, (
        f"chain only grows; expected ≥171 cylinders, got {report.total}"
    )

    # Chain anchors: genesis exists, tip exists
    assert report.genesis_seq is not None
    assert report.tip_seq is not None
    assert report.tip_seq == report.total - 1

    # G polish #2 — monotonic & unique sequence guard (defense-in-depth)
    seqs = [c.sequence for c in report.cylinders_in_order]
    assert seqs == sorted(set(seqs)) == sorted(seqs), "sequences not strictly monotonic/unique"
    filenames = [c.filename for c in report.cylinders_in_order]
    assert len(filenames) == len(set(filenames)), "duplicate cylinder filenames detected"


@pytest.mark.skipif(
    not SEAL_SH.exists(),
    reason="Tiger seal.sh not present on this host",
)
def test_real_tiger_chain_audit_subprocess_corroborates() -> None:
    """Defense-in-depth: ``seal.sh --audit`` total matches replay_chain.encoded.

    Cross-checks the platform's deterministic replay against the operator's
    canonical audit script. Both must agree on the count of SIX1-encoded
    cylinders.
    """
    result = subprocess.run(
        [str(SEAL_SH), "--audit"],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=str(SEAL_SH.parent),
    )
    assert result.returncode == 0, f"seal.sh --audit failed: {result.stderr}"

    # Parse "Encoded:    NNN" from seal.sh output
    encoded_count = None
    for line in result.stdout.splitlines():
        stripped = line.strip()
        # Tolerate ANSI color codes around "Encoded:"
        if "Encoded:" in stripped and "SIX1" in stripped:
            for token in stripped.replace(":", " ").split():
                if token.isdigit():
                    encoded_count = int(token)
                    break
            if encoded_count is not None:
                break
    assert encoded_count is not None, (
        f"could not parse Encoded count from seal.sh output:\n{result.stdout}"
    )

    report = replay_chain(TIGER_CYLINDERS, max_cylinders=1000)
    assert report.encoded == encoded_count, (
        f"replay_chain.encoded ({report.encoded}) disagrees with "
        f"seal.sh --audit Encoded ({encoded_count})"
    )


# ∞Δ∞ Section 8.3 sealed — chain integrity replayable from genesis to tip ∞Δ∞
