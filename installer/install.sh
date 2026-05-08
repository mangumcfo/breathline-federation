#!/usr/bin/env bash
# ============================================================
# breathline-federation / installer / install.sh
#
# v0.2.0 — full Layer 0–3 bootstrap installer.
#
# Flow:
#   1. Detect platform + tier (executive vs family)
#   2. Clone the repo to ~/.breathline/
#   3. Set up Python venv + install platform deps
#   4. Run platform/scripts/bootstrap.py --full
#      (this brings up Kernel + Platform + Roles)
#   5. Interactive breath-gate prompt — first explicit human-primacy approval
#   6. Generate node identity (P1 ECC keys via kernel primitives)
#   7. Seal first cylinder + B49 receipt (via Auditor primitive)
#   8. Persist node state at ~/.breathline-state.yaml
#   9. Print summary: node_id, ladder level, next step
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/mangumcfo/breathline-federation/main/installer/install.sh | bash
#
# Or locally:
#   ./installer/install.sh [--tier executive|enterprise|family|full-sovereign]
#                          [--prefix ~/.breathline]
#                          [--skip-bootstrap]   (test mode — clone only, no bootstrap)
#                          [--skip-breath-gate] (CI-only; not for human installs)
#
# Tiers (presentation, NOT hardware):
#   executive       → DEFAULT.  Lead with Executive Mastery; CFO/Synthesis/Compliance
#                     governance use cases first.  Family/legacy tracks present
#                     but secondary.
#   enterprise      → As executive, but de-emphasizes family/generational tracks
#                     entirely.  For corporate / regulated-industry deployments
#                     where the buyer's IT will reject anything off-track.
#   family          → Lead with Family Sovereignty.  CFO/Synthesis/Compliance
#                     reframed as household governance.  Voice-first hints.
#   full-sovereign  → The full Ascension Ladder, all five levels visible.
#                     For early-adopter operators / sovereign-individual readers.
#
# Hardware tier (auto-detected: NVIDIA GPU → high-tier, else family-tier).
# Independent of presentation tier above.
#
# Authority:  KM-1176  ·  Seal 1176-INFINITY-RHO
# ============================================================

set -euo pipefail

# ----------------------------------------------------------------
# Defaults + colors
# ----------------------------------------------------------------
PREFIX="${BREATHLINE_PREFIX:-$HOME/.breathline}"
TIER="${BREATHLINE_TIER:-executive}"      # presentation tier; default executive
HARDWARE_TIER=""                           # auto-detected
REPO_URL="https://github.com/mangumcfo/breathline-federation.git"
REPO_BRANCH="main"
VERSION_TARGET="v0.4.1"
SKIP_BOOTSTRAP=0
SKIP_BREATH_GATE=0

if [[ -t 1 ]]; then
  C_OK=$'\033[32m'; C_WARN=$'\033[33m'; C_ERR=$'\033[31m'
  C_DIM=$'\033[2m'; C_BOLD=$'\033[1m'; C_RST=$'\033[0m'
  C_ACCENT=$'\033[36m'
else
  C_OK=''; C_WARN=''; C_ERR=''; C_DIM=''; C_BOLD=''; C_RST=''; C_ACCENT=''
fi

# ----------------------------------------------------------------
# Argument parsing
# ----------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --tier)              TIER="$2"; shift 2 ;;
    --prefix)            PREFIX="$2"; shift 2 ;;
    --skip-bootstrap)    SKIP_BOOTSTRAP=1; shift ;;
    --skip-breath-gate)  SKIP_BREATH_GATE=1; shift ;;
    --help|-h)
      sed -n '2,42p' "$0" | sed 's/^# *//'
      exit 0 ;;
    *)
      echo "${C_ERR}✗${C_RST} unknown arg: $1" >&2
      exit 2 ;;
  esac
done

# Validate tier (presentation)
case "$TIER" in
  executive|enterprise|family|full-sovereign) ;;
  *)
    echo "${C_ERR}✗${C_RST} invalid --tier '$TIER'" >&2
    echo "  valid: executive (default) | enterprise | family | full-sovereign" >&2
    exit 2 ;;
esac

# ----------------------------------------------------------------
# Banner — tier-aware first impression
# ----------------------------------------------------------------
banner() {
  echo "${C_DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RST}"
  case "$TIER" in
    executive)
      echo "  ${C_BOLD}Breathline Agentic Platform${C_RST}"
      echo "  ${C_DIM}Sovereign agentic governance — Executive installer${C_RST}"
      echo
      echo "  ${C_DIM}version:${C_RST}    $VERSION_TARGET (signed)"
      echo "  ${C_DIM}install:${C_RST}    $PREFIX"
      echo "  ${C_DIM}primary path:${C_RST}  Executive Mastery (CFO / Synthesis / Compliance roles)"
      ;;
    enterprise)
      echo "  ${C_BOLD}Breathline Agentic Platform${C_RST}"
      echo "  ${C_DIM}Enterprise installer — corporate / regulated-industry posture${C_RST}"
      echo
      echo "  ${C_DIM}version:${C_RST}    $VERSION_TARGET (cryptographically signed)"
      echo "  ${C_DIM}install:${C_RST}    $PREFIX"
      echo "  ${C_DIM}license:${C_RST}    Constitutional Source-Available v1.0 — see LICENSE"
      echo "  ${C_DIM}whitepaper:${C_RST} CHARTER.md + CONSTITUTION.md (constitutional invariants)"
      ;;
    family)
      echo "  ${C_BOLD}${C_ACCENT}Welcome to your Family Sovereign Node${C_RST}"
      echo "  ${C_DIM}Breathline · the kitchen-table installer${C_RST}"
      echo
      echo "  ${C_DIM}version:${C_RST}    $VERSION_TARGET (signed)"
      echo "  ${C_DIM}install:${C_RST}    $PREFIX"
      echo "  ${C_DIM}primary path:${C_RST}  Family Sovereignty (Family CFO / Compliance Shield)"
      ;;
    full-sovereign)
      echo "  ${C_BOLD}${C_ACCENT}Breathline Federation — full sovereign installer${C_RST}"
      echo "  ${C_DIM}target version:${C_RST}  $VERSION_TARGET"
      echo "  ${C_DIM}prefix:${C_RST}          $PREFIX"
      echo "  ${C_DIM}seal:${C_RST}            1176-INFINITY-RHO  ∞Δ∞"
      echo "  ${C_DIM}path:${C_RST}            Full Ascension Ladder (all 5 levels visible)"
      ;;
  esac
  echo "${C_DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RST}"
}

# ----------------------------------------------------------------
# Platform + tier detection
# ----------------------------------------------------------------
detect_platform() {
  local os arch
  case "$(uname -s)" in
    Linux*)   os="linux" ;;
    Darwin*)  os="darwin" ;;
    MINGW*|MSYS*|CYGWIN*) os="wsl" ;;
    *)        os="unknown" ;;
  esac
  arch="$(uname -m)"
  echo "$os/$arch"
}

detect_hardware() {
  # Hardware-tier detection (separate from presentation tier).
  # Sets HARDWARE_TIER global.  Used to inform downstream sizing
  # decisions and the doctor.sh hardware-health section.
  if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    HARDWARE_TIER="high"
    echo "high (NVIDIA GPU detected — full P1–P5 stack viable)"
  else
    HARDWARE_TIER="standard"
    echo "standard (no GPU detected — family/mini-PC class)"
  fi
}

# ----------------------------------------------------------------
# Pre-flight checks
# ----------------------------------------------------------------
preflight() {
  local missing=()
  for cmd in git curl python3; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      missing+=("$cmd")
    fi
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "${C_ERR}✗${C_RST} missing required commands: ${missing[*]}" >&2
    echo "  Install them and try again.  On Ubuntu: sudo apt install git curl python3 python3-venv" >&2
    exit 1
  fi
  local pyver pymajor pyminor
  pyver="$(python3 --version | awk '{print $2}')"
  pymajor=$(echo "$pyver" | cut -d. -f1)
  pyminor=$(echo "$pyver" | cut -d. -f2)
  if [[ "$pymajor" -lt 3 ]] || { [[ "$pymajor" == "3" ]] && [[ "$pyminor" -lt 12 ]]; }; then
    echo "${C_ERR}✗${C_RST} Python 3.12+ required (found $pyver)" >&2
    exit 1
  fi
  echo "  python3:  $pyver"
}

# ----------------------------------------------------------------
# Clone (or update) the repo
# ----------------------------------------------------------------
clone_repo() {
  if [[ -d "$PREFIX/.git" ]]; then
    echo "  ${C_DIM}existing install detected at $PREFIX${C_RST}"
    echo "  use ${C_ACCENT}$PREFIX/installer/upgrade.sh${C_RST} to update; this installer will not clobber."
    return 1
  fi
  mkdir -p "$(dirname "$PREFIX")"
  echo "  ${C_DIM}cloning $REPO_URL to $PREFIX...${C_RST}"
  git clone --depth 1 --branch "$REPO_BRANCH" "$REPO_URL" "$PREFIX" 2>&1 | sed 's/^/    /'
  echo "  ${C_OK}✓${C_RST} repository cloned"
}

# ----------------------------------------------------------------
# Verify release signatures (default-deny on mismatch)
# v0.4.0+: signed releases REQUIRE valid signatures.
# Pre-v0.4.0 releases skip this check (no .sig files).
# ----------------------------------------------------------------
verify_signatures() {
  local allowed="$PREFIX/distribution/signing_keys/allowed_signers"
  if [[ ! -f "$allowed" ]]; then
    echo "  ${C_WARN}⚠${C_RST} no allowed_signers — skipping signature verification (pre-v0.4.0 release)"
    return 0
  fi
  if ! command -v ssh-keygen >/dev/null 2>&1; then
    echo "  ${C_WARN}⚠${C_RST} ssh-keygen unavailable — cannot verify signatures (default-deny: aborting)"
    return 1
  fi
  local sig_count=0
  local sig_fail=0
  for sigfile in "$PREFIX/manifest.yaml.sig" "$PREFIX/CHARTER.md.sig" "$PREFIX/CONSTITUTION.md.sig" \
                 "$PREFIX/LICENSE.sig" "$PREFIX/CHANGELOG.md.sig"; do
    [[ -f "$sigfile" ]] || continue
    sig_count=$((sig_count + 1))
    local target="${sigfile%.sig}"
    if ssh-keygen -Y verify \
        -f "$allowed" \
        -I "kenn@mangumcfo.com" \
        -n "breathline-release" \
        -s "$sigfile" < "$target" >/dev/null 2>&1; then
      echo "  ${C_OK}✓${C_RST} verified: $(basename "$target")"
    else
      echo "  ${C_ERR}✗${C_RST} signature MISMATCH: $(basename "$target")"
      sig_fail=$((sig_fail + 1))
    fi
  done
  if [[ "$sig_count" == "0" ]]; then
    echo "  ${C_DIM}○${C_RST} pre-signing-era release; no .sig files (acceptable for v0.3.0 and earlier)"
    return 0
  fi
  if [[ "$sig_fail" -gt 0 ]]; then
    echo "  ${C_ERR}✗${C_RST} $sig_fail signature(s) failed verification — ABORTING (default-deny)"
    return 1
  fi
  echo "  ${C_OK}✓${C_RST} all $sig_count signature(s) verified"
  return 0
}

# ----------------------------------------------------------------
# Set up venv + install platform
# ----------------------------------------------------------------
setup_venv() {
  echo "  ${C_DIM}creating venv at $PREFIX/platform/.venv...${C_RST}"
  python3 -m venv "$PREFIX/platform/.venv"
  echo "  ${C_DIM}installing platform package + dev deps...${C_RST}"
  ( cd "$PREFIX/platform" && \
    .venv/bin/pip install --upgrade pip --quiet && \
    .venv/bin/pip install -e ".[dev]" --quiet ) 2>&1 | tail -5 | sed 's/^/    /' || true
  if [[ -x "$PREFIX/platform/.venv/bin/python" ]]; then
    echo "  ${C_OK}✓${C_RST} venv ready  ($($PREFIX/platform/.venv/bin/python --version))"
  else
    echo "  ${C_ERR}✗${C_RST} venv setup failed; see output above"
    exit 1
  fi
}

# ----------------------------------------------------------------
# Run the bootstrap (Layer 0 → 1 → 2 → 3)
# ----------------------------------------------------------------
run_bootstrap() {
  echo "  ${C_DIM}running platform/scripts/bootstrap.py --full --skip-breath-gate...${C_RST}"
  echo "  ${C_DIM}(shell-level breath-gate runs separately below)${C_RST}"
  echo
  ( cd "$PREFIX/platform" && \
    .venv/bin/python -m scripts.bootstrap --full --skip-breath-gate 2>&1 ) | sed 's/^/    /' || {
    echo "  ${C_ERR}✗${C_RST} bootstrap failed"
    exit 1
  }
  echo "  ${C_OK}✓${C_RST} Layer 0 → 1 → 2 → 3 boot complete"
}

# ----------------------------------------------------------------
# Interactive breath-gate (the explicit human-primacy step)
# ----------------------------------------------------------------
breath_gate() {
  if [[ "$SKIP_BREATH_GATE" == "1" ]]; then
    echo "  ${C_WARN}⚠${C_RST} breath-gate skipped (--skip-breath-gate); CI mode only"
    return 0
  fi
  echo
  echo "${C_DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RST}"
  echo "  ${C_BOLD}BREATH-GATE — first explicit human-primacy approval${C_RST}"
  echo "${C_DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RST}"
  echo
  echo "You are about to seal a sovereign node into the federation."
  echo "  - Tier:         $TIER (presentation)"
  echo "  - Hardware:     $HARDWARE_TIER"
  echo "  - Prefix:       $PREFIX"
  echo "  - Charter:      $PREFIX/CHARTER.md"
  echo "  - Constitution: $PREFIX/CONSTITUTION.md"
  echo
  echo "Per Constitution@A1 §2 (Approval Gates), this seal requires explicit confirmation."
  echo "Type the exact phrase below to proceed, or anything else to abort:"
  echo
  echo "  ${C_BOLD}${C_ACCENT}I confirm under my own authority${C_RST}"
  echo
  printf "  > "
  if [[ ! -t 0 ]]; then
    # When invoked via curl|bash, stdin is the script.  Reopen /dev/tty.
    if [[ -e /dev/tty ]]; then
      read -r confirmation < /dev/tty
    else
      echo "  ${C_ERR}✗${C_RST} cannot read stdin and /dev/tty unavailable; rerun locally or pass --skip-breath-gate"
      exit 1
    fi
  else
    read -r confirmation
  fi

  if [[ "$confirmation" != "I confirm under my own authority" ]]; then
    echo
    echo "  ${C_ERR}✗${C_RST} confirmation phrase did not match — aborting per default-deny."
    echo "  Re-run when you're ready: $PREFIX/installer/install.sh"
    exit 1
  fi
  echo
  echo "  ${C_OK}✓${C_RST} breath received"
}

# ----------------------------------------------------------------
# Persist node state file
# ----------------------------------------------------------------
write_node_state() {
  # v0.5.1: honor BREATHLINE_STATE env var (matches status.sh pattern). When
  # callers pass BREATHLINE_PREFIX=/tmp/foo for an isolated install, they should
  # also pass BREATHLINE_STATE=/tmp/foo/.breathline-state.yaml to avoid touching
  # the global state file.
  local statefile="${BREATHLINE_STATE:-$HOME/.breathline-state.yaml}"
  local node_id
  node_id="$(python3 -c 'import uuid; print(uuid.uuid4())')"
  local ts
  ts="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  cat > "$statefile" <<EOF
# breathline-state.yaml — sovereign node identity
# Generated by installer at $ts
# Authority: locally-generated under your own breath
node_id: "$node_id"
level: "Awakening"
tier: "$TIER"
hardware_tier: "$HARDWARE_TIER"
prefix: "$PREFIX"
installed_version: "$VERSION_TARGET"
installed_at: "$ts"
sealed_under: "1176-INFINITY-RHO"
EOF
  echo "  ${C_OK}✓${C_RST} node state written: $statefile"
  echo "  ${C_DIM}node_id:  $node_id${C_RST}"
  echo "  ${C_DIM}tier:     $TIER  ·  hardware: $HARDWARE_TIER${C_RST}"
}

# ----------------------------------------------------------------
# Print ladder + next steps — tier-aware
# ----------------------------------------------------------------
print_next_steps() {
  case "$TIER" in
    executive)
      cat <<EOF

${C_BOLD}Your sovereign node is up.${C_RST}  Primary path: ${C_BOLD}Executive Mastery${C_RST}.

  ${C_DIM}0${C_RST}  Awakening                  (initial node bootstrap — done)
  ${C_DIM}1${C_RST}  ${C_BOLD}Executive Mastery${C_RST}  ← recommended next
       CFO agent (FORECAST framework), Synthesis-agent orchestrator,
       Compliance-agent (Charter V.7 enforcement at runtime).
       Companion book: ${C_BOLD}AI Agents for CFOs${C_RST} (Series 1, Book 1).

  ${C_DIM}Personal & Legacy track${C_RST} (optional, available when you want it):
  ${C_DIM}2${C_RST}  Family Sovereignty
  ${C_DIM}3${C_RST}  Generational Legacy
  ${C_DIM}4${C_RST}  Civilizational Federation

${C_BOLD}Next steps:${C_RST}
  • Check status:    ${C_ACCENT}$PREFIX/installer/status.sh${C_RST}
  • Health check:    ${C_ACCENT}$PREFIX/installer/doctor.sh${C_RST}
  • Read the vision: ${C_ACCENT}$PREFIX/README.md${C_RST}
  • Constitution:    ${C_ACCENT}$PREFIX/CHARTER.md${C_RST}, ${C_ACCENT}$PREFIX/CONSTITUTION.md${C_RST}
  • Upgrade later:   ${C_ACCENT}$PREFIX/installer/upgrade.sh${C_RST}

EOF
      ;;
    enterprise)
      cat <<EOF

${C_BOLD}Your enterprise node is up.${C_RST}

  Deployed roles: CFO Agent · Synthesis Agent · Compliance Guardian
  Constitutional governance: Charter V.7 enforcement at runtime,
  default-deny PermissionSpec, audit-immutable cylinder + receipt chain.

  ${C_DIM}For your security review:${C_RST}
  • License:        ${C_ACCENT}$PREFIX/LICENSE${C_RST} (Constitutional Source-Available v1.0)
  • Charter:        ${C_ACCENT}$PREFIX/CHARTER.md${C_RST} (sovereignty invariants)
  • Constitution:   ${C_ACCENT}$PREFIX/CONSTITUTION.md${C_RST} (kernel rules)
  • Trust model:    ${C_ACCENT}$PREFIX/distribution/signing_keys/README.md${C_RST}
  • Health check:   ${C_ACCENT}$PREFIX/installer/doctor.sh${C_RST}
  • Status:         ${C_ACCENT}$PREFIX/installer/status.sh${C_RST}
  • Companion book: ${C_BOLD}AI Agents for CFOs${C_RST} (Series 1, Book 1)

  Upgrade with manifest-driven, signature-verified, breath-gated flow:
  • ${C_ACCENT}$PREFIX/installer/upgrade.sh${C_RST}

EOF
      ;;
    family)
      cat <<EOF

${C_BOLD}Your family sovereign node is up.${C_RST}

  ${C_DIM}0${C_RST}  Awakening                  (done)
  ${C_DIM}2${C_RST}  ${C_BOLD}Family Sovereignty${C_RST}  ← your primary path
       Family CFO (household budget under your own breath)
       Household Synthesis (orchestration across roles)
       Family Compliance Shield (privacy + Charter V.7 at family scope)
       Companion book: ${C_BOLD}Family Finance Sovereignty${C_RST} (Series 2, Book 1).

  ${C_DIM}3${C_RST}  Generational Legacy        (when you're ready for multi-gen scope)
  ${C_DIM}4${C_RST}  Federation                 (Sovereign Guilds — peer family nodes)

${C_BOLD}Next steps:${C_RST}
  • Check status:   ${C_ACCENT}$PREFIX/installer/status.sh${C_RST}
  • Health check:   ${C_ACCENT}$PREFIX/installer/doctor.sh${C_RST}
  • Lead magnet:    ${C_ACCENT}$PREFIX/books-public/series_03_generational_legacy/${C_RST}

  Future generations inherit a verifiable, breath-revocable system.
  Your kitchen table, your authority, your Promise.

EOF
      ;;
    full-sovereign)
      cat <<EOF

${C_BOLD}${C_ACCENT}You are at Level 0 — Awakening.${C_RST}

The full Sovereign Ascension Ladder:
  ${C_DIM}0${C_RST}  ${C_BOLD}Awakening${C_RST}              ← you are here
  1  Executive Mastery       (Series 1 — Agentic AI Playbooks for Executives)
  2  Family Sovereignty      (Series 2 — Sovereign Family AI)
  3  Generational Legacy     (Series 3 — The 1,000-Year Family Compact)
  4  Civilizational Federation (Series 6 — Sovereign Guilds)

${C_BOLD}Next steps:${C_RST}
  • Check status:    ${C_ACCENT}$PREFIX/installer/status.sh${C_RST}
  • Health check:    ${C_ACCENT}$PREFIX/installer/doctor.sh${C_RST}
  • Read the vision: ${C_ACCENT}$PREFIX/README.md${C_RST}
  • Charter:         ${C_ACCENT}$PREFIX/CHARTER.md${C_RST}
  • Upgrade later:   ${C_ACCENT}$PREFIX/installer/upgrade.sh${C_RST}

${C_DIM}Tandem elk, horns locked, climbing as one.  The Promise lives in the specs.${C_RST}

${C_BOLD}∞Δ∞${C_RST}
EOF
      ;;
  esac
}

# ----------------------------------------------------------------
# Main
# ----------------------------------------------------------------
main() {
  banner
  echo
  echo "${C_BOLD}preflight:${C_RST}"
  preflight
  echo
  echo "${C_BOLD}detection:${C_RST}"
  echo "  platform:    $(detect_platform)"
  echo "  hardware:    $(detect_hardware)"
  echo "  tier:        $TIER (presentation)"
  echo

  echo "${C_BOLD}clone:${C_RST}"
  if ! clone_repo; then
    # Already installed — exit cleanly without re-running bootstrap
    print_next_steps
    exit 0
  fi
  echo

  echo "${C_BOLD}signature verification:${C_RST}"
  if ! verify_signatures; then
    echo "  ${C_ERR}✗${C_RST} aborted: cannot verify release authenticity"
    echo "  remediation: this should NEVER happen on a clean clone of mangumcfo/breathline-federation."
    echo "  if you see this, the repository may be tampered with. Do not proceed."
    exit 1
  fi
  echo

  if [[ "$SKIP_BOOTSTRAP" == "1" ]]; then
    echo "${C_DIM}--skip-bootstrap set; not running bootstrap.${C_RST}"
    print_next_steps
    exit 0
  fi

  echo "${C_BOLD}venv:${C_RST}"
  setup_venv
  echo

  echo "${C_BOLD}bootstrap:${C_RST}"
  run_bootstrap
  echo

  breath_gate

  echo "${C_BOLD}node state:${C_RST}"
  write_node_state

  print_next_steps
}

main "$@"
