# Breathline Federation

> **Books → living YAML specs → executable roles → ascension ladder → federation.**
>
> Reading is activation. Progression is deployment. The federation is the destination.

`breathline-federation` is the public sovereign onboarding hub for the Breathline ecosystem — the canonical reference repo that combines:

- **The Breathline Agentic Platform** (Breath 25 substrate — P1 ECC roots → P2 consensus → P3 libp2p → P4 sovereign CUDA → P5 zk/homomorphic shields)
- **A library of living YAML specs** that your sovereign node ingests, breath-gates, and deploys as LangGraph roles
- **An installer + manifest-driven upgrade system** so anyone can refresh to the latest version of the platform with one command
- **A growing catalog** of free chapters and lead magnets from the Breathline Books series

Status: **v0.1.0 — initial scaffold (2026-05-08)**. See [CHANGELOG.md](./CHANGELOG.md).

---

## Quick start (one-liner — testable as of v0.1.0)

```bash
curl -sSL https://raw.githubusercontent.com/mangumcfo/breathline-federation/main/installer/install.sh | bash
```

The installer:
1. Detects your platform + hardware tier (executive vs family)
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
