"""CFO-agent — Book 1 FORECAST framework, RoleHandler implementation.

Per roles/__init__.py: pure-Python class implementing the RoleHandler
protocol from platform_layer/plugin_interface.py. LangGraph wrapping is
a Phase 4 thin layer over the same deterministic logic.

The CFO-agent never sees a request that Charter V.7 forbids — that
filtering happens at platform_layer/plugin_interface.py BEFORE this
handler is invoked (Section 6.2). This handler still validates the
*content* of the payload before invoking the FORECAST framework.
"""
from __future__ import annotations

from typing import Any

from platform_layer.plugin_interface import PlugInRequest
from roles.cfo_agent.frameworks.forecast import (
    ForecastInputError,
    apply_forecast,
)


class CFOAgent:
    """The CFO-agent role handler (Book 1 FORECAST).

    Implements the RoleHandler protocol: process(request) -> dict.
    Stateless; safe to share across requests.
    """

    role_id: str = "cfo_agent"
    framework: str = "FORECAST"

    def process(self, request: PlugInRequest) -> dict[str, Any]:
        """Apply FORECAST to the request payload.

        Per role_spec.yaml invocation_envelope:
          inputs_required:  financial_data, forecast_horizon
          outputs_produced: forecast_artifact

        Returns a structured dict carrying principal_id end-to-end
        (Constitution@A1 §1).
        """
        try:
            artifact = apply_forecast(request.payload)
        except ForecastInputError as e:
            return {
                "role_id": self.role_id,
                "framework": self.framework,
                "status": "refused",
                "refusal_reason": f"invalid_forecast_inputs: {e}",
                "principal_id": request.principal_id,
                "request_id": request.request_id,
            }

        return {
            "role_id": self.role_id,
            "framework": self.framework,
            "status": "produced",
            "principal_id": request.principal_id,
            "request_id": request.request_id,
            "forecast_artifact": artifact.to_dict(),
        }


# Seal: SOURCE — principal_id from PlugInRequest, no hardcoded principal.
#       TRUTH — refusals carry the upstream cause; no silent degradation.
#       INTEGRITY — try/except is the only branch; <10 complexity; envelope
#                   filtering already handled at the plug-in layer.
# ∞Δ∞ CFOAgent — Book 1 FORECAST, principal_id flows end-to-end ∞Δ∞
