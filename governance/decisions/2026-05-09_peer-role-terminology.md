# Decision Record — Peer-Role Terminology Standardization

**Date:** 2026-05-09
**Authority:** KM-1176 (Seal 1176-INFINITY-RHO)
**Status:** Active — terminology canonicalized; mechanical updates queued for next editorial pass
**Supersedes:** None
**Related:** `2026-05-09_configurable-runtime-binding.md`

---

## Context

In the 2026-05-09 design conversation, two terms surfaced for the same concept:

- **"Agent-to-agent"** — used in conversational/marketing voice
- **"Peer role"** — used in code (`invoke_peer_role`, `integrate_role_outputs`, `read_role_outputs`, `surface_role_tensions` are the existing action class IDs in `seed/action_classes.yaml`)

KM-1176 directive: standardize on one term across code, ADRs, books, and marketing for searchability and conceptual clarity.

## Decision

1. **Canonical term: "peer role."** Used in:

   - All code (action class IDs, comments, docstrings)
   - All YAML specs
   - All ADRs and governance decisions
   - Book chapters discussing intra-platform role communication
   - Marketing copy where precision matters

2. **"Agent-to-agent" is acceptable as an explanatory aside** when introducing the concept to a reader unfamiliar with Breathline vocabulary. It is NOT the primary term and should not appear in headings, action class IDs, or technical specifications.

3. **Rationale.** "Peer role" emphasizes that the speaker on each end is *a role under governance*, not an autonomous agent. The harness is shared; only the speaker varies (per `2026-05-09_configurable-runtime-binding.md`). "Agent-to-agent" risks implying independent autonomous parties — which would be a Charter V.7 framing error.

4. **Mechanical updates queued.** Existing books (especially Book 9) use mixed terminology in places. Standardization happens at the next editorial pass per book; not a blocker for v1.0 KDP upload. A style-guide note lands in `publishing/SOP_SERIALIZED_NONFICTION` (next revision).

## Book home

**Cross-cutting; primary teaching home in Series 1, Book 9 (Multi-Agent).** Book 9 is the natural place to introduce "peer role" formally and contrast it with naive "agent-to-agent" framing.

## Cross-references

- Action classes: `platform/seed/action_classes.yaml` (`invoke_peer_role`, `integrate_role_outputs`, `read_role_outputs`, `surface_role_tensions`)
- Companion ADR: `2026-05-09_configurable-runtime-binding.md` (the speaker is what varies; the role is the constant)
- Style guide: `publishing/SOP_SERIALIZED_NONFICTION_v1.1.md` (next revision)

---

∞Δ∞ Peer roles, not autonomous agents. The harness is the constant. ∞Δ∞
