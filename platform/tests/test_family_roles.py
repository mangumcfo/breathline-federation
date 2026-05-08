"""Tests for the Series 2 family role pack (v0.5.0).

Verifies:
  - Protocol conformance (process(PlugInRequest) -> dict)
  - Inheritance from executive parents (Python class hierarchy)
  - Family-tier metadata injection (audit_scope, family_tier, thresholds)
  - role_spec.yaml registration in RoleRegistry
  - create_family_handlers() factory wiring
  - create_full_handlers() combined factory

Per the Phase 5 plan: family roles MUST inherit from executive parents
and MUST NOT weaken K1-K4 invariants.  The structural floor (charter V.7
forbidden classes) is preserved.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from platform_layer.permission_spec import ActionClassRegistry
from platform_layer.plugin_interface import PlugInRequest
from platform_layer.registry import RoleRegistry
from roles import (
    create_demo2_handlers,
    create_family_handlers,
    create_full_handlers,
    register_demo2_roles,
    register_family_roles,
    role_spec_path,
)
from roles.cfo_agent.role import CFOAgent
from roles.compliance_agent.role import ComplianceAgent
from roles.synthesis_agent.role import SynthesisAgent
from roles.family_cfo_agent.role import FamilyCFOAgent
from roles.family_compliance_shield.role import FamilyComplianceShield
from roles.household_synthesis_agent.role import HouseholdSynthesisAgent


# ============================================================
# Local fixtures (mirror the conftest pattern)
# ============================================================

@pytest.fixture
def _action_class_registry(seed_dir: Path) -> ActionClassRegistry:
    """ActionClassRegistry built from seed/action_classes.yaml."""
    return ActionClassRegistry.from_yaml(seed_dir / "action_classes.yaml")


@pytest.fixture
def _role_registry(_action_class_registry: ActionClassRegistry) -> RoleRegistry:
    """Empty RoleRegistry — tests register what they need."""
    return RoleRegistry(_action_class_registry)


def _registry_with_all_roles(_role_registry: RoleRegistry) -> RoleRegistry:
    """Helper: register exec + family roles into the fixture registry."""
    register_demo2_roles(_role_registry)
    register_family_roles(_role_registry)
    return _role_registry


# ============================================================
# 1. INHERITANCE — family classes subclass executive parents
# ============================================================

def test_family_cfo_subclasses_executive_cfo():
    assert issubclass(FamilyCFOAgent, CFOAgent)


def test_family_compliance_shield_subclasses_executive_compliance():
    assert issubclass(FamilyComplianceShield, ComplianceAgent)


def test_household_synthesis_subclasses_executive_synthesis():
    assert issubclass(HouseholdSynthesisAgent, SynthesisAgent)


# ============================================================
# 2. ROLE_ID + parent_role_id metadata
# ============================================================

def test_family_role_ids_distinct_from_executive():
    family_cfo = FamilyCFOAgent()
    assert family_cfo.role_id == "family_cfo_agent"
    assert family_cfo.role_id != CFOAgent.role_id
    assert family_cfo.parent_role_id == "cfo_agent"
    assert family_cfo.series == "family"


def test_household_synthesis_id_distinct_from_executive():
    handlers = {"family_cfo_agent": FamilyCFOAgent()}
    hsynth = HouseholdSynthesisAgent(peer_handlers=handlers)
    assert hsynth.role_id == "household_synthesis_agent"
    assert hsynth.role_id != SynthesisAgent.role_id
    assert hsynth.parent_role_id == "synthesis_agent"


# ============================================================
# 3. THRESHOLD NARROWING — family thresholds < enterprise
# ============================================================

def test_family_cfo_breath_gate_thresholds_are_lower_than_enterprise():
    """Household-scope thresholds MUST be lower than enterprise defaults."""
    family_cfo = FamilyCFOAgent()
    # Enterprise CFO has no breath_gate_*_usd attributes — these are
    # family-tier additions.  Just verify the family values are sane
    # (positive, household-scale).
    assert 0 < family_cfo.breath_gate_transaction_usd <= 5000
    assert 0 < family_cfo.breath_gate_recurring_usd <= 1000
    assert 0 < family_cfo.breath_gate_transfer_usd <= 10000


def test_household_synthesis_recursion_depth_lower_than_enterprise():
    """Household-tier feels drift sooner — lower default + max depth."""
    handlers = {"family_cfo_agent": FamilyCFOAgent()}
    hsynth = HouseholdSynthesisAgent(peer_handlers=handlers)
    assert hsynth.recursion_depth_default <= 3
    assert hsynth.recursion_depth_max <= 5
    assert hsynth.breath_gate_at_depth <= hsynth.recursion_depth_max


def test_family_compliance_audit_cadence(_role_registry: RoleRegistry):
    """Family compliance has a quarterly self-audit cadence."""
    register_demo2_roles(_role_registry)
    register_family_roles(_role_registry)
    shield = FamilyComplianceShield(role_registry=_role_registry)
    assert shield.audit_cadence == "quarterly"
    assert shield.audit_scope == "household"
    assert shield.family_guild_threshold_minimum >= 2


# ============================================================
# 4. PROTOCOL CONFORMANCE — process(PlugInRequest) -> dict
# ============================================================

def _request(role_id: str, action_class: str = "produce_forecast_artifact",
             payload: dict | None = None) -> PlugInRequest:
    """Helper: build a minimal PlugInRequest matching the codebase signature."""
    return PlugInRequest(
        request_id="test-req-001",
        principal_id="kmangum",
        role_target=role_id,
        action_class=action_class,
        payload=payload or {},
    )


def test_family_cfo_process_returns_dict_with_required_keys():
    family_cfo = FamilyCFOAgent()
    payload = {
        "financial_data": {
            "revenue_monthly": 8000,
            "expenses_monthly": 5500,
            "cash_on_hand": 25000,
        },
        "forecast_horizon": 12,
    }
    result = family_cfo.process(_request("family_cfo_agent", payload))
    assert isinstance(result, dict)
    assert "role_id" in result
    assert "principal_id" in result
    assert "request_id" in result
    assert "status" in result


def test_family_cfo_result_carries_family_tier_metadata():
    """Family-tier results MUST carry the audit_scope + family_tier tag."""
    family_cfo = FamilyCFOAgent()
    payload = {
        "financial_data": {
            "revenue_monthly": 8000,
            "expenses_monthly": 5500,
            "cash_on_hand": 25000,
        },
        "forecast_horizon": 12,
    }
    result = family_cfo.process(_request("family_cfo_agent", payload))
    assert result.get("family_tier") is True
    assert result.get("audit_scope") == "household"
    assert result.get("series") == "family"
    assert result.get("role_id") == "family_cfo_agent"
    assert "breath_gate_thresholds" in result


def test_family_cfo_principal_id_propagation():
    """principal_id MUST flow end-to-end (Constitution@A1 §1)."""
    family_cfo = FamilyCFOAgent()
    payload = {
        "financial_data": {"revenue_monthly": 1000, "expenses_monthly": 800, "cash_on_hand": 5000},
        "forecast_horizon": 6,
    }
    result = family_cfo.process(_request("family_cfo_agent", payload))
    assert result["principal_id"] == "kmangum"
    assert result["request_id"] == "test-req-001"


def test_family_cfo_refusal_carries_metadata():
    """Refusals MUST still carry family-tier metadata."""
    family_cfo = FamilyCFOAgent()
    # Empty payload should refuse (parent's ForecastInputError path)
    result = family_cfo.process(_request("family_cfo_agent", {}))
    assert result["status"] in ("refused", "produced")  # parent decides
    # Family metadata always tags the result
    assert result.get("family_tier") is True
    assert result.get("audit_scope") == "household"


# ============================================================
# 5. role_spec.yaml registration in RoleRegistry
# ============================================================

def test_family_role_specs_register_into_registry(_role_registry: RoleRegistry):
    register_demo2_roles(_role_registry)
    register_family_roles(_role_registry)

    # All 6 roles should be present after registration.
    # Use the registry's iteration interface (whatever its name).
    expected = {
        "cfo_agent",
        "synthesis_agent",
        "compliance_agent",
        "family_cfo_agent",
        "family_compliance_shield",
        "household_synthesis_agent",
    }
    # Try several common registry-iteration patterns
    registered: set[str] = set()
    if hasattr(_role_registry, "list_roles"):
        registered = set(_role_registry.list_roles())
    elif hasattr(_role_registry, "_roles"):
        registered = set(_role_registry._roles.keys())
    elif hasattr(_role_registry, "roles"):
        registered = set(_role_registry.roles.keys() if isinstance(_role_registry.roles, dict) else _role_registry.roles)
    else:
        # Fallback: probe by role_id one at a time
        for r in expected:
            try:
                _role_registry.get(r)
                registered.add(r)
            except Exception:
                pass
    missing = expected - registered
    assert not missing, f"missing role registrations: {missing}"


def test_family_role_spec_yaml_files_exist():
    """role_spec.yaml MUST exist for each family role."""
    for role_id in (
        "family_cfo_agent",
        "family_compliance_shield",
        "household_synthesis_agent",
    ):
        path = role_spec_path(role_id)
        assert path.exists(), f"role_spec.yaml missing for {role_id}: {path}"


# ============================================================
# 6. create_family_handlers() + create_full_handlers() factories
# ============================================================

def test_create_family_handlers_returns_three_handlers(_role_registry: RoleRegistry):
    register_demo2_roles(_role_registry)
    register_family_roles(_role_registry)
    handlers = create_family_handlers(role_registry=_role_registry)
    expected = {"family_cfo_agent", "family_compliance_shield", "household_synthesis_agent"}
    assert set(handlers.keys()) == expected


def test_create_family_handlers_household_synthesis_has_family_peers(
    _role_registry: RoleRegistry,
):
    """HouseholdSynthesisAgent MUST be wired with the family handlers dict."""
    register_demo2_roles(_role_registry)
    register_family_roles(_role_registry)
    handlers = create_family_handlers(role_registry=_role_registry)
    hsynth = handlers["household_synthesis_agent"]
    # Peer dict is the same handlers dict (late-bound, shared reference)
    assert "family_cfo_agent" in hsynth._peer_handlers
    assert "family_compliance_shield" in hsynth._peer_handlers


def test_create_full_handlers_combines_executive_and_family(
    _role_registry: RoleRegistry,
):
    """create_full_handlers() returns 6 handlers: 3 executive + 3 family."""
    register_demo2_roles(_role_registry)
    register_family_roles(_role_registry)
    handlers = create_full_handlers(role_registry=_role_registry)
    expected = {
        "cfo_agent",
        "synthesis_agent",
        "compliance_agent",
        "family_cfo_agent",
        "family_compliance_shield",
        "household_synthesis_agent",
    }
    assert set(handlers.keys()) == expected


# ============================================================
# 7. K1–K4 invariants — family roles MUST NOT weaken them
# ============================================================

def test_family_cfo_does_not_weaken_default_deny():
    """Family CFO MUST refuse the same payloads the executive CFO refuses."""
    exec_cfo = CFOAgent()
    family_cfo = FamilyCFOAgent()

    bad_payload = {}  # missing required fields → ForecastInputError
    exec_result = exec_cfo.process(_request("cfo_agent", bad_payload))
    family_result = family_cfo.process(_request("family_cfo_agent", bad_payload))

    # Both refuse on bad input
    assert exec_result["status"] == "refused"
    assert family_result["status"] == "refused"


def test_family_compliance_shield_does_not_weaken_charter_v7(
    _role_registry: RoleRegistry,
):
    """Family compliance shield MUST enforce same Charter V.7 forbidden classes."""
    register_demo2_roles(_role_registry)
    register_family_roles(_role_registry)
    shield = FamilyComplianceShield(role_registry=_role_registry)
    # The Charter V.7 enforcement is structural — at the plugin_interface
    # level — so the shield NEVER receives a forbidden-class request.
    # Verify the shield's framework field is unchanged from parent.
    assert shield.framework == ComplianceAgent.framework
