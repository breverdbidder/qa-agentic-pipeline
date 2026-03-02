#!/usr/bin/env python3
"""
qa_telegram_commands.py — QA Commands for Existing Telegram Bot

ADD THESE HANDLERS to bot_v4.py in claude-code-telegram-control repo.

Commands added:
  /qa          — Full QA status dashboard
  /qa_biddeed  — BidDeed.AI QA status only
  /qa_zonewise — ZoneWise.AI QA status only
  /qa_last     — Last 5 QA run results
  /qa_issues   — Open QA critical GitHub issues
  /qa_trigger  — Manually trigger nightly QA run
"""

import os
import json
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import ContextTypes
import requests
from supabase import create_client


def get_supabase():
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    )


def score_emoji(score: float) -> str:
    if score >= 0.95: return "🟢"
    if score >= 0.8:  return "🟡"
    return "🔴"


# ─────────────────────────────────────────────────
# /qa — Full dashboard
# ─────────────────────────────────────────────────
async def cmd_qa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Fetching QA status...")
    
    supabase = get_supabase()
    
    # Latest run
    result = (
        supabase.table("insights")
        .select("*")
        .eq("type", "qa_sentinel")
        .order("timestamp", desc=True)
        .limit(1)
        .execute()
    )
    
    if not result.data:
        await update.message.reply_text(
            "⚠️ *No QA runs found.*\n"
            "Pipeline may not be configured yet.\n"
            "[Set up now](https://github.com/breverdbidder/qa-agentic-pipeline)",
            parse_mode="Markdown"
        )
        return
    
    run = result.data[0]
    details = json.loads(run["details"]) if isinstance(run["details"], str) else run["details"]
    scores = details.get("scores", {})
    status = run["status"].upper()
    overall = run.get("score", 0.0)
    
    ts = run["timestamp"][:16].replace("T", " ")
    status_line = "✅ PASS" if status == "PASS" else "❌ FAIL"
    
    lines = [
        f"📊 *QA Pipeline Status*",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"Last run: `{ts} UTC`",
        f"Overall: {status_line} `{overall*100:.0f}%`",
        f"",
        f"*BidDeed.AI*",
        f"  {score_emoji(scores.get('biddeed_unit',0))} Unit: `{scores.get('biddeed_unit',0)*100:.0f}%`",
        f"  {score_emoji(scores.get('biddeed_integration',0))} Integration: `{scores.get('biddeed_integration',0)*100:.0f}%`",
        f"  {score_emoji(scores.get('biddeed_evals',0))} DeepEval: `{scores.get('biddeed_evals',0)*100:.0f}%`",
        f"",
        f"*ZoneWise.AI*",
        f"  {score_emoji(scores.get('zonewise_agent',0))} Agent Tests: `{scores.get('zonewise_agent',0)*100:.0f}%`",
        f"  {score_emoji(scores.get('zonewise_e2e_pass_rate',0))} E2E (Playwright): `{scores.get('zonewise_e2e_pass_rate',0)*100:.0f}%`",
    ]
    
    failures = details.get("failures", [])
    if failures:
        lines += [f"", f"*Failures:*"]
        for f in failures:
            lines.append(f"  ❌ `{f['layer']}` → {f['score']*100:.0f}%")
    
    # Open issues
    try:
        issues_r = requests.get(
            "https://api.github.com/repos/breverdbidder/qa-agentic-pipeline/issues",
            headers={"Authorization": f"token {os.environ.get('GH_TOKEN','')}"},
            params={"labels": "qa-critical", "state": "open"},
            timeout=5
        )
        issues = issues_r.json() if issues_r.status_code == 200 else []
        if issues:
            lines += [f"", f"🚨 *{len(issues)} open critical issue(s)*"]
    except Exception:
        pass
    
    lines += [
        f"",
        f"[🔗 GitHub Actions](https://github.com/breverdbidder/qa-agentic-pipeline/actions) | "
        f"[📋 Supabase](https://supabase.com/dashboard/project/mocerqjnksmhcjzxrewo)"
    ]
    
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ─────────────────────────────────────────────────
# /qa_last — Last 5 runs history
# ─────────────────────────────────────────────────
async def cmd_qa_last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    supabase = get_supabase()
    result = (
        supabase.table("insights")
        .select("timestamp,status,score")
        .eq("type", "qa_sentinel")
        .order("timestamp", desc=True)
        .limit(5)
        .execute()
    )
    
    if not result.data:
        await update.message.reply_text("No runs yet.")
        return
    
    lines = ["📈 *Last 5 QA Runs*", "━━━━━━━━━━━━━━━━━━━━"]
    for run in result.data:
        ts = run["timestamp"][:16].replace("T", " ")
        status = "✅" if run["status"] == "pass" else "❌"
        score = run.get("score", 0.0)
        lines.append(f"{status} `{ts}` — `{score*100:.0f}%`")
    
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ─────────────────────────────────────────────────
# /qa_trigger — Manually trigger nightly pipeline
# ─────────────────────────────────────────────────
async def cmd_qa_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Triggering QA pipeline...")
    
    r = requests.post(
        "https://api.github.com/repos/breverdbidder/qa-agentic-pipeline/actions/workflows/nightly-qa.yml/dispatches",
        headers={
            "Authorization": f"token {os.environ.get('GH_TOKEN','')}",
            "Accept": "application/vnd.github.v3+json"
        },
        json={"ref": "main"},
        timeout=10
    )
    
    if r.status_code in [200, 204]:
        await update.message.reply_text(
            "✅ *QA Pipeline triggered.*\n"
            "Results will arrive here in ~15 minutes.\n"
            "[Monitor progress](https://github.com/breverdbidder/qa-agentic-pipeline/actions)",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"❌ Trigger failed: HTTP {r.status_code}")


# ─────────────────────────────────────────────────
# /qa_issues — Open critical issues
# ─────────────────────────────────────────────────
async def cmd_qa_issues(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = requests.get(
        "https://api.github.com/repos/breverdbidder/qa-agentic-pipeline/issues",
        headers={"Authorization": f"token {os.environ.get('GH_TOKEN','')}"},
        params={"labels": "qa-critical", "state": "open"},
        timeout=10
    )
    
    if r.status_code != 200 or not r.json():
        await update.message.reply_text("✅ *No open QA critical issues.*", parse_mode="Markdown")
        return
    
    issues = r.json()
    lines = [f"🚨 *{len(issues)} Open QA Issue(s)*", "━━━━━━━━━━━━━━━━━━━━"]
    for issue in issues[:5]:
        lines.append(f"• [{issue['title'][:55]}]({issue['html_url']})")
    
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ─────────────────────────────────────────────────
# REGISTER HANDLERS IN bot_v4.py
# Add these lines to the main() function where handlers are registered:
#
# from qa_telegram_commands import cmd_qa, cmd_qa_last, cmd_qa_trigger, cmd_qa_issues
# application.add_handler(CommandHandler("qa", cmd_qa))
# application.add_handler(CommandHandler("qa_last", cmd_qa_last))
# application.add_handler(CommandHandler("qa_trigger", cmd_qa_trigger))
# application.add_handler(CommandHandler("qa_issues", cmd_qa_issues))
# ─────────────────────────────────────────────────
