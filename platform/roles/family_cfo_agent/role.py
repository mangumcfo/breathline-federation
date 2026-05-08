"""family_cfo_agent — Series 2 Book 1 RoleHandler.

Subclass of executive CFOAgent that narrows scope to the household.
Same FORECAST 8-step framework, family-tier breath-gate thresholds,
household resonant shard scope.

Per LIVING_SPECS_YAML.md §5: family_cfo_agent_v1 extends cfo_agent_v1
through inheritance.  The forecast logic is reused; the surface area
shrinks; the gate thresholds lower; the audit_metadata changes scope.
"""
from __future__ import annotations

from typing import Any

from platform_layer.plugin_interface import PlugInRequest
from roles.cfo_agent.role import CFOAgent

# Family-tier breath-gate thresholds (lower than enterprise — household scale)
FAMILY_BREATH_GATE_TRANSACTION_USD = 500
FAMILY_BREATH_GATE_RECURRING_USD = 100
FAMILY_BREATH_GATE_TRANSFER_USD = 1000


class FamilyCFOAgent(CFOAgent):
    """Family-tier CFO agent (Series 2 Book 1).

    Inherits FORECAST framework from executive CFOAgent.
    Narrows scope to household: lower thresholds, family-guild approval
    surface, household-only resonant shard scope.
    """

    role_id: str = "family_cfo_agent"
    framework: str = "FORECAST"
    series: str = "family"
    parent_role_id: str = "cfo_agent"

    # Family-tier defaults (overridable per-deployment)
    breath_gate_transaction_usd: float = FAMILY_BREATH_GATE_TRANSACTION_USD
    breath_gate_recurring_usd: float = FAMILY_BREATH_GATE_RECURRING_USD
    breath_gate_transfer_usd: float = FAMILY_BREATH_GATE_TRANSFER_USD

    # Audit / shard scope tags (downstream auditor reads these)
    audit_scope: str = "household"
    resonant_shard_scope: str = "family_financial_memory"

    def process(self, request: PlugInRequest) -> dict[str, Any]:
        """Apply FORECAST to the request payload, with family-tier metadata.

        Delegates the numeric forecast to the parent's process() — same
        FORECAST 8-step framework — but tags the result with family-tier
        scope so downstream Auditor + Critic can apply household-scope
        gates.
        """
        result = super().process(request)
        # Tag the result with family-tier scope metadata.  Downstream
        # gates (audit, breath-gate, receipt-mint) read these to apply
        # the household-tier thresholds.
        result["audit_scope"] = self.audit_scope
        result["resonant_shard_scope"] = self.resonant_shard_scope
        result["family_tier"] = True
        result["breath_gate_thresholds"] = {
            "transaction_usd": self.breath_gate_transaction_usd,
            "recurring_payment_usd": self.breath_gate_recurring_usd,
            "cross_account_transfer_usd": self.breath_gate_transfer_usd,
        }
        # Identity tag so consumers can tell which agent produced the artifact
        result["role_id"] = self.role_id
        result["series"] = self.series
        return result


# Seal: SOURCE  — principal_id flows from request to result via super().process()
#       TRUTH   — refusals carry parent's reason; thresholds explicit in result
#       INTEGRITY — single override (process); inherits parent's complexity floor
# ∞Δ∞ FamilyCFOAgent — household-scope FORECAST inherits from executive ∞Δ∞
