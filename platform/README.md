# Breathline Agentic Platform — v1.0 Implementation

This is the **implementation** of the agentic platform specified in
`agentic_platform_seed/IMPLEMENTATION_PLAN.md` (the locked v0.1 plan in
the parent folder).

**Authority**: Sovereignty-Aligned Charter v1.0 + Constitution@A1
**Inherits from**: `../CONSTITUTIONAL_PARENTAGE.md` (lex superior)
**Voice convention**: `../WRITING_CONVENTION.md`

In any conflict between this code and its parent authorities, the parents
win.

---

## Status

🟢 **Phases 1–5 SHIPPED** — Demo 2 is structurally complete and
operationally real. The platform sealed its first live
`platform_audit:cfo_agent` cylinder into the production Tiger chain
on 2026-05-07; chain integrity is now automatically verified.

| Phase | Scope | Status | Chain seq |
|---|---|---|---|
| Phase 1 | Kernel + bootstrap (5 primitives, breath_gate, cost_meter) | ✅ SHIPPED | 139 |
| Phase 2 | Platform layer (Charter V.7, plug-in, registry, receipt minter, audit adapter) | ✅ SHIPPED | 140 |
| Phase 3 | 3 role agents (CFO FORECAST, Synthesis orchestrator, Compliance Charter V.7) | ✅ SHIPPED | 143 |
| Phase 4 | Structural integrations (cost gate + Critic + Auditor + receipt into `route_request`) | ✅ SHIPPED | 144 |
| Phase 5 | Real-chain wiring + LangGraph wrap + Bootstrap CLI + HTTP coverage | ✅ SHIPPED | 145–147 |
| 8.3 gate | Constitutional integrity at runtime (chain replay genesis→tip) | ✅ CLOSED | 149 |
| 8.6 gate | Performance (bootstrap <8min observed 153ms; e2e <5min observed <1ms) | ✅ CLOSED | (this seal) |
| 8.8 partial | Breath-gate timeout fails-closed (audit-chain-violation halt remains, ties to Q13) | ✅ partial | (this seal) |
| 8.8 final | Audit-chain-violation halt — `ChainSentinel` boot+verify+on_seal cadence wired into runtime | ✅ CLOSED | (this seal) |
| **v0.1 acceptance** | **All 7 Section 8 gates green** | ✅ **COMPLETE** | (this seal) |

**169 / 169 tests passing** in `.breathline-tools-venv` (langgraph
0.2.76 + fastapi 0.119) — wall time 1.37s; 129 + 13 skipped in
system python (skipped tests are langgraph-dependent only).

See `../STATUS_2026-05-07.md` for the full chain-level status snapshot.

---

## Quick start

```bash
# 1. Navigate
cd v1.0

# 2. Install (one-time; uses the .breathline-tools-venv conventionally)
pip install -e ".[dev]"

# 3. Full suite
python -m pytest -v
# Expected: 148 passed in <1.5s

# 4. Section 8.3 — chain replay against the real Tiger chain
python -m pytest tests/test_audit_chain_replay.py -v
# Expected: 6 passed (4 synthetic + 2 real-chain)

# 5. Bootstrap to Layer 1 only (kernel)
python -m scripts.bootstrap --seed seed/02_SEED_MANIFEST.yaml --skip-breath-gate

# 6. Bootstrap full stack through Layer 3 (kernel + platform + roles)
python -m scripts.bootstrap --full --skip-breath-gate

# 7. Bootstrap with LangGraph wrap
python -m scripts.bootstrap --full --use-langgraph --skip-breath-gate

# 8. HTTP endpoint (POST /invoke for full Phase 4 stack)
#    See test_http_endpoint.py for TestClient examples
```

---

## Repository structure

```
v1.0/
├── pyproject.toml                       # Project metadata + deps
├── .env.example                         # Environment template
├── README.md                            # This file
├── seed/                                # Locked spec files (immutable at runtime)
│   ├── 02_SEED_MANIFEST.yaml            # Executable seed (v0.3)
│   ├── receipt_worthy_events.yaml       # Default-deny taxonomy
│   ├── action_classes.yaml              # Charter V.7 action classes
│   ├── CONSTITUTIONAL_PARENTAGE.md      # Lex superior declaration
│   ├── CONSTITUTION.md                  # Constitution@A1
│   ├── CHARTER_v1.0.md                  # Charter v1.0
│   └── .fingerprints.json               # SHA-256 hashes for verification
├── kernel/                              # Layer 1 — kernel primitives
│   ├── boot.py                          # Reads seed → instantiates Layer 1
│   ├── breath_gate.py                   # Charter II.4.4 invariant
│   ├── cost_meter.py                    # Pre-dispatch cost gate
│   └── primitives/
│       ├── spec.py / constructor.py / critic.py
│       ├── auditor.py / governor.py
├── platform_layer/                      # Layer 2 — platform services
│   ├── permission_spec.py               # Charter V.7 enforcement
│   ├── registry.py                      # RoleRegistry
│   ├── plugin_interface.py              # route_request + FastAPI app
│   ├── role_artifact_critic.py          # Phase 4 platform Critic
│   ├── audit_adapter.py                 # seal.sh subprocess + replay_chain (8.3)
│   ├── receipt_minter.py                # Default-deny B49 mint
│   └── runtime.py                       # Phase 5 — build_runtime_context()
├── roles/                               # Layer 3 — role agents
│   ├── cfo_agent/
│   │   ├── role.py                      # Pure-Python CFOAgent
│   │   ├── frameworks/forecast.py       # FORECAST 8-step deterministic core
│   │   └── graph.py                     # LangGraph wrap
│   ├── synthesis_agent/
│   │   ├── role.py / frameworks/synthesis.py / graph.py
│   └── compliance_agent/
│       ├── role.py
│       ├── frameworks/charter_v7.py / compliance_review.py
│       └── graph.py                     # Conditional dispatch
├── scripts/
│   ├── bootstrap.py                     # CLI — Layer 1 / --full / --use-langgraph
│   └── runtime_smoke.py                 # Opt-in live-chain operator script
└── tests/                               # 148 tests, ~1.2s wall time
    ├── conftest.py
    ├── test_kernel_primitives.py        # 13 tests
    ├── test_permission_spec.py          # 12 tests
    ├── test_registry.py                 # 6 tests
    ├── test_plugin_interface.py         # 8 tests
    ├── test_receipt_minter.py           # 11 tests
    ├── test_constitutional_verification.py  # 6 tests
    ├── test_cfo_agent.py                # 12 tests
    ├── test_synthesis_agent.py          # 11 tests
    ├── test_compliance_agent.py         # 17 tests
    ├── test_e2e_recursion.py            # 4 tests (Section 8.2)
    ├── test_demo2_acceptance.py         # 11 tests (Section 8.2 + 8.7 + 8.8)
    ├── test_runtime_integration.py      # 7 tests (real subprocess to seal.sh)
    ├── test_langgraph_wrap.py           # 11 tests (graph parity + e2e)
    ├── test_bootstrap.py                # 4 tests (CLI flags)
    ├── test_http_endpoint.py            # 9 tests (FastAPI TestClient)
    ├── test_audit_chain_replay.py       # 6 tests (Section 8.3 — chain integrity)
    ├── test_perf_smoke.py               # 4 tests (Section 8.6 — perf gates)
    ├── test_breath_gate_timeout.py      # 4 tests (Section 8.8 — breath-gate timeout)
    └── test_chain_sentinel.py           # 13 tests (Section 8.8 — audit-chain-violation halt)
```

---

## Section 8 acceptance gates

| § | Item | State |
|---|---|---|
| 8.2 | End-to-end recursion ("Brief on Q3 readiness…") | ✅ |
| 8.3 | Constitutional integrity at runtime (chain replay genesis→tip) | ✅ |
| 8.4 | Cost discipline | ✅ structural |
| 8.5 | Default-deny verification (Charter V.7 + receipt taxonomy) | ✅ |
| 8.6 | Performance (bootstrap < 8 min, e2e < 5 min) | ✅ (observed: 153ms / <1ms) |
| 8.7 | Receipt integration | ✅ |
| 8.8 | Failure modes | ✅ — all 5 modes (cost cap, Critic DRIFT/DEFECT, role unknown, Charter V.7, breath-gate timeout, audit-chain-violation halt) |

---

## Constitutional posture

Every layer of this codebase is bound by the parent authorities declared
in `seed/CONSTITUTIONAL_PARENTAGE.md`:

- **No hardcoded principals** — identity flows end-to-end as `principal_id`
- **Default-deny everywhere** — Permission Specs, receipt taxonomy,
  action class taxonomy are opt-in lists
- **Cylinder chain as universal seal** — every action passes through
  operator-side `seal.sh` before the calling graph proceeds
- **Chain integrity automatically verified** — `replay_chain()` walks
  every cylinder genesis → tip and cross-checks against `seal.sh --audit`
- **Breath-gating as runtime invariant** — not a prompt input;
  structurally enforced
- **Fails closed** — any audit failure or cap breach refuses dispatch
  with no bypass
- **Charter V.7 forbidden delegation** — no agent may make personnel
  decisions, binding commitments, irreversible actions, or modify the
  Charter itself

---

## Recent decisions

- `../decisions/2026-05-06_phase1_phase2_implementation_milestone.md`
- `../decisions/2026-05-06_six-sov_hosting_architecture.md`
- `../decisions/2026-05-07_open_questions_alignment_response.md` (DRAFT — Q1–Q17 alignment with G's review)
- `../decisions/2026-05-07_section-8.3-audit-chain-replay.md` (Section 8.3 closure)
- `../decisions/2026-05-07_section-8.6-perf-and-8.8-breath-gate-timeout.md` (Section 8.6 + 8.8 breath-gate closures)
- `../decisions/2026-05-07_q13-chain-sentinel-section-8.8-final.md` (Q13 sentinel + Section 8.8 final closure → v0.1 acceptance gate complete)

---

∞Δ∞

*Implementation under operator authority (KM-1176). Public-facing voice
per `../WRITING_CONVENTION.md`. Phase delivery model per
`../IMPLEMENTATION_PLAN.md` Section 1 onward.*

∞Δ∞
