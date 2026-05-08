"""Layer 3 — role agents.

Per IMPLEMENTATION_PLAN.md Section 1, Demo 2 ships 3 fully-implemented
roles (CFO, Synthesis, Compliance). The other 9 from the 12-book series
are designed in v1.0 and onboarded via the spec-only path documented in
Appendix C.

Per peer-review decision Q1 (2026-05-06):
  - Kernel primitives (Constructor, Critic, Auditor, Governor) are shared
    persistent subgraphs invoked by every role
  - Role-specific framework logic (FORECAST, SYNTHESIS, charter_v7 +
    compliance_review) is implemented per-role for independent evolution

Phase 3 implements role logic as pure-Python classes implementing the
RoleHandler protocol from platform_layer.plugin_interface. LangGraph
wrapping is a Phase 4 thin layer over the same logic — Phase 3 keeps the
test suite deterministic without external LLM dependencies.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from platform_layer.plugin_interface import PlugInRequest
from platform_layer.registry import RoleRegistry


ROLES_DIR = Path(__file__).resolve().parent


def role_spec_path(role_id: str) -> Path:
    """Return the path to a role's role_spec.yaml."""
    return ROLES_DIR / role_id / "role_spec.yaml"


def register_demo2_roles(role_registry: RoleRegistry) -> None:
    """Register the three Demo 2 role specs into the registry.

    The Permission Spec validation (Charter V.7 inheritance, action class
    vocabulary) happens inside RoleRegistry.register_from_yaml.
    """
    for role_id in ("cfo_agent", "synthesis_agent", "compliance_agent"):
        spec_path = role_spec_path(role_id)
        if not spec_path.exists():
            raise FileNotFoundError(
                f"Role spec for {role_id!r} not found at {spec_path}. "
                f"Cannot complete Layer 3 instantiation."
            )
        role_registry.register_from_yaml(spec_path)


def create_demo2_handlers(
    role_registry: RoleRegistry,
    auditor: Any | None = None,
    receipt_minter: Any | None = None,
) -> dict[str, Any]:
    """Instantiate the three Demo 2 role handlers.

    Each handler is a pure-Python class implementing the RoleHandler
    protocol (process(PlugInRequest) -> dict). Auditor + receipt_minter
    are injected for the Compliance-agent's compliance_review framework
    (which needs to enumerate audit entries and embed receipt metadata).
    """
    from roles.cfo_agent.role import CFOAgent
    from roles.synthesis_agent.role import SynthesisAgent
    from roles.compliance_agent.role import ComplianceAgent

    handlers: dict[str, Any] = {
        "cfo_agent": CFOAgent(),
        "compliance_agent": ComplianceAgent(
            role_registry=role_registry,
            auditor=auditor,
            receipt_minter=receipt_minter,
        ),
    }
    # Synthesis takes the handlers dict so it can invoke peer roles
    handlers["synthesis_agent"] = SynthesisAgent(peer_handlers=handlers)
    return handlers


def create_demo2_graph_handlers(
    role_registry: RoleRegistry,
    auditor: Any | None = None,
    receipt_minter: Any | None = None,
) -> dict[str, Any]:
    """Instantiate the LangGraph-wrapped Demo 2 role handlers (Phase 5).

    Drop-in alternative to ``create_demo2_handlers``: same shape, same
    contract, but each role's ``.process()`` runs through a LangGraph
    StateGraph wrapping the deterministic pure-Python core. Use this
    factory when wiring the runtime against LangGraph-observable role
    invocations; use ``create_demo2_handlers`` for the lighter pure-Python
    path.
    """
    from roles.cfo_agent.graph import CFOAgentGraph
    from roles.synthesis_agent.graph import SynthesisAgentGraph
    from roles.compliance_agent.graph import ComplianceAgentGraph

    handlers: dict[str, Any] = {
        "cfo_agent": CFOAgentGraph(),
        "compliance_agent": ComplianceAgentGraph(
            role_registry=role_registry,
            auditor=auditor,
            receipt_minter=receipt_minter,
        ),
    }
    handlers["synthesis_agent"] = SynthesisAgentGraph(peer_handlers=handlers)
    return handlers


# ∞Δ∞ Layer 3 — three roles, two frameworks for Compliance, one orchestrator ∞Δ∞
