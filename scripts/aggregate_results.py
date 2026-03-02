#!/usr/bin/env python3
"""
aggregate_results.py v4 — 90% threshold enforcement
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
GITHUB_ENV = os.environ.get("GITHUB_ENV", "/dev/null")

# 90% benchmark across all layers
THRESHOLDS = {
    "biddeed_unit":           0.90,
    "zonewise_agent":         0.90,
    "zonewise_e2e_pass_rate": 0.90,
}
DEEPEVAL_THRESHOLD = 0.90  # Only enforced if deepeval tests actually ran


def parse_pytest_json(filepath: str):
    """Returns pass rate excluding skipped. None if nothing ran."""
    try:
        with open(filepath) as f:
            data = json.load(f)
        summary = data.get("summary", {})
        total   = summary.get("total", 0)
        passed  = summary.get("passed", 0)
        skipped = summary.get("skipped", 0)
        errors  = summary.get("error", 0)
        ran = total - skipped  # errors count as failures in denominator
        if ran == 0:
            return None
        return passed / ran
    except Exception as e:
        print(f"  Warning: {filepath}: {e}")
        return None


def parse_playwright_json(filepath: str):
    """Returns pass rate from playwright JSON report."""
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


def check(label: str, score, threshold: float, failures: list, scores: dict):
    scores[label] = score if score is not None else 0.0
    bar = "█" * int((score or 0) * 10) + "░" * (10 - int((score or 0) * 10))
    status = "✅" if (score or 0) >= threshold else "❌"
    print(f"  {status} {label}: {(score or 0):.0%} [{bar}] (need {threshold:.0%})")
    if score is None:
        failures.append({"layer": label, "score": 0.0, "threshold": threshold, "reason": "not_run"})
    elif score < threshold:
        failures.append({"layer": label, "score": score, "threshold": threshold})


def main():
    print(f"📊 QA Benchmark — 90% threshold enforcement")
    print(f"{'─'*50}")
    scores, failures = {}, []

    # BidDeed Unit + Integration
    unit_file = find_artifact("unit-results.json")
    score = parse_pytest_json(unit_file) if unit_file else None
    check("biddeed_unit", score, THRESHOLDS["biddeed_unit"], failures, scores)

    # DeepEval (optional — enforced only if tests ran)
    de_file = find_artifact("deepeval-results.json")
    de_score = parse_pytest_json(de_file) if de_file else None
    if de_score is not None:
        scores["biddeed_evals"] = de_score
        bar = "█" * int(de_score * 10) + "░" * (10 - int(de_score * 10))
        status = "✅" if de_score >= DEEPEVAL_THRESHOLD else "❌"
        print(f"  {status} biddeed_evals:  {de_score:.0%} [{bar}] (need {DEEPEVAL_THRESHOLD:.0%})")
        if de_score < DEEPEVAL_THRESHOLD:
            failures.append({"layer": "biddeed_evals", "score": de_score, "threshold": DEEPEVAL_THRESHOLD})
    else:
        print(f"  ⏭  biddeed_evals:  skipped (deepeval not collected — not enforced)")

    # ZoneWise Agents
    agent_file = find_artifact("agent-results.json")
    score = parse_pytest_json(agent_file) if agent_file else None
    check("zonewise_agent", score, THRESHOLDS["zonewise_agent"], failures, scores)

    # ZoneWise E2E
    pw_file = find_artifact("playwright-results.json")
    score = parse_playwright_json(pw_file) if pw_file else None
    check("zonewise_e2e_pass_rate", score, THRESHOLDS["zonewise_e2e_pass_rate"], failures, scores)

    print(f"{'─'*50}")
    enforced = {k: v for k, v in scores.items() if k != "biddeed_evals" or "biddeed_evals" in THRESHOLDS}
    overall = sum(enforced.values()) / len(enforced) if enforced else 0.0
    status = "pass" if not failures else "fail"

    details = {
        "scores": scores,
        "failures": failures,
        "thresholds": THRESHOLDS,
        "benchmark": "90%",
        "heal_required": bool(failures),
        "github_run_url": GITHUB_RUN_URL,
        "run_at": datetime.now(timezone.utc).isoformat(),
    }

    if SUPABASE_AVAILABLE and SUPABASE_URL and SUPABASE_KEY:
        try:
            sb = create_client(SUPABASE_URL, SUPABASE_KEY)
            sb.table("insights").insert({
                "type":         "qa_sentinel",
                "insight_type": "qa_result",
                "title":        f"QA Nightly — {status.upper()} {overall:.0%} (90% benchmark)",
                "description":  f"{len(failures)} layer(s) below 90% threshold.",
                "data":         json.dumps(details),
                "source":       "github_actions",
                "confidence":   overall,
                "status":       status,
                "priority":     "high" if failures else "low",
            }).execute()
            print(f"✅ Supabase logged — {status} @ {overall:.0%}")
        except Exception as e:
            print(f"⚠️  Supabase failed: {e}")

    with open("SENTINEL_REPORT.json", "w") as f:
        json.dump({"status": status, "score": overall, "failures": failures, "details": details}, f, indent=2)
    print("✅ SENTINEL_REPORT.json written")

    if failures:
        print(f"\n❌ BELOW 90% BENCHMARK — {len(failures)} failure(s):")
        for f in failures:
            reason = f.get("reason", "")
            print(f"   {f['layer']}: {f['score']:.0%} (need {f['threshold']:.0%}) {reason}")
        with open(GITHUB_ENV, "a") as f:
            f.write("FAILURES_FOUND=true\n")
    else:
        print(f"\n✅ ALL LAYERS ≥ 90% — Overall: {overall:.0%}")


if __name__ == "__main__":
    main()
