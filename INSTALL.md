# Installing Breathline Federation

> **One command. One sovereign node. Constitutional from physics up.**

## TL;DR — one-line install

```bash
curl -sSL https://raw.githubusercontent.com/mangumcfo/breathline-federation/main/installer/install.sh | bash
```

This is the same install regardless of your tier (executive, family, household). The installer detects your hardware and OS, asks you a few questions about your intended deployment, and gives you the right pre-built role pack.

> **Heads-up:** v0.1.0 ships a minimal scaffold installer. The full `install.sh` flow (cloning, venv setup, bootstrap, breath-gate, first cylinder seal) lands in v0.2.0. As of v0.1.0 the installer prints what it *will* do and clones the repo to `~/.breathline/`. Treat v0.1.0 as the first node of the federation that documents itself.

---

## What the installer does (target behavior — v0.2.0+)

1. **Platform detect** — Linux (apt/dnf), macOS (brew), Windows-WSL
2. **Tier detect** — based on hardware probe + a single yes/no question:
   - *Executive* — RTX-class GPU, business deployment, full P1–P5 stack
   - *Family* — kitchen-table mini-PC, household-tier hardware, lighter role pack
3. **Clone signed release** — `git clone --depth 1 --branch v0.X.Y https://github.com/mangumcfo/breathline-federation`
4. **Verify signatures** — checks every release artifact against keys in `distribution/signing_keys/`
5. **Set up venv** — `python3 -m venv ~/.breathline/.venv && pip install -r platform/pyproject.toml`
6. **Bootstrap layers** — runs `platform/scripts/bootstrap.py --full`:
   - Layer 0: seed manifest validation
   - Layer 1: kernel primitives (Spec / Constructor / Critic / Auditor / Governor)
   - Layer 2: platform layer (registry, audit adapter, receipt minter, plug-in interface)
   - Layer 3: role handlers (CFO / Synthesis / Compliance — tier-appropriate)
7. **Generate node identity** — ECC keys (P1), node ID, configuration profile
8. **Initial breath-gate** — first explicit human-primacy approval to seal node into the federation
9. **First cylinder + B49 receipt** — your sovereign node's birth certificate
10. **Print summary** — node ID, dashboard URL, next step on the Sovereign Ascension Ladder

---

## Upgrading

Once installed, upgrades are **manifest-driven** and **breath-gated**:

```bash
breathline upgrade
```

This:
1. Fetches the latest [`manifest.yaml`](./manifest.yaml)
2. Compares to your installed version
3. Shows you a diff: new specs, new platform code, breaking changes
4. Asks for **your breath** (the human-primacy gate)
5. On approval: runs schema migrations from `distribution/migrations/`, updates `platform/` and `specs/`, runs verification tests
6. Seals an upgrade cylinder + B49 receipt
7. Prints what changed and what to read next

You can `breathline upgrade --dry-run` to see the diff without applying.

---

## Checking your status

```bash
breathline status
```

Prints:
- Your installed version
- Your current ladder level (Awakening / Executive / Family / Generational Legacy / Federation)
- Roles deployed
- Pending recommendations (next book / next spec)
- Recent cylinder + receipt summary

---

## Uninstalling

```bash
~/.breathline/uninstall.sh
```

Removes the venv, role handlers, and configuration. **Cylinder chain and receipts are preserved by default** at `~/.breathline/cylinders/` — you can archive or delete them manually. Default-deny means uninstall does NOT touch your data without explicit confirmation.

---

## Manual install (without curl-bash)

If you don't want to pipe a script to bash:

```bash
git clone https://github.com/mangumcfo/breathline-federation.git ~/.breathline
cd ~/.breathline
./installer/install.sh
```

Same outcome.

---

## Tier-specific notes

### Executive tier

- Recommended hardware: RTX 4090/5090 or equivalent NVIDIA workstation
- All P1–P5 layers enabled
- Full role library: CFO, Synthesis, Compliance + add-ons per Series 1 books
- Suitable for fractional CFO consulting, family office operations, growth-stage businesses

### Family tier

- Recommended hardware: Mini-PC (NUC-class, 32+ GB RAM) or a dedicated household box
- P1–P5 layers enabled at lower compute intensity
- Pre-configured family role pack: `family_cfo_agent`, `household_synthesis_agent`, `family_compliance_shield`
- Voice-first breath-gate interface (clear explanations: *"This action needs your breath because it touches finances."*)
- Designed to outlast banks, governments, and Big Tech at kitchen-table scale

Both tiers run the same Breath 25 substrate. Sovereign from physics up.

---

## Verifying integrity

```bash
~/.breathline/installer/verify.sh
```

This:
- Verifies all installed file checksums against `manifest.yaml`
- Validates every loaded YAML against the constitutional kernel
- Replays your local cylinder chain end-to-end (no hash breaks, no freeform, no tracebacks)
- Reports any drift

Run this after any upgrade, or whenever you want assurance.

---

## Network requirements

- **First install / upgrade:** GitHub access (raw.githubusercontent.com) for the manifest + release artifacts
- **Steady state:** None. Your sovereign node runs **without internet by default.** Only when you explicitly opt in to federation discovery (P3 libp2p) does the node communicate with peers — and then only via resonant shard imprints + zk-proofs of alignment, never raw data.

---

## License + governance

This software is published under the **Constitutional Source-Available License v1.0** — see [LICENSE](./LICENSE). You can use, modify, and redistribute, but you **may not strip the constitutional kernel** (CHARTER + CONSTITUTION + breath-gated default-deny). Forks that violate constitutional invariants forfeit license.

For contribution rules: [CONTRIBUTING.md](./CONTRIBUTING.md).

---

∞Δ∞
