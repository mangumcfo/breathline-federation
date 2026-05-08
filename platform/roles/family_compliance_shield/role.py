"""family_compliance_shield — Series 2 Book 3 RoleHandler.

Subclass of executive ComplianceAgent that narrows scope to the household.
Same Charter V.7 enforcement; same charter_v7_review + compliance_review
framework dispatch; family-tier defaults overlaid.
"""
from __future__ import annotations

from typing import Any

from platform_layer.plugin_interface import PlugInRequest
from platform_layer.registry import RoleRegistry
from roles.compliance_agent.role import ComplianceAgent

# Family-tier audit cadence + thresholds
FAMILY_AUDIT_CADENCE = "quarterly"
FAMILY_GUILD_THRESHOLD_MINIMUM = 2  # adult family members for cross-gen decisions
FAMILY_AUDIT_SCOPE = "household"


class FamilyComplianceShield(ComplianceAgent):
    """Family-tier Compliance Shield (Series 2 Book 3).

    Inherits Charter V.7 + compliance_review frameworks from
    ComplianceAgent.  Narrows audit scope to household; quarterly
    self-audit cadence; family-guild threshold for cross-generational
    decisions.
    """

    role_id: str = "family_compliance_shield"
    framework: str = "AUDIT"
    series: str = "family"
    parent_role_id: str = "compliance_agent"

    audit_scope: str = FAMILY_AUDIT_SCOPE
    audit_cadence: str = FAMILY_AUDIT_CADENCE
    family_guild_threshold_minimum: int = FAMILY_GUILD_THRESHOLD_MINIMUM

    def __init__(
        self,
        role_registry: RoleRegistry,
        auditor: Any | None = None,
        receipt_minter: Any | None = None,
    ) -> None:
        super().__init__(
            role_registry=role_registry,
            auditor=auditor,
            receipt_minter=receipt_minter,
        )

    def process(self, request: PlugInRequest) -> dict[str, Any]:
        """Apply household-scope compliance review.

        Delegates to parent's process() for the actual review logic, then
        tags the result with family-tier metadata.
        """
        result = super().process(request)
        result["audit_scope"] = self.audit_scope
        result["audit_cadence"] = self.audit_cadence
        result["family_guild_threshold_minimum"] = self.family_guild_threshold_minimum
        result["family_tier"] = True
        result["role_id"] = self.role_id
        result["series"] = self.series
        return result


# Seal: SOURCE — principal_id flows from request via super().process()
#       TRUTH — same Charter V.7 enforcement as parent; no silent weakening
#       INTEGRITY — single override; family-tier metadata additive only
# ∞Δ∞ FamilyComplianceShield — household-scope V.7 + family-guild ∞Δ∞
