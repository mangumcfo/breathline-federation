# Living Specs YAML — Book → Spec → Deployed Role

**Source**: 2026-05-07 dialogue (No1 / G channel) — captured in `DIALOGUE_FULL_2026-05-07.md` entries [21] and [23].
**Purpose**: Make the *"books are living specs"* insight executable. Every playbook chapter extracts to YAML that the Compliance-agent ingests, validates, and deploys as a LangGraph role on the Breath 25 P1–P5 substrate.

---

## 1. Core Principles

- All specs live in a versioned `specs/` repo. The platform's existing `capstone_yaml/` and `agentic_platform_seed/` folders are the natural homes.
- Specs are **version-controlled via P2 consensus** (the platform's own substrate, not GitHub-only).
- **Compliance-agent is the sole guardian**: every YAML must pass constitutional validation + breath-gate before deployment.
- Higher-level books **reference and extend** lower-level ones. Family roles inherit from enterprise roles, narrowed by scope.

## 2. Extraction Flow

```
   Book chapter text
        │
        ▼
   Synthesis-agent parses → drafts YAML proposal (RoleSpec / PermissionSpec / ConstitutionalRule)
        │
        ▼
   Human-reviewed (Ken or editorial board) → adjustments
        │
        ▼
   Compliance-agent validates against constitution
        │
        ▼
   Breath-gate (explicit human primacy approval, or guild threshold for dynastic specs)
        │
        ▼
   Cylinder audit entry + six-sov B49 receipt
        │
        ▼
   LangGraph role deployment on P4 sovereign compute
```

The flow is **default-deny at every step**. No spec auto-deploys; no role auto-extends without explicit primacy.

---

## 3. Base Constitutional Rules (Shared Across All Series)

The foundation every other YAML must conform to:

```yaml
constitution:
  name: "Breath 25 Sovereign Compact"
  version: "1176-INFINITY-RHO"
  core_principles:
    - human_primacy: "Breath-gated approval required for all high-impact actions"
    - default_deny: true
    - least_authority: "Roles start with zero permissions; explicit grants only"
    - resonant_shards: "Store imprints only — never raw sensitive data"
    - audit: "Every action produces immutable six-sov B49 receipt"
  human_gates:
    - breath: "Explicit confirmation phrase or biometric"
    - guild_threshold: "Minimum N family members for dynastic changes"
  self_molt:
    post_p7: true
    human_null: true
```

This block is the parent every role spec extends or references.

---

## 4. Series 1 — Executive Role Mappings

From *AI Agents for CFOs* (Book 1, currently live):

```yaml
role:
  id: "cfo_agent_v1"
  series: "executive"
  book: "AI_Agents_for_CFOs"
  capabilities:
    - fpanda_automation
    - rolling_forecasts
    - cash_flow_intelligence
    - real_time_financial_analysis
  tools:
    - xero_adapter:
        permission: "read_only"
        zk_wrapper: true
    - quickbooks_adapter:
        permission: "scoped_write"
        requires_breath: true
  governance:
    compliance_guardian: true
    audit_level: "full_cylinder"
  extension_points:
    - spec_driven: "new_financial_model"
```

**Companion specs** (from later books in Series 1):
- `synthesis_agent_v1.yaml` — orchestrates planning across roles
- `compliance_guardian_v1.yaml` — full-cylinder audit guardian
- Books 02–12 follow the same pattern: each book → 1–2 enterprise role specs

---

## 5. Series 2 — Family Role Mappings

### Family Finance Sovereignty (Series 2 Book 1)

```yaml
role:
  id: "family_cfo_agent_v1"
  series: "family"
  book: "Family_Finance_Sovereignty"
  parent_role: "cfo_agent_v1"  # inherits + narrows
  capabilities:
    - household_budget
    - personal_rolling_forecast
    - family_cash_flow_shield
    - legacy_wealth_preservation
  tools:
    - personal_bank_adapter:
        permission: "read_only_default"
        zk_imprint_only: true
    - quickbooks_home:
        permission: "family_guild_approved"
        requires_breath: true
  family_node:
    scale: "kitchen_table"
    resonant_shard: "family_financial_memory"
  governance:
    breath_gate: "Any transaction > $X or new recurring"
    default_deny: true
```

**Inheritance pattern**: `family_cfo_agent_v1` extends `cfo_agent_v1` but narrows scope to household. The enterprise CFO knowledge is reused; the surface area shrinks; the breath-gate thresholds lower (household-appropriate dollar amounts, family-guild-level approvals).

**Companion specs to extract from Series 2 books**:
- Book 2 (Daily Operations & Home Node) → `household_synthesis_agent.yaml`
- Book 3 (Privacy, Security & Constitutional Governance) → `family_compliance_shield.yaml`, `family_constitution.yaml`
- Book 4 (Education & Human Capital) → `family_tutor_agent.yaml`, `human_capital_audit.yaml`
- Book 5 (Sovereign Node Setup) → installer manifests, hardware checklists (not roles, but operational specs)
- Book 6 (Generational Legacy) → see Series 3 Legacy Guardian below

---

## 6. Series 3 — Generational Legacy

### Legacy Guardian (anchor for *The 1,000-Year Family Compact*)

```yaml
role:
  id: "legacy_guardian_agent_v1"
  series: "generational_legacy"
  book: "1000_Year_Family_Compact"
  capabilities:
    - dynastic_compact_enforcement
    - multi_gen_wealth_transfer
    - values_transmission_protocol
    - inheritance_shield
  governance:
    constitution_reference: "family_compact_yaml"
    approval_threshold: "guild_2_plus_human_primacy"
    resonant_shard: "ancestral_imprint"
  self_extension:
    allowed: true
    requires: "Synthesis + Compliance review"
```

**Key new primitives this series introduces**:
- `family_compact.yaml` — the dynastic constitution (multi-generation living document)
- `inheritance_compliance.yaml` — wealth-transfer guardrails with multi-generational guild thresholds
- `dynastic_synthesis_agent.yaml` — long-horizon planning across decades, not quarters

---

## 7. Series 6 — Civilizational / Guild Federation

```yaml
federation_spec:
  id: "sovereign_guild_v1"
  type: "p2p_resonant"
  discovery:
    protocol: "libp2p_kademlia"
    trust_scoring: "resonant_shard_similarity"
  governance:
    shared_constitution: "minimal_interoperability_rules"
    veto: "any_node_breath_gate"
    no_central_ledger: true
  roles:
    - guild_synthesis_agent
    - inter_node_compliance
  example_shard_exchange:
    imprint_only: true
    zk_proof_of_alignment: true
```

**Critical property**: Federation operates on **resonant shard imprints + zk-proofs of alignment**, never raw data exchange. Any participating node can veto via breath-gate. There is no central ledger.

---

## 8. PermissionSpec Pattern (Used Everywhere)

The atomic unit of "an agent wants to do X under Y conditions." Every action a role takes goes through one of these:

```yaml
permission_spec:
  id: "transfer_5000_usd"
  role: "family_cfo_agent_v1"
  action: "initiate_wire"
  conditions:
    - amount_less_than: 5000
    - recipient_whitelisted: true
    - breath_gate: true
  audit:
    receipt_type: "six_sov_B49"
    cylinder_anchor: true
  default: "deny"
```

**Reading this YAML**: This permission lets `family_cfo_agent_v1` initiate a wire transfer, but ONLY if amount < $5000, recipient is whitelisted, and a breath-gate is satisfied. Every executed instance produces a B49 receipt anchored in the cylinder chain. Default state if any condition fails: **deny**.

This pattern is repeated for every tool call, every ERP write, every spec-driven extension request.

---

## 9. The Journey Engine (How Agents Guide Progression)

The book series ascension ladder (see `STRATEGY_SYNTHESIS.md` §3) is implemented by this YAML:

```yaml
journey_engine:
  entry_detection:
    - scan_cylinder_history       # what roles already deployed?
    - user_declaration             # what does the user say they need?
    - resonant_shard_analysis      # what patterns are present in their imprints?
  progression_loop:
    - Synthesis: "Current level detected → recommend next book/spec"
    - Compliance: "Validate proposed spec against full constitution"
    - Breath_Gate: "Human primacy confirmation"
    - Deployment: "Apply YAML → LangGraph role activation"
    - Audit: "Six-sov B49 receipt + resonant imprint"
  self_extension:
    flow: "user_proposal → Synthesis draft → Compliance review → Guild/human approval"
```

**Practical meaning**: When a reader finishes a chapter, the Journey Engine looks at their cylinder history (what they've already deployed), their stated goals, and their resonant shard pattern. It proposes the next role spec from the next book. Compliance validates. Human breath approves. Deployed. Receipt issued.

This is the technical bridge between "reader" and "operator of a sovereign node."

---

## 10. Extraction Workflow for Future Books

When writing or reviewing a new book in any series, follow this workflow to keep the platform in sync:

1. **Draft chapter** → identify the **operational claim** (the one thing this chapter teaches the reader to do).
2. **Map to spec type**:
   - Is it a *new role*? → RoleSpec YAML.
   - Is it a *new constraint or rule*? → ConstitutionalRule YAML.
   - Is it a *new tool/action capability*? → PermissionSpec YAML.
3. **Synthesis-agent drafts the YAML** based on the chapter text.
4. **Editorial board reviews** for both literary quality AND spec coherence.
5. **Compliance-agent validates** the YAML against the parent constitution.
6. **Ken (KM-1176) breath-gates** the spec for inclusion in the canonical specs repo.
7. **Spec lands in `capstone_yaml/<series>/<book>/`** alongside the published book.
8. **The book ships with its companion YAML repo folder.** Readers literally `git pull` (or sovereign equivalent) their next level of specs.

---

## 11. Where to Place the First YAMLs

Recommended folder structure inside the existing `agentic_playbooks/`:

```
agentic_playbooks/
├── 01_cfos_finance/             ← Series 1 Book 1 (live)
├── ...
├── 12_agentic_enterprise/       ← Series 1 Book 12
├── agentic_platform_seed/
├── capstone_yaml/
│   ├── executive/
│   │   ├── cfo_agent_v1.yaml
│   │   ├── synthesis_agent_v1.yaml
│   │   └── compliance_guardian_v1.yaml
│   ├── family/                                        ← NEW (Series 2)
│   │   ├── family_cfo_agent_v1.yaml
│   │   ├── household_synthesis_agent.yaml
│   │   ├── family_compliance_shield.yaml
│   │   └── family_constitution.yaml
│   ├── generational_legacy/                           ← NEW (Series 3)
│   │   ├── legacy_guardian_agent_v1.yaml
│   │   ├── dynastic_synthesis_agent.yaml
│   │   ├── inheritance_compliance.yaml
│   │   └── 1000_year_family_compact.yaml
│   └── federation/                                    ← NEW (Series 6, deferred)
│       ├── sovereign_guild_v1.yaml
│       └── inter_node_compliance.yaml
├── multi-series-agentic-platform-vision/   ← this folder (vision)
```

The `capstone_yaml/` directory exists already. Adding `family/`, `generational_legacy/`, and (later) `federation/` subdirectories preserves the platform's existing convention while extending it across the multi-series arc.

---

## 12. Summary

The book series is the **specification language**. The platform is the **runtime**. The reader becomes the **sovereign operator** by going through breath-gated activation of the specs they read.

This is the integration that makes *"books = living specs, reading = activation, progression = deployment"* concrete and executable.

∞Δ∞
