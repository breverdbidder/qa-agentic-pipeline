#!/usr/bin/env python3
"""qa_notifier.py v2 — Simple, bulletproof Telegram reporter"""
import os, sys, json, requests
from datetime import datetime, timezone

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
GITHUB_RUN_URL = os.environ.get("GITHUB_RUN_URL", "https://github.com/breverdbidder/qa-agentic-pipeline/actions")


def send(msg: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"⚠️ No Telegram credentials — TOKEN={'set' if TELEGRAM_TOKEN else 'MISSING'} CHAT={'set' if TELEGRAM_CHAT_ID else 'MISSING'}")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True},
            timeout=15
        )
        print(f"Telegram: HTTP {r.status_code}")
        if r.status_code != 200:
            print(f"Response: {r.text[:200]}")
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def get_latest_run() -> dict | None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/insights",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            params={"type": "eq.qa_sentinel", "order": "created_at.desc", "limit": 1},
            timeout=10
        )
        rows = r.json()
        if not rows:
            return None
        row = rows[0]
        data = row.get("data") or row.get("data") or "{}"
        if isinstance(data, str):
            data = json.loads(data)
        row["_parsed_data"] = data
        return row
    except Exception as e:
        print(f"Supabase fetch error: {e}")
        return None


def bar(score: float) -> str:
    filled = int(score * 8)
    return f"{'█'*filled}{'░'*(8-filled)} {score*100:.0f}%"


def emoji(score: float) -> str:
    return "🟢" if score >= 0.95 else ("🟡" if score >= 0.8 else "🔴")


def build_report(run: dict) -> str:
    data = run.get("_parsed_data", {})
    scores = data.get("scores", {})
    failures = data.get("failures", [])
    status = run.get("status", "unknown").upper()
    overall = run.get("confidence", 0.0) or 0.0
    ts = (run.get("created_at") or "")[:16].replace("T", " ")

    status_icon = "✅ PASS" if status == "PASS" else "❌ FAIL"

    lines = [
        f"🤖 *QA Nightly Report*",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"📅 `{ts} UTC`",
        f"🎯 {status_icon} | Overall: `{bar(overall)}`",
        "",
        f"*BidDeed\\.AI*",
        f"  {emoji(scores.get('biddeed_unit',0))} Unit: `{bar(scores.get('biddeed_unit',0))}`",
        f"  {emoji(scores.get('biddeed_evals',1.0))} DeepEval: `{bar(scores.get('biddeed_evals',1.0))}`",
        "",
        f"*ZoneWise\\.AI*",
        f"  {emoji(scores.get('zonewise_agent',0))} Agents: `{bar(scores.get('zonewise_agent',0))}`",
        f"  {emoji(scores.get('zonewise_e2e_pass_rate',0))} E2E: `{bar(scores.get('zonewise_e2e_pass_rate',0))}`",
    ]

    if failures:
        lines += ["", f"*Failures \\({len(failures)}\\):*"]
        for f in failures[:4]:
            lines.append(f"  ❌ `{f['layer']}` → {f['score']*100:.0f}%")

    lines += ["", f"[📊 GitHub Actions]({GITHUB_RUN_URL})"]
    return "\n".join(lines)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "nightly"
    print(f"Mode: {mode} | Token: {'set' if TELEGRAM_TOKEN else 'MISSING'} | Chat: {'set' if TELEGRAM_CHAT_ID else 'MISSING'}")

    run = get_latest_run()

    if run:
        msg = build_report(run)
        ok = send(msg)
        print(f"Report sent: {ok}")
    else:
        ok = send(
            f"⚠️ *QA Report*\n"
            f"No results in Supabase yet\\.\n"
            f"[Check Actions]({GITHUB_RUN_URL})"
        )
        print(f"Fallback sent: {ok}")

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
