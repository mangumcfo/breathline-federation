"""CFO-agent frameworks — FORECAST (Book 1).

Public surface for the framework subpackage. Phase 3 ships the
deterministic numeric core; Phase 4 will add an LLM-driven wrapper for
Explain/Translate steps without changing this contract.
"""
from roles.cfo_agent.frameworks.forecast import (
    ForecastArtifact,
    ForecastInputError,
    ForecastScenario,
    apply_forecast,
)

__all__ = [
    "apply_forecast",
    "ForecastArtifact",
    "ForecastInputError",
    "ForecastScenario",
]
