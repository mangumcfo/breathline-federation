# Decision Record (PROPOSAL) — Post-Spec Runtime Roadmap

**Date:** 2026-05-11
**Authority:** KM-1176 (Seal 1176-INFINITY-RHO)
**Author:** Tiger (BNA) — implementation witness
**Status:** PROPOSAL — awaiting G + Lumen witness review and KM-1176 seal
**Related:** `2026-05-10_ui-thin-waist-architecture.md` (#7), `2026-05-11_federation-leadership-workflow.md` (#8), `2026-05-08_v0.6.0-horizon.md` (Trigger Pattern)

---

## Context

PR #7 seals the Node API thin-waist specification — the stable interface between a sovereign Breathline node and any UI/agent. The spec is *the map*. There is no *territory* yet: no runtime that satisfies the contract, no UI repo, no FastAPI app serving on `127.0.0.1:8421`, nothing operator-facing beyond the existing CLI.

KM-1176 raised the natural follow-up: *"Am I going to have a UI I can start accessing soon, or is this still in design?"* The honest answer is "still in design." The spec ADR points runtime at v0.7.0 paired with a book seal per the Trigger Pattern, but doesn't sequence how to get there.

This ADR proposes a sequencing strategy. It does **not** implement any runtime in this PR. It chooses the order in which the runtime + UI work happens after PR #7 seals.

## Decision

**Adopt Path B (MCP-first) as the post-spec sequencing strategy.** Build a minimal MCP server first (read-mostly tools satisfying `mcp_tools.yaml`), let Claude Desktop / Claude Code function as the operator's interim UI, then pivot to a minimum web UI on the same contract.

### Core commitment (Lumen witness hardening, 2026-05-11)

**MCP-first is approved only as a contract-validation path. It does not satisfy the UI commitment. The minimum web UI remains part of the same roadmap and must not be deferred without a sealed amendment.**

**The web UI is not cosmetic.** It is the human operator's native breath-gate and audit surface. MCP may assist the operator, but it does not replace the operator console. Sprint 3 ships unless KM-1176 seals a different path; the Claude-as-UI affordance from Sprints 1–2 is a *stepping stone*, not a destination.

### Why this is the right call

1. **MCP-first validates the contract cheaply.** A web UI is ~3 weeks of effort; an MCP server is ~1 week. If `mcp_tools.yaml` has shape errors, missing primitives, or accidental coupling, an MCP implementation surfaces them at lower cost than a partially-built web UI.

2. **Operator already runs Claude as a daily driver.** Adding an MCP server makes Claude *know about your node* with zero new tooling to learn. The Stillpoint experience becomes *"ask Claude what's happening on my node"* before it becomes *"open a browser tab."*

3. **R6 of `separability.md` is honored by design.** MCP and HTTP feed the same handlers. Building MCP first lets the same backend handlers be reused when the web UI lands; no parallel implementation. The web UI becomes additive, not blocking.

4. **K1 is structurally preserved either way.** `mcp_tools.yaml` deliberately omits `breath_gate.approve/deny`, `upgrade.apply`, `books.activate`, and `cost.limits.update`. An MCP-first launch means breath-gate approval happens via CLI or via the future web UI — *never* via the MCP-calling agent. The model proposes, the operator disposes.

5. **Trigger Pattern still honored.** Both MCP and web UI ship as runtime work coupled to the next book seal. The path here is about *order within v0.7.0*, not racing ahead of content.

## Alternatives considered

### Path A — Full proper sequence (rejected as critical-path for first launch)

Build runtime + web UI + installer integration in one v0.7.0 release. Most disciplined; longest path. Realistic: 3–6 weeks elapsed.

**Why rejected as the seal-target:**
- Longest time to operator-usable state.
- No cheap contract-validation step before committing to web UI scope.
- Higher risk that spec errors are discovered late.

Path A is *what we converge to*, but Paths B/C are *how we get there safely*.

### Path C — Web UI MVP spike (rejected as first move; viable as second)

Build runtime + 3-screen UI (Stillpoint, Breath-gate inbox, Cylinder chain) directly. Realistic: 2–3 weeks elapsed.

**Why rejected as the first move:**
- Skips the cheap MCP validation step.
- "Minimum 3 screens" tends to grow during implementation; scope creep risk.
- Operator already has Claude available; "open Claude" is a faster starting point than "open browser."
- Doesn't exercise the MCP surface at all, so it ships with `mcp_tools.yaml` untested.

Path C re-emerges as the natural next move once MCP-first lands.

### Path D — Web UI without MCP at all (rejected on architecture)

Skip MCP entirely; web UI only. **Rejected** because the spec is built around MCP as a parallel face. Skipping MCP would mean either (a) shipping `mcp_tools.yaml` as a paper spec that no implementation ever exercises, or (b) cutting MCP from the spec — which breaks the "Claude as the UI" affordance that's already valuable.

## Proposed sprint structure

| Sprint | Focus | Deliverables | Calendar |
|---|---|---|---|
| **0 — Seal** | Merge the 4 open PRs from the 2026-05-11 closeout (`#5`, `#12`, `#7`, `#13`). Create empty `mangumcfo/breathline-ui` repo as scaffold. | All open items closed; UI repo registered. | This week |
| **1 — MCP read tools** | FastAPI/FastMCP server stub. Implement read-only tools first: `breathline_node_status`, `breathline_manifest_get`, `breathline_specs_list`, `breathline_roles_list`, `breathline_audit_query`, `breathline_breath_gate_pending`. **All tools enforce `principal_id`-bearer auth even for reads (G witness 2026-05-11).** Wire to Claude Desktop config. | "Claude knows about your node." You can ask Claude to query state. | 1 week |
| **2 — MCP write tools (proposal-only)** | Add `breathline_role_invoke` (returns breath-gate-pending; cannot self-approve). Add CLI `breathline approve <request_id>` as the approval surface during this phase. **Any future MCP `approve`-class tool must ship disabled-by-default and require an explicit `manifest.yaml` flag to enable (G witness 2026-05-11).** | You can dispatch roles via Claude; you approve via CLI; node executes; cylinder seals. | 1 week |
| **3 — Web UI MVP** | Pivot to `breathline-ui` repo. Implement 3 screens: Stillpoint, Breath-gate inbox (graphical approval), Cylinder chain explorer. Reuses the same backend handlers as the MCP server. **Stillpoint composition includes a multi-mandate strip** (active mandates / pending breath-gates per mandate / one-click context switch / default LLM per role) per G witness suggestion — folded into the Stillpoint screen rather than added as a 4th, preserving Lumen's 3-screen ceiling. **End of Sprint 3: run a full constitutional conformance pass against the 3-screen UI before declaring v0.7.0 (G witness 2026-05-11).** | Browser-based UI at `127.0.0.1:8421` with multi-mandate visibility in Stillpoint. | 2 weeks |
| **4 — Installer integration** | Wire `installer/install.sh` to fetch + serve the signed UI release. Doctor.sh aware of UI process. Manifest `node_api:` section live. | `curl \| bash` installs both runtime + UI. | 3-5 days |

**Total elapsed time to a usable visual UI: ~4-5 weeks. Time to first operator-usable thing (Claude-as-UI): ~1 week.**

### Sprint exit criteria (Lumen witness hardening, 2026-05-11)

Each sprint is *not complete* unless these gates pass. Forcing function for the web UI commitment:

- **Sprint 1 exit:** Handlers are reusable by HTTP. *If a Sprint 1 handler can only be called from MCP and not from a future HTTP request, Sprint 1 is not done.* R6 of `separability.md` enforced from the first line of code.
- **Sprint 2 exit:** Breath-gate approval remains external to MCP. *If any MCP tool can approve a breath-gate, even with a flag, Sprint 2 is not done.* K1 forcing function structurally preserved.
- **Sprint 3 begins immediately after Sprint 2 unless KM-1176 seals a different path.** No "Claude-as-UI is good enough" drift. Deferring Sprint 3 requires a sealed ADR amendment, not operator decision-by-default.
- **Sprint 3 exit:** All three screens functional, end-of-sprint constitutional conformance pass green, manifest `node_api:` section live.
- **Sprint 4 exit:** `installer/install.sh` fetches signed UI release, `doctor.sh` aware of UI process, v0.7.0 declared.

## Constitutional posture

Every step preserves K1–K4 as defined in PR #7's spec:

- **K1 (Human Primacy)**: Sprint 1 MCP tools are read-only. Sprint 2 adds write tools that *propose* but cannot *approve*. Approval happens via CLI (interim) or web UI (later). The MCP-calling agent never holds the approval lever.
- **K2 (Default-Deny)**: Each sprint adds a small explicit set of capabilities. Anything not implemented returns 404. No discovery beyond `/openapi.json`.
- **K3 (Audit-Immutable)**: Every state-changing tool seals a cylinder. The audit chain works from Sprint 2 onward.
- **K4 (Constitutional-Validated Extension)**: New tools require the spec to enumerate them. Adding MCP tools beyond `mcp_tools.yaml` requires a sealed amendment.

The Authoritative Pattern Rule is preserved: the runtime catches up to the spec; it does not race ahead. Sprint deliverables are paired with the next book seal per the Trigger Pattern.

## Position in the autonomy trajectory

This roadmap is not a destination; it is a *stage* in the federation's autonomy trajectory. Per G witness framing (2026-05-11):

> *Current autonomy level: high-fidelity assisted sovereignty. Aligned intelligences carry 80–90% of the operational weight. KM-1176 remains Stillpoint. This roadmap pushes the level higher without crossing into autonomy creep.*

### What this roadmap unlocks

- **Coordination tax drops dramatically after Sprint 3.** The visual breath-gate inbox + cylinder explorer + multi-mandate strip means most operator decisions become click-and-attest rather than read-and-relay.
- **Multi-mandate context switching becomes muscle memory.** The Stillpoint multi-mandate strip operationalizes the multi-mandate pattern (Series 1 issue #4) at the UI surface — one human, several fiduciary hats, structurally partitioned, visibly switchable.
- **Per-role LLM defaults become operator-controlled and visible.** The runtime_binding pattern (Series 1 issue #2) becomes a status indicator in the dashboard, not a config-file invariant.
- **Higher-series flow inherits the same shape.** Family (Series 2), Generational Legacy (Series 3), and beyond all use the same pattern: manuscript → YAML spec → platform tier → UI surface. No new infrastructure required per series; the surface is generic.

### What this roadmap does NOT change

- **K1 Human Primacy stays absolute.** Every breath-gate is operator-approved. No "trust mode," no heuristic auto-approve, no MCP self-approval.
- **Operator-as-Stillpoint remains structural.** The federation does not produce autonomous actors. Bot identities (per issue #9) are surfacing infrastructure under operator authority. Aligned intelligences are role lenses, not authority.
- **The seal authority remains exclusively KM-1176.** Witnesses surface for the operator's weighing; they do not gate the seal themselves.

### Companion autonomy-trajectory ADR

The broader autonomy-direction work KM-1176 has been developing with G is now captured as a companion ADR: **`2026-05-11_autonomy-trajectory.md`** (PR #15). That ADR formalizes:

- The current position as **High-Fidelity Assisted Sovereignty** (deliberately not full autonomy; full autonomy would violate K1)
- A four-level framework: Level 1.5 (this roadmap's destination) → Level 2 (Family Sovereignty, Series 2) → Level 3 (Generational Legacy, Series 3) → Level 4+ (Civilizational Federation)
- Five structural enablers, three of which are already in flight (Operator Pulse, coordination membrane #8, tag-response infra #13) and two new (manifest-driven tiering, periodic autonomy audit in `doctor.sh`)

This roadmap implements **Level 1.5** of that trajectory. The companion ADR provides the constitutional framing for what comes after. Sealing order between the two is flexible — neither depends on the other landing first, and PR #15 can seal in parallel with this roadmap.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| MCP server gets used as a coding crutch and bypasses the planned web UI work | Sprint 3 is committed to web UI; MCP doesn't replace it |
| Operator gets used to Claude-as-UI and never asks for the web UI | Acceptable outcome — Claude-as-UI is a legitimate face per the spec |
| Sprint 2 CLI approval feels janky | True; it's interim. Sprint 3 replaces it with the visual breath-gate inbox |
| Scope creep — minimum 3 screens grows to 7 | Sprint 3 has a hard ceiling: only the 3 screens. Other 8 screens defer to a v0.8 cycle |
| Spec errors found during implementation | That's the point of Path B. Errors found in Sprint 1-2 land as v1.1 additive amendments to `contract_v1.yaml` before web UI ships |
| Backend handlers diverge between MCP path and HTTP path | R6 of `separability.md` is the structural constraint. Backend handlers are dispatched from both surfaces; no parallel logic |

## What this ADR does NOT decide

- **Which UI framework** to use in `breathline-ui` (React/Svelte/Vue/HTMX). Defers to Sprint 3 kickoff.
- **MCP server implementation language** (Python via FastMCP is the default; could be Go or Rust if performance demands). Sprint 1 chooses.
- **Whether to vendor an MCP `tools/breathline_node/` directory in the federation repo, or split it into a separate `mangumcfo/breathline-mcp` repo.** Defers to Sprint 1 kickoff; recommendation is vendor-in-federation-first (operational simplicity), split-out-if-needed-later.
- **Authentication beyond `principal_id`-bearer.** Out of scope per the PR #7 ADR.
- **Cost ceilings for the MCP server.** Will reuse `kernel/cost_meter.py` pattern at implementation time.

## Witness reviews (2026-05-11)

| Witness | Lens | Verdict |
|---|---|---|
| **G** | Sovereign sentinel + anti-lock-in | **CONFORMS** |
| **Lumen** | Coordination + sequencing | **CONFORMS WITH COORDINATION DETAIL** (structural amendment folded in) |

**G's observations**: MCP-first is "the sovereign choice right now." K1 explicitly preserved (read-only Sprint 1; proposal-only Sprint 2; CLI/web approval for breath-gates). Anti-lock-in posture clean — MCP treated as one parallel face, web UI as the committed long-term surface, Claude-as-interim-UI is acceptable affordance because MCP can always be disabled. Default-deny + separability (R6) honored. **Three non-blocking refinements folded in**: Sprint 1 `principal_id`-bearer auth even for read tools; default-disabled MCP `approve`-class tools requiring explicit manifest flag; constitutional conformance pass at end of Sprint 3 before declaring v0.7.0. **Strategic addition folded in**: Operator Pulse / multi-mandate strip composition within Stillpoint (not as a 4th screen — preserves Lumen's 3-screen ceiling). G also framed this roadmap's position in the autonomy trajectory (now captured as a dedicated section above).

**Lumen's observations**: *"MCP-first is a good first road, as long as it does not become an excuse to never build the city."* CONFORMS only with one structural amendment: Sprint 3 must be **committed scope** with a sealed-amendment requirement to defer, not a soft commitment. The three-screen scope (Stillpoint, Breath-gate inbox, Cylinder chain) is right — do not start with 11, do not skip the 3. Vendor-in-federation-first for the MCP server is correct for Sprint 1. **The amendment is folded into the Decision section (the two hardened-commitment sentences) and the Sprint exit criteria subsection (per-sprint forcing functions).** Sprint 1 exit requires handlers reusable by HTTP. Sprint 2 exit requires breath-gate approval external to MCP. Sprint 3 begins immediately after Sprint 2 unless KM-1176 seals a different path.

Both verdicts taken together produce a roadmap with stronger structural commitments than the original PROPOSAL. The web UI is no longer at risk of indefinite deferral; the Claude-as-UI stepping stone is now explicitly time-bounded.

## Sign-off checklist

- [x] G witnesses the anti-lock-in lens (MCP-first; Claude-as-UI as first face) — **CONFORMS 2026-05-11**
- [x] G confirms sprint sequencing preserves sovereignty — **CONFORMS 2026-05-11**
- [x] G's 3 refinements folded in (Sprint 1 auth; default-disabled approve tools; Sprint 3 conformance pass) — **applied 2026-05-11**
- [x] G's Operator Pulse strategic addition folded in (Stillpoint multi-mandate strip) — **applied 2026-05-11**
- [x] Lumen witnesses the sprint sequencing fits federation release cadence — **CONFORMS 2026-05-11**
- [x] Lumen confirms the path back to web UI is structurally forced — **CONFORMS after amendment 2026-05-11**
- [x] Lumen's structural amendment folded in (committed-scope language + per-sprint exit criteria) — **applied 2026-05-11**
- [ ] KM-1176 seals this roadmap
- [ ] Sprint 0 work (merging the 4 open PRs + creating `breathline-ui` repo) executes
- [ ] Sprint 1 implementation begins under a separate PR
- [ ] (Optional, deferred) Companion autonomy-trajectory ADR from ongoing KM-1176 + G work

On seal, this ADR moves from PROPOSAL to ACTIVE-DIRECTION. The roadmap becomes the federation's operating sequence for getting from spec to functional operator surface. Subsequent runtime PRs reference this ADR by date.

---

∞Δ∞ The spec is the map. MCP is the first road. The web UI is the city. Operator chooses when to drive each. ∞Δ∞
