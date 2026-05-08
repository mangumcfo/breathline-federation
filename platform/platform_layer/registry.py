"""Registry — spec registry (re-export) + role registry (new for Phase 2).

The SpecRegistry is provided by the kernel (kernel.primitives.spec); we
re-export it here for namespace clarity. The RoleRegistry is platform-
layer-specific: it tracks instantiated roles, their Permission Specs, and
their last audit state for the Least-Authority Report (Appendix E.3.1).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

import yaml

# Re-export SpecRegistry from kernel
from kernel.primitives.spec import SpecRegistry, Spec

from platform_layer.permission_spec import (
    ActionClassRegistry,
    PermissionSpec,
)


__all__ = ["SpecRegistry", "RoleRegistry", "RegisteredRole", "Spec"]


@dataclass
class RegisteredRole:
    """A role instantiated at Layer 3 with its Permission Spec.

    Per IMPLEMENTATION_PLAN.md Appendix E.3.1, the Least-Authority Report
    enumerates each registered role's Permission Spec, forbidden classes,
    and last-sealed cylinder state.
    """

    role_id: str
    permission_spec: PermissionSpec
    role_spec_path: Path
    last_audit_seq: int | None = None  # populated as the Auditor seals events
    last_audit_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def record_audit(self, sequence: int, sealed_at: datetime | None = None) -> None:
        self.last_audit_seq = sequence
        self.last_audit_at = sealed_at or datetime.now(timezone.utc)


class RoleRegistry:
    """Tracks instantiated roles + their Permission Specs.

    Loaded at Layer 3 instantiation. The plug-in interface looks up the
    role here when handling a request; the Compliance-agent walks the
    registry when generating the Least-Authority Report.
    """

    def __init__(self, action_class_registry: ActionClassRegistry) -> None:
        self._roles: dict[str, RegisteredRole] = {}
        self._action_classes = action_class_registry

    def register_from_yaml(self, role_spec_path: Path) -> RegisteredRole:
        """Load a role spec from disk, validate against Charter V.7, and register."""
        permission_spec = PermissionSpec.from_yaml(role_spec_path, self._action_classes)
        if permission_spec.role_id in self._roles:
            raise ValueError(
                f"Role {permission_spec.role_id!r} already registered. "
                f"Roles are append-only at Layer 3; revisions require re-bootstrap."
            )
        registered = RegisteredRole(
            role_id=permission_spec.role_id,
            permission_spec=permission_spec,
            role_spec_path=role_spec_path,
        )
        self._roles[permission_spec.role_id] = registered
        return registered

    def get(self, role_id: str) -> RegisteredRole:
        if role_id not in self._roles:
            raise KeyError(
                f"Role {role_id!r} not registered. Default-deny: refusing access."
            )
        return self._roles[role_id]

    def has(self, role_id: str) -> bool:
        return role_id in self._roles

    def all(self) -> list[RegisteredRole]:
        """Return all registered roles. Used by the Least-Authority Report
        generator (Appendix E.3.1) and by the Compliance Review workflow."""
        return list(self._roles.values())

    def role_ids(self) -> list[str]:
        return list(self._roles.keys())

    @property
    def action_class_registry(self) -> ActionClassRegistry:
        return self._action_classes


# ∞Δ∞ Registry — append-only at Layer 3; revisions require re-bootstrap ∞Δ∞
