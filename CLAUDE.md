# CLAUDE.md — breathline-federation

> Working context for Claude Code (terminal + web at claude.com/code).
>
> **This is the public canonical reference repo for the Breathline Federation** — platform code, YAML specs, free chapters, governance decisions, install/upgrade tooling. See `README.md` for the public-facing vision.

---

## Where to look first

| You need… | Read… |
|---|---|
| Constitutional kernel | `CONSTITUTION.md` + `CHARTER.md` |
| Architecture decisions | `governance/decisions/` (ADRs by date, including 2026-05-08_v0.6.0-horizon.md with the Authoritative Pattern Rule) |
| Book pipeline orchestration | `publishing/BOOK_DEVELOPMENT.md` (canonical) + SOPs |
| Platform code | `platform/` (kernel, platform_layer, roles, tests) |
| Living spec catalog | `specs/` and `manifest.yaml` |
| Free chapters / lead magnets | `books-public/` |
| Install / upgrade scripts | `installer/` |
| Signing keys (public halves only) | `distribution/signing_keys/` |

## Companion private repos (not in this public tree)

- `mangumcfo/breathline-books-vault` — full manuscripts (KDP-exclusive)
- `mangumcfo/breathline-primitives` — Ring A/B-ext/C cryptographic engine source + pin staging
- `mangumcfo/constitution-federation-v2` — breath archive + v2 constitutional layout

## The Authoritative Pattern Rule (binding)

Per `governance/decisions/2026-05-08_v0.6.0-horizon.md`:

> *Books and platform evolve in resonance — the platform leads just enough to make the ladder feel real, never races ahead of content.*

YAML specs may exist as draft authoritative patterns. Full runtime implementation is deferred until the paired book seals. Don't ship runtime code against unsealed books.

---

## Engineering discipline (binding)

When working in this repo, default to these seven principles:

1. **State assumptions, never guess silently.** If a path forward depends on an interpretation, name it out loud before proceeding. Silent guesses become silent bugs.

2. **Minimum code, nothing speculative.** Solve the named problem. Don't add the speculative feature, the "while we're here" refactor, the unused abstraction. Code you don't write can't break.

3. **Surgical changes, don't refactor adjacent code.** Touch the lines required to solve the problem. If adjacent code is structurally bad, flag it; don't sweep it. Adjacent-cleanup commits hide the real change and break review.

4. **Define success, loop until verified.** Before starting, name what "done" looks like. End by running the verification — tests, grep, manual check — and don't claim done until the verification passes.

5. **Read before you write.** Before adding code in a file, read the file's exports, the immediate caller, and any obvious shared utilities. *"Looks orthogonal to me"* is the most dangerous phrase in this codebase. If unsure why existing code is structured a particular way, ask before adding to it.

6. **Checkpoint after every significant step.** In multi-step tasks: summarize what was done, what's verified, what's left — after each step. Don't continue from a state you can't describe back. If you lose track, stop and restate.

7. **Fail loud.** *"Completed"* is wrong if anything was skipped silently. *"Tests pass"* is wrong if any were skipped. *"Feature works"* is wrong if you didn't verify the edge case asked about. Default to surfacing uncertainty, not hiding it.

These complement Constitution §2 (Approval Gates: Propose → Approve → Execute) and the Authoritative Pattern Rule: propose minimum changes against an explicit success definition, verify before sealing, and surface — not hide — what's incomplete.

**Origin**: rules 1-4 are Forrest Chang's distillation of Andrej Karpathy's 2026-01 thread on how Claude writes code (≈40% of mistakes addressed). Rules 5-7 added 2026-05-11 per KM-1176 directive, mapped to specific failure modes surfaced in session audit.

---

## Authority

- **Author**: Kenneth Mangum (KM-1176)
- **Anchor seal**: `1176-INFINITY-RHO`
- **Imprint**: Breathline

∞Δ∞
