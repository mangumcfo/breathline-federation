  breathline-federation — Proposed Repo Architecture                                                                                                                                                       
                                                                                                                                                                                                             
  0. The architectural choice — hybrid federation, not mono-repo
                                                                                                                                                                                                             
  Three options were possible. I'm recommending Option C (hybrid) — breathline-federation is the public sovereign onboarding hub + platform distribution + spec catalog, with private companion repos for    
  assets that can't be public (KDP-exclusive manuscripts).                                                                                                                                                   
                                                                                                                                                                                                             
  ┌──────────────────────────┬────────────────────────────────────────────────────────┬─────────────────────────────────────┬─────────────────────────────────────────────────────┐                          
  │                          │    Mono-repo (everything in breathline-federation)     │      Federation of small repos      │                Hybrid (recommended)                 │
  ├──────────────────────────┼────────────────────────────────────────────────────────┼─────────────────────────────────────┼─────────────────────────────────────────────────────┤                          
  │ Repo size                │ Bloats to 10+ GB over years (book PDFs, images, audio) │ Each tiny but coordination overhead │ Small, focused, public-facing                       │                        
  ├──────────────────────────┼────────────────────────────────────────────────────────┼─────────────────────────────────────┼─────────────────────────────────────────────────────┤
  │ KDP compatibility        │ ❌ Manuscripts can't be public                         │ ✅ private repos allowed            │ ✅ via books-vault private sibling                  │                          
  ├──────────────────────────┼────────────────────────────────────────────────────────┼─────────────────────────────────────┼─────────────────────────────────────────────────────┤                          
  │ User refresh story       │ One git pull but heavy                                 │ Many sync points                    │ One breathline upgrade against this repo            │                          
  ├──────────────────────────┼────────────────────────────────────────────────────────┼─────────────────────────────────────┼─────────────────────────────────────────────────────┤                          
  │ Book + spec co-publish   │ Coupled tightly but messy                              │ Loose, error-prone                  │ Specs in main repo; book artifacts in private vault │                        
  ├──────────────────────────┼────────────────────────────────────────────────────────┼─────────────────────────────────────┼─────────────────────────────────────────────────────┤                          
  │ Federation P2P semantics │ Awkward                                                │ Natural per-node sovereignty        │ Natural — one canonical reference, peers fork       │                        
  └──────────────────────────┴────────────────────────────────────────────────────────┴─────────────────────────────────────┴─────────────────────────────────────────────────────┘                          
                                                                                                                                                                                                           
  ---                                                                                                                                                                                                        
  1. The repo layout                                                                                                                                                                                       
                                                                                                                                                                                                             
  mangumcfo/breathline-federation/                    PUBLIC, the canonical source of truth
  │                                                                                                                                                                                                          
  ├── README.md                                       ← Vision, ascension ladder, install one-liner                                                                                                        
  ├── INSTALL.md                                      ← Quick-start                                                                                                                                          
  ├── LICENSE                                         ← Constitutional license (see §6)                                                                                                                      
  ├── CHARTER.md                                      ← Sovereignty-Aligned Charter v1.0                                                                                                                     
  ├── CONSTITUTION.md                                 ← Constitution@A1                                                                                                                                      
  ├── manifest.yaml                                   ← LATEST VERSION + checksums (the refresh anchor)                                                                                                      
  │                                                                                                                                                                                                          
  ├── installer/                                      ← USER-FACING INSTALL/UPGRADE                                                                                                                          
  │   ├── install.sh                                  ← curl | bash entry point                                                                                                                              
  │   ├── upgrade.sh                                  ← `breathline upgrade`                                                                                                                               
  │   ├── verify.sh                                   ← integrity + constitutional validation                                                                                                                
  │   └── platforms/                                  ← Linux, macOS, Windows-WSL nuances                                                                                                                  
  │       ├── linux.sh                                                                                                                                                                                       
  │       ├── darwin.sh                                                                                                                                                                                      
  │       └── wsl.sh                                                                                                                                                                                         
  │                                                                                                                                                                                                          
  ├── platform/                                       ← THE AGENTIC PLATFORM CODE (Breath 25)                                                                                                              
  │   ├── kernel/                                     ← P1–P5 primitives + breath_gate + cost_meter                                                                                                          
  │   ├── platform_layer/                             ← runtime, audit_adapter, chain_sentinel,                                                                                                              
  │   │                                                  receipt_minter, role_artifact_critic                                                                                                                
  │   ├── roles/                                      ← Pre-built role handlers (CFO/Synth/Comp + family + legacy + ...)                                                                                     
  │   │   ├── executive/                              ← Series 1 roles                                                                                                                                       
  │   │   ├── family/                                 ← Series 2 roles                                                                                                                                       
  │   │   ├── generational_legacy/                    ← Series 3 roles                                                                                                                                       
  │   │   └── ...                                                                                                                                                                                            
  │   ├── scripts/                                    ← bootstrap.py, runtime_smoke.py                                                                                                                       
  │   ├── tests/                                      ← 169+ tests                                                                                                                                           
  │   └── pyproject.toml                                                                                                                                                                                     
  │                                                                                                                                                                                                          
  ├── specs/                                          ← LIVING YAML SPECS (the books' executable form)                                                                                                       
  │   ├── _base/                                      ← base_constitution.yaml, breath_25_compact.yaml                                                                                                       
  │   ├── executive/                                                                                                                                                                                         
  │   │   ├── cfo_agent_v1.yaml                                                                                                                                                                              
  │   │   ├── synthesis_agent_v1.yaml                                                                                                                                                                        
  │   │   ├── compliance_guardian_v1.yaml                                                                                                                                                                    
  │   │   └── ...                                     ← one per chapter / book                                                                                                                             
  │   ├── family/                                                                                                                                                                                            
  │   │   ├── family_cfo_agent_v1.yaml                ← extends executive/cfo_agent_v1                                                                                                                     
  │   │   ├── household_synthesis_agent_v1.yaml                                                                                                                                                              
  │   │   ├── family_compliance_shield_v1.yaml                                                                                                                                                             
  │   │   ├── family_constitution_v1.yaml                                                                                                                                                                    
  │   │   └── ...                                                                                                                                                                                          
  │   ├── generational_legacy/                                                                                                                                                                               
  │   │   ├── 1000_year_family_compact_v1.yaml                                                                                                                                                             
  │   │   ├── legacy_guardian_agent_v1.yaml                                                                                                                                                                  
  │   │   ├── inheritance_compliance_v1.yaml                                                                                                                                                                 
  │   │   └── ...                                                                                                                                                                                            
  │   ├── education/                                                                                                                                                                                         
  │   ├── health/                                                                                                                                                                                            
  │   ├── federation/                                                                                                                                                                                      
  │   │   ├── sovereign_guild_v1.yaml
  │   │   └── inter_node_compliance_v1.yaml                                                                                                                                                                  
  │   └── INDEX.yaml                                  ← master index, version-tagged                                                                                                                         
  │                                                                                                                                                                                                          
  ├── books-public/                                   ← FREE / PROMOTIONAL CONTENT (legal under KDP)                                                                                                         
  │   ├── series_01_executive/                                                                                                                                                                               
  │   │   └── sample_chapters/                                                                                                                                                                             
  │   │       └── 01_cfos_finance_chapter_1.pdf                                                                                                                                                              
  │   ├── series_03_generational_legacy/                                                                                                                                                                     
  │   │   └── free_pilots/                                                                                                                                                                                   
  │   │       └── 1000_year_family_compact_lead_magnet.pdf                                                                                                                                                   
  │   ├── illustration_style_guide.md                  ← shared visual system                                                                                                                                
  │   └── series_map.md                                ← public roadmap                                                                                                                                      
  │                                                                                                                                                                                                          
  ├── docs/                                           ← USER-FACING DOCS (mkdocs build)                                                                                                                      
  │   ├── source/                                     ← markdown                                                                                                                                             
  │   │   ├── index.md                                                                                                                                                                                     
  │   │   ├── ascension_ladder.md                     ← the journey                                                                                                                                          
  │   │   ├── getting_started/                                                                                                                                                                             
  │   │   ├── concepts/                               ← breath-gate, default-deny, cylinder, B49                                                                                                             
  │   │   ├── roles/                                  ← per-role usage guide                                                                                                                                 
  │   │   ├── upgrading.md                                                                                                                                                                                   
  │   │   └── faq.md                                                                                                                                                                                         
  │   ├── built/                                      ← mkdocs output (gitignored or committed)                                                                                                              
  │   └── mkdocs.yml                                                                                                                                                                                         
  │                                                                                                                                                                                                          
  ├── distribution/                                   ← RELEASE ARTIFACTS + MIGRATIONS                                                                                                                       
  │   ├── releases/                                   ← versioned release notes + checksums                                                                                                                  
  │   │   ├── v0.1.0.md                                                                                                                                                                                      
  │   │   ├── v0.2.0.md                                                                                                                                                                                      
  │   │   └── ...                                                                                                                                                                                            
  │   ├── migrations/                                 ← spec/data schema migrations between versions                                                                                                       
  │   │   ├── v0.1_to_v0.2.py                                                                                                                                                                                
  │   │   └── ...                                                                                                                                                                                          
  │   └── signing_keys/                               ← public keys for release signature verification                                                                                                       
  │                                                                                                                                                                                                          
  ├── publishing/                                     ← BOOK PRODUCTION SOPS + AUTOMATION (writer-side)                                                                                                      
  │   ├── SOP_SERIALIZED_NONFICTION_v1.1.md                                                                                                                                                                  
  │   ├── SOP_KDP_PUBLISHING.md                                                                                                                                                                              
  │   ├── prep_audiobooks.py                                                                                                                                                                                 
  │   ├── editorial_board_template.md                                                                                                                                                                        
  │   └── (no manuscripts here — those go in books-vault)                                                                                                                                                    
  │                                                                                                                                                                                                          
  ├── governance/                                     ← CONSTITUTIONAL RECORD                                                                                                                              
  │   ├── decisions/                                  ← ADRs (architecture decision records)                                                                                                                 
  │   │   ├── 2026-05-08_q1-q17-sealed-staged-b.md                                                                                                                                                           
  │   │   └── ...                                                                                                                                                                                            
  │   └── seals/                                      ← KM-1176 sealed approvals per release                                                                                                                 
  │                                                                                                                                                                                                          
  ├── examples/                                       ← Onboarding examples per ladder level                                                                                                               
  │   ├── awakening/                                  ← Level 0 — minimal node bootstrap                                                                                                                     
  │   ├── executive/                                  ← Level 1 — Demo 2 walkthrough                                                                                                                         
  │   ├── family/                                     ← Level 2 — kitchen-table setup                                                                                                                        
  │   └── ...                                                                                                                                                                                                
  │                                                                                                                                                                                                          
  ├── .github/                                        ← CI/CD                                                                                                                                                
  │   ├── workflows/                                                                                                                                                                                       
  │   │   ├── test.yml                                ← run platform/tests/ + spec validation                                                                                                                
  │   │   ├── release.yml                             ← on tag: build + sign + update manifest                                                                                                               
  │   │   ├── docs.yml                                ← rebuild docs on push                                                                                                                                 
  │   │   └── constitutional_check.yml                ← Compliance-agent validates every PR                                                                                                                  
  │   └── ISSUE_TEMPLATE/                                                                                                                                                                                    
  │                                                                                                                                                                                                        
  └── CHANGELOG.md                                    ← human-readable release log                                                                                                                           
                                                                                                                                                                                                           
  Companion private repos (mangumcfo org):                                                                                                                                                                   
                                                                                                                                                                                                           
  mangumcfo/breathline-books-vault       PRIVATE — full KDP-exclusive manuscripts                                                                                                                            
  mangumcfo/six-sov.com                  PRIVATE — already done — site/marketing front-end                                                                                                                   
                                                                                                                                                                                                             
  ---                                                                                                                                                                                                        
  2. The "anybody can refresh" mechanism                                                                                                                                                                     
                                                                                                                                                                                                           
  This is the heart of your ask. Here's the flow:
                                                                                                                                                                                                             
  USER                                          breathline-federation
  ────                                          ───────────────────────                                                                                                                                      
  1. curl -sSL breathline.dev/install.sh | bash                                                                                                                                                            
                            ──────────────────▶  installer/install.sh                                                                                                                                        
                                                 ├── detect OS / hardware tier (executive vs family)                                                                                                       
                                                 ├── git clone --depth 1 --branch <latest-tag>                                                                                                               
                                                 ├── verify signatures against signing_keys/                                                                                                                 
                                                 ├── set up Python venv + deps from platform/                                                                                                                
                                                 ├── run platform/scripts/bootstrap.py                                                                                                                       
                                                 │   (Layer 0 → 1 → 2 → 3 with tier-appropriate roles)                                                                                                       
                                                 ├── generate node ECC keys (P1)                                                                                                                             
                                                 ├── seal first cylinder + B49 receipt                                                                                                                       
                                                 └── print: node_id, URL, next-step ladder                                                                                                                   
                                                                                                                                                                                                             
  2. Months later:  breathline upgrade                                                                                                                                                                       
                            ──────────────────▶  installer/upgrade.sh                                                                                                                                        
                                                 ├── fetch manifest.yaml (current_version + checksums)                                                                                                       
                                                 ├── compare to installed version
                                                 ├── show diff: new specs, new platform code, breaking changes                                                                                               
                                                 ├── ASK FOR BREATH-GATE APPROVAL (the user's own breath)                                                                                                    
                                                 ├── on approval:                                                                                                                                            
                                                 │   ├── run distribution/migrations/<from>_to_<to>.py                                                                                                       
                                                 │   ├── apply new platform/ + specs/                                                                                                                        
                                                 │   ├── run platform/tests/ to verify integrity                                                                                                             
                                                 │   ├── re-bootstrap if Layer schema changed                                                                                                                
                                                 │   └── seal upgrade cylinder + B49 receipt                                                                                                                 
                                                 └── print: new version, what changed, what to read next                                                                                                     
                                                                                                                                                                                                             
  3. New book ships:                                                                                                                                                                                         
                            ◀──────────────────  Editorial board approves Book N                                                                                                                             
                                                 Synthesis-agent extracts YAMLs from manuscript                                                                                                              
                                                 Compliance-agent validates against base constitution                                                                                                        
                                                 KM-1176 breath-seals the release                                                                                                                            
                                                 specs/<series>/<role>_v<n>.yaml pushed                                                                                                                      
                                                 manifest.yaml bumped: version + new spec entry                                                                                                              
                                                 GitHub release tagged                                                                                                                                       
                                                 (Optional) Notification to running nodes                                                                                                                    
     User runs:  breathline upgrade                                                                                                                                                                          
     → gets the new role spec                                                                                                                                                                                
     → reviews + breath-gates → role activates → ladder progresses                                                                                                                                           
                                                                                                                                                                                                             
  The manifest.yaml (the refresh anchor)                                                                                                                                                                     
                                                                                                                                                                                                             
  # breathline-federation/manifest.yaml                                                                                                                                                                      
  version: "0.2.0"                                                                                                                                                                                         
  released: "2026-05-08"
  sealed_by: "KM-1176"                                                                                                                                                                                       
  seal: "1176-INFINITY-RHO"
                                                                                                                                                                                                             
  platform:                                                                                                                                                                                                
    kernel_version: "0.2.0"                                                                                                                                                                                  
    required_python: ">=3.12"                                                                                                                                                                              
    test_count: 169                                                                                                                                                                                          
   
  specs:                                                                                                                                                                                                     
    - id: cfo_agent_v1                                                                                                                                                                                     
      series: executive
      book: 01_cfos_finance                                                                                                                                                                                  
      sha256: a4f8...
    - id: family_cfo_agent_v1                                                                                                                                                                                
      series: family                                                                                                                                                                                       
      book: family_finance_sovereignty                                                                                                                                                                       
      extends: cfo_agent_v1                                                                                                                                                                                  
      sha256: b2c7...
    # ... one entry per spec                                                                                                                                                                                 
                                                                                                                                                                                                           
  books_public:                                                                                                                                                                                              
    - 1000_year_family_compact_lead_magnet.pdf                                                                                                                                                             
      sha256: c8d9...                                                                                                                                                                                        
      series: generational_legacy                                                                                                                                                                            
                                                                                                                                                                                                             
  migrations:                                                                                                                                                                                                
    from_v0_1_0:                                                                                                                                                                                           
      script: distribution/migrations/v0.1_to_v0.2.py                                                                                                                                                        
      breaking: false
      notes: "Adds chain sentinel; auto-applies to existing nodes"                                                                                                                                           
                                                                                                                                                                                                             
  Every install / upgrade verifies this manifest against detached signatures (distribution/signing_keys/). Cryptographically anchored sovereign distribution. No central server required — just the GitHub   
  repo + signature verification.                                                                                                                                                                             
                                                                                                                                                                                                             
  ---                                                                                                                                                                                                      
  3. How books and platform co-publish
                                                                                                                                                                                                             
  Per LIVING_SPECS_YAML.md, every book ships with companion YAML specs. Here's the operational flow per release:
                                                                                                                                                                                                             
  WEEK N — book release flow:                                                                                                                                                                              
                                                                                                                                                                                                             
  📝 Manuscript editing (in mangumcfo/breathline-books-vault, PRIVATE)                                                                                                                                       
     └─ docs/SOP_SERIALIZED_NONFICTION_v1.1.md                                                                                                                                                               
                                                                                                                                                                                                             
  📋 Synthesis-agent extracts specs (per-chapter operational claims → YAML drafts)                                                                                                                           
                                                                                                                                                                                                             
  🔍 Editorial board reviews (literary + spec coherence)                                                                                                                                                     
                                                                                                                                                                                                           
  ✅ Compliance-agent validates each spec against base_constitution                                                                                                                                          
                                                                                                                                                                                                           
  🤝 KM-1176 breath-seals (governance/seals/<date>_book_<N>_release.md)                                                                                                                                      
                                                                                                                                                                                                           
  📦 Release artifacts assemble:                                                                                                                                                                             
     ├── KDP package    → uploaded to Amazon (NOT in any repo)                                                                                                                                             
     ├── Audible package → uploaded to ACX                                                                                                                                                                   
     ├── Free chapter / lead magnet → breathline-federation/books-public/                                                                                                                                    
     ├── Companion YAMLs → breathline-federation/specs/<series>/                                                                                                                                             
     └── Platform code update (if new role handler) → breathline-federation/platform/roles/<series>/                                                                                                         
                                                                                                                                                                                                             
  🏷  GitHub release tagged on breathline-federation                                                                                                                                                          
     └── manifest.yaml bumped, signed, committed                                                                                                                                                             
                                                                                                                                                                                                             
  🔔 Existing user nodes notice manifest update on next `breathline upgrade`                                                                                                                                 
     └── New specs available; user breath-gates to deploy → ladder ascends                                                                                                                                   
                                                                                                                                                                                                             
  📜 The book is published, and reading it now activates real software.                                                                                                                                      
                                                                                                                                                                                                             
  ---                                                                                                                                                                                                        
  4. Public vs private — what goes where                                                                                                                                                                   
                                                                                                                                                                                                             
  ┌─────────────────────────────────┬────────────────────────────────┬──────────────────────────────────┬─────────────────────────────────────────────┐
  │              Asset              │ Public (breathline-federation) │ Private (breathline-books-vault) │                     Why                     │                                                      
  ├─────────────────────────────────┼────────────────────────────────┼──────────────────────────────────┼─────────────────────────────────────────────┤                                                    
  │ Vision, charter, constitution   │ ✅                             │                                  │ Public-by-design                            │                                                      
  ├─────────────────────────────────┼────────────────────────────────┼──────────────────────────────────┼─────────────────────────────────────────────┤                                                    
  │ Platform code                   │ ✅                             │                                  │ Open-source kernel + paid roles per Q5      │                                                      
  ├─────────────────────────────────┼────────────────────────────────┼──────────────────────────────────┼─────────────────────────────────────────────┤                                                      
  │ YAML specs                      │ ✅                             │                                  │ "Reading specs IS activation"               │                                                      
  ├─────────────────────────────────┼────────────────────────────────┼──────────────────────────────────┼─────────────────────────────────────────────┤                                                      
  │ Free chapters / lead magnets    │ ✅                             │                                  │ Marketing                                   │                                                    
  ├─────────────────────────────────┼────────────────────────────────┼──────────────────────────────────┼─────────────────────────────────────────────┤                                                      
  │ Series map / roadmap            │ ✅                             │                                  │ Marketing + transparency                    │                                                    
  ├─────────────────────────────────┼────────────────────────────────┼──────────────────────────────────┼─────────────────────────────────────────────┤                                                      
  │ Documentation                   │ ✅                             │                                  │ User-facing                                 │
  ├─────────────────────────────────┼────────────────────────────────┼──────────────────────────────────┼─────────────────────────────────────────────┤                                                      
  │ Editorial board reviews         │ ✅                             │                                  │ Trust signal                                │                                                    
  ├─────────────────────────────────┼────────────────────────────────┼──────────────────────────────────┼─────────────────────────────────────────────┤                                                      
  │ Full manuscripts                │ ❌                             │ ✅                               │ KDP exclusivity; required to be Amazon-only │
  ├─────────────────────────────────┼────────────────────────────────┼──────────────────────────────────┼─────────────────────────────────────────────┤                                                      
  │ Final PDF builds for KDP upload │ ❌                             │ ✅                               │ Same                                        │                                                    
  ├─────────────────────────────────┼────────────────────────────────┼──────────────────────────────────┼─────────────────────────────────────────────┤                                                      
  │ Cover designs (final/)          │ ❌                             │ ✅                               │ Same                                        │                                                    
  ├─────────────────────────────────┼────────────────────────────────┼──────────────────────────────────┼─────────────────────────────────────────────┤                                                      
  │ Audible WAV masters             │ ❌                             │ ✅                               │ ACX exclusivity                             │                                                    
  ├─────────────────────────────────┼────────────────────────────────┼──────────────────────────────────┼─────────────────────────────────────────────┤                                                      
  │ Pre-launch drafts               │ ❌                             │ ✅                               │ Editorial process                           │                                                    
  └─────────────────────────────────┴────────────────────────────────┴──────────────────────────────────┴─────────────────────────────────────────────┘                                                      
                                                                                                                                                                                                           
  The breathline-books-vault private repo is where Series 1's 01_cfos_finance/v1.0/manuscript_v1.0.md etc. eventually move (or stay synced from the dev tree). KDP-exclusive content stays out of            
  breathline-federation.                                                                                                                                                                                   
                                                                                                                                                                                                             
  ---                                                                                                                                                                                                      
  5. Migration path — how to get from today to this
                                                                                                                                                                                                             
  You're not starting empty. Here's the staged plan:
                                                                                                                                                                                                             
  Phase 0 — Prep (today, ~30 min)                                                                                                                                                                            
   
  1. Decide: clear out the empty breathline-federation README and start fresh? Or preserve any existing content?                                                                                             
  2. Choose: install path → breathline.dev (a domain on six-sov.com or new) vs raw GitHub URL for v0.1                                                                                                     
  3. Confirm naming: are we keeping breathline-federation as the repo name, or renaming to e.g. breathline-platform to be clearer?                                                                           
                                                                                                                                                                                                             
  Phase 1 — Skeleton + governance (1 day)                                                                                                                                                                    
                                                                                                                                                                                                             
  - Lay down the directory structure above (mostly empty)                                                                                                                                                    
  - Drop in CHARTER.md, CONSTITUTION.md (already exist; just symlink/copy)                                                                                                                                 
  - Initial README.md with the ascension ladder + vision                                                                                                                                                     
  - LICENSE (you'll want a custom "constitutional source-available" license — I can draft)                                                                                                                 
  - .github/workflows/test.yml skeleton                                                                                                                                                                      
                                                                                                                                                                                                           
  Phase 2 — Platform import (1 day)                                                                                                                                                                          
                                                                                                                                                                                                           
  - Sync agentic_platform_seed/v1.0/ → breathline-federation/platform/                                                                                                                                       
  - Either: git subtree add (preserves history, complex) OR clean copy + initial commit (simpler)
  - Run tests in the new location to confirm 169/169 still passes                                                                                                                                            
  - First manifest.yaml with version: 0.1.0 reflecting current platform state                                                                                                                                
                                                                                                                                                                                                             
  Phase 3 — Specs catalog (1–2 days)                                                                                                                                                                         
                                                                                                                                                                                                             
  - Move/copy capstone_yaml/ → breathline-federation/specs/                                                                                                                                                  
  - Author the missing v1 specs from LIVING_SPECS_YAML.md (cfo_agent, family_cfo_agent, legacy_guardian, etc.)                                                                                             
  - INDEX.yaml ties them together by series                                                                                                                                                                  
                                                                                                                                                                                                           
  Phase 4 — Installer (2–3 days)                                                                                                                                                                             
                                                                                                                                                                                                           
  - Write installer/install.sh (curl-pipe-bash compatible)                                                                                                                                                   
  - Write installer/upgrade.sh (manifest comparison + breath-gate)
  - Set up signing keys + signature verification                                                                                                                                                             
  - Test full install + upgrade cycle on a clean machine                                                                                                                                                     
                                                                                                                                                                                                             
  Phase 5 — Public surface (ongoing)                                                                                                                                                                         
                                                                                                                                                                                                             
  - Books-public starts populating with each release                                                                                                                                                         
  - Docs site (mkdocs serve from docs/source/) deployed (similar to six-sov.com pattern)
  - First breathline upgrade works end-to-end                                                                                                                                                                
  - Tag v0.1.0 and ship                                                                                                                                                                                    
                                                                                                                                                                                                             
  Phase 6 — Decentralization (later)                                                                                                                                                                       
                                                                                                                                                                                                             
  - P3 libp2p shard exchange between nodes                                                                                                                                                                   
  - Federation discovery via Kademlia
  - Multi-node trust scoring via resonant shard similarity                                                                                                                                                   
  - Series 6 (Sovereign Guilds) becomes operationally real                                                                                                                                                   
                                                                                                                                                                                                             
  ---                                                                                                                                                                                                        
  6. The constitutional license question                                                                                                                                                                     
                                                                                                                                                                                                             
  You'll want a custom license. Standard ones miss the point:
  - MIT/Apache: too permissive — someone could fork and remove breath-gate                                                                                                                                   
  - GPL: doesn't enforce the constitutional invariants                                                                                                                                                       
  - AGPL: closer, but still allows forks that strip default-deny                                                                                                                                             
                                                                                                                                                                                                             
  Proposed: "Constitutional Source-Available License v1.0" with these clauses:                                                                                                                               
  - Source available, modification allowed                                                                                                                                                                   
  - Commercial use allowed                                                                                                                                                                                   
  - Forks must preserve the constitutional kernel (CHARTER.md + CONSTITUTION.md unchanged)                                                                                                                   
  - Forks must preserve breath-gated default-deny as a runtime invariant                                                                                                                                   
  - Forks that violate constitutional invariants forfeit license                                                                                                                                             
  - Amendment requires KM-1176 signature                                                                                                                                                                     
                                                                                                                                                                                                             
  This is novel territory. I can draft it; you decide whether to deploy.                                                                                                                                     
                                                                                                                                                                                                             
  ---                                                                                                                                                                                                        
  7. Open decisions to surface                                                                                                                                                                               
                                                                                                                                                                                                             
  These are the choices you need to make before I scaffold anything:
─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
←  ☐ Repo name  ☐ Platform sync  ☐ Books vault  ☐ Next step  ✔ Submit  →                                                                                                                                   
                                                                                                                                                                                                             
Repo name — keep as breathline-federation or rename?                                                                                                                                                         
   
❯ 1. Keep breathline-federation (Recommended)                                                                                                                                                                
     Already-created public repo. The name aligns with the multi-node federation vision (Series 6 endpoint). Distribution = federation of sovereign nodes refreshing from a canonical reference.           
  2. Rename to breathline-platform
     Narrower — emphasizes 'this repo gives you the platform.' Less aligned with the federation vision but clearer to first-time visitors.
  3. Split: breathline-platform (this repo) + breathline-federation (governance)
     Two public repos: one for the runnable code/specs (breathline-platform), one for the federation governance (charter/constitution/decisions/seals). Cleaner separation; more coordination.
  4. Type something.

How should the platform code get from agentic_platform_seed/ INTO breathline-federation/platform/?                                                                                                           
   
❯ 1. Git subtree (preserves full history)                                                                                                                                                                    
     git subtree add the agentic_platform_seed contents. The 8 commits of platform history (Phase 1 through Q13 close) come along. Bigger initial commit, cleaner provenance.                              
  2. Clean copy + initial commit (Recommended)
     cp -R, then commit fresh. New repo's history starts at v0.1.0. Provenance lives in CHANGELOG.md and the agentic_platform_seed origin reference. Faster, simpler.
  3. Git submodule pointing at the existing location                            
     breathline-federation/platform is a submodule of constitution-federation/...platform. Tightly coupled; user clones get auto-pulled. Adds clone complexity.                               
  4. Type something.

←  ☒ Repo name  ☒ Platform sync  ☐ Books vault  ☐ Next step  ✔ Submit  →                                                                                                                                   
                                                                                                                                                                                                             
Books-vault — set up as a private companion repo today?                                                                                                                                                      
   
❯ 1. Yes — create mangumcfo/breathline-books-vault private now                                                                                                                                               
     I'll create the private repo and lay down the directory structure (series_01_executive/01_cfos_finance/v1.0/...). You move actual manuscripts in when you want.                                       
  2. Defer — books stay in constitution-federation/ for now
     Don't create the vault repo today. Books continue to live where they are; we revisit after breathline-federation is operational.                                
  3. Create + migrate first 5 books (already-shipped Series 1)                  
     Create the vault AND move the 5 already-published books in (01_cfos_finance through 12_agentic_enterprise as-shipped). Establishes the pattern.                                          
  4. Type something.

←  ☒ Repo name  ☒ Platform sync  ☒ Books vault  ☐ Next step  ✔ Submit  →                                                                                                                                   
                                                                                                                                                                                                             
What's the next concrete move you want me to make?                                                                                                                                                           
   
❯ 1. Scaffold breathline-federation skeleton (empty dirs + README + manifest stub)                                                                                                                           
     I lay down the full directory structure, write the new README, drop manifest.yaml v0.1.0 stub. ~30 min work, gives you a navigable repo to start filling in.                                          
  2. Write a formal architecture doc first (this proposal as a versioned ADR)
     Promote this conversation into governance/decisions/2026-05-08_breathline-federation-architecture.md so the choice is sealed before scaffolding. Slower, cleaner provenance.
  3. Write the installer + manifest mechanics first                             
     Skip the directory scaffolding, jump to installer/install.sh + installer/upgrade.sh + manifest.yaml as the first deliverable. Proves the user-refresh loop works before building everything around it.
  4. Pause — something to discuss/refine first
     There's a piece of this proposal that needs more thought before I scaffold.                                                                                                                             
  5. Type something.

  
