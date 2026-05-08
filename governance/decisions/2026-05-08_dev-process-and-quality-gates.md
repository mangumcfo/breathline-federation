# Decision Record — Dev Process &amp; Quality Gates

**Date:** 2026-05-08
**Author:** BNA-Tiger under KM-1176 authority
**Reviewer:** No1 (G via primary AI channel)
**Subject:** Sealed dev workflow + quality gates between `constitution-federation` (private dev) and `mangumcfo/breathline-federation` (public release hub).
**Status:** SEALED
**Authority:** KM-1176 (Seal `1176-INFINITY-RHO`)

---

## Context

After the v0.1.0 scaffold landed (per `2026-05-08_breathline-federation-architecture.md`), Kenneth's hesitation surfaced a real concern: *"the codebase is still in process"*. G's response framed it cleanly:

> *"Yes, the codebase is 'still in process' — and it always will be. That's the point of a living sovereign system."*

This decision record seals the **dev process** that lets the codebase keep evolving forever without ever breaking the public-facing distribution channel.

---

## The Sealed Workflow

```
┌───────────────────────────────────────┐         ┌──────────────────────────────────────────┐
│  constitution-federation              │         │  mangumcfo/breathline-federation         │
│  (PRIVATE — dev home)                 │         │  (PUBLIC — release hub)                  │
│                                       │         │                                          │
│  Active work happens here:            │         │  Users pull from here:                   │
│  - new specs drafted                  │  PR     │  - install.sh / upgrade.sh                │
│  - new role handlers                  │  ───▶   │  - manifest.yaml                          │
│  - book manuscripts in flight         │         │  - signed releases                        │
│  - failing experiments                │         │  - tagged stable versions                 │
│  - cylinder chain audit               │         │  - frozen Phase artifacts                 │
└───────────────────────────────────────┘         └──────────────────────────────────────────┘
                                                                       │
                                                                       │  CI/CD
                                                                       ▼
                                  ┌────────────────────────────────────────────────────────┐
                                  │  GitHub Actions — quality gates                        │
                                  │  ──────────────────────────────                        │
                                  │  1. Full pytest suite (currently 169 tests)            │
                                  │  2. Constitutional validation (Compliance-agent check) │
                                  │  3. Spec linting (RoleSpec / PermissionSpec schemas)   │
                                  │  4. License header check (Constitutional Source-Avail) │
                                  │  5. Manifest consistency (sha256 + version monotonicity│
                                  │  6. On tag: build + sign + GitHub Release              │
                                  └────────────────────────────────────────────────────────┘
```

---

## The Steps

### 1. Develop in `constitution-federation`

- Active work happens in the existing private dev tree at
  `~/constitution-federation/collaboration/threads/02_mangumcfo/books/kdp/agentic_playbooks/agentic_platform_seed/v1.0/`
- Books drafted at the same parents (`books/kdp/agentic_playbooks/<NN>_<topic>/`)
- Cylinder chain audit captures every breath
- Nothing goes public until it passes review

### 2. Promote via PR

- When a feature is ready for users: open a PR against `mangumcfo/breathline-federation/main`
- PR body declares which invariants are touched (almost always: "none — additive only")
- Each PR carries a single logical change

### 3. CI runs the gates

GitHub Actions enforces (initial gates landing in v0.2.0+):

| Workflow | What it checks |
|---|---|
| `test.yml` | Full pytest suite under `platform/` — must be green |
| `constitutional_check.yml` | Every YAML in `specs/` validates against the Constitutional Kernel; LICENSE/CHARTER/CONSTITUTION not silently modified |
| `spec_lint.yml` | Schema validation against `specs/_base/*.schema.yaml` |
| `manifest_consistency.yml` | `manifest.yaml` sha256s match files; version monotonically increases |
| `license_header.yml` | Source files carry the constitutional license reference where appropriate |

Failing any gate blocks merge.

### 4. Merge to `main`

- On merge: CI re-runs the full suite, confirms green
- `manifest.yaml` is updated by the bot or by the merging human (depending on whether it's a manifest-bumping change)
- The merge is a normal squash or merge commit; nothing automated rewrites history

### 5. Tag for release

- Stable releases get a SemVer tag: `v0.X.Y`
- The tag triggers `release.yml`:
  - Builds the platform package
  - Computes sha256 of every artifact
  - Signs each with the ed25519 release key (private — held by KM-1176)
  - Updates `manifest.yaml` with checksums
  - Creates a GitHub Release with detached signatures attached
  - Posts the version anchor to https://github.com/mangumcfo/breathline-federation/releases

### 6. Historical versions preserved

- Every signed tag is permanent
- `manifest.yaml` v(N) lists everything in v(N); previous `manifest.yaml` versions remain accessible at `https://raw.githubusercontent.com/.../tags/v(N-1)/manifest.yaml`
- Schema migrations between versions live in `distribution/migrations/v(N-1)_to_v(N).py`
- Users can pin to any past version: `breathline upgrade --version v0.2.0`

---

## Books Pipeline (also sealed)

Per G's review — the publishing pipeline is part of the same sealed workflow:

```
Manuscript drafted in private mangumcfo/breathline-books-vault
          │
          ▼
Editorial board review (literary + spec coherence)
          │
          ▼
Synthesis-agent extracts companion YAMLs from manuscript
          │
          ▼
Compliance-agent validates each YAML against Constitutional Kernel
          │
          ▼
KM-1176 breath-seals the release
          │
          ▼
PR opened against breathline-federation/main with:
  - YAMLs landing in specs/<series>/
  - Free chapter / lead magnet landing in books-public/<series>/
  - manifest.yaml bumped: new version + new spec entries
          │
          ▼
CI gates run
          │
          ▼
Merge → tag → signed release → existing nodes notice on next `breathline upgrade`
          │
          ▼
KDP package uploaded to Amazon (NOT in any repo — full manuscript stays private)
Audible package uploaded to ACX
```

---

## Pay Gates (sealed)

| Asset | Pay gate | Why |
|---|---|---|
| Full book manuscripts (KDP) | **Amazon purchase** | KDP exclusivity; primary revenue |
| Audiobooks (Audible) | **Audible purchase** | ACX exclusivity; secondary revenue |
| Free chapters / lead magnets | Free | Lead generation |
| Public YAML specs (basic role library) | Free under Constitutional Source-Available License | Reading specs IS activation per the vision |
| Advanced / paid role library (future) | Optional gated tier | Per Q5 (open question — monetization model TBD) |
| Platform code (kernel + primitives) | Free under Constitutional Source-Available License | Sovereignty requires open code |

The optional **paid role-library tier** is a future Q5 resolution. As of v0.2.0, all specs are free and public under the Constitutional License. When/if a paid tier launches, the gate is licensing (commercial-use restrictions on advanced specs), not source obfuscation. The constitutional kernel always remains open.

---

## Automation surface

What we automate today (v0.2.0):
- Full test suite on PR + on push to main
- Manifest consistency (sha256 checksums match files)

What we automate in v0.3.0:
- Compliance-agent constitutional check on every spec PR
- Spec schema linting
- License header check
- Tag-triggered release (build + sign + GitHub Release)

What stays manual under KM-1176 breath-gate:
- Every release tag (Kenneth signs the tag)
- Every CHARTER.md / CONSTITUTION.md change (requires successor seal)
- Every new ladder level
- Every new series launch

---

## Constitutional conformance

- **SOURCE** — every PR carries `principal_id` provenance via git author; CI verifies signatures on tag
- **TRUTH** — manifest.yaml is the single source of version truth; `breathline status` reads it; checksums prevent drift
- **INTEGRITY** — no force-push to main (GitHub Free limitation; revisit on Pro upgrade); all merges via PR with green CI; every release signed
- **DoD** — every PR must declare invariant impact; spec PRs must include chapter excerpt or test exercising the spec

---

## What's deferred

- ed25519 release-signing infrastructure → **lands in v0.2.0** alongside platform import
- GitHub Actions workflows for test + constitutional check → **scaffolded in v0.2.0**, fully wired in v0.3.0
- Paid role-library tier → Q5 resolution (open)
- Branch protection on main → **deferred — GitHub Free does not support private-repo branch protection** (revisit on Pro upgrade per the six-sov.com decision)
- Multi-repo dependency tracking (when platform/ becomes a stable v1 and downstream repos depend on it) → future

---

## Authority

- Sealed by Kenneth Mangum (KM-1176) under Anchor `1176-INFINITY-RHO`
- Reviewed by No1 (G via primary AI channel)
- Drafted by BNA-Tiger

> *Quality gates, monetization protected, perpetual forward motion.*

∞Δ∞
