"""Role artifact Critic — platform-layer conformance verdict on role dicts.

Per IMPLEMENTATION_PLAN.md Section 4 + 8.2:
    Critic returns CONFORMS | DRIFT | DEFECT on the recursion path. Only
    CONFORMS permits elevation.

The kernel Critic (kernel/primitives/critic.py) operates on the
Constructor → Artifact pipeline (Spec → Artifact identity check). The
platform-layer Critic here operates one level up: on the dict returned
by a RoleHandler.process(). It verifies the artifact's structural
conformance to the role's invocation_envelope BEFORE the platform
elevates the response (audits + mints receipts + returns to operator).

Phase 4 ships deterministic structural Critic. Phase 5 may add LLM-driven
adversarial review on top, but the structural floor is preserved.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from platform_layer.permission_spec import PermissionSpec


class RoleArtifactVerdict(str, Enum):
    """Per seed manifest: three verdicts; only CONFORMS permits elevation."""

    CONFORMS = "CONFORMS"
    DRIFT = "DRIFT"
    DEFECT = "DEFECT"


@dataclass(frozen=True)
class RoleArtifactReport:
    """Output of a RoleArtifactCritic.review() call."""

    verdict: RoleArtifactVerdict
    role_id: str
    findings: list[str]
    drift_report: str | None = None
    reviewed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "role_id": self.role_id,
            "findings": self.findings,
            "drift_report": self.drift_report,
            "reviewed_at": self.reviewed_at.isoformat(),
        }


# Required keys on every role-handler dict (the platform contract).
REQUIRED_TOP_LEVEL_KEYS: tuple[str, ...] = (
    "role_id", "framework", "status", "principal_id", "request_id",
)

ALLOWED_STATUS_VALUES: tuple[str, ...] = ("produced", "refused")


class RoleArtifactCritic:
    """Platform-layer Critic for role-handler dict outputs.

    Stateless; safe to share across requests.
    """

    def review(
        self,
        role_id: str,
        artifact: dict[str, Any],
        permission_spec: PermissionSpec,
        expected_principal_id: str,
        expected_request_id: str,
    ) -> RoleArtifactReport:
        """Verify the artifact's structural conformance to the role spec.

        Returns DEFECT for missing/malformed contracts; DRIFT for
        principal/request-id mismatches; CONFORMS otherwise. Refusal
        artifacts ("status": "refused") still CONFORM if shaped correctly —
        the Critic verifies the SHAPE, not the success.
        """
        findings: list[str] = []

        if not isinstance(artifact, dict):
            return self._defect(role_id, ["artifact_not_a_dict"])

        missing = [k for k in REQUIRED_TOP_LEVEL_KEYS if k not in artifact]
        if missing:
            return self._defect(role_id, [f"missing_required_keys:{missing}"])

        if artifact["role_id"] != role_id:
            return self._drift(
                role_id,
                ["role_id_mismatch"],
                f"artifact.role_id={artifact['role_id']!r} but expected {role_id!r}",
            )
        findings.append("role_id_match")

        if artifact["status"] not in ALLOWED_STATUS_VALUES:
            return self._defect(
                role_id,
                [f"invalid_status:{artifact['status']!r}"],
            )
        findings.append(f"status_valid:{artifact['status']}")

        if artifact["principal_id"] != expected_principal_id:
            return self._drift(
                role_id,
                ["principal_id_mismatch"],
                "principal_id did not propagate end-to-end",
            )
        findings.append("principal_id_propagated")

        if artifact["request_id"] != expected_request_id:
            return self._drift(
                role_id,
                ["request_id_mismatch"],
                "request_id did not propagate end-to-end",
            )
        findings.append("request_id_propagated")

        # If produced, verify at least one of the expected output keys is present
        if artifact["status"] == "produced":
            outputs_produced = self._outputs_produced(permission_spec)
            if outputs_produced:
                present = [k for k in outputs_produced if k in artifact]
                if not present and not _has_any_artifact_key(artifact):
                    return self._drift(
                        role_id,
                        ["no_output_artifact_present"],
                        f"none of role_spec.outputs_produced={outputs_produced} "
                        f"appear in produced artifact",
                    )
                findings.append(f"outputs_present:{present}")

        # If refused, verify a refusal_reason is present
        if artifact["status"] == "refused" and not artifact.get("refusal_reason"):
            return self._defect(
                role_id,
                ["refused_without_reason"],
            )

        findings.append("structural_conformance: phase4_platform_critic")
        return RoleArtifactReport(
            verdict=RoleArtifactVerdict.CONFORMS,
            role_id=role_id,
            findings=findings,
        )

    # -- internal helpers (each <10 complexity) --------------------------------
    @staticmethod
    def _outputs_produced(permission_spec: PermissionSpec) -> list[str]:
        envelope = permission_spec.invocation_envelope or {}
        outputs = envelope.get("outputs_produced", [])
        return list(outputs) if isinstance(outputs, list) else []

    @staticmethod
    def _defect(role_id: str, findings: list[str]) -> RoleArtifactReport:
        return RoleArtifactReport(
            verdict=RoleArtifactVerdict.DEFECT,
            role_id=role_id,
            findings=findings,
            drift_report=None,
        )

    @staticmethod
    def _drift(
        role_id: str, findings: list[str], drift_report: str
    ) -> RoleArtifactReport:
        return RoleArtifactReport(
            verdict=RoleArtifactVerdict.DRIFT,
            role_id=role_id,
            findings=findings,
            drift_report=drift_report,
        )


# Recognized "artifact" keys role handlers may use when outputs_produced
# names a logical artifact (e.g., "forecast_artifact" → "forecast_artifact"
# key in the dict). Keep flexible.
_ARTIFACT_KEY_HINTS: tuple[str, ...] = (
    "forecast_artifact", "executive_brief", "evidence_bundle",
    "least_authority_report", "verdict", "compliance_review_verdict",
)


def _has_any_artifact_key(artifact: dict[str, Any]) -> bool:
    return any(k in artifact for k in _ARTIFACT_KEY_HINTS)


# Seal: SOURCE — verifies principal_id propagated end-to-end (Constitution@A1 §1).
#       TRUTH — DRIFT/DEFECT findings explain WHY; no silent CONFORMS.
#       INTEGRITY — refused artifacts still pass shape conformance; only
#                   CONFORMS permits elevation; functions ≤10 complexity.
# ∞Δ∞ Platform-layer Critic — structural conformance for role-handler outputs ∞Δ∞
