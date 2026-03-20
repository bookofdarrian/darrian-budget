#!/usr/bin/env python3
"""
seed_social_posts.py
Seeds all 10 ready-to-post drafts into the Social Media Manager database.
Open /social_media_manager in your app, go to Queue tab, and review/post each one.
"""

import sqlite3, os, sys
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "budget.db")
NOW     = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

# ── Captions ───────────────────────────────────────────────────────────────────

IG_PERSONAL = """Built something I'm proud of. 🍑

Over the past year, quietly building while working full-time at @Visa and finishing my @GeorgiaTech degree. Three AI-powered platforms. One home server. 140+ pages of code.

Here's what we've built:

📊 Peach State Savings — personal finance OS
Your budget, investments, RSU calendar, cash flow, AI chat — all in one place.
→ peachstatesavings.com (free)

👟 SoleOps — sneaker resale business suite
Inventory manager, AI listing generator, P&L dashboard, live price monitor, ARB scanner with Telegram alerts.
→ getsoleops.com (launching April 2026 — early access open)

🎓 College Confused — free AI college prep
FAFSA guide, essay assistant, scholarship tracker, AI mock interviews. Built for first-gen students. Always free.
→ collegeconfused.org

This isn't a solo W. I have to shout out:

🙏 @Anthropic / Claude AI — my co-creator on every line
🙏 The Streamlit team — for making this possible without a frontend team
🙏 Georgia Tech — for teaching me to think in systems
🙏 My Visa family — for the TPM discipline that ships things
🙏 The ATL community — for riding with me since day one
🙏 My family — every sacrifice, every belief — this is all for y'all
🙏 Dr. Bedir — for promoting the growth of beautiful minds 🙏
🙏 Josh, Keona, Nylah, Omar, Noah, Liddon, Nauri, Metri, Joa, Juan + the whole Menace2 GC — y'all kept me going
🙏 Vine — you were there from the start
🙏 252 // 525 — you already know
🙏 RIP Danny 🕊️ — building for you too
🙏 And you — for every DM, comment, and "keep going" when I needed it

One year ago this was a spreadsheet. Today it's three live products with real users.

More coming. Subscribe to the channel for the full build story.

@bookofdarrian everywhere.
👇 Links in bio"""

IG_PSS = """Peach State Savings isn't just an app. It's a personal finance OS built by someone who actually needed it.

140+ pages. One goal: know exactly where your money is going and where it should go next.

✅ Expense & income tracking
✅ Paycheck + Georgia state tax calculator
✅ RSU vest calendar
✅ Net worth tracker
✅ Cash flow forecast
✅ AI budget chat (powered by Claude)
✅ Debt payoff planner
✅ Investment rebalancer
✅ Crypto, dividend, subscription trackers
✅ SoleOps sneaker resale suite
✅ And 130+ more pages...

Free to use. Self-hosted. Your data stays yours.

Visit peachstatesavings.com →

Big shoutout to everyone who has been along for this build. The product is better because of your feedback. 🍑"""

TIKTOK_PERSONAL = """I built 140 AI-powered app pages while working at Visa and going to Georgia Tech 🤯

Three platforms. One home server. Zero team.

→ Peach State Savings (personal finance OS) — peachstatesavings.com
→ SoleOps (sneaker resale suite) — getsoleops.com
→ College Confused (free first-gen college prep) — collegeconfused.org

BIGGEST shoutouts to: Claude AI (@anthropic), the Streamlit team, Georgia Tech, my Visa fam, Dr. Bedir, my family, Josh, Keona, Nylah, Omar, Noah, Liddon, Nauri, Metri, Joa, Juan, Vine, the Menace2 GC, 252 // 525, RIP Danny 🕊️ 💙

None of this was solo. We built this together.

Links in bio 🍑"""

TIKTOK_PSS = """This Telegram alert made me $200 before breakfast 👀

I built SoleOps — an AI system that monitors sneaker prices on eBay and Mercari 24/7. When a pair on my watchlist drops below my max buy price, it texts me instantly.

The alert fired at 7am. I bought it. Flipped it same day. $200 profit. The tool paid for itself 10× over.

SoleOps launches April 2026. Early access at getsoleops.com 🔗 link in bio"""

FB_PERSONAL = """I've been building in silence for a while. Today I'm sharing everything.

Over the past year — while working full-time as a Technical Program Manager at Visa and finishing my Georgia Tech data analytics degree — I've been building three AI-powered platforms from a home server in my house.

📊 Peach State Savings (peachstatesavings.com)
A 140+ page personal finance operating system. Budget tracking, investment monitoring, RSU calendar, cash flow forecasting, AI budget chat, and a full sneaker resale business suite called SoleOps. Free for everyone.

👟 SoleOps (getsoleops.com — launching April 2026)
A full operating system for sneaker resellers. AI listing generator, inventory manager, P&L dashboard, live price monitor, and an arbitrage scanner that texts you on Telegram when a pair you're watching drops below your buy price. First 25 signups get 30 free Pro days.

🎓 College Confused (collegeconfused.org)
Free AI-powered college prep for first-gen students. FAFSA walkthrough, essay assistant, scholarship tracker, AI mock interview prep. I was a first-gen student — this is the platform I wish I'd had. Always free.

I could not have done any of this without:

❤️ Anthropic / Claude AI — genuine co-creator on every feature
❤️ The Streamlit framework team
❤️ Georgia Tech for teaching me to build in systems
❤️ My colleagues at Visa for the program discipline I apply to every build
❤️ My family — every sacrifice, every "go do what you gotta do" — this is for you
❤️ Dr. Bedir — for promoting the growth of beautiful minds. Thank you for seeing us.
❤️ Josh, Keona, Nylah, Omar, Noah, Liddon, Nauri, Metri, Joa, Juan + the whole Menace2 GC — y'all kept me going
❤️ Vine — you were there from the start. Still building for you.
❤️ 252 // 525 — you already know. Always.
❤️ RIP Danny 🕊️ — gone too soon. This one's for you too.
❤️ Everyone who's ever used these tools and left feedback

To the Atlanta community — you've been with me since the beginning and it shows.

If you know someone who'd benefit from any of these tools, please share.
If you want to follow the build journey, subscribe to my YouTube: @bookofdarrian

One year ago I had a spreadsheet. Today I have three live products and a server that builds features while I sleep.

This is just the beginning. 🍑"""

FB_PSS = """🍑 Peach State Savings — Built for people who actually want to understand their money.

140+ pages covering everything from day-to-day budgeting to RSU vest calendars to sneaker resale P&L to AI-powered financial conversations.

All free. All yours. Live at peachstatesavings.com.

New this week: Social Media Manager — plan, schedule, and cross-post content to YouTube Shorts, TikTok, Instagram, Facebook, and Twitter/X all from one place. AI writes your captions for every platform automatically.

Building this has been a team effort. Massive thanks to our users, the Anthropic team, and the open source community that makes all of this possible.

What feature do you want to see next? Drop it in the comments 👇"""

TWITTER_THREAD = """🧵 THREAD: I built 140 AI-powered apps while working at Visa, going to Georgia Tech, and running a sneaker business.

Here's everything, and everyone who made it possible. 🍑 (1/12)

---

2/ Three platforms. One home server. Zero outside funding.
→ Peach State Savings (peachstatesavings.com) — personal finance OS
→ SoleOps (getsoleops.com) — sneaker resale suite
→ College Confused (collegeconfused.org) — first-gen college prep
All live. All real. All built by me + AI.

---

3/ Peach State Savings is a 140+ page financial operating system.
Budget tracker, income manager, RSU vest calendar, portfolio monitor, cash flow forecast, debt payoff planner, investment rebalancer, AI budget chat, crypto tracker, sneaker resale P&L, tax projection...
Free at peachstatesavings.com

---

4/ SoleOps is the sneaker reseller's operating system.
The feature I'm most proud of: an ARB scanner that monitors Mercari 24/7 and sends a Telegram alert to my phone when a pair drops below my max buy price.
It texted me a $200 opportunity before breakfast last month.

---

5/ College Confused is personal.
I was a first-gen college student. No one in my family knew what FAFSA was. I got into 25 schools.
CC is the free AI platform I wish I'd had. FAFSA walkthrough, essay assistant, scholarship tracker, AI mock interviews.
Always free. collegeconfused.org

---

6/ The tech: Python + Streamlit. SQLite/PostgreSQL. Anthropic Claude API.
Home server running Proxmox. Tailscale VPN. Nginx. Docker. Grafana + Prometheus.
And the wildest part — an overnight AI dev system that reads a backlog and builds features WHILE I SLEEP. Tested. Committed. Deployed.

---

7/ Now the most important part. SHOUTOUTS. Nothing I've built happened alone. Let me be explicit about that.

---

8/ @AnthropicAI + Claude — my co-creator.
Claude isn't just a tool in my apps. It's the dev partner that reviews my code, writes features, debugs errors, and talks to my users about their money.
They built something that genuinely changed what one person can build.

---

9/ The Streamlit team — you lowered the barrier.
I'm a TPM, not a frontend engineer. Streamlit let me build 140 production-quality app pages in Python, no React required.
If you want to build something real and know Python — streamlit.io. No more excuses.

---

10/ My Visa + Georgia Tech communities.
TPM at Visa taught me how to ship real programs. Georgia Tech taught me to think in data and systems.
Both show up in every product decision I make.

---

11/ My people. This is for y'all.
My family — every sacrifice, every belief, everything.
Dr. Bedir — for promoting the growth of beautiful minds.
Josh, Keona, Nylah, Omar, Noah, Liddon, Nauri, Metri, Joa, Juan + the whole Menace2 GC.
Vine — you were there from the start.
252 // 525 — you already know.
RIP Danny 🕊️ — gone too soon. Building for you.

---

12/ If you made it here:
✅ peachstatesavings.com — free personal finance OS
👟 getsoleops.com — sneaker resale suite (April launch)
🎓 collegeconfused.org — free first-gen college prep
📱 @bookofdarrian — follow the build

One year ago: a spreadsheet.
Today: three live products.
Tomorrow: $1K MRR.

The build continues. 🍑"""

YT_SHORT_A = """My computer built me a new app feature while I was sleeping. Let me show you.

Every night my homelab reads a backlog file, picks the highest priority item, has Claude AI write the code, run the tests, commit to GitHub, and by morning there's a new feature live in production.

This system has built 140+ pages across three platforms — a personal finance OS, a sneaker resale business suite, and a college prep platform for first-gen students.

None of it was solo. Shoutout to Claude AI, the Streamlit team, Georgia Tech, Dr. Bedir, my family, Josh, Keona, Nylah, Omar, Noah, Liddon, Nauri, Metri, Joa, Juan, the Menace2 GC, Vine, 252//525, and RIP Danny 🕊️

Links in bio. Everything is free. Try it.

peachstatesavings.com | getsoleops.com | collegeconfused.org"""

REEL_FIRSTGEN = """Nobody in my family had ever gone to a 4-year college. I figured it out, got into 25 schools, and built a free app so nobody has to figure it out alone again.

That app is College Confused — free AI college prep for first-gen students. FAFSA walkthrough, essay assistant, scholarship tracker, AI mock interviews. collegeconfused.org — always free.

But that's just one of three products I built from a home server in my house — while working full-time at Visa and finishing my Georgia Tech degree.

Peach State Savings: 140-page personal finance OS.
SoleOps: AI sneaker resale suite.
College Confused: free first-gen college prep.

Links in bio. Shoutout to everyone who believed before there was anything to believe in. This is for y'all. 🙏"""

# ── Hashtags ───────────────────────────────────────────────────────────────────

HT_PERSONAL  = "#buildInPublic #indiedev #AI #personalfinance #sneakerresale #firstgen #atlanta #atl #atlcreator #sideproject #streamlit #python #anthropic #peachstatesavings #soleops #collegeconfused #bookofdarrian #tpm #visatech"
HT_FINANCE   = "#personalfinance #budgeting #financialfreedom #buildingwealth #peachstatesavings #AI #python #streamlit #atlanta #moneymanagement"
HT_TIKTOK    = "#buildinpublic #ai #tpm #sideproject #sneakerresale #personalfinance #firstgen #collegeprep #atlanta #bookofdarrian #peachstatesavings #soleops"
HT_RESALE    = "#sneakerresale #soleops #sneakers #jordans #ebay #mercari #stockx #flipping #reselling #sneakerhead #404solearchive #hustle #sidehustle"
HT_TWITTER   = "#buildInPublic #AI #TPM #firstgen #peachstatesavings #soleops #collegeconfused"
HT_REEL      = "#firstgen #firstgeneration #collegeprep #collegeconfused #fafsa #ai #buildInPublic #atlanta #bookofdarrian #peachstatesavings"


def main():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # ── Ensure tables exist ────────────────────────────────────────────────────
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

    # ── Get or seed accounts ───────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM smm_accounts")
    if cur.fetchone()[0] == 0:
        defaults = [
            ("bookofdarrian",    "YouTube Shorts", "personal", "@bookofdarrian",    "#ff0000"),
            ("bookofdarrian",    "TikTok",         "personal", "@bookofdarrian",    "#000000"),
            ("bookofdarrian",    "Instagram",      "personal", "@bookofdarrian",    "#e1306c"),
            ("bookofdarrian",    "Twitter/X",      "personal", "@bookofdarrian",    "#1da1f2"),
            ("bookofdarrian",    "Facebook",       "personal", "bookofdarrian",     "#1877f2"),
            ("Peach State Savings", "YouTube Shorts", "business", "@peachstatesavings", "#ff0000"),
            ("Peach State Savings", "TikTok",         "business", "@peachstatesavings", "#000000"),
            ("Peach State Savings", "Instagram",      "business", "@peachstatesavings", "#e1306c"),
            ("Peach State Savings", "Twitter/X",      "business", "@pss_finance",        "#1da1f2"),
            ("Peach State Savings", "Facebook",       "business", "PeachStateSavings",  "#1877f2"),
        ]
        for d in defaults:
            cur.execute(
                "INSERT INTO smm_accounts (display_name, platform, account_type, handle, color) VALUES (?,?,?,?,?)", d
            )
        conn.commit()
        print("✅ Seeded 10 accounts")

    # ── Get account IDs ────────────────────────────────────────────────────────
    cur.execute("SELECT id, display_name, platform FROM smm_accounts ORDER BY id")
    rows   = cur.fetchall()
    acc_id = {(row[1], row[2]): row[0] for row in rows}

    def aid(name, platform):
        return str(acc_id.get((name, platform), ""))

    # ── Clear old seeded posts from this campaign (if re-running) ─────────────
    cur.execute("DELETE FROM smm_posts WHERE campaign = '🍑 Launch Campaign 2026'")
    conn.commit()

    # ── Define all 10 posts ────────────────────────────────────────────────────
    CAMPAIGN = "🍑 Launch Campaign 2026"

    posts = [
        # title, caption, hashtags, post_type, account_ids_str, link, notes
        (
            "🎬 YouTube Short — AI builds while I sleep",
            YT_SHORT_A, HT_PERSONAL, "short",
            f"{aid('bookofdarrian','YouTube Shorts')}",
            "https://peachstatesavings.com",
            "Post Version A — show GitHub commit at 3am then live feature demo"
        ),
        (
            "🎵 TikTok — 140 AI apps (bookofdarrian)",
            TIKTOK_PERSONAL, HT_TIKTOK, "short",
            f"{aid('bookofdarrian','TikTok')}",
            "https://peachstatesavings.com",
            "60 sec cut — fast montage of all 140 pages"
        ),
        (
            "🎵 TikTok — $200 Telegram alert (PSS)",
            TIKTOK_PSS, HT_RESALE, "short",
            f"{aid('Peach State Savings','TikTok')}",
            "https://getsoleops.com",
            "30 sec — show Telegram notification, sneaker flip story"
        ),
        (
            "📸 Instagram Reel — First-gen to 3 products (bookofdarrian)",
            REEL_FIRSTGEN, HT_REEL, "reel",
            f"{aid('bookofdarrian','Instagram')}",
            "https://collegeconfused.org",
            "Version B — 45 sec — first-gen story angle"
        ),
        (
            "📸 Instagram Feed — Full launch post (bookofdarrian)",
            IG_PERSONAL, HT_PERSONAL, "photo",
            f"{aid('bookofdarrian','Instagram')}",
            "https://peachstatesavings.com",
            "Long caption with all shoutouts — link in bio"
        ),
        (
            "📸 Instagram Feed — PSS business post",
            IG_PSS, HT_FINANCE, "photo",
            f"{aid('Peach State Savings','Instagram')}",
            "https://peachstatesavings.com",
            "Business account — 140+ pages checklist format"
        ),
        (
            "📘 Facebook — Personal launch story",
            FB_PERSONAL, "", "post",
            f"{aid('bookofdarrian','Facebook')}",
            "https://peachstatesavings.com",
            "Full story post — tag people directly in Facebook"
        ),
        (
            "📘 Facebook — PSS business page",
            FB_PSS, HT_FINANCE, "post",
            f"{aid('Peach State Savings','Facebook')}",
            "https://peachstatesavings.com",
            "PSS business page — Social Media Manager feature shoutout"
        ),
        (
            "🐦 Twitter/X — Full 12-tweet thread",
            TWITTER_THREAD, HT_TWITTER, "thread",
            f"{aid('bookofdarrian','Twitter/X')}",
            "https://peachstatesavings.com",
            "Post as thread — each --- separator is a new tweet"
        ),
        (
            "🎬 YouTube Short — PSS business (AI builds while I sleep)",
            YT_SHORT_A, HT_PERSONAL, "short",
            f"{aid('Peach State Savings','YouTube Shorts')}",
            "https://peachstatesavings.com",
            "Same Version A cut — post on PSS channel too"
        ),
    ]

    for title, caption, hashtags, post_type, account_ids, link, notes in posts:
        cur.execute("""
            INSERT INTO smm_posts
            (title, caption, hashtags, post_type, status, account_ids, link, campaign, notes, created_at)
            VALUES (?, ?, ?, ?, 'draft', ?, ?, ?, ?, ?)
        """, (title, caption, hashtags, post_type, account_ids, link, CAMPAIGN, notes, NOW))

    conn.commit()
    conn.close()

    print()
    print("=" * 55)
    print("🍑  Social Media Posts Seeded!")
    print("=" * 55)
    print(f"  ✅ {len(posts)} posts added as drafts")
    print(f"  📋 Campaign: {CAMPAIGN}")
    print()
    print("  Posts created:")
    for i, (title, *_) in enumerate(posts, 1):
        print(f"  {i:2}. {title}")
    print()
    print("  Next step:")
    print("  → Open your app: http://100.95.125.112:8501/social_media_manager")
    print("  → Go to 'Queue' tab")
    print("  → Review each draft and copy captions to the real platform")
    print()
    print("  Post order for max momentum:")
    print("  1. YouTube Short → 2. TikTok (personal) → 3. TikTok (PSS)")
    print("  4. IG Reel → 5. IG Feed (personal) → 6. IG Feed (PSS)")
    print("  7. Facebook (personal) → 8. Facebook (PSS) → 9. Twitter thread → 10. YT Short (PSS)")
    print()


if __name__ == "__main__":
    main()
