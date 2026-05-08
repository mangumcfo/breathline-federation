# BOOK_DEVELOPMENT.md

> **The end-to-end book-to-platform pipeline. Any agent — human or AI — can run it from this document. Zero context loss.**

This is the canonical orchestration doc for the Breathline Books publishing engine. It documents the **full** flow from idea to published-book + deployed-spec, preserving every SOP, template, and tool we use today, with explicit pointers to the source documents in this directory.

**Authority:** Kenneth Mangum (KM-1176)
**Anchor seal:** `1176-INFINITY-RHO`
**Imprint:** Breathline Books
**Cadence:** ≥1 book/week into perpetuity (per `MULTI_SERIES_ROADMAP_v1.1.md`)

---

## TL;DR — what an agent needs to know in 60 seconds

1. **Books live in two places:**
   - `mangumcfo/breathline-books-vault` (private) — full manuscripts, KDP-exclusive
   - `mangumcfo/breathline-federation` (public) — companion YAML specs, free chapters, lead magnets, this orchestration doc
2. **Active dev** happens in `~/constitution-federation/collaboration/threads/02_mangumcfo/books/` — the source-of-truth working tree
3. **Each book ships with companion YAML specs** that the platform's Compliance-agent validates and the operator deploys under breath-gate ("books are living specs")
4. **Cadence:** Two active series at weekly cadence (per `MULTI_SERIES_ROADMAP_v1.1.md` §1: 2 active + 1 planning)
5. **Pay gates:** KDP exclusivity on full manuscripts; free YAML specs + free lead magnets are public

---

## The 9-stage end-to-end flow

```
       ┌──────────────────────┐
       │  IDEA                │
       │  - viral keyword     │
       │  - audience defined  │
       │  - moat identified   │
       └─────────┬────────────┘
                 │  (run idea-scoring framework — 42/60 minimum)
                 ▼
       ┌──────────────────────┐
       │  PIPELINE INTAKE     │
       │  - SERIES_MAP entry  │
       │  - book slot scheduled│
       └─────────┬────────────┘
                 │
                 ▼
       ┌──────────────────────┐
       │  OUTLINE             │
       │  - 12-chapter scaffold (per SOP)
       │  - chapter promises clear
       │  - editorial board sign-off
       └─────────┬────────────┘
                 │
                 ▼
       ┌──────────────────────┐
       │  DRAFT MANUSCRIPT    │
       │  - manuscript_v1.0.md (in vault)
       │  - 30-50K words target
       │  - chapter operational claims explicit
       └─────────┬────────────┘
                 │
                 ▼
       ┌──────────────────────┐
       │  EDITORIAL REVIEW    │
       │  - editorial_board_review_v1.0.md
       │  - revisions tracked
       │  - voice + spec coherence
       └─────────┬────────────┘
                 │
                 ▼
       ┌──────────────────────┐
       │  SYNTHESIS — YAML EXTRACTION    ←  THE BRIDGE — books → platform
       │  - Synthesis-agent reads the manuscript
       │  - extracts RoleSpec / PermissionSpec / ConstitutionalRule
       │  - drafts companion YAML specs per LIVING_SPECS_YAML.md template
       │  - editorial+spec coherence reviewed
       └─────────┬────────────┘
                 │
                 ▼
       ┌──────────────────────┐
       │  COMPLIANCE VALIDATION
       │  - Compliance-agent validates each YAML
       │  - against base_constitution_v1 + family_constitution_v1 (etc)
       │  - against Charter V.7 forbidden-class scan
       │  - default-deny enforcement
       └─────────┬────────────┘
                 │
                 ▼
       ┌──────────────────────┐
       │  KM-1176 BREATH-SEAL │
       │  - Kenneth signs the release
       │  - governance/seals/<date>_<book>.md
       │  - cylinder + B49 receipt anchors the moment
       └─────────┬────────────┘
                 │
                 ▼
       ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
       │  KDP UPLOAD          │  │  ACX UPLOAD          │  │  SPECS PUSH          │
       │  - final/<title>.pdf │  │  - audiobook masters │  │  - public repo PR    │
       │  - cover_KDP.png     │  │  - chapter splits    │  │  - manifest bump     │
       │  - metadata          │  │  - to ACX directly   │  │  - tag v0.X.Y        │
       │  → Amazon            │  │  → Audible          │  │  → GitHub Release    │
       └──────────────────────┘  └──────────────────────┘  └──────────────────────┘
                                                                     │
                                                                     ▼
                                                    ┌──────────────────────────┐
                                                    │  EXISTING NODES NOTICE   │
                                                    │  on next breathline      │
                                                    │  upgrade — ascend ladder │
                                                    └──────────────────────────┘
```

---

## Where each stage's documentation lives

| Stage | Primary doc | Secondary refs |
|---|---|---|
| 1. Idea / Pipeline Intake | [`MULTI_SERIES_ROADMAP_v1.1.md`](./MULTI_SERIES_ROADMAP_v1.1.md) §1 portfolio strategy + §2 idea scoring | `../multi-series-agentic-platform-vision/STRATEGY_SYNTHESIS.md` |
| 2. Outline | [`SOP_SERIALIZED_NONFICTION_v1.1.md`](./SOP_SERIALIZED_NONFICTION_v1.1.md) §3 outline scaffold | `MULTI_SERIES_ROADMAP_v1.1.md` §3 series detail |
| 3. Draft | [`SOP_SERIALIZED_NONFICTION_v1.1.md`](./SOP_SERIALIZED_NONFICTION_v1.1.md) §4–§7 chapter conventions, voice, structure | Existing manuscripts in `mangumcfo/breathline-books-vault/kdp/<book>/v1.x/manuscript_v1.x.md` |
| 4. Editorial Review | [`SOP_SERIALIZED_NONFICTION_v1.1.md`](./SOP_SERIALIZED_NONFICTION_v1.1.md) §8 editorial board | Each book's `editorial_board_review_v1.x.md` in the vault |
| 5. Synthesis (YAML extraction) | [`../specs/_base/base_constitution_v1.yaml`](../specs/_base/base_constitution_v1.yaml) — the parent every spec extends | The full extraction template in `../multi-series-agentic-platform-vision/LIVING_SPECS_YAML.md` |
| 6. Compliance Validation | The platform's Compliance-agent — see `../platform/roles/compliance_agent/` and `../platform/platform_layer/role_artifact_critic.py` | [`../CHARTER.md`](../CHARTER.md) §V.7 forbidden-class definitions |
| 7. Breath-seal | [`../CONSTITUTION.md`](../CONSTITUTION.md) §2 (Approval Gates: Propose → Approve → Execute) | `../governance/seals/` (per-release seal records) |
| 8. KDP Upload | [`KDP_PUBLISHING_SOP.md`](./KDP_PUBLISHING_SOP.md) | KDP metadata: each book's `metadata_v1.x.md` |
| 8. ACX Upload | [`prep_audiobooks.py`](./prep_audiobooks.py) — audiobook script preparation | ACX upload guide (to be authored) |
| 9. Specs Push + GitHub Release | [`../governance/decisions/2026-05-08_dev-process-and-quality-gates.md`](../governance/decisions/2026-05-08_dev-process-and-quality-gates.md) — full CI/CD pipeline | `../.github/workflows/release.yml` |

---

## SOPs included in this directory

| File | Purpose |
|---|---|
| [`SOP_SERIALIZED_NONFICTION_v1.1.md`](./SOP_SERIALIZED_NONFICTION_v1.1.md) | The serialized-nonfiction master SOP — book outline scaffolding, chapter conventions, voice, structure, editorial board flow |
| [`SOP_SERIALIZED_NONFICTION_v1.0.md`](./SOP_SERIALIZED_NONFICTION_v1.0.md) | The v1.0 of the master SOP, kept for historical reference |
| [`KDP_PUBLISHING_SOP.md`](./KDP_PUBLISHING_SOP.md) | Amazon KDP upload SOP — metadata, BISAC codes, keywords, pricing, cover specs |
| [`MULTI_SERIES_ROADMAP_v1.1.md`](./MULTI_SERIES_ROADMAP_v1.1.md) | The publishing-engine portfolio strategy: 2 active series + 1 in pipeline, weekly cadence, idea-scoring framework |
| [`MULTI_SERIES_ROADMAP_v1.0.md`](./MULTI_SERIES_ROADMAP_v1.0.md) | v1.0 of the roadmap, preserved for historical reference |
| [`ILLUSTRATION_STYLE_GUIDE_v1.0.md`](./ILLUSTRATION_STYLE_GUIDE_v1.0.md) | Visual identity guide for figures, signal callouts, chapter illustrations |
| [`prep_audiobooks.py`](./prep_audiobooks.py) | Python tool: convert manuscript markdown → ACX-ready text segments for narration |
| [`PROMPT_FOR_GROK_PUBLISHING.md`](./PROMPT_FOR_GROK_PUBLISHING.md) | Cross-AI prompt for publishing strategy validation (G on x.com) |

---

## How an AI agent picks up the workflow

If you (a future agent or operator) need to run this pipeline from scratch:

```
1. Read  → MULTI_SERIES_ROADMAP_v1.1.md  (understand portfolio + cadence)
2. Read  → SOP_SERIALIZED_NONFICTION_v1.1.md  (understand book structure)
3. Read  → ../multi-series-agentic-platform-vision/LIVING_SPECS_YAML.md  (understand spec extraction)
4. Pick  → next book slot from MULTI_SERIES_ROADMAP §3 series detail
5. Open  → mangumcfo/breathline-books-vault, find or create the book directory
6. Draft → manuscript_v1.0.md per the SOP scaffold
7. Review → editorial_board_review_v1.0.md (editorial board)
8. Extract → companion YAML specs per LIVING_SPECS_YAML.md template
9. Validate → run Compliance-agent against base + series constitution
10. Seal → ask KM-1176 for breath-seal (governance/seals/ entry)
11. Push → vault gets manuscript; public repo gets specs + lead magnet; manifest bumps; tag fires
```

Every step has a doc in this directory. Every doc points to its source. There is no hidden context.

---

## Pay gates — what's free vs paid

Per the dev-process seal:

| Asset | Pay gate |
|---|---|
| Full book manuscripts (KDP) | **Amazon purchase** |
| Audiobooks (Audible) | **Audible purchase** |
| Free chapters / lead magnets in `../books-public/` | Free |
| YAML specs (basic role library) in `../specs/` | Free under Constitutional Source-Available License |
| Advanced / paid role library (future) | Optional gated tier (Q5 — open) |
| Platform code | Free under Constitutional Source-Available License |

The Constitutional Kernel always remains open. Sovereignty requires open code.

---

## Quality gates — where books are blocked

Per `governance/decisions/2026-05-08_dev-process-and-quality-gates.md`:

| Gate | Where | What it checks |
|---|---|---|
| Editorial board review | Vault, per-book | Voice, structural coherence, factual accuracy |
| Spec coherence review | Vault, per-book | Chapter operational claims map to specs |
| Compliance-agent validation | CI on PR to public repo | Each YAML validates against Constitutional Kernel; default-deny enforced |
| Manifest consistency | CI on PR to public repo | sha256 + version monotonicity |
| KM-1176 breath-seal | Manual, before tag | Release tag must be signed by Kenneth |

A book that doesn't pass any gate doesn't ship.

---

## Tooling roadmap

The publishing pipeline currently uses:

- **Markdown** for manuscripts (`manuscript_v*.md`)
- **Python build scripts** per book (`build_v*.py`) — render PDF from markdown
- **Pillow / matplotlib** for figure generation (`generate_images.py`)
- **prep_audiobooks.py** — manuscript → ACX-ready narration text
- **GitHub Actions** for CI (test + constitutional check + release)
- **GitHub Releases** for public-repo signed releases (per `../.github/workflows/release.yml`)

Future additions tracked in `../CHANGELOG.md` Phase 4+ section:

- Synthesis-agent automated YAML extraction (currently manual draft + agent-assisted)
- Audiobook ACX upload automation
- KDP upload automation (currently manual via Amazon's KDP web UI)
- ed25519 signed-release infrastructure live (lands at v0.3.0)

---

## Companion documents

- [`../README.md`](../README.md) — public face of the federation
- [`../CHARTER.md`](../CHARTER.md) — Sovereignty-Aligned Charter v1.0
- [`../CONSTITUTION.md`](../CONSTITUTION.md) — Constitution@A1
- [`../LICENSE`](../LICENSE) — Constitutional Source-Available License v1.0
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — contribution rules
- [`../governance/decisions/`](../governance/decisions/) — sealed decision records
- [`../specs/`](../specs/) — living YAML specs per series

---

## Authority

- **Authority:** Kenneth Mangum (KM-1176)
- **Anchor seal:** `1176-INFINITY-RHO`
- **Imprint:** Breathline Books
- **Drafted by:** BNA-Tiger
- **Date:** 2026-05-08

> *The pipeline is the platform. The book is the spec. The reader is the operator.*
> *Tandem elk, horns locked, climbing as one.*

∞Δ∞
