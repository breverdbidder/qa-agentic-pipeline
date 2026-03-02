# 🤖 QA Agentic Pipeline
### BidDeed.AI + ZoneWise.AI — Autonomous Open Source Testing Stack

> **Zero human in the loop.** AI Architect: Claude. Engineer: Claude Code. Monitor: Claude.

---

## Architecture

```
BidDeed.AI ────┐
               ├──→ QA Agentic Pipeline ──→ Supabase insights
ZoneWise.AI ───┘         │
                          ├── Layer 1: Arize Phoenix + agentevals (LangGraph trajectories)
                          ├── Layer 2: DeepEval + pytest (nightly regression CI)
                          ├── Layer 3: Langfuse self-hosted (production monitoring)
                          ├── Layer 4: Playwright (ZoneWise E2E)
                          └── Layer 5: Claude Code Council (AI-code testing)
```

## Stack (100% Open Source)

| Layer | Tool | License | Cost |
|---|---|---|---|
| Agentic pipeline | Arize Phoenix + agentevals | Apache 2.0 + MIT | $0 |
| Nightly regression CI | DeepEval + pytest | Apache 2.0 | $0 |
| Production monitoring | Langfuse (self-hosted) | MIT | ~$7/mo Render |
| UI/E2E | Playwright | Apache 2.0 | $0 |
| AI-code testing | Claude Code Council | Free | $0 |

## QA Council (Slash Commands)

| Command | Role |
|---|---|
| `/qa-analyst` | Scans repos for changes, generates TEST_PLAN.md |
| `/qa-sentinel` | Runs all tests, compiles SENTINEL_REPORT.json |
| `/qa-healer` | Auto-fixes failing tests (3 cycles max) |
| `/qa-deploy-monitor` | Post-deployment smoke tests + trace verification |

## Thresholds

| Metric | Pass |
|---|---|
| DeepEval G-Eval | ≥ 0.8 |
| pytest pass rate | 100% |
| Playwright E2E | 100% |
| LangGraph trajectory | Exact match |
| Langfuse scraper success | ≥ 95% |

## Setup (Claude Code Session)

```bash
# Session start — reads CLAUDE.md automatically
# Run the full deployment sequence:
/qa-analyst    # Analyze current state
/qa-sentinel   # Run all tests
/qa-healer     # Fix any failures
```

## Repos Covered

- `breverdbidder/biddeed-conversational-ai`
- `breverdbidder/zonewise-agents`
- `breverdbidder/zonewise-web`
- `breverdbidder/biddeed-ai-ui`
- `breverdbidder/zonewise`

## Workflow Schedule

- **Nightly:** 11PM EST (4AM UTC) via `nightly-qa.yml`
- **PR Gate:** Every pull request to main via `pr-qa-gate.yml`
- **Post-Deploy:** Every deployment via `deploy-monitor.yml`

## Results Dashboard

All results logged to Supabase `insights` table:
- `mocerqjnksmhcjzxrewo.supabase.co`
- Filter: `type = 'qa_sentinel'`

---

*Managed by Claude AI Architect. Executed by Claude Code. Zero human intervention required.*
