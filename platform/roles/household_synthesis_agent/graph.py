"""LangGraph thin-layer wrap for HouseholdSynthesisAgent (Ladder Level 2).

Family-tier metadata overlay over the executive ``SynthesisAgentGraph``'s
compiled StateGraph. Same SYNTHESIS orchestration; same peer invocation;
lower recursion depths and family-scope peer allowlist applied via the
result-tag overlay so downstream gates apply household-tier breath-gates.

Mirrors ``household_synthesis_agent/role.py`` (HouseholdSynthesisAgent).
Phase 5 thin-layer wrap; v0.5.0.
"""
from __future__ import annotations

from typing import Any

from platform_layer.plugin_interface import PlugInRequest
from roles.synthesis_agent.graph import SynthesisAgentGraph
from roles.household_synthesis_agent.role import (
    HOUSEHOLD_BREATH_GATE_AT_DEPTH,
    HOUSEHOLD_RECURSION_DEPTH_DEFAULT,
    HOUSEHOLD_RECURSION_DEPTH_MAX,
)


class HouseholdSynthesisAgentGraph(SynthesisAgentGraph):
    """LangGraph-wrapped Household Synthesis agent (Series 2 Book 2, Ladder Level 2).

    Inherits SYNTHESIS graph from ``SynthesisAgentGraph``. Narrows: lower
    recursion depths, family-scope peer roles only (typically the family
    triad's other two handlers).
    """

    role_id: str = "household_synthesis_agent"
    framework: str = "SYNTHESIS"
    series: str = "family"
    parent_role_id: str = "synthesis_agent"
    ladder_level: int = 2  # Family Sovereignty

    recursion_depth_default: int = HOUSEHOLD_RECURSION_DEPTH_DEFAULT
    recursion_depth_max: int = HOUSEHOLD_RECURSION_DEPTH_MAX
    breath_gate_at_depth: int = HOUSEHOLD_BREATH_GATE_AT_DEPTH

    def __init__(self, peer_handlers: dict[str, Any]) -> None:
        super().__init__(peer_handlers=peer_handlers)

    def process(self, request: PlugInRequest) -> dict[str, Any]:
        """Run parent graph, then overlay household-tier metadata."""
        result = super().process(request)
        result["audit_scope"] = "household"
        result["recursion_depth_default"] = self.recursion_depth_default
        result["recursion_depth_max"] = self.recursion_depth_max
        result["breath_gate_at_depth"] = self.breath_gate_at_depth
        result["family_tier"] = True
        result["role_id"] = self.role_id
        result["series"] = self.series
        return result


# Seal: SOURCE — peer_handlers held by reference; principal_id flows via parent.
#       TRUTH — same orchestration logic as enterprise; thresholds explicit.
#       INTEGRITY — parent graph untouched; family-tier metadata additive only.
# ∞Δ∞ HouseholdSynthesisAgent LangGraph wrap — kitchen-table SYNTHESIS, family-guild ∞Δ∞
