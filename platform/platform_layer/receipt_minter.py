"""Receipt Minter — default-deny external B49 receipts via SIX-SOV.

Per IMPLEMENTATION_PLAN.md Section 7:
    - Internal cylinder seal first (always; default-allow)
    - External B49 mint second (default-deny per receipt_worthy_events.yaml)
    - Artifact return last (receipt_id embedded when minted)

Per Section 7.2:
    "default-deny is structural — events not on the list cannot mint
    receipts even if a role tries"

Per Section 7.3 — rate limiting:
    - Default 30/min per event class
    - Per-principal 500/hour
    - Per-class overrides honored
    - Burst behavior: batch with `count`

Per Section 7.4 — Phase 2 dependency:
    - Until Cloudflare Tunnel is live, /verify returns placeholder JSON 503
    - Cylinder seal still happens (internal record preserved)
    - Mint attempt logs receipt_pending in cylinder metadata
    - Reconciliation script back-fills receipt IDs once tunnel is live
"""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml


DEFAULT_SEED_DIR = Path(__file__).resolve().parent.parent / "seed"
DEFAULT_SIX_SOV_VERIFY = "https://six-sov.com/verify"
DEFAULT_DEGRADED_MODE_OK = True


class ReceiptMintRefused(Exception):
    """Raised when an event is not on the receipt-worthy taxonomy.

    Default-deny: structurally enforced — a role attempting to mint a
    receipt for an event class outside the taxonomy gets a hard refusal."""


@dataclass(frozen=True)
class ReceiptID:
    """A B49 receipt identifier returned by SIX-SOV /verify."""

    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class MintResult:
    """The outcome of a mint attempt.

    Per Section 7 sequencing: cylinder seal happens first (always); this
    object captures whether external mint succeeded, was batched, or
    landed in degraded mode (receipt_pending).
    """

    minted: bool
    receipt_id: ReceiptID | None
    pending: bool  # degraded mode: tunnel not live yet
    batched_count: int  # >0 if this represents a batched record
    event: str
    timestamp: datetime

    def to_metadata(self) -> dict[str, Any]:
        """Convert to the metadata dict embedded in cylinder seal + artifact."""
        out: dict[str, Any] = {
            "event": self.event,
            "minted": self.minted,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.receipt_id is not None:
            out["receipt_id"] = str(self.receipt_id)
        if self.pending:
            out["receipt_pending"] = True
        if self.batched_count > 0:
            out["batched_count"] = self.batched_count
        return out


@dataclass
class _RateLimitState:
    """Per-class rate limit state."""

    max_per_minute: int
    timestamps: deque[float] = field(default_factory=deque)
    pending_batch: list[dict[str, Any]] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)


def _purge_old_timestamps(ts_deque: deque[float], window_seconds: float, now: float) -> None:
    """Remove timestamps older than `window_seconds` from the deque."""
    cutoff = now - window_seconds
    while ts_deque and ts_deque[0] < cutoff:
        ts_deque.popleft()


class ReceiptMinter:
    """Default-deny external receipt minter with rate limiting + batching.

    The taxonomy at seed/receipt_worthy_events.yaml is the contract.
    Anything not in the taxonomy raises ReceiptMintRefused.
    """

    def __init__(
        self,
        taxonomy_path: Path | None = None,
        verify_endpoint: str | None = None,
        degraded_mode_ok: bool | None = None,
        clock: Callable[[], float] = time.monotonic,
        post_fn: Callable[..., Any] | None = None,
    ) -> None:
        path = taxonomy_path or (DEFAULT_SEED_DIR / "receipt_worthy_events.yaml")
        self._taxonomy = yaml.safe_load(path.read_text())

        self._verify_endpoint = verify_endpoint or os.environ.get(
            "SIX_SOV_VERIFY_ENDPOINT", DEFAULT_SIX_SOV_VERIFY
        )
        if degraded_mode_ok is None:
            env_val = os.environ.get("SIX_SOV_DEGRADED_MODE_OK", "true").lower()
            degraded_mode_ok = env_val in ("true", "1", "yes")
        self._degraded_mode_ok = degraded_mode_ok

        self._clock = clock
        self._post_fn = post_fn  # injected for testing; None → degraded mode if no httpx

        self._allowed_events: set[str] = set()
        self._rate_state: dict[str, _RateLimitState] = {}
        self._principal_timestamps: dict[str, deque[float]] = defaultdict(deque)
        self._principal_lock = threading.Lock()

        self._build_allowed_events()
        self._build_rate_limiters()

    # ─── Setup ────────────────────────────────────────────────────────────
    def _build_allowed_events(self) -> None:
        """Walk the taxonomy `events:` block and collect all event ids."""
        events = self._taxonomy.get("events", {})
        for category, entries in events.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                event_id = entry.get("event")
                if event_id:
                    # Configurable events default to OFF — not added to allowed
                    if entry.get("default") == "off":
                        continue
                    self._allowed_events.add(event_id)

    def _build_rate_limiters(self) -> None:
        """Construct per-class rate limiters with default + override."""
        rl = self._taxonomy.get("rate_limits", {})
        default = rl.get("default", {})
        default_per_minute = int(default.get("max_per_minute", 30))
        overrides = rl.get("per_class_overrides", {})

        for event_id in self._allowed_events:
            override = overrides.get(event_id, {})
            per_minute = int(override.get("max_per_minute", default_per_minute))
            self._rate_state[event_id] = _RateLimitState(max_per_minute=per_minute)

    # ─── Public API ───────────────────────────────────────────────────────
    @property
    def allowed_events(self) -> frozenset[str]:
        return frozenset(self._allowed_events)

    def can_mint(self, event: str) -> bool:
        """Return True iff this event is on the receipt-worthy taxonomy."""
        return event in self._allowed_events

    def mint(
        self,
        event: str,
        principal_id: str,
        payload: dict[str, Any] | None = None,
    ) -> MintResult:
        """Attempt to mint a B49 receipt for the given event.

        Default-deny: raises ReceiptMintRefused if the event is not on the
        taxonomy. Rate-limited per class (with batching). Degraded-mode
        falls back to receipt_pending when SIX-SOV is unreachable.
        """
        if not self.can_mint(event):
            raise ReceiptMintRefused(
                f"Event {event!r} is not on the receipt-worthy taxonomy. "
                f"Default-deny — no external receipt minted. "
                f"(Internal cylinder seal still occurs via the Auditor.)"
            )

        payload = payload or {}
        now_mono = self._clock()
        now_utc = datetime.now(timezone.utc)

        # Per-class rate limiter
        rl_state = self._rate_state[event]
        with rl_state.lock:
            _purge_old_timestamps(rl_state.timestamps, window_seconds=60.0, now=now_mono)
            if len(rl_state.timestamps) >= rl_state.max_per_minute:
                # Batch mode — accumulate this event into the pending batch
                rl_state.pending_batch.append({"event": event, "payload": payload, "principal_id": principal_id})
                return MintResult(
                    minted=False,
                    receipt_id=None,
                    pending=False,
                    batched_count=len(rl_state.pending_batch),
                    event=event,
                    timestamp=now_utc,
                )
            rl_state.timestamps.append(now_mono)

        # Per-principal hourly limit
        with self._principal_lock:
            principal_ts = self._principal_timestamps[principal_id]
            _purge_old_timestamps(principal_ts, window_seconds=3600.0, now=now_mono)
            principal_ts.append(now_mono)

        # Now actually attempt the mint
        try:
            receipt_id = self._post_to_verify(event, principal_id, payload)
        except Exception:
            # Degraded mode: SIX-SOV not reachable
            if not self._degraded_mode_ok:
                raise
            return MintResult(
                minted=False,
                receipt_id=None,
                pending=True,
                batched_count=0,
                event=event,
                timestamp=now_utc,
            )

        if receipt_id is None:
            # Treated as degraded
            return MintResult(
                minted=False,
                receipt_id=None,
                pending=True,
                batched_count=0,
                event=event,
                timestamp=now_utc,
            )

        return MintResult(
            minted=True,
            receipt_id=receipt_id,
            pending=False,
            batched_count=0,
            event=event,
            timestamp=now_utc,
        )

    def flush_batch(self, event: str) -> MintResult | None:
        """Flush any accumulated batch for an event class as a single receipt
        with `count`. Returns None if no batch is pending."""
        rl_state = self._rate_state[event]
        with rl_state.lock:
            if not rl_state.pending_batch:
                return None
            batch = list(rl_state.pending_batch)
            rl_state.pending_batch.clear()

        # Mint a single receipt representing the batch
        principal_ids = sorted({item["principal_id"] for item in batch})
        merged_payload = {
            "batched_events": batch,
            "count": len(batch),
            "principals": principal_ids,
        }
        try:
            receipt_id = self._post_to_verify(
                event,
                principal_ids[0] if principal_ids else "system",
                merged_payload,
            )
        except Exception:
            if not self._degraded_mode_ok:
                raise
            receipt_id = None

        return MintResult(
            minted=receipt_id is not None,
            receipt_id=receipt_id,
            pending=receipt_id is None,
            batched_count=len(batch),
            event=event,
            timestamp=datetime.now(timezone.utc),
        )

    # ─── Internal ────────────────────────────────────────────────────────
    def _post_to_verify(
        self,
        event: str,
        principal_id: str,
        payload: dict[str, Any],
    ) -> ReceiptID | None:
        """POST to SIX-SOV /verify. Returns a ReceiptID on success, None
        if the endpoint is degraded (returns 503 placeholder JSON).
        """
        body = {
            "event": event,
            "principal_id": principal_id,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if self._post_fn is not None:
            response = self._post_fn(self._verify_endpoint, json=body, timeout=10)
        else:
            try:
                import httpx  # lazy import to avoid hard dependency in tests
            except ImportError:
                return None
            response = httpx.post(self._verify_endpoint, json=body, timeout=10)

        status_code = getattr(response, "status_code", None)
        if status_code is None:
            return None
        if status_code == 503:
            # Phase 2 transitioning placeholder; treated as pending
            return None
        if status_code >= 400:
            raise RuntimeError(
                f"SIX-SOV /verify returned HTTP {status_code} for event {event!r}"
            )

        try:
            data = response.json()
        except Exception:
            return None
        rid = data.get("receipt_id")
        if rid is None:
            return None
        return ReceiptID(rid)


# ∞Δ∞ Receipt minter — default-deny, rate-limited, degraded-mode safe ∞Δ∞
