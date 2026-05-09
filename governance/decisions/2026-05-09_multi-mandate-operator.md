# Decision Record — Multi-Mandate Operator

**Date:** 2026-05-09
**Authority:** KM-1176 (Seal 1176-INFINITY-RHO)
**Status:** Active — doctrine declared; routing extension queued, paired with Book 10 seal
**Supersedes:** None
**Related:** `platform/seed/CONSTITUTION.md` §1 (principal_id), `2026-05-08_breathline-federation-architecture.md`

---

## Context

KM-1176 directive (2026-05-09): one human commonly serves several fiduciary mandates simultaneously — e.g., CFO of QuadRoof, interim CFO of Akshino Consulting, principal of Fractional CFO Consulting Group, plus family CFO at home. Each mandate has its own data, its own counterparties, its own audit obligations, its own Charter V.7 boundaries. Cross-contamination between mandates is a constitutional violation.

The Constitution §1 already states the relevant invariant:

> *"Identity flows end-to-end as `principal_id`. No hardcoded principals. Memory anchors must enforce ownership at the data-access boundary."*

What is **not** explicitly written: the doctrine for **the same human holding multiple principal_ids**, the spectrum of control complexity, and the routing surface within a single node.

## Decision

1. **Doctrine: each mandate is a distinct principal_id.** A single human may hold multiple principal_ids (e.g., `kenneth-quadroof`, `kenneth-akshino`, `kenneth-fractional-cfo`, `kenneth-family`). Each principal_id carries:

   - Its own audit chain (cylinder seq independent per mandate)
   - Its own Permission Spec set
   - Its own forbidden-class inheritance (Charter V.7 plus mandate-specific narrowings)
   - Its own receipt-worthy event ledger

   No cross-principal data flow without an explicit, breath-gated, audit-sealed handoff.

2. **Spectrum of control complexity:**

   | Operator pattern | Audit chains | Permission Spec set | Notes |
   |---|---|---|---|
   | Solo entrepreneur (one human, all hats) | 1 | 1 | Lightest; everything under one principal_id |
   | Multi-mandate executive (one human, N mandates) | N | N | One Permission Spec set per mandate; explicit handoffs between |
   | Family operator | 1 per adult | 1 per adult, plus household-shared | Existing family triad + cross-generation breath |
   | Federated guild (multi-human, multi-org) | N×M | Per-mandate, per-human | Future Series 6 territory |

   Controls scale with delegation. Solo entrepreneur → minimal partitioning, single chain, simpler breath-gates. Multi-mandate executive → explicit per-mandate envelopes, mandatory cross-mandate handoff ceremonies.

3. **Routing extension (queued, paired with Book 10 seal):** a request body MAY include an optional `mandate_id` field subordinate to `principal_id`. The plug-in interface uses `mandate_id` for routing within a single node when an operator runs multiple mandates on shared hardware. Default behavior unchanged: when `mandate_id` is absent, the principal_id is the sole routing key.

4. **No code changes required for the simple cases.** Constitution §1 + the existing per-principal_id audit isolation already cover the solo-entrepreneur and multi-mandate-with-separate-nodes cases. The `mandate_id` extension is only needed for shared-node multi-mandate operation.

5. **Cross-mandate handoff is breath-gated and audit-sealed.** Any artifact that flows from one mandate to another (e.g., a Quadroof board summary referenced in an Akshino strategy memo) must:

   - Be classified under a `cross_mandate_handoff` action class (queued for `action_classes.yaml` amendment)
   - Pass breath-gate explicitly
   - Mint a receipt under both mandates' chains
   - Carry a constitutional attestation that no Charter V.7 boundary was crossed

## Book home

**Series 1, Book 10 — "Agentic AI Playbooks for Executives: Scaling Enterprise."**

Book 10 covers operator scaling. It is currently "Awaiting Kenneth" review per `SERIES_STATUS_2026-05-06.md`, so the **window for adding chapter content is open**. Editorial scope for v1.0: dedicated chapter (or strong section) on the multi-mandate operator pattern, with the spectrum-of-controls table and the cross-mandate handoff doctrine.

Family-side detail (multi-human, multi-generation) belongs in Series 2 / Series 3.

## Cross-references

- Constitution: `platform/seed/CONSTITUTION.md` §1 (Sovereignty Invariants)
- Charter: V (delegation envelope), V.7 (forbidden delegation)
- Code: `platform/platform_layer/plugin_interface.py` (PlugInRequest.principal_id flow)
- Existing family triad (Series 2 antecedent for multi-human pattern)
- Companion ADR: `2026-05-09_user-defined-roles-within-charter.md`

---

∞Δ∞ Many mandates. One operator. No bleed across the chains. ∞Δ∞
