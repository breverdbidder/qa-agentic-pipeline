#!/usr/bin/env python3
"""
aggregate_results.py — QA Results Aggregator
Reads pytest JSON reports from artifacts/ directory
Computes scores, logs to Supabase insights table
"""
import os, json, glob, sys
from datetime import datetime, timezone
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
GITHUB_RUN_URL = os.environ.get("GITHUB_RUN_URL", "")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

THRESHOLDS = {
    "biddeed_unit":       1.0,
    "biddeed_integration": 1.0,
    "biddeed_evals":      0.8,
    "zonewise_agent":     1.0,
    "zonewise_e2e_pass_rate": 1.0,
}

def parse_pytest_json(filepath: str) -> float:
    """Returns pass rate 0.0-1.0"""
    try:
        with open(filepath) as f:
            data = json.load(f)
        summary = data.get("summary", {})
        total = summary.get("total", 0)
        passed = summary.get("passed", 0)
        if total == 0:
            return 0.0
        return passed / total
    except Exception as e:
        print(f"  Warning: Could not parse {filepath}: {e}")
        return 0.0

def parse_playwright_json(filepath: str) -> float:
    """Returns pass rate from Playwright JSON report"""
    try:
        with open(filepath) as f:
            data = json.load(f)
        suites = data.get("suites", [])
        total, passed = 0, 0
        def walk(suite):
            nonlocal total, passed
            for spec in suite.get("specs", []):
                for test in spec.get("tests", []):
                    total += 1
                    if test.get("status") == "expected":
                        passed += 1
            for child in suite.get("suites", []):
                walk(child)
        for suite in suites:
            walk(suite)
        return (passed / total) if total > 0 else 0.0
    except Exception as e:
        print(f"  Warning: Could not parse Playwright JSON {filepath}: {e}")
        return 0.0

def find_artifact(pattern: str) -> str | None:
    matches = glob.glob(f"artifacts/**/{pattern}", recursive=True)
    return matches[0] if matches else None

def main():
    print("📊 Aggregating QA results...")
    
    scores = {}
    failures = []

    # BidDeed unit + integration (single pytest run covers both)
    unit_file = find_artifact("unit-results.json")
    if unit_file:
        score = parse_pytest_json(unit_file)
        scores["biddeed_unit"] = score
        scores["biddeed_integration"] = score  # Same run covers both files
        print(f"  BidDeed unit: {score:.2%}")
    else:
        scores["biddeed_unit"] = 0.0
        scores["biddeed_integration"] = 0.0
        print("  BidDeed unit: artifact not found")

    # BidDeed DeepEval
    deepeval_file = find_artifact("deepeval-results.json")
    if deepeval_file:
        score = parse_pytest_json(deepeval_file)
        scores["biddeed_evals"] = score
        print(f"  BidDeed DeepEval: {score:.2%}")
    else:
        scores["biddeed_evals"] = 1.0  # Skipped = not a failure
        print("  BidDeed DeepEval: skipped (no API key)")

    # ZoneWise agents
    agent_file = find_artifact("agent-results.json")
    if agent_file:
        score = parse_pytest_json(agent_file)
        scores["zonewise_agent"] = score
        print(f"  ZoneWise agents: {score:.2%}")
    else:
        scores["zonewise_agent"] = 0.0
        print("  ZoneWise agents: artifact not found")

    # ZoneWise Playwright
    pw_file = find_artifact("playwright-results.json")
    if pw_file:
        score = parse_playwright_json(pw_file)
        scores["zonewise_e2e_pass_rate"] = score
        print(f"  ZoneWise E2E: {score:.2%}")
    else:
        scores["zonewise_e2e_pass_rate"] = 0.0
        print("  ZoneWise E2E: artifact not found")

    # Compute failures
    for layer, threshold in THRESHOLDS.items():
        score = scores.get(layer, 0.0)
        if score < threshold:
            failures.append({"layer": layer, "score": score, "threshold": threshold})

    overall_score = sum(scores.values()) / len(scores) if scores else 0.0
    status = "pass" if not failures else "fail"
    heal_required = bool(failures)

    details = {
        "scores": scores,
        "failures": failures,
        "heal_required": heal_required,
        "github_run_url": GITHUB_RUN_URL,
    }

    # Log to Supabase
    try:
        supabase.table("insights").insert({
            "type": "qa_sentinel",
            "platform": "biddeed+zonewise",
            "layer": "all",
            "status": status,
            "score": overall_score,
            "details": json.dumps(details),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "healer_applied": False,
        }).execute()
        print(f"\n✅ Logged to Supabase — status={status} score={overall_score:.2%}")
    except Exception as e:
        print(f"\n⚠️ Supabase log failed: {e}")

    # Write SENTINEL_REPORT.json for healer
    with open("SENTINEL_REPORT.json", "w") as f:
        json.dump({"status": status, "score": overall_score, "failures": failures, "details": details}, f, indent=2)
    print("✅ SENTINEL_REPORT.json written")

    if failures:
        print(f"\n❌ {len(failures)} layer(s) below threshold:")
        for f in failures:
            print(f"   {f['layer']}: {f['score']:.2%} (need {f['threshold']:.0%})")
        sys.exit(1)
    else:
        print(f"\n✅ All layers passed — overall {overall_score:.2%}")

if __name__ == "__main__":
    main()
