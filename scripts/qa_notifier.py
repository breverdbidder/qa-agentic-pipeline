import json
#!/usr/bin/env python3
"""
qa_notifier.py — QA Pipeline Telegram Reporter
Reads Supabase insights → formats → pushes to Ariel's Telegram

Called by:
  1. nightly-qa.yml after aggregate_results.py completes
  2. On-demand via /qa-status Telegram command
  3. On any critical failure (immediate alert)

Phone: +1(561)809-0929 | Chat ID: stored in TELEGRAM_CHAT_ID env var
"""

import os
import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests
from supabase import create_client

# ─────────────────────────────────────────────────
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GITHUB_RUN_URL = os.environ.get("GITHUB_RUN_URL", "https://github.com/breverdbidder/qa-agentic-pipeline/actions")
# ─────────────────────────────────────────────────

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_latest_sentinel_run() -> Optional[dict]:
    """Fetch the most recent QA sentinel run from Supabase."""
    result = (
        supabase.table("insights")
        .select("*")
        .eq("type", "qa_sentinel")
        .order("timestamp", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        row = result.data[0]
        row["details"] = json.loads(row.get("data", "{}")) if isinstance(row.get("data"), str) else (row.get("data") or {})
        return row
    return None


def get_recent_runs(hours: int = 24) -> list:
    """Fetch all QA runs in the last N hours."""
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    result = (
        supabase.table("insights")
        .select("*")
        .eq("type", "qa_sentinel")
        .gte("timestamp", since)
        .order("timestamp", desc=True)
        .execute()
    )
    return result.data or []


def get_open_issues() -> list:
    """Fetch open QA critical issues from GitHub."""
    try:
        r = requests.get(
            "https://api.github.com/repos/breverdbidder/qa-agentic-pipeline/issues",
            headers={"Authorization": f"token {os.environ.get('GITHUB_TOKEN','')}"},
            params={"labels": "qa-critical", "state": "open"},
            timeout=10,
        )
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


def format_score_bar(score: float, width: int = 10) -> str:
    """Visual progress bar for score 0.0–1.0."""
    filled = int(score * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {score*100:.0f}%"


def format_layer_results(details: dict) -> str:
    """Format per-layer scores for Telegram message."""
    scores = details.get("scores", {})
    lines = []
    
    layer_labels = {
        "biddeed_unit":        "BidDeed Unit Tests    ",
        "biddeed_integration": "BidDeed Integration   ",
        "biddeed_evals":       "BidDeed DeepEval      ",
        "zonewise_agent":      "ZoneWise Agent Tests  ",
        "zonewise_e2e_pass_rate": "ZoneWise E2E (PW)  ",
    }
    
    for key, label in layer_labels.items():
        score = scores.get(key)
        if score is None:
            lines.append(f"  {label}: ⏸ not run")
            continue
        emoji = "✅" if score >= 0.95 else ("⚠️" if score >= 0.8 else "❌")
        lines.append(f"  {emoji} {label}: {format_score_bar(score)}")
    
    return "\n".join(lines)


def build_nightly_report(run: dict) -> str:
    """Build the nightly summary Telegram message."""
    details = json.loads(run.get("data", "{}")) if isinstance(run.get("data"), str) else (run.get("data") or {})
    status = run.get("status", "unknown").upper()
    score = run.get("score", 0.0)
    timestamp = run.get("timestamp", "")
    failures = details.get("failures", [])
    heal_required = details.get("heal_required", False)
    
    # Parse timestamp
    try:
        ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        time_str = ts.strftime("%b %d, %Y at %I:%M %p UTC")
    except Exception:
        time_str = timestamp

    status_emoji = "✅ PASS" if status == "PASS" else ("🔧 HEALING" if heal_required else "❌ FAIL")
    
    lines = [
        f"🤖 *QA Nightly Report*",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"📅 {time_str}",
        f"🎯 Overall: {status_emoji} | Score: {format_score_bar(score)}",
        f"",
        f"*Layer Results:*",
        format_layer_results(details),
    ]
    
    if failures:
        lines += [
            f"",
            f"*Failed Layers ({len(failures)}):*",
        ]
        for f in failures[:5]:  # Max 5 shown
            lines.append(f"  ❌ `{f['layer']}` — score {f['score']:.2f} (need {f['threshold']:.2f})")
    
    if heal_required:
        lines += [
            f"",
            f"⚙️ *Auto-healer triggered* — check back in 15 min",
        ]
    
    open_issues = get_open_issues()
    if open_issues:
        lines += [
            f"",
            f"🚨 *{len(open_issues)} open QA issue(s):*",
        ]
        for issue in open_issues[:3]:
            lines.append(f"  • [{issue['title'][:50]}...]({issue['html_url']})")
    
    lines += [
        f"",
        f"[📊 Full Report]({GITHUB_RUN_URL}) | [🗃️ Supabase](https://supabase.com/dashboard/project/mocerqjnksmhcjzxrewo/editor)",
    ]
    
    return "\n".join(lines)


def build_critical_alert(failure_details: dict) -> str:
    """Build an immediate critical failure alert."""
    layer = failure_details.get("layer", "unknown")
    score = failure_details.get("score", 0.0)
    threshold = failure_details.get("threshold", 0.0)
    
    return (
        f"🚨 *QA CRITICAL FAILURE*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Layer: `{layer}`\n"
        f"Score: {score:.2f} (need {threshold:.2f})\n"
        f"Auto-healer: attempting fix...\n\n"
        f"[View Issue]({GITHUB_RUN_URL})"
    )


def build_status_summary() -> str:
    """Build on-demand /qa-status summary."""
    recent = get_recent_runs(hours=24)
    
    if not recent:
        return (
            "📊 *QA Status*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ No runs in the last 24 hours.\n"
            "Nightly pipeline runs at 11PM EST.\n\n"
            "[Trigger manually](" + GITHUB_RUN_URL + ")"
        )
    
    latest = recent[0]
    latest["details"] = json.loads(latest["details"]) if isinstance(latest["details"], str) else latest["details"]
    
    pass_count = sum(1 for r in recent if r.get("status") == "pass")
    total = len(recent)
    
    lines = [
        f"📊 *QA Status Dashboard*",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"Last 24h: {pass_count}/{total} runs passed",
        f"Latest run: {latest.get('timestamp','')[:16]}",
        f"",
        build_nightly_report(latest),
    ]
    return "\n".join(lines)


def send_telegram(message: str, parse_mode: str = "Markdown") -> bool:
    """Send message to Telegram."""
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": False,
            },
            timeout=15,
        )
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return False


def main(mode: str = "nightly"):
    """
    mode: nightly | critical | status
    """
    if mode == "nightly":
        run = get_latest_sentinel_run()
        if not run:
            send_telegram("⚠️ QA Nightly: No results found in Supabase. Check GitHub Actions.")
            return
        message = build_nightly_report(run)
        success = send_telegram(message)
        print(f"Nightly report sent: {success}")

    elif mode == "critical":
        # Read failure details from env or stdin
        failure_json = os.environ.get("QA_FAILURE_DETAILS", "{}")
        failure_details = json.loads(failure_json)
        message = build_critical_alert(failure_details)
        send_telegram(message)

    elif mode == "status":
        message = build_status_summary()
        send_telegram(message)


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "nightly"
    main(mode)
