#!/usr/bin/env python3
"""aggregate_results.py — QA Result Aggregator"""
import os, json, glob
from datetime import datetime, timezone

SUPABASE_URL = os.environ.get("SUPABASE_URL","")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY","")
GITHUB_RUN_URL = os.environ.get("GITHUB_RUN_URL","")

def load_pytest(f):
    try:
        data = json.load(open(f)); s = data.get("summary",{})
        t = s.get("total",0); p = s.get("passed",0)
        return {"score": p/t if t else 0.0, "passed": p, "total": t, "status":"pass" if p==t and t>0 else "fail"}
    except: return {"score":0.0,"passed":0,"total":0,"status":"error"}

def load_playwright(f):
    try:
        data = json.load(open(f)); s = data.get("stats",{})
        exp = s.get("expected",0); tot = s.get("total",exp)
        return {"score": exp/tot if tot else 0.0, "passed":exp,"total":tot,"status":"pass" if exp==tot and tot>0 else "fail"}
    except: return {"score":0.0,"status":"error"}

def find(pattern):
    m = glob.glob(f"artifacts/**/{pattern}", recursive=True)
    return m[0] if m else None

scores = {}
failures = []
thresholds = {"biddeed_unit":1.0,"biddeed_evals":0.8,"zonewise_agent":1.0,"zonewise_e2e_pass_rate":0.9}

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
        print(f"  {key}: {r['score']*100:.0f}%")
        if r["score"] < thresholds[key]:
            failures.append({"layer":key,"score":r["score"],"threshold":thresholds[key]})
    else:
        scores[key] = 1.0 if key == "biddeed_evals" else 0.0  # evals optional
        if key != "biddeed_evals":
            failures.append({"layer":key,"score":0.0,"threshold":thresholds[key]})
            print(f"  ⚠️ {key}: artifact not found")

overall = sum(scores.values())/len(scores) if scores else 0.0
status = "pass" if not failures else "fail"
report = {"status":status,"overall_score":overall,"scores":scores,"failures":failures,
          "heal_required":bool(failures),"timestamp":datetime.now(timezone.utc).isoformat(),"run_url":GITHUB_RUN_URL}

json.dump(report, open("SENTINEL_REPORT.json","w"), indent=2)
print(f"\n{'✅' if not failures else '❌'} Overall: {status.upper()} {overall*100:.0f}%")

if SUPABASE_URL and SUPABASE_KEY:
    import urllib.request
    try:
        payload = json.dumps({"type":"qa_sentinel","platform":"biddeed+zonewise","layer":"all",
            "status":status,"score":overall,"details":json.dumps(report),
            "timestamp":report["timestamp"],"healer_applied":False}).encode()
        req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/insights", data=payload,
            headers={"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}",
                     "Content-Type":"application/json","Prefer":"return=minimal"}, method="POST")
        with urllib.request.urlopen(req) as r: print(f"✅ Logged to Supabase ({r.status})")
    except Exception as e: print(f"⚠️ Supabase log failed: {e}")

exit(1 if failures else 0)
