# Decision Record — Compliance Scope: Code + Spec Amendments

**Date:** 2026-05-09
**Authority:** KM-1176 (Seal 1176-INFINITY-RHO)
**Status:** Active — scope expansion declared; implementation queued, paired with Book 6 seal
**Supersedes:** None
**Related:** `2026-05-08_dev-process-and-quality-gates.md`, `2026-05-09_user-defined-roles-within-charter.md`

---

## Context

The Compliance role's action-class envelope today (per `platform/seed/action_classes.yaml`) is artifact-centric:

- `review_peer_outputs`
- `flag_charter_v7_violations`
- `generate_least_authority_report`
- `generate_compliance_evidence_bundle`

These cover artifacts produced by other roles at runtime. They do NOT cover:

- **Code changes** to the platform itself (kernel, platform_layer, role implementations)
- **Spec amendments** — changes to `seed/action_classes.yaml`, `seed/receipt_worthy_events.yaml`, role specs, manifest entries

KM-1176 directive (2026-05-09): in an enterprise context, code and spec changes are exactly where Charter V.7 violations or default-deny breaches would slip in. Compliance should structurally see them — but the scope must be **narrow enough not to break adoption**. Compliance is not a code-quality reviewer; it is a constitutional reviewer.

## Decision

1. **Add two new action classes to `seed/action_classes.yaml`** (via the standard amendment path: operator approval + Charter V.7 review):

   - `code_change_review` — "Review a proposed code change for Charter V.7 / default-deny / forbidden-list integrity"
   - `spec_amendment_review` — "Review a proposed spec amendment (action class, receipt-worthy event, role spec) for constitutional integrity"

2. **Wire CI to invoke `compliance_agent` on PRs touching governance-critical paths:**

   - `platform/seed/**` (any spec amendment)
   - `platform/kernel/**` (kernel changes)
   - `platform/platform_layer/permission_spec.py` (Charter V.7 enforcement)
   - `platform/platform_layer/audit_adapter.py` (chain integrity)
   - `platform/roles/*/role_spec.yaml` (role permission changes)

3. **Compliance scope is narrow and structural — not stylistic.** The reviewer checks:

   - Does the change preserve Charter V.7 forbidden-class inheritance?
   - Does the change preserve default-deny semantics?
   - Does the change preserve append-only role registration?
   - Does the change preserve audit-chain integrity (chain replay still passes)?
   - Does the change preserve principal_id end-to-end flow?

   **Out of scope:** code style, bug-finding, performance, test coverage. Those belong to the existing dev-process gates from `2026-05-08_dev-process-and-quality-gates.md`.

4. **Verdict semantics:**

   - **CONFORMS** — PR may merge
   - **DRIFT** — advisory; merge allowed with operator override + audit note
   - **DEFECT (Charter V.7 violation)** — blocking; merge refused regardless of operator approval. Mirrors the Governor's existing veto power on role specs.

5. **Defer implementation per Authoritative Pattern Rule.** Book 6 (Compliance & Audit) is the teaching home. Implementation lands in the v0.6.x release paired with Book 6's seal.

## Book home

**Series 1, Book 6 — "Agentic AI Playbooks for Executives: Compliance & Audit."**

The meta-layer expansion ("compliance reviews changes to compliance itself") fits naturally inside the existing compliance-as-structural-invariant teaching. Book 6 is "Done (113 items)" review and "Ready for KDP upload." Editorial scope for v1.0: short sidebar on compliance-as-meta-layer if voice/length permits; full doctrine in v1.1 or supplemental.

## Cross-references

- Existing compliance role: `platform/roles/compliance_agent/`
- Action class vocabulary: `platform/seed/action_classes.yaml`
- Existing dev-process gates: `2026-05-08_dev-process-and-quality-gates.md`
- Companion ADR: `2026-05-09_user-defined-roles-within-charter.md` (which itself triggers spec_amendment_review for new action classes)

---

∞Δ∞ Compliance reviews itself. Charter V.7 is the floor; style is not. ∞Δ∞
