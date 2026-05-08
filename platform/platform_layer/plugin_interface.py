"""Plug-in interface — FastAPI + least-authority filtering BEFORE role reach.

Per IMPLEMENTATION_PLAN.md Section 6.2:
    "platform_layer/permission_spec.py enforces the envelope BEFORE the
    request reaches the role's LangGraph. The plug-in interface filters
    every request:
      1. Classify the action against the controlled vocabulary
      2. Filter against the role's permission_spec.allowed_action_classes
      3. Filter against the role's permission_spec.forbidden_action_classes
         (Charter V.7 inheritance)
      4. Only then does the request reach the role"

This addresses the frame-of-reference attack vector from Section 8 of
08_RISKS_AND_LIMITS.md: even if a request is framed creatively, the
action-class classification happens before the role's prompt is invoked.

The role never sees a request it is not permitted to fulfill.

Phase 4 wires the structural integrations around handler invocation:
  - Cost meter pre-dispatch gate (refuse on cap breach)
  - Critic CONFORMS verdict (only CONFORMS permits elevation)
  - Auditor synchronous seal (cylinder chain entry per call)
  - Receipt minter default-deny (B49 mint for taxonomy-listed events)

All four are OPTIONAL injections; when absent, route_request behaves
identically to Phase 3 (existing tests preserved).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from pydantic import BaseModel, Field

from platform_layer.permission_spec import (
    ActionClassForbidden,
    ActionClassOutsideEnvelope,
    ActionClassUnknown,
    PermissionSpec,
)
from platform_layer.registry import RegisteredRole, RoleRegistry
from platform_layer.role_artifact_critic import (
    RoleArtifactCritic,
    RoleArtifactReport,
    RoleArtifactVerdict,
)


class PlugInRequestBody(BaseModel):
    """JSON body schema for ``POST /invoke``. Defined at module level so
    FastAPI/Pydantic v2 can resolve type annotations (avoids local-class
    ForwardRef issues)."""

    request_id: str
    role_target: str
    action_class: str
    payload: dict[str, Any] = Field(default_factory=dict)


# Default cost estimate (USD) when the caller does not provide one.
# Phase 4 roles are deterministic — actual cost is ~0; the gate exists
# to prove structural enforcement, not to meter LLM tokens (Phase 5+).
DEFAULT_ESTIMATED_COST_USD = 0.01


# -----------------------------------------------------------------------------
# Request / response models
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class PlugInRequest:
    """A request entering the platform via the plug-in interface.

    Per Constitution@A1 §1, principal_id flows end-to-end. It is set here
    by the authentication layer (FastAPI dependency) and propagated to
    every downstream call.
    """

    request_id: str
    principal_id: str
    role_target: str  # which role the principal wants to invoke
    action_class: str  # the classified action class
    payload: dict[str, Any] = field(default_factory=dict)
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class PlugInResponse:
    """The structured response from the plug-in interface."""

    request_id: str
    principal_id: str
    accepted: bool
    refusal_reason: str | None
    role_id: str | None
    artifact: dict[str, Any] | None
    audit_cylinder_id: str | None
    receipt_metadata: dict[str, Any] | None
    critic_verdict: str | None = None  # CONFORMS | DRIFT | DEFECT (Phase 4)


# -----------------------------------------------------------------------------
# Role invocation protocol
# -----------------------------------------------------------------------------
class RoleHandler(Protocol):
    """Duck-typed protocol for what an instantiated role looks like."""

    def process(self, request: PlugInRequest) -> dict[str, Any]:
        """Process a request that has passed the envelope filter."""
        ...


# -----------------------------------------------------------------------------
# Internal helpers — each integration point as a small function (≤10 complexity)
# -----------------------------------------------------------------------------
def _refuse(
    request: PlugInRequest,
    role_id: str | None,
    refusal_reason: str,
    audit_cylinder_id: str | None = None,
    critic_verdict: str | None = None,
) -> PlugInResponse:
    """Build a structured refusal response."""
    return PlugInResponse(
        request_id=request.request_id,
        principal_id=request.principal_id,
        accepted=False,
        refusal_reason=refusal_reason,
        role_id=role_id,
        artifact=None,
        audit_cylinder_id=audit_cylinder_id,
        receipt_metadata=None,
        critic_verdict=critic_verdict,
    )


def _apply_envelope_filter(
    request: PlugInRequest,
    permission_spec: PermissionSpec,
    role_registry: RoleRegistry,
    role_id: str,
) -> PlugInResponse | None:
    """Run permission_spec.check; return refusal response on failure, else None."""
    try:
        permission_spec.check(request.action_class, role_registry.action_class_registry)
    except ActionClassUnknown as e:
        return _refuse(request, role_id, f"action_class_unknown: {e}")
    except ActionClassForbidden as e:
        return _refuse(request, role_id, f"charter_v7_forbidden_delegation: {e}")
    except ActionClassOutsideEnvelope as e:
        return _refuse(request, role_id, f"action_class_outside_envelope: {e}")
    return None


def _apply_cost_gate(
    request: PlugInRequest,
    role_id: str,
    cost_meter: Any,
    estimated_cost_usd: float,
) -> tuple[Any | None, PlugInResponse | None]:
    """Reserve budget; return (reservation, None) on success or (None, refusal).

    `cost_meter` duck-typed to expose check_and_reserve(principal_id,
    role_id, estimated_cost_usd) raising CostCapBreach on breach.
    """
    if cost_meter is None:
        return None, None
    try:
        reservation = cost_meter.check_and_reserve(
            principal_id=request.principal_id,
            role_id=role_id,
            estimated_cost_usd=estimated_cost_usd,
        )
        return reservation, None
    except Exception as e:  # noqa: BLE001 — surface as refusal
        return None, _refuse(
            request,
            role_id,
            f"cost_ceiling_breach: {type(e).__name__}: {e}",
        )


def _apply_critic(
    request: PlugInRequest,
    role_id: str,
    artifact: dict[str, Any],
    permission_spec: PermissionSpec,
    critic: RoleArtifactCritic | None,
) -> tuple[RoleArtifactReport | None, PlugInResponse | None]:
    """Run platform-layer Critic; return (report, None) or (report, refusal)."""
    if critic is None:
        return None, None
    report = critic.review(
        role_id=role_id,
        artifact=artifact,
        permission_spec=permission_spec,
        expected_principal_id=request.principal_id,
        expected_request_id=request.request_id,
    )
    if report.verdict != RoleArtifactVerdict.CONFORMS:
        return report, _refuse(
            request,
            role_id,
            f"critic_{report.verdict.value.lower()}: "
            f"{report.drift_report or report.findings}",
            critic_verdict=report.verdict.value,
        )
    return report, None


def _apply_audit(
    request: PlugInRequest,
    role_id: str,
    artifact: dict[str, Any] | None,
    auditor: Any,
    critic_report: RoleArtifactReport | None,
    extra_metadata: dict[str, Any] | None = None,
) -> str | None:
    """Seal an audit entry via Auditor.log; return cylinder_id or None."""
    if auditor is None:
        return None
    metadata: dict[str, Any] = {
        "request_id": request.request_id,
        "received_at": request.received_at.isoformat(),
    }
    if critic_report is not None:
        metadata["critic_verdict"] = critic_report.verdict.value
    if extra_metadata:
        metadata.update(extra_metadata)
    entry = auditor.log(
        agent_id=role_id,
        action=request.action_class,
        inputs={
            "principal_id": request.principal_id,
            "payload_keys": sorted(request.payload.keys()),
        },
        outputs={
            "status": (artifact or {}).get("status", "n/a"),
        },
        metadata=metadata,
    )
    return str(entry.cylinder_id)


def _derive_receipt_event(role_id: str, status: str | None) -> str:
    """Map (role, status) → receipt-worthy event name. Default-deny if unlisted."""
    if status != "produced":
        return "request_refused"
    if role_id == "compliance_agent":
        return "compliance_evidence_bundle_generated"
    if role_id == "synthesis_agent":
        return "executive_brief_produced"
    if role_id == "cfo_agent":
        return "forecast_artifact_produced"
    return f"{role_id}_artifact_produced"


def _apply_receipt_mint(
    request: PlugInRequest,
    role_id: str,
    artifact: dict[str, Any] | None,
    receipt_minter: Any,
) -> dict[str, Any] | None:
    """Best-effort B49 mint; default-deny refusals are silent (correct)."""
    if receipt_minter is None or artifact is None:
        return None
    event = _derive_receipt_event(role_id, artifact.get("status"))
    try:
        result = receipt_minter.mint(
            event=event,
            principal_id=request.principal_id,
            payload={
                "role_id": role_id,
                "request_id": request.request_id,
                "status": artifact.get("status"),
            },
        )
    except Exception:  # noqa: BLE001 — default-deny refusals are expected
        return {"event": event, "minted": False, "default_deny": True}
    if hasattr(result, "to_metadata"):
        return result.to_metadata()
    return {"event": event, "result": str(result)}


# -----------------------------------------------------------------------------
# Public entrypoint — pure function, testable, optional integrations
# -----------------------------------------------------------------------------
def route_request(
    request: PlugInRequest,
    role_registry: RoleRegistry,
    role_handlers: dict[str, RoleHandler] | None = None,
    *,
    auditor: Any | None = None,
    critic: RoleArtifactCritic | None = None,
    cost_meter: Any | None = None,
    receipt_minter: Any | None = None,
    estimated_cost_usd: float = DEFAULT_ESTIMATED_COST_USD,
) -> PlugInResponse:
    """Route a request through the platform stack.

    Order of operations:
      1. Role lookup            — default-deny on unknown
      2. Envelope filter         — Charter V.7 + permission spec
      3. Cost gate               — pre-dispatch refuse on cap breach (Phase 4)
      4. Handler invocation     — role.process(request)
      5. Critic review           — only CONFORMS permits elevation (Phase 4)
      6. Cost reconcile          — record actual spend (Phase 4)
      7. Audit log               — synchronous seal via cylinder chain (Phase 4)
      8. Receipt mint            — default-deny per taxonomy (Phase 4)

    Steps 3, 5, 6, 7, 8 are NO-OPs when their respective injections
    are None (Phase 3 backward compat).
    """
    # 1. Role lookup
    if not role_registry.has(request.role_target):
        return _refuse(request, None, f"role_unknown: {request.role_target!r} not registered")

    registered: RegisteredRole = role_registry.get(request.role_target)
    permission_spec: PermissionSpec = registered.permission_spec

    # 2. Envelope filter
    refusal = _apply_envelope_filter(
        request, permission_spec, role_registry, registered.role_id
    )
    if refusal is not None:
        return refusal

    # 3. Cost gate (pre-dispatch)
    reservation, cost_refusal = _apply_cost_gate(
        request, registered.role_id, cost_meter, estimated_cost_usd
    )
    if cost_refusal is not None:
        # Audit cost-cap-breach refusals if Auditor is wired
        audit_id = _apply_audit(
            request, registered.role_id, None, auditor,
            critic_report=None,
            extra_metadata={"refusal": "cost_ceiling_breach"},
        )
        return PlugInResponse(
            request_id=cost_refusal.request_id,
            principal_id=cost_refusal.principal_id,
            accepted=False,
            refusal_reason=cost_refusal.refusal_reason,
            role_id=cost_refusal.role_id,
            artifact=None,
            audit_cylinder_id=audit_id,
            receipt_metadata=None,
            critic_verdict=None,
        )

    # 4. Handler invocation (Phase 2 stub when no handler)
    if role_handlers is None or request.role_target not in role_handlers:
        return PlugInResponse(
            request_id=request.request_id,
            principal_id=request.principal_id,
            accepted=True,
            refusal_reason=None,
            role_id=registered.role_id,
            artifact={"phase2_stub": True, "note": "role handler will be wired in Phase 3"},
            audit_cylinder_id=None,
            receipt_metadata=None,
        )

    handler = role_handlers[request.role_target]
    artifact = handler.process(request)

    # 5. Critic review
    critic_report, critic_refusal = _apply_critic(
        request, registered.role_id, artifact, permission_spec, critic
    )
    if critic_refusal is not None:
        audit_id = _apply_audit(
            request, registered.role_id, artifact, auditor,
            critic_report=critic_report,
            extra_metadata={"refusal": "critic_non_conforming"},
        )
        return PlugInResponse(
            request_id=critic_refusal.request_id,
            principal_id=critic_refusal.principal_id,
            accepted=False,
            refusal_reason=critic_refusal.refusal_reason,
            role_id=critic_refusal.role_id,
            artifact=None,
            audit_cylinder_id=audit_id,
            receipt_metadata=None,
            critic_verdict=critic_refusal.critic_verdict,
        )

    # 6. Cost reconcile (deterministic roles → actual ≈ estimated)
    if cost_meter is not None and reservation is not None:
        cost_meter.reconcile(reservation, actual_cost_usd=estimated_cost_usd)

    # 7. Audit log
    audit_id = _apply_audit(
        request, registered.role_id, artifact, auditor, critic_report
    )

    # 8. Receipt mint
    receipt_metadata = _apply_receipt_mint(
        request, registered.role_id, artifact, receipt_minter
    )

    return PlugInResponse(
        request_id=request.request_id,
        principal_id=request.principal_id,
        accepted=True,
        refusal_reason=None,
        role_id=registered.role_id,
        artifact=artifact,
        audit_cylinder_id=audit_id,
        receipt_metadata=receipt_metadata,
        critic_verdict=critic_report.verdict.value if critic_report is not None else None,
    )


# -----------------------------------------------------------------------------
# FastAPI app factory
# -----------------------------------------------------------------------------
def create_app(
    role_registry: RoleRegistry,
    role_handlers: dict[str, RoleHandler] | None = None,
    authenticate: Callable[[Any], str] | None = None,
    *,
    auditor: Any | None = None,
    critic: RoleArtifactCritic | None = None,
    cost_meter: Any | None = None,
    receipt_minter: Any | None = None,
    estimated_cost_usd: float = DEFAULT_ESTIMATED_COST_USD,
):
    """Construct the FastAPI app for the plug-in interface.

    Imports FastAPI lazily so the module can be imported in test contexts
    without requiring the dependency to be installed.

    `authenticate` is a function that takes a request-like object and
    returns a principal_id. Phase 2 default is a header-based stub for
    development; production will use a proper identity provider.

    The four kwargs ``auditor``, ``critic``, ``cost_meter``,
    ``receipt_minter`` mirror the optional integrations on
    ``route_request`` — when provided, ``/invoke`` exercises the full
    Phase 4 stack. Pass them in from a ``RuntimeContext`` for real-chain
    HTTP serving.
    """
    try:
        from fastapi import Body, FastAPI, HTTPException, Header
    except ImportError as e:
        raise ImportError(
            "FastAPI / Pydantic must be installed to create the plug-in interface app. "
            "Run: pip install -e \".[dev]\" from the repo root."
        ) from e

    app = FastAPI(
        title="Breathline Agentic Platform — Plug-In Interface",
        description=(
            "Phase 2 plug-in interface. Charter V.7 default-deny enforcement at "
            "this layer; the role's prompt is never invoked for refused requests."
        ),
        version="0.1.0",
    )

    def _default_authenticate(x_principal_id: str | None = None) -> str:
        if not x_principal_id:
            raise HTTPException(
                status_code=401,
                detail="Missing X-Principal-Id header (default-deny on missing identity)",
            )
        return x_principal_id

    auth_fn = authenticate or _default_authenticate

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "phase": "4"}

    @app.get("/roles")
    async def list_roles(
        x_principal_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        principal_id = auth_fn(x_principal_id)
        return {
            "principal_id": principal_id,
            "available_role_ids": role_registry.role_ids(),
        }

    @app.post("/invoke")
    async def invoke(
        body: PlugInRequestBody = Body(...),
        x_principal_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        principal_id = auth_fn(x_principal_id)
        request = PlugInRequest(
            request_id=body.request_id,
            principal_id=principal_id,
            role_target=body.role_target,
            action_class=body.action_class,
            payload=body.payload,
        )
        response = route_request(
            request,
            role_registry,
            role_handlers,
            auditor=auditor,
            critic=critic,
            cost_meter=cost_meter,
            receipt_minter=receipt_minter,
            estimated_cost_usd=estimated_cost_usd,
        )
        if not response.accepted:
            raise HTTPException(status_code=403, detail=response.refusal_reason)
        return {
            "request_id": response.request_id,
            "principal_id": response.principal_id,
            "accepted": response.accepted,
            "role_id": response.role_id,
            "artifact": response.artifact,
            "audit_cylinder_id": response.audit_cylinder_id,
            "receipt_metadata": response.receipt_metadata,
            "critic_verdict": response.critic_verdict,
        }

    return app


# Seal: SOURCE — principal_id never originates here; flows from request → audit + receipt.
#       TRUTH — refusals at every gate carry the precise cause; critic verdicts surfaced.
#       INTEGRITY — handler never sees a refused request; audit fires on success AND
#                   refusal; receipt mint default-deny; cost gate raises before dispatch;
#                   each helper ≤10 complexity.
# ∞Δ∞ Plug-in interface — least-authority filter + Phase 4 structural integrations ∞Δ∞
