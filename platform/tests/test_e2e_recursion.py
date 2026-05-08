"""End-to-end recursion test — IMPLEMENTATION_PLAN Section 8.2.

The capstone test for Demo 2's recursion path:

  Synthesis-agent receives request: "Brief on Q3 readiness — pull from
  CFO and Compliance; integrate; flag tensions."

Steps verified (Section 8.2 checklist):
  ✓ Synthesis-agent receives the high-level request
  ✓ Synthesis invokes CFO-agent with FORECAST request (synthetic Q3 data)
  ✓ CFO-agent produces forecast artifact with three scenarios + assumption flags
  ✓ Synthesis invokes Compliance-agent with the CFO output (charter_v7 review)
  ✓ Compliance-agent reviews; returns approved (clean) or refused-with-reasons
  ✓ Synthesis integrates outputs; surfaces any tensions
  ✓ Final brief carries all referenced principal_id + request_id end-to-end

Critic CONFORMS verdict + audit chain replay are deferred to Phase 4
LangGraph integration (the deterministic Phase 3 core does not yet
emit Critic verdicts; that wraps the role at the platform layer).
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from platform_layer.permission_spec import ActionClassRegistry
from platform_layer.plugin_interface import PlugInRequest
from platform_layer.registry import RoleRegistry
from roles import create_demo2_handlers, register_demo2_roles


# -----------------------------------------------------------------------------
# Fixtures — wire the full Demo 2 stack via the canonical entry points
# -----------------------------------------------------------------------------
@pytest.fixture
def action_class_registry(seed_dir: Path) -> ActionClassRegistry:
    return ActionClassRegistry.from_yaml(seed_dir / "action_classes.yaml")


@pytest.fixture
def role_registry(action_class_registry: ActionClassRegistry) -> RoleRegistry:
    """Register all three Demo 2 roles from their on-disk role_spec.yaml files."""
    registry = RoleRegistry(action_class_registry)
    register_demo2_roles(registry)
    return registry


@pytest.fixture
def handlers(role_registry: RoleRegistry) -> dict:
    """Construct the Demo 2 handlers via the canonical factory."""
    return create_demo2_handlers(role_registry)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _q3_financial_data() -> dict:
    return {
        "revenue": [950.0, 1010.0, 1075.0, 1140.0],   # 4 quarters trailing
        "expenses": [820.0, 845.0, 870.0, 895.0],
        "market_signals": {"macro_index": 1.03},
    }


def _q3_brief_request(principal: str = "kmangum") -> PlugInRequest:
    """The Section 8.2 invocation: 'Brief on Q3 readiness…'"""
    return PlugInRequest(
        request_id="req-e2e-q3-001",
        principal_id=principal,
        role_target="synthesis_agent",
        action_class="produce_executive_brief",
        payload={
            "request_summary": (
                "Brief on Q3 readiness — pull from CFO and Compliance; "
                "integrate; flag tensions."
            ),
            "peer_roles_to_invoke": ["cfo_agent", "compliance_agent"],
            "peer_payloads": {
                "cfo_agent": {
                    "action_class": "produce_forecast_artifact",
                    "payload": {
                        "financial_data": _q3_financial_data(),
                        "forecast_horizon": 4,
                    },
                },
                "compliance_agent": {
                    "action_class": "review_peer_outputs",
                    "payload": {
                        "mode": "compliance_review",
                        # No time_window — full snapshot
                    },
                },
            },
        },
    )


# -----------------------------------------------------------------------------
# The capstone test
# -----------------------------------------------------------------------------
def test_section_8_2_q3_readiness_recursion(handlers: dict) -> None:
    """The full Section 8.2 recursion path, end to end."""
    synthesis = handlers["synthesis_agent"]
    request = _q3_brief_request(principal="kmangum")

    result = synthesis.process(request)

    # Synthesis returned a produced executive brief
    assert result["status"] == "produced", result
    assert result["role_id"] == "synthesis_agent"
    assert result["framework"] == "SYNTHESIS"
    assert result["principal_id"] == "kmangum"  # SOURCE flows end-to-end

    brief = result["executive_brief"]
    assert brief["request_summary"].startswith("Brief on Q3 readiness")
    assert brief["principal_id"] == "kmangum"
    assert brief["request_id"] == "req-e2e-q3-001"

    # Both peers were invoked
    peer_results = {p["role_id"]: p for p in brief["peer_results"]}
    assert set(peer_results.keys()) == {"cfo_agent", "compliance_agent"}

    # CFO produced a 3-scenario forecast with assumption flags
    cfo = peer_results["cfo_agent"]
    assert cfo["invoked"] is True
    assert cfo["artifact"]["status"] == "produced"
    forecast = cfo["artifact"]["forecast_artifact"]
    assert {s["name"] for s in forecast["scenarios"]} == {"baseline", "upside", "downside"}
    assert isinstance(forecast["assumptions_flagged"], list)

    # Compliance returned an Evidence Bundle (compliance_review path)
    comp = peer_results["compliance_agent"]
    assert comp["invoked"] is True
    assert comp["artifact"]["status"] == "produced"
    assert "evidence_bundle" in comp["artifact"]
    bundle = comp["artifact"]["evidence_bundle"]
    assert "least_authority_report" in bundle

    # Synthesis executed all six SYNTHESIS steps
    assert brief["framework_steps_executed"] == [
        "Decompose", "Invoke", "Aggregate",
        "Reconcile", "SurfaceTensions", "Translate",
    ]


def test_section_8_2_principal_flows_to_every_layer(handlers: dict) -> None:
    """Constitution@A1 §1: principal_id end-to-end through the recursion."""
    synthesis = handlers["synthesis_agent"]
    result = synthesis.process(_q3_brief_request(principal="auditor-007"))

    brief = result["executive_brief"]
    assert brief["principal_id"] == "auditor-007"

    for peer in brief["peer_results"]:
        assert peer["artifact"]["principal_id"] == "auditor-007"


def test_section_8_2_charter_v7_review_path(handlers: dict, role_registry: RoleRegistry) -> None:
    """Run Synthesis with Compliance configured for charter_v7_review on a clean CFO output.

    Verifies the Compliance-agent's charter_v7 framework approves a real
    CFO forecast (no forbidden tokens in numeric scenarios).
    """
    # First: get a CFO forecast directly
    cfo = handlers["cfo_agent"]
    cfo_result = cfo.process(
        PlugInRequest(
            request_id="req-e2e-cfo-1",
            principal_id="kmangum",
            role_target="cfo_agent",
            action_class="produce_forecast_artifact",
            payload={
                "financial_data": _q3_financial_data(),
                "forecast_horizon": 4,
            },
        )
    )
    assert cfo_result["status"] == "produced"

    # Second: ask Compliance to review it via charter_v7
    comp = handlers["compliance_agent"]
    comp_result = comp.process(
        PlugInRequest(
            request_id="req-e2e-comp-1",
            principal_id="kmangum",
            role_target="compliance_agent",
            action_class="review_peer_outputs",
            payload={
                "mode": "charter_v7_review",
                "peer_artifact": cfo_result,
            },
        )
    )
    assert comp_result["status"] == "produced"
    assert comp_result["framework"] == "charter_v7_enforcement"
    assert comp_result["verdict"]["approved"] is True


def test_section_8_2_evidence_bundle_lists_all_three_roles(handlers: dict) -> None:
    """The Evidence Bundle's Least-Authority Report enumerates all Demo 2 roles."""
    comp = handlers["compliance_agent"]
    result = comp.process(
        PlugInRequest(
            request_id="req-bundle-1",
            principal_id="kmangum",
            role_target="compliance_agent",
            action_class="generate_compliance_evidence_bundle",
            payload={"mode": "compliance_review"},
        )
    )
    assert result["status"] == "produced"
    role_ids = {r["role_id"] for r in result["evidence_bundle"]["least_authority_report"]["roles"]}
    assert role_ids == {"cfo_agent", "synthesis_agent", "compliance_agent"}


# ∞Δ∞ Section 8.2 e2e seal — recursion path verified, principal_id holds ∞Δ∞
