"""LangGraph thin-layer wrap for CFO-agent.

Per ``roles/__init__.py`` docstring (Phase 4 plan):
    "Phase 3 implements role logic as pure-Python classes... LangGraph
    wrapping is a Phase 4 thin layer over the same logic."

Phase 5 ships this wrap. The deterministic FORECAST core
(``frameworks/forecast.apply_forecast``) is UNCHANGED; this graph
adds explicit state-machine structure for:

  - Future LLM-driven Explain / Translate nodes (Phase 6)
  - Conditional routing on validation outcomes
  - Observable transitions for Auditor introspection

The compiled graph satisfies the ``RoleHandler`` protocol via
``CFOAgentGraph.process(request)`` so it drops into the existing
plug-in interface without changing ``route_request``.
"""
from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from platform_layer.plugin_interface import PlugInRequest
from roles.cfo_agent.frameworks.forecast import (
    ForecastInputError,
    apply_forecast,
)


class _CFOState(TypedDict, total=False):
    """Mutable state passed between graph nodes."""

    request: PlugInRequest
    artifact: dict[str, Any] | None
    refusal: str | None
    output: dict[str, Any] | None


# -----------------------------------------------------------------------------
# Nodes (each pure; <10 complexity)
# -----------------------------------------------------------------------------
def _node_validate(state: _CFOState) -> dict[str, Any]:
    """Surface a structured refusal early on missing required inputs.

    Mirrors the validation in apply_forecast; running it here lets the
    graph short-circuit to finalize without touching the FORECAST core
    on bad input.
    """
    payload = state["request"].payload
    required = ("financial_data", "forecast_horizon")
    missing = [k for k in required if k not in payload]
    if missing:
        return {"refusal": f"invalid_forecast_inputs: missing {missing}"}
    return {"refusal": None}


def _node_apply_forecast(state: _CFOState) -> dict[str, Any]:
    """Invoke the deterministic FORECAST 8-step loop unchanged."""
    if state.get("refusal"):
        return {}  # already refused; pass through
    try:
        artifact = apply_forecast(state["request"].payload)
        return {"artifact": artifact.to_dict()}
    except ForecastInputError as e:
        return {"refusal": f"invalid_forecast_inputs: {e}"}


def _node_finalize(state: _CFOState) -> dict[str, Any]:
    """Compose the RoleHandler-protocol output dict."""
    request = state["request"]
    base = {
        "role_id": "cfo_agent",
        "framework": "FORECAST",
        "principal_id": request.principal_id,
        "request_id": request.request_id,
    }
    refusal = state.get("refusal")
    if refusal:
        output = {**base, "status": "refused", "refusal_reason": refusal}
    else:
        output = {
            **base,
            "status": "produced",
            "forecast_artifact": state.get("artifact"),
        }
    return {"output": output}


# -----------------------------------------------------------------------------
# Graph builder
# -----------------------------------------------------------------------------
def build_cfo_graph():
    """Compile the CFO-agent state graph."""
    sg = StateGraph(_CFOState)
    sg.add_node("validate", _node_validate)
    sg.add_node("apply_forecast", _node_apply_forecast)
    sg.add_node("finalize", _node_finalize)
    sg.set_entry_point("validate")
    sg.add_edge("validate", "apply_forecast")
    sg.add_edge("apply_forecast", "finalize")
    sg.add_edge("finalize", END)
    return sg.compile()


# -----------------------------------------------------------------------------
# RoleHandler implementation
# -----------------------------------------------------------------------------
class CFOAgentGraph:
    """LangGraph-wrapped CFO-agent. Implements the RoleHandler protocol.

    Drop-in replacement for ``CFOAgent`` — produces identical output
    structure for the same inputs (deterministic core unchanged).
    """

    role_id: str = "cfo_agent"
    framework: str = "FORECAST"

    def __init__(self) -> None:
        self._graph = build_cfo_graph()

    def process(self, request: PlugInRequest) -> dict[str, Any]:
        final_state = self._graph.invoke({
            "request": request,
            "artifact": None,
            "refusal": None,
            "output": None,
        })
        return final_state["output"]


# Seal: SOURCE — principal_id never leaves the request; nodes read it from state.
#       TRUTH — refusal path short-circuits without fabricating an artifact.
#       INTEGRITY — nodes are pure; deterministic FORECAST core untouched;
#                   graph structure is observable for the Auditor.
# ∞Δ∞ CFO-agent LangGraph wrap — Phase 5 thin layer over deterministic core ∞Δ∞
