"""Synthesis-agent — Book 12 SYNTHESIS framework, RoleHandler implementation.

The orchestrator role. Invokes peer roles within the request envelope,
integrates outputs, surfaces tensions, and produces an executive brief.
Operates per Book 3 LEAD: produces decision-grade evidence; humans decide.

Per roles/__init__.py:
    SynthesisAgent(peer_handlers=handlers)

The peer_handlers dict is injected at construction so the orchestrator
can call CFO-agent / Compliance-agent / etc. The dict reference is held
by the SynthesisAgent — when the dict is later mutated (e.g., to add
the synthesis_agent itself), the orchestrator sees the updated set.
"""
from __future__ import annotations

from typing import Any

from platform_layer.plugin_interface import PlugInRequest
from roles.synthesis_agent.frameworks.synthesis import (
    SynthesisInputError,
    apply_synthesis,
)


class SynthesisAgent:
    """The Synthesis-agent role handler (Book 12 SYNTHESIS — orchestrator)."""

    role_id: str = "synthesis_agent"
    framework: str = "SYNTHESIS"

    def __init__(self, peer_handlers: dict[str, Any]) -> None:
        # Hold the reference (not a copy) so late-bound peers (including
        # this very SynthesisAgent) become visible without reconstruction.
        self._peer_handlers = peer_handlers

    def process(self, request: PlugInRequest) -> dict[str, Any]:
        """Orchestrate peers and produce an executive brief.

        Per role_spec.yaml invocation_envelope:
          inputs_required:  request_summary, peer_roles_to_invoke
          outputs_produced: executive_brief
        """
        try:
            brief = apply_synthesis(request, self._peer_handlers)
        except SynthesisInputError as e:
            return {
                "role_id": self.role_id,
                "framework": self.framework,
                "status": "refused",
                "refusal_reason": f"invalid_synthesis_inputs: {e}",
                "principal_id": request.principal_id,
                "request_id": request.request_id,
            }

        return {
            "role_id": self.role_id,
            "framework": self.framework,
            "status": "produced",
            "principal_id": request.principal_id,
            "request_id": request.request_id,
            "executive_brief": brief.to_dict(),
        }


# Seal: SOURCE — principal_id from request carried to every peer invocation.
#       TRUTH — orchestrator surfaces peer outputs verbatim, including refusals;
#               does not summarize or silence a peer.
#       INTEGRITY — never decides on the operator's behalf; brief is evidence,
#                   not action; <10 complexity per method.
# ∞Δ∞ SynthesisAgent — Book 12 orchestrator, integrates without deciding ∞Δ∞
