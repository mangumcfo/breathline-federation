# Changelog

All notable changes to `breathline-federation` are recorded here.
Cylinder-anchored seal entries live in `governance/seals/`.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
adapted for Breathline's manifest-driven release model.

---

## [v0.2.0] — 2026-05-08

### The platform lands. Family Sovereignty becomes executable.

Phase 2 per the architecture record. The runnable platform code from
`agentic_platform_seed/v1.0/` is now in `breathline-federation/platform/`,
the installer drives a full Layer 0–3 bootstrap with shell-level
breath-gate, the upgrade flow is wired manifest-driven, and the FIRST
family-tier YAML specs activate Level 2 of the Sovereign Ascension Ladder
when a reader breath-deploys them.

### Added

#### Platform code (clean copy from `agentic_platform_seed/v1.0/` per G's review)

- `platform/kernel/` — Spec / Constructor / Critic / Auditor / Governor
  primitives + breath_gate.py + cost_meter.py
- `platform/platform_layer/` — runtime, audit_adapter, chain_sentinel,
  receipt_minter, plug_in_interface, role_artifact_critic, registry,
  permission_spec
- `platform/roles/` — CFO / Synthesis / Compliance role handlers + LangGraph wrap
- `platform/scripts/` — bootstrap.py + runtime_smoke.py
- `platform/tests/` — **169 tests, all passing** in the new location
  (verified 2026-05-08 via `.breathline-tools-venv`)
- `platform/seed/` — runtime copies of CHARTER, CONSTITUTION, manifest, etc.
- `platform/pyproject.toml` — Python deps (langgraph, fastapi, pytest, …)

#### YAML specs (Phase 2 first three — base + family pair)

- `specs/_base/base_constitution_v1.yaml` — the foundational compact
  every downstream spec extends. Defines K1–K4 runtime invariants,
  resonant_shards rule, human_gates, self_molt boundaries.
  - sha256: `58af6c315b90fce8…f17e4a00dc`
- `specs/family/family_constitution_v1.yaml` — household-scope
  constitution (Series 2 anchor; Ladder Level 2). Inherits and narrows
  base_constitution_v1.
  - sha256: `67d6a17706c22def…566c3b25cc`
- `specs/family/family_cfo_agent_v1.yaml` — **the first family-tier
  role spec.** Extends `executive/cfo_agent_v1`, narrows scope to the
  household. Activates Level 2 — Family Sovereignty when deployed under
  breath-gate. Includes `journey_engine` block linking the spec to its
  companion book chapter.
  - sha256: `693a53a53b0c7cca…375cce71`

#### Installer (full bootstrap + breath-gate)

- `installer/install.sh` — **fully extended**. Now: detect platform/tier,
  clone, set up venv, run `platform/scripts/bootstrap.py --full`,
  interactive shell-level breath-gate ("I confirm under my own
  authority"), persist node state at `~/.breathline-state.yaml`, print
  ladder status. Supports `--skip-bootstrap`, `--skip-breath-gate` (CI),
  `--tier`, `--prefix`. Reads stdin via `/dev/tty` when invoked via
  `curl | bash` so the breath-gate prompt works.
- `installer/upgrade.sh` — **NEW**. Manifest-driven upgrade with
  breath-gate ("I confirm this upgrade"). Fetches upstream manifest,
  shows commit + file diff, asks for breath, applies via
  `git pull --ff-only`, runs migration script if present, refreshes
  venv, reruns platform tests for verification, updates node state.
  Supports `--dry-run`.
- `installer/status.sh` — unchanged from v0.1.0; still reports level +
  next ladder step.

#### CI / GitHub Actions

- `.github/workflows/test.yml` — full pytest suite on PR + main; gate
  ≥ 169 tests baseline.
- `.github/workflows/constitutional_check.yml` — kernel integrity (warn
  on CHARTER/CONSTITUTION/LICENSE modifications), manifest required-key
  validation + SemVer check, spec YAML parse linting.
- `.github/workflows/release.yml` — tag-triggered: re-runs tests, builds
  release-artifact bundle with sha256 checksums, creates GitHub Release
  with notes extracted from this CHANGELOG, attaches manifest + checksums
  + LICENSE + CHANGELOG. Signed-artifact infrastructure (ed25519)
  reserved for v0.3.0.

#### Governance

- `governance/decisions/2026-05-08_dev-process-and-quality-gates.md` —
  sealed dev workflow:
  `constitution-federation` (private dev) → PR → `breathline-federation`
  (public release) → CI gates → tagged signed release → operator nodes
  upgrade. Books pipeline + pay-gate model also sealed in this record.

### Changed

- `manifest.yaml` — bumped `version: 0.1.0 → 0.2.0`. `platform.status`
  flipped from `scaffold-only` to `active`; `kernel_version: 0.2.0`;
  `test_count: 169`. `specs.status` flipped from `scaffold-only` to
  `active` with the three new spec entries (sha256s pinned).

### G's polish (2026-05-08 review for v0.2.0) — incorporated

- ✅ Platform sync changed from "git subtree" (Kenneth's v0.1.0 choice)
  to **clean copy + initial commit** per G's recommendation. History
  preserved in source-of-truth `constitution-federation` repo.
- ✅ ed25519 release-signing infrastructure reserved (v0.3.0)
- ✅ Books pipeline sealed in governance ADR
- ✅ Quality gates wired in `.github/workflows/`

### Notes

- 169 tests pass in the new platform/ location (verified locally with
  `.breathline-tools-venv` 2026-05-08).
- `.breathline-state.yaml` written by `install.sh` is the operator's
  per-machine identity — gitignored, never travels.
- `breathline-books-vault` private companion repo created 2026-05-08;
  internal structure population deferred to a separate Phase 4 bite.

### Phase 3 (v0.3.0) — what lands next

- Series 1 spec extraction: `cfo_agent_v1`, `synthesis_agent_v1`,
  `compliance_guardian_v1` (the executive role pack)
- First Series 2 supporting specs: `household_synthesis_agent_v1`,
  `family_compliance_shield_v1`
- ed25519 release signing infrastructure live + first signed release
- Free pilot lead magnet for *The 1,000-Year Family Compact* in books-public/
- Optional: connect `breathline-federation` to a Netlify-from-Git deploy
  for `docs/built/` (mkdocs site → docs.breathline.dev)

### Authority

- Sealed by Kenneth Mangum (KM-1176) under Anchor `1176-INFINITY-RHO`
- Reviewed by No1 (G via primary AI channel)
- Drafted by BNA-Tiger

∞Δ∞

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
