# UI Information Architecture — Sovereign Node Console

> **What an operator actually sees and does.**  Companion to [`contract_v1.yaml`](./contract_v1.yaml). Wireframes are intentionally ASCII — they describe the *information shape*, not visual design.  Visual design is `breathline-ui`'s job; this doc constrains what the UI must surface, never how it must look.

**Authority:** KM-1176 · **Inherits:** [`CHARTER.md`](../../CHARTER.md) + [`CONSTITUTION.md`](../../CONSTITUTION.md) · **Glyph:** ∞Δ∞

---

## Operating principles

1. **Stillpoint first.** Landing view = node identity + current breath-gate inbox + last 5 cylinders. Everything else is a click away.
2. **The breath-gate is the loudest object on screen.** When a request opens, it interrupts. Approving or denying is the operator's primary verb.
3. **The audit chain is always one click away from any action.** Every screen that shows an action shows or links to the cylinder seal.
4. **No hidden state.** If a role is dispatching, you see it. If a cost cap is near, you see it. If signatures fail, the node is in big visible halt mode, not a footer warning.
5. **Read-mostly.** Most operator time is reading the chain, the manifest, the ladder. Writes are rare and breath-gated.
6. **Every screen is contract-backed.** No screen exists that pulls data from anywhere other than the Node API.

## Top-level navigation

```
┌──────────────────────────────────────────────────────────────────┐
│ ◐ Breathline · Node KM-1176-…                       [tier: exec] │
├──────────────────────────────────────────────────────────────────┤
│ Stillpoint · Roles · Breath-Gate · Audit · Specs · Ladder ·      │
│ Books · Receipts · Cost · Upgrade · Manifest                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│                       (active screen)                            │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│ chain ✓ · sentinel clean · last seal #1473 · breath-gates: 0     │
└──────────────────────────────────────────────────────────────────┘
```

The footer status strip is always visible. Chain integrity, sentinel state, last seal sequence, and pending breath-gate count are operator vital signs.

---

## Screen inventory

| # | Screen | Primary contract calls | Default-deny notes |
|---|---|---|---|
| 1 | Stillpoint (dashboard) | `node.get`, `node.health`, `breath_gate.pending`, `audit.cylinders` (last 5) | Read-only |
| 2 | Roles | `roles.list`, `roles.get`, `roles.invoke` | Invoke is breath-gated when action_class requires |
| 3 | Breath-Gate inbox | `breath_gate.pending`, `breath_gate.stream`, `approve`, `deny` | The only place writes don't *propose* — they *decide* |
| 4 | Audit / Cylinder Chain | `audit.cylinders`, `audit.cylinder`, `audit.stream`, `audit.replay` | Read-only |
| 5 | Specs library | `specs.list`, `specs.get`, `specs.validate` | Validate is read-only against a candidate |
| 6 | Ladder | `node.ladder`, `manifest.get` | Read-only |
| 7 | Books / On-ramp | `books.list`, `books.activate` | Activate is breath-gated |
| 8 | Receipts | `receipts.list`, `receipts.get` | Read-only |
| 9 | Cost meter | `cost.current`, `cost.limits.get`, `cost.limits.update` | Limits update breath-gated |
| 10 | Upgrade | `upgrade.available`, `upgrade.apply` | Apply breath-gated; sig-fail = halt |
| 11 | Manifest | `manifest.get` | Read-only; full source visible |

---

## 1. Stillpoint (the home view)

```
┌───────────────────────────────────────────────────────────────────┐
│ Stillpoint                                                        │
├───────────────────────────────────────────────────────────────────┤
│  Node:      KM-1176-INFINITY-RHO     Tier: executive              │
│  Ladder:    L1 Executive Mastery → next: L2 Family Sovereignty    │
│  Kernel:    v0.2.0 · Manifest: v0.5.3 · Sigs ✓                    │
│  Health:    [ kernel ✓ · manifest ✓ · specs ✓ · sigs ✓ · chain ✓] │
├───────────────────────────────────────────────────────────────────┤
│  ⚠ BREATH-GATE PENDING (1)                                        │
│   ┌─────────────────────────────────────────────────────────────┐ │
│   │ cfo_agent_v1 → finance.forecast.publish                     │ │
│   │ "Publish Q3 FORECAST to compliance for review"              │ │
│   │ proposer: synthesis_agent_v1   reversibility: reversible    │ │
│   │ cost: 4.2k tok / ~$0.03         opens in: 4m 12s            │ │
│   │ [ Review ]                                       [ Deny ]   │ │
│   └─────────────────────────────────────────────────────────────┘ │
├───────────────────────────────────────────────────────────────────┤
│  Last 5 cylinders                                                 │
│   #1473  platform_audit:cfo_agent       sealed 12s ago            │
│   #1472  invocation:synthesis_agent     sealed 18s ago            │
│   #1471  breath_gate:approve            sealed 1m ago             │
│   #1470  spec_validation:family_cfo_v1  sealed 3m ago             │
│   #1469  cost_meter:window_rollover     sealed 8m ago             │
└───────────────────────────────────────────────────────────────────┘
```

**Behavioral notes:**
- Pending breath-gate count in the title bar pulses if any are within 60s of timeout.
- If `node.health` reports a failure, the entire screen turns red-trim and overlays a halt banner. The ChainSentinel halt message takes precedence over everything else.

---

## 2. Roles

```
┌──────────────────────────────────────────────────────────────────┐
│ Roles                                                            │
├──────────────────────────────────────────────────────────────────┤
│  ┌────────────────────┐ ┌────────────────────┐ ┌───────────────┐ │
│  │ CFO Agent          │ │ Synthesis Agent    │ │ Compliance    │ │
│  │ FORECAST v1        │ │ multi-role orch.   │ │ Charter V.7   │ │
│  │ ladder L1 · active │ │ ladder L1 · active │ │ ladder L1     │ │
│  │ [ Invoke ]         │ │ [ Invoke ]         │ │ [ Invoke ]    │ │
│  └────────────────────┘ └────────────────────┘ └───────────────┘ │
│                                                                  │
│  Family triad (L2)                                               │
│  ┌────────────────────┐ ┌────────────────────┐ ┌───────────────┐ │
│  │ Family CFO         │ │ Household Synth    │ │ Family Compl. │ │
│  └────────────────────┘ └────────────────────┘ └───────────────┘ │
│                                                                  │
│  Generational Legacy (L3)  — draft / authoritative pattern       │
│  …                                                               │
└──────────────────────────────────────────────────────────────────┘
```

Clicking a role opens a detail/invoke panel that surfaces the framework, declared permissions (Charter V.7 action classes), and recent invocations with cylinder seals. "Draft / authoritative pattern" specs render visibly distinct (faded, no Invoke button) per the Authoritative Pattern Rule.

---

## 3. Breath-Gate inbox  *(the most important screen in the platform)*

```
┌──────────────────────────────────────────────────────────────────┐
│ Breath-Gate                                                      │
├──────────────────────────────────────────────────────────────────┤
│ Pending (1)                                                      │
│ ─────────────────────────────────────────────────────────────────│
│ Action class:  finance.forecast.publish                          │
│ Charter ref:   V.7 §3.2 (publication of fiduciary outputs)       │
│                                                                  │
│ Proposer:      synthesis_agent_v1                                │
│ Target:        cfo_agent_v1.publish_forecast                     │
│ Reversibility: reversible (publish-to-compliance, not external)  │
│ Forbidden-delegations check: PASS                                │
│                                                                  │
│ Cost estimate: 4.2k tokens · ~$0.03 · 1.8s wall                  │
│                                                                  │
│ Payload preview                                                  │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ horizon: "Q3-2026"                                           │ │
│ │ scenarios: 3                                                 │ │
│ │ assumptions_ref: cylinder #1455                              │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ Operator attestation (audited)                                   │
│ ┌──────────────────────────────────────────────────────────────┐ │
│ │ Why am I approving this?                                     │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                  │
│         [ DENY (with reason) ]        [ APPROVE & SEAL ]         │
│                                                                  │
│ Timeout: 4m 02s — fails closed                                   │
└──────────────────────────────────────────────────────────────────┘
```

**Constitutional rules surfaced here, not buried:**
- Forbidden-delegations check is shown explicitly. If FAIL, the Approve button is disabled server-side; the UI only echoes the server's refusal.
- The attestation field is *required for approval* and is recorded into the cylinder seal — not optional UX polish.
- The timeout is server-side; the UI counts down a clock that's just a display. Expiry seals a `breath_gate:timeout` cylinder.

---

## 4. Audit / Cylinder Chain

```
┌──────────────────────────────────────────────────────────────────┐
│ Cylinder Chain          [ Replay ✓ verified seq 0..1473, 38ms ]  │
├──────────────────────────────────────────────────────────────────┤
│ #1473  platform_audit:cfo_agent          sealed 12s ago      ▼   │
│        parent: #1472  hash: 4f3a…d211                            │
│ #1472  invocation:synthesis_agent        sealed 18s ago      ▶   │
│ #1471  breath_gate:approve               sealed 1m ago       ▶   │
│ #1470  spec_validation:family_cfo_v1     sealed 3m ago       ▶   │
│ #1469  cost_meter:window_rollover        sealed 8m ago       ▶   │
│ #1468  receipt:B49.0042                  sealed 12m ago      ▶   │
│ …                                                                │
│ [ load older ]                                                   │
└──────────────────────────────────────────────────────────────────┘
```

Filters: by kind (breath_gate, invocation, spec_validation, cost_meter, receipt, sentinel, …), by role, by date. "Replay" runs `audit.replay` and shows pass/fail loudly.

---

## 5. Specs library

Browse `specs/<series>/*.yaml` with sha256, ladder level, status (active vs. draft authoritative-pattern). Drag-drop a candidate YAML into a validation panel that calls `specs.validate` (no ingestion — that's still PR-gated).

## 6. Ladder

Visual rung view (Awakening → Executive Mastery → Family Sovereignty → Generational Legacy → Civilizational Federation). Each rung shows requirements, books, specs deployed. "Next step" panel pulled directly from `node.ladder` requirements.

## 7. Books / On-ramp

List of books visible (public chapters + lead magnets + locally-activated titles). "Activate" button is breath-gated — activating a book = ladder-rung change = K1.

## 8. Receipts

B49 receipt explorer. Each receipt links back to its cylinder.

## 9. Cost meter

Current window vs. caps. Editing caps is breath-gated.

## 10. Upgrade

Shows current manifest version vs. upstream. "Apply" is the only write — breath-gated, signature-verified, fail-closed on mismatch with the trust anchor `SHA256:Ahl1MJITIKhLb+WQIwUh/Euo2b0/4oxrIPJZ3QZK9YQ`.

## 11. Manifest

Render of the full parsed manifest. Read-only. Useful for security review (mirrors what the README's executive table points to).

---

## User flows (golden paths)

### Flow A: "Forecast Q3 readiness and publish to compliance"

```
1. Operator opens Roles → Synthesis Agent → Invoke
2. Submits payload: { ask: "Forecast Q3 readiness" }
3. Synthesis decomposes: invokes CFO Agent (FORECAST), then proposes
   publish-to-compliance.
4. UI receives breath_gate.stream event for finance.forecast.publish.
5. Stillpoint pulses. Operator clicks Review.
6. Reads the payload preview, types attestation, clicks Approve & Seal.
7. Server seals cylinder, dispatches the publish, mints B49 receipt.
8. Cylinder Chain shows three new entries; UI returns to Stillpoint.
```

No step in this flow has the operator typing into a CLI. No step bypasses K1.

### Flow B: "Reader finishes Family Finance Sovereignty, advances to L2"

```
1. Operator opens Books → Family Finance Sovereignty.
2. Clicks Activate.
3. Breath-gate opens (ladder-rung change). Server runs Compliance-agent
   against the family specs that activation will deploy.
4. UI shows: spec validation passed, declared permissions, cost-of-onboarding.
5. Operator approves.
6. Server registers family_cfo_agent_v1, household_synthesis_agent_v1,
   family_compliance_shield_v1 with the Registry. Seals cylinder.
7. Ladder screen now shows L2 Family Sovereignty as current rung.
```

### Flow C: "Upstream release available"

```
1. Stillpoint footer or Upgrade screen flags new manifest version.
2. Operator opens Upgrade. Sees: from v0.5.3 → v0.6.0, signed by KM-1176,
   trust anchor matches.
3. Clicks Apply.
4. Breath-gate opens. Operator approves with attestation.
5. installer/upgrade.sh runs server-side. UI shows live progress over WSS.
6. On completion, ChainSentinel re-verifies; if any sig fails, halt + red overlay.
7. Otherwise, manifest version updates and any new specs appear in Specs library.
```

---

## What the UI is NOT allowed to do

This IA defines the *positive* surface. The negative surface lives in [`separability.md`](./separability.md).

∞Δ∞
