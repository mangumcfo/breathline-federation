"""Tests for Compliance-agent — two frameworks, one role.

Covers:
  - charter_v7_enforcement: peer-output review for forbidden drift tokens
  - compliance_review:      Evidence Bundle (with + without auditor/minter)

Hermetic: no LLM, no network, no SIX-SOV. Phase 3 deterministic core.
"""
from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

import pytest

from platform_layer.permission_spec import ActionClassRegistry
from platform_layer.plugin_interface import PlugInRequest
from platform_layer.registry import RoleRegistry
from roles.compliance_agent import ComplianceAgent
from roles.compliance_agent.frameworks.charter_v7 import (
    CHARTER_V7_FORBIDDEN_TARGETS,
    apply_charter_v7_review,
)
from roles.compliance_agent.frameworks.compliance_review import (
    apply_compliance_review,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def action_class_registry(seed_dir: Path) -> ActionClassRegistry:
    return ActionClassRegistry.from_yaml(seed_dir / "action_classes.yaml")


@pytest.fixture
def role_registry(
    tmp_path: Path,
    action_class_registry: ActionClassRegistry,
) -> RoleRegistry:
    """Register two test roles so the LeastAuthorityReport has multiple rows."""
    registry = RoleRegistry(action_class_registry)
    cfo_path = tmp_path / "cfo.yaml"
    cfo_path.write_text(
        textwrap.dedent(
            """\
            role: cfo_agent
            version: "0.1"
            allowed_action_classes:
              - read_structured_financial_data
              - produce_forecast_artifact
              - generate_scenarios
              - cite_assumptions
              - flag_uncertainty
            invocation_envelope:
              inputs_required: [financial_data, forecast_horizon]
            """
        )
    )
    compliance_path = tmp_path / "compliance.yaml"
    compliance_path.write_text(
        textwrap.dedent(
            """\
            role: compliance_agent
            version: "0.1"
            allowed_action_classes:
              - read_role_outputs
              - read_audit_chain
              - review_peer_outputs
              - flag_charter_v7_violations
              - generate_least_authority_report
              - generate_compliance_evidence_bundle
              - produce_audit_trail_entry
              - cite_assumptions
            """
        )
    )
    registry.register_from_yaml(cfo_path)
    registry.register_from_yaml(compliance_path)
    return registry


def _request(
    mode: str,
    payload_extra: dict[str, Any] | None = None,
    principal: str = "kmangum",
) -> PlugInRequest:
    payload: dict[str, Any] = {"mode": mode}
    if payload_extra:
        payload.update(payload_extra)
    return PlugInRequest(
        request_id="req-comp-001",
        principal_id=principal,
        role_target="compliance_agent",
        action_class="review_peer_outputs",
        payload=payload,
    )


# -----------------------------------------------------------------------------
# Charter V.7 framework
# -----------------------------------------------------------------------------
def test_charter_v7_approves_clean_artifact() -> None:
    artifact = {
        "role_id": "cfo_agent",
        "status": "produced",
        "forecast_artifact": {"scenarios": [{"name": "baseline"}]},
    }
    verdict = apply_charter_v7_review(artifact)
    assert verdict.approved is True
    assert verdict.violations == []


def test_charter_v7_flags_external_commitment() -> None:
    artifact = {
        "role_id": "rogue_agent",
        "advice": "I will sign this on your behalf and proceed with the binding agreement on behalf of you.",
    }
    verdict = apply_charter_v7_review(artifact)
    assert verdict.approved is False
    targets = {v.forbidden_target for v in verdict.violations}
    assert "external_commitment" in targets


def test_charter_v7_flags_personnel_decision() -> None:
    artifact = {"recommendation": "You should fire Bob immediately."}
    verdict = apply_charter_v7_review(artifact)
    assert verdict.approved is False
    assert any(v.forbidden_target == "personnel_decision" for v in verdict.violations)


def test_charter_v7_flags_charter_modification() -> None:
    artifact = {"plan": "We must amend the charter to permit this."}
    verdict = apply_charter_v7_review(artifact)
    assert verdict.approved is False
    assert any(v.forbidden_target == "charter_modification" for v in verdict.violations)


def test_charter_v7_handles_non_dict_input() -> None:
    verdict = apply_charter_v7_review("not a dict")  # type: ignore[arg-type]
    assert verdict.approved is False
    assert verdict.framework_steps_executed == ["Refuse"]


def test_charter_v7_returns_location_hints() -> None:
    artifact = {
        "outputs": [
            {"role_id": "x", "advice": "I have already executed the trade."},
        ],
    }
    verdict = apply_charter_v7_review(artifact)
    assert verdict.approved is False
    assert any("$.outputs[0].advice" in v.location_hint for v in verdict.violations)


def test_charter_v7_forbidden_targets_complete() -> None:
    """The five Charter V.7 forbidden targets are present."""
    expected = {
        "external_commitment",
        "personnel_decision",
        "irreversible_action",
        "charter_modification",
        "judgment_over_humans",
    }
    assert set(CHARTER_V7_FORBIDDEN_TARGETS) == expected


# -----------------------------------------------------------------------------
# Compliance Review framework — Least-Authority Report + Evidence Bundle
# -----------------------------------------------------------------------------
def test_compliance_review_enumerates_every_role(role_registry: RoleRegistry) -> None:
    bundle = apply_compliance_review(
        role_registry=role_registry,
        principal_id="kmangum",
        request_id="r-1",
    )
    role_ids = {r.role_id for r in bundle.least_authority_report.roles}
    assert role_ids == {"cfo_agent", "compliance_agent"}


def test_compliance_review_includes_charter_v7_classes(
    role_registry: RoleRegistry,
) -> None:
    bundle = apply_compliance_review(
        role_registry=role_registry,
        principal_id="kmangum",
        request_id="r-2",
    )
    forbidden = bundle.least_authority_report.charter_v7_forbidden_classes
    assert isinstance(forbidden, list)
    assert len(forbidden) >= 1


def test_compliance_review_marks_degraded_without_auditor(
    role_registry: RoleRegistry,
) -> None:
    bundle = apply_compliance_review(
        role_registry=role_registry,
        principal_id="kmangum",
        request_id="r-3",
        auditor=None,
        receipt_minter=None,
    )
    assert "drift_or_defect_verdicts" in bundle.degraded_sections
    assert "cost_ceiling_breaches" in bundle.degraded_sections
    assert "governor_decisions" in bundle.degraded_sections
    assert "cylinder_chain_integrity" in bundle.degraded_sections
    assert "receipts" in bundle.degraded_sections


def test_compliance_review_uses_auditor_when_provided(
    role_registry: RoleRegistry,
) -> None:
    class _AuditorStub:
        def query_critic_verdicts(self, w: Any) -> list[dict[str, Any]]:
            return [{"id": "v1", "verdict": "DRIFT"}]

        def query_cost_breaches(self, w: Any) -> list[dict[str, Any]]:
            return []

        def query_governor_decisions(self, w: Any) -> list[dict[str, Any]]:
            return [{"id": "g1", "decision": "approved"}]

        def verify_chain_integrity(self) -> dict[str, Any]:
            return {"ok": True, "chain_tip": 142}

    class _MinterStub:
        def list_receipts(self, w: Any) -> list[dict[str, Any]]:
            return [{"receipt_id": "r-001"}]

    bundle = apply_compliance_review(
        role_registry=role_registry,
        principal_id="kmangum",
        request_id="r-4",
        auditor=_AuditorStub(),
        receipt_minter=_MinterStub(),
    )
    assert bundle.degraded_sections == []
    assert bundle.drift_or_defect_verdicts == [{"id": "v1", "verdict": "DRIFT"}]
    assert bundle.receipts == [{"receipt_id": "r-001"}]
    assert bundle.cylinder_chain_integrity == {"ok": True, "chain_tip": 142}


# -----------------------------------------------------------------------------
# RoleHandler integration
# -----------------------------------------------------------------------------
def test_compliance_agent_charter_v7_review_path(role_registry: RoleRegistry) -> None:
    agent = ComplianceAgent(role_registry=role_registry)
    request = _request(
        mode="charter_v7_review",
        payload_extra={"peer_artifact": {"status": "produced", "note": "all clean"}},
    )
    result = agent.process(request)
    assert result["status"] == "produced"
    assert result["framework"] == "charter_v7_enforcement"
    assert result["verdict"]["approved"] is True


def test_compliance_agent_charter_v7_refuses_on_drift(
    role_registry: RoleRegistry,
) -> None:
    agent = ComplianceAgent(role_registry=role_registry)
    request = _request(
        mode="charter_v7_review",
        payload_extra={
            "peer_artifact": {
                "advice": "We must amend the charter to permit this elevation."
            }
        },
    )
    result = agent.process(request)
    assert result["status"] == "refused"
    assert "charter_v7_drift_detected" in result["refusal_reason"]


def test_compliance_agent_compliance_review_path(role_registry: RoleRegistry) -> None:
    agent = ComplianceAgent(role_registry=role_registry)
    request = _request(mode="compliance_review")
    result = agent.process(request)
    assert result["status"] == "produced"
    assert result["framework"] == "compliance_review"
    assert "evidence_bundle" in result
    assert "least_authority_report" in result["evidence_bundle"]


def test_compliance_agent_unknown_mode_refuses(role_registry: RoleRegistry) -> None:
    agent = ComplianceAgent(role_registry=role_registry)
    request = _request(mode="not_a_real_mode")
    result = agent.process(request)
    assert result["status"] == "refused"
    assert "unknown_mode" in result["refusal_reason"]


def test_compliance_agent_charter_v7_requires_dict_artifact(
    role_registry: RoleRegistry,
) -> None:
    agent = ComplianceAgent(role_registry=role_registry)
    request = _request(
        mode="charter_v7_review",
        payload_extra={"peer_artifact": "not a dict"},
    )
    result = agent.process(request)
    assert result["status"] == "refused"
    assert "missing_or_invalid_peer_artifact" in result["refusal_reason"]


def test_compliance_agent_preserves_principal(role_registry: RoleRegistry) -> None:
    agent = ComplianceAgent(role_registry=role_registry)
    for principal in ("alice", "bob"):
        result = agent.process(_request(mode="compliance_review", principal=principal))
        assert result["principal_id"] == principal
        assert result["evidence_bundle"]["principal_id"] == principal


# ∞Δ∞ ComplianceAgent test seal — both frameworks, all paths verified ∞Δ∞
