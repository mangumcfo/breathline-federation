# Decision Record — User-Defined Roles Within Charter

**Date:** 2026-05-09
**Authority:** KM-1176 (Seal 1176-INFINITY-RHO)
**Status:** Active — platform pattern documented; thin scaffolder + book teaching queued
**Supersedes:** None
**Related:** `2026-05-08_v0.6.0-horizon.md`, `2026-05-08_breathline-federation-architecture.md`

---

## Context

In the 2026-05-09 operator-harness design conversation, KM-1176 raised whether the platform supports **user-defined roles** — i.e., a user creating a role specific to their enterprise (e.g., `quadroof_cfo_agent`, `akshino_interim_cfo`, `fractional_consulting_cfo`) without requiring the role to be book-authored first.

A prior conversation turn implied this required relaxing the Authoritative Pattern Rule. **That implication was incorrect.** Verification of the code (`platform/platform_layer/registry.py`, `platform/platform_layer/permission_spec.py`) confirms the platform already supports user-defined roles structurally; the constraints sit at the action-class layer, not the role layer.

### What the code actually allows today

1. `RoleRegistry.register_from_yaml(path)` loads any role spec from disk. **No whitelist of allowed role IDs.**
2. The role's `allowed_action_classes` must be drawn from the controlled vocabulary in `platform/seed/action_classes.yaml`.
3. Charter V.7 forbidden classes are merged into every role's forbidden list unconditionally; the Governor refuses any role spec that attempts to override.
4. Roles are append-only at Layer 3; revisions require re-bootstrap.

A user authoring `roles/quadroof_cfo/role_spec.yaml` that composes existing action classes (`read_structured_financial_data`, `produce_forecast_artifact`, `cite_assumptions`, etc.) **works today with zero platform changes.**

### The actual friction

If a custom role needs an **action class that does not yet exist** (e.g., a Quadroof-specific `solar_project_irr_calculation`), adding that class requires the existing amendment path declared in `action_classes.yaml`:

- `add_class:    operator approval + Charter V.7 review`
- `remove_class: operator approval + Charter V.7 review + rationale documented`
- `modify_forbidden: OFFLINE ONLY — no in-platform path may modify the Charter V.7 forbidden list`

KM-1176 directive (2026-05-09): the Charter V.7 review for adding new (non-forbidden) action classes should be a **lightweight, in-band interaction** with the enterprise's compliance reviewer — not a heavyweight offline ceremony. Charter V.7 forbidden-list modifications remain offline-only, as already specified.

## Decision

1. **Document the existing capability.** User-defined roles within Charter are a first-class supported pattern, not a platform extension. Anyone running a Breathline node may author a `role_spec.yaml` that composes existing action classes.

2. **Add a thin scaffolder (queued, paired with Book 5 seal).** A CLI surface of the form:

   ```
   breathline role create --from-template cfo_agent --name quadroof_cfo --principal-id km-1176
   ```

   that emits a valid `role_spec.yaml` in the operator's node tree, pre-populated with the template's allowed action classes (which the operator can then narrow). The scaffolder does NOT bypass any validation — the resulting spec still flows through `PermissionSpec.from_yaml` at boot.

3. **Streamline the action-class amendment path (queued, paired with Book 5 seal).** When a user-defined role declares an action class not in the controlled vocabulary, the platform should:

   - Emit a structured amendment-request artifact (kind=spec, kind_subtype=action_class_amendment)
   - Route it to the node's `compliance_agent` for Charter V.7 review
   - Surface the verdict to the operator with the same UX clarity as breath-gate prompts ("Class `X` requires Charter V.7 review. Reviewer: `compliance_agent`. Verdict: APPROVED / DENIED / NEEDS_DETAIL.")
   - On approval: append to `action_classes.yaml`, re-fingerprint the seed, audit-seal the amendment
   - **Charter V.7 forbidden-list modifications remain offline-only — no in-platform path.**

4. **Validation gates remain unchanged.** No relaxation of:
   - Charter V.7 forbidden-class inheritance
   - Append-only role registration
   - Critic CONFORMS verdict for elevation
   - Auditor synchronous seal per request

## Book home

**Series 1, Book 5 — "Agentic AI Playbooks for Executives: HR & Talent."**

HR is the natural domain for role-design teaching: a job description maps to a role spec; HR delegations map to action-class envelopes; Charter V.7 forbidden delegations map to the unrelaxable HR boundaries (no autonomous personnel decisions, no autonomous binding commitments).

Book 5 is currently "Done (Kenneth deep)" review and "Ready for KDP upload" per `SERIES_STATUS_2026-05-06.md`. The window for inserting full-chapter teaching has effectively closed pre-publication. **Editorial scope for v1.0:** sidebar or short appendix on the role-builder pattern, voice-permitting. **Full-chapter teaching:** queued for a v1.1 edition or a Series 1.5 supplemental volume.

## Cross-references

- Code: `platform/platform_layer/registry.py:60` (RoleRegistry.register_from_yaml)
- Code: `platform/platform_layer/permission_spec.py:147` (Charter V.7 enforcement)
- Seed: `platform/seed/action_classes.yaml` (controlled vocabulary + amendment_path)
- Charter: V.7 forbidden delegation targets
- Constitution: §1 (no hardcoded principals; principal_id flows end-to-end)
- Authoritative Pattern Rule: `2026-05-08_v0.6.0-horizon.md`

---

∞Δ∞ Roles are sovereign by composition. Charter V.7 is unrelaxable. ∞Δ∞
