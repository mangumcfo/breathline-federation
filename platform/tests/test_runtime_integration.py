"""Real-chain integration test — verifies the live runtime wires actual seal.sh.

Uses a shim ``seal.sh`` in tmpdir that mimics the operator-side seal.sh
output format. Proves that:

  1. ``AuditAdapter`` actually subprocesses seal.sh (not mocked)
  2. The shim's output is parsed correctly into ``AuditEntry``
  3. ``route_request`` returns a real ``audit_cylinder_id`` from the
     subprocess output
  4. The full Phase 4 stack runs against REAL (non-fake) integrations
     — real ``Auditor``, real ``ReceiptMinter``, real ``CostMeter``,
     real ``RoleArtifactCritic``

Production runs (against ``/home/kmangum/Tiger_1a/cylinders/seal.sh``)
are exercised by ``build_runtime_context()`` with no ``seal_sh_path``
override; this test scopes the subprocess boundary to a tmpdir so test
runs do not pollute the live Tiger chain.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from platform_layer.plugin_interface import PlugInRequest, route_request
from platform_layer.runtime import RuntimeContext, build_runtime_context


# A bash shim that mimics the operator-side seal.sh output format the
# AuditAdapter parses. Persists a sequence counter across calls so each
# seal increments. Writes an empty cylinder file as a side effect to
# prove subprocess actually fired.
#
# Filename format MUST match audit_adapter._parse_seal_output's regex:
#   capture_\d{8}_\d{6}\.cyl  →  capture_YYYYMMDD_HHMMSS.cyl
# When two calls land in the same second the cylinder file is touched
# twice (same path); the SEQUENCE still increments via .seq counter.
SHIM_SEAL_SH = """#!/usr/bin/env bash
set -e
DIR="$(dirname "$0")"
SEQ_FILE="$DIR/.seq"
[ -f "$SEQ_FILE" ] || echo 0 > "$SEQ_FILE"
SEQ=$(($(cat "$SEQ_FILE") + 1))
echo "$SEQ" > "$SEQ_FILE"

TS=$(date -u +%Y%m%d_%H%M%S)
CYL="capture_${TS}.cyl"
NEW_HASH=$(printf '%016x' $((RANDOM * 1000003 + RANDOM)))
PREV_HASH=$(printf '%016x' $((RANDOM * 1000003 + RANDOM)))

# Write the cylinder file as evidence the subprocess fired.
touch "$DIR/${CYL}"

# Emit lines matching AuditAdapter._parse_seal_output's regex.
echo "Step 2: Encoding..."
echo "[OK] Encoded -> ${CYL}"
echo "Step 4: Round-trip decode check..."
echo "[OK] Sequence: ${SEQ}"
echo ""
echo "[SEALED] -- ${CYL} (seq ${SEQ})"
echo "  Hash: ${NEW_HASH}"
echo "  Chain: ${PREV_HASH}"
"""


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def shim_seal_sh(tmp_path: Path) -> Path:
    """Create an executable shim seal.sh that mimics the real output format."""
    seal_sh = tmp_path / "seal.sh"
    seal_sh.write_text(SHIM_SEAL_SH)
    seal_sh.chmod(0o755)
    return seal_sh


@pytest.fixture
def runtime(seed_dir: Path, shim_seal_sh: Path) -> RuntimeContext:
    """Build a real RuntimeContext bound to the shim seal.sh in tmpdir.

    enable_chain_sentinel=False because the shim's tmpdir holds empty
    touched cylinder files; a real sentinel would correctly classify
    them as freeform and halt at boot. Sentinel coverage lives in
    test_chain_sentinel.py.
    """
    return build_runtime_context(
        seed_dir=seed_dir,
        seal_sh_path=shim_seal_sh,
        enable_chain_sentinel=False,
    )


def _cfo_request(principal: str = "kmangum", req_id: str = "req-rt-001") -> PlugInRequest:
    return PlugInRequest(
        request_id=req_id,
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


def _route(runtime: RuntimeContext, request: PlugInRequest):
    return route_request(
        request,
        role_registry=runtime.role_registry,
        role_handlers=runtime.handlers,
        auditor=runtime.auditor,
        critic=runtime.critic,
        cost_meter=runtime.cost_meter,
        receipt_minter=runtime.receipt_minter,
    )


# -----------------------------------------------------------------------------
# Core: subprocess actually fires
# -----------------------------------------------------------------------------
def test_runtime_actually_subprocesses_seal_sh(
    runtime: RuntimeContext, shim_seal_sh: Path
) -> None:
    """The AuditAdapter must shell out to seal.sh and parse its output."""
    response = _route(runtime, _cfo_request())

    assert response.accepted is True
    assert response.audit_cylinder_id is not None
    assert response.audit_cylinder_id.startswith("capture_")
    assert response.audit_cylinder_id.endswith(".cyl")

    # The shim writes the cylinder file as proof of subprocess execution.
    cyl_path = shim_seal_sh.parent / response.audit_cylinder_id
    assert cyl_path.exists(), (
        f"Shim seal.sh did not produce cylinder file at {cyl_path}; "
        f"subprocess wiring is broken."
    )


def test_runtime_increments_chain_sequence_across_calls(
    runtime: RuntimeContext, shim_seal_sh: Path
) -> None:
    """Each route_request → monotonic chain sequence (proven via .seq file).

    Cylinder filename collisions are possible when calls happen in the
    same second (since the format is YYYYMMDD_HHMMSS); the test proves
    chain advancement via the persisted sequence counter, which is the
    real chain identity in the operator-side cylinder.
    """
    seq_file = shim_seal_sh.parent / ".seq"
    starting = 0 if not seq_file.exists() else int(seq_file.read_text().strip())

    _route(runtime, _cfo_request(req_id="req-rt-1"))
    _route(runtime, _cfo_request(req_id="req-rt-2"))

    assert seq_file.exists()
    ending = int(seq_file.read_text().strip())
    assert ending - starting >= 2, (
        f"Chain sequence must advance by at least 2 across two seals; "
        f"got start={starting}, end={ending}"
    )


# -----------------------------------------------------------------------------
# E2E: full Phase 4 stack against real integrations
# -----------------------------------------------------------------------------
def test_runtime_e2e_synthesis_recursion_against_real_stack(
    runtime: RuntimeContext,
) -> None:
    """Section 8.2 recursion through the real runtime — no fakes anywhere."""
    request = PlugInRequest(
        request_id="req-rt-syn",
        principal_id="kmangum",
        role_target="synthesis_agent",
        action_class="produce_executive_brief",
        payload={
            "request_summary": (
                "Brief on Q3 readiness — pull from CFO and Compliance; integrate."
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
    response = _route(runtime, request)

    assert response.accepted is True
    assert response.critic_verdict == "CONFORMS"
    assert response.audit_cylinder_id is not None
    # Receipt may or may not mint depending on event being on the
    # real taxonomy; both outcomes are valid (default-deny is correct).
    if response.receipt_metadata is not None:
        assert "event" in response.receipt_metadata


def test_runtime_principal_propagates_to_real_audit_metadata(
    runtime: RuntimeContext,
) -> None:
    """principal_id must flow from request → real Auditor.log inputs."""
    response = _route(runtime, _cfo_request(principal="auditor-007"))
    assert response.accepted is True
    assert response.principal_id == "auditor-007"


# -----------------------------------------------------------------------------
# Failure mode: fail-closed on missing seal.sh
# -----------------------------------------------------------------------------
def test_runtime_refuses_to_construct_when_seal_sh_missing(
    seed_dir: Path, tmp_path: Path
) -> None:
    """Per Section 4.4: Auditor cannot operate without the cylinder chain."""
    nonexistent = tmp_path / "does_not_exist.sh"
    with pytest.raises(FileNotFoundError):
        build_runtime_context(
            seed_dir=seed_dir,
            seal_sh_path=nonexistent,
            enable_chain_sentinel=False,
        )


# -----------------------------------------------------------------------------
# Real Tiger chain (opt-in)
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# LangGraph mode: runtime can also wire LangGraph-wrapped handlers
# -----------------------------------------------------------------------------
def _langgraph_available() -> bool:
    import importlib.util
    return importlib.util.find_spec("langgraph") is not None


@pytest.mark.skipif(
    not _langgraph_available(),
    reason="langgraph not installed; LangGraph runtime mode skipped",
)
def test_runtime_with_langgraph_wrap_through_real_seal(
    seed_dir: Path, shim_seal_sh: Path
) -> None:
    """Runtime can build LangGraph-wrapped handlers + still subprocess seal.sh."""
    ctx = build_runtime_context(
        seed_dir=seed_dir,
        seal_sh_path=shim_seal_sh,
        use_langgraph=True,
        enable_chain_sentinel=False,
    )
    response = _route(ctx, _cfo_request(req_id="req-rt-lg"))
    assert response.accepted is True
    assert response.audit_cylinder_id is not None
    assert response.audit_cylinder_id.startswith("capture_")
    # Confirm the handler is LangGraph-wrapped (not the plain class)
    assert type(ctx.handlers["cfo_agent"]).__name__ == "CFOAgentGraph"


@pytest.mark.skipif(
    not Path("/home/kmangum/Tiger_1a/cylinders/seal.sh").exists(),
    reason="Tiger chain seal.sh not present on this host",
)
def test_runtime_can_bind_to_real_tiger_seal_sh(seed_dir: Path) -> None:
    """Smoke test: the runtime can construct against the real Tiger seal.sh.

    This does NOT call seal — only verifies the binding succeeds. Sealing
    a test entry into the real chain is reserved for an explicit
    integration run, not the test suite (production chain integrity).
    """
    ctx = build_runtime_context(
        seed_dir=seed_dir,
        seal_sh_path="/home/kmangum/Tiger_1a/cylinders/seal.sh",
    )
    assert ctx.auditor is not None
    assert ctx.cost_meter is not None
    assert ctx.receipt_minter is not None
    # Adapter exists and points at the real seal.sh
    adapter = ctx.auditor._adapter  # noqa: SLF001
    assert "Tiger_1a/cylinders/seal.sh" in str(adapter._seal_sh)  # noqa: SLF001


# ∞Δ∞ Runtime integration seal — real subprocess, no fakes ∞Δ∞
