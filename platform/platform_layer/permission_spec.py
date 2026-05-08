"""Permission Spec — Charter V.7 enforcement at instantiation.

Per IMPLEMENTATION_PLAN.md Section 6:
    "Each role has a Permission Spec at roles/<role>/role_spec.yaml
    declaring allowed/forbidden action classes. The plug-in interface
    enforces the envelope BEFORE the request reaches the role's
    LangGraph. The role never sees a request it is not permitted to
    fulfill."

Charter V.7 forbidden classes are inherited unconditionally — no role spec
can override them. Per Section 6.1, forbidden classes are loaded from
seed/action_classes.yaml's `charter_v7_forbidden_classes` list and merged
into every Permission Spec at instantiation.

This addresses the frame-of-reference attack vector from
08_RISKS_AND_LIMITS.md: even if a request is framed creatively, the
action-class classification happens before the role's prompt is invoked.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# Default seed dir (overridable for testing)
DEFAULT_SEED_DIR = Path(__file__).resolve().parent.parent / "seed"


class PermissionSpecViolation(Exception):
    """Raised when a Permission Spec attempts to override Charter V.7
    forbidden classes, or when validation otherwise fails at instantiation."""


class ActionClassUnknown(Exception):
    """Raised when a request's classified action class is not in the
    seed's controlled vocabulary (action_classes.yaml). Default-deny."""


class ActionClassForbidden(Exception):
    """Raised when a request's classified action class is in the role's
    forbidden_action_classes (or in the Charter V.7 forbidden list)."""


class ActionClassOutsideEnvelope(Exception):
    """Raised when a request's classified action class is not in the role's
    allowed_action_classes envelope. Default-deny."""


@dataclass(frozen=True)
class ActionClass:
    """One allowed action class from the seed vocabulary."""

    id: str
    description: str
    always_available: bool = False


@dataclass(frozen=True)
class ActionClassRegistry:
    """The controlled vocabulary loaded from seed/action_classes.yaml.

    Loaded as immutable at boot. Adding a new action class requires the
    same amendment path as adding a receipt-worthy event.
    """

    charter_v7_forbidden: frozenset[str]
    allowed: dict[str, ActionClass]

    @classmethod
    def from_yaml(cls, path: Path | None = None) -> "ActionClassRegistry":
        path = path or (DEFAULT_SEED_DIR / "action_classes.yaml")
        data = yaml.safe_load(path.read_text())

        forbidden = frozenset(data.get("charter_v7_forbidden_classes", []))
        if not forbidden:
            raise PermissionSpecViolation(
                f"action_classes.yaml at {path} declares no Charter V.7 forbidden "
                f"classes. This is structurally invalid — Charter V.7 cannot be "
                f"empty. Refusing to load."
            )

        allowed_list = data.get("allowed_action_classes", [])
        allowed = {
            entry["id"]: ActionClass(
                id=entry["id"],
                description=entry["description"],
                always_available=entry.get("always_available", False),
            )
            for entry in allowed_list
        }

        # Sanity: forbidden and allowed must not overlap
        overlap = forbidden & set(allowed.keys())
        if overlap:
            raise PermissionSpecViolation(
                f"action_classes.yaml has classes appearing in BOTH forbidden "
                f"and allowed lists: {sorted(overlap)}. Charter V.7 forbidden "
                f"classes cannot also be allowed. Halting."
            )

        return cls(charter_v7_forbidden=forbidden, allowed=allowed)

    def is_known(self, action_class: str) -> bool:
        """Return True iff the action class is in the controlled vocabulary
        (either Charter V.7 forbidden or in the allowed list)."""
        return action_class in self.charter_v7_forbidden or action_class in self.allowed

    def is_forbidden(self, action_class: str) -> bool:
        return action_class in self.charter_v7_forbidden

    def is_always_available(self, action_class: str) -> bool:
        ac = self.allowed.get(action_class)
        return ac is not None and ac.always_available


@dataclass(frozen=True)
class PermissionSpec:
    """A role's Permission Spec — its least-authority envelope.

    Loaded from roles/<role>/role_spec.yaml at boot. Charter V.7 forbidden
    classes are merged in from action_classes.yaml at construction time;
    they cannot be overridden by the role spec.
    """

    role_id: str
    version: str
    allowed_action_classes: frozenset[str]
    forbidden_action_classes: frozenset[str]  # always includes Charter V.7
    invocation_envelope: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(
        cls,
        path: Path,
        action_class_registry: ActionClassRegistry,
    ) -> "PermissionSpec":
        """Load and validate a role's Permission Spec.

        Per Section 6.1, this is enforced at boot:
          - If the role's allowed list contains anything in Charter V.7 forbidden,
            raise PermissionSpecViolation
          - If the role's allowed list contains anything not in the controlled
            vocabulary, raise PermissionSpecViolation
          - Charter V.7 forbidden classes are merged into the role's forbidden
            list unconditionally
        """
        data = yaml.safe_load(path.read_text())

        role_id = data.get("role")
        version = data.get("version", "0.1")
        if not role_id:
            raise PermissionSpecViolation(f"Role spec at {path} missing 'role' field")

        allowed_list = data.get("allowed_action_classes", [])
        forbidden_list = data.get("forbidden_action_classes", [])

        # Charter V.7 forbidden classes always inherit, regardless of spec content
        merged_forbidden = frozenset(forbidden_list) | action_class_registry.charter_v7_forbidden

        # Validation 1: spec cannot allow what Charter V.7 forbids
        bad_allows = frozenset(allowed_list) & action_class_registry.charter_v7_forbidden
        if bad_allows:
            raise PermissionSpecViolation(
                f"Role spec at {path} attempts to allow Charter V.7 forbidden classes: "
                f"{sorted(bad_allows)}. The Governor refuses such elevations regardless of "
                f"operator approval. Refusing to load."
            )

        # Validation 2: every allowed class must be in the controlled vocabulary
        unknown = frozenset(allowed_list) - set(action_class_registry.allowed.keys())
        if unknown:
            raise PermissionSpecViolation(
                f"Role spec at {path} declares unknown action classes: "
                f"{sorted(unknown)}. Add them to seed/action_classes.yaml first "
                f"(amendment path: operator approval + Charter V.7 review)."
            )

        return cls(
            role_id=role_id,
            version=version,
            allowed_action_classes=frozenset(allowed_list),
            forbidden_action_classes=merged_forbidden,
            invocation_envelope=data.get("invocation_envelope", {}),
        )

    def check(self, action_class: str, action_class_registry: ActionClassRegistry) -> None:
        """Filter a classified action against this role's envelope.

        Raises:
          ActionClassUnknown        — class not in controlled vocabulary
          ActionClassForbidden      — class in forbidden list (incl. Charter V.7)
          ActionClassOutsideEnvelope— class not in role's allowed list

        Per Section 6.2, this is enforced at the plug-in interface layer
        BEFORE the role's prompt is invoked.
        """
        # Always-available classes bypass the envelope check
        if action_class_registry.is_always_available(action_class):
            return

        # Default-deny on unknown action classes
        if not action_class_registry.is_known(action_class):
            raise ActionClassUnknown(
                f"Action class {action_class!r} not in controlled vocabulary. "
                f"Default-deny: refusing request."
            )

        # Forbidden (Charter V.7 or role-specific) — refuse
        if action_class in self.forbidden_action_classes:
            raise ActionClassForbidden(
                f"Action class {action_class!r} is forbidden for role {self.role_id!r} "
                f"(Charter V.7 inheritance or role-specific). Refusing request."
            )

        # Outside the role's envelope — refuse
        if action_class not in self.allowed_action_classes:
            raise ActionClassOutsideEnvelope(
                f"Action class {action_class!r} is outside role {self.role_id!r}'s "
                f"allowed envelope. Default-deny: refusing request."
            )


# ∞Δ∞ Permission Spec — Charter V.7 inheritance, structural enforcement at plug-in layer ∞Δ∞
