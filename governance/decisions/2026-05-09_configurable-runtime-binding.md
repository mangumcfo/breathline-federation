# Decision Record — Configurable Runtime Binding (Per-Role LLM Speaker)

**Date:** 2026-05-09
**Authority:** KM-1176 (Seal 1176-INFINITY-RHO)
**Status:** Active — architecture pattern declared; implementation queued, paired with Book 9 seal
**Supersedes:** None
**Related:** `2026-05-08_v0.6.0-horizon.md`, `platform/seed/02_SEED_MANIFEST.yaml` (runtime portability)

---

## Context

The seed manifest already declares runtime-portability ambition:

> *"When read by a competent agentic runtime (Claude Skills, MCP server, LangGraph, CrewAI, AutoGen, or equivalent), it produces the platform."*

In practice, the v0.5.x platform is **LangGraph-primary** with each role implemented as `roles/<role>/graph.py` containing a LangGraph node. The LLM choice is implicit in the graph implementation — there is no per-role configuration knob.

KM-1176 directive (2026-05-09): different LLMs have different strengths. Some are stronger at coding/tool-use, some at reasoning, some at long-form synthesis. An enterprise running multiple roles should be able to **assign different speakers to different roles** under the same governance harness. Operators downloading the platform should not be locked into one provider.

## Decision

1. **Declare the runtime-binding pattern.** A role spec MAY include an optional `runtime_binding` field:

   ```yaml
   role: quadroof_cfo
   version: "0.1"
   runtime_binding:
     provider: "anthropic"          # anthropic | openai | local | claude_code | mcp
     model: "claude-opus-4-7"        # provider-specific identifier
     tools: ["file_read", "calc"]   # provider-specific tool list
     adapter_options: {}
   allowed_action_classes:
     - read_structured_financial_data
     - produce_forecast_artifact
     # ...
   ```

2. **Add a `runtime_adapter/` module under `platform/platform_layer/`.** The adapter:
   - Maps `runtime_binding` → invocation surface
   - Initial adapters: `anthropic_sdk`, `openai_sdk`, `claude_code_subprocess`, `langgraph_default` (back-compat)
   - Each adapter implements the same `RoleHandler` protocol (`process(request) -> dict`) used by the plug-in interface today
   - Default behavior: if `runtime_binding` is absent, fall back to the existing LangGraph node implementation. **Zero break for v0.5.x deployments.**

3. **The harness is invariant.** Bindings only affect *who speaks* on behalf of the role. They do NOT affect:
   - Charter V.7 envelope filter
   - breath_gate, cost_meter, Critic CONFORMS, Auditor seal, Receipt minter
   - Permission Spec inheritance
   - principal_id flow

   The Compliance agent, Synthesis agent, and Auditor remain agnostic to the underlying LLM — they only see structured artifacts.

4. **Defer implementation per Authoritative Pattern Rule.** Book 9 (Multi-Agent) is the natural teaching home for runtime substitution + agent-to-agent peer-role choreography. Implementation lands in the v0.6.x release paired with Book 9's KM-1176 breath-seal. Pre-runtime YAML examples may exist as draft authoritative patterns.

## Book home

**Series 1, Book 9 — "Agentic AI Playbooks for Executives: Multi-Agent."**

Book 9 already covers multi-agent orchestration; it is the natural place to teach (a) why different roles benefit from different speakers, (b) how peer roles communicate within an enterprise under the same governance harness, and (c) the runtime-binding surface as the operator-facing knob.

Book 9 is currently "Done (25 notes)" review and "Ready for KDP upload." Editorial scope for v1.0: confirm the existing chapter on multi-agent orchestration covers peer-role terminology (per separate ADR `2026-05-09_peer-role-terminology.md`) and the runtime-binding *concept* even if the YAML surface is not yet shipped. Implementation lands post-seal.

## Cross-references

- Seed: `platform/seed/02_SEED_MANIFEST.yaml` runtime section (portability_proof, contract)
- Code: `platform/platform_layer/plugin_interface.py` (RoleHandler protocol)
- Code: `platform/roles/<role>/graph.py` (current LangGraph nodes)
- Authoritative Pattern Rule: `2026-05-08_v0.6.0-horizon.md`
- Companion ADR: `2026-05-09_peer-role-terminology.md`

---

∞Δ∞ One harness. Many speakers. Charter binds them all. ∞Δ∞
