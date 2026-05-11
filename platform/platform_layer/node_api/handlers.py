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
# Sprint 1B response models
# -----------------------------------------------------------------------------
class CylinderResponse(BaseModel):
    """Single cylinder projected from audit_adapter.CylinderRef."""

    seq: int
    filename: str
    hash_prefix: str
    prev_hash_prefix: str
    timestamp: str
    is_encoded: bool
    has_traceback: bool
    kind: str | None = None  # parsed from filename suffix if present


class ChainIntegritySummary(BaseModel):
    """Light projection of audit_adapter.ChainReplayReport for query responses.

    The full replay report carries diagnostic state (hash_breaks, seq_gaps,
    every CylinderRef). The query response carries a summary so callers can
    paginate without re-pulling the entire chain on every page.
    """

    total: int
    encoded: int
    freeform: int
    tracebacks: int
    hash_breaks_count: int
    seq_gaps_count: int
    genesis_seq: int | None = None
    tip_seq: int | None = None


class AuditChainQuery(BaseModel):
    """Result of audit_query — paginated subset of the cylinder chain.

    R6 contract: same handler called from HTTP (audit.cylinders /
    audit.cylinder) and MCP (breathline_audit_query). The response shape
    is identical across transports.
    """

    total_in_chain: int
    returned_count: int
    since_seq: int | None = None
    limit: int
    filter_kind: str | None = None
    cylinders: list[CylinderResponse] = Field(default_factory=list)
    chain_integrity: ChainIntegritySummary
    queried_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BreathGatePendingResponse(BaseModel):
    """Result of breath_gate_pending — currently-blocking breath-gate requests.

    Per Lumen witness review (PR #18, 2026-05-11): the pending-queue
    mechanism the contract anticipates lands alongside Sprint 2's
    role-invocation tools — kernel/breath_gate.py today is a synchronous
    CLI ritual (Phase 1) with no pending queue. This handler is correctly
    implemented for Sprint 1B as returning an empty pending list with a
    status field; Sprint 2's role-invocation will populate it.
    """

    principal_id: str
    pending: list[dict[str, Any]] = Field(default_factory=list)
    pending_queue_status: str
    note: str
    queried_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# -----------------------------------------------------------------------------
# Handler: audit_query (backs audit.cylinders + audit.cylinder)
# -----------------------------------------------------------------------------
def _resolve_cylinders_dir(cylinders_dir: Path | str | None = None) -> Path:
    """Discover the cylinders directory.

    Resolution order:
      1. Explicit ``cylinders_dir`` argument (caller knows the location)
      2. Env var ``BREATHLINE_CYLINDERS_DIR``
      3. Fallback: ``$HOME/Tiger_1a/cylinders`` (the existing dev default
         used by ``audit_adapter.DEFAULT_SEAL_SH``)

    Raises NodeStateError if no usable directory is found.
    """
    if cylinders_dir is not None:
        p = Path(cylinders_dir).expanduser().resolve()
        if not p.is_dir():
            raise NodeStateError(
                f"cylinders_dir is not a directory: {p}"
            )
        return p
    env_dir = os.environ.get("BREATHLINE_CYLINDERS_DIR")
    if env_dir:
        p = Path(env_dir).expanduser().resolve()
        if not p.is_dir():
            raise NodeStateError(
                f"BREATHLINE_CYLINDERS_DIR is set but not a directory: {p}"
            )
        return p
    fallback = Path.home() / "Tiger_1a" / "cylinders"
    if fallback.is_dir():
        return fallback
    raise NodeStateError(
        "Could not locate a cylinders directory. "
        f"Tried explicit arg (None), env BREATHLINE_CYLINDERS_DIR (unset), "
        f"and fallback {fallback} (not a directory). Configure one of the above."
    )


def _parse_cylinder_kind(filename: str) -> str | None:
    """Parse a cylinder's optional kind suffix from its filename.

    Filenames have the shape ``capture_YYYYMMDD_HHMMSS[_<kind>].cyl`` per
    the regex in audit_adapter.py. The optional kind suffix is what we
    surface as the cylinder's 'kind' field. Returns None for filenames
    without a kind suffix.
    """
    if not filename.endswith(".cyl"):
        return None
    stem = filename[: -len(".cyl")]
    parts = stem.split("_")
    # Expect at least: ["capture", "<8 digits>", "<6 digits>", ...]
    if len(parts) < 3:
        return None
    if len(parts) == 3:
        return None  # No kind suffix
    return "_".join(parts[3:])


def _project_cylinder(ref: Any) -> CylinderResponse:
    """Project an audit_adapter.CylinderRef to our response model."""
    return CylinderResponse(
        seq=ref.sequence,
        filename=ref.filename,
        hash_prefix=ref.hash_prefix,
        prev_hash_prefix=ref.prev_hash_prefix,
        timestamp=ref.timestamp,
        is_encoded=ref.is_encoded,
        has_traceback=ref.has_traceback,
        kind=_parse_cylinder_kind(ref.filename),
    )


def handler_audit_query(
    *,
    principal_id: str,
    seq: int | None = None,
    since_seq: int | None = None,
    limit: int = 50,
    filter_kind: str | None = None,
    cylinders_dir: Path | str | None = None,
) -> AuditChainQuery:
    """Query the cylinder chain — paginated or by single seq.

    Backs the contract endpoints audit.cylinders (paginated) and
    audit.cylinder (single seq when ``seq`` is provided).

    Per R6: same handler exercised from HTTP (audit/cylinders, audit/cylinder
    routes in http_routes.py) and MCP (breathline_audit_query tool in
    mcp_server.py).

    Args:
        principal_id: required — no anonymous queries.
        seq: when provided, return the single cylinder at that sequence.
            ``since_seq``, ``limit``, ``filter_kind`` are ignored for the
            seq-filter step but still validated for shape.
        since_seq: when provided (and ``seq`` is None), return cylinders
            with sequence > since_seq.
        limit: max cylinders to return (default 50, max 500).
        filter_kind: optional case-insensitive substring match against the
            kind suffix parsed from filenames.
        cylinders_dir: explicit path to cylinders directory; otherwise
            falls back to env var or default per ``_resolve_cylinders_dir``.

    Raises:
        MissingPrincipalError: principal_id not provided.
        NodeStateError: cylinders directory cannot be located or the
            chain replay fails fundamentally.
        ValueError: when ``limit`` is outside [1, 500] or both ``seq`` and
            ``since_seq`` are provided.
    """
    _require_principal(principal_id)
    if seq is not None and since_seq is not None:
        raise ValueError(
            "Provide either seq (single-cylinder lookup) or since_seq "
            "(paginated query), not both."
        )
    if limit < 1 or limit > 500:
        raise ValueError(f"limit must be in [1, 500]; got {limit}")

    # Lazy import — audit_adapter pulls in subprocess machinery for seal()
    # that we don't need for read-only queries; keeping the import scoped
    # here avoids dragging that surface into module-import time.
    try:
        from platform_layer.audit_adapter import (
            ChainReplayError,
            replay_chain,
        )
    except ImportError as e:
        raise NodeStateError(
            f"audit_adapter module not importable: {e}"
        ) from e

    cyl_dir = _resolve_cylinders_dir(cylinders_dir)
    try:
        report = replay_chain(cyl_dir)
    except ChainReplayError as e:
        raise NodeStateError(f"chain replay failed: {e}") from e

    integrity = ChainIntegritySummary(
        total=report.total,
        encoded=report.encoded,
        freeform=report.freeform,
        tracebacks=report.tracebacks,
        hash_breaks_count=len(report.hash_breaks),
        seq_gaps_count=len(report.seq_gaps),
        genesis_seq=report.genesis_seq,
        tip_seq=report.tip_seq,
    )

    all_refs = report.cylinders_in_order
    if seq is not None:
        matches = [r for r in all_refs if r.sequence == seq]
        if not matches:
            return AuditChainQuery(
                total_in_chain=report.total,
                returned_count=0,
                limit=limit,
                cylinders=[],
                chain_integrity=integrity,
            )
        return AuditChainQuery(
            total_in_chain=report.total,
            returned_count=1,
            limit=limit,
            cylinders=[_project_cylinder(matches[0])],
            chain_integrity=integrity,
        )

    # Paginated query: filter then limit
    filtered = all_refs
    if since_seq is not None:
        filtered = [r for r in filtered if r.sequence > since_seq]
    if filter_kind is not None:
        needle = filter_kind.lower()
        filtered = [
            r for r in filtered
            if (_parse_cylinder_kind(r.filename) or "").lower().find(needle) != -1
        ]
    page = filtered[:limit]
    return AuditChainQuery(
        total_in_chain=report.total,
        returned_count=len(page),
        since_seq=since_seq,
        limit=limit,
        filter_kind=filter_kind,
        cylinders=[_project_cylinder(r) for r in page],
        chain_integrity=integrity,
    )


# -----------------------------------------------------------------------------
# Handler: breath_gate_pending (backs breath_gate.pending)
# -----------------------------------------------------------------------------
def handler_breath_gate_pending(
    *,
    principal_id: str,
    breath_gate: Any | None = None,
) -> BreathGatePendingResponse:
    """List currently-blocking breath-gate requests for this principal_id.

    Per Lumen witness review of PR #18 (2026-05-11): kernel/breath_gate.py
    today is a Phase 1 synchronous CLI ritual — there is no pending queue.
    The pending-queue mechanism the contract anticipates lands alongside
    Sprint 2's role-invocation tools (because role.invoke → propose-to-
    queue is what populates the pending list).

    For Sprint 1B, this handler is correctly implemented as:

      - Returns an empty pending list (no queue exists yet to read from)
      - Returns ``pending_queue_status`` = ``"queue_not_yet_active"``
      - Returns a note explaining the architecture and pointing at when it
        becomes meaningfully populated

    This is NOT a stub. The handler is the right shape for the contract;
    it returns honest state. When Sprint 2's role-invocation lands and
    creates pending entries, the handler signature is forward-compatible.

    K1 posture: approval/denial is DELIBERATELY NOT exposed in this handler
    or anywhere over MCP (per mcp_tools.yaml intentional_absences).

    Args:
        principal_id: required — no anonymous queries.
        breath_gate: reserved for Sprint 2 wiring; ignored in Sprint 1B.
    """
    pid = _require_principal(principal_id)
    return BreathGatePendingResponse(
        principal_id=pid,
        pending=[],
        pending_queue_status="queue_not_yet_active",
        note=(
            "Breath-gate pending queue is not yet populated. The current "
            "kernel/breath_gate.py is a Phase 1 synchronous CLI ritual; "
            "the persistent pending-queue mechanism the contract anticipates "
            "lands alongside Sprint 2's role-invocation tools. Reference: "
            "governance/decisions/2026-05-11_post-spec-runtime-roadmap.md. "
            "Approval/denial is DELIBERATELY NOT exposed over MCP "
            "(mcp_tools.yaml intentional_absences) — humans only, via the "
            "future Sprint 3 UI or via CLI."
        ),
    )


# Seal:
#   SOURCE — every handler requires principal_id; no hardcoded principals.
#   TRUTH  — handlers parse real on-disk state (manifest.yaml, specs/*.yaml,
#            role_registry); no synthetic data.
#   INTEGRITY — pure functions, no transport coupling; R6 enforced — both
#               http_routes.py and mcp_server.py dispatch here.
# ∞Δ∞ Node API handlers — R6 backstop, principal-aware, Sprint 1 scope ∞Δ∞
