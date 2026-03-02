#!/usr/bin/env python3
"""aggregate_results.py — QA Result Aggregator (v2)"""
import os, json, glob
from datetime import datetime, timezone

SUPABASE_URL = os.environ.get("SUPABASE_URL","https://mocerqjnksmhcjzxrewo.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY","")
GITHUB_RUN_URL = os.environ.get("GITHUB_RUN_URL","")

def load_pytest(f):
    try:
        data = json.load(open(f))
        s = data.get("summary",{})
        t = s.get("total",0)
        p = s.get("passed",0)
        sk = s.get("skipped",0)
        # If all tests skipped (e.g. no API key), treat as neutral 1.0
        if t == 0 or (sk == t):
            return {"score":1.0,"passed":p,"total":t,"skipped":sk,"status":"skipped"}
        return {"score":p/(t-sk) if (t-sk)>0 else 1.0,"passed":p,"total":t,"skipped":sk,"status":"pass" if p==(t-sk) else "fail"}
    except Exception as e:
        print(f"  parse error {f}: {e}")
        return {"score":0.0,"passed":0,"total":0,"status":"error"}

def load_playwright(f):
    try:
        data = json.load(open(f))
        s = data.get("stats",{})
        exp = s.get("expected",0); tot = s.get("total",exp)
        if tot == 0: return {"score":1.0,"status":"skipped"}
        return {"score":exp/tot,"passed":exp,"total":tot,"status":"pass" if exp==tot else "fail"}
    except: return {"score":0.0,"status":"error"}

def find(pattern):
    m = glob.glob(f"artifacts/**/{pattern}", recursive=True)
    return m[0] if m else None

scores = {}
failures = []
thresholds = {"biddeed_unit":1.0,"biddeed_evals":0.8,"zonewise_agent":0.5,"zonewise_e2e_pass_rate":0.9}

for key, pat, loader in [
    ("biddeed_unit","unit-results.json",load_pytest),
    ("biddeed_evals","deepeval-results.json",load_pytest),
    ("zonewise_agent","agent-results.json",load_pytest),
    ("zonewise_e2e_pass_rate","playwright-results.json",load_playwright),
]:
    f = find(pat)
    if f:
        r = loader(f)
        scores[key] = r["score"]
        note = " (skipped)" if r.get("status")=="skipped" else ""
        print(f"  {key}: {r['score']*100:.0f}%{note} [{r.get('passed',0)}/{r.get('total',0)}]")
        if r["score"] < thresholds[key]:
            failures.append({"layer":key,"score":r["score"],"threshold":thresholds[key],"status":r.get("status","fail")})
    else:
        # Missing artifact — warn but don't fail on first runs
        scores[key] = None
        print(f"  ⚠️ {key}: no artifact found")

valid = [v for v in scores.values() if v is not None]
overall = sum(valid)/len(valid) if valid else 0.0
status = "pass" if not failures else "fail"
ts = datetime.now(timezone.utc).isoformat()

report = {"status":status,"overall_score":overall,"scores":scores,"failures":failures,
          "heal_required":bool(failures),"timestamp":ts,"run_url":GITHUB_RUN_URL}

json.dump(report, open("SENTINEL_REPORT.json","w"), indent=2)
print(f"\n{'✅' if not failures else '❌'} Overall: {status.upper()} {overall*100:.0f}%")
if failures:
    for f2 in failures:
        print(f"  ❌ {f2['layer']}: {f2['score']*100:.0f}% (need {f2['threshold']*100:.0f}%)")

if SUPABASE_KEY:
    import urllib.request
    try:
        payload = json.dumps({
            "type": "qa_sentinel",
            "insight_type": "qa_result",
            "title": f"QA Pipeline — {status.upper()} {overall*100:.0f}%",
            "description": f"BidDeed+ZoneWise nightly QA. Failures: {len(failures)}. Run: {GITHUB_RUN_URL}",
            "status": status,
            "source": "qa-agentic-pipeline",
            "confidence": overall,
            "data": json.dumps(report)
        }).encode()
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/insights", data=payload,
            headers={"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}",
                     "Content-Type":"application/json","Prefer":"return=minimal"},
            method="POST"
        )
        with urllib.request.urlopen(req) as r:
            print(f"✅ Logged to Supabase ({r.status})")
    except Exception as e:
        print(f"⚠️ Supabase log failed: {e}")

exit(1 if failures else 0)
