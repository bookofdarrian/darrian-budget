#!/usr/bin/env python3
"""
agents/content_idea_bot.py
==========================
Content Idea Bank Populator — Peach State Savings / College Confused / SoleOps

Runs daily at 7am via cron on CT100.
Generates 3 viral content ideas per niche → saves to creator_ideas table
→ shows up in Creator Companion (page 24).

Cron (on CT100):
  0 7 * * * root cd /app && python3 agents/content_idea_bot.py >> /var/log/content-ideas.log 2>&1

Usage:
  python3 agents/content_idea_bot.py              # normal run
  python3 agents/content_idea_bot.py --dry-run    # show ideas, don't save
  python3 agents/content_idea_bot.py --niche "FAFSA tips"  # run one niche
"""

import sys
import os
import json
import re
import argparse
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, get_setting, init_db

# ── Niches to generate ideas for ─────────────────────────────────────────────
# Add/remove niches here to tune what the bot generates
NICHES = [
    "college admissions tips for first-gen students",
    "FAFSA and financial aid secrets",
    "sneaker reselling market and arbitrage",
    "personal finance for young adults in their 20s",
    "Black and Latino entrepreneurs",
    "Atlanta tech and startup scene",
    "productivity and AI tools for creators",
    "scholarship hunting strategies",
]

# ── DB setup ──────────────────────────────────────────────────────────────────

def _ensure_tables(conn) -> None:
    """Create creator_ideas table if it doesn't exist."""
    if USE_POSTGRES:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS creator_ideas (
                id SERIAL PRIMARY KEY,
                niche TEXT NOT NULL,
                hook TEXT,
                angle TEXT,
                platform TEXT,
                content_type TEXT,
                estimated_engagement TEXT,
                used INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
            )
        """)
    else:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS creator_ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                niche TEXT NOT NULL,
                hook TEXT,
                angle TEXT,
                platform TEXT,
                content_type TEXT,
                estimated_engagement TEXT,
                used INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
    conn.commit()


# ── Idea generation ───────────────────────────────────────────────────────────

def _generate_ideas(niche: str, api_key: str) -> list[dict]:
    """Call Claude to generate 3 viral content ideas for a niche."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        today = datetime.now().strftime("%B %d, %Y")
        prompt = f"""Generate exactly 3 viral short-form content ideas for this niche: "{niche}"

Today's date: {today}

For each idea, provide a JSON object with these exact keys:
- hook: the first 3-5 words that stop the scroll (urgent, specific, surprising)
- angle: the unique POV that makes this different from generic content (1 sentence)
- platform: the single best platform — TikTok, Instagram, or YouTube
- content_type: one of: talking head, text overlay, tutorial, storytime, reaction
- estimated_engagement: one sentence on why this will perform (what emotional trigger)

Return ONLY a valid JSON array of 3 objects. No markdown, no explanation, just the array.

Example format:
[
  {{
    "hook": "Nobody tells you this",
    "angle": "The scholarship deadline most students miss because it's not on common app",
    "platform": "TikTok",
    "content_type": "text overlay",
    "estimated_engagement": "Fear of missing out + specific insider knowledge = high save rate"
  }}
]"""

        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        text = msg.content[0].text.strip()
        # Extract JSON array even if Claude adds any surrounding text
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            ideas = json.loads(match.group())
            return ideas[:3]  # cap at 3
        return []

    except Exception as e:
        print(f"  ⚠️  Error generating ideas for '{niche}': {e}")
        return []


# ── Save to DB ────────────────────────────────────────────────────────────────

def _save_ideas(ideas: list[dict], niche: str, conn) -> int:
    """Save ideas to creator_ideas table. Returns count saved."""
    if not ideas:
        return 0

    ph = "%s" if USE_POSTGRES else "?"
    count = 0
    for idea in ideas:
        try:
            db_exec(conn, f"""
                INSERT INTO creator_ideas
                    (niche, hook, angle, platform, content_type, estimated_engagement)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """, (
                niche,
                idea.get("hook", ""),
                idea.get("angle", ""),
                idea.get("platform", ""),
                idea.get("content_type", ""),
                idea.get("estimated_engagement", ""),
            ))
            count += 1
        except Exception as e:
            print(f"  ⚠️  DB save error: {e}")
    conn.commit()
    return count


# ── Main ──────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False, single_niche: str | None = None) -> int:
    init_db()

    api_key = get_setting("anthropic_api_key")
    if not api_key:
        print("❌  anthropic_api_key not configured in app_settings. Exiting.")
        return 1

    conn = get_conn()
    _ensure_tables(conn)

    niches = [single_niche] if single_niche else NICHES
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'='*60}")
    print(f"🎬  Content Idea Bot — {ts}")
    print(f"   Niches: {len(niches)} | dry_run={dry_run}")
    print(f"{'='*60}\n")

    total_ideas = 0
    for niche in niches:
        print(f"📝  Generating ideas for: {niche}")
        ideas = _generate_ideas(niche, api_key)

        if dry_run:
            for i, idea in enumerate(ideas, 1):
                print(f"   [{i}] [{idea.get('platform')}] {idea.get('hook')}")
                print(f"       Angle: {idea.get('angle')}")
                print(f"       Type:  {idea.get('content_type')}")
        else:
            saved = _save_ideas(ideas, niche, conn)
            total_ideas += saved
            print(f"   ✅  Saved {saved} ideas")

    conn.close()

    if dry_run:
        print(f"\n✅  Dry run complete — {len(niches)} niches processed")
    else:
        print(f"\n✅  Done — {total_ideas} ideas saved to creator_ideas table")
        print("   View them in Creator Companion (page 24) → Idea Bank tab")

    print(f"{'='*60}\n")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Content Idea Bank Populator")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show ideas without saving to DB")
    parser.add_argument("--niche", metavar="NICHE",
                        help="Run for a single specific niche")
    args = parser.parse_args()
    sys.exit(main(dry_run=args.dry_run, single_niche=args.niche))
