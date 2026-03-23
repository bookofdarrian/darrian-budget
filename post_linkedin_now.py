#!/usr/bin/env python3
"""
post_linkedin_now.py
====================
LinkedIn Campaign Launch Script — Darrian Belcher / Peach State Savings

Does THREE things:
  1. Seeds the Social Media Manager DB with all 5 LinkedIn post variants
     (ready to review/send from pages/57_social_media_manager.py)
  2. Seeds scheduled posts for Instagram, TikTok, YouTube Shorts, Twitter/X
  3. Prints the interactive launch guide with copy-paste captions

Usage:
  python3 post_linkedin_now.py              # Seed DB + print guide
  python3 post_linkedin_now.py --dry-run    # Preview only, no DB writes
  python3 post_linkedin_now.py --status     # Show what's already seeded
"""

import sys
import argparse
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# ─── Project imports ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

try:
    from utils.db import get_conn, init_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("⚠️  utils.db not available — running in preview-only mode")

# ─── Video asset paths ───────────────────────────────────────────────────────
VERTICAL_VIDEO  = BASE_DIR / "videos" / "linkedin" / "linkedin_vertical_9x16.mp4"
LANDSCAPE_VIDEO = BASE_DIR / "videos" / "linkedin" / "linkedin_landscape_16x9.mp4"
SQUARE_VIDEO    = BASE_DIR / "videos" / "linkedin" / "linkedin_square_1x1.mp4"

# ─── Post Copy ────────────────────────────────────────────────────────────────
POST_2_LONG = """I built a system that ships production code while I sleep. 🤖

I'm a Product Manager at Visa by day.
At night I run 3 products:
→ Peach State Savings (personal finance app)
→ SoleOps (sneaker resale platform)
→ College Confused (college prep tool)

More ideas than hours. The bottleneck was always: shipping.

So I took the gated SDLC I learned at Visa — and gave it to AI agents.

Here's the architecture in 30 seconds:

⏰ 11PM cron kicks off on my home lab (Proxmox CT100 + Tailscale)

🧠 Planner Agent reads BACKLOG.md → writes spec
⚙️  Backend Agent generates DB tables + logic (follows my patterns)
🎨 UI Agent scaffolds Streamlit pages (my sidebar standard)
🧪 Test Agent writes + runs pytest
✅ QA Agent checks: no hardcoded keys, all tests pass, patterns correct
🚀 Git Agent commits on a feature branch, opens a GitHub PR

I wake up. Review the PR. Merge. Done.

What makes it different from vibe coding:
→ Guardrails are in the SYSTEM, not repeated every session
→ It knows my codebase, my patterns, my DB helpers
→ If tests fail → nothing commits
→ Human judgment is always the final gate

Cost: ~$1/night (Claude Opus 4)
Infrastructure: $0/month (self-hosted homelab)
Pages shipped: 73+
Time saved: 3–4 hours per feature

This isn't replacing my engineering judgment.
It's amplifying it.

A human still drives. The AI handles the road.

Comment "PIPELINE" and I'll share the orchestrator code. 👇

peachstatesavings.com

#AI #SDLC #ProductManagement #Python #Streamlit
#BuildInPublic #IndieHacker #MachineLearning #Automation
#SoftwareEngineering #CareerGrowth #TechInnovation"""

POST_1_HOOK = """I built a system that ships production code while I sleep.

6 AI agents. 1 home lab. $0/month infra.
73+ pages shipped. ~$1/night in Claude API costs.

Full autonomous SDLC: feature → dev → qa → staging → prod.

The pipeline is the product. 🔥

Drop a 🔁 to see the full architecture.
peachstatesavings.com

#AI #MachineLearning #SoftwareEngineering #BuildInPublic #Python"""

POST_3_CONTRARIAN = """Unpopular opinion: most "vibe coding" is just chaos engineering.

Real AI-assisted development needs guardrails.

I run a 6-agent pipeline that mirrors Visa's SDLC — nightly.
Tests fail → nothing commits. QA gate required. Human reviews every PR.

73 pages. $1/night. No shortcuts on quality.

The difference between vibe coding and autonomous development:
One is a demo. The other is a system.

Which are you building?

peachstatesavings.com

#AI #SoftwareEngineering #SDLC #Python #ProductManagement
#BuildInPublic #CodingLife #IndieHacker #MachineLearning"""

POST_4_NUMBERS = """Numbers from my autonomous AI dev system (after 30 days):

📦 73+ features shipped to production
⏰ 0 all-nighters required
💰 ~$30/month total cost (Claude Opus 4 API)
🏗️  $0/month infrastructure (self-hosted Proxmox)
🧪 100% test pass rate required before any commit
🤖 6 agents running every night at 11PM
🔒 0 hardcoded credentials ever committed
⚡ 3–4 hours saved per feature

The system:
feature → dev → qa → staging → main (prod)

Built it myself in a weekend using the same SDLC discipline I learned at Visa.

Full write-up + code: comment "CODE" below 👇

#AI #Automation #IndieHacker #BuildInPublic #Python
#SDLC #SoftwareEngineering #ProductManagement #CareerGrowth"""

POST_INSTAGRAM_REEL = """POV: your code ships itself every night 🤖

I built a 6-agent AI pipeline that runs my full SDLC while I sleep.
Planner → Backend → UI → Tests → QA → Git → PR

By morning, I have a PR to review. I merge it. Done.

$1/night. $0 infra. 73+ pages shipped.

The pipeline is the product. 🔥

Link in bio → peachstatesavings.com"""

POST_TIKTOK = """POV: Your AI writes your code every night so you don't have to 🤖

Built a 6-agent autonomous SDLC pipeline running on my home lab.
11PM: agents wake up → plan, code, test, QA, commit → PR waiting at 7AM.

$1/night in API costs. $0 infrastructure. 73+ pages live.

This is what indie building looks like in 2026.

peachstatesavings.com 🍑"""

POST_YOUTUBE_SHORT = """I Built an AI That Writes Code While I Sleep 🤖 (Full Pipeline)

Every night at 11PM, 6 AI agents run my full software development lifecycle:
🧠 Planner → ⚙️ Backend → 🎨 UI → 🧪 Tests → ✅ QA → 🚀 Git

By morning I have a GitHub PR ready to review.
$1/night | $0 infra | 73+ pages shipped

Stack: Python + Streamlit + Claude Opus 4 + Proxmox homelab

🔗 peachstatesavings.com
🐙 github.com/bookofdarrian

#shorts #AI #coding #python #automation #buildinpublic"""

POST_TWITTER_THREAD = """🧵 I built an autonomous AI SDLC pipeline. It ships production code while I sleep. Here's exactly how it works (thread):

1/ I'm a PM at Visa by day. At night I build 3 products: Peach State Savings, SoleOps, and College Confused. Problem: more ideas than hours.

2/ Solution: take Visa's gated SDLC and give it to AI agents. Every night at 11PM, 6 agents wake up:

3/ 🧠 PLANNER reads BACKLOG.md, writes a spec for tonight's feature
⚙️ BACKEND generates DB tables + logic (knows my patterns)
🎨 UI scaffolds the Streamlit page
🧪 TESTS writes + runs pytest
✅ QA gates: no hardcoded keys, all tests pass
🚀 GIT opens a PR on a feature branch

4/ I wake up, review the PR, merge if it looks good.
Human judgment = always the final gate.

5/ Numbers: 73+ pages shipped | ~$1/night (Claude Opus 4) | $0 infra (self-hosted Proxmox) | 3-4 hrs saved per feature

6/ The key insight: guardrails in the SYSTEM not the session. It knows my codebase, my patterns, my naming conventions. If tests fail → nothing commits.

7/ This isn't vibe coding. It's disciplined AI engineering. The pipeline is the product.

8/ Comment "PIPELINE" for the orchestrator code. 🔁 to help other builders see this.

peachstatesavings.com"""


# ─── Scheduled post data ─────────────────────────────────────────────────────
def _build_post_queue() -> list[dict]:
    """Return list of posts to seed into the SMM DB queue."""
    now = datetime.now()

    # Smart scheduling: find next best posting times
    def next_weekday_at(weekday: int, hour: int, minute: int = 0) -> str:
        """Get next occurrence of weekday (0=Mon) at given hour."""
        d = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        days_ahead = weekday - d.weekday()
        if days_ahead < 0 or (days_ahead == 0 and d <= now):
            days_ahead += 7
        d = d + timedelta(days=days_ahead)
        return d.strftime("%Y-%m-%d %H:%M:%S")

    # Mon=0, Tue=1, Wed=2, Thu=3, Fri=4
    return [
        # ── LINKEDIN ──────────────────────────────────────────────────────────
        {
            "platform": "LinkedIn",
            "account_name": "Darrian Belcher",
            "title": "🚀 AI SDLC Pipeline — Long Form Story (PRIMARY)",
            "content": POST_2_LONG,
            "media_path": str(VERTICAL_VIDEO),
            "hashtags": "#AI #SDLC #ProductManagement #Python #Streamlit",
            "status": "scheduled",
            "scheduled_at": next_weekday_at(0, 8, 0),   # Monday 8AM
            "notes": "PRIMARY POST — attach linkedin_vertical_9x16.mp4. Pin architecture diagram comment right after posting.",
        },
        {
            "platform": "LinkedIn",
            "account_name": "Darrian Belcher",
            "title": "🔥 AI SDLC — Contrarian Take",
            "content": POST_3_CONTRARIAN,
            "media_path": "",
            "hashtags": "#AI #SoftwareEngineering #SDLC #Python #ProductManagement",
            "status": "scheduled",
            "scheduled_at": next_weekday_at(1, 7, 30),  # Tuesday 7:30AM
            "notes": "Text-only post. Sparks debate = more comments = more reach.",
        },
        {
            "platform": "LinkedIn",
            "account_name": "Darrian Belcher",
            "title": "📊 AI SDLC — Numbers Post",
            "content": POST_4_NUMBERS,
            "media_path": str(LANDSCAPE_VIDEO),
            "hashtags": "#AI #Automation #IndieHacker #BuildInPublic #Python",
            "status": "scheduled",
            "scheduled_at": next_weekday_at(3, 8, 0),   # Thursday 8AM
            "notes": "Attach landscape video OR dashboard screenshot. Numbers posts get high shares.",
        },
        {
            "platform": "LinkedIn",
            "account_name": "Darrian Belcher",
            "title": "🎯 AI SDLC — Hook Variant",
            "content": POST_1_HOOK,
            "media_path": str(SQUARE_VIDEO),
            "hashtags": "#AI #MachineLearning #SoftwareEngineering #BuildInPublic #Python",
            "status": "scheduled",
            "scheduled_at": next_weekday_at(0, 9, 0),   # Following Monday 9AM
            "notes": "Week 2 post — attach square video for feed variety.",
        },
        # ── INSTAGRAM ─────────────────────────────────────────────────────────
        {
            "platform": "Instagram",
            "account_name": "bookofdarrian",
            "title": "🎬 AI Pipeline Reel",
            "content": POST_INSTAGRAM_REEL,
            "media_path": str(VERTICAL_VIDEO),
            "hashtags": "#AI #Python #BuildInPublic #IndieHacker #SDLC #Automation #Streamlit #MachineLearning #TechTok #Coding",
            "status": "scheduled",
            "scheduled_at": next_weekday_at(0, 9, 0),   # Monday 9AM
            "notes": "Upload as Reel. Add hashtags in FIRST COMMENT not caption. Use trending audio overlay in IG editor.",
        },
        # ── TIKTOK ────────────────────────────────────────────────────────────
        {
            "platform": "TikTok",
            "account_name": "bookofdarrian",
            "title": "🤖 POV: AI ships your code",
            "content": POST_TIKTOK,
            "media_path": str(VERTICAL_VIDEO),
            "hashtags": "#AI #coding #python #buildinpublic #automation #techtok #softwareengineering",
            "status": "scheduled",
            "scheduled_at": next_weekday_at(0, 10, 0),  # Monday 10AM
            "notes": "Add on-screen text captions in TikTok editor. Use trending sound. Hook text: 'POV: Your code ships itself every night'",
        },
        # ── YOUTUBE ───────────────────────────────────────────────────────────
        {
            "platform": "YouTube",
            "account_name": "bookofdarrian",
            "title": "▶️ AI SDLC Short",
            "content": POST_YOUTUBE_SHORT,
            "media_path": str(VERTICAL_VIDEO),
            "hashtags": "#shorts #AI #coding #python #automation",
            "status": "scheduled",
            "scheduled_at": next_weekday_at(2, 15, 0),  # Wednesday 3PM
            "notes": "Upload as YouTube Short. Title: 'I Built an AI That Writes Code While I Sleep 🤖 #shorts'",
        },
        # ── TWITTER/X ─────────────────────────────────────────────────────────
        {
            "platform": "Twitter",
            "account_name": "bookofdarrian",
            "title": "🧵 AI SDLC Thread",
            "content": POST_TWITTER_THREAD,
            "media_path": str(LANDSCAPE_VIDEO),
            "hashtags": "#AI #BuildInPublic #Python #SDLC",
            "status": "scheduled",
            "scheduled_at": next_weekday_at(4, 9, 0),   # Friday 9AM
            "notes": "Post as a thread (split by numbering). Attach landscape video to first tweet.",
        },
        # ── FACEBOOK ──────────────────────────────────────────────────────────
        {
            "platform": "Facebook",
            "account_name": "Peach State Savings",
            "title": "📘 AI SDLC Pipeline — Facebook",
            "content": POST_2_LONG,
            "media_path": str(LANDSCAPE_VIDEO),
            "hashtags": "#AI #BuildInPublic #Python #Automation",
            "status": "scheduled",
            "scheduled_at": next_weekday_at(2, 12, 0),  # Wednesday noon
            "notes": "Post to Peach State Savings page AND personal profile. Use landscape video.",
        },
    ]


# ─── DB seeding ───────────────────────────────────────────────────────────────
def _ensure_smm_tables(conn: sqlite3.Connection) -> None:
    """Ensure Social Media Manager tables exist with all required columns.

    Handles both:
      - Fresh DB → creates the table with full schema
      - Existing DB with old SMM schema → migrates by adding missing columns
    """
    cursor = conn.cursor()

    # Base table (matches existing SMM schema from pages/57_social_media_manager.py)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS smm_posts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL DEFAULT '',
            caption     TEXT    DEFAULT '',
            hashtags    TEXT    DEFAULT '',
            post_type   TEXT    DEFAULT 'video',
            status      TEXT    DEFAULT 'draft',
            account_ids TEXT    DEFAULT '',
            scheduled_at TEXT   DEFAULT NULL,
            published_at TEXT   DEFAULT NULL,
            media_urls  TEXT    DEFAULT '',
            link        TEXT    DEFAULT '',
            campaign    TEXT    DEFAULT '',
            notes       TEXT    DEFAULT '',
            created_at  TEXT    DEFAULT (datetime('now'))
        )
    """)

    # Migrate: add new columns needed by the LinkedIn campaign seeder
    # Uses ALTER TABLE ... ADD COLUMN which is idempotent-safe (wrapped in try/except)
    existing = {r[1] for r in cursor.execute("PRAGMA table_info(smm_posts)").fetchall()}
    new_cols = {
        "platform":     "TEXT DEFAULT ''",
        "account_name": "TEXT DEFAULT ''",
        "content":      "TEXT DEFAULT ''",
        "media_path":   "TEXT DEFAULT ''",
        "posted_at":    "TEXT DEFAULT NULL",
        "updated_at":   "TEXT DEFAULT (datetime('now'))",
    }
    for col, definition in new_cols.items():
        if col not in existing:
            try:
                cursor.execute(f"ALTER TABLE smm_posts ADD COLUMN {col} {definition}")
            except sqlite3.OperationalError:
                pass  # column may have been added by a concurrent migration

    conn.commit()


def seed_smm_db(posts: list[dict], dry_run: bool = False) -> int:
    """Insert posts into Social Media Manager DB. Returns count inserted."""
    if dry_run:
        print("  [DRY RUN] Would insert these posts:")
        for p in posts:
            print(f"    [{p['platform']:12}] {p['title']}")
            print(f"              Scheduled: {p['scheduled_at']}")
        return 0

    if not DB_AVAILABLE:
        print("  ⚠️  DB not available — skipping seed")
        return 0

    conn = get_conn()
    _ensure_smm_tables(conn)

    # Avoid duplicates: skip if same platform + title already exists
    cursor = conn.cursor()
    cursor.execute("SELECT platform, title FROM smm_posts WHERE platform IS NOT NULL")
    existing = {(r[0], r[1]) for r in cursor.fetchall()}

    inserted = 0
    for post in posts:
        key = (post["platform"], post["title"])
        if key in existing:
            print(f"  ⏭️  Already exists: [{post['platform']:12}] {post['title']}")
            continue

        cursor.execute("""
            INSERT INTO smm_posts
                (platform, account_name, title, content, media_path,
                 hashtags, status, scheduled_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            post["platform"],
            post["account_name"],
            post["title"],
            post["content"],
            post["media_path"],
            post["hashtags"],
            post["status"],
            post["scheduled_at"],
            post["notes"],
        ))
        inserted += 1
        print(f"  ✅ Seeded: [{post['platform']:12}] {post['title']}")
        print(f"              ⏰ {post['scheduled_at']}")

    conn.commit()
    conn.close()
    return inserted


def show_status() -> None:
    """Show current SMM queue status."""
    if not DB_AVAILABLE:
        print("  ⚠️  DB not available")
        return

    conn = get_conn()
    _ensure_smm_tables(conn)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT platform, account_name, title, status, scheduled_at
        FROM smm_posts
        ORDER BY scheduled_at ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("  📭  No posts in queue yet")
        return

    print(f"\n  {'Platform':12} {'Account':20} {'Status':10} {'Scheduled':20} Title")
    print("  " + "─" * 90)
    for r in rows:
        platform, account, title, status, sched = r
        status_icon = {"scheduled": "⏰", "draft": "📝", "posted": "✅", "failed": "❌"}.get(status, "?")
        print(f"  {platform:12} {account:20} {status_icon} {status:8} {(sched or 'Not set'):20} {title[:45]}")


# ─── Launch Guide ─────────────────────────────────────────────────────────────
LAUNCH_GUIDE = """
╔══════════════════════════════════════════════════════════════════════════════╗
║              🚀  LINKEDIN CAMPAIGN LAUNCH GUIDE — March 2026               ║
║              Darrian Belcher | peachstatesavings.com                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — BUILD VIDEOS  (if not already done)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  python3 make_linkedin_video.py

  Output: videos/linkedin/
    ✅ linkedin_vertical_9x16.mp4   ← PRIMARY for LinkedIn
    ✅ linkedin_landscape_16x9.mp4  ← Desktop / YouTube / Facebook
    ✅ linkedin_square_1x1.mp4      ← Feed / carousel

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — UPDATE LINKEDIN PROFILE (Do this first!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Open linkedin.com → Edit Profile
  2. Set headline to:
     "Product Manager @ Visa | Building AI-Powered Finance + Resale Tools |
      Autonomous SDLC • Python • Streamlit | peachstatesavings.com"
  3. Update About section (first 300 chars are visible before "see more"):
     "I build systems that ship themselves.
      PM at Visa. Indie builder. 3 products, 1 AI pipeline, $1/night."
  4. Add peachstatesavings.com to Featured section

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — POST ON LINKEDIN (Today, Mon Mar 23, 8AM EST)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Go to linkedin.com/feed
  2. Click "Start a post"
  3. Click 📎 → Upload video → select:
       videos/linkedin/linkedin_vertical_9x16.mp4
  4. Paste the caption below (POST 2 — LONG FORM):

  ─────────────────────────────────────────────
  COPY THIS CAPTION:
  ─────────────────────────────────────────────
  I built a system that ships production code while I sleep. 🤖

  I'm a Product Manager at Visa by day.
  At night I run 3 products:
  → Peach State Savings (personal finance app)
  → SoleOps (sneaker resale platform)
  → College Confused (college prep tool)

  More ideas than hours. The bottleneck was always: shipping.

  So I took the gated SDLC I learned at Visa — and gave it to AI agents.

  ⏰ 11PM: cron kicks off 6 agents on my home lab
  🧠 Planner → ⚙️ Backend → 🎨 UI → 🧪 Tests → ✅ QA → 🚀 Git Bot → PR

  I wake up. Review. Merge. Done.

  → Guardrails in the SYSTEM, not repeated every session
  → Tests fail = nothing commits
  → Human judgment = always the final gate

  ~$1/night | $0 infra | 73+ pages shipped

  A human still drives. The AI handles the road.

  Comment "PIPELINE" for the orchestrator code. 👇

  #AI #SDLC #ProductManagement #Python #Streamlit
  ─────────────────────────────────────────────

  5. Click POST
  6. IMMEDIATELY after posting — comment the architecture diagram:
       Open LINKEDIN_POST_COPY_PASTE.txt → screenshot the ASCII diagram
       Post it as the FIRST COMMENT
  7. Like your own post (signals algorithm it's good content)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — CROSS-POST (Same day, stagger by 1 hour)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  9:00 AM  → Instagram Reels (vertical video, shorter caption)
  10:00 AM → TikTok (vertical video, hook: "POV: code ships itself 🤖")
  3:00 PM  → YouTube Shorts (vertical video, add title in YT editor)
  (Wed)    → Facebook landscape video
  (Fri)    → Twitter/X thread

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — FIRST 2 HOURS AFTER POSTING (CRITICAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ Reply to EVERY comment (even just "🙏 Thanks!")
  ✅ DM 5 people: "Hey, just posted something you might find interesting"
  ✅ React to every like/comment notification
  ✅ Do NOT edit the post after publishing (kills reach)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 6 — REVIEW ALL POSTS IN SMM DASHBOARD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Open: http://localhost:8501 → Social Media Manager (page 57)
  Tab: Queue → see all 9 scheduled posts
  Tab: Calendar → see weekly posting schedule
  Tab: Accounts → verify all platforms connected

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VIDEO FILES READY AT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  videos/linkedin/linkedin_vertical_9x16.mp4    ← LinkedIn + IG + TikTok + YT
  videos/linkedin/linkedin_landscape_16x9.mp4   ← Facebook + YouTube + Twitter
  videos/linkedin/linkedin_square_1x1.mp4       ← LinkedIn feed / carousel

══════════════════════════════════════════════════
🎯 TARGET: 5,000 LinkedIn views | 200 reactions | 30+ comments
══════════════════════════════════════════════════
"""


# ─── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="LinkedIn Campaign Launch — seeds SMM DB + prints posting guide"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview posts without writing to DB")
    parser.add_argument("--status", action="store_true",
                        help="Show current SMM post queue status")
    args = parser.parse_args()

    print("╔════════════════════════════════════════════════════════════╗")
    print("║   📢  LinkedIn Campaign Launch — Darrian Belcher          ║")
    print("║   🍑  Peach State Savings | March 2026                    ║")
    print("╚════════════════════════════════════════════════════════════╝\n")

    if args.status:
        print("📋 Current SMM Post Queue:")
        show_status()
        return

    # Check if videos exist
    print("📁 Checking video assets...")
    videos = {
        "Vertical  (9:16)":  VERTICAL_VIDEO,
        "Landscape (16:9)":  LANDSCAPE_VIDEO,
        "Square    (1:1) ":  SQUARE_VIDEO,
    }
    all_ready = True
    for label, path in videos.items():
        if path.exists():
            size = path.stat().st_size / (1024 * 1024)
            print(f"  ✅  {label} — {path.name} ({size:.1f}MB)")
        else:
            print(f"  ⚠️   {label} — NOT FOUND: {path}")
            print(f"       Run: python3 make_linkedin_video.py")
            all_ready = False

    if not all_ready:
        print("\n  💡 Tip: run `python3 make_linkedin_video.py` first to build all videos")
        print("  ℹ️  Continuing with DB seeding (videos not required for seeding)\n")

    # Seed DB
    print("\n📥 Seeding Social Media Manager post queue...")
    posts = _build_post_queue()
    count = seed_smm_db(posts, dry_run=args.dry_run)

    if not args.dry_run and count > 0:
        print(f"\n  ✅ {count} posts seeded into SMM DB")
        print("  📱 View at: http://localhost:8501 → Social Media Manager → Queue tab")
    elif not args.dry_run and count == 0:
        print("  ℹ️  All posts already exist in DB (no duplicates inserted)")

    # Print the launch guide
    print(LAUNCH_GUIDE)


if __name__ == "__main__":
    main()
