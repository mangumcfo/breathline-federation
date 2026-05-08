"""Spec — the canonical machine-readable format for "what is this thing".

Every role, framework, capability, request, audit record, and elevation in
the platform is a Spec. Specs are immutable once published; revisions
create new ids. See seed/02_SEED_MANIFEST.yaml `primitives.spec` for the
authoritative schema.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, ConfigDict


class SpecKind(str, Enum):
    """The kinds of specs the registry recognizes (per seed manifest)."""

    ROLE = "role"
    FRAMEWORK = "framework"
    CAPABILITY = "capability"
    REQUEST = "request"
    ELEVATION = "elevation"
    AUDIT = "audit"


class SpecSignatures(BaseModel):
    """Who proposed, who critiqued, who governed."""

    proposed_by: str | None = None
    critiqued_by: str | None = None
    governed_by: str | None = None
    human_signature: str | None = None  # for breath-gated approvals

    model_config = ConfigDict(extra="forbid")


class Spec(BaseModel):
    """The seven required fields per the seed manifest's primitive.spec contract."""

    id: str = Field(..., description="Globally unique, kebab-case")
    kind: SpecKind
    version: str = Field(..., description="Semver")
    parent: str | None = Field(
        None,
        description="The spec that authorized this one. Only the seed itself has no parent.",
    )
    body: dict[str, Any] = Field(default_factory=dict)
    signatures: SpecSignatures = Field(default_factory=SpecSignatures)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="forbid")

    def is_real(self) -> bool:
        """Per seed manifest: 'Specs without all required signatures are unreal
        (cannot be referenced).'"""
        return self.signatures.proposed_by is not None


class SpecRegistry:
    """Append-only registry of specs. Revisions create new ids."""

    def __init__(self) -> None:
        self._by_id: dict[str, Spec] = {}

    def register(self, spec: Spec) -> None:
        """Register a new spec. Raises ValueError if id already exists."""
        if spec.id in self._by_id:
            raise ValueError(
                f"Spec id {spec.id!r} already exists. Specs are append-only; "
                f"revisions must create new ids."
            )
        if spec.parent is not None and spec.parent not in self._by_id:
            raise ValueError(
                f"Spec {spec.id!r} references parent {spec.parent!r} which does not exist. "
                f"Per seed manifest invariant: 'Every spec has a parent except the seed itself.'"
            )
        self._by_id[spec.id] = spec

    def get(self, spec_id: str) -> Spec:
        if spec_id not in self._by_id:
            raise KeyError(f"Spec id {spec_id!r} not in registry")
        return self._by_id[spec_id]

    def has(self, spec_id: str) -> bool:
        return spec_id in self._by_id

    def all(self) -> list[Spec]:
        return list(self._by_id.values())


# ∞Δ∞ Spec primitive — encoded per seed manifest contract ∞Δ∞
