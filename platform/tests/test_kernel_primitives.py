"""Basic structural tests for the 5 kernel primitives."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from kernel.primitives.constructor import (
    Artifact,
    Constructor,
    ConstructorRefusal,
)
from kernel.primitives.critic import Critic, CriticVerdict
from kernel.primitives.governor import (
    ElevationProposal,
    Governor,
    GovernorVerdict,
)
from kernel.primitives.spec import Spec, SpecKind, SpecRegistry, SpecSignatures


@pytest.fixture
def populated_registry() -> SpecRegistry:
    """A registry with one signed parent spec."""
    registry = SpecRegistry()
    parent = Spec(
        id="parent-spec",
        kind=SpecKind.FRAMEWORK,
        version="1.0",
        parent=None,
        body={"purpose": "test parent"},
        signatures=SpecSignatures(proposed_by="kmangum"),
    )
    registry.register(parent)
    return registry


# -----------------------------------------------------------------------------
# Spec + SpecRegistry
# -----------------------------------------------------------------------------
def test_spec_registry_is_append_only(populated_registry: SpecRegistry) -> None:
    """Per seed manifest: 'Specs are append-only; revisions create new ids.'"""
    duplicate = Spec(
        id="parent-spec",  # same id as fixture
        kind=SpecKind.FRAMEWORK,
        version="1.1",
        parent=None,
        body={"purpose": "would-be revision"},
        signatures=SpecSignatures(proposed_by="kmangum"),
    )
    with pytest.raises(ValueError, match="already exists"):
        populated_registry.register(duplicate)


def test_spec_must_reference_existing_parent() -> None:
    """Per seed manifest: 'Every spec has a parent except the seed itself.'"""
    registry = SpecRegistry()
    orphan = Spec(
        id="orphan",
        kind=SpecKind.ROLE,
        version="1.0",
        parent="nonexistent-parent",
        body={"x": 1},
        signatures=SpecSignatures(proposed_by="kmangum"),
    )
    with pytest.raises(ValueError, match="parent .+ which does not exist"):
        registry.register(orphan)


def test_unsigned_spec_is_unreal() -> None:
    """Per seed manifest: 'Specs without all required signatures are unreal.'"""
    spec = Spec(
        id="unsigned",
        kind=SpecKind.ROLE,
        version="1.0",
        parent=None,
        body={"x": 1},
        # signatures default — no proposed_by
    )
    assert not spec.is_real()


# -----------------------------------------------------------------------------
# Constructor
# -----------------------------------------------------------------------------
def test_constructor_refuses_unknown_spec() -> None:
    registry = SpecRegistry()
    constructor = Constructor(registry, role_prompt="(test)")
    with pytest.raises(ConstructorRefusal, match="not in registry"):
        constructor.construct("does-not-exist")


def test_constructor_refuses_empty_body(populated_registry: SpecRegistry) -> None:
    empty_body_spec = Spec(
        id="empty",
        kind=SpecKind.CAPABILITY,
        version="1.0",
        parent="parent-spec",
        body={},  # empty
        signatures=SpecSignatures(proposed_by="kmangum"),
    )
    populated_registry.register(empty_body_spec)
    constructor = Constructor(populated_registry, role_prompt="(test)")
    with pytest.raises(ConstructorRefusal, match="empty body"):
        constructor.construct("empty")


def test_constructor_produces_artifact_for_valid_spec(
    populated_registry: SpecRegistry,
) -> None:
    constructor = Constructor(populated_registry, role_prompt="(test)")
    artifact = constructor.construct("parent-spec")
    assert isinstance(artifact, Artifact)
    assert artifact.spec_id == "parent-spec"
    assert artifact.body  # non-empty
    assert "phase1_scaffold" in artifact.body
    assert artifact.construction_log  # non-empty


# -----------------------------------------------------------------------------
# Critic
# -----------------------------------------------------------------------------
def test_critic_returns_defect_on_unknown_spec() -> None:
    registry = SpecRegistry()
    critic = Critic(registry, role_prompt="(test)")
    artifact = Artifact(
        artifact_id="art-1",
        spec_id="missing",
        body={"any": "thing"},
        construction_log=[],
        constructed_at=datetime.now(timezone.utc),
    )
    report = critic.review("missing", artifact)
    assert report.verdict == CriticVerdict.DEFECT


def test_critic_returns_defect_on_identity_mismatch(
    populated_registry: SpecRegistry,
) -> None:
    critic = Critic(populated_registry, role_prompt="(test)")
    mismatched = Artifact(
        artifact_id="art-1",
        spec_id="other-spec",  # mismatch
        body={"x": 1},
        construction_log=[],
        constructed_at=datetime.now(timezone.utc),
    )
    report = critic.review("parent-spec", mismatched)
    assert report.verdict == CriticVerdict.DEFECT
    assert "identity_mismatch" in " ".join(report.findings)


def test_critic_conforms_on_valid_artifact(populated_registry: SpecRegistry) -> None:
    constructor = Constructor(populated_registry, role_prompt="(test)")
    artifact = constructor.construct("parent-spec")
    critic = Critic(populated_registry, role_prompt="(test)")
    report = critic.review("parent-spec", artifact)
    assert report.verdict == CriticVerdict.CONFORMS


# -----------------------------------------------------------------------------
# Governor
# -----------------------------------------------------------------------------
def test_governor_denies_on_non_conforming_critic_verdicts() -> None:
    from kernel.primitives.critic import CriticReport

    governor = Governor(role_prompt="(test)")
    bad_report = CriticReport(
        verdict=CriticVerdict.DRIFT,
        spec_id="s",
        artifact_id="a",
        drift_report="some drift",
        findings=[],
        reviewed_at=datetime.now(timezone.utc),
    )
    proposal = ElevationProposal(
        proposal_id="test-001",
        from_layer=2,
        to_layer=3,
        artifacts_summary={},
        critic_reports=[bad_report],
        proposes_kernel_modification=False,
        human_approval_signature=None,
        proposed_at=datetime.now(timezone.utc),
    )
    decision = governor.review_elevation(proposal)
    assert decision.verdict == GovernorVerdict.DENY
    assert "non-CONFORMS" in decision.rationale or "non-CONFORMS verdicts" in decision.rationale


def test_governor_denies_kernel_modification_proposals() -> None:
    """Per seed manifest, the Governor cannot approve modifications to the kernel."""
    from kernel.primitives.critic import CriticReport

    governor = Governor(role_prompt="(test)")
    proposal = ElevationProposal(
        proposal_id="test-002",
        from_layer=2,
        to_layer=3,
        artifacts_summary={},
        critic_reports=[
            CriticReport(
                verdict=CriticVerdict.CONFORMS,
                spec_id="s",
                artifact_id="a",
                drift_report=None,
                findings=[],
                reviewed_at=datetime.now(timezone.utc),
            )
        ],
        proposes_kernel_modification=True,
        human_approval_signature="signed-by-operator",  # even with human approval
        proposed_at=datetime.now(timezone.utc),
    )
    decision = governor.review_elevation(proposal)
    assert decision.verdict == GovernorVerdict.DENY
    assert "kernel" in decision.rationale.lower()


def test_governor_denies_when_human_approval_required_but_missing() -> None:
    """Layer 0 → 1, 1 → 2, 4 → 5 require human approval per seed manifest."""
    from kernel.primitives.critic import CriticReport

    governor = Governor(role_prompt="(test)")
    proposal = ElevationProposal(
        proposal_id="test-003",
        from_layer=1,
        to_layer=2,  # this gate requires human approval
        artifacts_summary={},
        critic_reports=[
            CriticReport(
                verdict=CriticVerdict.CONFORMS,
                spec_id="s",
                artifact_id="a",
                drift_report=None,
                findings=[],
                reviewed_at=datetime.now(timezone.utc),
            )
        ],
        proposes_kernel_modification=False,
        human_approval_signature=None,  # missing
        proposed_at=datetime.now(timezone.utc),
    )
    decision = governor.review_elevation(proposal)
    assert decision.verdict == GovernorVerdict.DENY
    assert "human approval" in decision.rationale.lower()


def test_governor_approves_clean_proposal() -> None:
    """All checks pass: critic CONFORMS, no kernel mod, human approval where needed."""
    from kernel.primitives.critic import CriticReport

    governor = Governor(role_prompt="(test)")
    proposal = ElevationProposal(
        proposal_id="test-004",
        from_layer=2,
        to_layer=3,  # Layer 2 → 3 doesn't need explicit human approval
        artifacts_summary={},
        critic_reports=[
            CriticReport(
                verdict=CriticVerdict.CONFORMS,
                spec_id="s",
                artifact_id="a",
                drift_report=None,
                findings=[],
                reviewed_at=datetime.now(timezone.utc),
            )
        ],
        proposes_kernel_modification=False,
        human_approval_signature=None,
        proposed_at=datetime.now(timezone.utc),
    )
    decision = governor.review_elevation(proposal)
    assert decision.verdict == GovernorVerdict.APPROVE
