"""LangGraph thin-layer wrap for FamilyComplianceShield (Ladder Level 2).

Family-tier metadata overlay over the executive ``ComplianceAgentGraph``'s
compiled StateGraph. Same Charter V.7 enforcement path; same charter_v7_review
+ compliance_review framework dispatch; family-tier defaults overlaid on the
result dict so downstream gates apply household audit cadence + family-guild
threshold.

Mirrors ``family_compliance_shield/role.py`` (FamilyComplianceShield).
Phase 5 thin-layer wrap; v0.5.0.
"""
from __future__ import annotations

from typing import Any

from platform_layer.plugin_interface import PlugInRequest
from platform_layer.registry import RoleRegistry
from roles.compliance_agent.graph import ComplianceAgentGraph
from roles.family_compliance_shield.role import (
    FAMILY_AUDIT_CADENCE,
    FAMILY_AUDIT_SCOPE,
    FAMILY_GUILD_THRESHOLD_MINIMUM,
)


class FamilyComplianceShieldGraph(ComplianceAgentGraph):
    """LangGraph-wrapped Family Compliance Shield (Series 2 Book 3, Ladder Level 2).

    Inherits Charter V.7 + compliance_review graph from ``ComplianceAgentGraph``.
    Narrows audit scope to household; quarterly self-audit cadence; family-
    guild threshold for cross-generational decisions.
    """

    role_id: str = "family_compliance_shield"
    framework: str = "AUDIT"
    series: str = "family"
    parent_role_id: str = "compliance_agent"
    ladder_level: int = 2  # Family Sovereignty

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
        """Run parent graph, then overlay family-tier compliance metadata."""
        result = super().process(request)
        result["audit_scope"] = self.audit_scope
        result["audit_cadence"] = self.audit_cadence
        result["family_guild_threshold_minimum"] = self.family_guild_threshold_minimum
        result["family_tier"] = True
        result["role_id"] = self.role_id
        result["series"] = self.series
        return result


# Seal: SOURCE — principal_id flows from request through parent graph.
#       TRUTH — same Charter V.7 enforcement as parent; no silent weakening
#               (verified by test_family_graph_does_not_weaken_default_deny).
#       INTEGRITY — parent graph untouched; family-tier metadata additive only.
# ∞Δ∞ FamilyComplianceShield LangGraph wrap — household V.7 + family-guild ∞Δ∞
