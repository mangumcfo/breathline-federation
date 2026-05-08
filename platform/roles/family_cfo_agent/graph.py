"""LangGraph thin-layer wrap for FamilyCFOAgent (Ladder Level 2 — Family Sovereignty).

Family-tier metadata overlay over the executive ``CFOAgentGraph``'s compiled
StateGraph. The deterministic FORECAST core is UNCHANGED; the parent graph
runs unaltered; this subclass only re-tags the result dict with household
audit_scope, family_tier=True, and family-tier breath-gate thresholds — so
downstream Auditor + Critic apply household-tier gates.

Mirrors the pattern in ``family_cfo_agent/role.py`` (FamilyCFOAgent), which
likewise overlays metadata on ``super().process()``. Phase 5 thin-layer wrap;
v0.5.0.
"""
from __future__ import annotations

from typing import Any

from platform_layer.plugin_interface import PlugInRequest
from roles.cfo_agent.graph import CFOAgentGraph
from roles.family_cfo_agent.role import (
    FAMILY_BREATH_GATE_RECURRING_USD,
    FAMILY_BREATH_GATE_TRANSACTION_USD,
    FAMILY_BREATH_GATE_TRANSFER_USD,
)


class FamilyCFOAgentGraph(CFOAgentGraph):
    """LangGraph-wrapped Family CFO agent (Series 2 Book 1, Ladder Level 2).

    Inherits FORECAST graph from ``CFOAgentGraph``. Narrows scope to
    household: lower thresholds, family-guild approval surface,
    household-only resonant shard scope.
    """

    role_id: str = "family_cfo_agent"
    framework: str = "FORECAST"
    series: str = "family"
    parent_role_id: str = "cfo_agent"
    ladder_level: int = 2  # Family Sovereignty

    # Family-tier defaults (mirror role.py for parity with pure-Python class)
    breath_gate_transaction_usd: float = FAMILY_BREATH_GATE_TRANSACTION_USD
    breath_gate_recurring_usd: float = FAMILY_BREATH_GATE_RECURRING_USD
    breath_gate_transfer_usd: float = FAMILY_BREATH_GATE_TRANSFER_USD

    audit_scope: str = "household"
    resonant_shard_scope: str = "family_financial_memory"

    def process(self, request: PlugInRequest) -> dict[str, Any]:
        """Run parent graph, then overlay family-tier metadata.

        Same delegation pattern as ``FamilyCFOAgent.process()`` — the
        parent's StateGraph runs unaltered; this method only re-tags the
        result dict so downstream gates can apply household thresholds.
        """
        result = super().process(request)
        result["audit_scope"] = self.audit_scope
        result["resonant_shard_scope"] = self.resonant_shard_scope
        result["family_tier"] = True
        result["breath_gate_thresholds"] = {
            "transaction_usd": self.breath_gate_transaction_usd,
            "recurring_payment_usd": self.breath_gate_recurring_usd,
            "cross_account_transfer_usd": self.breath_gate_transfer_usd,
        }
        result["role_id"] = self.role_id
        result["series"] = self.series
        return result


# Seal: SOURCE — principal_id flows from request through parent graph unchanged.
#       TRUTH — refusals carry parent's reason; thresholds explicit in result.
#       INTEGRITY — parent graph untouched; metadata overlay additive only;
#                   K1-K4 invariants preserved (verified by parity tests).
# ∞Δ∞ FamilyCFOAgent LangGraph wrap — household-scope thin layer, Ladder Level 2 ∞Δ∞
