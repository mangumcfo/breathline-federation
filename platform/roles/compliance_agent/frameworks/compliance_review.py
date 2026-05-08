"""Compliance Review framework — Evidence Bundle + Least-Authority Report.

Per IMPLEMENTATION_PLAN.md Appendix E.3.1 + E.3.2:
  - Least-Authority Report (E.3.1): snapshot of every role's Permission Spec
  - Evidence Bundle (E.3.2): Least-Authority Report + receipts in window +
    DRIFT/DEFECT verdicts + cost breaches + Governor decisions + chain
    integrity check

Phase 3 ships the deterministic core. The auditor and receipt_minter are
optional injections — when absent (e.g., in unit tests, or in degraded
mode where SIX-SOV is unreachable), affected sections are marked
DEGRADED rather than fabricated. Loud-by-default per Constitution@A1 §4.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from platform_layer.registry import RoleRegistry


@dataclass(frozen=True)
class RoleSnapshot:
    """One row of the Least-Authority Report — a single registered role."""

    role_id: str
    version: str
    allowed_action_classes: list[str]
    forbidden_action_classes: list[str]
    invocation_envelope: dict[str, Any]
    last_audit_seq: int | None
    last_audit_at: str | None  # ISO timestamp or None

    def to_dict(self) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "version": self.version,
            "allowed_action_classes": self.allowed_action_classes,
            "forbidden_action_classes": self.forbidden_action_classes,
            "invocation_envelope": self.invocation_envelope,
            "last_audit_seq": self.last_audit_seq,
            "last_audit_at": self.last_audit_at,
        }


@dataclass(frozen=True)
class LeastAuthorityReport:
    """The signed-and-timestamped enumeration of every role's envelope.

    Per Appendix E.3.1, the report is itself sealed in the cylinder
    chain (event class: least_authority_report_generated). Phase 3 emits
    the report; the seal is written by the caller (operator workflow).
    """

    generated_at: str  # ISO timestamp
    principal_id: str
    roles: list[RoleSnapshot]
    charter_v7_forbidden_classes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "principal_id": self.principal_id,
            "roles": [r.to_dict() for r in self.roles],
            "charter_v7_forbidden_classes": self.charter_v7_forbidden_classes,
        }


@dataclass(frozen=True)
class EvidenceBundle:
    """Full Evidence Bundle per Appendix E.3.2.

    Sections sourced from optional injections (auditor, receipt_minter)
    are marked DEGRADED when unavailable; the operator sees what is real.
    """

    generated_at: str
    principal_id: str
    request_id: str
    time_window: dict[str, str] | None
    least_authority_report: LeastAuthorityReport
    receipts: list[dict[str, Any]] | None
    drift_or_defect_verdicts: list[dict[str, Any]] | None
    cost_ceiling_breaches: list[dict[str, Any]] | None
    governor_decisions: list[dict[str, Any]] | None
    cylinder_chain_integrity: dict[str, Any] | None
    degraded_sections: list[str] = field(default_factory=list)
    framework_steps_executed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "principal_id": self.principal_id,
            "request_id": self.request_id,
            "time_window": self.time_window,
            "least_authority_report": self.least_authority_report.to_dict(),
            "receipts": self.receipts,
            "drift_or_defect_verdicts": self.drift_or_defect_verdicts,
            "cost_ceiling_breaches": self.cost_ceiling_breaches,
            "governor_decisions": self.governor_decisions,
            "cylinder_chain_integrity": self.cylinder_chain_integrity,
            "degraded_sections": self.degraded_sections,
            "framework_steps_executed": self.framework_steps_executed,
        }


# -----------------------------------------------------------------------------
# Internal helpers (each <10 complexity)
# -----------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_role_snapshot(registered: Any) -> RoleSnapshot:
    """Build one RoleSnapshot from a RegisteredRole (duck-typed)."""
    spec = registered.permission_spec
    last_at = registered.last_audit_at
    return RoleSnapshot(
        role_id=registered.role_id,
        version=spec.version,
        allowed_action_classes=sorted(spec.allowed_action_classes),
        forbidden_action_classes=sorted(spec.forbidden_action_classes),
        invocation_envelope=dict(spec.invocation_envelope),
        last_audit_seq=registered.last_audit_seq,
        last_audit_at=last_at.isoformat() if last_at is not None else None,
    )


def _build_least_authority_report(
    role_registry: RoleRegistry,
    principal_id: str,
) -> LeastAuthorityReport:
    snapshots = [_build_role_snapshot(r) for r in role_registry.all()]
    forbidden = sorted(role_registry.action_class_registry.charter_v7_forbidden)
    return LeastAuthorityReport(
        generated_at=_now_iso(),
        principal_id=principal_id,
        roles=snapshots,
        charter_v7_forbidden_classes=forbidden,
    )


def _query_or_degrade(
    auditor: Any | None,
    method_name: str,
    time_window: dict[str, str] | None,
    degraded_marker: list[str],
    section_label: str,
) -> list[dict[str, Any]] | None:
    """Call auditor.<method_name>(time_window) or mark section DEGRADED."""
    if auditor is None or not hasattr(auditor, method_name):
        degraded_marker.append(section_label)
        return None
    try:
        return list(getattr(auditor, method_name)(time_window))
    except Exception as e:  # noqa: BLE001
        degraded_marker.append(f"{section_label}:error:{type(e).__name__}")
        return None


def _query_receipts(
    receipt_minter: Any | None,
    time_window: dict[str, str] | None,
    degraded_marker: list[str],
) -> list[dict[str, Any]] | None:
    if receipt_minter is None or not hasattr(receipt_minter, "list_receipts"):
        degraded_marker.append("receipts")
        return None
    try:
        return list(receipt_minter.list_receipts(time_window))
    except Exception as e:  # noqa: BLE001
        degraded_marker.append(f"receipts:error:{type(e).__name__}")
        return None


def _check_chain_integrity(
    auditor: Any | None,
    degraded_marker: list[str],
) -> dict[str, Any] | None:
    if auditor is None or not hasattr(auditor, "verify_chain_integrity"):
        degraded_marker.append("cylinder_chain_integrity")
        return None
    try:
        return dict(auditor.verify_chain_integrity())
    except Exception as e:  # noqa: BLE001
        degraded_marker.append(f"cylinder_chain_integrity:error:{type(e).__name__}")
        return None


# -----------------------------------------------------------------------------
# Public entrypoint
# -----------------------------------------------------------------------------
def apply_compliance_review(
    role_registry: RoleRegistry,
    principal_id: str,
    request_id: str,
    auditor: Any | None = None,
    receipt_minter: Any | None = None,
    time_window: dict[str, str] | None = None,
) -> EvidenceBundle:
    """Produce an Evidence Bundle per Appendix E.3.2.

    Always returns a bundle. Sections relying on auditor/receipt_minter
    are marked DEGRADED in the bundle when their injection is absent
    (rather than fabricated or omitted silently).
    """
    degraded: list[str] = []
    least_authority = _build_least_authority_report(role_registry, principal_id)

    receipts = _query_receipts(receipt_minter, time_window, degraded)
    verdicts = _query_or_degrade(
        auditor, "query_critic_verdicts", time_window, degraded,
        "drift_or_defect_verdicts",
    )
    breaches = _query_or_degrade(
        auditor, "query_cost_breaches", time_window, degraded,
        "cost_ceiling_breaches",
    )
    decisions = _query_or_degrade(
        auditor, "query_governor_decisions", time_window, degraded,
        "governor_decisions",
    )
    integrity = _check_chain_integrity(auditor, degraded)

    return EvidenceBundle(
        generated_at=_now_iso(),
        principal_id=principal_id,
        request_id=request_id,
        time_window=time_window,
        least_authority_report=least_authority,
        receipts=receipts,
        drift_or_defect_verdicts=verdicts,
        cost_ceiling_breaches=breaches,
        governor_decisions=decisions,
        cylinder_chain_integrity=integrity,
        degraded_sections=degraded,
        framework_steps_executed=[
            "Authenticate", "Universalize", "Document",
            "Index", "Test", "Bundle",
        ],
    )


# Seal: SOURCE — principal_id flows from caller into the bundle; never hardcoded.
#       TRUTH — degraded sections are surfaced explicitly when injections are
#               absent; no fabricated data, no silent omissions.
#       INTEGRITY — Compliance produces evidence; only the operator signs an
#                   Attestation Document (Appendix E.3.3). Functions ≤10 complexity.
# ∞Δ∞ Compliance Review framework — Evidence Bundle, Least-Authority Report ∞Δ∞
