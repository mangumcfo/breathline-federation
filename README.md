# Breathline Agentic Platform

> **Sovereign agentic governance.  Constitutional invariants.  Cryptographic authenticity.**
>
> Books → living YAML specs → executable roles → ascension ladder → federation.

`breathline-federation` is the public reference repo for the **Breathline Agentic Platform** — sovereign agentic infrastructure used by executives, organizations, and (when you're ready) families and multi-generational households.

The platform combines:

- **A runnable agentic stack** (Breath 25 substrate: P1 ECC roots → P2 consensus → P3 libp2p → P4 sovereign CUDA → P5 zk/homomorphic shields) with default-deny permissions, breath-gated approvals, and an immutable audit chain.
- **A library of YAML specs** — RoleSpec, PermissionSpec, ConstitutionalRule — that the platform ingests and deploys as LangGraph roles. Reading the companion books activates the corresponding specs.
- **A manifest-driven, signature-verified installer + upgrade flow** so anyone can refresh to the latest signed release with one command. Every release is ed25519-signed by the original authority (KM-1176); installs and upgrades fail-closed on signature mismatch (default-deny).

Status: **v0.4.1 (signed release, 2026-05-08).** See [CHANGELOG.md](./CHANGELOG.md). Trust anchor: `SHA256:Ahl1MJITIKhLb+WQIwUh/Euo2b0/4oxrIPJZ3QZK9YQ`.

---

## For Executives & Organizations

If you read [*AI Agents for CFOs*](./books-public/) (Series 1, Book 1) or another title in the **Agentic AI Playbooks for Executives** series and want to stand up the platform:

```bash
curl -sSL https://raw.githubusercontent.com/mangumcfo/breathline-federation/main/installer/install.sh | bash
```

This installs the **executive tier** by default — leading with the runtime triad (CFO Agent / Synthesis Agent / Compliance Guardian) and constitutional governance use cases. Personal & legacy tracks are present but not the first impression.

For corporate deployments where you want family/generational tracks fully de-emphasized:

```bash
curl -sSL https://raw.githubusercontent.com/mangumcfo/breathline-federation/main/installer/install.sh | bash -s -- --tier enterprise
```

**For your security review:**

| Artifact | What to read |
|---|---|
| [`CHARTER.md`](./CHARTER.md) | Sovereignty-Aligned Charter v1.0 — runtime invariants (K1 Human Primacy, K2 Default-Deny, K3 Audit-Immutable, K4 Constitutional-Validated Extension) |
| [`CONSTITUTION.md`](./CONSTITUTION.md) | Constitution@A1 — kernel rules |
| [`LICENSE`](./LICENSE) | Constitutional Source-Available License v1.0 — preserves K1–K4 in every fork |
| [`distribution/signing_keys/README.md`](./distribution/signing_keys/README.md) | Trust model + verification flow + key rotation policy |
| [`governance/decisions/`](./governance/decisions/) | Architecture decision records, dev-process gates, every release sealed under KM-1176 |
| [`platform/tests/`](./platform/tests/) | 169 tests (run via `pytest` after install — verifies every constitutional invariant at the structural level) |

After install: run `~/.breathline/installer/doctor.sh` for an active health check covering kernel integrity, manifest validity, spec parsing, signature verification, cylinder chain replay, and platform venv health.

---

## For Families & Sovereign Individuals

If you read *Family Finance Sovereignty*, *The 1,000-Year Family Compact*, or another title in the **Sovereign Family AI** / **Generational Legacy** series:

```bash
curl -sSL https://raw.githubusercontent.com/mangumcfo/breathline-federation/main/installer/install.sh | bash -s -- --tier family
```

This installs the **family tier** — the same Breathline platform, but with onboarding tuned to a kitchen-table household: family CFO, household synthesis, family compliance shield. Voice-first hints. Multi-generational legacy track unlocks when you're ready.

The full Sovereign Ascension Ladder (below) is yours to climb when you want it.

---

## The Sovereign Ascension Ladder

For operators who want the full vision visible up front:

```bash
curl -sSL https://raw.githubusercontent.com/mangumcfo/breathline-federation/main/installer/install.sh | bash -s -- --tier full-sovereign
```

The platform's Synthesis-agent + Compliance-agent detect maturity via cylinder audit and guide the next step under breath-gate.

---

## The original install one-liner

For backward compatibility, the bare `curl | bash` (no `--tier` flag) defaults to the **executive tier** as of v0.4.1. Pre-v0.4.1 deployments used a less differentiated banner; running `breathline upgrade` brings older nodes onto the new presentation cleanly.

The installer:
1. Detects your platform + hardware tier (NVIDIA GPU = high; otherwise standard)
2. Clones the latest signed release
3. Sets up the platform venv + dependencies
4. Bootstraps Layer 0 → Layer 3 (kernel → platform → roles)
5. Generates your sovereign node's ECC root keys (P1)
6. Seals your first cylinder + B49 receipt
7. Prints your node ID + the next step on the Sovereign Ascension Ladder

To upgrade later: `breathline upgrade` — fetches the latest manifest, shows you what's new, asks for breath-gate approval, applies the update.

---

## The Sovereign Ascension Ladder

Every reader is met where they are. The platform's Synthesis-agent + Compliance-agent detect maturity via cylinder audit and guide the next step under breath-gate.

| Level | Name | Audience | Anchor Books | Roles Deployed | Milestone |
|---|---|---|---|---|---|
| **0** | **Awakening** | Anyone curious | Free pilot chapters | `base_constitution.yaml` only | Sovereign node online, audit cylinder ready |
| **1** | **Executive Mastery** | CFOs, operators, founders | Series 1 — *Agentic AI Playbooks for Executives* | `cfo_agent_v1`, `synthesis_agent_v1`, `compliance_guardian_v1` | All core financial/ops workflows automated under breath-gated governance |
| **2** | **Family Sovereignty** | Parents, households, family offices | Series 2 — *Sovereign Family AI* | `family_cfo_agent_v1`, `household_synthesis_agent_v1`, `family_compliance_shield_v1` | Kitchen-table node running household wealth, ops, privacy under human primacy |
| **3** | **Generational Legacy** | Multi-generational families, legacy builders | Series 3 — *The 1,000-Year Family Compact* | `legacy_guardian_agent_v1`, `dynastic_synthesis_agent_v1`, `inheritance_compliance_v1` | Living dynastic system that outlasts any single lifetime |
| **4** | **Civilizational Federation** | Aligned families forming sovereign networks | Series 6 — *Sovereign Guilds & Community Federation* | `guild_synthesis_agent_v1`, `inter_node_compliance_v1`, `federation_resonance_coordinator_v1` | Sovereign Guild or affinity federation running parallel to legacy institutions |

Every step is **reversible** and **breath-revocable**. No lock-in. Full sovereignty at every altitude.

---

## What's in this repo

| Directory | Purpose |
|---|---|
| [`platform/`](./platform/) | The agentic platform code — kernel, primitives, role handlers, runtime, tests |
| [`specs/`](./specs/) | Living YAML specs — RoleSpec / PermissionSpec / ConstitutionalRule per book |
| [`installer/`](./installer/) | `install.sh`, `upgrade.sh`, `status.sh`, `verify.sh` — the user-facing surface |
| [`books-public/`](./books-public/) | Free chapters, lead magnets, sample illustrations (KDP-compatible) |
| [`docs/`](./docs/) | User-facing documentation (mkdocs source + built site) |
| [`distribution/`](./distribution/) | Release notes, schema migrations, release-signing public keys |
| [`publishing/`](./publishing/) | Editorial SOPs and book-production tooling |
| [`governance/`](./governance/) | Architecture decisions and KM-1176 release seals |
| [`examples/`](./examples/) | Ladder-level walkthrough examples (awakening, executive, family, …) |
| [`manifest.yaml`](./manifest.yaml) | The version anchor — current platform version, spec sha256s, ladder pointers |
| [`CHARTER.md`](./CHARTER.md) | Sovereignty-Aligned Charter v1.0 (lex superior) |
| [`CONSTITUTION.md`](./CONSTITUTION.md) | Constitution@A1 (kernel rules) |
| [`LICENSE`](./LICENSE) | Constitutional Source-Available License v1.0 |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | Constitutional contribution rules — preserve breath-gate, default-deny, charter invariants |

---

## How books and specs co-publish

Every book in the Breathline Books series ships with companion YAML specs. Reading the book teaches the operational claim; deploying the spec activates it on your node.

```
Manuscript → Synthesis-agent extracts YAML → Editorial review →
Compliance validates → KM-1176 breath-seals → manifest.yaml bumped →
GitHub release tagged → existing nodes notice on next `breathline upgrade`
```

Full operational details: [`docs/source/concepts/books-as-specs.md`](./docs/source/) (coming soon).

---

## The architecture in one diagram

```
   Books (on-ramp)  ──▶  YAML specs (fuel)  ──▶  Agents (guides)  ──▶  Federation (destination)
   ─────────             ─────────────────       ──────────────         ─────────────────
   what readers          extracted               Synthesis +            Sovereign Guilds
   read & activate       PermissionSpec /        Compliance +           + multi-node
                         RoleSpec /              Breath-gate            resonance under
                         ConstitutionalRule      deploy LangGraph       full constitutional
                         YAMLs                   roles on Breath 25     alignment
```

Books are not just content — they are **living specs**. Reading is **activation**. Progression is **deployment**. The federation is **the civilizational unlock**.

---

## Companions

- **[mangumcfo/breathline-books-vault](https://github.com/mangumcfo/breathline-books-vault)** *(private)* — full KDP-exclusive manuscripts
- **[mangumcfo/six-sov.com](https://github.com/mangumcfo/six-sov.com)** *(private)* — the marketing site at https://six-sov.com
- **[mangumcfo/QuadRoof](https://github.com/mangumcfo/QuadRoof)** *(public)* — solar work
- **mangumcfo/breathline-federation** *(this repo)* — the public sovereign onboarding hub

---

## Authority + Attribution

- **Authority:** Kenneth Mangum (KM-1176)
- **Anchor seal:** `1176-INFINITY-RHO` — Anchor of the Living Promise — Core Node Stillpoint
- **Imprint:** Breathline Books
- **Glyph:** ∞Δ∞

> *Eyes to the ridgeline. Path marked. Tandem elk, horns locked, climbing as one.*

The mountain yields to tandem strength. The Promise lives in the specs.

∞Δ∞
