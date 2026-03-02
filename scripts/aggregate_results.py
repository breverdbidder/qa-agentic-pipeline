#!/usr/bin/env python3
"""
Aggregate QA results from all layers and log to Supabase insights table.
Called by: nightly-qa.yml after all test jobs complete.
Zero human interaction required.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from supabase import create_client


def load_json_safe(path: str) -> dict:
    """Load JSON file, return empty dict if missing or malformed."""
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return {}


def compute_score(results: dict) -> float:
    """Compute pass rate from pytest JSON report."""
    if not results:
        return 0.0
    summary = results.get("summary", {})
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    return passed / total if total > 0 else 0.0


def main():
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    artifacts_dir = Path("./artifacts")
    run_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()

    # Load all result files
    biddeed_unit = load_json_safe(artifacts_dir / "biddeed-pytest-results/results_unit.json")
    biddeed_integration = load_json_safe(artifacts_dir / "biddeed-pytest-results/results_integration.json")
    biddeed_evals = load_json_safe(artifacts_dir / "biddeed-deepeval-results/results_biddeed_evals.json")
    zonewise_agent = load_json_safe(artifacts_dir / "zonewise-agent-results/results_zonewise_agent.json")
    zonewise_e2e = load_json_safe(artifacts_dir / "zonewise-playwright-results/playwright_results.json")

    # Compute scores
    scores = {
        "biddeed_unit": compute_score(biddeed_unit),
        "biddeed_integration": compute_score(biddeed_integration),
        "biddeed_evals": biddeed_evals.get("overall_score", 0.0),
        "zonewise_agent": compute_score(zonewise_agent),
        "zonewise_e2e_pass_rate": (
            zonewise_e2e.get("stats", {}).get("expected", 0) /
            max(zonewise_e2e.get("stats", {}).get("total", 1), 1)
        ) if zonewise_e2e else 0.0,
    }

    # Thresholds
    THRESHOLDS = {
        "biddeed_unit": 1.0,
        "biddeed_integration": 1.0,
        "biddeed_evals": 0.8,
        "zonewise_agent": 1.0,
        "zonewise_e2e_pass_rate": 1.0,
    }

    # Find failures
    failures = []
    for layer, score in scores.items():
        threshold = THRESHOLDS[layer]
        if score < threshold:
            failures.append({
                "layer": layer,
                "score": score,
                "threshold": threshold,
                "gap": threshold - score,
            })

    overall_score = sum(scores.values()) / len(scores)
    overall_status = "PASS" if not failures else "FAIL"
    heal_required = bool(failures)

    # Build sentinel report
    sentinel_report = {
        "run_id": run_id,
        "timestamp": timestamp,
        "scores": scores,
        "overall_score": overall_score,
        "overall_status": overall_status,
        "failures": failures,
        "heal_required": heal_required,
    }

    # Save locally for healer to read
    Path("SENTINEL_REPORT.json").write_text(json.dumps(sentinel_report, indent=2))
    print(f"SENTINEL_REPORT.json written: {overall_status} (score={overall_score:.2f})")

    # Log to Supabase
    try:
        supabase.table("insights").insert({
            "type": "qa_sentinel",
            "platform": "biddeed+zonewise",
            "layer": "full_suite",
            "status": overall_status.lower(),
            "score": overall_score,
            "details": json.dumps(sentinel_report),
            "timestamp": timestamp,
        }).execute()
        print("✅ Logged to Supabase insights table")
    except Exception as e:
        print(f"⚠️ Supabase log failed: {e}")

    # Exit with error code on failures (will trigger healer)
    if failures:
        print(f"\n❌ {len(failures)} layer(s) below threshold:")
        for f in failures:
            print(f"  - {f['layer']}: {f['score']:.2f} < {f['threshold']:.2f}")
        exit(1)
    else:
        print(f"\n✅ All layers passing. Overall score: {overall_score:.2f}")


if __name__ == "__main__":
    main()
