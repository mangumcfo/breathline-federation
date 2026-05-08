"""LangGraph thin-layer wrap for Synthesis-agent (orchestrator).

Phase 5 ships this wrap over the deterministic SYNTHESIS framework.
The graph structure surfaces the orchestration sequence (validate →
invoke_peers → aggregate → finalize) while delegating to the existing
pure-Python ``apply_synthesis`` for the actual peer invocation.

LangGraph affords a future expansion point: per-peer subgraphs,
parallel peer invocation, Explain/Translate LLM nodes — all without
touching the deterministic numeric/orchestration logic.
"""
from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from platform_layer.plugin_interface import PlugInRequest
from roles.synthesis_agent.frameworks.synthesis import (
    SynthesisInputError,
    apply_synthesis,
)


class _SynState(TypedDict, total=False):
    request: PlugInRequest
    peer_handlers: dict[str, Any]
    brief: dict[str, Any] | None
    refusal: str | None
    output: dict[str, Any] | None


# -----------------------------------------------------------------------------
# Nodes (each pure; <10 complexity)
# -----------------------------------------------------------------------------
def _node_validate(state: _SynState) -> dict[str, Any]:
    payload = state["request"].payload
    if not isinstance(payload.get("request_summary"), str) or not payload.get("request_summary"):
        return {"refusal": "invalid_synthesis_inputs: request_summary missing/empty"}
    peers = payload.get("peer_roles_to_invoke")
    if not isinstance(peers, list) or not peers:
        return {"refusal": "invalid_synthesis_inputs: peer_roles_to_invoke missing/empty"}
    return {"refusal": None}


def _node_orchestrate(state: _SynState) -> dict[str, Any]:
    """Invoke peers and aggregate via the deterministic SYNTHESIS core."""
    if state.get("refusal"):
        return {}
    try:
        brief = apply_synthesis(state["request"], state["peer_handlers"])
        return {"brief": brief.to_dict()}
    except SynthesisInputError as e:
        return {"refusal": f"invalid_synthesis_inputs: {e}"}


def _node_finalize(state: _SynState) -> dict[str, Any]:
    request = state["request"]
    base = {
        "role_id": "synthesis_agent",
        "framework": "SYNTHESIS",
        "principal_id": request.principal_id,
        "request_id": request.request_id,
    }
    refusal = state.get("refusal")
    if refusal:
        output = {**base, "status": "refused", "refusal_reason": refusal}
    else:
        output = {**base, "status": "produced", "executive_brief": state.get("brief")}
    return {"output": output}


def build_synthesis_graph():
    sg = StateGraph(_SynState)
    sg.add_node("validate", _node_validate)
    sg.add_node("orchestrate", _node_orchestrate)
    sg.add_node("finalize", _node_finalize)
    sg.set_entry_point("validate")
    sg.add_edge("validate", "orchestrate")
    sg.add_edge("orchestrate", "finalize")
    sg.add_edge("finalize", END)
    return sg.compile()


class SynthesisAgentGraph:
    """LangGraph-wrapped Synthesis-agent. RoleHandler protocol-compatible."""

    role_id: str = "synthesis_agent"
    framework: str = "SYNTHESIS"

    def __init__(self, peer_handlers: dict[str, Any]) -> None:
        self._peer_handlers = peer_handlers
        self._graph = build_synthesis_graph()

    def process(self, request: PlugInRequest) -> dict[str, Any]:
        final = self._graph.invoke({
            "request": request,
            "peer_handlers": self._peer_handlers,
            "brief": None,
            "refusal": None,
            "output": None,
        })
        return final["output"]


# Seal: SOURCE — principal_id flows from request into peer_handlers via apply_synthesis.
#       TRUTH — orchestration outcome (peer refusals, missing peers) reaches the brief.
#       INTEGRITY — graph order matches the deterministic SYNTHESIS step list;
#                   peer_handlers held by reference (late-bound peers visible).
# ∞Δ∞ Synthesis-agent LangGraph wrap — Phase 5 thin layer over orchestrator core ∞Δ∞
