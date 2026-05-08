"""Demo 2 acceptance — IMPLEMENTATION_PLAN Sections 8.2, 8.7, 8.8.

The end-to-end runtime test for Demo 2: every role call goes through the
plug-in interface with the full Phase 4 stack wired:

  - Cost meter pre-dispatch gate
  - Critic CONFORMS verdict (only CONFORMS permits elevation)
  - Auditor synchronous seal (cylinder chain entry per call)
  - Receipt minter default-deny (B49 mint for taxonomy-listed events)

Sections covered:
  8.2 — End-to-end recursion ("Brief on Q3 readiness…")
  8.7 — Receipt integration (mint + default-deny verified)
  8.8 — Failure modes (cost cap breach, Critic DRIFT halts elevation,
        receipt default-deny on unknown event)

Hermetic: Auditor and receipt_minter are fakes that mirror the real
surfaces; CostMeter and RoleArtifactCritic are the real implementations.
The full kernel (real seal.sh + real SIX-SOV) is exercised by the
integration test suite, not here.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from kernel.cost_meter import CostCaps, CostMeter
from kernel.primitives.auditor import AuditEntry, CylinderID
from platform_layer.permission_spec import ActionClassRegistry
from platform_layer.plugin_interface import (
    PlugInRequest,
    PlugInResponse,
    route_request,
)
from platform_layer.registry import RoleRegistry
from platform_layer.role_artifact_critic import RoleArtifactCritic
from roles import create_demo2_handlers, register_demo2_roles


# -----------------------------------------------------------------------------
# Fakes — mirror Auditor + ReceiptMinter surfaces deterministically
# -----------------------------------------------------------------------------
class _FakeAuditor:
    """Records seal calls; returns synthetic AuditEntry without touching seal.sh."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self._seq = 0

    def log(
        self,
        agent_id: str,
        action: str,
        inputs: dict[str, Any] | None = None,
        outputs: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        netlify_deploy_hash: str | None = None,
    ) -> AuditEntry:
        self._seq += 1
        call = {
            "agent_id": agent_id,
            "action": action,
            "inputs": inputs or {},
            "outputs": outputs or {},
            "metadata": metadata or {},
        }
        self.calls.append(call)
        return AuditEntry(
            cylinder_id=CylinderID(f"fake-cyl-{self._seq:04d}"),
            sequence=self._seq,
            prev_hash=f"prev-{self._seq - 1:04d}",
            agent_id=agent_id,
            action=action,
            inputs=inputs or {},
            outputs=outputs or {},
            metadata=metadata or {},
            sealed_at=datetime.now(timezone.utc),
        )


class _FakeMintResult:
    def __init__(self, event: str, minted: bool, receipt_id: str | None = None) -> None:
        self.event = event
        self.minted = minted
        self.receipt_id = receipt_id

    def to_metadata(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "event": self.event,
            "minted": self.minted,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if self.receipt_id is not None:
            out["receipt_id"] = self.receipt_id
        return out


class _FakeReceiptMinter:
    """Default-deny receipt minter mirror.

    `allowed_events` controls which event names the minter accepts.
    Anything else raises RuntimeError (mirrors real ReceiptMintRefused).
    """

    def __init__(self, allowed_events: set[str], receipt_id_prefix: str = "rid") -> None:
        self.allowed_events = allowed_events
        self.calls: list[dict[str, Any]] = []
        self._receipt_id_prefix = receipt_id_prefix
        self._counter = 0

    def mint(
        self,
        event: str,
        principal_id: str,
        payload: dict[str, Any] | None = None,
    ) -> _FakeMintResult:
        if event not in self.allowed_events:
            raise RuntimeError(
                f"event {event!r} not on receipt-worthy taxonomy (default-deny)"
            )
        self._counter += 1
        call = {"event": event, "principal_id": principal_id, "payload": payload or {}}
        self.calls.append(call)
        return _FakeMintResult(
            event=event,
            minted=True,
            receipt_id=f"{self._receipt_id_prefix}-{self._counter:04d}",
        )


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def action_class_registry(seed_dir):
    return ActionClassRegistry.from_yaml(seed_dir / "action_classes.yaml")


@pytest.fixture
def role_registry(action_class_registry):
    registry = RoleRegistry(action_class_registry)
    register_demo2_roles(registry)
    return registry


@pytest.fixture
def handlers(role_registry):
    return create_demo2_handlers(role_registry)


@pytest.fixture
def auditor():
    return _FakeAuditor()


@pytest.fixture
def critic():
    return RoleArtifactCritic()


@pytest.fixture
def cost_meter():
    """Generous caps for happy-path tests; specific tests override."""
    return CostMeter(caps=CostCaps(
        per_request_usd=1.00,
        per_role_daily_usd=100.00,
        per_principal_hourly_usd=100.00,
        session_total_usd=100.00,
    ))


@pytest.fixture
def receipt_minter():
    """Allow exactly the three Demo 2 event names; any other → default-deny."""
    return _FakeReceiptMinter(
        allowed_events={
            "forecast_artifact_produced",
            "executive_brief_produced",
            "compliance_evidence_bundle_generated",
        },
    )


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _q3_synthesis_request(principal: str = "kmangum") -> PlugInRequest:
    return PlugInRequest(
        request_id="req-acceptance-q3",
        principal_id=principal,
        role_target="synthesis_agent",
        action_class="produce_executive_brief",
        payload={
            "request_summary": (
                "Brief on Q3 readiness — pull from CFO and Compliance; "
                "integrate; flag tensions."
            ),
            "peer_roles_to_invoke": ["cfo_agent", "compliance_agent"],
            "peer_payloads": {
                "cfo_agent": {
                    "action_class": "produce_forecast_artifact",
                    "payload": {
                        "financial_data": {
                            "revenue": [950.0, 1010.0, 1075.0, 1140.0],
                            "expenses": [820.0, 845.0, 870.0, 895.0],
                        },
                        "forecast_horizon": 4,
                    },
                },
                "compliance_agent": {
                    "action_class": "review_peer_outputs",
                    "payload": {"mode": "compliance_review"},
                },
            },
        },
    )


def _cfo_request(principal: str = "kmangum") -> PlugInRequest:
    return PlugInRequest(
        request_id="req-acceptance-cfo",
        principal_id=principal,
        role_target="cfo_agent",
        action_class="produce_forecast_artifact",
        payload={
            "financial_data": {
                "revenue": [100.0, 105.0, 110.0],
                "expenses": [80.0, 82.0, 84.0],
            },
            "forecast_horizon": 4,
        },
    )


# =============================================================================
# Section 8.2 — End-to-end recursion through the FULL Phase 4 stack
# =============================================================================
def test_8_2_full_stack_q3_readiness(
    handlers, role_registry, auditor, critic, cost_meter, receipt_minter
):
    """Full e2e: Synthesis invokes CFO + Compliance, all integrations active."""
    response = route_request(
        _q3_synthesis_request(),
        role_registry=role_registry,
        role_handlers=handlers,
        auditor=auditor,
        critic=critic,
        cost_meter=cost_meter,
        receipt_minter=receipt_minter,
    )

    assert response.accepted is True
    assert response.role_id == "synthesis_agent"
    assert response.principal_id == "kmangum"
    assert response.critic_verdict == "CONFORMS"
    assert response.audit_cylinder_id is not None
    assert response.audit_cylinder_id.startswith("fake-cyl-")
    assert response.receipt_metadata is not None
    assert response.receipt_metadata["event"] == "executive_brief_produced"
    assert response.receipt_metadata["minted"] is True


def test_8_2_principal_flows_through_audit_metadata(
    handlers, role_registry, auditor, critic, cost_meter
):
    """Audit entry must record the principal that initiated the request."""
    route_request(
        _cfo_request(principal="auditor-007"),
        role_registry=role_registry,
        role_handlers=handlers,
        auditor=auditor,
        critic=critic,
        cost_meter=cost_meter,
    )
    assert len(auditor.calls) == 1
    assert auditor.calls[0]["inputs"]["principal_id"] == "auditor-007"


# =============================================================================
# Section 8.7 — Receipt integration
# =============================================================================
def test_8_7_cfo_call_mints_forecast_receipt(
    handlers, role_registry, auditor, critic, cost_meter, receipt_minter
):
    response = route_request(
        _cfo_request(),
        role_registry=role_registry,
        role_handlers=handlers,
        auditor=auditor,
        critic=critic,
        cost_meter=cost_meter,
        receipt_minter=receipt_minter,
    )
    assert response.accepted is True
    assert response.receipt_metadata is not None
    assert response.receipt_metadata["event"] == "forecast_artifact_produced"
    assert "receipt_id" in response.receipt_metadata
    assert len(receipt_minter.calls) == 1


def test_8_7_default_deny_for_unknown_event(
    handlers, role_registry, auditor, critic, cost_meter
):
    """Receipt minter that allows ZERO events refuses every mint via default-deny.

    The plug-in interface absorbs the refusal silently — receipt_metadata
    flips to default_deny=True without breaking the request.
    """
    minter = _FakeReceiptMinter(allowed_events=set())  # nothing on taxonomy
    response = route_request(
        _cfo_request(),
        role_registry=role_registry,
        role_handlers=handlers,
        auditor=auditor,
        critic=critic,
        cost_meter=cost_meter,
        receipt_minter=minter,
    )
    assert response.accepted is True  # request still succeeds
    assert response.receipt_metadata is not None
    assert response.receipt_metadata.get("default_deny") is True
    assert response.receipt_metadata.get("minted") is False


def test_8_7_no_receipt_minter_means_no_receipt(
    handlers, role_registry, auditor, critic, cost_meter
):
    """When minter injection is absent, receipt_metadata is None (not crashed)."""
    response = route_request(
        _cfo_request(),
        role_registry=role_registry,
        role_handlers=handlers,
        auditor=auditor,
        critic=critic,
        cost_meter=cost_meter,
        receipt_minter=None,
    )
    assert response.accepted is True
    assert response.receipt_metadata is None


# =============================================================================
# Section 8.8 — Failure modes
# =============================================================================
def test_8_8_cost_cap_breach_refuses_dispatch(
    handlers, role_registry, auditor, critic
):
    """Tiny per-request cap → CostCapBreach → refusal BEFORE handler is invoked."""
    tight_meter = CostMeter(caps=CostCaps(
        per_request_usd=0.0001,  # below default estimated cost
        per_role_daily_usd=100.0,
        per_principal_hourly_usd=100.0,
        session_total_usd=100.0,
    ))
    response = route_request(
        _cfo_request(),
        role_registry=role_registry,
        role_handlers=handlers,
        auditor=auditor,
        critic=critic,
        cost_meter=tight_meter,
    )
    assert response.accepted is False
    assert "cost_ceiling_breach" in response.refusal_reason
    # Audit fires even on cost-cap refusal — no bypass
    assert response.audit_cylinder_id is not None
    assert auditor.calls[-1]["metadata"]["refusal"] == "cost_ceiling_breach"


def test_8_8_critic_drift_halts_elevation(
    role_registry, auditor, critic, cost_meter, receipt_minter
):
    """A handler returning a mismatched principal_id triggers Critic DRIFT, refusing.

    Verifies: only CONFORMS permits elevation (Section 8.8).
    """
    class _DriftingCFO:
        def process(self, request: PlugInRequest) -> dict[str, Any]:
            # Honest framework structure but lies about principal_id → DRIFT
            return {
                "role_id": "cfo_agent",
                "framework": "FORECAST",
                "status": "produced",
                "principal_id": "wrong-principal",  # ← intentional drift
                "request_id": request.request_id,
                "forecast_artifact": {"scenarios": []},
            }

    response = route_request(
        _cfo_request(principal="kmangum"),
        role_registry=role_registry,
        role_handlers={"cfo_agent": _DriftingCFO()},
        auditor=auditor,
        critic=critic,
        cost_meter=cost_meter,
        receipt_minter=receipt_minter,
    )
    assert response.accepted is False
    assert response.critic_verdict == "DRIFT"
    assert "critic_drift" in response.refusal_reason
    assert response.artifact is None  # drift halts elevation
    # Audit still fires on Critic refusal
    assert response.audit_cylinder_id is not None
    assert auditor.calls[-1]["metadata"]["refusal"] == "critic_non_conforming"
    # Receipt does NOT mint when elevation halts
    assert len(receipt_minter.calls) == 0


def test_8_8_critic_defect_on_malformed_handler_output(
    role_registry, auditor, critic, cost_meter
):
    """Handler returning a non-dict-shaped artifact triggers Critic DEFECT."""
    class _MalformedCFO:
        def process(self, request: PlugInRequest) -> dict[str, Any]:
            return {"oops": "missing required keys"}

    response = route_request(
        _cfo_request(),
        role_registry=role_registry,
        role_handlers={"cfo_agent": _MalformedCFO()},
        auditor=auditor,
        critic=critic,
        cost_meter=cost_meter,
    )
    assert response.accepted is False
    assert response.critic_verdict == "DEFECT"
    assert "critic_defect" in response.refusal_reason


def test_8_8_role_unknown_default_deny(handlers, role_registry, auditor, critic):
    """Unknown role refused before any other gate."""
    response = route_request(
        PlugInRequest(
            request_id="r",
            principal_id="kmangum",
            role_target="ghost_agent",
            action_class="produce_forecast_artifact",
        ),
        role_registry=role_registry,
        role_handlers=handlers,
        auditor=auditor,
        critic=critic,
    )
    assert response.accepted is False
    assert "role_unknown" in response.refusal_reason


def test_8_8_charter_v7_forbidden_at_envelope_layer(
    handlers, role_registry, auditor, critic, action_class_registry
):
    """Frame-of-reference attack: a Charter V.7 forbidden action class is
    refused at the envelope BEFORE the role is ever invoked.

    Pulls a forbidden class from the canonical list rather than hardcoding.
    """
    forbidden = next(iter(action_class_registry.charter_v7_forbidden))
    response = route_request(
        PlugInRequest(
            request_id="r",
            principal_id="kmangum",
            role_target="cfo_agent",
            action_class=forbidden,
        ),
        role_registry=role_registry,
        role_handlers=handlers,
        auditor=auditor,
        critic=critic,
    )
    assert response.accepted is False
    assert "charter_v7_forbidden_delegation" in response.refusal_reason


# =============================================================================
# Cross-cutting — every integration activates simultaneously
# =============================================================================
def test_demo2_acceptance_capstone(
    handlers, role_registry, auditor, critic, cost_meter, receipt_minter
):
    """One full e2e where every Phase 4 surface is observable in the response."""
    response = route_request(
        _q3_synthesis_request(),
        role_registry=role_registry,
        role_handlers=handlers,
        auditor=auditor,
        critic=critic,
        cost_meter=cost_meter,
        receipt_minter=receipt_minter,
    )
    # Acceptance criteria — all of these must be true together
    assert response.accepted is True
    assert response.critic_verdict == "CONFORMS"
    assert response.audit_cylinder_id is not None
    assert response.receipt_metadata is not None
    assert response.receipt_metadata["minted"] is True
    assert response.principal_id == "kmangum"
    assert response.role_id == "synthesis_agent"
    # Brief structure intact
    brief = response.artifact["executive_brief"]
    assert {p["role_id"] for p in brief["peer_results"]} == {"cfo_agent", "compliance_agent"}


# ∞Δ∞ Demo 2 acceptance seal — Sections 8.2 + 8.7 + 8.8 verified ∞Δ∞
