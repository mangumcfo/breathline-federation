# Node API — the thin waist between Breathline and any UI

> **Specification only. No implementation in this PR.**
>
> This directory defines the stable, versioned interface a sovereign Breathline node exposes to *anything* that wants to drive it — a web UI, a desktop app, an MCP-speaking AI agent, or a future thing we haven't imagined yet. The platform stays sovereign. The UI stays replaceable.

**Authority:** Kenneth Mangum (KM-1176) · **Inherits:** [`CHARTER.md`](../../CHARTER.md) (lex superior) + [`CONSTITUTION.md`](../../CONSTITUTION.md) · **Glyph:** ∞Δ∞

---

## Why this exists

Today `breathline-federation` runs as a Python platform plus a CLI (`installer/`, `breathline upgrade`, `doctor.sh`). There is no UI. Building one directly against the Python internals would couple the UI to platform internals forever — exactly the wrong shape if we want to *rebuild the UI a thousand different ways* as the book series matures.

The answer is the **thin waist**:

```
  many UIs / agents (replaceable)
            │
            │  Node API contract  ← this spec
            ▼
  one platform (sovereign, audited)
```

Every UI talks to the same contract. Every contract operation maps to existing kernel primitives (`kernel/breath_gate.py`, `kernel/cost_meter.py`, `platform_layer/audit_adapter.py`, `platform_layer/chain_sentinel.py`, `platform_layer/registry.py`, `platform_layer/permission_spec.py`). Nothing in the UI can bypass K1–K4.

## What's in this directory

| File | Purpose |
|---|---|
| [`README.md`](./README.md) | This file — orientation and decision summary |
| [`contract_v1.yaml`](./contract_v1.yaml) | The HTTP/JSON API surface, versioned, schema-defined |
| [`mcp_tools.yaml`](./mcp_tools.yaml) | The same surface re-expressed as MCP tools so any AI agent can drive a node |
| [`ui_information_architecture.md`](./ui_information_architecture.md) | Screens, user flows, ASCII wireframes — what an operator actually sees |
| [`separability.md`](./separability.md) | The rules that keep the UI repo rebuildable — what the UI must *not* do |

The architectural decision is recorded in [`../../governance/decisions/2026-05-10_ui-thin-waist-architecture.md`](../../governance/decisions/2026-05-10_ui-thin-waist-architecture.md).

## What this spec is NOT

- **Not an implementation.** No code is being added in this PR. The contract is the deliverable.
- **Not a UI repo.** The UI lives in a separate repo (`breathline-ui`, to be created on contract sign-off). Federation does not ship UI assets.
- **Not a replacement for the CLI.** `installer/install.sh`, `breathline upgrade`, and `doctor.sh` keep working. The UI is an *additional* face on the same platform; the CLI is the floor.
- **Not a remote service.** The Node API runs locally on each sovereign node (default `127.0.0.1:8421`, configurable). Sovereignty stays at the edge.

## Constitutional posture (what the contract enforces server-side)

The UI is untrusted. Every constitutional invariant is enforced *behind* the API, not in front of it.

| Invariant | Enforcement |
|---|---|
| **K1 Human Primacy** | Every write operation that mutates state, dispatches a role, applies an upgrade, or modifies a spec passes through `kernel/breath_gate.py` server-side. The UI surfaces the prompt; it cannot suppress it. |
| **K2 Default-Deny** | `platform_layer/permission_spec.py` validates every dispatch against Charter V.7 action classes. UI cannot present an action the principal isn't permitted to attempt. |
| **K3 Audit-Immutable** | Every state-changing API call yields a cylinder seal reference in the response. `chain_sentinel.py` runs the boot+verify+on_seal cadence regardless of who initiated the request. |
| **K4 Constitutional-Validated Extension** | New endpoints can only be added by amending this spec via a sealed PR + manifest version bump. The contract itself is constitutional code. |

If an operation cannot be expressed without bypassing one of K1–K4, it does not belong in the contract.

## How this evolves

1. **v1.x — additive only.** New endpoints, new fields, new MCP tools. Existing UIs keep working.
2. **v2 — breaking changes.** Requires a sealed amendment under KM-1176, manifest version bump, deprecation window for v1 endpoints.
3. **Book-driven extensions.** When a new book series seals, any new role specs it activates inherit the existing contract automatically (the registry exposes them; no new endpoint needed). New *capabilities* the book introduces — e.g., audiobook UI, generational legacy ledger, federation peering — get their own additive endpoints.

Versioning is anchored in [`manifest.yaml`](../../manifest.yaml) under a new `node_api:` section once this PR seals.

---

∞Δ∞
