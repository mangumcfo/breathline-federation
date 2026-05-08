"""Tests for the FastAPI plug-in interface (`platform_layer.plugin_interface.create_app`).

Verifies that ``POST /invoke`` exercises the full Phase 4 stack
(envelope filter + cost gate + Critic + Auditor + receipt mint) when
the runtime injections are passed to ``create_app``. Uses
``fastapi.testclient.TestClient`` — synchronous, hermetic, no actual
HTTP server.

Skipped when fastapi is not installed (pyproject declares it as a
runtime dep, but tests should not crash on collection in minimal envs).
"""
from __future__ import annotations

import importlib.util
from typing import Any

import pytest

_FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None
pytestmark = pytest.mark.skipif(
    not _FASTAPI_AVAILABLE,
    reason="fastapi not installed; HTTP endpoint tests skipped",
)


if _FASTAPI_AVAILABLE:
    from fastapi.testclient import TestClient

    from kernel.cost_meter import CostCaps, CostMeter
    from platform_layer.permission_spec import ActionClassRegistry
    from platform_layer.plugin_interface import create_app
    from platform_layer.registry import RoleRegistry
    from platform_layer.role_artifact_critic import RoleArtifactCritic
    from roles import create_demo2_handlers, register_demo2_roles


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def action_class_registry(seed_dir):
    return ActionClassRegistry.from_yaml(seed_dir / "action_classes.yaml")


@pytest.fixture
def role_registry(action_class_registry):
    registry = RoleRegistry(action_class_registry)
    register_demo2_roles(registry)
    return registry


@pytest.fixture
def handlers(role_registry):
    return create_demo2_handlers(role_registry)


@pytest.fixture
def cost_meter():
    return CostMeter(caps=CostCaps(
        per_request_usd=1.0, per_role_daily_usd=100.0,
        per_principal_hourly_usd=100.0, session_total_usd=100.0,
    ))


@pytest.fixture
def app(role_registry, handlers, cost_meter):
    """FastAPI app wired with full Phase 4 stack (no real auditor/minter)."""
    return create_app(
        role_registry=role_registry,
        role_handlers=handlers,
        critic=RoleArtifactCritic(),
        cost_meter=cost_meter,
    )


@pytest.fixture
def client(app):
    return TestClient(app)


def _cfo_invoke_body() -> dict[str, Any]:
    return {
        "request_id": "req-http-cfo",
        "role_target": "cfo_agent",
        "action_class": "produce_forecast_artifact",
        "payload": {
            "financial_data": {
                "revenue": [100.0, 105.0, 110.0],
                "expenses": [80.0, 82.0, 84.0],
            },
            "forecast_horizon": 4,
        },
    }


# -----------------------------------------------------------------------------
# Healthz + roles list
# -----------------------------------------------------------------------------
def test_healthz_returns_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_roles_endpoint_requires_principal(client):
    response = client.get("/roles")
    assert response.status_code == 401
    assert "X-Principal-Id" in response.json()["detail"]


def test_roles_endpoint_lists_demo2_roles(client):
    response = client.get("/roles", headers={"X-Principal-Id": "kmangum"})
    assert response.status_code == 200
    body = response.json()
    assert body["principal_id"] == "kmangum"
    assert set(body["available_role_ids"]) == {
        "cfo_agent", "synthesis_agent", "compliance_agent",
    }


# -----------------------------------------------------------------------------
# /invoke happy path through full Phase 4 stack
# -----------------------------------------------------------------------------
def test_invoke_cfo_through_phase4_stack(client):
    response = client.post(
        "/invoke",
        json=_cfo_invoke_body(),
        headers={"X-Principal-Id": "kmangum"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["accepted"] is True
    assert body["role_id"] == "cfo_agent"
    assert body["principal_id"] == "kmangum"
    assert body["critic_verdict"] == "CONFORMS"
    assert body["artifact"]["status"] == "produced"
    assert "forecast_artifact" in body["artifact"]
    # No auditor/receipt_minter wired in this fixture; both stay None
    assert body["audit_cylinder_id"] is None
    assert body["receipt_metadata"] is None


def test_invoke_principal_propagation_via_header(client):
    body = _cfo_invoke_body()
    body["request_id"] = "req-http-principal"
    response = client.post(
        "/invoke",
        json=body,
        headers={"X-Principal-Id": "auditor-007"},
    )
    assert response.status_code == 200
    assert response.json()["principal_id"] == "auditor-007"
    assert response.json()["artifact"]["principal_id"] == "auditor-007"


def test_invoke_requires_principal_header(client):
    response = client.post("/invoke", json=_cfo_invoke_body())
    assert response.status_code == 401


# -----------------------------------------------------------------------------
# /invoke refusal paths (envelope + Critic + cost gate)
# -----------------------------------------------------------------------------
def test_invoke_refuses_unknown_role(client):
    body = _cfo_invoke_body()
    body["role_target"] = "ghost_agent"
    response = client.post(
        "/invoke", json=body, headers={"X-Principal-Id": "kmangum"}
    )
    assert response.status_code == 403
    assert "role_unknown" in response.json()["detail"]


def test_invoke_refuses_charter_v7_forbidden_at_envelope(
    client, action_class_registry
):
    body = _cfo_invoke_body()
    body["action_class"] = next(iter(action_class_registry.charter_v7_forbidden))
    response = client.post(
        "/invoke", json=body, headers={"X-Principal-Id": "kmangum"}
    )
    assert response.status_code == 403
    assert "charter_v7_forbidden_delegation" in response.json()["detail"]


def test_invoke_refuses_on_cost_cap_breach(role_registry, handlers):
    """Tight per-request cap → request refused with 403 cost_ceiling_breach."""
    tight_meter = CostMeter(caps=CostCaps(
        per_request_usd=0.0001,  # below default estimated cost
        per_role_daily_usd=100.0,
        per_principal_hourly_usd=100.0,
        session_total_usd=100.0,
    ))
    app = create_app(
        role_registry=role_registry,
        role_handlers=handlers,
        critic=RoleArtifactCritic(),
        cost_meter=tight_meter,
    )
    client = TestClient(app)
    response = client.post(
        "/invoke", json=_cfo_invoke_body(), headers={"X-Principal-Id": "kmangum"}
    )
    assert response.status_code == 403
    assert "cost_ceiling_breach" in response.json()["detail"]


# ∞Δ∞ HTTP endpoint test seal — Phase 5 Priority 3 ∞Δ∞
