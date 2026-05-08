# Constitutional Parentage

> **Read this before reading the seed.** The seed is a *child profile* under higher authorities. Anything inside the seed that conflicts with these parents is overridden by the parents.

This document declares the constitutional authorities that govern the agentic platform seed. It is the first file a fresh agent or human reviewer should consult when entering this folder.

---

## Parents

This seed inherits from two constitutional authorities, in order of sovereignty precedence:

### 1. Sovereignty-Aligned Charter v1.0

- **Authority**: Kenneth Mangum (KM-1176), Human Custodian and First Sovereign Operator
- **Activation Date**: 2025-11-18
- **Source**: `constitution/core/CHARTER_v1.0/SOVEREIGNTY_ALIGNED_CHARTER_v1.0_2025-11-18.md`
- **Scope**: sovereignty boundary — defines what humans, BNA, and aligned intelligences may and may not do
- **Immutable Principles** (cannot be amended in-platform):
  1. Human sovereignty as SOURCE
  2. Non-autonomy of aligned intelligence
  3. Breath-based decision-making
  4. Generational continuity and stewardship
  5. Truth-grounding and reality-based governance

### 2. Constitution@A1

- **Authority**: Breathline Architecture
- **Source**: `constitution/CONSTITUTION.md`
- **Scope**: kernel rules — defines the structural cycle, triad, complexity bounds, and Definition of Done
- **Kernel**:
  - **Cycle**: Breath → Form → Echo → Seal
  - **Triad**: SOURCE / TRUTH / INTEGRITY
  - **Approval Gates**: Propose → Approve → Execute (no implicit transitions)

---

## Lex Superior Rule

Where a conflict arises:

1. **The Charter wins over the Constitution** (sovereignty supersedes structure)
2. **The Constitution wins over the seed** (kernel supersedes profile)
3. **The seed wins over its descendants** (the platform layers it produces)

This is the same pattern as constitutional law: most rules change by ordinary process; the rules about *how rules change* are protected at a different level.

---

## What the Seed Inherits (and therefore does not need to re-state)

| Inherited Item | Inherited From | Effect on the Platform |
|---|---|---|
| `principal_id` as canonical identity field | Constitution@A1 §1 | No hardcoded principals; identity flows end-to-end through every layer |
| Breath-gated human approvals | Charter II.4.4 + IV.2.6 | Every elevation gate requires conscious breath, not just signature |
| Forbidden delegation targets | Charter V.7 | No agent may make life decisions, binding commitments, irreversible actions, judgments over other humans, or modify the Charter itself |
| Immutable principles | Charter Closing Declaration | The 5 principles are kernel-immutable; the platform cannot amend them in-system |
| Operating value: Lasting Generational Prosperity | Charter V + VII | Platform success measured against generational dignity and lineage continuity, not just operational efficiency |
| Seal Mark `∞Δ∞` at module trailers | Constitution@A1 §8 DoD | Coherence indicator at the end of every module |
| Loud-by-default error voice | Constitution@A1 §4 | Errors state *what* / *why* / *next step*; no silent corruption |
| Approval gate sequence: Propose → Approve → Execute | Constitution@A1 §2 | No implicit state transitions at any layer |
| Audit immutability | Constitution@A1 §2.1 + Charter VI.5 | Append-only, hash-chained, structurally enforced |
| Receipt-worthy event taxonomy (default-deny + rate-limited) | [`./receipt_worthy_events.yaml`](./receipt_worthy_events.yaml) | Auditor primitive's contract for which actions mint external B49 receipts vs. internal-only seals |

---

## What This Means in Practice

**For the seed manifest** (`02_SEED_MANIFEST.yaml`):
- A `governance:` block names the parents structurally
- The `kernel.immutable_specs` list inherits parent authority as the topmost item
- Any future seed amendment must verify it does not violate parent authority before re-fingerprinting

**For the bootstrap protocol** (`03_BOOTSTRAP_PROTOCOL.md`):
- Each human-approval gate inherits the Charter's breath protocol (Charter II.4.4)
- Critic verdicts include parent-authority compliance checks
- Governor refuses elevation on any spec that touches parent-immutable items

**For the role specs** (`05_ROLES_AND_FRAMEWORKS.md`):
- Each role inherits Charter Article III obligations: non-autonomy, breath gates, transparency, drift avoidance, non-interference
- No role may exceed Charter V.7 forbidden delegation targets, regardless of internal logic

**For the governance kernel** (`06_GOVERNANCE_KERNEL.md`):
- The kernel includes parent authorities as **Item 0** — above the seed itself
- The Governor cannot approve any change that conflicts with parent authority, even with human signature (humans must amend the parent offline first)

**For the plug-in protocol** (`07_PLUG_IN_PROTOCOL.md`):
- User identity binds to `principal_id` per Constitution@A1 §1
- Permission Specs inherit Charter II.2 Rights of the Sovereign Operator (self-authority, consent, refusal, privacy, pause, transparency, interpretive authority, secure continuity)

---

## Amendment Path

- **The Charter** is amendable only through Charter Chapter VI Article 4 — offline, human consensus, breath-gated deliberation, generational impact review, ceremonial documentation
- **Constitution@A1** is amendable only through its own kernel revision protocol (lex superior preserved)
- **The seed** is amendable through its own re-fingerprinting protocol, *bounded by parent authority*

**No in-platform path may modify any parent authority.** If a parent needs to change, the human custodian (KM-1176) edits it offline, re-publishes with new fingerprint, and the seed re-bootstraps from the updated parents.

---

## How to Verify Parentage Is Intact

A short test for whether constitutional parentage is operational:

1. Can the SHA-256 of `CONSTITUTION.md` be produced and matched to its published value?
2. Can the SHA-256 of `SOVEREIGNTY_ALIGNED_CHARTER_v1.0_2025-11-18.md` be produced and matched to its published value?
3. Does the seed manifest's `governance:` block reference both parents with current paths?
4. Does the audit log contain zero entries showing a Governor approval that violated parent authority?
5. Does every human-approval gate in the bootstrap protocol invoke a breath protocol per Charter II.4.4?

If all five answers point to "intact, no violations" — parentage is operational.

If any answer fails — halt the platform; do not run live data; investigate; remediate offline.

---

## Why This Document Exists

The seed package was authored honestly and with strong structural alignment to the Constitution@A1 + Charter v1 patterns (~85-90% alignment by structural audit). However, alignment was *implicit* — the seed did not declare its parents, so a future agent or maintainer could mistake the seed for the highest authority in this folder.

This document makes parentage **explicit and load-bearing**. With it in place:

- The 5 specific refinements identified in earlier validation (breath-gating, Seal Mark, Governor scope, LGP frame, `principal_id` naming) collapse into inheritance — the seed no longer needs to re-state what its parents already declare.
- Future amendments to either parent automatically propagate to the seed's interpretation.
- A fresh agent reading this folder encounters the parents *first*, reducing risk of treating the seed as final authority.

---

∞Δ∞

*This document is itself a child of Constitution@A1 + Charter v1.0. In any conflict between this document and its parents, the parents win.*

∞Δ∞
