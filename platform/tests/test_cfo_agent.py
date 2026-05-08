"""Tests for CFO-agent — Book 1 FORECAST framework.

Covers both the framework-level FORECAST loop and the RoleHandler
integration. Hermetic: no LLM, no network. Phase 3 deterministic core.
"""
from __future__ import annotations

import pytest

from platform_layer.plugin_interface import PlugInRequest
from roles.cfo_agent import CFOAgent
from roles.cfo_agent.frameworks.forecast import (
    ForecastInputError,
    apply_forecast,
)


def _sample_payload(horizon: int = 4) -> dict:
    return {
        "financial_data": {
            "revenue": [100.0, 105.0, 110.0, 115.0],
            "expenses": [80.0, 82.0, 84.0, 86.0],
            "market_signals": {"macro_index": 1.02},
        },
        "forecast_horizon": horizon,
    }


# -----------------------------------------------------------------------------
# Framework-level
# -----------------------------------------------------------------------------
def test_forecast_produces_three_scenarios() -> None:
    artifact = apply_forecast(_sample_payload())
    names = {s.name for s in artifact.scenarios}
    assert names == {"baseline", "upside", "downside"}
    for s in artifact.scenarios:
        assert s.horizon_periods == 4
        assert len(s.projected_revenue) == 4
        assert len(s.projected_expenses) == 4
        assert len(s.projected_net) == 4


def test_forecast_executes_all_eight_steps() -> None:
    artifact = apply_forecast(_sample_payload())
    assert artifact.framework_steps_executed == [
        "Forecast", "Observe", "Reconcile", "Explain",
        "Calibrate", "Adjust", "Surface", "Translate",
    ]


def test_forecast_flags_missing_market_signals() -> None:
    payload = _sample_payload()
    del payload["financial_data"]["market_signals"]
    artifact = apply_forecast(payload)
    assert any("market_signals" in flag for flag in artifact.assumptions_flagged)


def test_forecast_flags_thin_history() -> None:
    payload = _sample_payload()
    payload["financial_data"]["revenue"] = [100.0]  # only 1 point
    artifact = apply_forecast(payload)
    assert any("revenue_history_thin" in f for f in artifact.assumptions_flagged)


def test_forecast_uncertainty_bounds_present() -> None:
    artifact = apply_forecast(_sample_payload())
    assert "relative_sigma" in artifact.uncertainty_bounds
    assert "scenario_spread_pct" in artifact.uncertainty_bounds
    assert artifact.uncertainty_bounds["relative_sigma"] >= 0


def test_forecast_rejects_missing_required_inputs() -> None:
    with pytest.raises(ForecastInputError):
        apply_forecast({"forecast_horizon": 4})  # no financial_data


def test_forecast_rejects_invalid_horizon_zero() -> None:
    with pytest.raises(ForecastInputError):
        apply_forecast(_sample_payload(horizon=0))


def test_forecast_rejects_invalid_horizon_too_large() -> None:
    with pytest.raises(ForecastInputError):
        apply_forecast(_sample_payload(horizon=999))


def test_forecast_rejects_non_dict_financial_data() -> None:
    with pytest.raises(ForecastInputError):
        apply_forecast({"financial_data": "not-a-dict", "forecast_horizon": 4})


# -----------------------------------------------------------------------------
# RoleHandler integration
# -----------------------------------------------------------------------------
def test_cfo_agent_process_returns_produced_artifact() -> None:
    agent = CFOAgent()
    request = PlugInRequest(
        request_id="req-cfo-001",
        principal_id="kmangum",
        role_target="cfo_agent",
        action_class="produce_forecast_artifact",
        payload=_sample_payload(),
    )
    result = agent.process(request)
    assert result["status"] == "produced"
    assert result["role_id"] == "cfo_agent"
    assert result["framework"] == "FORECAST"
    assert result["principal_id"] == "kmangum"  # SOURCE: end-to-end
    assert result["request_id"] == "req-cfo-001"
    assert "forecast_artifact" in result
    assert len(result["forecast_artifact"]["scenarios"]) == 3


def test_cfo_agent_refuses_malformed_payload() -> None:
    agent = CFOAgent()
    request = PlugInRequest(
        request_id="req-cfo-002",
        principal_id="kmangum",
        role_target="cfo_agent",
        action_class="produce_forecast_artifact",
        payload={"financial_data": "not a dict"},  # malformed
    )
    result = agent.process(request)
    assert result["status"] == "refused"
    assert "invalid_forecast_inputs" in result["refusal_reason"]
    assert result["principal_id"] == "kmangum"  # principal preserved on refusal


def test_cfo_agent_preserves_principal_across_requests() -> None:
    agent = CFOAgent()
    for principal in ("alice", "bob", "kmangum"):
        request = PlugInRequest(
            request_id=f"req-{principal}",
            principal_id=principal,
            role_target="cfo_agent",
            action_class="produce_forecast_artifact",
            payload=_sample_payload(),
        )
        result = agent.process(request)
        assert result["principal_id"] == principal


# ∞Δ∞ CFOAgent test seal — produced + refused paths verified, principal_id flows ∞Δ∞
