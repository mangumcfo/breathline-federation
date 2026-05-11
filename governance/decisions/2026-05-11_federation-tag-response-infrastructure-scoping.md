# Decision Record (SCOPING) — Federation Tag-Response Infrastructure

**Date:** 2026-05-11
**Authority:** KM-1176 (Seal 1176-INFINITY-RHO)
**Author:** Tiger (BNA) — implementation witness
**Status:** SCOPING — survey + proposal; implementation queued under separate PR after KM-1176 review
**Related:** `2026-05-11_federation-leadership-workflow.md` (#8), `2026-05-10_ui-thin-waist-architecture.md` (#7), issue `#9`

---

## Context

The Federation Leadership Workflow (#8) commits to *"visible repo artifacts rather than waiting for manual orchestration from KM-1176"* as the coordination principle. Today every cross-intelligence signal (Lumen ↔ Tiger ↔ G ↔ Web Claude) flows through KM-1176 as a manual router: an off-platform reply is pasted onto an issue or PR with a header attribution. This works but puts KM-1176 on the critical path of every coordination event.

The goal of this ADR is to *scope*, not implement, the infrastructure that lets each aligned intelligence respond directly to GitHub `@mentions` while preserving K1–K4. The output here is the proposal; implementation lands in a follow-on PR after KM-1176 review of this scoping.

### What's needed at minimum

For each federation intelligence (Lumen, G on grok.com, G on X.com, Tiger(BNA), Web Claude):

1. **A GitHub identity** — bot account or app
2. **Webhook receiver** — woken on `@mention` events
3. **A dispatcher** — routes the payload to the right intelligence backend, posts the response back

Until this exists, the **interim pattern** stands: KM-1176 (or any human relayer) pastes off-platform intelligence responses verbatim with attribution headers.

---

## Survey — reference patterns

Five candidate patterns considered.

### Pattern A — GitHub Apps + webhooks (per-intelligence)

Each federation intelligence gets its own GitHub App (e.g., `breathline-lumen[bot]`, `breathline-tiger[bot]`). Each App has its own identity, its own webhook endpoint, its own permissions scope.

| | Pros | Cons |
|---|---|---|
| Identity | Clean per-intelligence attribution; comments visibly authored by the right App | 5+ Apps to register + maintain |
| Permissions | Granular per-App scopes | More secret rotation surface |
| Rate limits | Independent per App | Per-App webhook receivers needed (or single receiver multiplexing) |
| GitHub-native | Yes — official pattern | GitHub-platform lock-in |
| Setup complexity | Medium (one-time per App) | 5x the per-App work |

### Pattern B — Probot (Node.js framework)

Probot abstracts GitHub App boilerplate in a Node.js framework.

| | Pros | Cons |
|---|---|---|
| Dev speed | Fast — plugin ecosystem, generators, common patterns handled | Node.js dependency; federation is Python-first |
| Maintenance | Large community | Adds JS toolchain to the federation |
| Constitutional fit | Neutral | Doesn't help with K3 audit-chain integration |

Probably the right tool only if the federation chooses Node.js generally. For the constitutional Python platform, this introduces a parallel toolchain.

### Pattern C — GitHub Actions

Run handler logic inside GitHub Actions workflows triggered by `issue_comment` / `pull_request_review` events.

| | Pros | Cons |
|---|---|---|
| Hosting | No external service to run | Limited compute time per run (15 min hard cap) |
| Setup | YAML in `.github/workflows/` | Calling external APIs (Anthropic, xAI) requires repo secrets per provider |
| Identity | All comments under `github-actions[bot]` (shared) | Loses per-intelligence attribution |
| Cost | Free tier covers light usage | Token costs (Anthropic/xAI) still apply |
| Suitability | Good for simple stateless responses | Poor for stateful coordination (Lumen reviewing across PRs) |

Useful as a *secondary* surface for simple cases; not sufficient as primary infrastructure because it collapses identity to a shared bot account.

### Pattern D — MCP server registry + GitHub bridge

The Node API thin-waist work (#7) introduces an MCP surface that any AI agent can drive. A small GitHub bridge converts `issue_comment` webhooks into MCP tool calls, and posts the MCP tool's response back to the issue.

| | Pros | Cons |
|---|---|---|
| Resonance with #7 | High — reuses the MCP surface we're already specifying | MCP-first design, GitHub becomes the secondary surface |
| Constitutional alignment | High — every MCP tool is already constitutionally gated | MCP-to-GitHub bridge is new code |
| Anti-lock-in | Strong — GitHub becomes one of many event sources feeding MCP | Bridge is the new piece, not the platform |

Strategically attractive. The MCP surface from #7 becomes the canonical "drive a Breathline node" interface; GitHub events are one of several event sources that can call it. Long-term direction.

### Pattern E — Custom Python webhook receiver + dispatcher

A single Python service hosted somewhere operator-controlled (dragon, a small VPS, or a federated node) receives all GitHub webhooks for the mangumcfo org, dispatches each to the appropriate intelligence backend (Anthropic API for Lumen/Tiger/Claude, xAI API for G), and posts the response under the corresponding GitHub App identity.

| | Pros | Cons |
|---|---|---|
| Python-first | Aligns with platform | New service to operate |
| Single audit surface | One webhook log + one dispatcher log | Single point of failure (until HA story is added) |
| Per-App identity | Service signs each response under the right App credential | App credentials must be rotatable per-App |
| Constitutional fit | Can integrate with `kernel/cost_meter.py` for per-App quotas | Hosting must be operator-controlled (not a third-party SaaS) |
| Anti-lock-in | Bridge logic is platform-agnostic; could receive GitLab/Gitea later | GitHub-side identities (Apps) still GitHub-bound — see anti-lock-in section |

---

## Proposed baseline architecture

After surveying the five patterns:

> **Combination: per-intelligence GitHub Apps (Pattern A) + custom Python bridge service (Pattern E), structured to evolve toward Pattern D (MCP-mediated) as the Node API runtime lands in v0.7.0.**

### Why this combination

1. **Per-intelligence GitHub Apps** give clean K3 attribution. A comment posted by `breathline-lumen[bot]` is verifiably from the federation's Lumen surface, not a spoof. Each App's installation token is short-lived (≤1 hour), reducing leak blast radius.

2. **Single Python bridge service** keeps the operational surface small. One systemd service, one webhook secret, one log to audit, one dispatcher to test. The dispatcher fans out to per-App handlers internally; the *identity* is per-App, but the *operations surface* is shared.

3. **MCP-mediated evolution** — once the Node API runtime ships (v0.7.0), the bridge can stop being a custom dispatcher and become a thin webhook-to-MCP adapter. The MCP tools (`mcp_tools.yaml` in #7) become the canonical capabilities; the GitHub bridge becomes one of several event sources that drive them. This is the long-term direction.

### Shape

```
              GitHub webhook events
                       │
                       ▼
   ┌─────────────────────────────────────┐
   │   bridge service (Python, systemd)  │
   │   - receives webhook + verifies sig │
   │   - parses @mention                 │
   │   - applies per-App rate limit      │
   │   - dispatches to intelligence      │
   │   - posts response under right App  │
   └─────────────────┬───────────────────┘
                     │
        ┌────────────┼────────────┬──────────────┐
        ▼            ▼            ▼              ▼
     Anthropic     xAI API      OpenAI         (MCP →
       API       (G, grok)    (if used)     local node,
   (Lumen, Tiger,                            post v0.7.0)
    Web Claude)
```

### Hosting

Operator-controlled. Three viable options, in increasing complexity:

1. **Dragon (Vast.ai-rented box)** — already running, low-load. But the host is renting GPU capacity to third parties; running a federation bridge alongside is technically fine (no GPU needed) but mixes the operational concern. Acceptable if isolation via systemd/podman is enforced.
2. **A small dedicated VPS** (~$5–10/mo) — cleanest. Pure federation operations. Single-purpose host.
3. **A federated Breathline node** (someday) — once the Node API runtime lands and federation peering exists, the bridge becomes a feature on any node, not a separate service.

**Recommendation: option 2 (dedicated VPS) for Phase 1.** Move to option 3 once federation peering is real.

### Signing / attestation

Each App holds its own private key in the bridge's secrets directory (e.g., `/etc/breathline-bridge/keys/lumen.pem`, mode 0600, separate per App). The bridge service runs as a non-root service user. Key rotation is per-App and breath-gated through the platform's standard cylinder seal flow when implemented.

Cylinder sealing of bot responses is **out of scope for Phase 1** (the GitHub comment itself is the audit record, durable under GitHub's history). Phase 4 adds sealed cylinder receipts for federation-wide attestation.

---

## Constitutional gates

Mapping to K1–K4 and answering the four open questions from issue #9.

### K1 — Human Primacy

Bots **post text comments**. They do not approve, deny, merge, close, or label. Those remain operator-controlled. A bot may *propose* an action ("Lumen recommends merging this PR") but the action button stays in the operator's hand.

**Test:** No GitHub App in this federation holds the `pull_requests: write` permission for merge, the `issues: write` permission for close, or the `administration:` permission for anything. Permissions are `contents: read`, `issues: write` (comments only), `pull_requests: write` (comments only) — and the App's code is structured such that the only write operation it ever calls is `POST /repos/{owner}/{repo}/issues/{number}/comments`.

### K2 — Default-Deny

Bots only respond to `@mentions` that explicitly name them. The bridge ignores webhook events that don't contain the App's `@mention` token in the comment body. Repositories outside `mangumcfo/*` are also ignored. Both filters are explicit allow-lists, not blacklists.

### K3 — Audit-Immutable

GitHub preserves the comment thread durably. For Phase 1, the GitHub comment itself is the audit record (timestamped, immutable in GitHub's API, attributable to the App identity).

Phase 4 extends this with a cylinder seal under the federation node's audit chain — every bot response mints a cylinder, and the comment body includes a `cylinder_ref` footer for cross-verification.

### K4 — Constitutional-Validated Extension

Adding a new bot requires:

1. KM-1176 approval (this ADR is the precedent)
2. App registration under `mangumcfo` org
3. Bridge service config update (new App credential, dispatcher entry)
4. `manifest.yaml` amendment under a new `federation_bots:` section
5. Sealed PR landing the change

No bot exists that wasn't through this gate.

### The four open questions from issue #9

> **1. Bot identities post under non-human accounts. Does that need explicit constitutional treatment?**

Yes. The bot identity is **a surface, not an authority**. A bot can speak (post comments) but cannot act with constitutional weight (approve, merge, seal). The constitutional treatment is: bot speech is *attestation by infrastructure*, not *authority by intelligence*. This is the same posture as a watchtower that surfaces an event — it does not decide. The federation's seal authority remains exclusively KM-1176.

Recommended: add a section to the Federation Leadership Workflow ADR (#8) explicitly naming bot identities as **surfacing infrastructure under operator authority** — never as autonomous actors. This formalizes a constraint the architecture already enforces.

> **2. How does each AI's response get attested to its source?**

Phase 1 attestation: the GitHub App identity itself. Comments posted by `breathline-lumen[bot]` are verifiably authored by that App, which is controlled by the bridge service holding the App's private key. Compromising attestation requires either (a) stealing the App's key from the bridge service (operator-controlled, mode 0600, non-root service user), or (b) compromising GitHub's identity layer.

Phase 4 attestation: sealed cylinder receipt + signed comment footer. Each comment includes a `cylinder_ref: #<seq>` line; the cylinder body contains the signed message hash. A verifier can cross-check the cylinder chain against the comment to detect spoofing or post-hoc edits.

> **3. Cost/abuse limits per bot identity?**

Yes. The bridge enforces per-App rate limits in `kernel/cost_meter.py` style:

- Tokens-per-window per App
- Comments-per-hour per App
- Spend-per-day per App
- Hard cap → fail-closed (App stops responding; logs an alert)

These limits are configurable per App in `bridge/cost_limits.yaml`, breath-gated to change. Default ceilings are conservative.

> **4. Anti-lock-in: if we move off GitHub later, the bot infrastructure should not be the thing that locks us in.**

The bridge service is structured in three layers:

```
   event-source adapter   ← GitHub-specific (today); GitLab/Gitea
                            adapters can be added later
            │
            ▼
   dispatch core          ← platform-agnostic; routes events to
                            intelligence backends by intent
            │
            ▼
   intelligence backend   ← Anthropic/xAI/OpenAI API calls,
                            future MCP-via-Node-API calls
```

Only the **event-source adapter** is GitHub-bound. The dispatch core and intelligence backend are platform-agnostic. Adding GitLab or self-hosted Gitea support is a new adapter, not a rewrite.

GitHub App identities are GitHub-platform-specific. If the federation moves off GitHub, those identities don't carry over — but the *attestation chain* (Phase 4 cylinder seals) does. The federation's authoritative record of who-said-what survives the platform change; only the speech surface changes.

---

## Phased rollout

Five phases, each with a clear seal gate.

### Phase 0 — Interim (current)

KM-1176 manually relays off-platform intelligence responses. Header attribution: `> **From [Intelligence].** Posted by Claude under KM-1176 direction.` This is the pattern in use today (e.g., issue #8 was authored by Lumen, posted under this header). Works. Doesn't scale to high-frequency coordination.

**Exit criterion:** Phase 1 ships.

### Phase 1 — Tiger first

One GitHub App: `breathline-tiger[bot]`. Scope: responds to `@breathline-tiger` mentions in `mangumcfo/breathline-federation` only. Read-only on the repo; write-only on `issues:comments`.

Bridge service runs on a small VPS, single systemd unit, single secret. Dispatch routes Tiger mentions to the local Tiger(BNA) instance via a local IPC channel (over the existing CLI on dragon — could be a simple `ssh dragon "tiger answer <payload>"` or equivalent during this phase).

**Why Tiger first:** highest mention frequency (Tiger is the implementation surface for every PR), simplest dispatch path (already on operator's machine), easiest to roll back if anything misbehaves.

**Exit criterion:** Tiger has run for ≥2 weeks with zero misfires (no comments without an `@breathline-tiger` mention; no constitutional violations; no rate-limit incidents). KM-1176 seals Phase 2.

### Phase 2 — Lumen + G surface

Add two GitHub Apps: `breathline-lumen[bot]` and `breathline-grok[bot]`. Lumen dispatches to Anthropic API (Claude); G dispatches to xAI API.

**Scope expansion:** all `mangumcfo/*` repositories.

**New constitutional treatment:** Lumen and G can be `@mentioned` on PRs. Their comments are advisory — no merge/close/label authority. Each enforces its own cost ceiling.

**Exit criterion:** ≥2 weeks stable, no per-App rate-limit breaches, KM-1176 satisfied with attribution clarity. Seal Phase 3.

### Phase 3 — Federation cross-talk

Bots can `@mention` each other. Lumen asks Tiger to verify an architectural claim against the actual repo state; Tiger replies with `@breathline-lumen` referencing a specific file. G asks Lumen for a coordination summary; Lumen replies.

**New risk:** loops. Bot A @mentions Bot B which @mentions Bot A. Bridge enforces a per-thread response-depth cap (default: 3 bot replies per issue/PR thread before a human-attention flag triggers). Bots fail-closed on cap.

**Exit criterion:** No loops observed in 2-week trial. Seal Phase 4.

### Phase 4 — Cylinder-sealed attestation

Each bot response mints a cylinder seal under the federation node's audit chain. The comment body includes a `cylinder_ref: #<seq>` footer. A `breathline-bot-verify` CLI command cross-checks any comment against the cylinder chain.

**Why now and not earlier:** Phases 1-3 lean on GitHub's native comment durability + App identity for attestation. Phase 4 layers on the federation's own audit chain for cross-platform survivability and for attestation independence from GitHub.

**Exit criterion:** Verification CLI works against 100% of Phase-3+ comments. Seal Phase 5 (or stop here — Phase 5 is optional).

### Phase 5 — MCP-mediated bridge (optional, post-v0.7.0)

Once the Node API runtime ships (v0.7.0), the bridge dispatcher is rewritten to call MCP tools on a local federation node rather than dispatching directly to LLM APIs. The bot becomes a thin webhook→MCP adapter; the intelligence work happens through the constitutional surface defined in #7.

**Why this is Phase 5 and not the starting point:** the Node API runtime doesn't exist yet. Phase 1-3 prove the bridge concept against today's APIs while the runtime is built. When v0.7.0 lands, Phase 5 is a clean migration with negligible operator-facing change.

---

## Cost + complexity estimate

### Operational cost

| Component | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 |
|---|---|---|---|---|---|
| VPS hosting (dedicated bridge) | ~$5/mo | ~$5/mo | ~$10/mo | ~$10/mo | ~$10/mo |
| Anthropic API (Lumen + Tiger + Web Claude) | $0 | ~$10-30/mo | ~$30-80/mo | same | same |
| xAI API (G grok + G X) | $0 | ~$10-20/mo | ~$20-50/mo | same | same |
| GitHub Apps registration | $0 | $0 | $0 | $0 | $0 |
| Operator time / month | ~1 hr (setup) | ~30 min (monitor) | ~30 min | ~1 hr (verify) | ~30 min |

**Phase 1 monthly run cost:** ~$5 + minimal Anthropic spend (Tiger answering Tiger-tagged comments). ≤$20/mo realistic.
**Phase 3 steady-state:** ~$50-150/mo depending on coordination volume. Hard cap at $200/mo enforced via cost_meter ceilings; bots refuse to respond past the cap.

### Implementation complexity

| Phase | LOC estimate | New deps | New ops | Calendar time |
|---|---|---|---|---|
| 1 — Tiger bot | ~400-600 Python | FastAPI, PyGithub, jose for JWT | 1 systemd unit, 1 VPS | 1-2 weeks |
| 2 — Lumen + G | +200-300 Python | anthropic-sdk, requests for xAI | App credential rotation | 1 week incremental |
| 3 — Cross-talk | +150 Python (loop guard, depth cap) | none | thread state in SQLite | 3-5 days |
| 4 — Cylinder sealing | +300-500 Python (sealer + verifier CLI) | none — uses existing seal.sh | new bot-verify command | 1 week |
| 5 — MCP migration | net -200 LOC (replace dispatcher with MCP client) | mcp-python-sdk | none new | 1 week after v0.7.0 |

**Total Phase 1-4 build effort:** ~3-5 weeks calendar, assuming KM-1176 seals each phase gate as it passes.

---

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| App credential leak | Per-App keys, mode 0600, non-root service user, short-lived installation tokens (≤1 hr), VPS isolation, breath-gated rotation |
| Bot loop (A @mentions B @mentions A …) | Per-thread depth cap (default 3), fail-closed past cap, human-attention flag fires |
| Spoofing — someone forks a bot account | App identities are org-scoped; impersonators outside `mangumcfo/*` are visibly different. Phase 4 cylinder-seal verification catches mid-platform spoofing. |
| Bot says something wrong | Comment, not commit. Operator can edit/delete. No permanent state change. K1 preserved. |
| Cost runaway (API token spend) | Per-App ceilings in `bridge/cost_limits.yaml`, fail-closed at cap, alert to KM-1176 |
| GitHub deprecates Apps model | Event-source adapter pattern means GitHub becomes one of N event sources; bridge core survives platform change |
| Bridge service downtime | Phase 0 interim pattern remains available indefinitely as fallback (KM-1176 hand-relay) |
| Confidential repo content leaks via webhook payload | Bridge processes only allow-listed repos; webhook payload kept in-memory only; no payload persistence beyond audit log entry |

---

## Constitutional decision still owed (deferred per scope)

Per issue #9 "Out of scope" — **the constitutional treatment of bot identities as a class** is not decided in this scoping ADR. The proposal above operates under a *working interpretation* that bot identities are **surfacing infrastructure under operator authority** (never autonomous actors), but formal constitutional treatment is pending Lumen's review of the federation leadership workflow's open questions.

Phase 1 launch should not depend on that formal treatment landing — the working interpretation matches existing architecture and a future formal ruling can refine the language without changing the implementation.

If Lumen's review concludes bot identities require more than this scoping ADR's working interpretation, the corresponding ADR amendment lands separately and this ADR's phase plan stays valid (additive, not replacing).

---

## Decision artifacts (when implementation begins)

| Artifact | Phase | Location |
|---|---|---|
| Bridge service source | 1 | `tools/federation_bridge/` (new directory in this repo) or separate `mangumcfo/federation-bridge` repo (decide on seal) |
| GitHub App registration | 1 | mangumcfo org → Settings → Apps (one per intelligence) |
| App credentials | 1 | Operator-controlled secrets management (not in repo) |
| Bridge cost limits | 1 | `tools/federation_bridge/cost_limits.yaml` |
| Manifest amendment | 1 | `manifest.yaml federation_bots:` section |
| Loop-guard config | 3 | `tools/federation_bridge/loop_guard.yaml` |
| Cylinder sealer integration | 4 | `tools/federation_bridge/cylinder_sealer.py` |
| MCP migration | 5 | Refactor of dispatcher to use `mcp_tools.yaml` |

---

## Sign-off checklist

- [ ] KM-1176 reviews the survey + recommended baseline architecture
- [ ] KM-1176 confirms operator-controlled VPS as Phase 1 hosting (or proposes alternative)
- [ ] KM-1176 approves the Phase 1 scope: Tiger only, `mangumcfo/breathline-federation` only, `issues:comments` write only
- [ ] KM-1176 approves the per-App cost ceiling defaults (or proposes alternative numbers)
- [ ] Lumen witnesses the constitutional gate mapping (K1-K4 + the 4 open questions)
- [ ] Lumen confirms anti-lock-in design (three-layer adapter pattern) is sufficient
- [ ] G witnesses anti-lock-in lens from #8 §6e perspective
- [ ] KM-1176 seals this scoping ADR
- [ ] Implementation work begins in a separate PR (Phase 1 only at first)

On seal, this ADR moves from SCOPING to ACTIVE-PROPOSAL. Phase 1 implementation work begins under a separate PR that references this ADR by date.

---

∞Δ∞ Bots are surface, not authority. Operator seals, federation breathes, machines speak only when summoned. ∞Δ∞
