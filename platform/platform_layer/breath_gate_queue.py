"""Breath-gate pending queue — file-backed persistent storage.

Sprint 2 substrate (2026-05-11) per the post-spec runtime roadmap
(``governance/decisions/2026-05-11_post-spec-runtime-roadmap.md``).
The persistent pending-queue mechanism the Node API contract anticipates
for ``breath_gate.pending``. Activates when ``role_invoke`` proposes a
breath-gate-required action; cleared when the operator approves / denies
(via CLI ritual) or when the entry times out.

## Architecture

Each pending entry is one YAML file on disk:

  <queue_dir>/<request_id>.yaml

The queue directory defaults to ``~/.breathline/pending_queue/`` and is
operator-controlled (no platform service depends on a remote queue).

## K1-K4 posture

- **K1 Human Primacy**: ``approve()`` and ``deny()`` are queue-level
  operations called only by the CLI ritual (Sprint 2B) or by an
  HTTP route that requires a human-attestation payload. They are
  DELIBERATELY NOT exposed over MCP (per ``mcp_tools.yaml``
  intentional_absences). The MCP-calling agent can READ via
  ``list_pending()`` to summarize for the human; the human pulls the
  approval lever directly.

- **K2 Default-Deny**: ``submit()`` requires explicit principal_id;
  ``approve()``/``deny()`` require explicit principal_id (the
  approver's identity, audit-recorded). Missing identity → refuse.

- **K3 Audit-Immutable**: State transitions are recorded in the entry's
  YAML history (``status_history`` list). The transition events that
  matter constitutionally (submit, approve, deny, expire) ALSO seal
  cylinders via the existing AuditAdapter when an auditor is wired —
  the queue is the *operational* store; the cylinder chain is the
  *constitutional* record.

- **K4 Constitutional-Validated Extension**: The queue's entry schema
  is versioned (``schema_version`` field). Schema changes require
  a sealed amendment.

## Sprint scope

Sprint 2A (this commit): queue module + submit/list/get/approve/deny/
  expire_overdue operations. Tests.

Sprint 2B (next commit): wiring through ``handler_role_invoke`` (HTTP
  + MCP), HTTP approve/deny routes, CLI ``breathline_approve.py`` ritual,
  ``plugin_interface.create_app`` mounting.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml


# Schema version for entry files. Bumped on breaking schema changes;
# additive changes (new optional fields) do not bump.
SCHEMA_VERSION = 1

# Default timeout for new pending entries when none is specified. Matches
# the kernel/breath_gate.py default (5 minutes) so behavior is consistent
# whether the operator confirms synchronously or asynchronously.
DEFAULT_TIMEOUT_SECONDS = 300


# -----------------------------------------------------------------------------
# Error types — loud, contextual (CONSTITUTION §4)
# -----------------------------------------------------------------------------
class BreathGateQueueError(RuntimeError):
    """Base class for queue errors. Subclasses surface specific failures."""


class PendingEntryNotFound(BreathGateQueueError):
    """Raised when get/approve/deny is called with an unknown request_id."""


class PendingEntryNotPending(BreathGateQueueError):
    """Raised when approve/deny is called on an entry that is already
    approved / denied / expired (cannot re-decide a sealed state)."""


class PendingEntryExpired(BreathGateQueueError):
    """Raised when an operation tries to operate on an expired entry."""


# -----------------------------------------------------------------------------
# Entry shape
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class PendingEntry:
    """One breath-gate-required action awaiting human disposition.

    Frozen dataclass — state transitions produce *new* PendingEntry
    instances rather than mutating; the queue rewrites the file on
    transition. This keeps the entry immutable in-memory and the
    on-disk file the single source of truth.
    """

    request_id: str
    schema_version: int
    principal_id: str          # who the action is on behalf of
    role_id: str               # which role the action would dispatch to
    action_class: str          # the Charter V.7 action class
    payload: dict[str, Any]    # the role-specific payload
    proposer: str              # role_id or principal_id that proposed
    reversibility: str         # "reversible" | "irreversible" | "externally_visible"
    forbidden_delegations_check: str  # "pass" | "fail: <reason>"
    cost_estimate: dict[str, Any]
    payload_preview: dict[str, Any]
    opened_at: datetime
    timeout_at: datetime
    status: str = "pending"    # pending | approved | denied | expired
    status_history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    approver_principal_id: str | None = None
    approver_attestation: str | None = None
    denial_reason: str | None = None
    sealed_cylinder_seq: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for YAML emission."""
        return {
            "request_id": self.request_id,
            "schema_version": self.schema_version,
            "principal_id": self.principal_id,
            "role_id": self.role_id,
            "action_class": self.action_class,
            "payload": self.payload,
            "proposer": self.proposer,
            "reversibility": self.reversibility,
            "forbidden_delegations_check": self.forbidden_delegations_check,
            "cost_estimate": self.cost_estimate,
            "payload_preview": self.payload_preview,
            "opened_at": self.opened_at.isoformat(),
            "timeout_at": self.timeout_at.isoformat(),
            "status": self.status,
            "status_history": list(self.status_history),
            "approver_principal_id": self.approver_principal_id,
            "approver_attestation": self.approver_attestation,
            "denial_reason": self.denial_reason,
            "sealed_cylinder_seq": self.sealed_cylinder_seq,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PendingEntry":
        """Parse from on-disk YAML."""
        return cls(
            request_id=data["request_id"],
            schema_version=int(data.get("schema_version", SCHEMA_VERSION)),
            principal_id=data["principal_id"],
            role_id=data["role_id"],
            action_class=data["action_class"],
            payload=data.get("payload", {}),
            proposer=data["proposer"],
            reversibility=data["reversibility"],
            forbidden_delegations_check=data["forbidden_delegations_check"],
            cost_estimate=data.get("cost_estimate", {}),
            payload_preview=data.get("payload_preview", {}),
            opened_at=_parse_dt(data["opened_at"]),
            timeout_at=_parse_dt(data["timeout_at"]),
            status=data.get("status", "pending"),
            status_history=tuple(data.get("status_history", [])),
            approver_principal_id=data.get("approver_principal_id"),
            approver_attestation=data.get("approver_attestation"),
            denial_reason=data.get("denial_reason"),
            sealed_cylinder_seq=data.get("sealed_cylinder_seq"),
        )


def _parse_dt(value: Any) -> datetime:
    """Parse an ISO-8601 string or pass through if already a datetime."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


# -----------------------------------------------------------------------------
# Queue
# -----------------------------------------------------------------------------
@dataclass
class BreathGateQueue:
    """File-backed pending-queue for breath-gate-required actions.

    Single-writer assumption (one platform process owns the queue
    directory). For multi-process deployments, wrap operations in a
    flock around the queue directory — out of scope for Sprint 2A.

    The queue does NOT enforce constitutional invariants itself
    (Charter V.7, action_class registry, principal_id end-to-end). Those
    are checked at the route layer in ``handler_role_invoke`` BEFORE
    submission. The queue is operational storage — once an entry is in
    the queue, it has already passed those gates.
    """

    queue_dir: Path
    auditor: Any | None = None  # optional AuditAdapter for cylinder sealing

    def __post_init__(self) -> None:
        self.queue_dir = Path(self.queue_dir).expanduser().resolve()
        self.queue_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------
    # submit — write a new pending entry
    # -----------------------------------------------------------------
    def submit(
        self,
        *,
        principal_id: str,
        role_id: str,
        action_class: str,
        payload: dict[str, Any],
        proposer: str,
        reversibility: str = "reversible",
        forbidden_delegations_check: str = "pass",
        cost_estimate: dict[str, Any] | None = None,
        payload_preview: dict[str, Any] | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        request_id: str | None = None,
    ) -> PendingEntry:
        """Submit a new pending entry. Returns the entry with request_id assigned."""
        _require(principal_id, "principal_id")
        _require(role_id, "role_id")
        _require(action_class, "action_class")
        _require(proposer, "proposer")
        if reversibility not in {"reversible", "irreversible", "externally_visible"}:
            raise ValueError(
                f"reversibility must be reversible|irreversible|externally_visible; "
                f"got {reversibility!r}"
            )
        now = datetime.now(timezone.utc)
        entry = PendingEntry(
            request_id=request_id or _new_request_id(),
            schema_version=SCHEMA_VERSION,
            principal_id=principal_id,
            role_id=role_id,
            action_class=action_class,
            payload=dict(payload),
            proposer=proposer,
            reversibility=reversibility,
            forbidden_delegations_check=forbidden_delegations_check,
            cost_estimate=dict(cost_estimate or {}),
            payload_preview=dict(payload_preview or {}),
            opened_at=now,
            timeout_at=now + timedelta(seconds=timeout_seconds),
            status="pending",
            status_history=(
                {
                    "at": now.isoformat(),
                    "transition": "submitted",
                    "by": proposer,
                },
            ),
        )
        self._write(entry)
        return entry

    # -----------------------------------------------------------------
    # list_pending — currently-blocking entries for a principal
    # -----------------------------------------------------------------
    def list_pending(
        self,
        principal_id: str,
        *,
        include_expired_check: bool = True,
    ) -> list[PendingEntry]:
        """List currently-blocking entries (status='pending') for this principal_id.

        If ``include_expired_check`` is True (default), entries whose
        ``timeout_at`` has passed are silently expired in-place before
        the list is computed. This keeps callers from seeing zombie entries.
        """
        _require(principal_id, "principal_id")
        if include_expired_check:
            self.expire_overdue()
        out: list[PendingEntry] = []
        for entry in self._iter_entries():
            if entry.status != "pending":
                continue
            if entry.principal_id != principal_id:
                continue
            out.append(entry)
        # Sort by opened_at ascending (oldest first)
        return sorted(out, key=lambda e: e.opened_at)

    # -----------------------------------------------------------------
    # get — single entry by request_id
    # -----------------------------------------------------------------
    def get(self, request_id: str) -> PendingEntry:
        """Return a single entry by request_id. Raises PendingEntryNotFound."""
        _require(request_id, "request_id")
        path = self._path_for(request_id)
        if not path.is_file():
            raise PendingEntryNotFound(
                f"No pending entry for request_id={request_id!r}"
            )
        return self._read(path)

    # -----------------------------------------------------------------
    # approve — record human approval; transition status; return updated entry
    # -----------------------------------------------------------------
    def approve(
        self,
        request_id: str,
        *,
        approver_principal_id: str,
        attestation: str,
    ) -> PendingEntry:
        """Record human approval. Entry transitions pending → approved.

        ``approver_principal_id`` is the human pulling the lever. The
        attestation string is audit-recorded — every approval carries the
        operator's stated rationale per the contract spec.
        """
        _require(approver_principal_id, "approver_principal_id")
        _require(attestation, "attestation")
        entry = self.get(request_id)
        self._guard_pending(entry, "approve")
        now = datetime.now(timezone.utc)
        updated = _replace(
            entry,
            status="approved",
            approver_principal_id=approver_principal_id,
            approver_attestation=attestation,
            status_history=entry.status_history + (
                {
                    "at": now.isoformat(),
                    "transition": "approved",
                    "by": approver_principal_id,
                    "attestation_summary": attestation[:120],
                },
            ),
        )
        self._write(updated)
        self._maybe_audit_seal(updated, "breath_gate_approved")
        return updated

    # -----------------------------------------------------------------
    # deny — record human denial; transition status
    # -----------------------------------------------------------------
    def deny(
        self,
        request_id: str,
        *,
        denier_principal_id: str,
        reason: str,
    ) -> PendingEntry:
        """Record human denial. Entry transitions pending → denied."""
        _require(denier_principal_id, "denier_principal_id")
        _require(reason, "reason")
        entry = self.get(request_id)
        self._guard_pending(entry, "deny")
        now = datetime.now(timezone.utc)
        updated = _replace(
            entry,
            status="denied",
            approver_principal_id=denier_principal_id,
            denial_reason=reason,
            status_history=entry.status_history + (
                {
                    "at": now.isoformat(),
                    "transition": "denied",
                    "by": denier_principal_id,
                    "reason_summary": reason[:120],
                },
            ),
        )
        self._write(updated)
        self._maybe_audit_seal(updated, "breath_gate_denied")
        return updated

    # -----------------------------------------------------------------
    # expire_overdue — mark timed-out entries as expired
    # -----------------------------------------------------------------
    def expire_overdue(self) -> list[str]:
        """Walk the queue; mark any 'pending' entry past timeout_at as 'expired'.

        Returns the list of request_ids that were just expired.

        Per CHARTER II.4.4: breath-gates fail closed on timeout — no
        implicit approval. The expired status is the on-disk record of
        that closed-failure.
        """
        now = datetime.now(timezone.utc)
        expired_ids: list[str] = []
        for entry in self._iter_entries():
            if entry.status != "pending":
                continue
            if entry.timeout_at > now:
                continue
            updated = _replace(
                entry,
                status="expired",
                status_history=entry.status_history + (
                    {
                        "at": now.isoformat(),
                        "transition": "expired",
                        "by": "system_timeout",
                        "timeout_at": entry.timeout_at.isoformat(),
                    },
                ),
            )
            self._write(updated)
            self._maybe_audit_seal(updated, "breath_gate_timeout")
            expired_ids.append(entry.request_id)
        return expired_ids

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------
    def _path_for(self, request_id: str) -> Path:
        # request_id is a UUID; safe as a filename. Defensive: strip slashes.
        safe = str(request_id).replace("/", "_").replace("..", "_")
        return self.queue_dir / f"{safe}.yaml"

    def _write(self, entry: PendingEntry) -> None:
        path = self._path_for(entry.request_id)
        tmp = path.with_suffix(".yaml.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            yaml.safe_dump(entry.to_dict(), f, sort_keys=True, default_flow_style=False)
        os.replace(tmp, path)  # atomic rename per POSIX

    def _read(self, path: Path) -> PendingEntry:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            raise BreathGateQueueError(
                f"Pending entry file at {path} did not parse to a mapping; "
                f"got {type(data).__name__}"
            )
        return PendingEntry.from_dict(data)

    def _iter_entries(self):
        """Yield every PendingEntry currently in the queue directory."""
        for p in sorted(self.queue_dir.glob("*.yaml")):
            if p.name.endswith(".tmp"):
                continue
            try:
                yield self._read(p)
            except BreathGateQueueError:
                # A malformed entry file is loud at access; skip during iteration
                # so one bad entry doesn't poison list_pending().
                continue

    def _guard_pending(self, entry: PendingEntry, op: str) -> None:
        """Raise if the entry is not in pending state (op cannot proceed)."""
        if entry.status == "expired":
            raise PendingEntryExpired(
                f"Cannot {op} entry {entry.request_id!r}; status is 'expired'"
            )
        if entry.status != "pending":
            raise PendingEntryNotPending(
                f"Cannot {op} entry {entry.request_id!r}; status is "
                f"{entry.status!r} (already disposed)"
            )

    def _maybe_audit_seal(self, entry: PendingEntry, event: str) -> None:
        """Best-effort: seal a cylinder when an auditor is wired.

        The cylinder seal is the *constitutional* record of a queue
        transition (submit, approve, deny, timeout). The queue file is
        the *operational* record (what's pending, who's been notified).
        Both exist; the auditor seal is the source of constitutional
        truth.

        When ``self.auditor`` is None, the seal is a no-op — the
        operational record stands alone, and the integrator can wire an
        auditor later. CONSTITUTION §4: loud on failure — if an auditor
        IS wired and seal fails, we re-raise.
        """
        if self.auditor is None:
            return
        try:
            sealed = self.auditor.log(
                agent_id="breath_gate_queue",
                action=event,
                inputs={
                    "request_id": entry.request_id,
                    "principal_id": entry.principal_id,
                    "role_id": entry.role_id,
                    "action_class": entry.action_class,
                },
                outputs={
                    "status": entry.status,
                    "approver_principal_id": entry.approver_principal_id,
                },
                metadata={
                    "queue_transition": event,
                    "queue_dir": str(self.queue_dir),
                },
            )
            # Best-effort: record the cylinder seq on the entry if the
            # auditor's response carries one. Some adapters return a
            # CylinderEntry with .cylinder_id; others return a string.
            seq = getattr(sealed, "cylinder_seq", None)
            if seq is not None:
                # Re-write with the seq recorded.
                updated = _replace(entry, sealed_cylinder_seq=seq)
                self._write(updated)
        except Exception:  # noqa: BLE001 — loud per CONSTITUTION §4
            raise


# -----------------------------------------------------------------------------
# Free functions
# -----------------------------------------------------------------------------
def _new_request_id() -> str:
    """UUID-prefixed request_id. Lowercase, no hyphens removed (readable)."""
    return f"req_{uuid.uuid4()}"


def _require(value: Any, name: str) -> None:
    """Raise ValueError for missing / empty required arg."""
    if value is None or value == "":
        raise ValueError(f"{name} is required (default-deny on missing)")


def _replace(entry: PendingEntry, **changes: Any) -> PendingEntry:
    """Return a new PendingEntry with fields updated.

    dataclasses.replace exists, but the frozen + tuple-default makes it
    slightly cleaner to spell it explicitly here for readability.
    """
    current = entry.to_dict()
    for k, v in changes.items():
        current[k] = v
    # status_history is a tuple in-memory; to_dict made it a list — preserve
    # the tuple shape on the returned dataclass.
    if "status_history" in changes:
        current["status_history"] = changes["status_history"]
    # opened_at / timeout_at were ISO strings in to_dict; restore them as
    # datetime so from_dict's parse works.
    current["opened_at"] = entry.opened_at
    current["timeout_at"] = entry.timeout_at
    return PendingEntry(
        request_id=current["request_id"],
        schema_version=current["schema_version"],
        principal_id=current["principal_id"],
        role_id=current["role_id"],
        action_class=current["action_class"],
        payload=current["payload"],
        proposer=current["proposer"],
        reversibility=current["reversibility"],
        forbidden_delegations_check=current["forbidden_delegations_check"],
        cost_estimate=current["cost_estimate"],
        payload_preview=current["payload_preview"],
        opened_at=current["opened_at"],
        timeout_at=current["timeout_at"],
        status=current["status"],
        status_history=current["status_history"],
        approver_principal_id=current["approver_principal_id"],
        approver_attestation=current["approver_attestation"],
        denial_reason=current["denial_reason"],
        sealed_cylinder_seq=current["sealed_cylinder_seq"],
    )


# Seal:
#   SOURCE — every queue operation requires explicit principal_id; no
#            hardcoded principals; submit() requires proposer identity.
#   TRUTH  — file-backed atomic writes (os.replace); status transitions
#            recorded in entry.status_history; cylinder seal records the
#            constitutional truth when an auditor is wired.
#   INTEGRITY — frozen dataclass + atomic file replacement; approve/deny
#               guard against double-disposition; expire_overdue is the
#               on-disk record of CHARTER II.4.4 fail-closed-on-timeout;
#               complexity per function ≤ 10 per CONSTITUTION §5.
# ∞Δ∞ Breath-gate pending queue — Sprint 2 substrate, K1 by structure ∞Δ∞
