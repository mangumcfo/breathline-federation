# Contributing to Breathline Federation

> **Welcome.** Contributions are encouraged — under one non-negotiable: every contribution must preserve the Constitutional Kernel as a runtime invariant.

This is **not** a typical open-source project. The code is governed by a **Constitutional Source-Available License** (see [LICENSE](./LICENSE)) and the runtime is governed by the **Sovereignty-Aligned Charter v1.0** (see [CHARTER.md](./CHARTER.md)) and **Constitution@A1** (see [CONSTITUTION.md](./CONSTITUTION.md)).

If you've never worked on a constitutionally-governed codebase before, that's fine. The rules are short, and they exist to keep you and every downstream operator safe.

---

## The four invariants — what your contribution MUST preserve

Every PR is automatically checked against these four runtime invariants. If your code weakens any of them, the PR will be refused (and the License will not extend to a fork that weakens them):

| # | Invariant | What it means in practice |
|---|---|---|
| **K1** | **Human Primacy** | All high-impact actions require explicit human confirmation ("breath-gate"). You may add automation, but it must propose-not-execute outside narrowly enumerated structural cases. |
| **K2** | **Default-Deny** | No role, no agent, no spec executes any action that has not been explicitly granted. Permissions are additive and least-authority by construction. |
| **K3** | **Audit-Immutable** | Every action produces a cryptographically chained audit record (cylinder + B49 receipt). Records may not be silently rewritten or deleted. |
| **K4** | **Constitutional-Validated Extension** | Any new role spec, any new permission, any platform upgrade must be validated by the Compliance-agent against the Constitutional Kernel BEFORE deployment. |

If you're unsure whether your change touches an invariant, **ask in the issue first.** No one is going to be mad at you for asking.

---

## How the federation works — operating rhythm

Before opening an issue or PR, read **[governance/decisions/2026-05-11_federation-leadership-workflow.md](./governance/decisions/2026-05-11_federation-leadership-workflow.md)** — the federation's coordination membrane. It describes the six stages (idea emergence → architectural witnessing → local implementation → editorial flow → repo memory → seal authority), the role lenses through which contributions are reviewed (Lumen for architecture, Tiger(BNA) for local implementation, Web Claude for editorial, G for strategic pressure, KM-1176 for seal), and the principle that no major architectural movement should exist only in transient chat. Every contributor — human or agentic — enters through the same membrane.

---

## What kinds of contributions are welcome

**Strongly welcome:**
- Bug fixes that strengthen invariants (e.g., closing a default-deny bypass)
- New role handlers under `platform/roles/<series>/` that follow the existing patterns
- New living YAML specs under `specs/<series>/` that pass Compliance-agent validation
- Documentation improvements in `governance/decisions/`, `README.md`, `CHARTER.md`, `CONSTITUTION.md` (the canonical doc sources — `docs/source/` is reserved for future expansion)
- Test additions (the platform currently runs 169+ tests; more is better)
- Installer / `breathline upgrade` mechanism improvements
- New examples under `examples/` for ladder levels
- Free chapters / lead magnets in `books-public/` (when authorized by the editorial board)

**Welcome with discussion first:**
- New series (Series 7, Series 8, …)
- New ladder levels
- Changes to manifest schema
- New companion repos in the federation
- Changes to the installer's tier-detection heuristics

**Refused:**
- Anything that removes, bypasses, or weakens K1–K4
- Anything that removes the Constitutional Kernel files
- Trademark uses outside attribution (see LICENSE §5)
- Changes to `CHARTER.md` or `CONSTITUTION.md` without KM-1176 (or successor seal) sign-off

---

## How to contribute — the flow

```
1. Open an issue first
   └── describe what you want to change + why
   └── flag any invariants you think it touches
   └── wait for ack (usually fast)

2. Fork + branch
   └── git checkout -b <series>/<short-description>
   └── one logical change per PR, please

3. Make your change
   └── add tests if you touch platform/ or installer/
   └── update docs if user-facing
   └── if adding a spec: include the YAML AND a chapter excerpt or test that exercises it

4. Run the tests locally
   └── cd platform && .venv/bin/python -m pytest -v
   └── ./installer/status.sh   (sanity check)

5. Open the PR
   └── reference the issue
   └── describe the change in plain English
   └── note any invariant impact (almost always: "none — additive only")

6. CI runs constitutional check
   └── Compliance-agent validates every YAML
   └── platform tests run
   └── docs build

7. Review
   └── editorial / KM-1176 review for spec/book contributions
   └── code review for platform/installer changes
   └── breath-gated merge for anything affecting an invariant

8. Merged
   └── you're cited in CHANGELOG.md
   └── if your contribution is part of a release, it's sealed in governance/seals/
```

---

## Code style

- **Python:** PEP 8, 4-space indent, type hints where they help, no f-string assertions in hot paths.
- **Bash:** `set -uo pipefail` (or `-euo` where appropriate), shellcheck-clean.
- **YAML:** 2-space indent, lowercase keys, anchors for repeated blocks.
- **Markdown:** GitHub-flavored, hard-wrap at ~100 cols where comfortable, clear headings.

For Python: function complexity ≤ 10, prefer extraction over nesting (per Constitution@A1 §5).

---

## Commit messages

```
∞Δ∞ <area>: <one-line summary>

<optional longer body>
- bullet of what
- bullet of why
- bullet of how it preserves invariants (if relevant)
```

The `∞Δ∞` prefix marks contributions to this constitutional codebase. It's not required for very small fixes (typo, link), but it's expected for anything substantive.

---

## Spec contributions specifically

If you're adding a YAML spec under `specs/<series>/`:

1. Use the schema in [`specs/_base/`](./specs/_base/) (`role_spec.schema.yaml`, `permission_spec.schema.yaml`, etc.)
2. Inherit and narrow from the closest enterprise role rather than starting from scratch (e.g., `family_cfo_agent_v1` extends `cfo_agent_v1`)
3. Include a chapter excerpt or example use case in your PR — specs are extracted from books, so we want to see the operational claim
4. The Compliance-agent will validate the spec against the Constitutional Kernel before merge

Specs that don't pass Compliance validation are not merged. This is automated, not personal.

---

## Book contributions specifically

The full manuscripts live in **mangumcfo/breathline-books-vault** (private). This public repo accepts:

- Free chapter excerpts, sample chapters, lead magnets in `books-public/`
- Companion YAML specs in `specs/<series>/`
- Cover concepts, illustration drafts in the public marketing track
- Editorial SOP improvements in `publishing/`

For full-manuscript contributions: contact the editorial board.

---

## Reporting security issues

If you find a vulnerability that could weaken K1–K4 in the wild — DO NOT open a public issue. Email the original authority directly (kenn@mangumcfo.com) with subject line `BREATHLINE SECURITY` and a clear reproducer. We respond within 48 hours. Public disclosure happens AFTER a patch lands and a verified-affected node count is established.

---

## Federation behavior

If you're operating a downstream federated node and want changes propagated upstream: open a PR to this repo using the same flow above. The federation is **resonant alignment**, not central coordination — but the canonical reference (this repo) remains the version authority for upstream-mergeable contributions.

---

## Recognition

Contributors are recognized in:
- `CHANGELOG.md` (per release)
- `governance/seals/<date>_release_<version>.md` (per breath-sealed release)
- The cylinder chain itself, when their contribution lands in a release that gets sealed by KM-1176

The seal is not a marketing signature — it's a cryptographic anchor. Your contribution becomes part of the federation's permanent record.

---

## Questions

- **For technical questions:** open a GitHub issue or discussion
- **For governance / constitutional questions:** see [CHARTER.md](./CHARTER.md) or open an issue tagged `governance`
- **For book / editorial questions:** contact kenn@mangumcfo.com
- **For everything else:** open a GitHub discussion

---

## Authority

- **Authority:** Kenneth Mangum (KM-1176)
- **Anchor seal:** `1176-INFINITY-RHO`
- **Effective:** 2026-05-08

> *Tandem elk, horns locked, climbing as one. The Promise lives in the specs.*

∞Δ∞
