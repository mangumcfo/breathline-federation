"""Node API HTTP routes — FastAPI router; thin wrapper over handlers.

Per R6 of ``specs/node_api/separability.md``: handlers live in
``handlers.py``; this module is one of two transport layers (the other
is ``mcp_server.py``). Both call the same pure functions.

Mounting: extend ``platform_layer.plugin_interface.create_app`` to include
this router, OR mount independently into a separate FastAPI app for the
node-api-only deployment shape that the contract anticipates (default
bind ``127.0.0.1:8421``).

Auth: principal_id-bearer via ``X-Principal-Id`` header. Mirrors the
existing pattern in ``plugin_interface.create_app``. Per G's witness
refinement on the post-spec runtime roadmap (2026-05-11): every read
tool also enforces principal_id-bearer auth — read-only does not bypass
identity.
"""
from __future__ import annotations

from typing import Any, Callable

from platform_layer.node_api.handlers import (
    MissingPrincipalError,
    NodeStateError,
    NodeStatus,
    ManifestSummary,
    SpecListing,
    RolesListing,
    handler_node_status,
    handler_manifest_get,
    handler_specs_list,
    handler_roles_list,
)


def create_node_api_router(
    role_registry: Any,
    authenticate: Callable[[str | None], str] | None = None,
):
    """Build a FastAPI APIRouter exposing the Sprint 1 node-api endpoints.

    Routes added (Sprint 1 scope):

      - GET  /api/v1/node              → node.get (subset of NodeStatus)
      - GET  /api/v1/node/health       → node.health (subset of NodeStatus)
      - GET  /api/v1/node/ladder       → node.ladder (subset of NodeStatus)
      - GET  /api/v1/manifest          → manifest.get
      - GET  /api/v1/specs             → specs.list (?series=<series>)
      - GET  /api/v1/roles             → roles.list (existing /roles
                                          remains for Phase-4 callers; this
                                          is the contract-versioned route)

    Sprint 1B (continuation):

      - GET  /api/v1/audit/cylinders, /api/v1/audit/cylinders/{seq}
      - GET  /api/v1/breath-gate/pending

    Args:
        role_registry: live RoleRegistry instance (required for /roles and
            for node_status health probe).
        authenticate: optional callable that takes the X-Principal-Id header
            value and returns the resolved principal_id. Default raises 401
            on missing header (same pattern as plugin_interface.create_app).
    """
    try:
        from fastapi import APIRouter, Header, HTTPException, Query
    except ImportError as e:
        raise ImportError(
            "FastAPI must be installed to create the node-api router. "
            "Run: pip install -e \".[dev]\" from the repo root."
        ) from e

    router = APIRouter(prefix="/api/v1", tags=["node-api-v1"])

    def _default_authenticate(x_principal_id: str | None) -> str:
        if not x_principal_id:
            raise HTTPException(
                status_code=401,
                detail=(
                    "Missing X-Principal-Id header "
                    "(default-deny on missing identity; principal_id is "
                    "required for every Node API call per CONSTITUTION §1)"
                ),
            )
        return x_principal_id

    auth_fn = authenticate or _default_authenticate

    def _translate_handler_error(e: Exception) -> HTTPException:
        """Map handler errors → loud, contextual HTTP errors (CONSTITUTION §4)."""
        if isinstance(e, MissingPrincipalError):
            return HTTPException(status_code=401, detail=str(e))
        if isinstance(e, NodeStateError):
            return HTTPException(status_code=503, detail=str(e))
        if isinstance(e, NotImplementedError):
            return HTTPException(status_code=501, detail=str(e))
        if isinstance(e, ValueError):
            return HTTPException(status_code=400, detail=str(e))
        return HTTPException(
            status_code=500,
            detail=f"{type(e).__name__}: {e}",
        )

    # ------------------------------------------------------------------
    # A. Node identity / status (3 routes, all backed by node_status)
    # ------------------------------------------------------------------

    @router.get("/node", response_model=dict)
    async def node_get(
        x_principal_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        principal_id = auth_fn(x_principal_id)
        try:
            status = handler_node_status(
                principal_id=principal_id, role_registry=role_registry
            )
        except Exception as e:  # noqa: BLE001 — translate then surface
            raise _translate_handler_error(e) from e
        # node.get projection
        return {
            "node_id": status.node_id,
            "tier": status.tier,
            "ladder_level": status.ladder_level,
            "ladder_level_name": status.ladder_level_name,
            "kernel_version": status.kernel_version,
            "manifest_version": status.manifest_version,
            "seal_glyph": status.seal_glyph,
        }

    @router.get("/node/health", response_model=dict)
    async def node_health(
        x_principal_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        principal_id = auth_fn(x_principal_id)
        try:
            status = handler_node_status(
                principal_id=principal_id, role_registry=role_registry
            )
        except Exception as e:  # noqa: BLE001
            raise _translate_handler_error(e) from e
        return {
            "kernel_ok": status.kernel_ok,
            "manifest_ok": status.manifest_ok,
            "specs_valid": status.specs_valid,
            "signatures_ok": status.signatures_ok,
            "chain_sentinel": status.chain_sentinel,
            "breath_gate_ready": status.breath_gate_ready,
            "last_seal_seq": status.last_seal_seq,
            "details": [c.model_dump() for c in status.health_details],
        }

    @router.get("/node/ladder", response_model=dict)
    async def node_ladder(
        x_principal_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        principal_id = auth_fn(x_principal_id)
        try:
            status = handler_node_status(
                principal_id=principal_id, role_registry=role_registry
            )
        except Exception as e:  # noqa: BLE001
            raise _translate_handler_error(e) from e
        return {
            "current_level": status.current_level,
            "next_level": status.next_level,
            "requirements": status.ladder_requirements,
            "anchor_book": status.anchor_book,
        }

    # ------------------------------------------------------------------
    # B. Manifest
    # ------------------------------------------------------------------

    @router.get("/manifest", response_model=dict)
    async def manifest_get(
        x_principal_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        principal_id = auth_fn(x_principal_id)
        try:
            result: ManifestSummary = handler_manifest_get(principal_id=principal_id)
        except Exception as e:  # noqa: BLE001
            raise _translate_handler_error(e) from e
        return result.model_dump(mode="json")

    # ------------------------------------------------------------------
    # C. Specs
    # ------------------------------------------------------------------

    @router.get("/specs", response_model=dict)
    async def specs_list(
        x_principal_id: str | None = Header(default=None),
        series: str = Query(default="all"),
    ) -> dict[str, Any]:
        principal_id = auth_fn(x_principal_id)
        try:
            result: SpecListing = handler_specs_list(
                principal_id=principal_id, series=series
            )
        except Exception as e:  # noqa: BLE001
            raise _translate_handler_error(e) from e
        return result.model_dump(mode="json")

    # ------------------------------------------------------------------
    # D. Roles (versioned route; existing /roles in plugin_interface stays)
    # ------------------------------------------------------------------

    @router.get("/roles", response_model=dict)
    async def roles_list(
        x_principal_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        principal_id = auth_fn(x_principal_id)
        try:
            result: RolesListing = handler_roles_list(
                principal_id=principal_id, role_registry=role_registry
            )
        except Exception as e:  # noqa: BLE001
            raise _translate_handler_error(e) from e
        return result.model_dump(mode="json")

    # ------------------------------------------------------------------
    # E. Sprint 1B placeholders — 501 Not Implemented (intentional)
    # ------------------------------------------------------------------

    @router.get("/audit/cylinders", response_model=dict)
    async def audit_cylinders(
        x_principal_id: str | None = Header(default=None),
        since_seq: int | None = Query(default=None),
        limit: int = Query(default=50, le=500),
        filter_kind: str | None = Query(default=None),
    ) -> dict[str, Any]:
        # Auth still runs even before the handler raises — fail-on-missing-id
        # before fail-on-not-implemented. K2 default-deny is the first gate.
        auth_fn(x_principal_id)
        raise HTTPException(
            status_code=501,
            detail=(
                "audit.cylinders is scaffolded for Sprint 1B. The handler "
                "signature is final; implementation queued in the "
                "continuation PR (will dispatch to audit_adapter.read_chain)."
            ),
        )

    @router.get("/breath-gate/pending", response_model=dict)
    async def breath_gate_pending(
        x_principal_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        auth_fn(x_principal_id)
        raise HTTPException(
            status_code=501,
            detail=(
                "breath_gate.pending is scaffolded for Sprint 1B. The handler "
                "signature is final; implementation queued in the "
                "continuation PR (will dispatch to kernel.breath_gate.list_pending)."
            ),
        )

    return router


# Seal:
#   SOURCE — X-Principal-Id required on every route; default-deny on missing.
#   TRUTH  — handler exceptions translated to loud HTTP errors with cause.
#   INTEGRITY — every route delegates to handlers.py; no logic duplicated here.
# ∞Δ∞ Node API HTTP router — thin wrapper, R6 backstop ∞Δ∞
