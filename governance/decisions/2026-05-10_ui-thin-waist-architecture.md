# Architecture Decision — Thin-Waist UI Architecture for Breathline Federation

**Date:** 2026-05-10  
**Authority:** Kenneth Mangum (KM-1176)  
**Status:** PROPOSED — pending KM-1176 breath-seal on PR `claude/ui-architecture-spec-eLTR6`  
**Inherits:** [`CHARTER.md`](../../CHARTER.md) (lex superior) + [`CONSTITUTION.md`](../../CONSTITUTION.md)  
**Glyph:** ∞Δ∞

---

## Context

At v0.5.3, `breathline-federation` is a Python platform plus a CLI. There is no UI. Three motivating pressures converged at the 2026-05-10 review:

1. **Operator surface gap.** Executives and family operators reading the books deploy the platform via `curl | bash` and then have nothing visual to drive — no breath-gate inbox, no cylinder explorer, no role panel. The CLI works, but it under-represents the platform.
2. **Multi-series velocity.** With Series 1 in editorial review (books 10–12), Series 2 (Family) drafted, and Series 3+ in pipeline, the platform's role surface is going to keep expanding. A UI built tightly against today's Python internals will rot fast.
3. **Sovereignty constraint.** Whatever UI we build must enforce K1 Human Primacy, K2 Default-Deny, K3 Audit-Immutable, K4 Constitutional-Validated Extension at the same fidelity as the CLI does today. "Just put a Streamlit dashboard on it" fails this test the moment a sloppy frontend bypasses a breath-gate.

KM-1176 (the operator) framed the constraint directly: *"I'd like to see a UI that's separate from the back end. That's completely separate that we could recreate at any point in time and build maybe a thousand different ways."*

That's a textbook case for a thin-waist architecture.

## Decision

We adopt a **thin-waist architecture** with three components:

1. **The contract** — a versioned Node API specification, living in `specs/node_api/`, defining the HTTP/JSON surface (`contract_v1.yaml`) and an MCP surface (`mcp_tools.yaml`) that any UI or AI agent uses to drive a sovereign Breathline node. The contract is the *only* coupling between platform and UI.
2. **The platform** — `breathline-federation` (this repo) implements the contract by extending the existing FastAPI app in `platform/platform_layer/plugin_interface.py`. All constitutional invariants are enforced behind the contract; the UI is treated as untrusted.
3. **The UI** — a separate repo `breathline-ui` (to be created on contract sign-off) consumes the contract. The federation does not vendor UI assets. The UI is structurally rebuildable from scratch.

The first UI face is a **local web UI** served by the node on `127.0.0.1:8421`, accessed via browser. Sovereignty stays at the edge. Additional faces (desktop, MCP-only) can land later as additive surfaces against the same contract.

## Why a separate repo (not a monorepo subdirectory)

Industry practice is split. Grafana, GitLab, and VS Code use monorepos; Kubernetes Dashboard, Plex, and most HashiCorp UIs use separate repos. The deciding factors:

| Factor | Monorepo wins | Separate repo wins | Our case |
|---|---|---|---|
| Release cadence | Same | Different | **Different** — federation releases are book-driven; UI iterates on its own clock |
| Team boundary | Same team | Different teams | Solo operator, but conceptually separate concerns |
| API stability | Internal/unstable | Stable contract | **Stable** — that's the whole point of this PR |
| Replaceability goal | Not stated | First-order goal | **First-order goal** (operator's words) |
| Coupling temptation | High in monorepo | Low across repos | We need the structural backstop |

For solo operators, the "two-repos-to-sync" pain that hurts teams is essentially absent. The risk is the *opposite*: a monorepo subdirectory is one `import` statement away from coupling, and a future Claude session — having the platform code right there — will reach for it.

**Separate repo enforces by structure what the contract enforces by rule.**

## Why local-first web UI as the first face

- Familiar to operators on any device with a browser.
- No new install pipeline beyond the existing `installer/install.sh`.
- Matches the sovereign / local-first ethos: each node serves its own UI, no remote dependency, no third-party telemetry.
- Doesn't preclude a Tauri/Electron desktop wrapper later (that's just the same web UI in a window).
- Doesn't preclude an MCP-only "Claude as the UI" mode — `mcp_tools.yaml` ships in v1 alongside HTTP precisely to make that available immediately.

## What we are NOT deciding here

- **Specific UI framework** (React/Svelte/Vue/HTMX). That's `breathline-ui`'s call. The contract is framework-agnostic.
- **Visual design system.** The IA doc constrains *what* the UI surfaces; the visual treatment is downstream.
- **Implementation timeline for the platform-side server runtime.** This PR is spec-only. The server runtime that satisfies `contract_v1.yaml` lands in a follow-on PR (likely v0.6.0 or v0.7.0 — coordinated with the next book seal per the Trigger Pattern).
- **Authentication model beyond `principal_id`-bearer.** Local-only deployments don't need much. If a future tier wants remote access, that's an additive amendment.

## Constitutional posture

Every UI write-operation request maps to an existing kernel primitive:

- Identity → `principal_id` flow (CONSTITUTION §1, K1)
- Permissioning → `platform_layer/permission_spec.py` (Charter V.7, K2)
- Breath-gate → `kernel/breath_gate.py` (Charter II.4.4, K1 again)
- Cost discipline → `kernel/cost_meter.py`
- Audit → `platform_layer/audit_adapter.py` + `chain_sentinel.py` (K3)
- Cylinder seal → operator-side `seal.sh` subprocess (unchanged)

The UI cannot synthesize a request that bypasses any of these. The server independently validates K1–K4 on every call. The contract itself — `contract_v1.yaml` — is K4: extending the API surface requires a sealed amendment, never a runtime decision.

This is consistent with the Authoritative Pattern Rule: the contract leads just enough to make the operator surface real, but does not race ahead of platform capability.

## Manifest impact

On seal of this PR:

```yaml
# manifest.yaml — to be added
node_api:
  status:        "specification (v1, unreleased)"
  contract:      "specs/node_api/contract_v1.yaml"
  mcp_tools:     "specs/node_api/mcp_tools.yaml"
  ui_ia:         "specs/node_api/ui_information_architecture.md"
  separability:  "specs/node_api/separability.md"
  current_version: "1.0.0-draft"
  runtime:
    target_release: "v0.7.0 (book-coupled per Trigger Pattern)"
    serves_at:      "127.0.0.1:8421 (default; opt-in remote bind)"
  ui_repo:
    name:        "mangumcfo/breathline-ui"
    visibility:  "to be created public on contract seal"
    governs:     "specs/node_api/separability.md"
```

The manifest section + sha256 of the four spec files becomes part of the v0.5.4 (or next-cut) signed release.

## Trigger pattern alignment

Per G's directive: *"After any new book chapter or series milestone is sealed, run a targeted release so the ladder advances in lockstep with content."*

This PR is content-side polish, not book-driven. We seal it independently as a v0.5.4 spec-amendment release. The actual server runtime that satisfies the contract is queued for v0.7.0 alongside whatever book-driven work lands then. The UI repo's first usable build is whenever post-runtime that the UI team (= operator + AI) chooses to ship it.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| UI drifts ahead of platform; calls endpoints that don't exist yet | Versioned contract; UI pins minimum manifest version; About screen surfaces mismatch |
| MCP agent tries to auto-approve breath-gates | `mcp_tools.yaml` deliberately omits approve/deny tools; server-side enforcement is the backstop |
| Future capability needs cross-cutting changes the thin contract can't express cleanly | v2 contract path is reserved; deprecation window protects existing UIs |
| Operator finds local-only UI too restrictive | Remote bind is a documented, breath-gated opt-in — not forbidden, just default-deny |
| Subdirectory coupling temptation re-emerges | Separability rules R1, R7, R10 + structural separate-repo backstop |
| Spec rots because no one consumes it yet | First UI face shipping in v0.7+ exercises the contract; until then it's a design artifact, intentionally |

## Alternatives considered

1. **Streamlit/Gradio quick-dashboard inside `platform/`.** Rejected: every K1–K4 invariant becomes Streamlit's problem to enforce; the next UI rewrite is a full rewrite.
2. **Single-repo monorepo with `ui/` subdirectory.** Rejected: solves nothing the separate repo doesn't, costs us the structural backstop.
3. **MCP-only first; skip the visual UI.** Rejected as a *first* face; *included* as a parallel face in v1. "Claude as the UI" is real but isn't sufficient — operators want a visual breath-gate inbox, an audit explorer, a ladder view.
4. **Build the contract incrementally, no spec PR.** Rejected: the whole point is that the contract is constitutional. It needs a sealed amendment to exist, not an emergent shape.

## Decision artifacts

- [`specs/node_api/README.md`](../../specs/node_api/README.md)
- [`specs/node_api/contract_v1.yaml`](../../specs/node_api/contract_v1.yaml)
- [`specs/node_api/mcp_tools.yaml`](../../specs/node_api/mcp_tools.yaml)
- [`specs/node_api/ui_information_architecture.md`](../../specs/node_api/ui_information_architecture.md)
- [`specs/node_api/separability.md`](../../specs/node_api/separability.md)

## Sign-off

- [ ] KM-1176 review of contract surface (cover the breath-gate and audit chain semantics first; everything else is downstream)
- [ ] KM-1176 review of separability rules (R4, R5, R8 are the load-bearing ones)
- [ ] KM-1176 sign-off on creating `mangumcfo/breathline-ui` (public) on PR seal
- [ ] KM-1176 breath-seal of this ADR + spec PR
- [ ] manifest.yaml `node_api:` section added in same release

On seal, this ADR moves from PROPOSED to ACTIVE. The Node API contract becomes constitutional code: extension only by sealed amendment.

---

∞Δ∞
