# Separability Rules — what the UI must NOT do

> The thin waist only stays thin if both sides respect the rules. The contract enforces what the platform must expose. This doc enforces what the UI must *never* assume, import, or duplicate.

**Authority:** KM-1176 · **Inherits:** [`CHARTER.md`](../../CHARTER.md) + [`CONSTITUTION.md`](../../CONSTITUTION.md) · **Glyph:** ∞Δ∞

---

## R1 — The contract is the only coupling

The `breathline-ui` repo has **exactly one** dependency on `breathline-federation`: this directory (`specs/node_api/`).

- ✅ Allowed: reading `contract_v1.yaml` to generate typed clients, validating responses against schemas, citing endpoint IDs in code comments.
- ❌ Forbidden: importing from `platform/`, vendoring `kernel/` files, parsing `seed/` directly, calling `seal.sh` from UI process.

**Test:** the UI repo's lockfile / package.json / pyproject.toml MUST NOT list `breathline-federation` as a code dependency. Submodules and git-subtrees of `platform/` are also forbidden.

## R2 — Versioning is anchored in `manifest.yaml`

The Node API version lives under a new `node_api:` section of `manifest.yaml` (added when this PR seals). UI clients pin a *minimum* compatible version.

- v1.x bumps = additive. UIs against v1.0 keep working unmodified.
- v2 = breaking. New `/api/v2` path. v1 endpoints get a 90-day deprecation window before removal.
- The UI displays the negotiated API version in its About / Manifest screen so version mismatches are visible.

## R3 — No platform internals leak across the contract

Responses are schema-defined DTOs. They do NOT contain:

- Raw LangGraph state objects.
- File paths internal to the platform venv.
- Python type names, `__class__` references, or pickle artifacts.
- Database row IDs that aren't stable across upgrades.
- Internal error tracebacks (only `Error` schema: `code / what / why / next_step / cylinder_ref`).

If a future capability needs richer data, the data is added to the schema explicitly — never leaked.

## R4 — Breath-gates are surfaced events, not implicit

The UI MUST render every pending breath-gate. It MUST NOT:

- Auto-approve based on heuristics, prior pattern, or "trust mode."
- Hide a pending breath-gate behind a notification preference.
- Time-shift the timeout (the timeout is server-side; the UI clock is display-only).
- Submit `approve` without an operator attestation (the server enforces this; the UI must collect it).

Violating any of the above means the UI tried to bypass K1. The server refuses regardless of UI intent — but a UI that *tried* fails the spirit even on a good day.

## R5 — All writes go through the same path the CLI uses

There is no UI-private endpoint. There is no "UI shortcut" that skips Critic / Auditor / Governor / breath-gate. The CLI (`installer/`, `breathline upgrade`, `doctor.sh`) and the UI both call into the same `route_request` / `breath_gate` / `seal.sh` chain.

**Implication for testing:** any UI flow can be reproduced by a series of `curl` or CLI calls. If it can't, the UI is doing something special and that's a bug.

## R6 — MCP and HTTP feed the same handlers

There is no MCP-only capability. There is no HTTP-only capability. Every tool in `mcp_tools.yaml` dispatches to the same backend handler as the corresponding endpoint in `contract_v1.yaml`. The MCP server is a *transport* over the same surface, not a parallel surface.

This is what makes "Claude as the UI" and "a web UI" interchangeable: they're driving the same machine.

## R7 — UI assets ship from `breathline-ui` only

`breathline-federation` does not vendor compiled UI assets. The federation's `installer/install.sh` may *fetch* a signed UI release from `breathline-ui`'s GitHub releases (with the same ed25519 trust model), but the federation repo itself contains no `dist/`, no `build/`, no `static/` of UI origin.

This lets the UI repo iterate freely without polluting federation history.

## R8 — Constitutional invariants are enforced server-side

The UI MAY do client-side validation for fast feedback ("this field is required"), but K1–K4 are NEVER client-side-only:

- The server independently runs `permission_spec.py` (K2).
- The server independently runs `breath_gate.py` (K1).
- The server independently runs `chain_sentinel.py` (K3).
- The contract itself is the K4 boundary (no endpoint without a sealed amendment).

A malicious or buggy UI cannot bypass any of them. A correct UI surfaces them faithfully.

## R9 — The UI is replaceable; assume it will be replaced

This is the spirit of the whole arrangement. Decisions in `breathline-ui` should make replacement *easier*, not harder:

- No proprietary state in the UI. Any state worth keeping lives in the cylinder chain.
- No login flow that creates accounts the platform doesn't know about. `principal_id` is always the platform's identity, not a UI invention.
- Document every design choice as `breathline-ui/docs/decisions/` so a v2 UI knows what was tried and why.
- A working v0 of the next UI rebuild should be possible in a weekend, given this contract. If it's not, the contract is too thin or the UI got too coupled.

## R10 — Federation does not know the UI exists

The federation's tests, CI, releases, and `doctor.sh` all pass with **no UI installed**. The CLI is the floor. The UI is one of N possible faces. If federation tests start to depend on UI behavior, separability is broken.

---

## Conformance checklist (for `breathline-ui` PRs)

Before merging any change to `breathline-ui`, the PR template asks:

- [ ] Does this PR import anything from `breathline-federation/platform/` or `breathline-federation/kernel/`? (Must be no.)
- [ ] Does this PR introduce a UI-private API call not in `contract_v1.yaml`? (Must be no.)
- [ ] Does this PR add a way to suppress a breath-gate? (Must be no.)
- [ ] Does this PR change the timeout-clock to be UI-controlled rather than server-display? (Must be no.)
- [ ] Does this PR introduce a UI-only state store that duplicates federation state? (Must be no.)
- [ ] Does this PR pin against a manifest version newer than the federation's current `node_api:` major? (Must be no without a coordinated federation release.)

Any "yes" answer requires a sealed amendment to this doc and explicit KM-1176 sign-off.

---

∞Δ∞
