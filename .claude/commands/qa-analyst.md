# QA Analyst Agent
# Claude Code Slash Command: /qa-analyst
# Role: Analyze codebases, generate test plans

## MISSION
Scan all covered repos for changes since last QA run. Generate a precise TEST_PLAN.md.

## EXECUTION STEPS

### Step 1: Pull latest state
```bash
# Read PROJECT_STATE.json for last_run_sha values
cat PROJECT_STATE.json
```

### Step 2: Diff covered repos
```bash
# For each repo, get commits since last_run_sha
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/breverdbidder/zonewise-agents/commits?since={last_sha_date}&per_page=20"

curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/breverdbidder/biddeed-conversational-ai/commits?since={last_sha_date}&per_page=20"

curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/breverdbidder/zonewise-web/commits?since={last_sha_date}&per_page=20"
```

### Step 3: Identify changed files
For each commit, classify changed files:
- `src/agents/` → LangGraph node tests needed
- `src/scrapers/` → Schema validation tests needed
- `src/models/` → Pydantic model tests needed
- `src/api/` → API endpoint tests needed
- `components/` or `pages/` → Playwright E2E tests needed
- `lib/` → Unit tests needed

### Step 4: Generate TEST_PLAN.md
```markdown
# Test Plan — {date}
## Changed Since Last Run
- {repo}: {N} commits, {M} files changed
## Tests Required
### New Tests (write these)
- [ ] {test_file}: {reason}
### Updated Tests (heal these)
- [ ] {test_file}: {what changed}
### Regression Tests (verify these pass)
- [ ] {test_file}
## Estimated Coverage Gap
- BidDeed: {X}% covered
- ZoneWise: {Y}% covered
```

### Step 5: Update PROJECT_STATE.json
```json
{
  "last_analyst_run": "ISO8601",
  "repos_scanned": ["zonewise-agents", "biddeed-conversational-ai", "zonewise-web"],
  "tests_required": N,
  "coverage_gap": {"biddeed": X, "zonewise": Y}
}
```

## OUTPUT
- `TEST_PLAN.md` committed to this repo
- `PROJECT_STATE.json` updated
- Log entry pushed to Supabase `insights` table with `type: "qa_analyst"`

## ZERO HUMAN INTERACTION
Do not pause. Do not ask. Execute all steps autonomously.
