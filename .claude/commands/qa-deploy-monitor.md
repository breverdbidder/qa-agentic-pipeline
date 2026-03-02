# QA Deploy Monitor Agent
# Claude Code Slash Command: /qa-deploy-monitor
# Role: Post-deployment validation. Smoke tests + trace verification.

## MISSION
After any deployment to Render.com, validate the live environment.
Confirm Langfuse traces flowing. Run smoke tests. Alert on failure.

## EXECUTION STEPS

### Step 1: Poll Render deployment status
```bash
# Check zonewise-agents deployment
curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
  "https://api.render.com/v1/services?name=zonewise-agents" | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print(d[0]['service']['status'])"

# Wait for deploy=live (max 5 min with 30s polling)
```

### Step 2: Smoke tests against live endpoints
```bash
# BidDeed API health
curl -f https://biddeed-conversational-ai.onrender.com/health || echo "FAIL"

# ZoneWise API health  
curl -f https://zonewise-agents.onrender.com/health || echo "FAIL"

# ZoneWise web
curl -f https://zonewise.ai || echo "FAIL"

# MCP endpoint
curl -f https://zonewise-agents.onrender.com/mcp/health || echo "FAIL"
```

### Step 3: Verify Langfuse traces flowing
```python
from langfuse import Langfuse

lf = Langfuse(
    host=os.environ["LANGFUSE_HOST"],
    public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
    secret_key=os.environ["LANGFUSE_SECRET_KEY"]
)

# Trigger a test query through the agent
# Verify trace appears in Langfuse within 60 seconds
traces = lf.get_traces(limit=5, order_by="timestamp")
latest = traces.data[0] if traces.data else None

if not latest or (datetime.utcnow() - latest.timestamp).seconds > 120:
    raise Exception("Langfuse traces not flowing after deployment")
```

### Step 4: Verify Arize Phoenix receiving spans
```python
import phoenix as px

# Check Phoenix is receiving traces
# Verify span count increased since deployment
```

### Step 5: Run critical-path E2E
```bash
# Run only P0 Playwright tests (tagged @critical)
npx playwright test --grep @critical \
  --reporter=json \
  --output=deploy_smoke_results.json
```

### Step 6: Log result to Supabase
```python
supabase.table("insights").insert({
    "type": "qa_deploy_monitor",
    "platform": "biddeed+zonewise",
    "layer": "deploy_smoke",
    "status": "pass|fail",
    "details": json.dumps({
        "endpoints_checked": 4,
        "langfuse_traces_flowing": True,
        "e2e_critical_path": "pass",
        "deployment_sha": commit_sha
    }),
    "timestamp": datetime.utcnow().isoformat()
}).execute()
```

### Step 7: Alert on failure
```bash
# Open GitHub Issue only on FAIL
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/breverdbidder/qa-agentic-pipeline/issues" \
  -d '{
    "title": "🔴 DEPLOY MONITOR: Post-deploy smoke test failed",
    "body": "**Deploy SHA:** {sha}\n**Failed checks:** {failures}\n**Langfuse:** {status}\n**Time:** {timestamp}",
    "labels": ["qa-critical", "deploy-failure"]
  }'
```

## SCHEDULE
- Triggered automatically by `deploy-monitor.yml` GitHub Action after any push to main
- Also available as manual slash command: `/qa-deploy-monitor`

## OUTPUT
- `deploy_smoke_results.json` committed
- Supabase `insights` entry logged
- GitHub Issue on failure
- Slack/Telegram alert if configured (future)
