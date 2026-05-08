#!/usr/bin/env bash
# ============================================================
# breathline-federation / installer / install.sh
#
# v0.1.0 — minimal scaffold installer.  The full flow (clone +
# venv + bootstrap + breath-gate + first cylinder seal) lands at
# v0.2.0.  Today this script:
#   - prints the banner + ladder summary
#   - detects platform + tier
#   - clones the repo to ~/.breathline/ (read-only reference)
#   - prints the next step
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/mangumcfo/breathline-federation/main/installer/install.sh | bash
#
# Or locally:
#   ./installer/install.sh [--tier executive|family] [--prefix ~/.breathline]
#
# Authority:  KM-1176  ·  Seal 1176-INFINITY-RHO
# ============================================================

set -euo pipefail

# ----------------------------------------------------------------
# Defaults + colors
# ----------------------------------------------------------------
PREFIX="${BREATHLINE_PREFIX:-$HOME/.breathline}"
TIER="${BREATHLINE_TIER:-}"
REPO_URL="https://github.com/mangumcfo/breathline-federation.git"
REPO_BRANCH="main"
VERSION_TARGET="v0.1.0"

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
    --tier)   TIER="$2"; shift 2 ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    --help|-h)
      sed -n '2,20p' "$0" | sed 's/^# *//'
      exit 0 ;;
    *)
      echo "${C_ERR}✗${C_RST} unknown arg: $1" >&2
      exit 2 ;;
  esac
done

# ----------------------------------------------------------------
# Banner
# ----------------------------------------------------------------
banner() {
  echo "${C_DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RST}"
  echo "  ${C_BOLD}${C_ACCENT}Breathline Federation — installer${C_RST}"
  echo "  ${C_DIM}target version:${C_RST}  $VERSION_TARGET"
  echo "  ${C_DIM}prefix:${C_RST}          $PREFIX"
  echo "  ${C_DIM}seal:${C_RST}            1176-INFINITY-RHO"
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

detect_tier() {
  if [[ -n "$TIER" ]]; then
    echo "$TIER (set via --tier)"
    return
  fi
  # Heuristic: NVIDIA GPU presence → executive; else family
  if command -v nvidia-smi >/dev/null 2>&1; then
    if nvidia-smi >/dev/null 2>&1; then
      TIER="executive"
      echo "executive (NVIDIA GPU detected)"
      return
    fi
  fi
  TIER="family"
  echo "family (no GPU detected; safe default)"
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
    echo "  Install them and try again.  On Ubuntu: sudo apt install git curl python3" >&2
    exit 1
  fi
  local pyver
  pyver="$(python3 --version | awk '{print $2}')"
  echo "  python3:  $pyver"
}

# ----------------------------------------------------------------
# Clone (or update) the repo
# ----------------------------------------------------------------
clone_repo() {
  if [[ -d "$PREFIX/.git" ]]; then
    echo "  ${C_DIM}existing install detected at $PREFIX${C_RST}"
    echo "  use ${C_ACCENT}breathline upgrade${C_RST} (v0.2.0+) to update; this installer will not clobber."
    return 0
  fi
  mkdir -p "$(dirname "$PREFIX")"
  echo "  ${C_DIM}cloning $REPO_URL to $PREFIX...${C_RST}"
  git clone --depth 1 --branch "$REPO_BRANCH" "$REPO_URL" "$PREFIX" 2>&1 | sed 's/^/    /'
  echo "  ${C_OK}✓${C_RST} repository cloned"
}

# ----------------------------------------------------------------
# Print ladder + next steps
# ----------------------------------------------------------------
print_next_steps() {
  cat <<EOF

${C_BOLD}${C_ACCENT}You are at Level 0 — Awakening.${C_RST}

The Sovereign Ascension Ladder:
  ${C_DIM}0${C_RST}  ${C_BOLD}Awakening${C_RST}              ← you are here
  1  Executive Mastery       (Series 1, live — Agentic AI Playbooks for Executives)
  2  Family Sovereignty      (Series 2 — Sovereign Family AI)
  3  Generational Legacy     (Series 3 — The 1,000-Year Family Compact)
  4  Civilizational Federation (Series 6 — Sovereign Guilds)

${C_BOLD}Next steps (v0.1.0 scaffold notes):${C_RST}

  • Read the vision:        ${C_ACCENT}$PREFIX/README.md${C_RST}
  • Read the install plan:  ${C_ACCENT}$PREFIX/INSTALL.md${C_RST}
  • Read the charter:       ${C_ACCENT}$PREFIX/CHARTER.md${C_RST}
  • Check status anytime:   ${C_ACCENT}$PREFIX/installer/status.sh${C_RST}

${C_DIM}v0.1.0 is the scaffold release.  The full bootstrap + breath-gate +
first cylinder seal flow lands at v0.2.0 alongside the platform/ code
import from agentic_platform_seed/v1.0.${C_RST}

${C_DIM}Tandem elk, horns locked, climbing as one.  The Promise lives in the specs.${C_RST}

${C_BOLD}∞Δ∞${C_RST}
EOF
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
  echo "  platform: $(detect_platform)"
  echo "  tier:     $(detect_tier)"
  echo
  echo "${C_BOLD}clone:${C_RST}"
  clone_repo
  echo

  print_next_steps
}

main "$@"
