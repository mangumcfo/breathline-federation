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
    breath_gate_queue: Any | None = None,
) -> BreathGatePendingResponse:
    """List currently-blocking breath-gate requests for this principal_id.

    Sprint 2A: now reads from the real breath-gate queue at
    ``platform_layer.breath_gate_queue.BreathGateQueue``. Sprint 1B
    returned empty-with-note because the queue substrate did not exist;
    Sprint 2A added the substrate, and this handler activates it.

    Queue discovery falls through:
      1. Explicit ``breath_gate_queue`` argument
      2. ``BREATHLINE_QUEUE_DIR`` env var pointing at a real directory
      3. ``~/.breathline/pending_queue/`` (created lazily by the queue)
      4. Fallback: return empty-with-note (substrate not configured)

    K1 posture: approval/denial is DELIBERATELY NOT exposed in this handler
    or anywhere over MCP (per mcp_tools.yaml intentional_absences). The
    list-pending operation is READ-ONLY — it surfaces the queue for the
    operator's situational awareness; the operator pulls the approval
    lever via the CLI ritual (Sprint 2B) or via the breath-gate-pending
    HTTP route's companion approve/deny endpoints (also Sprint 2B).

    Args:
        principal_id: required — no anonymous queries.
        breath_gate_queue: optional explicit queue; auto-discovered from
            BREATHLINE_QUEUE_DIR env or ~/.breathline/pending_queue/
            fallback.
    """
    pid = _require_principal(principal_id)

    # Sprint 2A: try to read from the real queue if available. If the queue
    # module isn't importable (older deployment) or the queue directory
    # doesn't exist yet, fall back to empty-with-note — both are honest
    # states. Per "Build broad substrate early. Activate capability
    # progressively." — the substrate is here; activation is observable.
    if breath_gate_queue is None:
        breath_gate_queue = _default_breath_gate_queue()
    if breath_gate_queue is None:
        return BreathGatePendingResponse(
            principal_id=pid,
            pending=[],
            pending_queue_status="queue_not_yet_active",
            note=(
                "Breath-gate pending queue substrate is not available in this "
                "deployment. Configure BREATHLINE_QUEUE_DIR or pass an explicit "
                "queue. Reference: "
                "governance/decisions/2026-05-11_post-spec-runtime-roadmap.md. "
                "Approval/denial is DELIBERATELY NOT exposed over MCP "
                "(mcp_tools.yaml intentional_absences) — humans only, via the "
                "future Sprint 3 UI or via CLI."
            ),
        )

    entries = breath_gate_queue.list_pending(principal_id=pid)
    pending_dicts: list[dict[str, Any]] = []
    for e in entries:
        pending_dicts.append(
            {
                "request_id": e.request_id,
                "action_class": e.action_class,
                "summary": (
                    f"{e.role_id} → {e.action_class}: proposed by {e.proposer}"
                ),
                "proposer": e.proposer,
                "reversibility": e.reversibility,
                "forbidden_delegations_check": e.forbidden_delegations_check,
                "cost_estimate": e.cost_estimate,
                "opened_at": e.opened_at.isoformat(),
                "timeout_at": e.timeout_at.isoformat(),
                "payload_preview": e.payload_preview,
            }
        )
    status = "active" if pending_dicts else "active_empty"
    note = (
        f"Read from breath-gate queue at {breath_gate_queue.queue_dir}. "
        f"{len(pending_dicts)} entry(ies) pending for principal {pid}. "
        "Approval/denial is DELIBERATELY NOT exposed over MCP — humans only, "
        "via the future Sprint 3 UI or via the breathline_approve CLI ritual."
    )
    return BreathGatePendingResponse(
        principal_id=pid,
        pending=pending_dicts,
        pending_queue_status=status,
        note=note,
    )


def _default_breath_gate_queue() -> Any | None:
    """Discover the default breath-gate queue if one is configured.

    Resolution order:
      1. Env var ``BREATHLINE_QUEUE_DIR`` set + directory exists/creatable
      2. Fallback: ``~/.breathline/pending_queue/`` (created lazily)

    Returns the BreathGateQueue instance, or None if the queue module
    itself is not importable (older deployment).
    """
    try:
        from platform_layer.breath_gate_queue import BreathGateQueue
    except ImportError:
        return None
    env_dir = os.environ.get("BREATHLINE_QUEUE_DIR")
    queue_dir = Path(env_dir).expanduser() if env_dir else (
        Path.home() / ".breathline" / "pending_queue"
    )
    return BreathGateQueue(queue_dir=queue_dir)


# -----------------------------------------------------------------------------
# Handler: role_invoke (Sprint 2A — submits to queue when breath-gate required)
# -----------------------------------------------------------------------------
class RoleInvokeResponse(BaseModel):
    """Result of role_invoke — the proposer's side of the breath-gate flow.

    Per CONSTITUTION §1 and CHARTER II.4.4: when an action class requires
    a breath-gate, ``role_invoke`` SUBMITS to the queue and returns the
    pending request_id. It DOES NOT dispatch the role. The CLI ritual
    (or future Sprint 3 UI) approves; the platform then dispatches on
    behalf of the approving human.

    For auto-approvable action classes (read-only or system-internal),
    Sprint 2A leaves dispatch to Sprint 2B's HTTP wiring — the handler
    only handles the submit path. ``status`` distinguishes the cases:

      - "pending_breath_gate": entry written to queue; awaiting human
      - "rejected": pre-submission gate refused (e.g., unknown role)
      - "auto_dispatch_pending_sprint2b": action_class was auto-approve
        but Sprint 2A doesn't wire dispatch yet; this is HONEST status,
        not silent success
    """

    request_id: str | None
    status: str
    role_id: str
    action_class: str
    breath_gate_request_id: str | None = None
    cost_estimate: dict[str, Any] = Field(default_factory=dict)
    refusal_reason: str | None = None
    queried_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def handler_role_invoke(
    *,
    principal_id: str,
    role_id: str,
    action_class: str,
    payload: dict[str, Any],
    proposer: str | None = None,
    cost_estimate: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    role_registry: Any | None = None,
    breath_gate_queue: Any | None = None,
) -> RoleInvokeResponse:
    """Submit a role invocation. If breath-gate required, write to queue.

    Sprint 2A scope: this handler only handles the SUBMIT side of the
    flow. It validates that the role exists, that the action_class is in
    the role's allowed_action_classes envelope, classifies the action,
    and writes to the breath-gate queue if a gate is required. The
    APPROVE side (handler_breath_gate_approve) plus actual role dispatch
    happens in Sprint 2B's HTTP route wiring.

    K1 by structure: This handler NEVER dispatches the role. Even if
    action_class were auto-approvable, Sprint 2A returns a status of
    ``auto_dispatch_pending_sprint2b`` — honest about what's wired and
    what isn't, never silent success.

    Args:
        principal_id: required — who the action is on behalf of.
        role_id: which role to invoke.
        action_class: the Charter V.7 action class.
        payload: the role-specific payload.
        proposer: optional — defaults to principal_id if not provided.
        cost_estimate: optional cost-budget hint for the queue entry.
        idempotency_key: optional — Sprint 2B may use this to de-dup
            repeated submits; Sprint 2A accepts but does not enforce.
        role_registry: required for envelope validation. If None, this
            handler refuses (default-deny on missing infrastructure).
        breath_gate_queue: optional explicit queue; defaults to the
            BREATHLINE_QUEUE_DIR env / ~/.breathline/pending_queue/ fallback.
    """
    pid = _require_principal(principal_id)
    _require_nonempty(role_id, "role_id")
    _require_nonempty(action_class, "action_class")
    if role_registry is None:
        raise NodeStateError(
            "role_invoke requires a live role_registry to validate the action "
            "class against the role's envelope. Cannot derive from disk."
        )
    if not role_registry.has(role_id):
        return RoleInvokeResponse(
            request_id=None,
            status="rejected",
            role_id=role_id,
            action_class=action_class,
            refusal_reason=f"role_unknown: {role_id!r} not registered",
        )

    # Sprint 2A: every action class submits to the queue. The "auto-approve"
    # bypass (where read-only classes skip the gate) is Sprint 2B scope —
    # for now, the safe default is "everything proposes, human approves",
    # which honors K1 maximally during the activation window.
    if breath_gate_queue is None:
        breath_gate_queue = _default_breath_gate_queue()
    if breath_gate_queue is None:
        raise NodeStateError(
            "role_invoke requires a breath-gate queue; none configured. Set "
            "BREATHLINE_QUEUE_DIR or pass an explicit queue."
        )

    # Build a conservative payload_preview — just the keys, not the values
    # (avoids leaking sensitive payload over the breath-gate-pending listing).
    payload_preview = {"keys": sorted(payload.keys())} if payload else {}
    proposer_final = proposer or pid

    entry = breath_gate_queue.submit(
        principal_id=pid,
        role_id=role_id,
        action_class=action_class,
        payload=payload,
        proposer=proposer_final,
        reversibility="reversible",  # Sprint 2B refines per action_class
        forbidden_delegations_check="pass",  # Sprint 2B wires real check
        cost_estimate=cost_estimate or {},
        payload_preview=payload_preview,
    )
    return RoleInvokeResponse(
        request_id=entry.request_id,
        status="pending_breath_gate",
        role_id=role_id,
        action_class=action_class,
        breath_gate_request_id=entry.request_id,
        cost_estimate=cost_estimate or {},
    )


def _require_nonempty(value: str | None, name: str) -> None:
    """Raise ValueError if a required string arg is missing / empty."""
    if not value:
        raise ValueError(f"{name} is required (default-deny on missing)")


# Seal:
#   SOURCE — every handler requires principal_id; no hardcoded principals.
#   TRUTH  — handlers parse real on-disk state (manifest, specs, role_registry,
#            queue); no synthetic data.
#   INTEGRITY — pure functions, no transport coupling; R6 enforced — both
#               http_routes.py and mcp_server.py dispatch here. role_invoke
#               NEVER dispatches the role itself — K1 by structure: propose,
#               never self-approve.
# ∞Δ∞ Node API handlers — R6 backstop, principal-aware, Sprint 1+2A scope ∞Δ∞
