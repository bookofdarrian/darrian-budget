#!/usr/bin/env python3
"""
seed_comeback_posts.py
Seeds the "Comeback Campaign — March 22, 2026" posts into the Social Media Manager.

The angle: Both sites went down. Here's what I built while you waited.

Run: python3 seed_comeback_posts.py
Then: open http://100.95.125.112:8501/social_media_manager → Queue tab
"""

import sqlite3, os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "budget.db")
NOW     = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
CAMPAIGN = "🔴→✅ Comeback Campaign — March 22, 2026"

# ─────────────────────────────────────────────────────────────────────────────
# CAPTIONS
# ─────────────────────────────────────────────────────────────────────────────

IG_PERSONAL = """Both sites went down this morning. 🔴

Most people would have just rebooted.

I reviewed everything instead.

Here's what just shipped while peachstatesavings.com + getsoleops.com were offline 👇

🍑 Peach State Savings — UPDATED
• Faster load times across all 140+ pages
• Cleaner dashboard UI
• Still completely free
→ peachstatesavings.com is back online ✅

👟 SoleOps — UPDATED
• ARB scanner running cleaner
• Inventory alerts improved
• AI listing generator refined
• April launch still on track
→ getsoleops.com is back ✅

The build never stops. A maintenance window is just another sprint.

If you've been sleeping on these — now's the time.

Links in bio 🔗"""

IG_PERSONAL_HASHTAGS = "#buildinpublic #blacktech #solofounder #indiedev #AI #peachstatesavings #soleops #atlanta #atl #python #streamlit #sideproject #sneakerresale #personalfinance #bookofdarrian"

IG_PSS = """We were down. Now we're back. Better. 🍑

peachstatesavings.com had scheduled maintenance this morning.

Here's what changed while we were offline:
✅ Performance improvements across all pages
✅ UI polish on the main dashboard
✅ Faster load times on mobile

Your data is safe. Your budget is intact. And the app just got better.

Visit peachstatesavings.com — free personal finance OS, 140+ pages, AI-powered."""

IG_PSS_HASHTAGS = "#peachstatesavings #personalfinance #budgeting #financialfreedom #buildingwealth #AI #moneymanagement #atlanta #moneytips #budgetapp"

TIKTOK_PERSONAL = """sites went down → used the time to ship instead 😭✅

maintenance windows hit different when you built the whole thing yourself 

🍑 peachstatesavings.com — back up ✅ (140+ page personal finance OS)
👟 getsoleops.com — back up ✅ (sneaker resale suite, april launch)

built solo from a home server while working full-time at Visa 🤯

follow the build → @bookofdarrian"""

TIKTOK_PERSONAL_HASHTAGS = "#buildinpublic #techlife #softwareengineer #sideproject #ai #blacktech #solofounder #sneakers #personalfinance #selfhosted"

TIKTOK_SOLEOPS = """the website went down. the arbitrage scanner kept running 🤖

SoleOps monitors sneaker prices 24/7 even when the dashboard is offline. Telegram alerts don't stop.

this is what $0/month infrastructure built on a home server looks like.

April 2026 launch. early access → getsoleops.com"""

TIKTOK_SOLEOPS_HASHTAGS = "#sneakerresale #soleops #sneakers #jordans #ebay #mercari #flipping #hustle #sidehustle #solofounder #buildinpublic"

TWITTER_THREAD = """Both of my sites went down this morning.

Here's what I built while they were offline. 🧵

---

peachstatesavings.com + getsoleops.com — both down.

Instead of just rebooting, I audited everything:
• Load times
• UI consistency
• Mobile experience
• New features waiting to ship

Maintenance windows are just unscheduled sprints when you built the whole thing yourself.

---

What just shipped on Peach State Savings:

• Performance improvements across 140+ pages
• Dashboard UI polish
• Faster cold start

Still free. Still self-hosted. Still runs on a server in my house.

→ peachstatesavings.com ✅ back online

---

SoleOps update while we were down:

• ARB scanner — tighter logic
• Inventory alerts — improved
• AI listing generator — refined

April launch still on track. First 25 signups get 30 days free Pro.

→ getsoleops.com ✅ back online
→ Early access list open now

---

The thing about building solo on a home server:

You own the uptime AND the downtime.

No ticket to file. No SLA to meet. Just you, the logs, and a decision to make it better before you bring it back up.

That's the build mentality. Every outage is a ship opportunity.

---

Both sites are back up. Better than before.

🍑 peachstatesavings.com — free personal finance OS (140+ pages)
👟 getsoleops.com — sneaker resale suite (April launch)
🎓 collegeconfused.org — free first-gen college prep

@bookofdarrian — follow the build.

#buildinpublic #solofounder #blacktech #AI"""

TWITTER_HASHTAGS = "#BuildInPublic #SoloFounder #BlackTech #AI #TPM"

FB_PERSONAL = """Real talk — both of my sites went down this morning. peachstatesavings.com and getsoleops.com.

When you're a solo builder running everything on a home server you built yourself, downtime hits different. There's no ops team to page. No incident commander to escalate to. Just you, the logs, and the choice of what to do next.

So I used the window.

I reviewed every major page on Peach State Savings. Fixed load performance. Polished the UI on things that had been bugging me for weeks. Shipped an improvement I'd been sitting on.

I audited SoleOps — tightened up the ARB scanner logic, improved the Telegram alert formatting, refined the AI listing generator output. April launch is still on track.

Both sites are back online now. Better than they were this morning.

Here's the thing about building in public that nobody talks about: the outages are part of the story. They're not failures — they're proof you're running something real. Something live. Something that actual people depend on.

peachstatesavings.com — 140+ page personal finance OS. Free.
getsoleops.com — sneaker resale suite. April 2026 launch. Early access open.
collegeconfused.org — free AI college prep for first-gen students. Always free.

If you've been meaning to check these out, today's a good day. Everything is fresh. 🍑

Follow the build: @bookofdarrian everywhere."""

FB_PSS = """📢 peachstatesavings.com experienced a brief outage this morning.

We're back online — and we used the downtime to ship improvements:

✅ Performance upgrades across all pages
✅ Dashboard UI refinements
✅ Mobile experience improvements

Your account data is secure and intact.

Thank you for your patience. The platform is stronger for it. 🍑

Visit peachstatesavings.com and let us know what you think in the comments 👇"""

FB_PSS_HASHTAGS = "#peachstatesavings #personalfinance #budgeting #AI #moneymanagement"

LINKEDIN = """Both of my production sites went down this morning.

My first instinct: reboot and move on.

My second instinct: wait. What can I ship?

That second instinct is what I've been training since I became a TPM at Visa. Downtime isn't just an ops problem — it's an unscheduled product sprint if you treat it right.

Here's what I did in the window:

→ Audited performance bottlenecks across 140+ Streamlit pages
→ Identified 3 UX improvements I'd been deferring
→ Shipped a feature update I'd been sitting on for two weeks
→ Tightened the SoleOps ARB scanner logic
→ Reviewed the deployment pipeline end-to-end

Both sites are back up. Stronger.

The larger point: I run three production platforms solo — peachstatesavings.com, getsoleops.com, collegeconfused.org — on a home server, while working as a TPM at Visa. The discipline that makes that possible isn't just technical. It's the Visa-trained habit of treating every incident as a system improvement opportunity, not just a recovery event.

That's what SDLC culture does to you. Even your downtime has a retrospective.

Both sites live. Both better. 🍑"""

LINKEDIN_HASHTAGS = "#TPM #BuildInPublic #ProductManagement #AI #IndieHacker #SDLC #SoloFounder"

YT_SHORTS = """My site went down. Here's everything I shipped in 1 hour. ⚡

Both peachstatesavings.com and getsoleops.com went down this morning.

Instead of just rebooting, I audited everything and shipped improvements before bringing them back online.

This is what solo building looks like when you own the whole stack.

📊 peachstatesavings.com — free personal finance OS (140+ pages)
👟 getsoleops.com — sneaker resale suite (April 2026 launch)
🎓 collegeconfused.org — free first-gen AI college prep

Follow the build: @bookofdarrian"""

YT_HASHTAGS = "#buildinpublic #solofounder #streamlit #python #ai #shorts #blacktech"


# ─────────────────────────────────────────────────────────────────────────────
# SEED
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ DB not found at {DB_PATH}")
        print("   Make sure you've run the app at least once to initialize the database.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # Ensure tables exist (safe even if they already do)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS smm_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            display_name TEXT NOT NULL,
            platform TEXT NOT NULL,
            account_type TEXT DEFAULT 'personal',
            handle TEXT DEFAULT '',
            profile_url TEXT DEFAULT '',
            follower_count INTEGER DEFAULT 0,
            color TEXT DEFAULT '#1da1f2',
            active INTEGER DEFAULT 1,
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS smm_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL DEFAULT '',
            caption TEXT DEFAULT '',
            hashtags TEXT DEFAULT '',
            post_type TEXT DEFAULT 'short',
            status TEXT DEFAULT 'draft',
            account_ids TEXT DEFAULT '',
            scheduled_at TEXT DEFAULT NULL,
            published_at TEXT DEFAULT NULL,
            media_urls TEXT DEFAULT '',
            link TEXT DEFAULT '',
            campaign TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()

    # Seed accounts if none exist
    cur.execute("SELECT COUNT(*) FROM smm_accounts")
    if cur.fetchone()[0] == 0:
        defaults = [
            ("bookofdarrian",       "YouTube Shorts", "personal",  "@bookofdarrian",       "#ff0000"),
            ("bookofdarrian",       "TikTok",         "personal",  "@bookofdarrian",       "#000000"),
            ("bookofdarrian",       "Instagram",      "personal",  "@bookofdarrian",       "#e1306c"),
            ("bookofdarrian",       "Twitter/X",      "personal",  "@bookofdarrian",       "#1da1f2"),
            ("bookofdarrian",       "Facebook",       "personal",  "bookofdarrian",        "#1877f2"),
            ("bookofdarrian",       "LinkedIn",       "personal",  "darrian-belcher",      "#0077b5"),
            ("Peach State Savings", "YouTube Shorts", "business",  "@peachstatesavings",   "#ff0000"),
            ("Peach State Savings", "TikTok",         "business",  "@peachstatesavings",   "#000000"),
            ("Peach State Savings", "Instagram",      "business",  "@peachstatesavings",   "#e1306c"),
            ("Peach State Savings", "Facebook",       "business",  "PeachStateSavings",    "#1877f2"),
        ]
        for d in defaults:
            cur.execute(
                "INSERT INTO smm_accounts (display_name, platform, account_type, handle, color) VALUES (?,?,?,?,?)", d
            )
        conn.commit()
        print("✅ Seeded 10 accounts")

    # Get account IDs
    cur.execute("SELECT id, display_name, platform FROM smm_accounts ORDER BY id")
    rows   = cur.fetchall()
    acc_id = {(row[1], row[2]): row[0] for row in rows}

    def aid(name, platform):
        return str(acc_id.get((name, platform), ""))

    # Clear old posts from this campaign to avoid duplicates on re-run
    cur.execute("DELETE FROM smm_posts WHERE campaign = ?", (CAMPAIGN,))
    conn.commit()

    # Media paths (relative, for reference in notes)
    DASHBOARD_IMG  = "static/dashboard_screenshot.png"
    HERO_IMG       = "static/hero_screenshot.jpg"
    VERTICAL_VID   = "videos/final_vertical.mp4"
    LINKEDIN_IMG   = "linkedin_diagram.png"

    # ── All 9 posts ────────────────────────────────────────────────────────────
    # (title, caption, hashtags, post_type, account_ids_str, link, media_urls, notes)
    posts = [
        (
            "🐦 Twitter/X — 6-tweet comeback thread",
            TWITTER_THREAD, TWITTER_HASHTAGS, "thread",
            aid("bookofdarrian", "Twitter/X"),
            "https://peachstatesavings.com",
            DASHBOARD_IMG,
            "POST FIRST at 9am. Each '---' separator = new tweet. Attach dashboard screenshot to tweet 3 or 4."
        ),
        (
            "📸 Instagram Carousel — Sites back up (bookofdarrian)",
            IG_PERSONAL, IG_PERSONAL_HASHTAGS, "photo",
            aid("bookofdarrian", "Instagram"),
            "https://peachstatesavings.com",
            f"{DASHBOARD_IMG},{HERO_IMG}",
            "POST at 10am. Carousel: 5 slides. Slide 1: 'Both sites went down 🔴 here's what I built.' Slide 2-3: PSS+SoleOps updates. Slide 4: dashboard screenshot. Slide 5: CTA."
        ),
        (
            "🎵 TikTok — Sites down → ship mode (bookofdarrian)",
            TIKTOK_PERSONAL, TIKTOK_PERSONAL_HASHTAGS, "short",
            aid("bookofdarrian", "TikTok"),
            "https://peachstatesavings.com",
            VERTICAL_VID,
            "POST at 10am. HOOK on screen: 'My sites went down. Then this happened.' Use final_vertical.mp4 as base. Show status pages flipping down→up. 60 sec max."
        ),
        (
            "💼 LinkedIn — TPM downtime retrospective",
            LINKEDIN, LINKEDIN_HASHTAGS, "post",
            aid("bookofdarrian", "LinkedIn"),
            "https://peachstatesavings.com",
            LINKEDIN_IMG,
            "POST at 11am. Attach linkedin_diagram.png. Strong LinkedIn hook: 'Both of my production sites went down this morning.' This will perform very well with the TPM/PM audience."
        ),
        (
            "📸 Instagram — PSS business comeback post",
            IG_PSS, IG_PSS_HASHTAGS, "photo",
            aid("Peach State Savings", "Instagram"),
            "https://peachstatesavings.com",
            DASHBOARD_IMG,
            "POST at 12pm. Business tone. Attach dashboard screenshot. Short and clean — maintenance → improvements → back online."
        ),
        (
            "📘 Facebook — Personal comeback story (bookofdarrian)",
            FB_PERSONAL, "", "post",
            aid("bookofdarrian", "Facebook"),
            "https://peachstatesavings.com",
            "",
            "POST at 1pm. Text only or attach hero screenshot. Long-form storytelling. Tag friends directly in Facebook. Great for family/personal network reach."
        ),
        (
            "📘 Facebook — PSS business page announcement",
            FB_PSS, FB_PSS_HASHTAGS, "post",
            aid("Peach State Savings", "Facebook"),
            "https://peachstatesavings.com",
            "",
            "POST at 1pm. Professional and brief. Reassure users data is safe. Announce improvements."
        ),
        (
            "🎵 TikTok — ARB scanner never sleeps (SoleOps angle)",
            TIKTOK_SOLEOPS, TIKTOK_SOLEOPS_HASHTAGS, "short",
            aid("bookofdarrian", "TikTok"),
            "https://getsoleops.com",
            VERTICAL_VID,
            "POST at 7pm — peak TikTok discovery hour. HOOK: 'The site was down. The ARB scanner kept running.' Show Telegram notification. 30 sec. Pure sneaker resale audience hook."
        ),
        (
            "▶️ YouTube Shorts — Downtime speedrun (bookofdarrian)",
            YT_SHORTS, YT_HASHTAGS, "short",
            aid("bookofdarrian", "YouTube Shorts"),
            "https://peachstatesavings.com",
            VERTICAL_VID,
            "POST when video is recorded. TITLE: 'My site went down. Here's everything I shipped in 1 hour. ⚡' Concept: split screen terminal + screen record of improvements. End: both sites loading ✅."
        ),
    ]

    for title, caption, hashtags, post_type, account_ids, link, media_urls, notes in posts:
        cur.execute("""
            INSERT INTO smm_posts
            (title, caption, hashtags, post_type, status, account_ids, link,
             campaign, media_urls, notes, created_at)
            VALUES (?, ?, ?, ?, 'draft', ?, ?, ?, ?, ?, ?)
        """, (title, caption, hashtags, post_type, account_ids, link,
              CAMPAIGN, media_urls, notes, NOW))

    conn.commit()
    conn.close()

    print()
    print("=" * 62)
    print("🍑  Comeback Campaign Posts Seeded!")
    print("=" * 62)
    print(f"  ✅ {len(posts)} posts added as drafts")
    print(f"  📋 Campaign: {CAMPAIGN}")
    print()
    print("  Posts created (in posting order):")
    for i, (title, *_) in enumerate(posts, 1):
        print(f"  {i:2}. {title}")
    print()
    print("  ─────────────────────────────────────────────────────")
    print("  POSTING SCHEDULE — Sunday March 22, 2026")
    print("  ─────────────────────────────────────────────────────")
    print("  9am   → Twitter/X thread (post FIRST — sets the narrative)")
    print("  10am  → Instagram carousel + TikTok (personal)")
    print("  11am  → LinkedIn TPM story")
    print("  12pm  → Instagram PSS business")
    print("  1pm   → Facebook personal + PSS business")
    print("  7pm   → TikTok SoleOps/ARB angle")
    print("  Later → YouTube Short (record video first)")
    print()
    print("  NEXT STEP:")
    print("  → Open: http://100.95.125.112:8501/social_media_manager")
    print("  → Go to 'Queue' tab → filter by this campaign")
    print("  → Review each draft → copy caption → 1-click post")
    print()
    print("  Media files ready at:")
    print("  → static/dashboard_screenshot.png   (IG, Twitter, LinkedIn)")
    print("  → static/hero_screenshot.jpg         (IG carousel slide)")
    print("  → videos/final_vertical.mp4           (TikTok, YouTube Short)")
    print("  → linkedin_diagram.png                (LinkedIn)")
    print()


if __name__ == "__main__":
    main()
