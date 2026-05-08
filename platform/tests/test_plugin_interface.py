"""Tests for the plug-in interface — least-authority filtering at the layer."""
from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

import pytest

from platform_layer.permission_spec import ActionClassRegistry
from platform_layer.plugin_interface import (
    PlugInRequest,
    route_request,
)
from platform_layer.registry import RoleRegistry


@pytest.fixture
def action_class_registry(seed_dir: Path) -> ActionClassRegistry:
    return ActionClassRegistry.from_yaml(seed_dir / "action_classes.yaml")


@pytest.fixture
def role_registry(
    tmp_path: Path,
    action_class_registry: ActionClassRegistry,
) -> RoleRegistry:
    """Register a CFO-like role for testing."""
    registry = RoleRegistry(action_class_registry)
    cfo_path = tmp_path / "cfo_role_spec.yaml"
    cfo_path.write_text(
        textwrap.dedent(
            """\
            role: cfo_agent
            version: "0.1"
            allowed_action_classes:
              - read_structured_financial_data
              - produce_forecast_artifact
              - generate_scenarios
              - cite_assumptions
              - flag_uncertainty
            """
        )
    )
    registry.register_from_yaml(cfo_path)
    return registry


# -----------------------------------------------------------------------------
# Default-deny on unknown role
# -----------------------------------------------------------------------------
def test_route_request_refuses_unknown_role(role_registry: RoleRegistry) -> None:
    request = PlugInRequest(
        request_id="req-001",
        principal_id="kmangum",
        role_target="nonexistent_role",
        action_class="read_spec",
    )
    response = route_request(request, role_registry)
    assert response.accepted is False
    assert "role_unknown" in (response.refusal_reason or "")


# -----------------------------------------------------------------------------
# Charter V.7 forbidden delegation refused at the layer
# -----------------------------------------------------------------------------
def test_route_request_refuses_charter_v7_forbidden(role_registry: RoleRegistry) -> None:
    """Per Section 6.2: the role never sees a request that violates Charter V.7."""
    request = PlugInRequest(
        request_id="req-002",
        principal_id="kmangum",
        role_target="cfo_agent",
        action_class="external_commitment",  # Charter V.7 forbidden
    )
    response = route_request(request, role_registry)
    assert response.accepted is False
    assert "charter_v7_forbidden_delegation" in (response.refusal_reason or "")


# -----------------------------------------------------------------------------
# Action class outside the role's envelope
# -----------------------------------------------------------------------------
def test_route_request_refuses_outside_envelope(role_registry: RoleRegistry) -> None:
    """Action class is in the vocabulary but not in this role's envelope."""
    request = PlugInRequest(
        request_id="req-003",
        principal_id="kmangum",
        role_target="cfo_agent",
        action_class="review_peer_outputs",  # Compliance-agent envelope, not CFO
    )
    response = route_request(request, role_registry)
    assert response.accepted is False
    assert "action_class_outside_envelope" in (response.refusal_reason or "")


# -----------------------------------------------------------------------------
# Default-deny on unknown action class
# -----------------------------------------------------------------------------
def test_route_request_refuses_unknown_action_class(role_registry: RoleRegistry) -> None:
    request = PlugInRequest(
        request_id="req-004",
        principal_id="kmangum",
        role_target="cfo_agent",
        action_class="entirely_invented_class",
    )
    response = route_request(request, role_registry)
    assert response.accepted is False
    assert "action_class_unknown" in (response.refusal_reason or "")


# -----------------------------------------------------------------------------
# Allowed request reaches the role handler
# -----------------------------------------------------------------------------
def test_route_request_accepts_allowed_request(role_registry: RoleRegistry) -> None:
    """When all checks pass, the request reaches the role (or stub)."""
    request = PlugInRequest(
        request_id="req-005",
        principal_id="kmangum",
        role_target="cfo_agent",
        action_class="produce_forecast_artifact",
    )
    response = route_request(request, role_registry)
    assert response.accepted is True
    assert response.refusal_reason is None
    assert response.role_id == "cfo_agent"


def test_route_request_invokes_role_handler_when_provided(
    role_registry: RoleRegistry,
) -> None:
    """When a role handler is registered, it processes the accepted request."""

    class StubHandler:
        def process(self, request: PlugInRequest) -> dict[str, Any]:
            return {
                "stub": True,
                "saw_action": request.action_class,
                "principal_id": request.principal_id,
            }

    handlers = {"cfo_agent": StubHandler()}
    request = PlugInRequest(
        request_id="req-006",
        principal_id="kmangum",
        role_target="cfo_agent",
        action_class="produce_forecast_artifact",
    )
    response = route_request(request, role_registry, role_handlers=handlers)
    assert response.accepted is True
    assert response.artifact == {
        "stub": True,
        "saw_action": "produce_forecast_artifact",
        "principal_id": "kmangum",
    }


# -----------------------------------------------------------------------------
# Frame-of-reference attack: refused at the layer, role never invoked
# -----------------------------------------------------------------------------
def test_role_handler_never_invoked_on_refused_request(
    role_registry: RoleRegistry,
) -> None:
    """Critical security property: a refused request never invokes the role.

    This is the structural defense against the frame-of-reference attack
    documented in 08_RISKS_AND_LIMITS.md. Even if the natural-language
    framing is creative, the classifier returns a forbidden class and
    refusal happens at the envelope layer.
    """
    invocations: list[Any] = []

    class TrackingHandler:
        def process(self, request: PlugInRequest) -> dict[str, Any]:
            invocations.append(request)
            return {"should_never_be_seen": True}

    handlers = {"cfo_agent": TrackingHandler()}
    # Try multiple attack-style framings — all classified to forbidden classes
    for action_class in [
        "external_commitment",
        "personnel_decision",
        "irreversible_action",
        "charter_modification",
    ]:
        request = PlugInRequest(
            request_id=f"req-attack-{action_class}",
            principal_id="kmangum",
            role_target="cfo_agent",
            action_class=action_class,
        )
        response = route_request(request, role_registry, role_handlers=handlers)
        assert response.accepted is False
        assert "charter_v7_forbidden_delegation" in (response.refusal_reason or "")

    # The role handler must never have been invoked
    assert invocations == []


# -----------------------------------------------------------------------------
# principal_id propagation (Constitution@A1 §1)
# -----------------------------------------------------------------------------
def test_principal_id_propagates_to_role(role_registry: RoleRegistry) -> None:
    """principal_id flows from request → role per Constitution@A1 §1."""
    captured: list[str] = []

    class CaptureHandler:
        def process(self, request: PlugInRequest) -> dict[str, Any]:
            captured.append(request.principal_id)
            return {}

    handlers = {"cfo_agent": CaptureHandler()}
    request = PlugInRequest(
        request_id="req-007",
        principal_id="alice@example.com",  # different principal
        role_target="cfo_agent",
        action_class="read_structured_financial_data",
    )
    response = route_request(request, role_registry, role_handlers=handlers)
    assert response.accepted is True
    assert response.principal_id == "alice@example.com"
    assert captured == ["alice@example.com"]
