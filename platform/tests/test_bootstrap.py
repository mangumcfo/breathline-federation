"""Tests for ``scripts/bootstrap.py``.

Verifies the bootstrap CLI can:

  - Run constitutional verification (--verify-only) and exit cleanly
  - Bootstrap to Layer 1 (default) — kernel only
  - Bootstrap to Layer 3 (--full) — kernel + platform + roles
  - Bootstrap to Layer 3 with LangGraph wrap (--full --use-langgraph)

Hermetic: --skip-breath-gate avoids interactive prompts; default seed
dir is the in-repo seed/.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

import scripts.bootstrap as bootstrap_module
from scripts.bootstrap import main as bootstrap_main


# Ensure scripts.bootstrap can find the seed at the repo's seed/ even
# when pytest's working dir varies; the script resolves seed_path relative
# to argv. Tests pass an absolute --seed.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SEED = str(_REPO_ROOT / "seed")


def _run_main(*args: str, capsys=None) -> int:
    """Invoke bootstrap_main with the given args."""
    return bootstrap_main(list(args))


def test_bootstrap_verify_only_exits_clean(capsys):
    rc = _run_main("--seed", _SEED, "--verify-only")
    assert rc == 0
    out = capsys.readouterr().out
    assert "constitutional verification" in out.lower()
    assert "All 5 constitutional verification tests passed" in out
    # Verify-only must NOT instantiate Layer 1
    assert "Layer 1 (kernel) instantiated" not in out


def test_bootstrap_layer_1_with_skip_gate(capsys):
    rc = _run_main("--seed", _SEED, "--skip-breath-gate")
    assert rc == 0
    out = capsys.readouterr().out
    assert "Layer 1 (kernel) instantiated" in out
    assert "Constructor" in out
    assert "Critic" in out
    assert "Auditor" in out
    assert "Governor" in out
    # Without --full, Layer 2/3 must NOT instantiate
    assert "Layer 2 (platform) + Layer 3 (roles) instantiated" not in out


def test_bootstrap_full_to_layer_3(capsys):
    rc = _run_main("--seed", _SEED, "--skip-breath-gate", "--full")
    assert rc == 0
    out = capsys.readouterr().out
    assert "Layer 1 (kernel) instantiated" in out
    assert "Layer 2 (platform) + Layer 3 (roles) instantiated" in out
    # All three Demo 2 roles registered
    assert "cfo_agent" in out
    assert "synthesis_agent" in out
    assert "compliance_agent" in out
    # All four Phase 4 integrations wired
    assert "auditor:" in out
    assert "critic:" in out
    assert "cost_meter:" in out
    assert "receipt_minter:" in out


@pytest.mark.skipif(
    importlib.util.find_spec("langgraph") is None,
    reason="langgraph not installed",
)
def test_bootstrap_full_with_langgraph(capsys):
    rc = _run_main(
        "--seed", _SEED, "--skip-breath-gate", "--full", "--use-langgraph"
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "Layer 2 (platform) + Layer 3 (roles) instantiated" in out
    assert "use_langgraph=True" in out
    assert "LangGraph wrap" in out


# ∞Δ∞ Bootstrap CLI test seal — Phase 5 Priority 3 ∞Δ∞
