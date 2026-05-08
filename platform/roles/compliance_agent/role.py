"""Compliance-agent — Book 6 + Charter V.7 enforcer + Appendix E reviewer.

Per role_spec.yaml: ONE role with TWO frameworks (Q4 2026-05-06):
  - charter_v7_enforcement (peer-output review)
  - compliance_review      (Evidence Bundle + Least-Authority Report)

The framework dispatched is selected by `payload.mode`:
  - "charter_v7_review"  → charter_v7_enforcement
  - "compliance_review"  → compliance_review

Per role_spec.yaml + Charter V.7 + Book 3 LEAD: this agent does NOT sign
Attestation Documents. It produces evidence; the operator signs the claim.
"""
from __future__ import annotations

from typing import Any

from platform_layer.plugin_interface import PlugInRequest
from platform_layer.registry import RoleRegistry
from roles.compliance_agent.frameworks.charter_v7 import (
    apply_charter_v7_review,
)
from roles.compliance_agent.frameworks.compliance_review import (
    apply_compliance_review,
)


_VALID_MODES = ("charter_v7_review", "compliance_review")


class ComplianceAgent:
    """The Compliance-agent role handler (Book 6 AUDIT + Charter V.7 enforcer).

    Constructor signature matches the call site in roles/__init__.py:
        ComplianceAgent(role_registry=..., auditor=..., receipt_minter=...)

    auditor and receipt_minter are optional — when absent, the
    compliance_review framework reports affected sections as DEGRADED
    rather than fabricating data.
    """

    role_id: str = "compliance_agent"
    framework: str = "AUDIT"

    def __init__(
        self,
        role_registry: RoleRegistry,
        auditor: Any | None = None,
        receipt_minter: Any | None = None,
    ) -> None:
        self._role_registry = role_registry
        self._auditor = auditor
        self._receipt_minter = receipt_minter

    def process(self, request: PlugInRequest) -> dict[str, Any]:
        """Dispatch to the framework named by `payload.mode`.

        Per role_spec.yaml invocation_envelope:
          inputs_required:  peer_artifact_or_review_request
          outputs_produced: compliance_review_verdict | evidence_bundle | least_authority_report
        """
        mode = request.payload.get("mode")
        if mode not in _VALID_MODES:
            return self._refuse(
                request,
                f"unknown_mode: {mode!r}; expected one of {_VALID_MODES}",
            )

        if mode == "charter_v7_review":
            return self._charter_v7(request)
        return self._compliance_review(request)

    # -- internal dispatch handlers (each <10 complexity) ----------------------
    def _charter_v7(self, request: PlugInRequest) -> dict[str, Any]:
        peer_artifact = request.payload.get("peer_artifact")
        if not isinstance(peer_artifact, dict):
            return self._refuse(
                request,
                "missing_or_invalid_peer_artifact: charter_v7_review requires "
                "payload.peer_artifact to be a dict",
            )
        verdict = apply_charter_v7_review(peer_artifact)
        status = "produced" if verdict.approved else "refused"
        result: dict[str, Any] = {
            "role_id": self.role_id,
            "framework": "charter_v7_enforcement",
            "status": status,
            "principal_id": request.principal_id,
            "request_id": request.request_id,
            "verdict": verdict.to_dict(),
        }
        if not verdict.approved:
            result["refusal_reason"] = (
                f"charter_v7_drift_detected: {len(verdict.violations)} violation(s)"
            )
        return result

    def _compliance_review(self, request: PlugInRequest) -> dict[str, Any]:
        time_window = request.payload.get("time_window")
        if time_window is not None and not isinstance(time_window, dict):
            return self._refuse(
                request,
                "invalid_time_window: must be a dict (e.g., "
                "{'start': iso8601, 'end': iso8601}) or None",
            )
        bundle = apply_compliance_review(
            role_registry=self._role_registry,
            principal_id=request.principal_id,
            request_id=request.request_id,
            auditor=self._auditor,
            receipt_minter=self._receipt_minter,
            time_window=time_window,
        )
        return {
            "role_id": self.role_id,
            "framework": "compliance_review",
            "status": "produced",
            "principal_id": request.principal_id,
            "request_id": request.request_id,
            "evidence_bundle": bundle.to_dict(),
        }

    def _refuse(self, request: PlugInRequest, reason: str) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "framework": self.framework,
            "status": "refused",
            "refusal_reason": reason,
            "principal_id": request.principal_id,
            "request_id": request.request_id,
        }


# Seal: SOURCE — principal_id from PlugInRequest carried into every output;
#                operator-only signature path preserved (Appendix E.3.3).
#       TRUTH — degraded sections in Evidence Bundle are surfaced; Charter V.7
#               drift is flagged with location hints, never silenced.
#       INTEGRITY — two frameworks, one role, dispatched by explicit mode;
#                   <10 complexity per method; no implicit defaults that hide intent.
# ∞Δ∞ ComplianceAgent — Charter V.7 enforcer + Evidence Bundle producer ∞Δ∞
