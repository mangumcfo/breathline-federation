"""Tests for Synthesis-agent — Book 12 SYNTHESIS orchestrator.

Validates the recursion path: Synthesis invokes CFO (real) and a stub
Compliance peer, aggregates outputs, surfaces tensions. Hermetic — no
LLM, no network. Phase 3 deterministic core.

Section 8.2 of IMPLEMENTATION_PLAN.md describes the full e2e recursion
test ("Brief on Q3 readiness…"). This file covers the orchestrator
mechanics; the full e2e test lands in test_e2e_recursion.py once
Compliance-agent exists.
"""
from __future__ import annotations

from typing import Any

import pytest

from platform_layer.plugin_interface import PlugInRequest
from roles.cfo_agent import CFOAgent
from roles.synthesis_agent import SynthesisAgent
from roles.synthesis_agent.frameworks.synthesis import (
    SynthesisInputError,
    apply_synthesis,
)


# -----------------------------------------------------------------------------
# Test stubs
# -----------------------------------------------------------------------------
class _ProducingStub:
    """Peer that always returns a 'produced' artifact."""

    def __init__(self, role_id: str, framework: str = "STUB") -> None:
        self.role_id = role_id
        self.framework = framework

    def process(self, request: PlugInRequest) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "framework": self.framework,
            "status": "produced",
            "principal_id": request.principal_id,
            "request_id": request.request_id,
            "stub_artifact": {"note": "test stub output"},
        }


class _RefusingStub:
    """Peer that always refuses, simulating a Compliance refusal."""

    def __init__(self, role_id: str = "compliance_agent") -> None:
        self.role_id = role_id

    def process(self, request: PlugInRequest) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "framework": "compliance_review",
            "status": "refused",
            "refusal_reason": "test_refusal: insufficient evidence",
            "principal_id": request.principal_id,
            "request_id": request.request_id,
        }


class _RaisingStub:
    """Peer that raises, to test orchestrator's error containment."""

    role_id = "buggy_peer"

    def process(self, request: PlugInRequest) -> dict[str, Any]:
        raise RuntimeError("simulated peer failure")


def _cfo_payload() -> dict[str, Any]:
    return {
        "action_class": "produce_forecast_artifact",
        "payload": {
            "financial_data": {
                "revenue": [100.0, 105.0, 110.0, 115.0],
                "expenses": [80.0, 82.0, 84.0, 86.0],
            },
            "forecast_horizon": 4,
        },
    }


def _synthesis_request(
    principal_id: str = "kmangum",
    peers: list[str] | None = None,
    peer_payloads: dict[str, Any] | None = None,
) -> PlugInRequest:
    return PlugInRequest(
        request_id="req-syn-001",
        principal_id=principal_id,
        role_target="synthesis_agent",
        action_class="produce_executive_brief",
        payload={
            "request_summary": "Brief on Q3 readiness — pull from CFO; integrate; flag tensions.",
            "peer_roles_to_invoke": peers or ["cfo_agent"],
            "peer_payloads": peer_payloads or {"cfo_agent": _cfo_payload()},
        },
    )


# -----------------------------------------------------------------------------
# Framework-level
# -----------------------------------------------------------------------------
def test_synthesis_invokes_real_cfo_agent() -> None:
    handlers = {"cfo_agent": CFOAgent()}
    brief = apply_synthesis(_synthesis_request(), handlers)
    assert len(brief.peer_results) == 1
    cfo_result = brief.peer_results[0]
    assert cfo_result.role_id == "cfo_agent"
    assert cfo_result.invoked is True
    assert cfo_result.artifact is not None
    assert cfo_result.artifact["status"] == "produced"


def test_synthesis_propagates_principal_to_peers() -> None:
    captured: list[str] = []

    class _Capturing:
        def process(self, request: PlugInRequest) -> dict[str, Any]:
            captured.append(request.principal_id)
            return {"status": "produced", "framework": "X"}

    handlers = {"cfo_agent": _Capturing()}
    apply_synthesis(_synthesis_request(principal_id="alice"), handlers)
    assert captured == ["alice"]  # principal_id flows end-to-end


def test_synthesis_executes_six_steps() -> None:
    handlers = {"cfo_agent": CFOAgent()}
    brief = apply_synthesis(_synthesis_request(), handlers)
    assert brief.framework_steps_executed == [
        "Decompose", "Invoke", "Aggregate",
        "Reconcile", "SurfaceTensions", "Translate",
    ]


def test_synthesis_surfaces_tensions_on_partial_refusal() -> None:
    handlers = {
        "cfo_agent": CFOAgent(),
        "compliance_agent": _RefusingStub(),
    }
    brief = apply_synthesis(
        _synthesis_request(
            peers=["cfo_agent", "compliance_agent"],
            peer_payloads={"cfo_agent": _cfo_payload()},
        ),
        handlers,
    )
    assert any("partial_synthesis" in t for t in brief.tensions_surfaced)


def test_synthesis_flags_missing_peer() -> None:
    handlers = {"cfo_agent": CFOAgent()}  # compliance_agent absent
    brief = apply_synthesis(
        _synthesis_request(peers=["cfo_agent", "compliance_agent"]),
        handlers,
    )
    missing = [r for r in brief.peer_results if r.role_id == "compliance_agent"]
    assert len(missing) == 1
    assert missing[0].invoked is False
    assert "peer_handler_unavailable" in (missing[0].refusal_reason or "")
    assert any("missing_peers" in t for t in brief.tensions_surfaced)


def test_synthesis_contains_raising_peer() -> None:
    handlers = {"buggy_peer": _RaisingStub()}
    brief = apply_synthesis(
        _synthesis_request(
            peers=["buggy_peer"],
            peer_payloads={"buggy_peer": {"payload": {}}},
        ),
        handlers,
    )
    result = brief.peer_results[0]
    assert result.invoked is True
    assert result.artifact is None
    assert "peer_invocation_error" in (result.refusal_reason or "")


def test_synthesis_rejects_missing_inputs() -> None:
    request = PlugInRequest(
        request_id="r",
        principal_id="kmangum",
        role_target="synthesis_agent",
        action_class="produce_executive_brief",
        payload={"request_summary": "x"},  # peer_roles_to_invoke missing
    )
    with pytest.raises(SynthesisInputError):
        apply_synthesis(request, {})


def test_synthesis_rejects_empty_peer_list() -> None:
    request = PlugInRequest(
        request_id="r",
        principal_id="kmangum",
        role_target="synthesis_agent",
        action_class="produce_executive_brief",
        payload={"request_summary": "x", "peer_roles_to_invoke": []},
    )
    with pytest.raises(SynthesisInputError):
        apply_synthesis(request, {})


# -----------------------------------------------------------------------------
# RoleHandler integration
# -----------------------------------------------------------------------------
def test_synthesis_agent_process_returns_executive_brief() -> None:
    handlers: dict[str, Any] = {"cfo_agent": CFOAgent()}
    agent = SynthesisAgent(peer_handlers=handlers)
    result = agent.process(_synthesis_request())

    assert result["status"] == "produced"
    assert result["role_id"] == "synthesis_agent"
    assert result["framework"] == "SYNTHESIS"
    assert result["principal_id"] == "kmangum"
    brief = result["executive_brief"]
    assert brief["request_summary"].startswith("Brief on Q3 readiness")
    assert len(brief["peer_results"]) == 1


def test_synthesis_agent_sees_late_bound_peers() -> None:
    """When the handlers dict is mutated AFTER construction, Synthesis sees it.

    Mirrors the registration flow in roles/__init__.py:create_demo2_handlers
    where handlers are built and then mutated to include synthesis itself.
    """
    handlers: dict[str, Any] = {}
    agent = SynthesisAgent(peer_handlers=handlers)
    handlers["cfo_agent"] = CFOAgent()  # late-bound
    result = agent.process(_synthesis_request())
    assert result["status"] == "produced"
    assert len(result["executive_brief"]["peer_results"]) == 1


def test_synthesis_agent_refuses_malformed_payload() -> None:
    agent = SynthesisAgent(peer_handlers={})
    request = PlugInRequest(
        request_id="r",
        principal_id="kmangum",
        role_target="synthesis_agent",
        action_class="produce_executive_brief",
        payload={"request_summary": ""},  # empty summary
    )
    result = agent.process(request)
    assert result["status"] == "refused"
    assert "invalid_synthesis_inputs" in result["refusal_reason"]


# ∞Δ∞ Synthesis test seal — orchestrator recursion + tension surfacing verified ∞Δ∞
