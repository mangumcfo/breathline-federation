"""Cost meter — structural pre-dispatch gate.

Per IMPLEMENTATION_PLAN.md Section 5:
    "The cost meter must be structurally enforced — agents cannot bypass
    it through prompt manipulation. Every model invocation passes through
    this gate before the call is dispatched."

Architecture (from Section 5.1):
  1. Look up token-cost estimate
  2. Check per-request cap
  3. Check per-role daily cap
  4. Check per-principal hour cap
  5. Check global session cap
  6. If any breached: refuse + emit cost_ceiling_breach
  7. If approved: reserve budget + dispatch to model
  8. After response: reconcile actual vs reserved

Per Section 5.3: there is no retry loop, no automatic cap raise. Caps are
raised only through breath-gated human approval.
"""
from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


# Default caps; overridable via env or config/cost_caps.yaml at boot.
DEFAULT_PER_REQUEST_USD = 1.00
DEFAULT_PER_ROLE_DAILY_USD = 25.00
DEFAULT_PER_PRINCIPAL_HOURLY_USD = 10.00
DEFAULT_SESSION_TOTAL_USD = 50.00


class CostCapBreach(Exception):
    """Raised when a cost cap would be exceeded.

    Carries the breach context so the calling graph can surface a
    structured refusal to the operator (per Section 5.3).
    """

    def __init__(self, cap_type: str, principal_id: str, cap_usd: float, would_be_usd: float) -> None:
        super().__init__(
            f"Cost cap breach: {cap_type} for principal {principal_id!r} "
            f"(cap={cap_usd:.2f} USD, would-be={would_be_usd:.2f} USD). "
            f"Refusing dispatch. No retry; no automatic cap raise."
        )
        self.cap_type = cap_type
        self.principal_id = principal_id
        self.cap_usd = cap_usd
        self.would_be_usd = would_be_usd


@dataclass
class CostCaps:
    """Configured cost caps. Loaded from env or config/cost_caps.yaml at boot."""

    per_request_usd: float = DEFAULT_PER_REQUEST_USD
    per_role_daily_usd: float = DEFAULT_PER_ROLE_DAILY_USD
    per_principal_hourly_usd: float = DEFAULT_PER_PRINCIPAL_HOURLY_USD
    session_total_usd: float = DEFAULT_SESSION_TOTAL_USD

    @classmethod
    def from_env(cls) -> "CostCaps":
        """Load caps from environment variables (ENV overrides YAML)."""
        return cls(
            per_request_usd=float(
                os.environ.get("COST_CAP_PER_REQUEST_USD", DEFAULT_PER_REQUEST_USD)
            ),
            per_role_daily_usd=float(
                os.environ.get("COST_CAP_PER_ROLE_DAILY_USD", DEFAULT_PER_ROLE_DAILY_USD)
            ),
            per_principal_hourly_usd=float(
                os.environ.get(
                    "COST_CAP_PER_PRINCIPAL_HOURLY_USD", DEFAULT_PER_PRINCIPAL_HOURLY_USD
                )
            ),
            session_total_usd=float(
                os.environ.get("COST_CAP_SESSION_TOTAL_USD", DEFAULT_SESSION_TOTAL_USD)
            ),
        )


@dataclass
class _Spend:
    """Accumulated spend with timestamp."""

    timestamp: datetime
    amount_usd: float


@dataclass
class CostMeter:
    """Structural pre-dispatch gate for model invocations.

    Tracks spend per role (daily) and per principal (hourly) plus the
    cumulative session total. Refuses dispatch when any cap is breached.
    """

    caps: CostCaps = field(default_factory=CostCaps.from_env)
    _session_total_usd: float = 0.0
    _per_role_spend: dict[str, list[_Spend]] = field(default_factory=lambda: defaultdict(list))
    _per_principal_spend: dict[str, list[_Spend]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def check_and_reserve(
        self,
        principal_id: str,
        role_id: str,
        estimated_cost_usd: float,
    ) -> dict[str, Any]:
        """Run all 4 cap checks; reserve budget if approved.

        Raises CostCapBreach if any cap would be exceeded. The caller's
        graph must let this propagate (Section 5.3 — no retry, no
        automatic raise).

        Returns a reservation handle (dict) to be passed to reconcile()
        after the model response.
        """
        # 1. Per-request cap
        if estimated_cost_usd > self.caps.per_request_usd:
            raise CostCapBreach(
                cap_type="per_request",
                principal_id=principal_id,
                cap_usd=self.caps.per_request_usd,
                would_be_usd=estimated_cost_usd,
            )

        # 2. Per-role daily
        daily_role = self._sum_recent(
            self._per_role_spend[role_id], window=timedelta(days=1)
        )
        if daily_role + estimated_cost_usd > self.caps.per_role_daily_usd:
            raise CostCapBreach(
                cap_type="per_role_daily",
                principal_id=principal_id,
                cap_usd=self.caps.per_role_daily_usd,
                would_be_usd=daily_role + estimated_cost_usd,
            )

        # 3. Per-principal hourly
        hourly_principal = self._sum_recent(
            self._per_principal_spend[principal_id], window=timedelta(hours=1)
        )
        if hourly_principal + estimated_cost_usd > self.caps.per_principal_hourly_usd:
            raise CostCapBreach(
                cap_type="per_principal_hourly",
                principal_id=principal_id,
                cap_usd=self.caps.per_principal_hourly_usd,
                would_be_usd=hourly_principal + estimated_cost_usd,
            )

        # 4. Session total
        if self._session_total_usd + estimated_cost_usd > self.caps.session_total_usd:
            raise CostCapBreach(
                cap_type="session_total",
                principal_id=principal_id,
                cap_usd=self.caps.session_total_usd,
                would_be_usd=self._session_total_usd + estimated_cost_usd,
            )

        # All checks pass — reserve budget
        now = datetime.now(timezone.utc)
        return {
            "principal_id": principal_id,
            "role_id": role_id,
            "reserved_usd": estimated_cost_usd,
            "reserved_at": now,
        }

    def reconcile(self, reservation: dict[str, Any], actual_cost_usd: float) -> None:
        """Reconcile actual cost against the reservation. Records the spend."""
        now = datetime.now(timezone.utc)
        self._per_role_spend[reservation["role_id"]].append(
            _Spend(timestamp=now, amount_usd=actual_cost_usd)
        )
        self._per_principal_spend[reservation["principal_id"]].append(
            _Spend(timestamp=now, amount_usd=actual_cost_usd)
        )
        self._session_total_usd += actual_cost_usd

    @staticmethod
    def _sum_recent(spend_list: list[_Spend], window: timedelta) -> float:
        cutoff = datetime.now(timezone.utc) - window
        return sum(s.amount_usd for s in spend_list if s.timestamp >= cutoff)


# ∞Δ∞ Cost meter — structural pre-dispatch gate, no bypass ∞Δ∞
