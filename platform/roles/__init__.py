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


# ============================================================
# Series 2 — Family role pack (v0.5.0)
# ============================================================
#
# Family role handlers inherit from executive parents and narrow scope
# to the household.  Same K1-K4 invariants; lower thresholds; family-
# guild approval surface; resonant shards stay private to the household
# node.
#
# Per LIVING_SPECS_YAML.md §5: family roles extend executive roles via
# Python subclassing.  The numeric / framework cores are reused; the
# narrowing happens at the role-handler level (process()) and at the
# role_spec.yaml PermissionSpec level (allowed_action_classes,
# breath_gate_thresholds).


def register_family_roles(role_registry: RoleRegistry) -> None:
    """Register the three family-tier role specs into the registry."""
    for role_id in (
        "family_cfo_agent",
        "family_compliance_shield",
        "household_synthesis_agent",
    ):
        spec_path = role_spec_path(role_id)
        if not spec_path.exists():
            raise FileNotFoundError(
                f"Family role spec for {role_id!r} not found at {spec_path}."
            )
        role_registry.register_from_yaml(spec_path)


def create_family_handlers(
    role_registry: RoleRegistry,
    auditor: Any | None = None,
    receipt_minter: Any | None = None,
) -> dict[str, Any]:
    """Instantiate the three Series 2 family role handlers.

    Each family handler subclasses an executive parent:
      family_cfo_agent           ← cfo_agent
      family_compliance_shield   ← compliance_agent
      household_synthesis_agent  ← synthesis_agent

    Same protocol surface (process(PlugInRequest) -> dict).  Family-tier
    metadata is added to every result (audit_scope, family_tier flag,
    breath_gate_thresholds, etc.) so downstream Auditor + Critic can
    apply household-tier gates.
    """
    from roles.family_cfo_agent.role import FamilyCFOAgent
    from roles.family_compliance_shield.role import FamilyComplianceShield
    from roles.household_synthesis_agent.role import HouseholdSynthesisAgent

    handlers: dict[str, Any] = {
        "family_cfo_agent": FamilyCFOAgent(),
        "family_compliance_shield": FamilyComplianceShield(
            role_registry=role_registry,
            auditor=auditor,
            receipt_minter=receipt_minter,
        ),
    }
    handlers["household_synthesis_agent"] = HouseholdSynthesisAgent(
        peer_handlers=handlers
    )
    return handlers


def create_full_handlers(
    role_registry: RoleRegistry,
    auditor: Any | None = None,
    receipt_minter: Any | None = None,
) -> dict[str, Any]:
    """Instantiate executive + family handlers in one combined dict.

    Useful for nodes that operate at Level 1 (Executive Mastery) AND
    Level 2 (Family Sovereignty) simultaneously — e.g., a fractional CFO
    using the platform for both client work and personal household.
    """
    handlers = create_demo2_handlers(
        role_registry=role_registry,
        auditor=auditor,
        receipt_minter=receipt_minter,
    )
    handlers.update(
        create_family_handlers(
            role_registry=role_registry,
            auditor=auditor,
            receipt_minter=receipt_minter,
        )
    )
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


def create_family_graph_handlers(
    role_registry: RoleRegistry,
    auditor: Any | None = None,
    receipt_minter: Any | None = None,
) -> dict[str, Any]:
    """Instantiate the LangGraph-wrapped Series 2 family role handlers (v0.5.0).

    Drop-in alternative to ``create_family_handlers``: same shape, same
    contract, but each family role's ``.process()`` runs through a LangGraph
    StateGraph (inherited from its executive parent) with family-tier
    metadata overlay. Deterministic FORECAST/SYNTHESIS/charter_v7 cores
    unchanged.
    """
    from roles.family_cfo_agent.graph import FamilyCFOAgentGraph
    from roles.family_compliance_shield.graph import FamilyComplianceShieldGraph
    from roles.household_synthesis_agent.graph import HouseholdSynthesisAgentGraph

    handlers: dict[str, Any] = {
        "family_cfo_agent": FamilyCFOAgentGraph(),
        "family_compliance_shield": FamilyComplianceShieldGraph(
            role_registry=role_registry,
            auditor=auditor,
            receipt_minter=receipt_minter,
        ),
    }
    handlers["household_synthesis_agent"] = HouseholdSynthesisAgentGraph(
        peer_handlers=handlers
    )
    return handlers


def create_full_graph_handlers(
    role_registry: RoleRegistry,
    auditor: Any | None = None,
    receipt_minter: Any | None = None,
) -> dict[str, Any]:
    """Instantiate executive + family LangGraph handlers in one combined dict.

    Mirrors ``create_full_handlers`` for the LangGraph-wrapped path. Useful
    for nodes that operate at Level 1 (Executive Mastery) AND Level 2
    (Family Sovereignty) simultaneously and want LangGraph observability.
    """
    handlers = create_demo2_graph_handlers(
        role_registry=role_registry,
        auditor=auditor,
        receipt_minter=receipt_minter,
    )
    handlers.update(
        create_family_graph_handlers(
            role_registry=role_registry,
            auditor=auditor,
            receipt_minter=receipt_minter,
        )
    )
    return handlers


# ∞Δ∞ Layer 3 — three roles, two frameworks for Compliance, one orchestrator ∞Δ∞
