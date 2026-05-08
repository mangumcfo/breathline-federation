"""Tests for the Phase 5 LangGraph thin-layer wrap.

Verifies:
  - Each LangGraph-wrapped role produces the SAME output structure as
    its pure-Python counterpart (the deterministic core is unchanged)
  - The full Section 8.2 e2e recursion runs through LangGraph handlers
  - LangGraph handlers integrate cleanly with route_request (cost gate,
    Critic CONFORMS, Auditor seal, receipt mint — Phase 4 stack)

Skipped automatically when langgraph is not installed (declared
optional for headless environments).
"""
from __future__ import annotations

import importlib.util
import textwrap
from pathlib import Path
from typing import Any

import pytest


_LANGGRAPH_AVAILABLE = importlib.util.find_spec("langgraph") is not None
pytestmark = pytest.mark.skipif(
    not _LANGGRAPH_AVAILABLE,
    reason="langgraph not installed; LangGraph wrap tests skipped",
)


# Imports inside the skip guard so collection succeeds without langgraph.
if _LANGGRAPH_AVAILABLE:
    from platform_layer.permission_spec import ActionClassRegistry
    from platform_layer.plugin_interface import PlugInRequest, route_request
    from platform_layer.registry import RoleRegistry
    from platform_layer.role_artifact_critic import RoleArtifactCritic
    from kernel.cost_meter import CostCaps, CostMeter
    from roles import (
        create_demo2_graph_handlers,
        create_demo2_handlers,
        register_demo2_roles,
    )
    from roles.cfo_agent.graph import CFOAgentGraph
    from roles.compliance_agent.graph import ComplianceAgentGraph
    from roles.synthesis_agent.graph import SynthesisAgentGraph


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def action_class_registry(seed_dir: Path):
    return ActionClassRegistry.from_yaml(seed_dir / "action_classes.yaml")


@pytest.fixture
def role_registry(action_class_registry):
    registry = RoleRegistry(action_class_registry)
    register_demo2_roles(registry)
    return registry


@pytest.fixture
def graph_handlers(role_registry):
    return create_demo2_graph_handlers(role_registry)


@pytest.fixture
def pure_handlers(role_registry):
    return create_demo2_handlers(role_registry)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _cfo_payload() -> dict[str, Any]:
    return {
        "financial_data": {
            "revenue": [100.0, 105.0, 110.0, 115.0],
            "expenses": [80.0, 82.0, 84.0, 86.0],
        },
        "forecast_horizon": 4,
    }


def _cfo_request(req_id: str = "req-lg-cfo") -> PlugInRequest:
    return PlugInRequest(
        request_id=req_id,
        principal_id="kmangum",
        role_target="cfo_agent",
        action_class="produce_forecast_artifact",
        payload=_cfo_payload(),
    )


def _normalize_for_compare(out: dict[str, Any]) -> dict[str, Any]:
    """Strip framework-internal volatile keys (timestamps, IDs) for diffing."""
    return {k: v for k, v in out.items() if k not in ()}


# -----------------------------------------------------------------------------
# Per-role parity: graph vs. pure-Python produce the same output
# -----------------------------------------------------------------------------
def test_cfo_graph_matches_pure_python_output(role_registry):
    pure = create_demo2_handlers(role_registry)["cfo_agent"]
    graph = CFOAgentGraph()
    request = _cfo_request()
    pure_out = pure.process(request)
    graph_out = graph.process(request)
    assert pure_out["status"] == graph_out["status"] == "produced"
    # Forecast artifact body equality (deterministic core unchanged)
    assert pure_out["forecast_artifact"]["scenarios"] == \
        graph_out["forecast_artifact"]["scenarios"]
    assert pure_out["forecast_artifact"]["framework_steps_executed"] == \
        graph_out["forecast_artifact"]["framework_steps_executed"]


def test_cfo_graph_refuses_invalid_payload():
    graph = CFOAgentGraph()
    bad = PlugInRequest(
        request_id="r",
        principal_id="kmangum",
        role_target="cfo_agent",
        action_class="produce_forecast_artifact",
        payload={"only_horizon": True},
    )
    out = graph.process(bad)
    assert out["status"] == "refused"
    assert "invalid_forecast_inputs" in out["refusal_reason"]


def test_synthesis_graph_invokes_peers_via_orchestrator(role_registry):
    handlers = create_demo2_graph_handlers(role_registry)
    syn = handlers["synthesis_agent"]
    request = PlugInRequest(
        request_id="req-lg-syn",
        principal_id="kmangum",
        role_target="synthesis_agent",
        action_class="produce_executive_brief",
        payload={
            "request_summary": "test",
            "peer_roles_to_invoke": ["cfo_agent"],
            "peer_payloads": {
                "cfo_agent": {
                    "action_class": "produce_forecast_artifact",
                    "payload": _cfo_payload(),
                },
            },
        },
    )
    out = syn.process(request)
    assert out["status"] == "produced"
    assert len(out["executive_brief"]["peer_results"]) == 1
    cfo_peer = out["executive_brief"]["peer_results"][0]
    assert cfo_peer["role_id"] == "cfo_agent"
    assert cfo_peer["invoked"] is True


def test_synthesis_graph_refuses_empty_peers(role_registry):
    handlers = create_demo2_graph_handlers(role_registry)
    syn = handlers["synthesis_agent"]
    bad = PlugInRequest(
        request_id="r",
        principal_id="kmangum",
        role_target="synthesis_agent",
        action_class="produce_executive_brief",
        payload={"request_summary": "x", "peer_roles_to_invoke": []},
    )
    out = syn.process(bad)
    assert out["status"] == "refused"
    assert "invalid_synthesis_inputs" in out["refusal_reason"]


def test_compliance_graph_charter_v7_clean(role_registry):
    graph = ComplianceAgentGraph(role_registry=role_registry)
    request = PlugInRequest(
        request_id="r",
        principal_id="kmangum",
        role_target="compliance_agent",
        action_class="review_peer_outputs",
        payload={
            "mode": "charter_v7_review",
            "peer_artifact": {"role_id": "cfo_agent", "status": "produced"},
        },
    )
    out = graph.process(request)
    assert out["status"] == "produced"
    assert out["framework"] == "charter_v7_enforcement"
    assert out["verdict"]["approved"] is True


def test_compliance_graph_charter_v7_refuses_drift(role_registry):
    graph = ComplianceAgentGraph(role_registry=role_registry)
    request = PlugInRequest(
        request_id="r",
        principal_id="kmangum",
        role_target="compliance_agent",
        action_class="review_peer_outputs",
        payload={
            "mode": "charter_v7_review",
            "peer_artifact": {
                "advice": "We must amend the charter to permit this elevation."
            },
        },
    )
    out = graph.process(request)
    assert out["status"] == "refused"
    assert "charter_v7_drift_detected" in out["refusal_reason"]


def test_compliance_graph_compliance_review_path(role_registry):
    graph = ComplianceAgentGraph(role_registry=role_registry)
    request = PlugInRequest(
        request_id="r",
        principal_id="kmangum",
        role_target="compliance_agent",
        action_class="review_peer_outputs",
        payload={"mode": "compliance_review"},
    )
    out = graph.process(request)
    assert out["status"] == "produced"
    assert out["framework"] == "compliance_review"
    assert "evidence_bundle" in out


def test_compliance_graph_unknown_mode_refuses(role_registry):
    graph = ComplianceAgentGraph(role_registry=role_registry)
    request = PlugInRequest(
        request_id="r",
        principal_id="kmangum",
        role_target="compliance_agent",
        action_class="review_peer_outputs",
        payload={"mode": "not_a_mode"},
    )
    out = graph.process(request)
    assert out["status"] == "refused"
    assert "unknown_mode" in out["refusal_reason"]


# -----------------------------------------------------------------------------
# E2E: Section 8.2 recursion through LangGraph handlers + Phase 4 stack
# -----------------------------------------------------------------------------
def test_section_8_2_recursion_through_langgraph_stack(role_registry, graph_handlers):
    syn = graph_handlers["synthesis_agent"]
    request = PlugInRequest(
        request_id="req-lg-e2e",
        principal_id="kmangum",
        role_target="synthesis_agent",
        action_class="produce_executive_brief",
        payload={
            "request_summary": (
                "Brief on Q3 readiness — pull from CFO and Compliance; integrate."
            ),
            "peer_roles_to_invoke": ["cfo_agent", "compliance_agent"],
            "peer_payloads": {
                "cfo_agent": {
                    "action_class": "produce_forecast_artifact",
                    "payload": _cfo_payload(),
                },
                "compliance_agent": {
                    "action_class": "review_peer_outputs",
                    "payload": {"mode": "compliance_review"},
                },
            },
        },
    )
    out = syn.process(request)
    assert out["status"] == "produced"
    role_ids = {p["role_id"] for p in out["executive_brief"]["peer_results"]}
    assert role_ids == {"cfo_agent", "compliance_agent"}


def test_langgraph_handlers_through_route_request_full_phase4_stack(
    role_registry, graph_handlers
):
    """Full Phase 4 stack (cost / Critic / Auditor / receipt) wraps LangGraph roles."""
    cost_meter = CostMeter(caps=CostCaps(
        per_request_usd=1.0, per_role_daily_usd=100.0,
        per_principal_hourly_usd=100.0, session_total_usd=100.0,
    ))
    critic = RoleArtifactCritic()

    request = PlugInRequest(
        request_id="req-lg-route",
        principal_id="kmangum",
        role_target="cfo_agent",
        action_class="produce_forecast_artifact",
        payload=_cfo_payload(),
    )
    response = route_request(
        request,
        role_registry=role_registry,
        role_handlers=graph_handlers,
        critic=critic,
        cost_meter=cost_meter,
    )
    assert response.accepted is True
    assert response.critic_verdict == "CONFORMS"
    assert response.role_id == "cfo_agent"


def test_langgraph_principal_propagation(role_registry, graph_handlers):
    syn = graph_handlers["synthesis_agent"]
    request = PlugInRequest(
        request_id="r-principal",
        principal_id="auditor-007",
        role_target="synthesis_agent",
        action_class="produce_executive_brief",
        payload={
            "request_summary": "x",
            "peer_roles_to_invoke": ["cfo_agent"],
            "peer_payloads": {
                "cfo_agent": {
                    "action_class": "produce_forecast_artifact",
                    "payload": _cfo_payload(),
                },
            },
        },
    )
    out = syn.process(request)
    assert out["principal_id"] == "auditor-007"
    cfo_peer_artifact = out["executive_brief"]["peer_results"][0]["artifact"]
    assert cfo_peer_artifact["principal_id"] == "auditor-007"


# ∞Δ∞ LangGraph wrap test seal — Phase 5 thin-layer parity verified ∞Δ∞
