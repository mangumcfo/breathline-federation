"""LangGraph thin-layer wrap for Compliance-agent.

Per role_spec.yaml (Q4 2026-05-06): one role, two frameworks. The graph
dispatches by ``payload.mode`` via a conditional edge:

    dispatch ─┬─ charter_v7_review  ─┐
              └─ compliance_review  ─┴─ finalize

The deterministic frameworks are UNCHANGED; nodes call into them.
"""
from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from platform_layer.plugin_interface import PlugInRequest
from platform_layer.registry import RoleRegistry
from roles.compliance_agent.frameworks.charter_v7 import (
    apply_charter_v7_review,
)
from roles.compliance_agent.frameworks.compliance_review import (
    apply_compliance_review,
)


_VALID_MODES = ("charter_v7_review", "compliance_review")


class _CompState(TypedDict, total=False):
    request: PlugInRequest
    role_registry: RoleRegistry
    auditor: Any | None
    receipt_minter: Any | None
    framework_used: str | None
    body: dict[str, Any] | None  # the framework-specific body (verdict / bundle)
    refusal: str | None
    output: dict[str, Any] | None


# -----------------------------------------------------------------------------
# Nodes (each pure; <10 complexity)
# -----------------------------------------------------------------------------
def _node_dispatch(state: _CompState) -> dict[str, Any]:
    """Validate mode field; the conditional edge routes by it."""
    mode = state["request"].payload.get("mode")
    if mode not in _VALID_MODES:
        return {"refusal": f"unknown_mode: {mode!r}; expected one of {_VALID_MODES}"}
    return {"refusal": None}


def _route_by_mode(state: _CompState) -> str:
    """Conditional edge selector — short-circuit on refusal."""
    if state.get("refusal"):
        return "finalize"
    mode = state["request"].payload.get("mode")
    if mode == "charter_v7_review":
        return "charter_v7"
    return "compliance_review"


def _node_charter_v7(state: _CompState) -> dict[str, Any]:
    peer_artifact = state["request"].payload.get("peer_artifact")
    if not isinstance(peer_artifact, dict):
        return {
            "refusal": (
                "missing_or_invalid_peer_artifact: "
                "charter_v7_review requires payload.peer_artifact to be a dict"
            ),
            "framework_used": "charter_v7_enforcement",
        }
    verdict = apply_charter_v7_review(peer_artifact)
    body: dict[str, Any] = {"verdict": verdict.to_dict()}
    if not verdict.approved:
        body["refusal_reason_inner"] = (
            f"charter_v7_drift_detected: {len(verdict.violations)} violation(s)"
        )
    return {
        "framework_used": "charter_v7_enforcement",
        "body": body,
    }


def _node_compliance_review(state: _CompState) -> dict[str, Any]:
    request = state["request"]
    time_window = request.payload.get("time_window")
    if time_window is not None and not isinstance(time_window, dict):
        return {
            "refusal": (
                "invalid_time_window: must be a dict (e.g., "
                "{'start': iso8601, 'end': iso8601}) or None"
            ),
            "framework_used": "compliance_review",
        }
    bundle = apply_compliance_review(
        role_registry=state["role_registry"],
        principal_id=request.principal_id,
        request_id=request.request_id,
        auditor=state.get("auditor"),
        receipt_minter=state.get("receipt_minter"),
        time_window=time_window,
    )
    return {
        "framework_used": "compliance_review",
        "body": {"evidence_bundle": bundle.to_dict()},
    }


def _node_finalize(state: _CompState) -> dict[str, Any]:
    request = state["request"]
    framework_used = state.get("framework_used") or "AUDIT"
    base = {
        "role_id": "compliance_agent",
        "framework": framework_used,
        "principal_id": request.principal_id,
        "request_id": request.request_id,
    }
    refusal = state.get("refusal")
    if refusal:
        return {"output": {**base, "status": "refused", "refusal_reason": refusal}}

    body = state.get("body") or {}
    inner_refusal = body.get("refusal_reason_inner")
    if inner_refusal:
        # charter_v7 detected drift in peer artifact → role-level refusal
        return {
            "output": {
                **base,
                "status": "refused",
                "refusal_reason": inner_refusal,
                "verdict": body.get("verdict"),
            }
        }

    output = {**base, "status": "produced"}
    output.update({k: v for k, v in body.items() if k != "refusal_reason_inner"})
    return {"output": output}


def build_compliance_graph():
    sg = StateGraph(_CompState)
    sg.add_node("dispatch", _node_dispatch)
    sg.add_node("charter_v7", _node_charter_v7)
    sg.add_node("compliance_review", _node_compliance_review)
    sg.add_node("finalize", _node_finalize)
    sg.set_entry_point("dispatch")
    sg.add_conditional_edges(
        "dispatch",
        _route_by_mode,
        {
            "charter_v7": "charter_v7",
            "compliance_review": "compliance_review",
            "finalize": "finalize",
        },
    )
    sg.add_edge("charter_v7", "finalize")
    sg.add_edge("compliance_review", "finalize")
    sg.add_edge("finalize", END)
    return sg.compile()


class ComplianceAgentGraph:
    """LangGraph-wrapped Compliance-agent. RoleHandler protocol-compatible."""

    role_id: str = "compliance_agent"
    framework: str = "AUDIT"

    def __init__(
        self,
        role_registry: RoleRegistry,
        auditor: Any | None = None,
        receipt_minter: Any | None = None,
    ) -> None:
        self._role_registry = role_registry
        self._auditor = auditor
        self._receipt_minter = receipt_minter
        self._graph = build_compliance_graph()

    def process(self, request: PlugInRequest) -> dict[str, Any]:
        final = self._graph.invoke({
            "request": request,
            "role_registry": self._role_registry,
            "auditor": self._auditor,
            "receipt_minter": self._receipt_minter,
            "framework_used": None,
            "body": None,
            "refusal": None,
            "output": None,
        })
        return final["output"]


# Seal: SOURCE — principal_id from request preserved across both framework paths.
#       TRUTH — charter_v7 drift surfaces as refusal with verdict body intact;
#               degraded compliance_review sections preserved verbatim.
#       INTEGRITY — conditional edge selects framework explicitly; no implicit
#                   fallback; deterministic frameworks unchanged.
# ∞Δ∞ Compliance-agent LangGraph wrap — Phase 5 thin layer, two frameworks ∞Δ∞
