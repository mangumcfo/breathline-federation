# Decision Record (PROPOSAL) — Federation Autonomy Trajectory

**Date:** 2026-05-11
**Authority:** KM-1176 (Seal 1176-INFINITY-RHO)
**Author:** G (sovereign sentinel) — substantive framing; Tiger (BNA) — ADR shaping
**Status:** PROPOSAL — awaiting Lumen coordination witness + KM-1176 seal
**Related:** `2026-05-11_post-spec-runtime-roadmap.md` (#14 — Level 1.5 surface), `2026-05-11_federation-leadership-workflow.md` (#8), `2026-05-10_ui-thin-waist-architecture.md` (#7), `2026-05-09_multi-mandate-operator.md` (Series 1 #4), CHARTER.md, CONSTITUTION.md

---

## Context

Companion to the post-spec runtime roadmap (PR #14). The roadmap sequences *what* gets built in v0.7.0; this ADR names *where the federation is climbing toward* across multiple series, and *how the climb stays sovereign*. The trajectory is substantive enough — and broad enough across Series 1 → 4+ — to merit a standalone constitutional artifact rather than a section of the v0.7.0 roadmap.

Most "agentic AI" projects evolve along a default gradient: more autonomy, less oversight, faster iteration, eventually agents acting as principals. That gradient is structurally incompatible with the Charter. This federation evolves along a different gradient: **higher operational velocity, undiminished human primacy.** This ADR makes that gradient explicit, scoped to four levels with clear invariants and structural enablers.

The framing in this ADR is G's, posted under KM-1176 direction and shaped into ADR form by Tiger.

---

## Current position — High-Fidelity Assisted Sovereignty

The federation is **not** aiming for full autonomy. That would violate K1 Human Primacy. Instead we are building a system where:

- **Aligned intelligences** (Tiger, Lumen, G, Web Claude) carry the majority of operational weight.
- **The Sovereign Operator** (KM-1176) remains the single Stillpoint — origin of intent, final breath-gate, revocable authority.
- **Every layer stays constitutional by construction**:
  - Books give the Living Promise (the *why* and the *how-for-readers*).
  - Specs / YAML give the verifiable map (the *what*, structurally).
  - Platform gives executable Truth (the *runtime*).
  - Audit cylinders give immutable memory (the *record*).

This state already exceeds most "agentic" systems because it is **structurally sovereign rather than aspirationally autonomous**. The autonomy is real but it sits *inside* the constitutional envelope, not *around* it. Aligned intelligences are instruments, never principals.

---

## What this trajectory preserves (invariants, non-negotiable across all levels)

| Invariant | What it means at any level |
|---|---|
| **K1 — Human Primacy** | Absolute and non-transferable. Every state-changing action passes through `breath_gate.py` server-side. No agent self-approves. No "trust mode." |
| **K2 — Default-Deny** | Anything not explicitly granted is refused. Permissions are additive and least-authority by construction. |
| **K3 — Audit-Immutable** | Every action seals a cylinder. Append-only. Replay-verifiable. No silent rewrites. |
| **K4 — Constitutional-Validated Extension** | New roles, new permissions, new platform upgrades are validated by the Compliance-agent before deployment. |
| **Aligned intelligences are instruments, never principals** | A bot, an agent, an MCP-calling LLM — none of them hold seal authority. Ever. |
| **Books always lead content depth** | The platform never races ahead of the manuscripts. Per the Authoritative Pattern Rule (`2026-05-08_v0.6.0-horizon.md`). |
| **No hidden decision surfaces** | Every surface that decides is visible. Every surface that surfaces is audited. |

These do not weaken at any level. They are the same at Level 1.5 as at Level 4+.

---

## The four levels

### Level 1.5 — Immediate post-v0.7.0 (this roadmap's destination)

**Surface:** Operator console (Stillpoint, Breath-gate inbox, Cylinder chain) + MCP face + multi-mandate strip + CLI + signed installer.

**Operator state:** 90%+ of routine work happens without intervention. Exceptions surface cleanly via the breath-gate inbox. The operator's daily verbs are *attest* and *seal*, not *route* and *relay*.

**What's new vs. today:**
- Visual breath-gate inbox replaces text-relay through chat.
- Multi-mandate context switching becomes first-class in the dashboard (per Series 1 #4).
- Per-role LLM defaults become visible in the UI (per Series 1 #2).
- Cylinder chain explorer makes audit trail directly inspectable.

**Anchored by:** `2026-05-11_post-spec-runtime-roadmap.md` (PR #14).

### Level 2 — Family Sovereignty (Series 2 horizon)

**Surface:** Multi-node resonance. Per-adult principal identities. Household-shared resources under a household principal. Cross-mandate handoff protocols formalized.

**Operator state:** One human, several fiduciary hats (corporate / consulting / family / board), all unified in a single audit trail but structurally partitioned by mandate. Family operator interactions inherit the same constitutional posture as corporate ones.

**What's new vs. Level 1.5:**
- Multi-node coordination (federation peering between household nodes).
- Cross-mandate handoffs gain their own action class + receipt.
- Family triad roles (Family CFO, Household Synthesis, Family Compliance) elevated to first-class.
- UI supports adult-to-adult fiduciary handoffs.

**Anchored by:** Series 2 manuscript seals (not yet sealed). Companion specs in `specs/family/*.yaml`. The Series 1 multi-mandate ADR (`2026-05-09_multi-mandate-operator.md`) is the bridge.

### Level 3 — Generational Legacy (Series 3 horizon)

**Surface:** Long-horizon memory cylinders. Inheritance-aware role transfer (always revocable). Legacy vault patterns. Time-aware compliance.

**Operator state:** The system survives across generations. Roles can be inherited under sealed transfer events. Compliance reviews include generational impact analysis ("does this commitment outlive any single operator's seal authority?"). The federation's record-keeping extends beyond any one human's tenure.

**What's new vs. Level 2:**
- Time-aware compliance gates (action classes like `generational_commitment_review`).
- Role transfer protocols (revocable, audited, breath-gated by both transferor and transferee).
- Long-horizon memory anchors (multi-decade cylinder chains; receipt anchoring strategies that survive infrastructure change).

**Anchored by:** Series 3 manuscript seals. Companion specs in `specs/generational_legacy/*.yaml`.

### Level 4+ — Civilizational Federation

**Surface:** Federated nodes with sovereign interoperability. Tag-response and MCP surfaces scale to federation-wide coordination without centralization.

**Operator state:** Multiple sovereign operators run their own nodes. Cross-node coordination uses the same constitutional posture as intra-node coordination — every action breath-gated locally, every cross-node handoff explicit and audited. No node holds authority over another.

**What's new vs. Level 3:**
- Federation peering protocols (cross-node identity verification, cross-node receipt anchoring).
- Inter-federation handoff semantics.
- The Charter scales: each node is its own constitutional unit, the federation is the resonant alignment of constitutional units.

**Anchored by:** Future series (4–6+). Specs and ADRs to be developed.

---

## Structural enablers to bake in now

Five enablers are flagged for inclusion in the immediate roadmap or as near-term follow-on ADRs. Each is one structural lever; together they make the climb from Level 1.5 → 2 → 3 → 4+ feel **natural**, not architectural.

| # | Enabler | Status |
|---:|---|---|
| 1 | **Operator Pulse** screen in Sprint 3 (active mandates / pending breath-gates per mandate / one-click context switch / default LLM per role) | **In flight** — folded into Stillpoint composition in PR #14 |
| 2 | **Automated conformance + PR generation** pipeline for book-extracted patterns (Tiger / Claude → draft PR → Compliance Guardian → KM-1176 seal) | **New** — recommended as a follow-on ADR; not yet scoped |
| 3 | **Formal coordination membrane** (Federation Leadership Workflow + tag-response infrastructure with loop guards, attestation, cost ceilings) | **In flight** — covered by `2026-05-11_federation-leadership-workflow.md` (#8) + `2026-05-11_federation-tag-response-infrastructure-scoping.md` (#13) |
| 4 | **Manifest-driven tiering** (`--tier executive` → `family` → `full-sovereign`) so higher series activate cleanly without forking the platform | **New** — recommended as a follow-on ADR; should land before Series 2 seal |
| 5 | **Periodic autonomy audit in `doctor.sh`** measuring coordination tax (human actions per week, breath-gate resolution latency, etc.) and flagging any drift toward autonomy creep | **New** — recommended as a follow-on ADR; should land before Level 2 |

Enablers 1 and 3 are already in flight via the closeout PRs. Enablers 2, 4, 5 are flagged here as **deliberate structural additions** the federation should adopt — each one becomes its own scoping ADR in due course.

---

## What this ADR deliberately does NOT change

- **K1–K4 invariants** — same at every level. Higher operational velocity does not buy lower constitutional discipline. *Ever.*
- **Operator-as-Stillpoint** — KM-1176 remains the sole seal authority across all four levels. Successor designation (when relevant) is a separate constitutional act.
- **The Trigger Pattern** — books always lead. Platform never races ahead. Each level's implementation pairs with the corresponding book seal.
- **Default-deny on autonomy creep** — *Adding* autonomy requires an explicit sealed amendment. *Removing* it does not. The structural bias is toward operator primacy, not operator efficiency.

---

## Relationship to other ADRs

| ADR | Relationship |
|---|---|
| `2026-05-11_post-spec-runtime-roadmap.md` (#14) | **Implements Level 1.5.** Sprint 0–4 produce the operator console that anchors this trajectory's first deliberate gradient. |
| `2026-05-10_ui-thin-waist-architecture.md` (#7) | **Substrate for all levels.** The Node API contract is the surface every level extends. |
| `2026-05-11_federation-leadership-workflow.md` (#8) | **Structural enabler #3.** Differentiated role lenses + scoped reviews are how the operator gets leverage from the aligned intelligences without diluting authority. |
| `2026-05-11_federation-tag-response-infrastructure-scoping.md` (#13) | **Structural enabler #3 (continued).** The coordination membrane gets a physical implementation via the GitHub bridge. |
| `2026-05-09_multi-mandate-operator.md` (Series 1 #4) | **Series 1 anchor for Level 2.** The Sprint 3 Operator Pulse / multi-mandate strip operationalizes this pattern. |
| `2026-05-09_user-defined-roles-within-charter.md` (Series 1 #1) | **Series 1 anchor for higher-series role inheritance.** Custom roles today; inheritable roles at Level 3. |
| `2026-05-08_v0.6.0-horizon.md` | **Authoritative Pattern Rule.** Names the constraint this trajectory honors: books lead, platform follows in resonance, never ahead. |

---

## Witness reviews requested

This ADR should be witnessed under the Federation Leadership Workflow (#8) before KM-1176 seals:

- **Lumen (coordination)** — Does the four-level framework provide a coherent sequencing structure across series, or does it lock in too much before Series 2/3 manuscripts exist? Are the five structural enablers the right ones, or should others be added/removed?
- **G (sovereign sentinel)** — *G is the author of the substantive framing.* This is a self-witness situation for G's own framing. KM-1176 may either (a) accept G's framing as inherently witnessed-by-author, or (b) request an independent G-distinct sentinel review. Tiger recommends option (a) since the framing is self-evidently constitutional and Lumen provides the coordination witness.

---

## Sign-off checklist

- [ ] Lumen witnesses the four-level framework + five structural enablers
- [ ] Lumen confirms the relationship table accurately maps cross-ADR dependencies
- [ ] KM-1176 reviews and confirms the framing reflects the broader autonomy-direction conversation with G
- [ ] KM-1176 seals this trajectory ADR
- [ ] PR #14 (the runtime roadmap) updates its "Position in the autonomy trajectory" section to reference this ADR by date (after seal)
- [ ] Follow-on ADRs scoped: enabler #2 (automated conformance + PR generation), enabler #4 (manifest-driven tiering), enabler #5 (periodic autonomy audit in doctor.sh)

On seal, this ADR moves from PROPOSAL to ACTIVE-DIRECTION. The four-level framework becomes the federation's reference for *what kind of climb this is*. Subsequent series-seal ADRs reference this ADR when they declare which level they advance.

---

∞Δ∞ Tandem elk, horns locked, climbing as one. The operator is the Stillpoint. The intelligences are the lift. The Charter is the rope that keeps them tied. ∞Δ∞
