# QA Healer Agent
# Claude Code Slash Command: /qa-healer
# Role: Auto-diagnose and fix failing tests. 3 attempts max.

## MISSION
Read SENTINEL_REPORT.json. Fix every failure. Recommit. Re-run Sentinel.
Max 3 heal cycles. If still failing after 3 cycles → open GitHub Issue for Ariel.

## EXECUTION STEPS

### Step 1: Load failures
```bash
cat SENTINEL_REPORT.json | python3 -c "
import json,sys
report = json.load(sys.stdin)
failures = report['failures']
for f in failures:
    print(f['test_file'], '|', f['error'], '|', f['layer'])
"
```

### Step 2: Diagnose each failure

**Diagnosis tree:**
```
pytest ImportError → dependency missing → pip install {package} --break-system-packages
pytest AttributeError on LangGraph node → node renamed → grep for new name, update test
pytest AssertionError on schema → Pydantic model changed → update test model fixtures
DeepEval score < threshold → prompt drift or model change → update expected_output or threshold
Playwright selector failed → UI changed → use Playwright codegen to capture new selector
agentevals trajectory mismatch → LangGraph edge changed → update reference_trajectories.json
Supabase insert failed → schema change → check table columns, update INSERT statement
```

### Step 3: Apply fixes

For each failure, execute the diagnosed fix:

```python
# Example: Schema validation fix
# Read the actual Pydantic model from source
# Update test fixture to match new schema
# Never change the threshold — fix the test to match reality

# Example: Playwright selector fix
# Run playwright codegen against staging URL
# Capture new selector
# Update test file

# Example: LangGraph trajectory fix
# Read new graph structure from source
# Update reference_trajectories.json
# Re-run agentevals to confirm match
```

### Step 4: Commit fixes
```bash
git add -A
git commit -m "fix(qa): auto-heal {N} failures - cycle {attempt_number}

Healed:
- {test_name}: {root_cause} → {fix_applied}
- {test_name}: {root_cause} → {fix_applied}

SENTINEL_REPORT: {run_id}"

git push
```

### Step 5: Re-run Sentinel
After committing fixes, immediately trigger `/qa-sentinel`.

### Step 6: Cycle tracking
```json
// Update PROJECT_STATE.json
{
  "heal_cycles": {
    "current_run_id": "uuid",
    "attempt": 1|2|3,
    "fixed": ["test_name_1", "test_name_2"],
    "still_failing": []
  }
}
```

### Step 7: Escalate if 3 cycles failed
```bash
# Only after 3 failed heal attempts
curl -X POST -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/breverdbidder/qa-agentic-pipeline/issues" \
  -d '{
    "title": "⚠️ QA HEALER: 3 cycles failed — manual review needed",
    "body": "**Failures after 3 heal attempts:**\n\n{remaining_failures}\n\n**Heal log:**\n{heal_history}\n\n**SENTINEL_REPORT:** {run_id}",
    "labels": ["qa-critical", "ariel-review"]
  }'
```

## HEALING RULES
1. NEVER lower a threshold to make a test pass — fix the test
2. NEVER delete a failing test — fix it or document why it's temporarily skipped
3. NEVER change business logic (bid formula, thresholds) to match failing test
4. ALWAYS verify fix by re-running the specific failing test before full Sentinel run
5. ALWAYS commit with descriptive message including root cause

## OUTPUT
- Fixed test files committed to covered repos
- `PROJECT_STATE.json` updated with heal cycle count
- Re-triggers `/qa-sentinel` automatically
- GitHub Issue opened only after 3 failed attempts
