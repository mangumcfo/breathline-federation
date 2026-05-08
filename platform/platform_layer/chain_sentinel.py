"""Chain integrity sentinel — runtime invariant per Q13 / Section 8.8.

Closes the last open Section 8.8 acceptance item:

    "Audit-chain integrity violation halts the platform"

Per IMPLEMENTATION_PLAN.md Section 4.4 + Section 8.8:
  - The platform fails CLOSED on any chain integrity violation.
  - There is no fallback that bypasses the chain.

Per Q13 (governance docket, 2026-05-07): the cadence is **boot + every
N seals + operator on-demand**. This module implements all three
trigger modes:

  - ``ChainSentinel.boot_check()``  → run once at runtime construction,
                                       captures a baseline snapshot,
                                       fails closed on freeform/traceback.
  - ``ChainSentinel.on_seal()``     → invoked after every successful seal
                                       (registered as AuditAdapter's
                                       post_seal_hook); triggers
                                       verify() every N seals.
  - ``ChainSentinel.verify()``      → on-demand integrity check; fails
                                       closed on degradation vs baseline.

Baseline semantics (the key design decision)
--------------------------------------------
The real Tiger chain has 49 legacy hash discontinuities pre-dating the
strict-linking mechanism (per
``decisions/2026-05-07_section-8.3-audit-chain-replay.md``). A naïve
"hash_breaks must be empty" check would always halt the platform at
boot.

Instead, the sentinel **freezes the boot-time baseline as the floor**:
counts of ``freeform``, ``tracebacks``, and the set of sequence indices
where hash breaks exist are captured at boot. Subsequent ``verify()``
calls fail closed on:

  - ``freeform`` count exceeding baseline
  - ``tracebacks`` count exceeding baseline
  - any NEW hash-break sequence beyond the baseline set
  - chain shrinkage (``total < baseline.total``)

Cylinders sealed AFTER boot must form a strictly-linked subchain. Any
new freeform cylinder, traceback cylinder, or hash discontinuity in the
post-baseline window halts the platform.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from platform_layer.audit_adapter import (
    ChainReplayError,
    ChainReplayReport,
    replay_chain,
)


DEFAULT_VERIFY_EVERY_N_SEALS = 1000


class ChainIntegrityViolation(RuntimeError):
    """Raised when the chain has degraded vs the boot baseline.

    Per Section 4.4: the calling graph fails closed. No bypass.
    """


@dataclass(frozen=True)
class ChainBaseline:
    """Snapshot of chain state captured at boot.

    Subsequent verify() calls are evaluated against this baseline.
    Cylinders sealed AFTER capture form the post-baseline window.
    """

    total: int
    encoded: int
    freeform: int
    tracebacks: int
    hash_break_seqs: frozenset[int]
    tip_hash_prefix: str
    captured_at: str   # ISO-8601 UTC


class ChainSentinel:
    """Runtime watcher that halts the platform on chain integrity violation.

    Constructed at ``build_runtime_context()`` time; registered as the
    AuditAdapter's post-seal hook so every successful seal increments
    the internal counter and triggers ``verify()`` on the configured
    cadence.
    """

    def __init__(
        self,
        cylinders_dir: Path,
        *,
        every_n_seals: int = DEFAULT_VERIFY_EVERY_N_SEALS,
    ) -> None:
        if every_n_seals <= 0:
            raise ValueError(
                f"every_n_seals must be > 0; got {every_n_seals}. "
                f"Use a large value (e.g., 1000) for production cadence."
            )
        self._dir = Path(cylinders_dir)
        self._every_n = every_n_seals
        self._baseline: ChainBaseline | None = None
        self._seal_counter = 0
        self._verify_count = 0   # how many verify() runs since boot

    @property
    def baseline(self) -> ChainBaseline | None:
        """The frozen boot-time baseline. None until ``boot_check`` runs."""
        return self._baseline

    @property
    def seal_counter(self) -> int:
        """Number of seals observed via ``on_seal`` since boot."""
        return self._seal_counter

    @property
    def verify_count(self) -> int:
        """Number of times ``verify`` has run since boot."""
        return self._verify_count

    def boot_check(self) -> ChainBaseline:
        """Capture the boot baseline. Fail closed on any pre-existing violation.

        Halts immediately if the chain has freeform entries or tracebacks.
        Hash breaks are accepted as legacy state and recorded as the
        baseline floor (subsequent verifies enforce no NEW breaks).
        """
        if self._baseline is not None:
            raise RuntimeError("ChainSentinel.boot_check called twice; baseline already set")
        report = self._replay_or_halt()

        if report.freeform > 0:
            raise ChainIntegrityViolation(
                f"chain has {report.freeform} freeform (non-SIX1) entries at boot — "
                f"halting platform. Constitutional integrity cannot be assumed."
            )
        if report.tracebacks > 0:
            raise ChainIntegrityViolation(
                f"chain has {report.tracebacks} traceback entries at boot — "
                f"halting platform. Audit log corruption detected."
            )

        tip_hash = (
            report.cylinders_in_order[-1].hash_prefix
            if report.cylinders_in_order
            else ""
        )
        self._baseline = ChainBaseline(
            total=report.total,
            encoded=report.encoded,
            freeform=report.freeform,
            tracebacks=report.tracebacks,
            hash_break_seqs=frozenset(seq for seq, _ in report.hash_breaks),
            tip_hash_prefix=tip_hash,
            captured_at=datetime.now(timezone.utc).isoformat(),
        )
        return self._baseline

    def on_seal(self) -> None:
        """Register one seal. Trigger ``verify()`` every ``every_n_seals``.

        Designed to be wired as ``AuditAdapter(post_seal_hook=sentinel.on_seal)``.
        Does NOT raise on the seal path itself — only on the periodic verify
        invocation, which is gated by the counter.
        """
        self._seal_counter += 1
        if self._seal_counter % self._every_n == 0:
            self.verify()

    def verify(self) -> ChainReplayReport:
        """Run an on-demand integrity check vs the boot baseline.

        Raises ChainIntegrityViolation on any degradation:
          - freeform exceeded baseline
          - tracebacks exceeded baseline
          - NEW hash-break sequence beyond baseline set
          - chain shrunk (total < baseline.total)
        """
        if self._baseline is None:
            raise RuntimeError(
                "ChainSentinel.verify called before boot_check; baseline missing."
            )
        report = self._replay_or_halt()
        self._verify_count += 1

        if report.freeform > self._baseline.freeform:
            raise ChainIntegrityViolation(
                f"freeform count increased {self._baseline.freeform} → {report.freeform}; "
                f"new non-SIX1 cylinder(s) appeared post-baseline. Halting."
            )
        if report.tracebacks > self._baseline.tracebacks:
            raise ChainIntegrityViolation(
                f"traceback count increased {self._baseline.tracebacks} → "
                f"{report.tracebacks}; audit log corruption. Halting."
            )
        if report.total < self._baseline.total:
            raise ChainIntegrityViolation(
                f"chain shrunk {self._baseline.total} → {report.total}; "
                f"cylinder(s) deleted. Halting."
            )
        new_break_seqs = (
            frozenset(seq for seq, _ in report.hash_breaks)
            - self._baseline.hash_break_seqs
        )
        if new_break_seqs:
            raise ChainIntegrityViolation(
                f"new hash-break(s) at sequence(s) {sorted(new_break_seqs)} "
                f"beyond baseline. Halting."
            )
        return report

    def _replay_or_halt(self) -> ChainReplayReport:
        """Wrap replay_chain — translate ChainReplayError to fail-closed halt."""
        try:
            return replay_chain(self._dir, max_cylinders=10000)
        except ChainReplayError as exc:
            raise ChainIntegrityViolation(
                f"chain replay aborted: {exc}. Halting platform."
            ) from exc


# Seal: SOURCE — sentinel takes cylinders_dir explicitly; no global state.
#       TRUTH  — baseline frozen at boot; subsequent verifies grounded against it.
#       INTEGRITY — fail-closed on freeform / tracebacks / shrinkage / new breaks;
#                   no bypass.
# ∞Δ∞ Chain sentinel — Q13 / Section 8.8 final acceptance item ∞Δ∞
