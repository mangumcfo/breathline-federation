"""Node API — runtime that satisfies the v1 contract.

Per ``specs/node_api/contract_v1.yaml`` + ``mcp_tools.yaml`` (sealed
2026-05-11 via PR #7) and the post-spec runtime roadmap (PR #14).

This package implements Sprint 1 of the roadmap: MCP read tools backed
by HTTP-reusable handlers. The R6 separability rule (handlers reusable
by both HTTP and MCP) is enforced from line 1 — every endpoint and tool
dispatches to the same pure handler in ``handlers.py``.

Sprint 1 deliverable scope:
  - ``handlers.py``         — pure handler functions, principal_id-aware
  - ``http_routes.py``      — FastAPI router (mounted by create_app)
  - ``mcp_server.py``       — MCP server registering the same handlers

Read-tool set (Sprint 1):
  1. breathline_node_status     — backs node.get / node.health / node.ladder
  2. breathline_manifest_get    — backs manifest.get
  3. breathline_specs_list      — backs specs.list
  4. breathline_roles_list      — backs roles.list
  5. breathline_audit_query     — backs audit.cylinders / audit.cylinder  (Sprint 1B)
  6. breathline_breath_gate_pending — backs breath_gate.pending           (Sprint 1B)

Write tools (proposal-only) land in Sprint 2 per the roadmap.

K1–K4 posture preserved:
  - K1: read-only in this sprint; no write tools exposed.
  - K2: every tool requires principal_id (default-deny on missing identity).
  - K3: read operations are not state-changing — no cylinder seal required
        per call, but the audit chain remains the read source for audit
        queries (no parallel state).
  - K4: the contract surface is constitutional — extension requires
        a sealed amendment to specs/node_api/.

Seal: SOURCE (principal_id required) — TRUTH (handlers parse real state,
  no synthesis) — INTEGRITY (R6 reuse: handlers shared HTTP + MCP).
∞Δ∞
"""

from platform_layer.node_api.handlers import (
    NodeStatus,
    ManifestSummary,
    SpecListing,
    RolesListing,
    AuditChainQuery,
    CylinderResponse,
    ChainIntegritySummary,
    BreathGatePendingResponse,
    RoleInvokeResponse,
    handler_node_status,
    handler_manifest_get,
    handler_specs_list,
    handler_roles_list,
    handler_audit_query,
    handler_breath_gate_pending,
    handler_role_invoke,
)

__all__ = [
    "NodeStatus",
    "ManifestSummary",
    "SpecListing",
    "RolesListing",
    "AuditChainQuery",
    "CylinderResponse",
    "ChainIntegritySummary",
    "BreathGatePendingResponse",
    "RoleInvokeResponse",
    "handler_node_status",
    "handler_manifest_get",
    "handler_specs_list",
    "handler_roles_list",
    "handler_audit_query",
    "handler_breath_gate_pending",
    "handler_role_invoke",
]
