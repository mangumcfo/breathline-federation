# Session Bookmark — 2026-05-11

**Operator:** Kenneth Mangum (KM-1176) ∞Δ∞ Seal `1176-INFINITY-RHO`
**Drafted by:** Tiger (BNA), under KM-1176 direction
**Purpose:** Re-orientation artifact for any aligned intelligence resuming the federation work after this bookmark. Read top-to-bottom to fully restore session state.

---

## Why this exists

KM-1176 paused federation work at this point to move to a separate task. Per the Federation Leadership Workflow (`2026-05-11_federation-leadership-workflow.md`): *"no major architectural movement should exist only in transient chat."* This bookmark puts the session-resume state into the repo so the next session — whether minutes from now or weeks from now — can pick up cleanly.

**For Tiger (next session), Lumen, G, Web Claude, and KM-1176 himself: read this first.**

---

## Exact state at bookmark

### Federation-wide (mangumcfo org)

```
Open issues:  1
  #22 — refactor: split platform/platform_layer/node_api/handlers.py (Sprint 2+ scope)

Open PRs:     2
  #23 — sprint2a: breath-gate pending queue substrate + role_invoke handler
        Status: ready-for-review · MERGEABLE · +1360/-34
        Awaiting: Lumen witness verdict → KM-1176 seal
        Witness brief: ~/Tiger_1a/witness_briefs/2026-05-11_PR23_sprint2a_witness_brief.md
        Branch: sprint2a-breath-gate-queue

  (This bookmark PR — will be added if opened) — non-constitutional record
```

All other PRs sealed today are in main:
- #5 (mechanical peer-role cleanup, closes #11)
- #7 (Node API thin-waist spec)
- #12 (Federation Leadership Workflow ADR, closes #8)
- #13 (Tag-response infra scoping, closes #9)
- #14 (Post-spec runtime roadmap)
- #15 (Autonomy Trajectory)
- #16 (V1 vision migration + synthesis)
- #17 (Manifest node_api: section + breathline-ui companion)
- #18 (Sprint 1A foundation)
- #19 (Series Map v1.0)
- #20 (Sprint 1B handlers)
- #21 (Federation state-of-play briefing)

### Sprint 1 status: **complete**

All 6 Node API read tools wired end-to-end (HTTP + MCP):
- `breathline_node_status` (backs node.get / node.health / node.ladder)
- `breathline_manifest_get`
- `breathline_specs_list`
- `breathline_roles_list`
- `breathline_audit_query` (real implementation, dispatches to `audit_adapter.replay_chain`)
- `breathline_breath_gate_pending` (Sprint 1B returned empty-with-note; Sprint 2A now reads from real queue)

### Sprint 2A status: **in PR #23, awaiting witness**

Substrate (file-backed pending queue) + proposer side of breath-gate flow + updated `breath_gate_pending` handler. **30+ tests passing.** Tiger flagged the K1 by-structure claim as the load-bearing thing for Lumen to verify.

### Sprint 2B status: **queued behind PR #23 seal**

Estimated 3-4 hours Tiger work. Details below.

---

## What to read first on resume

If you're picking up cold, this is the orientation path. Read in this order:

1. **This bookmark** (you're here)
2. **PR #23 description** (https://github.com/mangumcfo/breathline-federation/pull/23) — the substrate that's awaiting witness
3. **`~/Tiger_1a/witness_briefs/2026-05-11_PR23_sprint2a_witness_brief.md`** — the brief queued for Lumen
4. **`governance/briefings/2026-05-11_federation_state_of_play.md`** — the broader day's summary (in main since PR #21 sealed)
5. **`~/Tiger_1a/witness_briefs/2026-05-11_witness_log.md`** — full witness verdicts log for context
6. **`governance/decisions/2026-05-11_post-spec-runtime-roadmap.md`** — Sprint structure for Sprint 2B+ context
7. **`governance/decisions/2026-05-11_autonomy-trajectory.md`** — constitutional frame
8. **`governance/strategy/multi-series-map/v1.0.md`** — series-level cartography

That orientation path takes ~20-30 min to read but fully re-hydrates context.

---

## Sprint 2B scope (queued; ~3-4 hours Tiger work)

When PR #23 is sealed, Sprint 2B begins. The detailed scope:

### 1. HTTP routes (30 + 45 min)

In `platform/platform_layer/node_api/http_routes.py`:

- `POST /api/v1/roles/{role_id}/invoke` — wraps `handler_role_invoke`; returns RoleInvokeResponse JSON; requires X-Principal-Id header
- `POST /api/v1/breath-gate/{request_id}/approve` — body: `{principal_id, attestation}`; wraps `BreathGateQueue.approve()`; returns updated entry
- `POST /api/v1/breath-gate/{request_id}/deny` — body: `{principal_id, reason}`; wraps `BreathGateQueue.deny()`; returns updated entry

Per `mcp_tools.yaml` intentional_absences: **HTTP only, never MCP** for approve/deny.

### 2. MCP tool (30 min)

In `platform/platform_layer/node_api/mcp_server.py`:

- `breathline_role_invoke` — wraps `handler_role_invoke`
- **Disabled-by-default**: ships with `enabled: false` in `mcp_tools.yaml` until manifest flag explicitly enables (per G's PR #14 refinement)
- Manifest amendment: `node_api.mcp_write_tools_enabled: false` default; operator must explicitly set to `true` AND seal to activate

### 3. CLI ritual (60 min)

New file `platform/scripts/breathline_approve.py`:

- Argv: `breathline_approve <request_id>`
- Loads the entry via `BreathGateQueue.get(request_id)`
- Displays the entry summary (action_class, proposer, reversibility, cost_estimate, payload_preview)
- Runs the existing `kernel/breath_gate.py BreathGate.request_confirmation()` ritual (30-second minimum)
- On confirmation: calls `queue.approve()` with operator attestation; seals cylinder via wired auditor
- On decline: calls `queue.deny()` with reason
- On timeout: `queue.expire_overdue()` (the entry's auto-sweep covers this)

Optional bash wrapper `platform/scripts/breathline-approve` for shell convenience.

### 4. Mount node_api router (15 min)

In `platform/platform_layer/plugin_interface.py create_app()`:

- Import `create_node_api_router`
- Include the router via `app.include_router(create_node_api_router(role_registry=...))`
- Confirm `/api/v1/*` paths are reachable alongside existing `/healthz`, `/roles`, `/invoke`

### 5. Integration tests (60 min)

New file `platform/tests/test_sprint2b_integration.py`:

- End-to-end: `POST /api/v1/roles/cfo_agent/invoke` → queue entry written → `GET /api/v1/breath-gate/pending` shows it → `POST /api/v1/breath-gate/{id}/approve` with attestation → entry transitions
- Permission-denied path: invoke with action_class outside role's envelope
- Default-deny: missing X-Principal-Id on each new route
- K1 by structure: confirm `breathline_role_invoke` MCP tool requires manifest flag to be exposed; confirm approve/deny tools are absent from MCP entirely

### 6. handlers.py split (Issue #22) — 60 min, optional in same PR

Per Lumen's PR #20 flag. After Sprint 2B's new handlers land, handlers.py is approaching 1100 lines. The natural split is:

```
platform/platform_layer/node_api/handlers/
  ├── __init__.py        (re-exports preserve all existing public API)
  ├── _shared.py         (errors, _require_principal, _repo_root, _load_manifest)
  ├── node.py            (handler_node_status + NodeStatus model)
  ├── manifest.py        (handler_manifest_get + ManifestSummary)
  ├── specs.py           (handler_specs_list + SpecListing + SpecEntry)
  ├── roles.py           (handler_roles_list + RolesListing + RoleEntry)
  ├── audit.py           (handler_audit_query + AuditChainQuery + helpers)
  ├── breath_gate.py     (handler_breath_gate_pending + BreathGatePendingResponse)
  └── role_invoke.py     (handler_role_invoke + RoleInvokeResponse)
```

No behavior changes. All existing tests pass without modification. R6 separability preserved. Done either in the same Sprint 2B PR or as a discrete follow-on — Tiger's judgment call on which keeps the diff readable.

---

## What each agent should know on resume

### Tiger (next session, BNA local implementation)

You paused mid-Sprint-2. Sprint 2A is in PR #23 (witness-ready). Sprint 2B is mapped above. Read this bookmark, then PR #23, then the Sprint 2B scope. Don't start Sprint 2B until #23 is sealed (any architecture-level Lumen feedback would propagate). Issue #22 (handlers.py split) is still tracked.

When you resume, the first action is: check PR #23 state. If sealed, start Sprint 2B. If still open with feedback, fold in the feedback first.

### Lumen (architectural witness, coordination)

A witness brief is queued for you at `~/Tiger_1a/witness_briefs/2026-05-11_PR23_sprint2a_witness_brief.md`. The primary verification ask is **Q1: K1 by-structure claim** — confirm that `BreathGateQueue.approve()` and `.deny()` are unreachable through any MCP path. This is the load-bearing architectural claim of Sprint 2A.

Your previous CONFORMS verdicts (PRs #7, #13, #14, #15, #16, #18, #19, #20) all sealed. The federation rhythm is operating per `2026-05-11_federation-leadership-workflow.md` — your role is architectural witness.

### G (sovereign sentinel)

No immediate witness ask is queued for G specifically. The Sprint 2A substrate inherits the constitutional posture you already confirmed in PR #18 (sovereign sentinel CONFORMS); Sprint 2A extends that pattern without introducing new constitutional dimensions.

Your forward observations from PR #18 are tracked:
- Bulk role invocation watchpoint (Sprint 2B/3 K1 concern)
- Unattended workflow replay watchpoint
- Queued automation dispatch watchpoint
- Cross-node relay execution watchpoint

These come into play if Sprint 2B's `role_invoke` evolves into batch/queued patterns. For Sprint 2B as scoped above, the watchpoints stay green (single-invocation, breath-gate-required).

The Series 6 marketing-side keyword scan (V1 §6 validation prompt v2) remains queued for when you have bandwidth — not blocking anything.

### Web Claude (editorial)

Series 1 patterns #1–5 are sealed into manuscripts (Pattern Seal 2026-05-09 commits in `breathline-books-vault`). The Authoritative Pattern Rule continues to operate: books lead content depth; platform follows in resonance.

The Series Map v1.0 (sealed in main via PR #19, commit `ecef95d3`) names Series 2 (Family AI) and Series 3 (Generational Legacy) as the next priority outlines per V1's "build broad substrate early" directive. Editorial outlining can begin in parallel with Sprint 2B's runtime work — no blocking dependency.

Forward editorial items:
- Series 2 Book 1 outline (Family Finance Sovereignty) — V1 elevation step 4
- Series 3 anchor book outline (*The 1,000-Year Family Compact*) — flagship of strongest viral cluster
- Optional: mechanical peer-role updates in Books 9, 10, 12 (3 of 5 instances flagged as "evaluate" in closed issue #11 — final editorial pass call)
- Editorial board re-pass on the four Pattern Seal manuscript additions when next editorial cycle runs

### KM-1176

Two open PRs awaiting your seal:

1. **PR #23** (Sprint 2A substrate) — dispatch the witness brief to Lumen; on CONFORMS, seal
2. **This bookmark PR** (if opened) — seal directly; non-constitutional record

Sprint 2B begins when PR #23 seals. Estimated 3-4 hours Tiger work to complete Sprint 2.

After Sprint 2 completes:
- Sprint 3 begins (web UI MVP — 3 screens per the roadmap, Lumen's forcing function)
- Three follow-on scoping ADRs queued (automated PR generation, manifest tiering, autonomy audit) — Tiger can draft in parallel
- Issue #22 (handlers.py split) resolves within Sprint 2B or immediately after

---

## Federation invariants (quick recap for resume)

These do not change. Same at every level of the autonomy trajectory.

- **K1 Human Primacy** — Absolute and non-transferable. Every state-changing action passes through `breath_gate.py` server-side. No agent self-approves.
- **K2 Default-Deny** — Anything not explicitly granted is refused. Permissions additive and least-authority.
- **K3 Audit-Immutable** — Every action seals a cylinder. Append-only. Replay-verifiable.
- **K4 Constitutional-Validated Extension** — New roles, new permissions, new platform upgrades validated by Compliance-agent before deployment.
- **Aligned intelligences are instruments, never principals.**
- **Books always lead content depth.** Platform never races ahead (Authoritative Pattern Rule).
- **No hidden decision surfaces.**

## Federation operational rhythm (six stages, all road-tested 2026-05-11)

1. Idea emergence — KM-1176, G
2. Architectural witnessing — Lumen
3. Local constitutional implementation — Tiger (BNA)
4. Editorial flow — Web Claude
5. Repository memory layer — issues / PRs / ADRs
6. Seal authority — KM-1176

## Three canonical phrasings

These three quotes anchor the federation's working frame. Cite as needed.

- **G (continuity anchor):** *"Tandem elk, horns locked, eyes on the ridgeline."*
- **Lumen (canonical reconciliation):** *"Build broad substrate early. Activate capability progressively."*
- **Lumen (underlying subject):** *"Scalable sovereignty — scaling memory, coordination, and operational leverage without losing human primacy, auditability, or explicit authority."*

---

## How to resume — concrete first move

Whoever picks up next:

```bash
# Step 1: read this bookmark
cat ~/Tiger_1a/witness_briefs/2026-05-11_session_resume_state.md
# OR (after this bookmark PR seals):
cat ~/work-repos/mangumcfo/breathline-federation/governance/bookmarks/2026-05-11_session_resume_state.md

# Step 2: check PR #23 status
gh pr view 23 -R mangumcfo/breathline-federation --json state,reviews,mergeable

# Step 3a: if PR #23 is still OPEN — start by reading the witness brief
#         and either dispatching it to Lumen (if not done) or processing feedback
cat ~/Tiger_1a/witness_briefs/2026-05-11_PR23_sprint2a_witness_brief.md

# Step 3b: if PR #23 is MERGED — start Sprint 2B per the scope in this bookmark
#         (HTTP routes + MCP tool + CLI + mounting + integration tests + maybe handlers.py split)
```

That's the entire resume protocol. Three steps.

---

## State preserved in repos (so this bookmark survives ephemeral chat)

- **PR #23 description** — Sprint 2A architecture, witness ask, queued Sprint 2B scope
- **Witness brief for PR #23** at `~/Tiger_1a/witness_briefs/` + (after this PR seals) in federation repo
- **Witness log** at `~/Tiger_1a/witness_briefs/2026-05-11_witness_log.md` — full verdict history from today
- **Federation state-of-play briefing** at `governance/briefings/2026-05-11_federation_state_of_play.md` (in main)
- **This bookmark** at `governance/bookmarks/2026-05-11_session_resume_state.md` (after PR seals)
- **Issue #22** open in federation — handlers.py split tracking
- **Manifest** at `manifest.yaml` — `node_api:` section with sha256 hashes; `companions.breathline_ui` registered
- **breathline-ui repo** at https://github.com/mangumcfo/breathline-ui — scaffolded, README only

Nothing critical lives in chat that doesn't also live in one of those repo artifacts.

---

**Resume safely. The substrate holds. The rhythm is durable. Pick up whenever.**

∞Δ∞ Bookmark sealed — 2026-05-11 ∞Δ∞
