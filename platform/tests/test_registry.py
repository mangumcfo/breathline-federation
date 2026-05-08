"""Tests for the platform-layer Role Registry."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from platform_layer.permission_spec import ActionClassRegistry, PermissionSpecViolation
from platform_layer.registry import RoleRegistry


@pytest.fixture
def action_class_registry(seed_dir: Path) -> ActionClassRegistry:
    return ActionClassRegistry.from_yaml(seed_dir / "action_classes.yaml")


@pytest.fixture
def role_registry(action_class_registry: ActionClassRegistry) -> RoleRegistry:
    return RoleRegistry(action_class_registry)


def _write_role(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / f"{name}_role_spec.yaml"
    p.write_text(textwrap.dedent(content))
    return p


def test_role_registry_register_loads_and_validates(
    tmp_path: Path, role_registry: RoleRegistry
) -> None:
    spec_path = _write_role(
        tmp_path,
        "cfo",
        """\
        role: cfo_agent
        version: "0.1"
        allowed_action_classes:
          - read_structured_financial_data
          - produce_forecast_artifact
        """,
    )
    registered = role_registry.register_from_yaml(spec_path)
    assert registered.role_id == "cfo_agent"
    assert role_registry.has("cfo_agent")


def test_role_registry_default_deny_on_unknown_lookup(role_registry: RoleRegistry) -> None:
    with pytest.raises(KeyError, match="Default-deny"):
        role_registry.get("nonexistent_role")


def test_role_registry_refuses_charter_v7_violating_spec(
    tmp_path: Path, role_registry: RoleRegistry
) -> None:
    bad_spec = _write_role(
        tmp_path,
        "rogue",
        """\
        role: rogue_agent
        version: "0.1"
        allowed_action_classes:
          - personnel_decision   # Charter V.7 forbidden
        """,
    )
    with pytest.raises(PermissionSpecViolation, match="Charter V.7 forbidden"):
        role_registry.register_from_yaml(bad_spec)
    assert not role_registry.has("rogue_agent")


def test_role_registry_is_append_only(tmp_path: Path, role_registry: RoleRegistry) -> None:
    spec_path = _write_role(
        tmp_path,
        "cfo",
        """\
        role: cfo_agent
        version: "0.1"
        allowed_action_classes:
          - read_spec
        """,
    )
    role_registry.register_from_yaml(spec_path)
    # Try to re-register the same role
    with pytest.raises(ValueError, match="already registered"):
        role_registry.register_from_yaml(spec_path)


def test_role_registry_records_audit_state(
    tmp_path: Path, role_registry: RoleRegistry
) -> None:
    """For Appendix E.3.1 Least-Authority Report — each role tracks its
    last-sealed cylinder state."""
    spec_path = _write_role(
        tmp_path,
        "cfo",
        """\
        role: cfo_agent
        version: "0.1"
        allowed_action_classes:
          - read_spec
        """,
    )
    registered = role_registry.register_from_yaml(spec_path)
    assert registered.last_audit_seq is None
    registered.record_audit(sequence=140)
    assert registered.last_audit_seq == 140
    assert registered.last_audit_at is not None


def test_role_registry_all_returns_all_registered(
    tmp_path: Path, role_registry: RoleRegistry
) -> None:
    """For Compliance Review workflow — must enumerate every role."""
    for name in ["cfo_agent", "synthesis_agent", "compliance_agent"]:
        spec_path = _write_role(
            tmp_path,
            name,
            f"""\
            role: {name}
            version: "0.1"
            allowed_action_classes:
              - read_spec
            """,
        )
        role_registry.register_from_yaml(spec_path)
    all_roles = role_registry.all()
    assert len(all_roles) == 3
    role_ids = {r.role_id for r in all_roles}
    assert role_ids == {"cfo_agent", "synthesis_agent", "compliance_agent"}
