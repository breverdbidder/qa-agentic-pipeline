#!/usr/bin/env python3
"""
aggregate_results.py v3 — QA Results Aggregator
Reads pytest-json + playwright-json artifacts → scores → Supabase insights
Exits 0 always (workflow controls failure via FAILURES_FOUND env var)
"""
import os, json, glob, sys
from datetime import datetime, timezone

try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
GITHUB_RUN_URL = os.environ.get("GITHUB_RUN_URL", "")

THRESHOLDS = {
    "biddeed_unit":           1.0,
    "zonewise_agent":         0.5,
    "zonewise_e2e_pass_rate": 0.75,
}
DEEPEVAL_THRESHOLD = 0.75  # Only enforced if deepeval ran (score is not None)


def parse_pytest_json(filepath: str):
    try:
        with open(filepath) as f:
            data = json.load(f)
        summary = data.get("summary", {})
        total   = summary.get("total", 0)
        passed  = summary.get("passed", 0)
        skipped = summary.get("skipped", 0)
        ran = total - skipped
        if ran == 0:
            return None  # All skipped / nothing ran
        return passed / ran
    except Exception as e:
        print(f"  Warning: {filepath}: {e}")
        return None


def parse_playwright_json(filepath: str):
    try:
        with open(filepath) as f:
            data = json.load(f)
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
        for suite in data.get("suites", []):
            walk(suite)
        return (passed / total) if total > 0 else None
    except Exception as e:
        print(f"  Warning: Playwright {filepath}: {e}")
        return None


def find_artifact(pattern: str):
    matches = glob.glob(f"artifacts/**/{pattern}", recursive=True)
    return matches[0] if matches else None


def main():
    print("📊 Aggregating QA results...")
    scores, failures = {}, []

    # BidDeed Unit
    unit_file = find_artifact("unit-results.json")
    score = parse_pytest_json(unit_file) if unit_file else None
    if score is not None:
        scores["biddeed_unit"] = score
        print(f"  BidDeed unit: {score:.2%}")
    else:
        scores["biddeed_unit"] = 0.0
        print("  BidDeed unit: ❌ not found / all failed")

    # BidDeed DeepEval (optional — only enforced if tests ran)
    de_file = find_artifact("deepeval-results.json")
    de_score = parse_pytest_json(de_file) if de_file else None
    if de_score is not None:
        scores["biddeed_evals"] = de_score
        print(f"  BidDeed DeepEval: {de_score:.2%}")
        if de_score < DEEPEVAL_THRESHOLD:
            failures.append({"layer": "biddeed_evals", "score": de_score, "threshold": DEEPEVAL_THRESHOLD})
    else:
        print("  BidDeed DeepEval: ⏭ skipped (tests not collected — informational only)")

    # ZoneWise Agents
    agent_file = find_artifact("agent-results.json")
    score = parse_pytest_json(agent_file) if agent_file else None
    if score is not None:
        scores["zonewise_agent"] = score
        print(f"  ZoneWise agents: {score:.2%}")
    else:
        scores["zonewise_agent"] = 0.0
        print("  ZoneWise agents: ❌ not found")

    # ZoneWise E2E
    pw_file = find_artifact("playwright-results.json")
    score = parse_playwright_json(pw_file) if pw_file else None
    if score is not None:
        scores["zonewise_e2e_pass_rate"] = score
        print(f"  ZoneWise E2E: {score:.2%}")
    else:
        scores["zonewise_e2e_pass_rate"] = 0.0
        print("  ZoneWise E2E: ❌ not found")

    # Check thresholds (only for non-deepeval layers)
    for layer, threshold in THRESHOLDS.items():
        s = scores.get(layer, 0.0)
        if s < threshold:
            failures.append({"layer": layer, "score": s, "threshold": threshold})

    overall = sum(scores.values()) / len(scores) if scores else 0.0
    status  = "pass" if not failures else "fail"

    details = {
        "scores": scores,
        "failures": failures,
        "heal_required": bool(failures),
        "github_run_url": GITHUB_RUN_URL,
        "run_at": datetime.now(timezone.utc).isoformat(),
    }

    # Log to Supabase
    if SUPABASE_AVAILABLE and SUPABASE_URL and SUPABASE_KEY:
        try:
            sb = create_client(SUPABASE_URL, SUPABASE_KEY)
            sb.table("insights").insert({
                "type":        "qa_sentinel",
                "insight_type": "qa_result",
                "title":       f"QA Nightly — {status.upper()} {overall:.0%}",
                "description": f"BidDeed+ZoneWise pipeline. {len(failures)} failure(s).",
                "data":        json.dumps(details),
                "source":      "github_actions",
                "confidence":  overall,
                "status":      status,
                "priority":    "high" if failures else "low",
            }).execute()
            print(f"\n✅ Supabase — status={status} score={overall:.2%}")
        except Exception as e:
            print(f"\n⚠️ Supabase log failed: {e}")
    else:
        print("\n⚠️ Supabase not configured — skipping")

    with open("SENTINEL_REPORT.json", "w") as f:
        json.dump({"status": status, "score": overall, "failures": failures, "details": details}, f, indent=2)
    print("✅ SENTINEL_REPORT.json written\n")

    if failures:
        print(f"❌ {len(failures)} layer(s) below threshold:")
        for fail in failures:
            print(f"   {fail['layer']}: {fail['score']:.2%} (need {fail['threshold']:.0%})")
        # Write env var for workflow to detect — don't exit(1) here so Telegram step runs
        with open(os.environ.get("GITHUB_ENV", "/dev/null"), "a") as f:
            f.write("FAILURES_FOUND=true\n")
    else:
        print(f"✅ All layers passed — {overall:.2%}")


if __name__ == "__main__":
    main()
