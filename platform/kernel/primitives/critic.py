"""Critic — adversarial verifier with veto power over elevation.

Decides whether a produced Artifact conforms to its Spec. Returns one of
three verdicts: CONFORMS, DRIFT, or DEFECT. Only CONFORMS permits
elevation.

This Phase 1 implementation provides the verdict structure and basic
conformance checks (spec/artifact identity, required-field presence). The
LLM-driven adversarial verification will be wired in Phase 3.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from kernel.primitives.constructor import Artifact
from kernel.primitives.spec import Spec, SpecRegistry


class CriticVerdict(str, Enum):
    """Three possible verdicts per seed manifest."""

    CONFORMS = "CONFORMS"
    DRIFT = "DRIFT"
    DEFECT = "DEFECT"


@dataclass(frozen=True)
class CriticReport:
    """The output of a Critic run."""

    verdict: CriticVerdict
    spec_id: str
    artifact_id: str
    drift_report: str | None
    findings: list[str]
    reviewed_at: datetime


CRITIC_ROLE_PROMPT_REFERENCE = """\
You are the Critic. You receive a Spec and an Artifact. You decide
whether the Artifact faithfully implements the Spec. You are
adversarial by design — you assume the Constructor may have
hallucinated, drifted, or taken shortcuts. You produce a verdict:
CONFORMS, DRIFT, or DEFECT. Drift means the artifact is plausible
but does not match the spec. Defect means the artifact is broken.
Only CONFORMS permits elevation.
"""


class Critic:
    """The Critic primitive (Layer 1 agent) — has veto power over elevation."""

    veto_power = True

    def __init__(self, registry: SpecRegistry, role_prompt: str) -> None:
        self._registry = registry
        self._role_prompt = role_prompt

    @property
    def role_prompt(self) -> str:
        return self._role_prompt

    def review(self, spec_id: str, artifact: Artifact) -> CriticReport:
        """Review a produced artifact against its spec; return verdict."""
        findings: list[str] = []

        if not self._registry.has(spec_id):
            return CriticReport(
                verdict=CriticVerdict.DEFECT,
                spec_id=spec_id,
                artifact_id=artifact.artifact_id,
                drift_report=f"Spec {spec_id!r} not in registry",
                findings=["spec_missing_from_registry"],
                reviewed_at=datetime.now(timezone.utc),
            )

        spec = self._registry.get(spec_id)
        findings.append(f"loaded spec {spec.id}")

        # Identity check: artifact must reference the same spec
        if artifact.spec_id != spec.id:
            return CriticReport(
                verdict=CriticVerdict.DEFECT,
                spec_id=spec_id,
                artifact_id=artifact.artifact_id,
                drift_report=(
                    f"Artifact references spec_id={artifact.spec_id!r} "
                    f"but was reviewed against {spec.id!r}"
                ),
                findings=["spec_artifact_identity_mismatch"],
                reviewed_at=datetime.now(timezone.utc),
            )
        findings.append("spec/artifact identity match")

        # Body check: artifact must have a body
        if not artifact.body:
            return CriticReport(
                verdict=CriticVerdict.DEFECT,
                spec_id=spec_id,
                artifact_id=artifact.artifact_id,
                drift_report="Artifact body is empty",
                findings=["empty_artifact_body"],
                reviewed_at=datetime.now(timezone.utc),
            )
        findings.append("artifact has body")

        # Phase 1 scaffold: structural conformance only.
        # Phase 3 will wire LLM-driven adversarial review against spec body.
        findings.append("phase1_scaffold: structural conformance only")
        return CriticReport(
            verdict=CriticVerdict.CONFORMS,
            spec_id=spec_id,
            artifact_id=artifact.artifact_id,
            drift_report=None,
            findings=findings,
            reviewed_at=datetime.now(timezone.utc),
        )


# ∞Δ∞ Critic primitive — adversarial by design, veto power over elevation ∞Δ∞
