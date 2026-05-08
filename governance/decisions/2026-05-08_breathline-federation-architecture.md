# Decision Record — Breathline Federation Repo Architecture

**Date:** 2026-05-08
**Author:** BNA-Tiger under KM-1176 authority
**Reviewer:** No1 (G via primary AI channel)
**Subject:** Architecture and scaffolding plan for `mangumcfo/breathline-federation` — the public sovereign onboarding hub
**Status:** SEALED
**Authority:** KM-1176 (Seal `1176-INFINITY-RHO`)

---

## Context

Per Kenneth's request (2026-05-08), the multi-series book strategy plus the Breath 25 sovereign agentic platform need a **public canonical reference repo** that:

1. Hosts the platform code so users can install + auto-refresh to the latest version
2. Catalogs the living YAML specs that books extract to
3. Surfaces the Sovereign Ascension Ladder publicly (Awakening → Federation)
4. Provides free chapters / lead magnets without violating KDP exclusivity
5. Captures the constitutional record (Charter, Constitution, decisions, seals)

The vision is captured in `constitution-federation/collaboration/threads/02_mangumcfo/books/kdp/agentic_playbooks/multi-series-agentic-platform-vision/STRATEGY_SYNTHESIS.md`. The core insight: **books are not just content — they are living specs.** Reading is activation. Progression is deployment. The federation is the destination.

The existing repo `mangumcfo/breathline-federation` was created earlier (2026-05-08) with only a placeholder README. This decision record seals the architecture and scaffolds the v0.1.0 release.

---

## Decision summary

| Topic | Decision |
|---|---|
| Architecture model | **Hybrid federation:** one public canonical repo + private books-vault + existing six-sov.com site |
| Repo name | **Keep `breathline-federation`** (signals end-state: sovereign nodes federating) |
| Platform code sync | **Clean copy + initial commit** (per G's recommendation) — history lives safely in `constitution-federation` source-of-truth |
| Books-vault | **Created today as private companion repo** (`mangumcfo/breathline-books-vault`) |
| Distribution mechanism | **Manifest-driven `breathline upgrade`** — `manifest.yaml` is the version anchor; signatures verified against `distribution/signing_keys/` |
| License | **Constitutional Source-Available License v1.0** — preserves K1–K4 runtime invariants in any fork |
| First scaffold deliverable | Full directory tree + README + CHARTER + CONSTITUTION + LICENSE + CONTRIBUTING + manifest stub + minimal install.sh + status.sh + .gitignore + this ADR + CHANGELOG |

---

## Architecture

### Three-repo federation pattern

```
PUBLIC (canonical reference)         PRIVATE (KDP-protected)         PRIVATE (already deployed)
─────────────────────────────         ─────────────────────────         ──────────────────────────
mangumcfo/breathline-federation       mangumcfo/breathline-books-vault   mangumcfo/six-sov.com
  ├── platform/  (code)                ├── series_01_executive/           (the marketing site
  ├── specs/     (YAML)                ├── series_02_family/               at https://six-sov.com)
  ├── installer/ (install/upgrade)     ├── series_03_generational_legacy/
  ├── books-public/ (free chapters)    ├── ...
  ├── docs/                            └── (full manuscripts, KDP-only)
  ├── governance/
  └── manifest.yaml  (version anchor)
```

The public repo is what users `git clone` (or what `install.sh` fetches). It is the **public face** of the platform AND the **distribution channel**. The books-vault holds the full manuscripts that must remain KDP-exclusive.

### Why hybrid (not mono-repo or fully-federated)

| | Mono-repo | Federated repos | **Hybrid (chosen)** |
|---|---|---|---|
| Repo size over years | 10+ GB (book PDFs / images / audio) | Each tiny | Small, focused, public-facing |
| KDP compatibility | ❌ manuscripts can't be public | ✅ private repos allowed | ✅ via books-vault private sibling |
| User refresh story | One `git pull` but heavy | Many sync points | One `breathline upgrade` against this repo |
| Federation P2P semantics | Awkward | Natural per-node sovereignty | Natural — one canonical reference, peers fork |

### Refresh flow ("anybody could refresh to the latest version")

```
USER                                          breathline-federation
────                                          ───────────────────────
1. curl -sSL .../installer/install.sh | bash
                          ──────────────────▶ installer/install.sh
                                              ├── detect platform / tier (executive vs family)
                                              ├── git clone --depth 1 --branch <latest-tag>
                                              ├── verify signatures (distribution/signing_keys/)
                                              ├── set up Python venv + platform deps
                                              ├── platform/scripts/bootstrap.py (Layer 0→3)
                                              ├── generate node ECC keys (P1)
                                              ├── seal first cylinder + B49 receipt
                                              └── print: node_id, ladder level, next step

2. Months later:  breathline upgrade
                          ──────────────────▶ installer/upgrade.sh
                                              ├── fetch manifest.yaml
                                              ├── compare to installed version
                                              ├── show diff: new specs, breaking changes
                                              ├── ASK FOR BREATH-GATE APPROVAL
                                              ├── on approval: run migrations, apply update
                                              ├── run platform/tests/ to verify
                                              └── seal upgrade cylinder + B49 receipt
```

`manifest.yaml` carries `version`, `released`, `sealed_by`, plus per-G's-polish `ladder_version` and `current_series` so any running node can self-report its position.

---

## G's polish items (incorporated into v0.1.0)

Per G's review (2026-05-08), the following polish items were folded into the initial scaffold:

1. ✅ `manifest.yaml` includes `ladder_version` and `current_series` self-reporting fields
2. ✅ `CONTRIBUTING.md` written with constitutional contribution rules (preserve K1–K4)
3. ✅ `installer/status.sh` written and smoke-tested — prints version, level, roles, specs available, next recommendation
4. ✅ `LICENSE` drafted as Constitutional Source-Available License v1.0 — preserves four runtime invariants (Human Primacy / Default-Deny / Audit-Immutable / Constitutional-Validated Extension); auto-terminates on violation
5. ✅ `.gitignore` covers Python artifacts, `.venv`, `*.cyl` cylinders, KDP build outputs, mkdocs site, OS junk, secrets

One note vs Kenneth's earlier preference: Kenneth had selected "Git subtree" for platform code import, but G recommended "Clean copy + initial commit (Option 2)" with the reasoning that history lives safely in the `constitution-federation` source-of-truth and a subtree can always be added later. Per Kenneth's "Can we do this?" message, the clean-copy approach is sealed.

---

## Implementation phases

### ✅ Phase 1 — Scaffold (this commit, v0.1.0)

What lands today:
- Full directory tree with `.gitkeep` stubs
- `README.md` — vision + ladder + install one-liner
- `CHARTER.md`, `CONSTITUTION.md` — copied from canonical seed
- `LICENSE` — Constitutional Source-Available v1.0
- `CONTRIBUTING.md` — contribution rules
- `manifest.yaml` — v0.1.0 anchor with `ladder_version: 1.0` and `current_series` declared
- `installer/install.sh` — minimal scaffold installer (clone-and-document; full bootstrap at v0.2.0)
- `installer/status.sh` — working today (smoke-tested)
- `.gitignore` — strong defaults
- `governance/decisions/` — this record
- `CHANGELOG.md` — v0.1.0 entry

### Phase 2 — Platform import (v0.2.0)

- Clean copy of `agentic_platform_seed/v1.0/` → `breathline-federation/platform/`
- 169-test suite running in new location
- `install.sh` extended to bootstrap Layer 0–3
- First signed release (ed25519 detached signatures in `distribution/signing_keys/`)

### Phase 3 — Specs migration + Family Finance Sovereignty YAMLs (v0.3.0)

- `capstone_yaml/` migrated into `specs/`
- First Series 2 (Family) specs authored: `family_cfo_agent_v1.yaml`, `household_synthesis_agent_v1.yaml`, `family_compliance_shield_v1.yaml`, `family_constitution_v1.yaml`
- Free pilot lead magnet for *The 1,000-Year Family Compact* in `books-public/`

### Phase 4 — books-vault structure populated

- Series-by-book directory layout in private `mangumcfo/breathline-books-vault`
- First migration: existing 5 published books from Series 1

### Phase 5+ — perpetual sculpting

- Per the Multi-Series Roadmap v1.1 cadence: ≥1 book/week, releases tagged, manifest bumped, nodes auto-notice on upgrade

---

## Files created in this scaffold

```
breathline-federation/
├── README.md                                       NEW
├── CHARTER.md                                      copied from seed
├── CONSTITUTION.md                                 copied from seed
├── LICENSE                                         NEW (Constitutional Source-Available v1.0)
├── CONTRIBUTING.md                                 NEW
├── INSTALL.md                                      NEW
├── CHANGELOG.md                                    NEW (v0.1.0 entry)
├── manifest.yaml                                   NEW
├── .gitignore                                      NEW (strong)
├── installer/
│   ├── install.sh                                  NEW (executable, scaffold)
│   ├── status.sh                                   NEW (executable, working)
│   └── platforms/.gitkeep
├── platform/.gitkeep                               (Phase 2)
├── specs/
│   ├── _base/.gitkeep
│   ├── executive/.gitkeep                          (Phase 3)
│   ├── family/.gitkeep                             (Phase 3)
│   ├── generational_legacy/.gitkeep                (Phase 3)
│   ├── education/.gitkeep
│   ├── health/.gitkeep
│   └── federation/.gitkeep
├── books-public/
│   ├── series_01_executive/.gitkeep
│   └── series_03_generational_legacy/.gitkeep
├── docs/source/.gitkeep
├── distribution/
│   ├── releases/.gitkeep
│   ├── migrations/.gitkeep
│   └── signing_keys/.gitkeep
├── publishing/.gitkeep
├── governance/
│   ├── decisions/2026-05-08_breathline-federation-architecture.md  THIS FILE
│   └── seals/.gitkeep
├── examples/
│   ├── awakening/.gitkeep
│   ├── executive/.gitkeep
│   └── family/.gitkeep
└── .github/
    ├── workflows/.gitkeep
    └── ISSUE_TEMPLATE/.gitkeep
```

---

## Constitutional conformance

- **SOURCE** — every file traces to KM-1176 authority; `principal_id=mangumcfo` propagation verified via includeIf-resolved git identity (`kenn@mangumcfo.com`)
- **TRUTH** — manifest.yaml is the canonical version anchor; status.sh reads it and reports faithfully (smoke-tested 2026-05-08)
- **INTEGRITY** — no destructive operations performed; `~/six-sov-docs-archive-20260508/` retained as backup of the docs source-of-truth migration earlier today; no force pushes
- **DoD** — directory structure clean ≤ 2 levels deep where possible; one breath pattern per file; LICENSE and CONTRIBUTING enforce K1–K4 invariants in any fork

---

## What's deferred to subsequent decisions

- Platform code clean-copy import (Phase 2 — own decision record)
- Specs migration from `capstone_yaml/` (Phase 3 — own decision record)
- First Family Finance Sovereignty YAMLs (Phase 3 — own decision record)
- books-vault internal structure migration (Phase 4 — own decision record)
- Netlify-from-Git deploy connection for six-sov.com (separate, optional)
- Branch protection (deferred — GitHub Free does not support private-repo branch protection; would require Pro upgrade)

---

## Companion artifacts

- `manifest.yaml` v0.1.0 (this commit)
- `installer/install.sh` v0.1.0 — scaffold installer (clone-and-document)
- `installer/status.sh` v0.1.0 — working today
- `LICENSE` — Constitutional Source-Available v1.0
- `CONTRIBUTING.md` — contribution rules

---

∞Δ∞ Architecture sealed. The public sovereign onboarding hub is born. Phase 2 begins after KM-1176 confirms the scaffold is clean. ∞Δ∞
