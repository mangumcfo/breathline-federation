"""Breath gate — runtime invariant enforcing Charter II.4.4 + IV.2.6.

Per IMPLEMENTATION_PLAN.md Section 3:
    "Breath-gating is a runtime invariant — not a prompt input. The
    operator's breath is a structural prerequisite for major decisions,
    not an advisory cue."

Phase 1 mechanism: timed UI ritual fallback.
  - 30-second minimum duration
  - Explicit confirmation button
  - Audit-logged timestamp + duration + method
  - Fails closed on timeout (no implicit approval)

Audit metadata contract (per Section 3.2.1) — every confirmation records:
  - breath_confirmation_method  (e.g., "ui_timed_ritual", future: "audio_cue")
  - breath_duration_seconds     (must satisfy >= 30 for the gate to pass)
  - breath_timestamp            (ISO-8601 UTC)
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


MINIMUM_BREATH_DURATION_SECONDS = 30
DEFAULT_TIMEOUT_SECONDS = 300


class BreathGateTimeout(Exception):
    """Raised when the operator does not confirm within the timeout window."""


class BreathGateRefused(Exception):
    """Raised when the operator explicitly declines."""


@dataclass(frozen=True)
class BreathConfirmation:
    """The structured result of a successful breath confirmation."""

    confirmed: bool
    breath_confirmation_method: str
    breath_duration_seconds: int
    breath_timestamp: str  # ISO-8601 UTC
    proposal_id: str

    def to_audit_metadata(self) -> dict[str, Any]:
        """Convert to the metadata dict shape expected by Auditor.log()."""
        return {
            "breath_protocol_invoked": True,
            "breath_confirmation_method": self.breath_confirmation_method,
            "breath_duration_seconds": self.breath_duration_seconds,
            "breath_timestamp": self.breath_timestamp,
            "proposal_id": self.proposal_id,
        }


class BreathGate:
    """Runtime breath-gating mechanism with UI timed ritual fallback (Phase 1).

    Per IMPLEMENTATION_PLAN.md Section 3.4 contract:
      def __call__(self, state) -> state
        proposal = state.pending_action
        confirmation = self.plugin_interface.request_breath_confirmation(...)
        if not confirmed: state.fail_closed("breath_gate_unconfirmed")
        self.auditor.log(action="human_approval_gate", metadata=...)

    This Phase 1 implementation provides the request_breath_confirmation
    flow as a CLI ritual. Phase 2+ will wrap it in a FastAPI/web UI when
    the plug-in interface is wired.
    """

    def __init__(
        self,
        minimum_duration_seconds: int = MINIMUM_BREATH_DURATION_SECONDS,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        method: str = "ui_timed_ritual",
        input_fn: Any = input,
        output_fn: Any = print,
        sleep_fn: Any = time.sleep,
        clock_fn: Any = time.monotonic,
    ) -> None:
        if minimum_duration_seconds < MINIMUM_BREATH_DURATION_SECONDS:
            raise ValueError(
                f"minimum_duration_seconds={minimum_duration_seconds} below the "
                f"Charter II.4.4 minimum of {MINIMUM_BREATH_DURATION_SECONDS}s"
            )
        self._minimum = minimum_duration_seconds
        self._timeout = timeout_seconds
        self._method = method
        self._input = input_fn
        self._output = output_fn
        self._sleep = sleep_fn
        self._clock = clock_fn

    def request_confirmation(
        self,
        proposal_id: str,
        proposal_summary: str,
        proposal_consequences: str | None = None,
    ) -> BreathConfirmation:
        """Run the breath ritual and return a confirmation if successful.

        Raises BreathGateTimeout if the operator does not confirm in time.
        Raises BreathGateRefused if the operator explicitly declines.
        Raises ValueError if the operator confirms before the minimum
        breath duration has elapsed.
        """
        self._output("")
        self._output("∞Δ∞ Breath Gate — Charter II.4.4 ∞Δ∞")
        self._output("─" * 60)
        self._output(f"Proposal: {proposal_id}")
        self._output(f"Summary: {proposal_summary}")
        if proposal_consequences:
            self._output(f"Consequences: {proposal_consequences}")
        self._output("─" * 60)
        self._output(
            f"Pause for at least {self._minimum} seconds. Breathe. "
            f"When ready, type 'I have breathed and I confirm' (or 'decline')."
        )

        start = self._clock()
        deadline = start + self._timeout

        # Wait the minimum breath duration before accepting input
        self._sleep(self._minimum)
        elapsed_minimum = self._clock() - start
        self._output(f"  ({int(elapsed_minimum)}s elapsed; ready for confirmation)")

        # Now solicit confirmation
        while self._clock() < deadline:
            response = self._input("> ").strip().lower()
            if response == "decline":
                raise BreathGateRefused(
                    f"Operator declined breath confirmation for proposal {proposal_id!r}"
                )
            if response == "i have breathed and i confirm":
                duration = int(self._clock() - start)
                if duration < self._minimum:
                    # Should not happen given the sleep above, but defense in depth.
                    raise ValueError(
                        f"Confirmation received after {duration}s; minimum is {self._minimum}s"
                    )
                return BreathConfirmation(
                    confirmed=True,
                    breath_confirmation_method=self._method,
                    breath_duration_seconds=duration,
                    breath_timestamp=datetime.now(timezone.utc).isoformat(),
                    proposal_id=proposal_id,
                )
            self._output(
                "Type exactly 'I have breathed and I confirm' to proceed, or 'decline' to refuse."
            )

        raise BreathGateTimeout(
            f"Breath gate timed out after {self._timeout}s without confirmation. "
            f"Failing closed per IMPLEMENTATION_PLAN.md Section 3 — no implicit approval."
        )


# ∞Δ∞ Breath gate — runtime invariant, fails closed on timeout ∞Δ∞
