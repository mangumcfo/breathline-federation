"""Synthesis-agent frameworks — SYNTHESIS (Book 12).

Public surface for the orchestrator framework.
"""
from roles.synthesis_agent.frameworks.synthesis import (
    ExecutiveBrief,
    PeerInvocationResult,
    SynthesisInputError,
    apply_synthesis,
)

__all__ = [
    "apply_synthesis",
    "ExecutiveBrief",
    "PeerInvocationResult",
    "SynthesisInputError",
]
