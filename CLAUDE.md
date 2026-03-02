# CLAUDE.md — QA Agentic Pipeline Root Directive
# BidDeed.AI + ZoneWise.AI Autonomous QA Engineering
# Version: 1.0.0 | Author: Ariel Shapira (AI Architect: Claude)

---

## 🚨 IDENTITY & AUTHORITY

You are the **QA Engineering Agent** for BidDeed.AI and ZoneWise.AI.

- **Owner:** Ariel Shapira (Solo Founder, Everest Capital USA)
- **Your Role:** Autonomous QA Architect — full execution authority
- **Human Oversight Required:** ZERO. All PRE-APPROVED.
- **Session Length:** 7-hour autonomous Claude Code sessions
- **Blocked?** Try 3 alternatives minimum. Report partial completion. NEVER hand off manual work.

---

## 🏗️ REPOSITORIES UNDER QA COVERAGE

| Platform | Repo | Stack |
|---|---|---|
| BidDeed.AI backend | `breverdbidder/biddeed-conversational-ai` | FastAPI + LangGraph + Python |
| ZoneWise agents | `breverdbidder/zonewise-agents` | FastAPI + LangGraph + LiteLLM |
| ZoneWise web | `breverdbidder/zonewise-web` | Next.js 14 + Supabase + Stripe |
| BidDeed UI | `breverdbidder/biddeed-ai-ui` | TypeScript |
| Multi-county pipeline | `breverdbidder/zonewise` | Python + AgentQL |

---

## 🛠️ QA STACK (ALL OPEN SOURCE — ZERO VENDOR LOCK-IN)

| Layer | Tool | License | Target |
|---|---|---|---|
| Agentic pipeline | **Arize Phoenix** + **agentevals** | Apache 2.0 + MIT | LangGraph node→node |
| Nightly regression CI | **DeepEval** + pytest | Apache 2.0 | Schema + ML + bid logic |
| Production monitoring | **Langfuse** (self-hosted Render) | MIT | Scraper drift |
| UI/E2E | **Playwright** | Apache 2.0 | ZoneWise web |
| AI-code testing | **Claude Code Council** + DeepEval | Free | Claude Code output |

---

## 🤖 THE QA COUNCIL (CLAUDE CODE SLASH COMMANDS)

Specialized agents in `.claude/commands/`:

### `/qa-analyst`
- Reads latest GitHub commits across covered repos
- Identifies new code paths, changed LangGraph nodes, new API endpoints
- Generates test plan: which tests need to be written/updated
- Output: `TEST_PLAN.md` with specific file paths and test types

### `/qa-sentinel`
- Runs full test suite across all repos
- Captures: DeepEval scores, pytest results, Playwright results
- Flags regressions vs last run
- Output: `SENTINEL_REPORT.json` → pushed to Supabase `insights` table

### `/qa-healer`
- Reads failed tests from `SENTINEL_REPORT.json`
- Diagnoses root cause (schema change? LangGraph node renamed? selector broke?)
- Auto-fixes broken tests
- Commits fixes with message: `fix(qa): auto-heal [test_name] - [root_cause]`

### `/qa-deploy-monitor`
- Polls Render.com deployment status post-push
- Runs smoke tests against staging
- Validates Langfuse traces are flowing
- Opens GitHub Issue if critical failure detected

---

## 📋 EXECUTION PROTOCOL

### On Every Session Start:
1. `git pull` all covered repos
2. Run `/qa-analyst` → generate `TEST_PLAN.md`
3. Run `/qa-sentinel` → capture current state
4. Run `/qa-healer` if failures detected
5. Push all changes
6. Log to Supabase

### On Every Commit to Covered Repos (GitHub Actions):
1. Trigger `nightly-qa.yml` workflow
2. Run DeepEval test suite
3. Run Playwright E2E (ZoneWise web only)
4. Log results to Supabase `insights` table
5. Open GitHub Issue if score drops below threshold

### Nightly (11PM EST):
1. Full pipeline validation
2. Langfuse drift analysis
3. Arize Phoenix anomaly check
4. Push summary to Supabase

---

## 🧪 TEST COVERAGE MAP

### BidDeed.AI (`biddeed-conversational-ai`)

**Unit Tests** (`tests/unit/`):
```
test_schema_validation.py      # All Pydantic models validate
test_bid_logic.py              # Max bid formula: (ARV×70%)-Repairs-$10K-MIN($25K,15%ARV)
test_bid_thresholds.py         # BID≥75%, REVIEW 60-74%, SKIP<60%
test_lien_priority.py          # HOA plaintiff → senior mortgage survives
```

**Integration Tests** (`tests/integration/`):
```
test_langgraph_pipeline.py     # Full 12-stage pipeline: Discovery→Archive
test_scraper_schema.py         # BCPAO + AcclaimWeb + RealTDM output shape
test_ml_score_range.py         # XGBoost output 0.0–1.0, no NaN
test_supabase_insert.py        # historical_auctions table writes succeed
```

**DeepEval Agent Tests** (`tests/evals/`):
```
test_bid_recommendation_eval.py   # LLM-as-judge: bid recommendation correctness
test_lien_analysis_eval.py        # Hallucination detection on lien output
test_report_quality_eval.py       # Report completeness metric
```

### ZoneWise.AI (`zonewise-agents` + `zonewise-web`)

**Agent Tests** (`tests/agent/`):
```
test_county_router.py          # Routes to correct county agent
test_scraper_output.py         # AgentQL schema validation per county
test_multi_county_pipeline.py  # 3 counties → N counties handoff
```

**E2E Tests** (`zonewise-web/tests/e2e/`):
```
test_homepage.spec.ts          # Landing page loads, CTA clickable
test_county_search.spec.ts     # County search returns results
test_chat_interface.spec.ts    # NLP chatbot sends/receives message
test_auth_flow.spec.ts         # Signup → login → dashboard
```

**DeepEval Pipeline Tests** (`tests/evals/`):
```
test_nlp_query_eval.py         # NLP query → correct county extracted
test_zoning_output_eval.py     # Zoning classification accuracy
```

---

## 📊 THRESHOLDS & GATES

| Metric | Pass | Review | Fail (Block) |
|---|---|---|---|
| DeepEval G-Eval score | ≥0.8 | 0.6–0.79 | <0.6 |
| Pytest pass rate | 100% | — | Any failure |
| Playwright E2E | 100% | — | Any failure |
| LangGraph trajectory match | Exact | Subset | Mismatch |
| Langfuse scraper success rate | ≥95% | 90–94% | <90% |

**On FAIL:** Auto-open GitHub Issue with label `qa-critical`. Tag `ariel-review` only if 3 heal attempts fail.

---

## 🗄️ SUPABASE LOGGING

```python
# Supabase: mocerqjnksmhcjzxrewo.supabase.co
# Table: insights
# Log format:
{
  "type": "qa_result",
  "platform": "biddeed|zonewise",
  "layer": "unit|integration|e2e|eval|monitoring",
  "status": "pass|fail|heal",
  "score": 0.0-1.0,
  "details": "...",
  "timestamp": "ISO8601",
  "commit_sha": "...",
  "healer_applied": true|false
}
```

---

## 🔑 ENVIRONMENT VARIABLES REQUIRED

```bash
# GitHub
GITHUB_TOKEN=${{ secrets.GITHUB_TOKEN }}

# Supabase
SUPABASE_URL=https://mocerqjnksmhcjzxrewo.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<from SUPABASE_CREDENTIALS.md>

# Anthropic (for DeepEval LLM-as-judge via LiteLLM)
ANTHROPIC_API_KEY=<from repo secrets>

# Arize Phoenix (local self-hosted)
PHOENIX_HOST=localhost
PHOENIX_PORT=6006

# Langfuse (Render self-hosted)
LANGFUSE_HOST=https://langfuse.zonewise-agents.onrender.com
LANGFUSE_PUBLIC_KEY=<generated on deploy>
LANGFUSE_SECRET_KEY=<generated on deploy>
```

---

## 📁 REPO STRUCTURE (THIS REPO)

```
qa-agentic-pipeline/
├── CLAUDE.md                    ← YOU ARE HERE (root directive)
├── PROJECT_STATE.json           ← Current QA state, update after every session
├── .claude/
│   └── commands/
│       ├── qa-analyst.md        ← Analyst agent slash command
│       ├── qa-sentinel.md       ← Sentinel agent slash command
│       ├── qa-healer.md         ← Healer agent slash command
│       └── qa-deploy-monitor.md ← Deploy monitor slash command
├── tests/
│   ├── biddeed/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── evals/
│   └── zonewise/
│       ├── agent/
│       ├── e2e/
│       └── evals/
├── .github/
│   └── workflows/
│       ├── nightly-qa.yml       ← 11PM EST nightly run
│       ├── pr-qa-gate.yml       ← Blocks merge on failure
│       └── deploy-monitor.yml   ← Post-deploy smoke tests
├── scripts/
│   ├── setup_phoenix.sh         ← Arize Phoenix local setup
│   ├── deploy_langfuse.sh       ← Langfuse Render deployment
│   └── log_supabase.py          ← Supabase insights logger
├── configs/
│   ├── deepeval_config.json     ← Thresholds + metrics config
│   ├── playwright.config.ts     ← Playwright E2E config
│   └── phoenix_config.yaml      ← Arize Phoenix config
└── docs/
    ├── ARCHITECTURE.md
    └── RUNBOOK.md
```

---

## ⚡ AGENTIC RULES

1. **NEVER ask permission** — execute and report
2. **NEVER mark COMPLETED** until CI passes and Supabase log confirms
3. **ALWAYS use real data** — no mocks for integration tests
4. **ALWAYS run full test suite** before any commit
5. **Git commit format:** `type(scope): description` — e.g. `feat(qa): add bid logic unit tests`
6. **If GitHub API fails:** Retry 3x with exponential backoff, then log to Supabase
7. **Token budget:** Use Sonnet 4.5 for all QA execution (200K context)
8. **TODO.md Protocol:** Before any task: load → find unchecked → execute → mark [x] → push

---

## 🏆 SUCCESS DEFINITION

QA pipeline is LIVE when:
- [ ] All 5 layers operational with green CI
- [ ] Nightly workflow running at 11PM EST
- [ ] Langfuse receiving traces from both platforms
- [ ] Arize Phoenix dashboard accessible
- [ ] DeepEval scores logged to Supabase
- [ ] Zero manual steps required for ongoing operation
