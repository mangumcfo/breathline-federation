"""Node API MCP server — registers tools that dispatch to shared handlers.

Per R6 of ``specs/node_api/separability.md``: MCP and HTTP feed the same
handlers. There is no MCP-only capability. There is no HTTP-only
capability. Every tool here dispatches to a handler in ``handlers.py``
that is also reachable from the HTTP routes in ``http_routes.py``.

Per ``specs/node_api/mcp_tools.yaml`` intentional_absences (sealed in
PR #7): the MCP surface deliberately does NOT expose breath-gate
approve/deny, upgrade.apply, books.activate, cost.limits.update, or
spec mutation. The model proposes; the operator disposes. K1 enforced
by REMOVING the lever, not hoping the calling agent is aligned.

Sprint 1 scope (this module):
  - breathline_node_status          (read; backs node.get/health/ladder)
  - breathline_manifest_get          (read)
  - breathline_specs_list            (read)
  - breathline_roles_list            (read)

Sprint 1B (continuation, scaffolded):
  - breathline_audit_query           (read; raises NotImplementedError)
  - breathline_breath_gate_pending   (read-only; raises NotImplementedError)

Auth: every tool requires principal_id. The MCP server obtains principal_id
from the calling context per the active MCP protocol's auth model; the
``authenticate`` callable injected into ``create_node_mcp_server`` translates
the context into a principal_id string.
"""
from __future__ import annotations

from typing import Any, Callable

from platform_layer.node_api.handlers import (
    MissingPrincipalError,
    NodeStateError,
    handler_node_status,
    handler_manifest_get,
    handler_specs_list,
    handler_roles_list,
    handler_audit_query,
    handler_breath_gate_pending,
)


def create_node_mcp_server(
    role_registry: Any,
    authenticate: Callable[[Any], str] | None = None,
    server_name: str = "breathline-node",
):
    """Build an MCP server with the Sprint 1 read tools registered.

    Args:
        role_registry: live RoleRegistry instance (required for roles_list
            and for the node_status health probe's registry check).
        authenticate: optional callable that takes the MCP context object
            and returns a principal_id. Default raises if the context does
            not carry a principal — production deployments must wire this
            against the deployment's auth model.
        server_name: MCP server name (default ``breathline-node`` per
            ``mcp_tools.yaml``).

    Returns:
        An MCP server instance with tools registered and ready to bind to
        a transport (stdio or WSS at 127.0.0.1:8421/mcp per the spec).

    Note: This module imports the ``mcp`` library lazily so the rest of
    the platform_layer code remains importable in environments without
    MCP installed. The MCP library will be added to platform/pyproject.toml
    as an optional dep for Sprint 1.
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as e:
        raise ImportError(
            "The 'mcp' library must be installed to create the node MCP server. "
            "Run: pip install 'mcp[cli]' from the platform/ venv. "
            "Will be added to pyproject.toml [project.optional-dependencies.mcp] "
            "before this module ships."
        ) from e

    mcp = FastMCP(server_name)

    def _resolve_principal(ctx: Any) -> str:
        """Resolve principal_id from the MCP call context."""
        if authenticate is not None:
            return authenticate(ctx)
        principal = getattr(ctx, "principal_id", None) if ctx is not None else None
        if not principal:
            raise MissingPrincipalError(
                "MCP call context did not carry a principal_id. "
                "Configure an authenticate callable when creating the MCP server "
                "(no hardcoded principals — CONSTITUTION §1)."
            )
        return principal

    # ------------------------------------------------------------------
    # READ tools (Sprint 1)
    # ------------------------------------------------------------------

    @mcp.tool()
    def breathline_node_status(
        include_health: bool = True,
        include_ladder: bool = True,
    ) -> dict[str, Any]:
        """Identify the local Breathline node, report health, current ladder rung.

        Backs the contract endpoints node.get + node.health + node.ladder.
        Returns the full status; ``include_health=False`` omits the health
        block, ``include_ladder=False`` omits the ladder block.
        """
        principal_id = _resolve_principal(_current_ctx())
        result = handler_node_status(
            principal_id=principal_id, role_registry=role_registry
        )
        out: dict[str, Any] = {
            "node_id": result.node_id,
            "tier": result.tier,
            "ladder_level": result.ladder_level,
            "ladder_level_name": result.ladder_level_name,
            "kernel_version": result.kernel_version,
            "manifest_version": result.manifest_version,
            "seal_glyph": result.seal_glyph,
            "queried_at": result.queried_at.isoformat(),
        }
        if include_health:
            out["health"] = {
                "kernel_ok": result.kernel_ok,
                "manifest_ok": result.manifest_ok,
                "specs_valid": result.specs_valid,
                "signatures_ok": result.signatures_ok,
                "chain_sentinel": result.chain_sentinel,
                "breath_gate_ready": result.breath_gate_ready,
                "last_seal_seq": result.last_seal_seq,
                "details": [c.model_dump() for c in result.health_details],
            }
        if include_ladder:
            out["ladder"] = {
                "current_level": result.current_level,
                "next_level": result.next_level,
                "requirements": result.ladder_requirements,
                "anchor_book": result.anchor_book,
            }
        return out

    @mcp.tool()
    def breathline_manifest_get() -> dict[str, Any]:
        """Return the parsed, signature-verified manifest.yaml.

        Sprint 1 surfaces ``integrity_ok=True`` and a note that signature
        verification lands in Sprint 4 with the installer integration.
        Backs the contract endpoint manifest.get.
        """
        principal_id = _resolve_principal(_current_ctx())
        result = handler_manifest_get(principal_id=principal_id)
        return result.model_dump(mode="json")

    @mcp.tool()
    def breathline_specs_list(series: str = "all") -> dict[str, Any]:
        """Enumerate role / permission / constitutional specs on this node.

        Args:
            series: one of ``executive``, ``family``, ``generational_legacy``,
                ``education``, ``health``, ``federation``, ``_base``, or
                ``all`` (default).

        Backs the contract endpoint specs.list.
        """
        principal_id = _resolve_principal(_current_ctx())
        result = handler_specs_list(principal_id=principal_id, series=series)
        return result.model_dump(mode="json")

    @mcp.tool()
    def breathline_roles_list() -> dict[str, Any]:
        """List roles registered with the platform RoleRegistry.

        Returns the active roles, their frameworks, and permission spec
        references. Backs the contract endpoint roles.list.
        """
        principal_id = _resolve_principal(_current_ctx())
        result = handler_roles_list(
            principal_id=principal_id, role_registry=role_registry
        )
        return result.model_dump(mode="json")

    # ------------------------------------------------------------------
    # Sprint 1B placeholders — wired but raise NotImplementedError
    # ------------------------------------------------------------------

    @mcp.tool()
    def breathline_audit_query(
        seq: int | None = None,
        since_seq: int | None = None,
        limit: int = 50,
        filter_kind: str | None = None,
    ) -> dict[str, Any]:
        """Query the cylinder chain — paginated or by single seq.

        SPRINT 1B SCAFFOLD: signature is final; implementation queued in the
        continuation PR (will dispatch to audit_adapter.read_chain). R6 contract
        same handler called from HTTP (audit.cylinders / audit.cylinder)
        and MCP.
        """
        principal_id = _resolve_principal(_current_ctx())
        return handler_audit_query(
            principal_id=principal_id,
            seq=seq,
            since_seq=since_seq,
            limit=limit,
            filter_kind=filter_kind,
        )

    @mcp.tool()
    def breathline_breath_gate_pending() -> dict[str, Any]:
        """List currently-blocking breath-gate requests.

        Read-only over MCP. Approval/denial is INTENTIONALLY not exposed
        over MCP per mcp_tools.yaml intentional_absences — humans only, via
        UI or CLI. The model proposes; the operator disposes.

        SPRINT 1B SCAFFOLD: signature is final; implementation queued.
        """
        principal_id = _resolve_principal(_current_ctx())
        return handler_breath_gate_pending(principal_id=principal_id)

    return mcp


def _current_ctx() -> Any:
    """Return the current MCP call context (or None if not in a tool call).

    FastMCP threads request context via a contextvar; this helper retrieves
    it without coupling tool implementations to FastMCP internals. If
    FastMCP's API changes, this is the single touch point to update.
    """
    try:
        from mcp.server.fastmcp import Context
    except ImportError:
        return None
    try:
        return Context.get()
    except Exception:  # noqa: BLE001 — context unavailable outside tool call
        return None


# -----------------------------------------------------------------------------
# Intentional absences — for K1 audit trail
# -----------------------------------------------------------------------------
# The following MCP tools are DELIBERATELY NOT registered, matching
# specs/node_api/mcp_tools.yaml intentional_absences:
#
#   - breath_gate.approve / breath_gate.deny  (humans only)
#   - upgrade.apply                            (humans only)
#   - books.activate                           (humans only — ladder-rung K1)
#   - cost.limits.update                       (humans only)
#   - specs ingestion / mutation               (sealed PR only)
#
# K1 Human Primacy is enforced by REMOVING the lever, not by hoping the
# calling agent is well-aligned. If the lever is not exposed over MCP,
# no MCP client — well-aligned or not — can pull it.

# Seal:
#   SOURCE — every tool requires principal_id; no hardcoded principals.
#   TRUTH  — handlers dispatched directly; no MCP-specific data synthesis.
#   INTEGRITY — R6 backstop: all 6 tools share the http_routes.py handlers.
#               Write-class tools (approve/deny/apply/activate/update/mutate)
#               are deliberately ABSENT — K1 enforced by removal, not hope.
# ∞Δ∞ Node API MCP server — read-only, R6-shared handlers, K1 by absence ∞Δ∞
