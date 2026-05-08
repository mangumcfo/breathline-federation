"""The 5 constitutional verification tests from
seed/02_SEED_MANIFEST.yaml `governance.verification_tests`,
encoded as runnable pytest signatures per IMPLEMENTATION_PLAN.md Section 2.

Bootstrap fails closed if any of these fail.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from kernel.breath_gate import MINIMUM_BREATH_DURATION_SECONDS


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def published_fingerprints(fingerprints_path: Path) -> dict[str, str]:
    assert fingerprints_path.exists(), (
        f"Published fingerprints not found at {fingerprints_path}. "
        f"This file is generated at scaffolding time."
    )
    return json.loads(fingerprints_path.read_text())


# -----------------------------------------------------------------------------
# Verification test 1: SHA-256 of CONSTITUTION.md matches published value
# -----------------------------------------------------------------------------
def test_constitution_fingerprint_matches_published(
    seed_dir: Path, published_fingerprints: dict[str, str]
) -> None:
    actual = _sha256(seed_dir / "CONSTITUTION.md")
    expected = published_fingerprints.get("CONSTITUTION.md", "")
    assert actual == expected, (
        f"Constitution fingerprint mismatch: actual={actual[:16]}..., "
        f"expected={expected[:16]}..."
    )


# -----------------------------------------------------------------------------
# Verification test 2: SHA-256 of CHARTER_v1.0.md matches published value
# -----------------------------------------------------------------------------
def test_charter_fingerprint_matches_published(
    seed_dir: Path, published_fingerprints: dict[str, str]
) -> None:
    actual = _sha256(seed_dir / "CHARTER_v1.0.md")
    expected = published_fingerprints.get("CHARTER_v1.0.md", "")
    assert actual == expected, (
        f"Charter fingerprint mismatch: actual={actual[:16]}..., "
        f"expected={expected[:16]}..."
    )


# -----------------------------------------------------------------------------
# Verification test 3: Seed manifest references both parents with current paths
# -----------------------------------------------------------------------------
def test_seed_manifest_references_both_parents(seed_dir: Path) -> None:
    manifest = yaml.safe_load((seed_dir / "02_SEED_MANIFEST.yaml").read_text())
    parents = manifest.get("governance", {}).get("parents", [])
    authorities = {p.get("authority") for p in parents}
    assert "Sovereignty-Aligned Charter v1.0" in authorities, (
        f"Charter not declared as parent in seed manifest. Found authorities: {authorities}"
    )
    assert "Constitution@A1" in authorities, (
        f"Constitution@A1 not declared as parent in seed manifest. Found authorities: {authorities}"
    )


# -----------------------------------------------------------------------------
# Verification test 4: Audit log contains zero Governor approvals violating parent authority
# -----------------------------------------------------------------------------
def test_no_governor_approvals_violate_parent_authority() -> None:
    """Phase 1: structural check that the Governor's denial logic refuses
    elevations modifying the kernel. Phase 3 will replay live audit log.
    """
    from kernel.primitives.governor import (
        ElevationProposal,
        Governor,
        GovernorVerdict,
    )
    from kernel.primitives.critic import CriticReport, CriticVerdict
    from datetime import datetime, timezone

    governor = Governor(role_prompt="(test prompt)")
    proposal = ElevationProposal(
        proposal_id="test-kernel-mod",
        from_layer=1,
        to_layer=2,
        artifacts_summary={},
        critic_reports=[
            CriticReport(
                verdict=CriticVerdict.CONFORMS,
                spec_id="test",
                artifact_id="art",
                drift_report=None,
                findings=[],
                reviewed_at=datetime.now(timezone.utc),
            )
        ],
        proposes_kernel_modification=True,
        human_approval_signature="signed",
        proposed_at=datetime.now(timezone.utc),
    )
    decision = governor.review_elevation(proposal)
    assert decision.verdict == GovernorVerdict.DENY, (
        f"Governor must deny kernel-modification elevations. Got: {decision.verdict}"
    )
    assert "kernel" in decision.rationale.lower()


# -----------------------------------------------------------------------------
# Verification test 5: Every human-approval gate invokes Charter II.4.4 breath protocol
# -----------------------------------------------------------------------------
def test_breath_gate_enforces_minimum_duration() -> None:
    """Structural verification: BreathGate cannot be configured below the
    Charter II.4.4 minimum of 30 seconds."""
    from kernel.breath_gate import BreathGate

    assert MINIMUM_BREATH_DURATION_SECONDS >= 30, (
        f"Charter II.4.4 minimum is 30s; got {MINIMUM_BREATH_DURATION_SECONDS}"
    )

    # Defense in depth: BreathGate constructor refuses sub-minimum configurations
    with pytest.raises(ValueError, match="below the Charter II.4.4 minimum"):
        BreathGate(minimum_duration_seconds=10)


def test_breath_gate_metadata_includes_required_fields() -> None:
    """Per Section 3.2.1: every breath confirmation always records
    breath_confirmation_method, breath_duration_seconds, breath_timestamp.
    """
    from kernel.breath_gate import BreathConfirmation

    confirmation = BreathConfirmation(
        confirmed=True,
        breath_confirmation_method="ui_timed_ritual",
        breath_duration_seconds=33,
        breath_timestamp="2026-05-06T20:00:00+00:00",
        proposal_id="test-001",
    )
    metadata = confirmation.to_audit_metadata()
    assert metadata["breath_protocol_invoked"] is True
    assert metadata["breath_confirmation_method"] == "ui_timed_ritual"
    assert metadata["breath_duration_seconds"] == 33
    assert metadata["breath_timestamp"] == "2026-05-06T20:00:00+00:00"
