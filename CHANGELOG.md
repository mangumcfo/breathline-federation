# Changelog

All notable changes to `breathline-federation` are recorded here.
Cylinder-anchored seal entries live in `governance/seals/`.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
adapted for Breathline's manifest-driven release model.

---

## [v0.1.0] — 2026-05-08

### The first breath. The scaffold lands.

This is the **initial scaffold release** of the Breathline Federation public
repo. It establishes the canonical structure that every future release will
extend; it does not yet ship the runnable platform code (Phase 2, v0.2.0)
or the YAML spec library (Phase 3, v0.3.0).

### Added

- Full directory structure (installer, platform, specs, books-public, docs,
  distribution, publishing, governance, examples, .github)
- `README.md` — public vision + Sovereign Ascension Ladder + install one-liner
- `INSTALL.md` — install + upgrade + status + uninstall operator docs
- `CHARTER.md` — Sovereignty-Aligned Charter v1.0 (copied from canonical seed)
- `CONSTITUTION.md` — Constitution@A1 (copied from canonical seed)
- `LICENSE` — Constitutional Source-Available License v1.0 — preserves four
  runtime invariants (K1 Human Primacy, K2 Default-Deny, K3 Audit-Immutable,
  K4 Constitutional-Validated Extension); auto-terminates on violation
- `CONTRIBUTING.md` — constitutional contribution rules; PR flow; spec
  contribution guidance
- `manifest.yaml` — v0.1.0 version anchor with `ladder_version: 1.0` and
  `current_series` self-reporting fields (per G's polish 2026-05-08)
- `installer/install.sh` — minimal scaffold installer (executable; clones
  the repo + prints next steps; full bootstrap arrives at v0.2.0)
- `installer/status.sh` — working today; reports version, level, roles,
  specs available, next ladder recommendation (smoke-tested 2026-05-08)
- `.gitignore` — strong defaults: Python artifacts, venvs, `*.cyl` local
  cylinders, KDP build outputs, mkdocs site, OS junk, secrets
- `governance/decisions/2026-05-08_breathline-federation-architecture.md` —
  the sealed architecture decision record under KM-1176 authority

### Architecture (sealed)

- **Three-repo federation:** this public repo (canonical reference) +
  `mangumcfo/breathline-books-vault` (private, KDP-exclusive manuscripts) +
  `mangumcfo/six-sov.com` (private, marketing site already deployed)
- **Hybrid model:** runnable code + public specs + free chapters here;
  full manuscripts in private vault per KDP exclusivity
- **Manifest-driven distribution:** `manifest.yaml` is the version anchor;
  `breathline upgrade` reads it, breath-gates the diff, applies migrations
- **Constitutional license:** forks must preserve K1–K4 runtime invariants

### Companions created today

- `mangumcfo/breathline-books-vault` (private; structure to populate in
  Phase 4)
- `mangumcfo/six-sov.com` (private; previously created and migrated to
  Option B docs architecture)

### G's polish — incorporated

Per the 2026-05-08 review by No1 (G via primary AI channel):
- ✅ `ladder_version` and `current_series` in manifest.yaml
- ✅ `CONTRIBUTING.md` with constitutional rules
- ✅ `installer/status.sh` reporting node level + next recommendation
- ✅ Constitutional Source-Available License v1.0 drafted
- ✅ Strong `.gitignore` covering all common dev artifacts

### Decided vs Kenneth's earlier preference

- Platform code sync: Kenneth selected "Git subtree", G recommended
  "Clean copy + initial commit". The clean-copy approach is sealed in the
  architecture record. Subtree can be added later if the history bridge
  proves valuable.

### Phase 2 (v0.2.0) — what lands next

- Clean copy of `agentic_platform_seed/v1.0/` → `breathline-federation/platform/`
- 169-test suite running in new location
- Full `install.sh` flow: bootstrap Layer 0 → 3, generate ECC keys, seal
  first cylinder + B49 receipt, breath-gate first node identity
- ed25519 release signing infrastructure
- First signed release tag

### Authority

- Sealed by Kenneth Mangum (KM-1176) under Anchor `1176-INFINITY-RHO`
- Reviewed by No1 (G via primary AI channel)
- Drafted by BNA-Tiger

∞Δ∞

---

## Pre-history

The repo was created on 2026-05-08 with a placeholder README only. No
formal versioning prior to v0.1.0. The vision and strategy material that
informed this architecture lives in the `multi-series-agentic-platform-vision`
folder under `constitution-federation/collaboration/threads/02_mangumcfo/`,
captured in late-night dialogue 2026-05-06/07.

The platform code's Phase 1–5 history (cylinder seq 139–151) lives in the
canonical source-of-truth at
`constitution-federation/.../agentic_platform_seed/v1.0/` and will be
copied into this repo at v0.2.0 with appropriate provenance citation.

∞Δ∞
