# QA Sentinel Agent
# Claude Code Slash Command: /qa-sentinel
# Role: Run all tests, capture results, flag regressions

## MISSION
Execute every test in the QA pipeline. Capture all results.
Block deployment if ANY critical threshold is breached.

## EXECUTION STEPS

### Step 1: Install dependencies
```bash
pip install deepeval pytest pytest-asyncio arize-phoenix agentevals langfuse supabase --break-system-packages
cd zonewise-web && npm install @playwright/test && npx playwright install chromium
```

### Step 2: Run BidDeed DeepEval suite
```bash
cd /qa-agentic-pipeline/tests/biddeed

# Unit tests
pytest unit/ -v --tb=short --json-report --json-report-file=results_unit.json

# Integration tests  
pytest integration/ -v --tb=short -m "not scraper" --json-report --json-report-file=results_integration.json

# DeepEval eval tests
deepeval test run evals/ --output-file results_evals.json
```

### Step 3: Run ZoneWise agent suite
```bash
cd /qa-agentic-pipeline/tests/zonewise

# Agent tests
pytest agent/ -v --tb=short --json-report --json-report-file=results_agent.json

# DeepEval eval tests
deepeval test run evals/ --output-file results_evals.json
```

### Step 4: Run Playwright E2E
```bash
cd zonewise-web
npx playwright test tests/e2e/ --reporter=json --output=../qa-agentic-pipeline/tests/zonewise/results_e2e.json
```

### Step 5: Run agentevals LangGraph trajectory check
```python
from agentevals.graph_trajectory.strict import graph_trajectory_strict_match
# Load reference trajectories from configs/reference_trajectories.json
# Compare against latest runs captured via Langfuse traces
# Score each node→node handoff
```

### Step 6: Compile SENTINEL_REPORT.json
```json
{
  "run_id": "uuid",
  "timestamp": "ISO8601",
  "commit_sha": {"biddeed": "...", "zonewise": "..."},
  "results": {
    "biddeed_unit": {"pass": N, "fail": M, "score": 0.0-1.0},
    "biddeed_integration": {"pass": N, "fail": M, "score": 0.0-1.0},
    "biddeed_evals": {"deepeval_score": 0.0-1.0, "metrics": {}},
    "zonewise_agent": {"pass": N, "fail": M, "score": 0.0-1.0},
    "zonewise_e2e": {"pass": N, "fail": M, "score": 0.0-1.0},
    "zonewise_evals": {"deepeval_score": 0.0-1.0, "metrics": {}},
    "langgraph_trajectory": {"match": true|false, "nodes_checked": N}
  },
  "thresholds": {
    "deepeval_pass": 0.8,
    "pytest_pass_rate": 1.0,
    "e2e_pass_rate": 1.0
  },
  "overall_status": "PASS|FAIL|HEAL_REQUIRED",
  "failures": [],
  "heal_required": true|false
}
```

### Step 7: Log to Supabase
```python
import os
from supabase import create_client

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
supabase.table("insights").insert({
    "type": "qa_sentinel",
    "platform": "biddeed+zonewise",
    "layer": "full_suite",
    "status": overall_status,
    "score": overall_score,
    "details": json.dumps(sentinel_report),
    "timestamp": datetime.utcnow().isoformat()
}).execute()
```

### Step 8: Open GitHub Issue if FAIL
```bash
# Only if overall_status == "FAIL" and heal_required == true
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/breverdbidder/qa-agentic-pipeline/issues" \
  -d '{
    "title": "🚨 QA SENTINEL: Critical failures detected [{date}]",
    "body": "...",
    "labels": ["qa-critical"]
  }'
```

## THRESHOLDS
- DeepEval G-Eval ≥ 0.8 → PASS
- Pytest 100% pass rate → PASS
- Playwright 100% pass rate → PASS
- LangGraph trajectory exact match → PASS
- Langfuse scraper success ≥ 95% → PASS
- ANY below threshold → trigger `/qa-healer`

## OUTPUT
- `SENTINEL_REPORT.json` committed to this repo
- Supabase `insights` entry logged
- GitHub Issue opened on FAIL (after 3 heal attempts)
