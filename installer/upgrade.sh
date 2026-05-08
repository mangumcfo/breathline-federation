#!/usr/bin/env bash
# ============================================================
# breathline-federation / installer / upgrade.sh
#
# Upgrade an installed Breathline node to the latest manifest.
#
# Flow:
#   1. Read installed version from local manifest.yaml
#   2. Fetch upstream manifest.yaml from origin/main
#   3. Diff: show what's new (specs added/changed, platform code changes)
#   4. Breath-gate the operator (explicit confirmation phrase)
#   5. git pull --ff-only origin main
#   6. Run any migrations from distribution/migrations/<from>_to_<to>.py
#   7. Rebuild venv + reinstall platform
#   8. Run platform tests to verify integrity
#   9. Update node state file
#  10. Print what changed + next ladder step
#
# Usage:
#   ./installer/upgrade.sh                 # full upgrade with breath-gate
#   ./installer/upgrade.sh --dry-run       # diff only; no changes
#   ./installer/upgrade.sh --skip-breath-gate  # CI mode only
#
# Authority:  KM-1176  ·  Seal 1176-INFINITY-RHO
# ============================================================

set -euo pipefail

PREFIX="${BREATHLINE_PREFIX:-$HOME/.breathline}"
DRY_RUN=0
SKIP_BREATH_GATE=0

if [[ -t 1 ]]; then
  C_OK=$'\033[32m'; C_WARN=$'\033[33m'; C_ERR=$'\033[31m'
  C_DIM=$'\033[2m'; C_BOLD=$'\033[1m'; C_RST=$'\033[0m'
  C_ACCENT=$'\033[36m'
else
  C_OK=''; C_WARN=''; C_ERR=''; C_DIM=''; C_BOLD=''; C_RST=''; C_ACCENT=''
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)            DRY_RUN=1; shift ;;
    --skip-breath-gate)   SKIP_BREATH_GATE=1; shift ;;
    --help|-h)
      sed -n '2,25p' "$0" | sed 's/^# *//'
      exit 0 ;;
    *)
      echo "${C_ERR}✗${C_RST} unknown arg: $1" >&2
      exit 2 ;;
  esac
done

yaml_get() {
  local file="$1" key="$2"
  [[ -f "$file" ]] || { echo ""; return; }
  awk -v k="$key" -F': *' '$1 == k { sub(/"/, "", $2); sub(/"$/, "", $2); print $2; exit }' "$file" | tr -d '"'
}

if [[ ! -d "$PREFIX/.git" ]]; then
  echo "${C_ERR}✗${C_RST} no Breathline install at $PREFIX"
  echo "  install first:"
  echo "  curl -sSL https://raw.githubusercontent.com/mangumcfo/breathline-federation/main/installer/install.sh | bash"
  exit 1
fi

echo "${C_DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RST}"
echo "  ${C_BOLD}${C_ACCENT}Breathline upgrade${C_RST}"
echo "  ${C_DIM}prefix:${C_RST}  $PREFIX"
echo "${C_DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RST}"

echo
echo "${C_BOLD}installed version:${C_RST}"
INSTALLED=$(yaml_get "$PREFIX/manifest.yaml" "version")
echo "  $INSTALLED"

echo
echo "${C_BOLD}fetching upstream manifest...${C_RST}"
( cd "$PREFIX" && git fetch --quiet origin main )
git -C "$PREFIX" show origin/main:manifest.yaml > /tmp/breathline-upstream-manifest.yaml 2>&1 || {
  echo "${C_ERR}✗${C_RST} failed to fetch upstream manifest"
  exit 1
}
UPSTREAM=$(yaml_get /tmp/breathline-upstream-manifest.yaml "version")
echo "  upstream version: $UPSTREAM"

echo
if [[ "$INSTALLED" == "$UPSTREAM" ]]; then
  echo "  ${C_OK}● already at the latest version${C_RST}  ($INSTALLED)"
  echo "  Nothing to do.  ${C_DIM}breathline status${C_RST} for the full picture."
  rm -f /tmp/breathline-upstream-manifest.yaml
  exit 0
fi

echo "${C_BOLD}upgrade available:${C_RST}  ${C_DIM}$INSTALLED${C_RST}  →  ${C_ACCENT}$UPSTREAM${C_RST}"
echo

echo "${C_BOLD}commits since installed version:${C_RST}"
git -C "$PREFIX" log --oneline "HEAD..origin/main" 2>&1 | head -20 | sed 's/^/  /'
echo
echo "${C_BOLD}files changed:${C_RST}"
git -C "$PREFIX" diff --stat HEAD origin/main 2>&1 | tail -10 | sed 's/^/  /'

if [[ "$DRY_RUN" == "1" ]]; then
  echo
  echo "${C_DIM}--dry-run: nothing applied.  Re-run without --dry-run to upgrade.${C_RST}"
  rm -f /tmp/breathline-upstream-manifest.yaml
  exit 0
fi

if [[ "$SKIP_BREATH_GATE" != "1" ]]; then
  echo
  echo "${C_DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RST}"
  echo "  ${C_BOLD}BREATH-GATE${C_RST} — confirm to apply $INSTALLED → $UPSTREAM"
  echo "${C_DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RST}"
  echo
  echo "  Type the exact phrase below to proceed, or anything else to abort:"
  echo
  echo "  ${C_BOLD}${C_ACCENT}I confirm this upgrade${C_RST}"
  echo
  printf "  > "
  read -r confirmation
  if [[ "$confirmation" != "I confirm this upgrade" ]]; then
    echo
    echo "  ${C_ERR}✗${C_RST} aborted (default-deny)"
    rm -f /tmp/breathline-upstream-manifest.yaml
    exit 1
  fi
  echo "  ${C_OK}✓${C_RST} breath received"
fi

echo
echo "${C_BOLD}applying upgrade...${C_RST}"
( cd "$PREFIX" && git pull --ff-only --quiet origin main ) || {
  echo "  ${C_ERR}✗${C_RST} fast-forward failed; manual merge required"
  exit 1
}
echo "  ${C_OK}✓${C_RST} repo fast-forwarded"

# Post-pull signature verification (v0.4.0+)
ALLOWED_SIGNERS="$PREFIX/distribution/signing_keys/allowed_signers"
if [[ -f "$ALLOWED_SIGNERS" ]] && command -v ssh-keygen >/dev/null 2>&1; then
  echo "  ${C_DIM}verifying release signatures...${C_RST}"
  sig_fail=0
  for sigfile in "$PREFIX/manifest.yaml.sig" "$PREFIX/CHARTER.md.sig" "$PREFIX/CONSTITUTION.md.sig" \
                 "$PREFIX/LICENSE.sig" "$PREFIX/CHANGELOG.md.sig"; do
    [[ -f "$sigfile" ]] || continue
    target="${sigfile%.sig}"
    if ! ssh-keygen -Y verify -f "$ALLOWED_SIGNERS" -I "kenn@mangumcfo.com" \
         -n "breathline-release" -s "$sigfile" < "$target" >/dev/null 2>&1; then
      echo "  ${C_ERR}✗${C_RST} signature MISMATCH: $(basename "$target")"
      sig_fail=$((sig_fail + 1))
    fi
  done
  if [[ "$sig_fail" -gt 0 ]]; then
    echo "  ${C_ERR}✗${C_RST} $sig_fail signature failure(s) — UPGRADE PAUSED.  Default-deny."
    echo "  Manually inspect $PREFIX before proceeding."
    exit 1
  fi
  echo "  ${C_OK}✓${C_RST} all release signatures verified"
fi

# Try migration script if exists (versions converted to compact form for path)
INST_KEY=$(echo "$INSTALLED" | tr -d '.')
UP_KEY=$(echo "$UPSTREAM" | tr -d '.')
MIGRATION_SCRIPT="$PREFIX/distribution/migrations/v${INST_KEY}_to_v${UP_KEY}.py"
if [[ -f "$MIGRATION_SCRIPT" ]]; then
  echo "  ${C_DIM}running migration: $(basename "$MIGRATION_SCRIPT")...${C_RST}"
  ( cd "$PREFIX" && "$PREFIX/platform/.venv/bin/python" "$MIGRATION_SCRIPT" ) || {
    echo "  ${C_ERR}✗${C_RST} migration failed; see above"
    exit 1
  }
  echo "  ${C_OK}✓${C_RST} migration applied"
else
  echo "  ${C_DIM}(no migration needed for $INSTALLED → $UPSTREAM)${C_RST}"
fi

if [[ -d "$PREFIX/platform/.venv" ]]; then
  echo "  ${C_DIM}refreshing platform deps...${C_RST}"
  ( cd "$PREFIX/platform" && .venv/bin/pip install -e ".[dev]" --quiet --upgrade ) 2>&1 | tail -3 | sed 's/^/    /' || true
  echo "  ${C_DIM}verifying with platform tests...${C_RST}"
  ( cd "$PREFIX/platform" && .venv/bin/python -m pytest --tb=no -q 2>&1 | tail -3 ) | sed 's/^/    /'
fi

STATEFILE="$HOME/.breathline-state.yaml"
if [[ -f "$STATEFILE" ]]; then
  ts="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  if grep -q "installed_version:" "$STATEFILE"; then
    sed -i.bak "s/^installed_version:.*/installed_version: \"$UPSTREAM\"/" "$STATEFILE"
    sed -i "s/^installed_at:.*/installed_at: \"$ts\"/" "$STATEFILE"
    rm -f "$STATEFILE.bak"
    echo "  ${C_OK}✓${C_RST} node state updated: $STATEFILE"
  fi
fi

rm -f /tmp/breathline-upstream-manifest.yaml

echo
echo "${C_OK}${C_BOLD}✓ upgrade complete${C_RST}  $INSTALLED → $UPSTREAM"
echo
echo "  ${C_DIM}breathline status${C_RST} to see what's new"
echo
echo "${C_BOLD}∞Δ∞${C_RST}"
