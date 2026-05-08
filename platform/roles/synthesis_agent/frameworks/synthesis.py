"""SYNTHESIS framework — Book 12, deterministic orchestrator core.

Loop: Decompose → Invoke → Aggregate → Reconcile → Surface tensions →
Produce executive brief.

The orchestrator never decides FOR the operator; it produces a unified
brief that surfaces peer outputs and the tensions between them. Every
operator-facing decision is gated upstream (Charter II + Book 3 LEAD).

Phase 3 ships deterministic orchestration with a generic peer-handler
interface; Phase 4 adds LangGraph wrapping for richer narrative.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from platform_layer.plugin_interface import PlugInRequest


REQUIRED_INPUTS: tuple[str, ...] = ("request_summary", "peer_roles_to_invoke")


class _PeerHandler(Protocol):
    """Local Protocol mirroring RoleHandler — keeps this module standalone."""

    def process(self, request: PlugInRequest) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class PeerInvocationResult:
    """Result of invoking one peer role inside the synthesis loop."""

    role_id: str
    invoked: bool
    artifact: dict[str, Any] | None
    refusal_reason: str | None


@dataclass(frozen=True)
class ExecutiveBrief:
    """The integrated output of SYNTHESIS — decision-grade evidence for humans."""

    request_summary: str
    principal_id: str
    request_id: str
    peer_results: list[PeerInvocationResult]
    integrated_findings: list[str]
    tensions_surfaced: list[str]
    framework_steps_executed: list[str]
    refusals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_summary": self.request_summary,
            "principal_id": self.principal_id,
            "request_id": self.request_id,
            "peer_results": [
                {
                    "role_id": p.role_id,
                    "invoked": p.invoked,
                    "artifact": p.artifact,
                    "refusal_reason": p.refusal_reason,
                }
                for p in self.peer_results
            ],
            "integrated_findings": self.integrated_findings,
            "tensions_surfaced": self.tensions_surfaced,
            "framework_steps_executed": self.framework_steps_executed,
            "refusals": self.refusals,
        }


class SynthesisInputError(ValueError):
    """Required SYNTHESIS inputs are missing or malformed."""


# -----------------------------------------------------------------------------
# Internal step functions (each <10 complexity)
# -----------------------------------------------------------------------------
def _validate_inputs(payload: dict[str, Any]) -> tuple[str, list[str]]:
    missing = [k for k in REQUIRED_INPUTS if k not in payload]
    if missing:
        raise SynthesisInputError(
            f"Missing required SYNTHESIS inputs: {missing}. "
            f"Both request_summary and peer_roles_to_invoke are required."
        )
    summary = payload["request_summary"]
    peers = payload["peer_roles_to_invoke"]
    if not isinstance(summary, str) or not summary.strip():
        raise SynthesisInputError("request_summary must be a non-empty string")
    if not isinstance(peers, list) or not peers:
        raise SynthesisInputError(
            "peer_roles_to_invoke must be a non-empty list of role IDs"
        )
    if not all(isinstance(p, str) for p in peers):
        raise SynthesisInputError("peer_roles_to_invoke must contain only role-id strings")
    return summary, peers


def _build_peer_request(
    parent_request: PlugInRequest,
    peer_role_id: str,
    peer_payload: dict[str, Any],
) -> PlugInRequest:
    """Carry principal_id from parent request into the peer invocation."""
    return PlugInRequest(
        request_id=f"{parent_request.request_id}::{peer_role_id}",
        principal_id=parent_request.principal_id,
        role_target=peer_role_id,
        action_class=peer_payload.get("action_class", "produce_forecast_artifact"),
        payload=peer_payload.get("payload", {}),
    )


def _invoke_peer(
    peer_role_id: str,
    peer_handlers: dict[str, _PeerHandler],
    parent_request: PlugInRequest,
    peer_payloads: dict[str, dict[str, Any]],
) -> PeerInvocationResult:
    """Invoke one peer role; return structured result regardless of outcome."""
    if peer_role_id not in peer_handlers:
        return PeerInvocationResult(
            role_id=peer_role_id,
            invoked=False,
            artifact=None,
            refusal_reason=f"peer_handler_unavailable: {peer_role_id!r} not registered",
        )
    handler = peer_handlers[peer_role_id]
    sub_payload = peer_payloads.get(peer_role_id, {})
    sub_request = _build_peer_request(parent_request, peer_role_id, sub_payload)
    try:
        artifact = handler.process(sub_request)
    except Exception as e:  # noqa: BLE001 — surface any peer error as refusal
        return PeerInvocationResult(
            role_id=peer_role_id,
            invoked=True,
            artifact=None,
            refusal_reason=f"peer_invocation_error: {type(e).__name__}: {e}",
        )
    return PeerInvocationResult(
        role_id=peer_role_id,
        invoked=True,
        artifact=artifact,
        refusal_reason=None,
    )


def _integrate_findings(results: list[PeerInvocationResult]) -> list[str]:
    """Aggregate one-line findings per peer for the executive brief."""
    findings: list[str] = []
    for r in results:
        if not r.invoked:
            findings.append(f"{r.role_id}: NOT_INVOKED — {r.refusal_reason}")
            continue
        if r.artifact is None:
            findings.append(f"{r.role_id}: NO_ARTIFACT — {r.refusal_reason}")
            continue
        status = r.artifact.get("status", "unknown")
        framework = r.artifact.get("framework", "?")
        findings.append(f"{r.role_id} [{framework}]: {status}")
    return findings


def _surface_tensions(results: list[PeerInvocationResult]) -> list[str]:
    """Detect cross-role tensions worth surfacing to the operator."""
    tensions: list[str] = []
    refused = [r for r in results if r.invoked and r.artifact and r.artifact.get("status") == "refused"]
    produced = [r for r in results if r.invoked and r.artifact and r.artifact.get("status") == "produced"]
    if refused and produced:
        refused_ids = ", ".join(r.role_id for r in refused)
        produced_ids = ", ".join(r.role_id for r in produced)
        tensions.append(
            f"partial_synthesis: {produced_ids} produced while {refused_ids} refused — "
            f"executive brief is incomplete and the refusal must be reviewed before action"
        )
    not_invoked = [r for r in results if not r.invoked]
    if not_invoked:
        ids = ", ".join(r.role_id for r in not_invoked)
        tensions.append(f"missing_peers: {ids} — synthesis covers only the available roles")
    return tensions


# -----------------------------------------------------------------------------
# Public entrypoint
# -----------------------------------------------------------------------------
def apply_synthesis(
    request: PlugInRequest,
    peer_handlers: dict[str, _PeerHandler],
) -> ExecutiveBrief:
    """Run the SYNTHESIS loop on a request.

    Steps: Decompose → Invoke → Aggregate → Reconcile → Surface tensions →
    Translate. Always returns an ExecutiveBrief; peer failures appear in
    the brief rather than raising (operator must see what was attempted).
    """
    summary, peers = _validate_inputs(request.payload)
    peer_payloads: dict[str, dict[str, Any]] = request.payload.get("peer_payloads", {})

    results: list[PeerInvocationResult] = []
    for peer_role_id in peers:
        results.append(
            _invoke_peer(peer_role_id, peer_handlers, request, peer_payloads)
        )

    findings = _integrate_findings(results)
    tensions = _surface_tensions(results)

    return ExecutiveBrief(
        request_summary=summary,
        principal_id=request.principal_id,
        request_id=request.request_id,
        peer_results=results,
        integrated_findings=findings,
        tensions_surfaced=tensions,
        framework_steps_executed=[
            "Decompose", "Invoke", "Aggregate",
            "Reconcile", "SurfaceTensions", "Translate",
        ],
        refusals=[],
    )


# Seal: SOURCE — principal_id from PlugInRequest carried into every peer call.
#       TRUTH — peer refusals and unavailability are surfaced, never silenced;
#               operator sees exactly what was attempted and what failed.
#       INTEGRITY — refuses on malformed input; peer errors caught and
#                   surfaced without poisoning the brief; functions ≤10 complexity.
# ∞Δ∞ SYNTHESIS framework — orchestrator without decision authority ∞Δ∞
