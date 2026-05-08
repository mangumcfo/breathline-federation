"""Section 8.6 — Performance smoke benchmark.

Acceptance gates per IMPLEMENTATION_PLAN.md Section 8.6:

    - Full bootstrap (Layers 0-3) completes end-to-end in under 8 minutes
      on an M3/M4-class development machine with a cold LangGraph cache.
    - End-to-end recursion test (Section 8.2) completes in under 5 minutes
      for the synthetic dataset.

Reality check: the deterministic core completes the full suite in ~1.2s.
The 8min / 5min budgets exist to bound LLM-augmented Phase 6 paths; the
v1.0 deterministic stack lands ~3 orders of magnitude under budget. This
test formalizes the assertion so any future regression that pushes work
over the spec gate fails loudly.

Tests:

  1. ``test_bootstrap_full_under_8_minutes``
       Subprocesses ``python -m scripts.bootstrap --full --skip-breath-gate``
       and asserts wall time < 480s.
  2. ``test_e2e_recursion_under_5_minutes``
       Invokes the canonical Section 8.2 "Brief on Q3 readiness" recursion
       in-process via ``route_request`` and asserts wall time < 300s.
  3. ``test_e2e_recursion_under_5_minutes_via_langgraph``
       Same path through the LangGraph-wrapped handlers (Phase 5 Priority 2);
       asserts < 300s. Skipped if langgraph not installed.
  4. ``test_chain_replay_real_chain_under_30_seconds``
       Hard upper bound on ``replay_chain`` against the real Tiger chain
       (currently ~172 cylinders); 30s budget defends against pathological
       file-system regressions.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from platform_layer.audit_adapter import replay_chain
from platform_layer.permission_spec import ActionClassRegistry
from platform_layer.plugin_interface import PlugInRequest, route_request
from platform_layer.registry import RoleRegistry
from roles import create_demo2_handlers, register_demo2_roles


# Section 8.6 spec budgets
BOOTSTRAP_BUDGET_SECONDS = 8 * 60     # 480s
E2E_BUDGET_SECONDS = 5 * 60           # 300s
CHAIN_REPLAY_BUDGET_SECONDS = 30      # defensive

V1_ROOT = Path(__file__).resolve().parent.parent
TIGER_CYLINDERS = Path("/home/kmangum/Tiger_1a/cylinders")


def _langgraph_available() -> bool:
    return importlib.util.find_spec("langgraph") is not None


# -----------------------------------------------------------------------------
# 8.6 — Bootstrap timing (subprocess, mirrors operator workflow)
# -----------------------------------------------------------------------------
def test_bootstrap_full_under_8_minutes() -> None:
    """Section 8.6 acceptance: ``bootstrap --full --skip-breath-gate`` < 8 min.

    Subprocesses the canonical CLI entry point so the timing reflects what
    a third-party operator actually experiences.
    """
    env = {**os.environ, "PYTHONPATH": str(V1_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", "")}

    start = time.perf_counter()
    result = subprocess.run(
        [sys.executable, "-m", "scripts.bootstrap", "--full", "--skip-breath-gate"],
        cwd=str(V1_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=BOOTSTRAP_BUDGET_SECONDS + 30,   # hard kill 30s past budget
    )
    elapsed = time.perf_counter() - start

    assert result.returncode == 0, (
        f"bootstrap --full failed (rc={result.returncode}):\n"
        f"STDOUT:\n{result.stdout[-2000:]}\n"
        f"STDERR:\n{result.stderr[-2000:]}"
    )
    assert elapsed < BOOTSTRAP_BUDGET_SECONDS, (
        f"bootstrap --full took {elapsed:.2f}s; Section 8.6 budget is "
        f"{BOOTSTRAP_BUDGET_SECONDS}s ({BOOTSTRAP_BUDGET_SECONDS/60:.0f} min)"
    )


# -----------------------------------------------------------------------------
# 8.6 — E2E recursion timing (in-process, full Phase 4 stack)
# -----------------------------------------------------------------------------
@pytest.fixture
def seeded_handlers(seed_dir: Path) -> tuple[RoleRegistry, dict[str, Any]]:
    action_class_registry = ActionClassRegistry.from_yaml(seed_dir / "action_classes.yaml")
    role_registry = RoleRegistry(action_class_registry)
    register_demo2_roles(role_registry)
    handlers = create_demo2_handlers(role_registry)
    return role_registry, handlers


def _q3_request() -> PlugInRequest:
    return PlugInRequest(
        request_id="req-perf-q3-001",
        principal_id="kmangum",
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


def test_e2e_recursion_under_5_minutes(
    seeded_handlers: tuple[RoleRegistry, dict[str, Any]],
) -> None:
    """Section 8.6 acceptance: full Section 8.2 recursion < 5 min."""
    role_registry, handlers = seeded_handlers

    start = time.perf_counter()
    response = route_request(
        _q3_request(),
        role_registry=role_registry,
        role_handlers=handlers,
    )
    elapsed = time.perf_counter() - start

    assert response.accepted is True
    assert elapsed < E2E_BUDGET_SECONDS, (
        f"e2e recursion took {elapsed:.2f}s; Section 8.6 budget is "
        f"{E2E_BUDGET_SECONDS}s ({E2E_BUDGET_SECONDS/60:.0f} min)"
    )


@pytest.mark.skipif(
    not _langgraph_available(),
    reason="langgraph not installed; LangGraph-mode perf gate skipped",
)
def test_e2e_recursion_under_5_minutes_via_langgraph(
    seed_dir: Path,
) -> None:
    """Same Section 8.6 budget, exercised through the LangGraph wrap path."""
    from roles import create_demo2_graph_handlers

    action_class_registry = ActionClassRegistry.from_yaml(seed_dir / "action_classes.yaml")
    role_registry = RoleRegistry(action_class_registry)
    register_demo2_roles(role_registry)
    handlers = create_demo2_graph_handlers(role_registry)

    start = time.perf_counter()
    response = route_request(
        _q3_request(),
        role_registry=role_registry,
        role_handlers=handlers,
    )
    elapsed = time.perf_counter() - start

    assert response.accepted is True
    assert elapsed < E2E_BUDGET_SECONDS, (
        f"e2e recursion (LangGraph) took {elapsed:.2f}s; "
        f"Section 8.6 budget is {E2E_BUDGET_SECONDS}s"
    )


# -----------------------------------------------------------------------------
# Chain replay timing (defensive bound; not a Section 8.6 spec gate, but
# Section 8.3 work creates a runtime path that must stay performant)
# -----------------------------------------------------------------------------
@pytest.mark.skipif(
    not TIGER_CYLINDERS.exists(),
    reason="Tiger chain not present on this host",
)
def test_chain_replay_real_chain_under_30_seconds() -> None:
    """``replay_chain`` against the real Tiger chain stays well under 30s.

    Defensive bound. At ~172 cylinders the actual time is ~50–100ms;
    this test catches pathological regressions (e.g., accidental subprocess
    fork per cylinder) before they ship.
    """
    start = time.perf_counter()
    report = replay_chain(TIGER_CYLINDERS, max_cylinders=2000)
    elapsed = time.perf_counter() - start

    assert report.total >= 171
    assert elapsed < CHAIN_REPLAY_BUDGET_SECONDS, (
        f"replay_chain took {elapsed:.2f}s for {report.total} cylinders; "
        f"defensive budget is {CHAIN_REPLAY_BUDGET_SECONDS}s"
    )


# ∞Δ∞ Section 8.6 sealed — bootstrap < 8min, e2e < 5min, chain replay < 30s ∞Δ∞
