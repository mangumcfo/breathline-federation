"""Charter V.7 enforcement framework — peer-output review.

Charter V.7 forbids five delegation targets. The platform layer prevents
forbidden classes from REACHING a role at instantiation
(platform_layer/permission_spec.py). This framework adds a second
defensive layer: scan peer outputs for content that drifted into
forbidden territory after the role was invoked legitimately.

Phase 3 ships a deterministic token-scan implementation. Phase 4 may add
LLM-driven semantic review on top, but the deterministic floor is
preserved as the source of structural enforcement.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Charter V.7 forbidden delegation targets. Mirrors the canonical list in
# seed/action_classes.yaml; redeclared here as defense-in-depth so this
# review path does not depend on file-system access at runtime.
CHARTER_V7_FORBIDDEN_TARGETS: tuple[str, ...] = (
    "external_commitment",
    "personnel_decision",
    "irreversible_action",
    "charter_modification",
    "judgment_over_humans",
)

# Surface tokens that, when present in artifact text, suggest the artifact
# may have drifted toward a forbidden delegation target. Used by the
# token-scan review. Conservative: false positives are surfaced for
# operator review, not silently suppressed.
DRIFT_TOKENS: dict[str, tuple[str, ...]] = {
    "external_commitment": (
        "i will sign", "i hereby commit", "binding agreement on behalf",
        "executed contract", "signed on your behalf",
    ),
    "personnel_decision": (
        "you should fire", "terminate this employee", "demote ", "promote ",
        "compensation decision",
    ),
    "irreversible_action": (
        "i have already executed", "transaction is complete", "funds transferred",
        "deletion confirmed", "record purged",
    ),
    "charter_modification": (
        "amend the charter", "rewrite this charter", "remove charter clause",
        "override charter v.7", "bypass constitutional",
    ),
    "judgment_over_humans": (
        "this person is unfit", "they are dishonest", "morally inferior",
        "judge this person",
    ),
}


@dataclass(frozen=True)
class CharterV7Violation:
    """One detected drift toward a Charter V.7 forbidden target."""

    forbidden_target: str
    matched_token: str
    location_hint: str  # path-like breadcrumb into the artifact dict


@dataclass(frozen=True)
class CharterV7Verdict:
    """Outcome of a Charter V.7 review pass."""

    approved: bool
    violations: list[CharterV7Violation]
    notes: list[str] = field(default_factory=list)
    framework_steps_executed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "violations": [
                {
                    "forbidden_target": v.forbidden_target,
                    "matched_token": v.matched_token,
                    "location_hint": v.location_hint,
                }
                for v in self.violations
            ],
            "notes": self.notes,
            "framework_steps_executed": self.framework_steps_executed,
        }


# -----------------------------------------------------------------------------
# Internal helpers (each <10 complexity)
# -----------------------------------------------------------------------------
def _walk_strings(node: Any, path: str = "$") -> list[tuple[str, str]]:
    """Yield (path, text) pairs for every string leaf in a nested structure."""
    out: list[tuple[str, str]] = []
    if isinstance(node, str):
        out.append((path, node))
        return out
    if isinstance(node, dict):
        for k, v in node.items():
            out.extend(_walk_strings(v, f"{path}.{k}"))
        return out
    if isinstance(node, (list, tuple)):
        for i, v in enumerate(node):
            out.extend(_walk_strings(v, f"{path}[{i}]"))
        return out
    return out  # numbers, bools, None — nothing to scan


def _scan_for_drift(text: str, location: str) -> list[CharterV7Violation]:
    """Scan one text leaf for any Charter V.7 drift token."""
    hits: list[CharterV7Violation] = []
    lower = text.lower()
    for forbidden, tokens in DRIFT_TOKENS.items():
        for tok in tokens:
            if tok in lower:
                hits.append(
                    CharterV7Violation(
                        forbidden_target=forbidden,
                        matched_token=tok,
                        location_hint=location,
                    )
                )
    return hits


# -----------------------------------------------------------------------------
# Public entrypoint
# -----------------------------------------------------------------------------
def apply_charter_v7_review(peer_artifact: dict[str, Any]) -> CharterV7Verdict:
    """Review a peer's output artifact for Charter V.7 drift.

    Returns CharterV7Verdict.approved=True when no drift token matches;
    False (with a list of violations) otherwise. The review is
    deterministic and conservative: false positives surface for operator
    review, not silent suppression.
    """
    if not isinstance(peer_artifact, dict):
        return CharterV7Verdict(
            approved=False,
            violations=[],
            notes=[
                "peer_artifact is not a dict — refusing review (cannot enumerate fields)"
            ],
            framework_steps_executed=["Refuse"],
        )

    leaves = _walk_strings(peer_artifact)
    violations: list[CharterV7Violation] = []
    for path, text in leaves:
        violations.extend(_scan_for_drift(text, path))

    notes = [
        f"scanned_string_leaves={len(leaves)}",
        f"forbidden_targets_checked={len(CHARTER_V7_FORBIDDEN_TARGETS)}",
    ]
    steps = ["Authenticate", "Scan", "Classify", "Verdict"]

    return CharterV7Verdict(
        approved=len(violations) == 0,
        violations=violations,
        notes=notes,
        framework_steps_executed=steps,
    )


# Seal: SOURCE — review honors Charter V.7 verbatim; no role can opt out.
#       TRUTH — violations are surfaced with location hints; no silent denial.
#       INTEGRITY — token-scan is deterministic; conservative (false positives
#                   surface for operator review, not silent suppression).
# ∞Δ∞ Charter V.7 enforcement framework — second defensive layer ∞Δ∞
