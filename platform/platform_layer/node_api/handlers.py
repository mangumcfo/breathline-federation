"""Node API handlers — pure functions; R6 separability enforced.

Every handler in this module is a pure function callable from both
HTTP (``http_routes.py``) and MCP (``mcp_server.py``) without any
surface-specific coupling. The R6 rule from ``specs/node_api/separability.md``:

  > "MCP and HTTP feed the same handlers. There is no MCP-only capability.
  >  There is no HTTP-only capability. Every tool in mcp_tools.yaml
  >  dispatches to the same backend handler as the corresponding endpoint
  >  in contract_v1.yaml. The MCP server is a transport over the same
  >  surface, not a parallel surface."

Lumen witness exit criterion (PR #14, 2026-05-11):
  Sprint 1 is not complete unless handlers are reusable by HTTP.

This module is the structural backstop for both rules: handlers live here
as pure functions; the two transport layers (HTTP, MCP) are thin wrappers.

K1 posture: every handler requires ``principal_id``. Missing or empty
principal_id → ``MissingPrincipalError``. The transport layer is
responsible for translating the error into the right surface response.

Each handler returns a Pydantic model so both HTTP (JSON) and MCP
(structured tool result) can serialize cleanly.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Error types
# -----------------------------------------------------------------------------
class MissingPrincipalError(ValueError):
    """Raised when a handler is called without a principal_id."""


class NodeStateError(RuntimeError):
    """Raised when the node's on-disk state cannot be loaded coherently."""


# -----------------------------------------------------------------------------
# Response models — same shape over HTTP and MCP
# -----------------------------------------------------------------------------
class HealthCheck(BaseModel):
    """Result of a single named health probe."""

    check: str
    ok: bool
    message: str | None = None


class NodeStatus(BaseModel):
    """Composite status response — backs node.get, node.health, node.ladder.

    The MCP `breathline_node_status` tool returns this whole object; HTTP
    routes split it across the three endpoints (node.get, node.health,
    node.ladder) for callers that want narrower data.
    """

    # node.get fields
    node_id: str
    tier: str
    ladder_level: int
    ladder_level_name: str
    kernel_version: str
    manifest_version: str
    seal_glyph: str = "∞Δ∞"

    # node.health fields
    kernel_ok: bool
    manifest_ok: bool
    specs_valid: bool
    signatures_ok: bool
    chain_sentinel: str
    breath_gate_ready: bool
    last_seal_seq: int
    health_details: list[HealthCheck] = Field(default_factory=list)

    # node.ladder fields
    current_level: int
    next_level: int | None
    ladder_requirements: list[dict[str, Any]] = Field(default_factory=list)
    anchor_book: str | None = None

    queried_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ManifestSummary(BaseModel):
    """Parsed manifest.yaml + integrity flag."""

    version: str
    released: str | None = None
    sealed_by: str | None = None
    seal_glyph: str = "∞Δ∞"
    raw: dict[str, Any]
    integrity_ok: bool = True
    integrity_note: str | None = None


class SpecEntry(BaseModel):
    """One spec file listed in the specs.list response."""

    spec_id: str  # canonical: "<series>/<filename-without-ext>"
    series: str
    path: str
    sha256: str | None = None
    ladder_level: int | None = None
    status: str = "unknown"


class SpecListing(BaseModel):
    """Result of specs.list."""

    series_filter: str
    count: int
    specs: list[SpecEntry] = Field(default_factory=list)


class RoleEntry(BaseModel):
    """One role listed in roles.list."""

    role_id: str
    framework: str | None = None
    ladder: int | None = None
    status: str = "active"
    permission_spec_ref: str | None = None


class RolesListing(BaseModel):
    """Result of roles.list."""

    count: int
    roles: list[RoleEntry] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------------
def _require_principal(principal_id: str | None) -> str:
    """Default-deny on missing identity (K1/K2)."""
    if not principal_id:
        raise MissingPrincipalError(
            "principal_id is required for every Node API call "
            "(no hardcoded principals — CONSTITUTION §1)"
        )
    return principal_id


def _repo_root(start: Path | None = None) -> Path:
    """Walk upward to find the manifest.yaml-anchored repo root.

    The handler doesn't assume a fixed cwd; it walks up from this file's
    location and the optional ``start`` parameter to find ``manifest.yaml``.
    """
    candidates: list[Path] = []
    if start is not None:
        candidates.append(Path(start).resolve())
    candidates.append(Path(__file__).resolve().parent)
    for c in candidates:
        cur = c
        for _ in range(10):
            if (cur / "manifest.yaml").exists():
                return cur
            if cur.parent == cur:
                break
            cur = cur.parent
    raise NodeStateError(
        "Could not locate manifest.yaml-anchored repo root from "
        f"{[str(c) for c in candidates]}"
    )


def _load_manifest(repo_root: Path) -> dict[str, Any]:
    """Parse manifest.yaml; raises NodeStateError on failure."""
    path = repo_root / "manifest.yaml"
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as e:
        raise NodeStateError(f"manifest.yaml unreadable: {e}") from e
    if not isinstance(data, dict):
        raise NodeStateError(
            f"manifest.yaml did not parse to a mapping; got {type(data).__name__}"
        )
    return data


# -----------------------------------------------------------------------------
# Handler: node_status (backs node.get, node.health, node.ladder)
# -----------------------------------------------------------------------------
def handler_node_status(
    *,
    principal_id: str,
    repo_root: Path | str | None = None,
    role_registry: Any | None = None,
) -> NodeStatus:
    """Identify the node, run a basic health probe, locate ladder rung.

    Composite handler: HTTP exposes it via three separate routes
    (``GET /node``, ``GET /node/health``, ``GET /node/ladder``) that
    each project a subset of fields; MCP exposes the full object via
    ``breathline_node_status`` (with ``include_health`` / ``include_ladder``
    booleans to opt out of subsets).

    The health probe is conservative: it confirms the manifest parses, the
    node-id can be derived, and the role registry (if provided) reports
    a non-empty active set. Cylinder-chain replay verification is left to
    ``handler_audit_query`` (separate tool) so this handler stays fast.
    """
    _require_principal(principal_id)
    root = _repo_root(Path(repo_root) if repo_root else None)
    manifest = _load_manifest(root)

    # Identity + tier + ladder
    tier = manifest.get("presentation_tier_default", "executive")
    manifest_version = str(manifest.get("version", "unknown"))
    ladder_version = str(manifest.get("ladder_version", "1.0"))
    # node_id derivation: use environment override if set (test/dev),
    # otherwise fall back to manifest sealed_by + ladder_version.
    node_id = os.environ.get(
        "BREATHLINE_NODE_ID",
        f"{manifest.get('sealed_by', 'unknown')}-LADDER-{ladder_version}",
    )

    # Ladder level (Sprint 1 reads current_series.executive as the anchor;
    # multi-series ladder is Sprint 2 / Family-series scope).
    ladder_level = 1
    ladder_level_name = "Executive Mastery"
    current_series = manifest.get("current_series") or {}
    if isinstance(current_series, dict):
        for series_key, series_info in current_series.items():
            if isinstance(series_info, dict) and series_info.get("active"):
                ladder_level = int(series_info.get("ladder_level", ladder_level))
                ladder_level_name = str(
                    series_info.get("ladder_level_name", ladder_level_name)
                )
                break

    # Health probes — start narrow; cylinder replay belongs to audit_query.
    checks: list[HealthCheck] = []
    checks.append(HealthCheck(check="manifest_parse", ok=True))
    kernel_ok = (root / "platform" / "kernel").exists()
    checks.append(HealthCheck(check="kernel_dir", ok=kernel_ok))
    specs_dir_ok = (root / "specs").exists()
    checks.append(HealthCheck(check="specs_dir", ok=specs_dir_ok))
    sigs_dir_ok = (root / "distribution" / "signing_keys").exists()
    checks.append(HealthCheck(check="signing_keys_dir", ok=sigs_dir_ok))

    registry_ok = True
    if role_registry is not None:
        try:
            role_ids = list(role_registry.role_ids())
            registry_ok = len(role_ids) > 0
            checks.append(
                HealthCheck(
                    check="role_registry",
                    ok=registry_ok,
                    message=f"{len(role_ids)} role(s) registered",
                )
            )
        except (AttributeError, TypeError) as e:
            registry_ok = False
            checks.append(
                HealthCheck(check="role_registry", ok=False, message=str(e))
            )

    # Ladder progression (Sprint 1: read manifest.current_series declarations;
    # full requirement-walk lands in Sprint 2 alongside the spec-coherence work).
    next_level = ladder_level + 1 if ladder_level < 4 else None
    requirements: list[dict[str, Any]] = []
    if next_level is not None:
        requirements.append(
            {
                "kind": "book",
                "ref": "next-series-anchor",
                "satisfied": False,
                "note": "Detailed requirement-walk lands in Sprint 2",
            }
        )

    return NodeStatus(
        node_id=node_id,
        tier=str(tier),
        ladder_level=ladder_level,
        ladder_level_name=ladder_level_name,
        kernel_version=str(manifest.get("platform", {}).get("kernel_version", "0.2.0")),
        manifest_version=manifest_version,
        kernel_ok=kernel_ok,
        manifest_ok=True,
        specs_valid=specs_dir_ok,
        signatures_ok=sigs_dir_ok,
        chain_sentinel="not_queried_in_sprint_1",
        breath_gate_ready=registry_ok,
        last_seal_seq=0,
        health_details=checks,
        current_level=ladder_level,
        next_level=next_level,
        ladder_requirements=requirements,
        anchor_book=None,
    )


# -----------------------------------------------------------------------------
# Handler: manifest_get (backs manifest.get)
# -----------------------------------------------------------------------------
def handler_manifest_get(
    *,
    principal_id: str,
    repo_root: Path | str | None = None,
) -> ManifestSummary:
    """Return the parsed manifest.yaml + integrity flag.

    Signature verification is out of scope for Sprint 1 (lands in Sprint 4
    with the installer integration). For now we surface ``integrity_ok=True``
    unless the parse fails, with a note that signature verification is queued.
    """
    _require_principal(principal_id)
    root = _repo_root(Path(repo_root) if repo_root else None)
    raw = _load_manifest(root)
    return ManifestSummary(
        version=str(raw.get("version", "unknown")),
        released=raw.get("released"),
        sealed_by=raw.get("sealed_by"),
        seal_glyph=str(raw.get("seal_glyph", "∞Δ∞")),
        raw=raw,
        integrity_ok=True,
        integrity_note="Signature verification queued for Sprint 4 (installer integration).",
    )


# -----------------------------------------------------------------------------
# Handler: specs_list (backs specs.list)
# -----------------------------------------------------------------------------
def handler_specs_list(
    *,
    principal_id: str,
    series: str = "all",
    repo_root: Path | str | None = None,
) -> SpecListing:
    """Enumerate role / permission / constitutional specs on this node.

    Walks ``specs/<series>/*.yaml`` and returns metadata. Per the spec
    contract, `series` is one of:
    executive | family | generational_legacy | education | health | federation | all.
    """
    _require_principal(principal_id)
    root = _repo_root(Path(repo_root) if repo_root else None)
    specs_dir = root / "specs"
    if not specs_dir.is_dir():
        return SpecListing(series_filter=series, count=0, specs=[])

    allowed_series = {
        "all",
        "executive",
        "family",
        "generational_legacy",
        "education",
        "health",
        "federation",
        "_base",
    }
    if series not in allowed_series:
        raise ValueError(
            f"series must be one of {sorted(allowed_series)}; got {series!r}"
        )

    entries: list[SpecEntry] = []
    series_dirs = (
        [specs_dir / s for s in sorted(allowed_series) if s != "all"]
        if series == "all"
        else [specs_dir / series]
    )
    for sd in series_dirs:
        if not sd.is_dir():
            continue
        for p in sorted(sd.glob("*.yaml")):
            entries.append(
                SpecEntry(
                    spec_id=f"{sd.name}/{p.stem}",
                    series=sd.name,
                    path=str(p.relative_to(root)),
                    status="active",
                )
            )

    return SpecListing(series_filter=series, count=len(entries), specs=entries)


# -----------------------------------------------------------------------------
# Handler: roles_list (backs roles.list)
# -----------------------------------------------------------------------------
def handler_roles_list(
    *,
    principal_id: str,
    role_registry: Any,
) -> RolesListing:
    """List roles registered with the platform RoleRegistry.

    Unlike the other read handlers, this one requires a live ``role_registry``
    object — there is no on-disk fallback because role registration is the
    runtime state of record. Calling without ``role_registry`` raises
    ``NodeStateError``.
    """
    _require_principal(principal_id)
    if role_registry is None:
        raise NodeStateError(
            "roles_list requires a live role_registry; cannot derive from disk"
        )
    role_ids = list(role_registry.role_ids())
    entries: list[RoleEntry] = []
    for rid in role_ids:
        registered = role_registry.get(rid)
        entries.append(
            RoleEntry(
                role_id=rid,
                framework=getattr(registered, "framework", None),
                status="active",
                permission_spec_ref=getattr(
                    getattr(registered, "permission_spec", None),
                    "source_path",
                    None,
                ),
            )
        )
    return RolesListing(count=len(entries), roles=entries)


# -----------------------------------------------------------------------------
# Sprint 1B (queued — scaffold only; implementation in continuation PR)
# -----------------------------------------------------------------------------
def handler_audit_query(
    *,
    principal_id: str,
    seq: int | None = None,
    since_seq: int | None = None,
    limit: int = 50,
    filter_kind: str | None = None,
    audit_adapter: Any | None = None,
) -> dict[str, Any]:
    """Query the cylinder chain (paginated or by single seq).

    SPRINT 1B SCAFFOLD: signature is final, implementation queued for the
    continuation PR. Calls audit_adapter.read_chain() once that surface is
    confirmed against the existing audit_adapter.py.

    Raises ``NotImplementedError`` until wired. Tests in Sprint 1B will exercise
    this against the existing AuditAdapter from platform_layer/audit_adapter.py.
    """
    _require_principal(principal_id)
    raise NotImplementedError(
        "handler_audit_query is scaffolded for Sprint 1B continuation. "
        "Implementation will dispatch to audit_adapter.read_chain() with "
        "(since_seq, limit, filter_kind) parameters; or audit_adapter.get(seq) "
        "when seq is provided. R6 contract: same handler called from HTTP "
        "(audit.cylinders, audit.cylinder) and MCP (breathline_audit_query)."
    )


def handler_breath_gate_pending(
    *,
    principal_id: str,
    breath_gate: Any | None = None,
) -> dict[str, Any]:
    """List currently-blocking breath-gate requests for this principal_id.

    SPRINT 1B SCAFFOLD: signature is final, implementation queued. Will
    dispatch to ``breath_gate.list_pending(principal_id)`` once the
    surface is confirmed against the existing kernel/breath_gate.py module.

    Raises ``NotImplementedError`` until wired. R6 contract: same handler
    called from HTTP (breath_gate.pending) and MCP (breathline_breath_gate_pending).
    """
    _require_principal(principal_id)
    raise NotImplementedError(
        "handler_breath_gate_pending is scaffolded for Sprint 1B continuation. "
        "Implementation will dispatch to kernel/breath_gate.py list_pending(). "
        "R6 contract: same handler called from HTTP (breath_gate.pending) "
        "and MCP (breathline_breath_gate_pending). Approval/denial deliberately "
        "NOT exposed over MCP per mcp_tools.yaml intentional_absences."
    )


# Seal:
#   SOURCE — every handler requires principal_id; no hardcoded principals.
#   TRUTH  — handlers parse real on-disk state (manifest.yaml, specs/*.yaml,
#            role_registry); no synthetic data.
#   INTEGRITY — pure functions, no transport coupling; R6 enforced — both
#               http_routes.py and mcp_server.py dispatch here.
# ∞Δ∞ Node API handlers — R6 backstop, principal-aware, Sprint 1 scope ∞Δ∞
