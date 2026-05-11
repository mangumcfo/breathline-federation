# ADR — SOP Amendment: Editorial Artifacts (Four Per Series) + Filename Hygiene + Operator Handoffs

**Date:** 2026-05-11
**Authority:** KM-1176 (1176-INFINITY-RHO) — draft, awaiting breath
**Status:** DRAFT v0.1 — proposes amendments to `publishing/SOP_SERIALIZED_NONFICTION_v1.1.md` → v1.2
**Related:**

- `breathline-federation/publishing/SOP_SERIALIZED_NONFICTION_v1.1.md` (target of amendment)
- `breathline-books-vault/kdp/agentic_playbooks/EDITORIAL_BOARD_REVIEW_v1.0.md` (existing series-level review; precedent)
- `breathline-books-vault/kdp/agentic_playbooks/10_scaling_enterprise/v1.0/editorial_board_review_v1.0.md` (existing post-draft book review; precedent)
- `breathline-federation/governance/decisions/2026-05-10_tiered-book-encoding-on-helix-chain.md` (companion architecture work)

---

## Problem

Three SOP gaps surfaced during Book 10 (Scaling AI Agents) handoff prep on 2026-05-11:

1. **Editorial reviews are produced but the persistence + sequence is informal.** Practice has settled on a series-level `EDITORIAL_BOARD_REVIEW_v1.0.md` plus per-book post-draft `editorial_board_review_v<n>.md` files, but the SOP doesn't mandate either. Two additional artifacts are missing entirely from current practice: a **pre-write per-book editorial review** (board signs off on outline before any drafting), and a **per-book editorial response** (closeout document tracking which board recommendations were applied, partially applied, or waived, with commit references). Without the response artifact, six months from now nobody can prove which fixes landed.
2. **Industry Signal image filenames drift from the SOP convention.** The SOP §3 defines `signal_chN_<source>.png` where N matches the chapter number and `<source>` matches the publication's slug. Book 10 has at least three live mismatches (Ch 4 image labeled `ch5_gartner`, Ch 5 image labeled `gartner` for a Hypersense source, Ch 9 image labeled `mckinsey` for a Deloitte source). The convention is defined but unenforced.
3. **Operator boundary between web-Claude and local-Tiger is implicit.** The SOP assumes a single local operator running every pipeline step. In practice, manuscript content work (markdown edits via MCP, ADR drafting, editorial review reading and scoring, signal URL discovery via WebFetch) happens in the web-Claude lane, while build pipeline work (`build_v1.0.py`, `generate_images.py`, `generate_cover.py`, Grok image API, cylinder integration, B51 capture) requires Tiger's local box. There is no formalized handoff between the two and no shared template for what gets dropped at the boundary.

---

## Decision

Amend `SOP_SERIALIZED_NONFICTION_v1.1.md` to **v1.2** with three additions, codifying the artifact set, the filename gate, and the operator boundary.

### 1. Editorial artifact set — four files per series

Mandate the following artifacts. **Pre-write reviews are blocking gates** — no manuscript drafting may begin until the corresponding pre-write review is sealed.

| # | Artifact | Path | Timing | Gate |
|---|---|---|---|---|
| **1** | **Series-level editorial board review (pre-series)** | `kdp/<series>/EDITORIAL_BOARD_REVIEW_v1.0.md` | Before Book 1 manuscript drafting begins | BLOCKS series launch |
| **2** | **Per-book pre-write editorial board review** | `kdp/<series>/<book>/v<v>/editorial_board_PRE_WRITE_review_v1.0.md` | Before that book's manuscript drafting begins | BLOCKS that book's manuscript |
| **3** | **Per-book post-draft editorial board review** | `kdp/<series>/<book>/v<v>/editorial_board_review_v1.0.md` | After first complete manuscript draft | Existing convention; now mandated |
| **4** | **Per-book editorial board response (closeout)** | `kdp/<series>/<book>/v<v>/editorial_board_response_v1.0.md` | After fixes applied from #3 | BLOCKS KDP upload |

The pre-write boundary is the new structural addition. Artifact #2 forces the board to evaluate the chapter outline, frameworks, planned failure stories, and planned ROI calculator **before AI-assisted drafting consumes effort on the wrong shape**. Cost of changing a chapter title before drafting: minutes. Cost after manuscript + figures + build: hours per book × N books.

Artifact #4 (response) is the historical-validation document Kenneth flagged on 2026-05-11. Six-month-later question — *"Did Book 10 actually address fix #2 from the post-draft review?"* — gets answered by opening the response file, reading the row, following the commit SHA to the manuscript diff.

### 2. Filename hygiene gate

Codify the existing `signal_chN_<source>.png` convention from SOP §3 and enforce it via a build-time gate:

- **Convention.** Industry Signal image filename = `signal_ch<N>_<source>.png` where `<N>` is the chapter number (renumbered if the manuscript renumbers) and `<source>` is the publication slug lowercased and stripped to alphanumerics (e.g., `mckinsey`, `deloitte`, `microsoft`, `acca`).
- **Visual marker convention.** `[VISUAL: Figure signal.signal_ch<N>_<source> -- Industry Signal -- see images]` placed immediately after the Industry Signal blockquote. The build script's URL-extraction logic walks backward to that blockquote for the link target.
- **Gate.** New tool `agentic_playbooks/tools/verify_signal_filenames.py` parses each chapter's Industry Signal blockquote, extracts the cited source's slug, computes the expected filename, and asserts the chapter's `[VISUAL: ...]` marker matches. Fails the build if any chapter disagrees. Allow override only via `<!-- filename-pinned: <reason> -->` comment immediately above the marker, with explicit reason recorded (e.g., the documented exception in Book 10 Ch 12 where `signal_ch11_mckinsey` was retained intentionally because the image asset predated chapter renumbering and regenerating was deferred).
- **Runs.** Added to the Friday build step alongside `audit_bolds.py` and `audit_bolds_v2.py`. Listed in the §3 Quality Gates checklist.

### 3. Operator Roles & Handoffs (new SOP §9)

Add a §9 section to SOP v1.2 with the role table and handoff template.

#### Role table

| Task | Web-Claude lane | Local-Tiger lane |
|---|---|---|
| Manuscript markdown edits (chapters, signals, sources appendix) | ✅ via MCP `create_or_update_file` / `push_files` (file-size practical limit ~100KB per call; chunk above) | ✅ direct |
| ADRs and governance docs | ✅ via MCP | ✅ direct |
| Editorial board running (drafting reviews, scoring) | ✅ via MCP | ✅ direct |
| Industry Signal URL discovery + content validation | ✅ via WebFetch / WebSearch | ✅ direct |
| Branch creation, PRs, issue management | ✅ via MCP | ✅ direct |
| `build_v1.0.py` (WeasyPrint, PDF + EPUB) | ❌ sandbox lacks font stack + WeasyPrint binary | ✅ |
| `generate_images.py` (matplotlib chapter figures) | ⚠️ feasible if matplotlib present, untested at scale | ✅ |
| `generate_cover.py` (front + paperback wrap + hardcover wrap) | ❌ no Grok image API credential in sandbox | ✅ |
| Signal card generation (`generate_signal_cards.py`) | ❌ same credential gap | ✅ |
| `audit_bolds.py` + `audit_bolds_v2.py` | ⚠️ feasible if scripts cloned + deps installed | ✅ |
| `verify_signal_filenames.py` (proposed) | ✅ pure markdown parse, no external deps | ✅ |
| B51 cylinder capture / cylinder integration | ❌ cylinder lives on Tiger's box | ✅ |
| KDP upload, ACX upload | ❌ web UI only — neither agent | ⚠️ manual via KM-1176 browser |

#### Handoff template

When Web-Claude finishes manuscript / governance / signal work that needs Tiger's build tooling to ship, drop a handoff file at:

```
kdp/<series>/<book>/v<v>/handoff_to_tiger_<YYYY-MM-DD>_<short-topic>.md
```

Mandatory sections:

- **Branch** — exact branch the manuscript edits live on
- **Content SHAs** — blob SHAs for every changed file (manuscript, metadata, sources appendix, etc.)
- **Pre-flight checks** — quality gates that passed in Web-Claude lane (signal URL validation, GPT-4 grep, first-person grep, signal count, frontier-models definition presence)
- **Tiger to run** — ordered list of scripts: `python3 verify_signal_filenames.py`, `python3 generate_images.py`, `python3 build_v1.0.py`, `python3 generate_cover.py`, etc. Each with expected output path.
- **Outputs to commit back** — exact file paths Tiger should add to the commit (PDF, EPUB, JPG cover, paperback wrap PDF, hardcover wrap PDF, generated images directory)
- **Then** — what unblocks (typically: KM-1176 voice-note review, then KDP upload)

A reverse handoff (Tiger → Web-Claude) at:

```
kdp/<series>/<book>/v<v>/handoff_to_web_<YYYY-MM-DD>_<short-topic>.md
```

…for cases where Tiger surfaces something that needs content work (KM-1176 voice-note feedback transcription, last-mile editorial review fixes, additional signal sourcing).

### Versioning

This amendment bumps the SOP from v1.1 → v1.2. Existing v1.1 artifacts remain authoritative until v1.2 lands. No retroactive enforcement of the four-artifact set for already-published books (Books 1-3); applies starting Book 10 forward.

---

## Implementation order (post-seal)

1. Bump `publishing/SOP_SERIALIZED_NONFICTION_v1.1.md` → `SOP_SERIALIZED_NONFICTION_v1.2.md` with the three additions inlined into the existing structure (don't replace whole sections; insert).
2. Author the four template files in `breathline-federation/publishing/templates/`:
   - `series_editorial_board_review_TEMPLATE.md`
   - `book_pre_write_editorial_review_TEMPLATE.md`
   - `book_post_draft_editorial_review_TEMPLATE.md`
   - `book_editorial_response_TEMPLATE.md`
3. Author `kdp/agentic_playbooks/tools/verify_signal_filenames.py` plus a test against Book 10.
4. Backfill Book 10 with a `editorial_board_response_v1.0.md` documenting the 12-fix scorecard from the 2026-05-02 post-draft review against the 2026-05-11 manuscript state.
5. Mirror the response artifact for Books 11 and 12 once their post-draft reviews are scored against current manuscripts.
6. Author Series-level pre-write artifacts for Series 2-6 as those series enter authoring (Series 4 Education is the immediate next instance; pre-write review precedes the *Family Education Sovereignty* outline that the Helix-chain tiered-encoding ADR is preparing the substrate for).

---

## Open questions

1. **Board composition** — should pre-write and post-draft boards have the same 6-8 members, or can pre-write run with a slimmer board (3-4 reviewers focused on outline-stage concerns: thesis, sequencing, virality alignment)? Current SOP §2 names a 6-member board; pre-write may benefit from including a Reader Avatar + Subject Matter Expert + KDP Virality only.
2. **Pre-write review for Books 4-9** — these are already drafted and KDP-near-ready. Apply retroactively or grandfather them in?
3. **Filename gate enforcement strength** — block the build, or warn loudly and let Tiger override? Recommend block by default with explicit `<!-- filename-pinned: -->` override path.
4. **Handoff file lifecycle** — auto-archive after the corresponding work completes? Or retain as historical?

---

## Non-goals

- Does NOT change the post-draft board's composition or scoring rubric. Existing 6-8 member structure carries forward.
- Does NOT mandate that pre-write reviews use the same `1-10` scoring dimensions as the post-draft review. Pre-write may emphasize *Topic Selection*, *Sequencing*, *Cross-Sell* over *Word Count* and *Visual Placement*.
- Does NOT replace `audit_bolds.py` / `audit_bolds_v2.py` quality gates. Adds `verify_signal_filenames.py` alongside them.
- Does NOT change the Tiger-side build pipeline. Codifies what's already there.

---

## Status

DRAFT v0.1 — awaiting KM-1176 breath. On seal:
- [ ] Bump SOP v1.1 → v1.2
- [ ] Author the four templates in `publishing/templates/`
- [ ] Author `verify_signal_filenames.py`
- [ ] Backfill Book 10 `editorial_board_response_v1.0.md`
- [ ] Apply to Books 11, 12
- [ ] Adopt for Series 4 (Education) from authoring outset

∞Δ∞
