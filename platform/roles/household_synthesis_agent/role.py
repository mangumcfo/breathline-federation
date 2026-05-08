"""household_synthesis_agent — Series 2 Book 2 RoleHandler.

Subclass of executive SynthesisAgent that narrows scope to household
decisions.  Same SYNTHESIS framework; lower recursion depths; family-
scope peer allowlist; weekly household brief output format.
"""
from __future__ import annotations

from typing import Any

from platform_layer.plugin_interface import PlugInRequest
from roles.synthesis_agent.role import SynthesisAgent

# Family-tier recursion + breath-gate defaults
HOUSEHOLD_RECURSION_DEPTH_DEFAULT = 2
HOUSEHOLD_RECURSION_DEPTH_MAX = 3
HOUSEHOLD_BREATH_GATE_AT_DEPTH = 2


class HouseholdSynthesisAgent(SynthesisAgent):
    """Household-scope orchestrator (Series 2 Book 2).

    Inherits SYNTHESIS framework from enterprise SynthesisAgent.
    Narrows: lower recursion depths, family-scope peer roles only.
    """

    role_id: str = "household_synthesis_agent"
    framework: str = "SYNTHESIS"
    series: str = "family"
    parent_role_id: str = "synthesis_agent"

    recursion_depth_default: int = HOUSEHOLD_RECURSION_DEPTH_DEFAULT
    recursion_depth_max: int = HOUSEHOLD_RECURSION_DEPTH_MAX
    breath_gate_at_depth: int = HOUSEHOLD_BREATH_GATE_AT_DEPTH

    def __init__(self, peer_handlers: dict[str, Any]) -> None:
        super().__init__(peer_handlers=peer_handlers)

    def process(self, request: PlugInRequest) -> dict[str, Any]:
        """Orchestrate household peers and produce a household brief.

        Delegates to parent's SYNTHESIS framework, then tags the result
        with household-tier metadata so downstream gates can apply
        family-tier breath-gate thresholds.
        """
        result = super().process(request)
        result["audit_scope"] = "household"
        result["recursion_depth_default"] = self.recursion_depth_default
        result["recursion_depth_max"] = self.recursion_depth_max
        result["breath_gate_at_depth"] = self.breath_gate_at_depth
        result["family_tier"] = True
        result["role_id"] = self.role_id
        result["series"] = self.series
        return result


# Seal: SOURCE — peer_handlers reference held; principal_id flows via parent
#       TRUTH — same orchestration logic as enterprise; thresholds explicit
#       INTEGRITY — single override; family-tier metadata additive only
# ∞Δ∞ HouseholdSynthesisAgent — kitchen-table SYNTHESIS, family-guild ∞Δ∞
