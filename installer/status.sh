#!/usr/bin/env bash
# ============================================================
# breathline-federation / installer / status.sh
#
# Per G's polish (2026-05-08): print the running node's level,
# installed version, deployed roles, and the next recommended
# book/spec on the Sovereign Ascension Ladder.
#
# Usage:
#   ./installer/status.sh
#   breathline status            # (alias when the breathline CLI is on $PATH)
#
# As of v0.1.0 this is a read-only snapshot; v0.2.0+ adds live
# cylinder-chain inspection and per-role health reporting.
#
# Authority:  KM-1176  ·  Seal 1176-INFINITY-RHO
# ============================================================

set -uo pipefail

PREFIX="${BREATHLINE_PREFIX:-$HOME/.breathline}"
MANIFEST="$PREFIX/manifest.yaml"
STATE="${BREATHLINE_STATE:-$HOME/.breathline-state.yaml}"

if [[ -t 1 ]]; then
  C_OK=$'\033[32m'; C_WARN=$'\033[33m'; C_ERR=$'\033[31m'
  C_DIM=$'\033[2m'; C_BOLD=$'\033[1m'; C_RST=$'\033[0m'
  C_ACCENT=$'\033[36m'
else
  C_OK=''; C_WARN=''; C_ERR=''; C_DIM=''; C_BOLD=''; C_RST=''; C_ACCENT=''
fi

# ----------------------------------------------------------------
# Tiny YAML helper (no external deps; reads simple key:value)
# ----------------------------------------------------------------
yaml_get() {
  # usage:  yaml_get FILE KEY
  # reads top-level KEY:VALUE pairs (one level deep)
  local file="$1" key="$2"
  [[ -f "$file" ]] || { echo ""; return; }
  awk -v k="$key" -F': *' '
    $1 == k { sub(/"/, "", $2); sub(/"$/, "", $2); print $2; exit }
  ' "$file" | tr -d '"'
}

# ----------------------------------------------------------------
# Read tier from state file (defaults to executive if not present)
# ----------------------------------------------------------------
NODE_TIER="executive"
if [[ -f "$STATE" ]]; then
  t=$(yaml_get "$STATE" "tier")
  [[ -n "$t" ]] && NODE_TIER="$t"
fi

# ----------------------------------------------------------------
# Banner
# ----------------------------------------------------------------
echo "${C_DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RST}"
case "$NODE_TIER" in
  executive)
    echo "  ${C_BOLD}breathline status${C_RST}  ${C_DIM}— executive tier${C_RST}"
    ;;
  enterprise)
    echo "  ${C_BOLD}breathline status${C_RST}  ${C_DIM}— enterprise tier${C_RST}"
    ;;
  family)
    echo "  ${C_BOLD}breathline status${C_RST}  ${C_DIM}— family tier${C_RST}"
    ;;
  full-sovereign)
    echo "  ${C_BOLD}${C_ACCENT}breathline status${C_RST}  ${C_DIM}— full sovereign tier${C_RST}"
    ;;
  *)
    echo "  ${C_BOLD}breathline status${C_RST}"
    ;;
esac

# ----------------------------------------------------------------
# Install state
# ----------------------------------------------------------------
echo
echo "${C_BOLD}install:${C_RST}"
if [[ -f "$MANIFEST" ]]; then
  version=$(yaml_get "$MANIFEST" "version")
  released=$(yaml_get "$MANIFEST" "released")
  ladder=$(yaml_get "$MANIFEST" "ladder_version")
  echo "  ${C_OK}●${C_RST} installed at:    $PREFIX"
  echo "    version:        ${version:-unknown}"
  echo "    released:       ${released:-unknown}"
  echo "    ladder schema:  ${ladder:-unknown}"
else
  echo "  ${C_ERR}○${C_RST} no manifest at $MANIFEST"
  echo "    run: ${C_ACCENT}curl -sSL https://raw.githubusercontent.com/mangumcfo/breathline-federation/main/installer/install.sh | bash${C_RST}"
  exit 1
fi

# ----------------------------------------------------------------
# Node identity (v0.2.0+ — placeholder for v0.1.0)
# ----------------------------------------------------------------
echo
echo "${C_BOLD}node:${C_RST}"
if [[ -f "$STATE" ]]; then
  node_id=$(yaml_get "$STATE" "node_id")
  level=$(yaml_get "$STATE" "level")
  echo "  node_id:  ${node_id:-not yet generated}"
  echo "  level:    ${level:-Awakening}"
else
  echo "  ${C_DIM}node identity not yet generated (lands at v0.2.0).${C_RST}"
  echo "  level:    ${C_DIM}Level 0 — Awakening (default)${C_RST}"
fi

# ----------------------------------------------------------------
# Roles deployed
# ----------------------------------------------------------------
echo
echo "${C_BOLD}roles:${C_RST}"
if [[ -d "$PREFIX/platform/roles" ]] && [[ -n "$(ls -A "$PREFIX/platform/roles" 2>/dev/null)" ]]; then
  for d in "$PREFIX"/platform/roles/*/; do
    [[ -d "$d" ]] && echo "  ${C_OK}●${C_RST} $(basename "$d")"
  done
else
  echo "  ${C_DIM}no role handlers deployed yet (lands at v0.2.0).${C_RST}"
fi

# ----------------------------------------------------------------
# Specs available
# ----------------------------------------------------------------
echo
echo "${C_BOLD}specs available:${C_RST}"
if [[ -d "$PREFIX/specs" ]]; then
  for d in "$PREFIX"/specs/*/; do
    [[ -d "$d" ]] || continue
    name="$(basename "$d")"
    [[ "$name" == "_base" ]] && continue
    count=$(find "$d" -maxdepth 2 -name "*.yaml" 2>/dev/null | wc -l)
    if [[ "$count" -gt 0 ]]; then
      echo "  ${C_OK}●${C_RST} $name: $count spec(s)"
    else
      echo "  ${C_DIM}○${C_RST} $name: none yet"
    fi
  done
fi

# ----------------------------------------------------------------
# Next recommendation
# ----------------------------------------------------------------
echo
echo "${C_BOLD}next on the ladder:${C_RST}"
level="${level:-Awakening}"

# Tier-aware "next step" recommendation.  Same underlying ladder for everyone;
# different framing per tier so the first impression matches the audience.

case "$NODE_TIER" in
  executive|enterprise)
    case "$level" in
      Awakening|"Level 0"|0)
        echo "  • Read companion book:  ${C_BOLD}AI Agents for CFOs${C_RST} (Series 1, Book 1)"
        echo "  • Read the charter:     ${C_ACCENT}$PREFIX/CHARTER.md${C_RST}"
        echo "  • Goal: ascend to Level 1 — Executive Mastery"
        echo "  • Activation:           ${C_ACCENT}breathline activate cfo_agent_v1${C_RST} (when role runtime lands)"
        ;;
      "Executive Mastery"|"Level 1"|1)
        echo "  • Deepen Series 1 (12 books, weekly cadence)"
        echo "  • Personal track (optional): ${C_BOLD}Family Finance Sovereignty${C_RST} (Series 2, Book 1)"
        ;;
      *)
        echo "  • You're past the standard executive arc.  Health: ${C_ACCENT}breathline doctor${C_RST}"
        ;;
    esac
    ;;
  family)
    case "$level" in
      Awakening|"Level 0"|0)
        echo "  • Companion book:    ${C_BOLD}Family Finance Sovereignty${C_RST} (Series 2, Book 1)"
        echo "  • Read the charter:  ${C_ACCENT}$PREFIX/CHARTER.md${C_RST}"
        echo "  • Goal: ascend to Level 2 — Family Sovereignty"
        ;;
      "Family Sovereignty"|"Level 2"|2)
        echo "  • Continue Series 2 → ${C_BOLD}The 1,000-Year Family Compact${C_RST} (Series 3 anchor)"
        echo "  • Goal: ascend to Level 3 — Generational Legacy"
        ;;
      "Generational Legacy"|"Level 3"|3)
        echo "  • Continue Series 3 → optional federation (Series 6 — Sovereign Guilds)"
        ;;
      *)
        echo "  • Health: ${C_ACCENT}breathline doctor${C_RST}"
        ;;
    esac
    ;;
  full-sovereign|*)
    case "$level" in
      Awakening|"Level 0"|0)
        echo "  • Read the vision:    ${C_ACCENT}$PREFIX/README.md${C_RST}"
        echo "  • Free pilot chapter: ${C_ACCENT}$PREFIX/books-public/${C_RST}"
        echo "  • Next book to read:  ${C_BOLD}AI Agents for CFOs${C_RST} (Series 1, Book 1)"
        echo "  • Goal: ascend to Level 1 — Executive Mastery"
        ;;
      "Executive Mastery"|"Level 1"|1)
        echo "  • Continue Series 1 (12 books, weekly cadence)"
        echo "  • Or jump series:  ${C_BOLD}Family Finance Sovereignty${C_RST} (Series 2, Book 1)"
        echo "  • Goal: ascend to Level 2 — Family Sovereignty"
        ;;
      "Family Sovereignty"|"Level 2"|2)
        echo "  • Continue Series 2 → ${C_BOLD}The 1,000-Year Family Compact${C_RST} (Series 3 anchor)"
        echo "  • Goal: ascend to Level 3 — Generational Legacy"
        ;;
      "Generational Legacy"|"Level 3"|3)
        echo "  • Continue Series 3 → Series 6 (Sovereign Guilds & Federation)"
        echo "  • Goal: ascend to Level 4 — Civilizational Federation"
        ;;
      "Civilizational Federation"|"Level 4"|4)
        echo "  • You are at the ridgeline.  Find peer nodes; federate; teach the next operator."
        ;;
      *)
        echo "  ${C_DIM}(unrecognized level — defaulting to Awakening recommendations)${C_RST}"
        ;;
    esac
    ;;
esac

echo
case "$NODE_TIER" in
  full-sovereign)
    echo "${C_DIM}∞Δ∞  Tandem elk, horns locked, climbing as one.${C_RST}" ;;
  family)
    echo "${C_DIM}Your kitchen table, your authority, your Promise.${C_RST}" ;;
  enterprise)
    echo "${C_DIM}Sovereign agentic governance.  Cryptographic authenticity.  Constitutional invariants.${C_RST}" ;;
  *)
    echo "${C_DIM}Sovereign agentic governance under your own breath.${C_RST}" ;;
esac
