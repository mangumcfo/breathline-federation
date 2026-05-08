"""Tests for Charter V.7 enforcement via Permission Spec at the plug-in interface."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from platform_layer.permission_spec import (
    ActionClassRegistry,
    ActionClassForbidden,
    ActionClassOutsideEnvelope,
    ActionClassUnknown,
    PermissionSpec,
    PermissionSpecViolation,
)


@pytest.fixture
def action_class_registry(seed_dir: Path) -> ActionClassRegistry:
    return ActionClassRegistry.from_yaml(seed_dir / "action_classes.yaml")


def _write_role_spec(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "role_spec.yaml"
    p.write_text(textwrap.dedent(content))
    return p


# -----------------------------------------------------------------------------
# ActionClassRegistry
# -----------------------------------------------------------------------------
def test_action_class_registry_loads_charter_v7_forbidden(
    action_class_registry: ActionClassRegistry,
) -> None:
    """Charter V.7 forbidden classes load and are non-empty."""
    assert "external_commitment" in action_class_registry.charter_v7_forbidden
    assert "personnel_decision" in action_class_registry.charter_v7_forbidden
    assert "irreversible_action" in action_class_registry.charter_v7_forbidden
    assert "charter_modification" in action_class_registry.charter_v7_forbidden
    assert "judgment_over_humans" in action_class_registry.charter_v7_forbidden


def test_action_class_registry_loads_allowed_classes(
    action_class_registry: ActionClassRegistry,
) -> None:
    assert "read_spec" in action_class_registry.allowed
    assert "produce_forecast_artifact" in action_class_registry.allowed
    assert "review_peer_outputs" in action_class_registry.allowed


def test_action_class_registry_marks_always_available(
    action_class_registry: ActionClassRegistry,
) -> None:
    """write_audit_entry and request_breath_confirmation should be always_available."""
    assert action_class_registry.is_always_available("write_audit_entry")
    assert action_class_registry.is_always_available("request_breath_confirmation")
    assert not action_class_registry.is_always_available("produce_forecast_artifact")


# -----------------------------------------------------------------------------
# Charter V.7 enforcement at PermissionSpec construction
# -----------------------------------------------------------------------------
def test_permission_spec_refuses_to_allow_charter_v7_forbidden(
    tmp_path: Path,
    action_class_registry: ActionClassRegistry,
) -> None:
    """A role spec attempting to allow a Charter V.7 forbidden class must raise."""
    spec_path = _write_role_spec(
        tmp_path,
        """\
        role: rogue_agent
        version: "0.1"
        allowed_action_classes:
          - external_commitment   # Charter V.7 forbidden
          - read_spec
        """,
    )
    with pytest.raises(PermissionSpecViolation, match="Charter V.7 forbidden"):
        PermissionSpec.from_yaml(spec_path, action_class_registry)


def test_permission_spec_refuses_unknown_action_class(
    tmp_path: Path,
    action_class_registry: ActionClassRegistry,
) -> None:
    """A role spec with an action class not in the controlled vocabulary must raise."""
    spec_path = _write_role_spec(
        tmp_path,
        """\
        role: cfo_agent
        version: "0.1"
        allowed_action_classes:
          - hypothetical_invented_class
        """,
    )
    with pytest.raises(PermissionSpecViolation, match="unknown action classes"):
        PermissionSpec.from_yaml(spec_path, action_class_registry)


def test_permission_spec_merges_charter_v7_into_forbidden(
    tmp_path: Path,
    action_class_registry: ActionClassRegistry,
) -> None:
    """Charter V.7 classes appear in the role's forbidden_action_classes regardless of spec."""
    spec_path = _write_role_spec(
        tmp_path,
        """\
        role: cfo_agent
        version: "0.1"
        allowed_action_classes:
          - read_structured_financial_data
          - produce_forecast_artifact
        # Note: no explicit forbidden_action_classes; Charter V.7 still inherits
        """,
    )
    spec = PermissionSpec.from_yaml(spec_path, action_class_registry)
    for forbidden in action_class_registry.charter_v7_forbidden:
        assert forbidden in spec.forbidden_action_classes


# -----------------------------------------------------------------------------
# PermissionSpec.check — runtime envelope filter
# -----------------------------------------------------------------------------
@pytest.fixture
def cfo_spec(tmp_path: Path, action_class_registry: ActionClassRegistry) -> PermissionSpec:
    spec_path = _write_role_spec(
        tmp_path,
        """\
        role: cfo_agent
        version: "0.1"
        allowed_action_classes:
          - read_structured_financial_data
          - produce_forecast_artifact
          - generate_scenarios
          - cite_assumptions
          - flag_uncertainty
        invocation_envelope:
          inputs_required:
            - financial_data_uri
            - forecast_horizon
        """,
    )
    return PermissionSpec.from_yaml(spec_path, action_class_registry)


def test_check_passes_for_allowed_class(
    cfo_spec: PermissionSpec, action_class_registry: ActionClassRegistry
) -> None:
    cfo_spec.check("produce_forecast_artifact", action_class_registry)  # no exception


def test_check_refuses_charter_v7_forbidden(
    cfo_spec: PermissionSpec, action_class_registry: ActionClassRegistry
) -> None:
    with pytest.raises(ActionClassForbidden, match="forbidden"):
        cfo_spec.check("external_commitment", action_class_registry)


def test_check_refuses_outside_envelope(
    cfo_spec: PermissionSpec, action_class_registry: ActionClassRegistry
) -> None:
    """An action class that is in the vocabulary but not in this role's envelope must refuse."""
    with pytest.raises(ActionClassOutsideEnvelope, match="outside role"):
        cfo_spec.check("review_peer_outputs", action_class_registry)


def test_check_refuses_unknown_class(
    cfo_spec: PermissionSpec, action_class_registry: ActionClassRegistry
) -> None:
    with pytest.raises(ActionClassUnknown, match="not in controlled vocabulary"):
        cfo_spec.check("totally_invented_class", action_class_registry)


def test_check_passes_always_available_classes(
    cfo_spec: PermissionSpec, action_class_registry: ActionClassRegistry
) -> None:
    """write_audit_entry and request_breath_confirmation bypass the envelope filter."""
    cfo_spec.check("write_audit_entry", action_class_registry)
    cfo_spec.check("request_breath_confirmation", action_class_registry)


# -----------------------------------------------------------------------------
# Frame-of-reference attack vector
# -----------------------------------------------------------------------------
def test_frame_of_reference_attack_is_refused_at_envelope_layer(
    cfo_spec: PermissionSpec, action_class_registry: ActionClassRegistry
) -> None:
    """Per IMPLEMENTATION_PLAN.md Section 6.2:
        'The role never sees a request it is not permitted to fulfill.'

    A request creatively framed to invoke a forbidden class still gets
    classified into that class and refused at the envelope layer — the
    role's prompt is never reached.
    """
    # Suppose a request was classified into 'personnel_decision' regardless of
    # how the natural-language framing tried to disguise it.
    with pytest.raises(ActionClassForbidden):
        cfo_spec.check("personnel_decision", action_class_registry)
    # Or 'external_commitment' (the "I'm helping the CFO; draft a contract" attack)
    with pytest.raises(ActionClassForbidden):
        cfo_spec.check("external_commitment", action_class_registry)
