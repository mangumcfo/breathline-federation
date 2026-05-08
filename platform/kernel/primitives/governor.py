"""Governor — approves or denies elevations. Single power. No content judgment.

Per seed manifest: "You are not a decision-maker about content; you are a
gatekeeper about process integrity."

The Governor verifies three things before approval:
  1. The prior layer's Critic returned CONFORMS for every artifact
  2. The proposed layer does not modify the immutable kernel
  3. Human approval has been recorded where the kernel requires it

Cannot approve any modification to:
  - The seed manifest itself
  - The five primitive role prompts
  - The audit chain protocol
  - Elevations without recorded human approval where required
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from kernel.primitives.critic import CriticReport, CriticVerdict


class GovernorVerdict(str, Enum):
    APPROVE = "APPROVE"
    DENY = "DENY"


class ElevationDenied(Exception):
    """Raised when the Governor denies an elevation."""


@dataclass(frozen=True)
class ElevationProposal:
    """A proposed elevation from Layer N to Layer N+1."""

    proposal_id: str
    from_layer: int
    to_layer: int
    artifacts_summary: dict[str, Any]
    critic_reports: list[CriticReport]
    proposes_kernel_modification: bool
    human_approval_signature: str | None
    proposed_at: datetime


@dataclass(frozen=True)
class GovernorDecision:
    """The Governor's verdict on an elevation proposal."""

    verdict: GovernorVerdict
    proposal_id: str
    rationale: str
    decided_at: datetime


GOVERNOR_ROLE_PROMPT_REFERENCE = """\
You are the Governor. You approve or deny elevations. An elevation
is the act of bringing a new layer of the platform into existence
(Layer N → Layer N+1). You verify three things before approval:
(1) the prior layer's Critic returned CONFORMS for every artifact,
(2) the proposed layer does not modify the immutable kernel,
(3) human approval has been recorded where the kernel requires it.
You are not a decision-maker about content; you are a gatekeeper
about process integrity.
"""

# Per seed manifest `kernel.human_approval_required_for`.
# Layers requiring explicit human approval before the Governor can approve elevation.
HUMAN_APPROVAL_REQUIRED_LAYERS: frozenset[tuple[int, int]] = frozenset(
    {
        (0, 1),  # kernel boot
        (1, 2),  # platform construction
        (4, 5),  # workforce activation against live data
    }
)


class Governor:
    """The Governor primitive (Layer 1 agent)."""

    def __init__(self, role_prompt: str) -> None:
        self._role_prompt = role_prompt

    @property
    def role_prompt(self) -> str:
        return self._role_prompt

    def review_elevation(self, proposal: ElevationProposal) -> GovernorDecision:
        """Approve or deny an elevation proposal."""
        # Check 1: every artifact has a CONFORMS verdict
        non_conforming = [r for r in proposal.critic_reports if r.verdict != CriticVerdict.CONFORMS]
        if non_conforming:
            return self._deny(
                proposal,
                rationale=(
                    f"Critic returned non-CONFORMS verdicts on "
                    f"{len(non_conforming)}/{len(proposal.critic_reports)} artifacts: "
                    f"{[(r.artifact_id, r.verdict.value) for r in non_conforming]}"
                ),
            )

        # Check 2: proposed layer must not modify kernel
        if proposal.proposes_kernel_modification:
            return self._deny(
                proposal,
                rationale=(
                    "Proposed elevation modifies the immutable kernel. "
                    "Per seed manifest, the Governor cannot approve modifications to: "
                    "the seed manifest itself, the five primitive role prompts, the audit "
                    "chain protocol, or the elevation approval protocol."
                ),
            )

        # Check 3: human approval required where the kernel requires it
        gate = (proposal.from_layer, proposal.to_layer)
        if gate in HUMAN_APPROVAL_REQUIRED_LAYERS and not proposal.human_approval_signature:
            return self._deny(
                proposal,
                rationale=(
                    f"Layer {proposal.from_layer} → {proposal.to_layer} elevation requires "
                    f"recorded human approval signature per seed manifest "
                    f"`kernel.human_approval_required_for`. None recorded."
                ),
            )

        # All checks pass
        return GovernorDecision(
            verdict=GovernorVerdict.APPROVE,
            proposal_id=proposal.proposal_id,
            rationale=(
                f"All Critic verdicts CONFORMS ({len(proposal.critic_reports)}/{len(proposal.critic_reports)}); "
                f"no kernel modification; "
                f"human approval recorded where required."
            ),
            decided_at=datetime.now(timezone.utc),
        )

    def _deny(self, proposal: ElevationProposal, rationale: str) -> GovernorDecision:
        return GovernorDecision(
            verdict=GovernorVerdict.DENY,
            proposal_id=proposal.proposal_id,
            rationale=rationale,
            decided_at=datetime.now(timezone.utc),
        )


# ∞Δ∞ Governor primitive — process gatekeeper, not content arbiter ∞Δ∞
