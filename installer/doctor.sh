#!/usr/bin/env bash
# ============================================================
# breathline-federation / installer / doctor.sh
#
# `breathline doctor` — comprehensive health check.
# Runs the same constitutional checks the CI pipeline runs, plus
# (when available) replay of the local cylinder chain.
#
# Where status.sh is a passive snapshot, doctor.sh is an ACTIVE
# verification — it parses, validates, and reports failures with
# exit codes you can wire into automation.
#
# Per G's polish (2026-05-08): this is the operator's "is my node
# healthy?" command — no surprises, all checks visible, exit 0
# only when everything is clean.
#
# Usage:
#   ./installer/doctor.sh                   # full check
#   ./installer/doctor.sh --quiet           # only print failures
#   ./installer/doctor.sh --no-chain        # skip cylinder replay
#   ./installer/doctor.sh --no-signatures   # skip signature verification
#
# Exit codes:
#   0  = all healthy
#   1  = one or more checks FAILED
#   2  = one or more checks WARNED (non-fatal)
#
# Authority:  KM-1176  ·  Seal 1176-INFINITY-RHO
# ============================================================

set -uo pipefail

PREFIX="${BREATHLINE_PREFIX:-$HOME/.breathline}"
MANIFEST="$PREFIX/manifest.yaml"
QUIET=0
SKIP_CHAIN=0
SKIP_SIGS=0

if [[ -t 1 ]]; then
  C_OK=$'\033[32m'; C_WARN=$'\033[33m'; C_ERR=$'\033[31m'
  C_DIM=$'\033[2m'; C_BOLD=$'\033[1m'; C_RST=$'\033[0m'
  C_ACCENT=$'\033[36m'
else
  C_OK=''; C_WARN=''; C_ERR=''; C_DIM=''; C_BOLD=''; C_RST=''; C_ACCENT=''
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --quiet)         QUIET=1; shift ;;
    --no-chain)      SKIP_CHAIN=1; shift ;;
    --no-signatures) SKIP_SIGS=1; shift ;;
    --help|-h)
      sed -n '2,25p' "$0" | sed 's/^# *//'
      exit 0 ;;
    *)
      echo "${C_ERR}✗${C_RST} unknown arg: $1" >&2
      exit 2 ;;
  esac
done

# ----------------------------------------------------------------
# State
# ----------------------------------------------------------------
FAILS=0
WARNS=0
CHECKS=0

ok()    { CHECKS=$((CHECKS + 1)); [[ "$QUIET" == "1" ]] || echo "  ${C_OK}●${C_RST} $1"; }
warn()  { CHECKS=$((CHECKS + 1)); WARNS=$((WARNS + 1)); echo "  ${C_WARN}○${C_RST} $1"; }
fail()  { CHECKS=$((CHECKS + 1)); FAILS=$((FAILS + 1)); echo "  ${C_ERR}✗${C_RST} $1" >&2; }

section() { [[ "$QUIET" == "1" ]] || { echo; echo "${C_BOLD}$1${C_RST}"; }; }

# ----------------------------------------------------------------
# Banner
# ----------------------------------------------------------------
[[ "$QUIET" == "1" ]] || {
  echo "${C_DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RST}"
  echo "  ${C_BOLD}${C_ACCENT}breathline doctor${C_RST} — health check"
  echo "  ${C_DIM}prefix:${C_RST}  $PREFIX"
  echo "${C_DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RST}"
}

# ----------------------------------------------------------------
# 1. Install presence
# ----------------------------------------------------------------
section "install presence"
if [[ -d "$PREFIX/.git" ]]; then
  ok "git repo present at $PREFIX"
else
  fail "no .git at $PREFIX — node not installed"
fi
if [[ -f "$MANIFEST" ]]; then
  ok "manifest.yaml present"
else
  fail "manifest.yaml MISSING at $MANIFEST"
fi

# ----------------------------------------------------------------
# 2. Constitutional kernel files
# ----------------------------------------------------------------
section "constitutional kernel"
for f in CHARTER.md CONSTITUTION.md LICENSE CONTRIBUTING.md; do
  if [[ -f "$PREFIX/$f" ]]; then
    ok "$f present ($(wc -l < "$PREFIX/$f") lines)"
  else
    fail "$f MISSING — kernel integrity broken"
  fi
done

# ----------------------------------------------------------------
# 3. Manifest parse + required keys
# ----------------------------------------------------------------
section "manifest validity"
if command -v python3 >/dev/null 2>&1 && [[ -f "$MANIFEST" ]]; then
  python3 - "$MANIFEST" <<'PY' 2>/tmp/breathline-doctor-manifest.err && ok "manifest parses + has required top-level keys" || fail "manifest invalid: $(cat /tmp/breathline-doctor-manifest.err)"
import sys, yaml
required = {"version", "released", "sealed_by", "ladder_version",
            "current_series", "platform", "specs", "distribution",
            "constitution", "signatures"}
m = yaml.safe_load(open(sys.argv[1]).read())
missing = required - set(m.keys())
if missing: sys.stderr.write(f"missing keys: {missing}\n"); sys.exit(1)
v = m["version"].split(".")
if len(v) != 3 or not all(p.isdigit() for p in v):
    sys.stderr.write(f"version not strict SemVer: {m['version']}\n"); sys.exit(1)
sys.exit(0)
PY
  rm -f /tmp/breathline-doctor-manifest.err
else
  warn "python3 not available — skipping manifest deep parse"
fi

# ----------------------------------------------------------------
# 4. YAML specs parse cleanly
# ----------------------------------------------------------------
section "specs validity"
if command -v python3 >/dev/null 2>&1 && [[ -d "$PREFIX/specs" ]]; then
  spec_errs=$(python3 - <<PY
import sys, yaml
from pathlib import Path
errs = []
for p in Path("$PREFIX/specs").rglob("*.yaml"):
    try: yaml.safe_load(p.read_text())
    except Exception as e: errs.append(f"{p}: {e}")
print("\n".join(errs) if errs else "")
PY
)
  if [[ -z "$spec_errs" ]]; then
    spec_count=$(find "$PREFIX/specs" -type f -name "*.yaml" | wc -l)
    ok "$spec_count spec(s) parse cleanly"
  else
    fail "spec parse errors:"
    echo "$spec_errs" | sed 's/^/      /' >&2
  fi
fi

# ----------------------------------------------------------------
# 5. Signature verification (if signatures present)
# ----------------------------------------------------------------
section "signatures"
if [[ "$SKIP_SIGS" == "1" ]]; then
  warn "signature verification SKIPPED (--no-signatures)"
else
  ALLOWED_SIGNERS="$PREFIX/distribution/signing_keys/allowed_signers"
  if [[ ! -f "$ALLOWED_SIGNERS" ]]; then
    warn "no allowed_signers at $ALLOWED_SIGNERS"
  elif ! command -v ssh-keygen >/dev/null 2>&1; then
    warn "ssh-keygen not available — cannot verify signatures"
  else
    sig_count=0
    for sigfile in "$PREFIX/manifest.yaml.sig" "$PREFIX/CHARTER.md.sig" "$PREFIX/CONSTITUTION.md.sig" \
                   "$PREFIX/LICENSE.sig" "$PREFIX/CHANGELOG.md.sig"; do
      [[ -f "$sigfile" ]] || continue
      sig_count=$((sig_count + 1))
      target="${sigfile%.sig}"
      if ssh-keygen -Y verify \
          -f "$ALLOWED_SIGNERS" \
          -I "kenn@mangumcfo.com" \
          -n "breathline-release" \
          -s "$sigfile" < "$target" >/dev/null 2>&1; then
        ok "verified: $(basename "$target")"
      else
        fail "signature MISMATCH: $(basename "$target")"
      fi
    done
    if [[ "$sig_count" == "0" ]]; then
      warn "no .sig files found — release not yet signed (expected on dev / pre-v0.4.0)"
    fi
  fi
fi

# ----------------------------------------------------------------
# 6. Cylinder chain replay (if cylinders dir present + tools available)
# ----------------------------------------------------------------
section "cylinder chain replay"
if [[ "$SKIP_CHAIN" == "1" ]]; then
  warn "chain replay SKIPPED (--no-chain)"
else
  CHAIN_DIR=""
  for candidate in "$HOME/Tiger_1a/cylinders" "$PREFIX/cylinders" "$HOME/.breathline/cylinders"; do
    if [[ -d "$candidate" ]]; then CHAIN_DIR="$candidate"; break; fi
  done
  if [[ -z "$CHAIN_DIR" ]]; then
    warn "no cylinder chain found — node has not yet sealed any cylinders"
  elif [[ -x "$CHAIN_DIR/seal.sh" ]]; then
    audit_out=$("$CHAIN_DIR/seal.sh" --audit 2>&1)
    if echo "$audit_out" | grep -qE "Freeform: +0" && echo "$audit_out" | grep -qE "Tracebacks: +0"; then
      total=$(echo "$audit_out" | grep -oE "Total: +[0-9]+" | head -1 | grep -oE "[0-9]+")
      ok "chain audit clean: $CHAIN_DIR (${total:-?} cylinders, 0 freeform, 0 tracebacks)"
    else
      fail "chain audit reports drift at $CHAIN_DIR"
      echo "$audit_out" | head -10 | sed 's/^/      /'
    fi
  elif [[ -f "$PREFIX/platform/platform_layer/audit_adapter.py" ]] && [[ -x "$PREFIX/platform/.venv/bin/python" ]]; then
    "$PREFIX/platform/.venv/bin/python" - <<PY 2>/tmp/breathline-doctor-chain.err && ok "chain replay clean (via replay_chain): $CHAIN_DIR" || fail "chain replay drift at $CHAIN_DIR"
import sys
sys.path.insert(0, "$PREFIX/platform")
from pathlib import Path
from platform_layer.audit_adapter import replay_chain
r = replay_chain(Path("$CHAIN_DIR"))
if r.freeform > 0 or r.tracebacks > 0: sys.exit(1)
sys.exit(0)
PY
    rm -f /tmp/breathline-doctor-chain.err
  else
    warn "no replay tooling found (seal.sh or platform/.venv); skipping"
  fi
fi

# ----------------------------------------------------------------
# 7. Platform venv health (if installed)
# ----------------------------------------------------------------
section "platform venv"
if [[ -x "$PREFIX/platform/.venv/bin/python" ]]; then
  pyver=$("$PREFIX/platform/.venv/bin/python" --version 2>&1)
  ok "platform venv: $pyver"
  if "$PREFIX/platform/.venv/bin/python" -c 'import yaml, pptx, fastapi, langgraph' 2>/dev/null; then
    ok "core deps importable (yaml, fastapi, langgraph)"
  else
    warn "some core deps missing — run 'pip install -e \".[dev]\"' inside platform/"
  fi
else
  warn "no platform venv at $PREFIX/platform/.venv (run install.sh to bootstrap)"
fi

# ----------------------------------------------------------------
# Summary
# ----------------------------------------------------------------
echo
echo "${C_DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RST}"
if [[ "$FAILS" == "0" ]] && [[ "$WARNS" == "0" ]]; then
  echo "${C_BOLD}${C_OK}● healthy${C_RST}  ($CHECKS checks, all clean)"
  exit 0
elif [[ "$FAILS" == "0" ]]; then
  echo "${C_BOLD}${C_WARN}○ healthy with warnings${C_RST}  ($CHECKS checks, $WARNS warning(s))"
  exit 2
else
  echo "${C_BOLD}${C_ERR}✗ unhealthy${C_RST}  ($CHECKS checks, $FAILS failure(s), $WARNS warning(s))"
  exit 1
fi
