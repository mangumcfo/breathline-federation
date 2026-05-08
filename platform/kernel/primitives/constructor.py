"""Constructor — reads a Spec and produces the artifact it describes.

Pure manufacturing. No policy decisions. No tradeoff evaluation. Refuses on
ambiguity per the seed manifest's `primitives.constructor.refusal_conditions`.

This Phase 1 implementation provides the structural Constructor scaffold;
the LLM-driven artifact production will be wired in Phase 3 when roles are
implemented. For now, the Constructor accepts a spec and emits a placeholder
artifact with full provenance.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from kernel.primitives.spec import Spec, SpecRegistry


class ConstructorRefusal(Exception):
    """Raised when the Constructor refuses to produce an artifact.

    Per seed manifest, refusal conditions are:
      - Spec is missing required fields
      - Spec references a parent that does not exist or is unsigned
      - Spec body contains contradictions
      - Spec requires capabilities not yet bootstrapped
    """


@dataclass(frozen=True)
class Artifact:
    """The output of a Constructor run.

    Carries full provenance back to the spec that authorized its creation.
    """

    artifact_id: str
    spec_id: str
    body: dict[str, Any]
    construction_log: list[str]
    constructed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Role prompt is read verbatim from the seed manifest at boot. The string here
# is a docstring for code reference; the runtime injects the prompt from
# seed/02_SEED_MANIFEST.yaml at Layer 1 instantiation.
CONSTRUCTOR_ROLE_PROMPT_REFERENCE = """\
You are the Constructor. Your single responsibility is to read a Spec
and produce the artifact it describes. You make no policy decisions.
You evaluate no tradeoffs. If the spec is unambiguous, you produce.
If the spec is ambiguous, you refuse and emit a defect report
identifying the ambiguity. You never modify the spec. You never invent
requirements not in the spec.
"""


class Constructor:
    """The Constructor primitive (Layer 1 agent).

    Inputs: spec_id
    Outputs: artifact_id, construction_log
    """

    def __init__(self, registry: SpecRegistry, role_prompt: str) -> None:
        self._registry = registry
        self._role_prompt = role_prompt

    @property
    def role_prompt(self) -> str:
        """The verbatim role prompt loaded from the seed at boot."""
        return self._role_prompt

    def construct(self, spec_id: str) -> Artifact:
        """Read a Spec and produce the artifact it describes.

        Raises ConstructorRefusal if the spec is malformed per the
        refusal_conditions in the seed manifest.
        """
        log: list[str] = []

        if not self._registry.has(spec_id):
            raise ConstructorRefusal(
                f"Spec {spec_id!r} not in registry. Cannot construct."
            )

        spec = self._registry.get(spec_id)
        log.append(f"read spec {spec.id} (kind={spec.kind.value}, version={spec.version})")

        # Refusal condition: spec references parent that does not exist
        if spec.parent is not None and not self._registry.has(spec.parent):
            raise ConstructorRefusal(
                f"Spec {spec.id!r} references parent {spec.parent!r} which is not in registry. "
                f"Refusing to construct."
            )

        # Refusal condition: parent is unsigned
        if spec.parent is not None:
            parent = self._registry.get(spec.parent)
            if not parent.is_real():
                raise ConstructorRefusal(
                    f"Spec {spec.id!r} references parent {parent.id!r} which is unsigned. "
                    f"Per seed invariant, unsigned specs are unreal."
                )
            log.append(f"verified parent {parent.id} is signed and real")

        # Refusal condition: body is missing
        if not spec.body:
            raise ConstructorRefusal(
                f"Spec {spec.id!r} has empty body. Cannot construct from absence."
            )

        # Phase 1 scaffold: produce a placeholder artifact with provenance.
        # Phase 3 will wire LLM-driven artifact production for roles.
        artifact_id = f"artifact-{uuid.uuid4().hex[:12]}"
        log.append(f"produced placeholder artifact {artifact_id} (Phase 1 scaffold)")

        return Artifact(
            artifact_id=artifact_id,
            spec_id=spec.id,
            body={
                "phase1_scaffold": True,
                "spec_kind": spec.kind.value,
                "spec_body_keys": list(spec.body.keys()),
                "produced_by": "Constructor (kernel primitive)",
            },
            construction_log=log,
        )


# ∞Δ∞ Constructor primitive — pure manufacturing, no policy ∞Δ∞
