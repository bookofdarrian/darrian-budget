"""
Seed script: Kobe & Gigi shoes into soleops_inventory (status=listed, platform=eBay)
               + genuine social media posts in smm_posts.
Run: python3 seed_kobe_gigi.py
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

from utils.db import get_conn, USE_POSTGRES, init_db

init_db()

# ── 1. Ensure inventory table exists ─────────────────────────────────────────
def _ensure_inventory():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100),
                brand VARCHAR(100) NOT NULL,
                model VARCHAR(200) NOT NULL,
                colorway VARCHAR(200),
                size VARCHAR(20) NOT NULL,
                condition VARCHAR(50) DEFAULT 'New',
                purchase_price DECIMAL(10,2),
                purchase_date DATE,
                purchase_source TEXT,
                listed_platforms JSONB DEFAULT '[]',
                list_prices JSONB DEFAULT '{}',
                status VARCHAR(50) DEFAULT 'in_stock',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                colorway TEXT,
                size TEXT NOT NULL,
                condition TEXT DEFAULT 'New',
                purchase_price REAL,
                purchase_date TEXT,
                purchase_source TEXT,
                listed_platforms TEXT DEFAULT '[]',
                list_prices TEXT DEFAULT '{}',
                status TEXT DEFAULT 'in_stock',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    cur.close()
    conn.close()

_ensure_inventory()

# ── 2. Ensure SMM tables exist ────────────────────────────────────────────────
def _ensure_smm():
    conn = get_conn()
    if USE_POSTGRES:
        ts = "DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))"
        ai = "SERIAL PRIMARY KEY"
    else:
        ts = "DEFAULT (datetime('now'))"
        ai = "INTEGER PRIMARY KEY AUTOINCREMENT"

    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS smm_posts (
            id {ai},
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
            created_at TEXT {ts}
        )
    """)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS smm_campaigns (
            id {ai},
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            goal TEXT DEFAULT '',
            start_date TEXT DEFAULT NULL,
            end_date TEXT DEFAULT NULL,
            color TEXT DEFAULT '#e040fb',
            active INTEGER DEFAULT 1,
            created_at TEXT {ts}
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

_ensure_smm()

# ── 3. Seed Kobe & Gigi shoes ─────────────────────────────────────────────────
ph = "%s" if USE_POSTGRES else "?"

KOBE_SHOES = [
    {
        "brand": "Nike",
        "model": "Kobe 6 Protro",
        "colorway": "Grinch",
        "sku": "CW2190-300",
        "size": "10",
        "condition": "New",
        "purchase_price": 290.00,
        "purchase_date": "2024-12-26",
        "purchase_source": "Nike SNKRS",
        "list_prices": {"eBay": 650},
        "notes": "DS — one of Kobe's most iconic colorways. The Grinch.\nThis one means a lot. Kobe was the reason I started taking sneakers seriously. Mamba forever. 🐍💜💛",
    },
    {
        "brand": "Nike",
        "model": "Kobe 8 Protro",
        "colorway": "Court Purple",
        "sku": "FQ3549-500",
        "size": "10",
        "condition": "New",
        "purchase_price": 180.00,
        "purchase_date": "2025-01-24",
        "purchase_source": "Foot Locker",
        "list_prices": {"eBay": 320},
        "notes": "1/26 — the anniversary. Can't hold this one forever, but it hurts to let it go.",
    },
    {
        "brand": "Nike",
        "model": "Kobe 4 Protro",
        "colorway": "Wizenard",
        "sku": "FQ3544-001",
        "size": "9.5",
        "condition": "New",
        "purchase_price": 200.00,
        "purchase_date": "2025-02-10",
        "purchase_source": "Nike SNKRS",
        "list_prices": {"eBay": 395},
        "notes": "Based on Kobe's novel 'The Wizenard Series.' He really was more than a basketball player.",
    },
    {
        "brand": "Nike",
        "model": "Kobe 6 Protro",
        "colorway": "Mambacita Sweet 16",
        "sku": "DJ3596-600",
        "size": "10",
        "condition": "New",
        "purchase_price": 340.00,
        "purchase_date": "2025-05-01",
        "purchase_source": "Nike SNKRS",
        "list_prices": {"eBay": 900},
        "notes": "This one is for Gigi. Made for her Sweet 16 that never came. Every dollar from this goes toward something meaningful. 13 forever. 💜",
    },
]

conn = get_conn()
cur = conn.cursor()
added = 0
for shoe in KOBE_SHOES:
    # Check if already exists
    cur.execute(
        f"SELECT COUNT(*) FROM soleops_inventory WHERE brand={ph} AND model={ph} AND colorway={ph} AND size={ph}",
        (shoe["brand"], shoe["model"], shoe["colorway"], shoe["size"])
    )
    if cur.fetchone()[0] > 0:
        print(f"  ⏭️  Already exists: {shoe['brand']} {shoe['model']} — {shoe['colorway']} Sz {shoe['size']}")
        continue

    listed_platforms = json.dumps(["eBay"])
    list_prices      = json.dumps(shoe["list_prices"])

    cur.execute(f"""
        INSERT INTO soleops_inventory
        (user_id, sku, brand, model, colorway, size, condition,
         purchase_price, purchase_date, purchase_source,
         listed_platforms, list_prices, status, notes)
        VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})
    """, (
        1,
        shoe.get("sku", ""),
        shoe["brand"],
        shoe["model"],
        shoe["colorway"],
        shoe["size"],
        shoe["condition"],
        shoe["purchase_price"],
        shoe["purchase_date"],
        shoe["purchase_source"],
        listed_platforms,
        list_prices,
        "listed",
        shoe["notes"],
    ))
    print(f"  ✅ Added: {shoe['brand']} {shoe['model']} — {shoe['colorway']} Sz {shoe['size']} @ ${shoe['list_prices']['eBay']}")
    added += 1

conn.commit()
cur.close()
conn.close()
print(f"\n👟 {added} Kobe/Gigi shoe(s) seeded into soleops_inventory.\n")

# ── 4. Seed genuine social media posts ───────────────────────────────────────
SMM_POSTS = [
    {
        "title": "Kobe 6 Grinch — eBay Listing Drop",
        "caption": (
            "The Grinch Kobe 6s are live on eBay. 💚\n\n"
            "I been holding these. Every time I thought about listing them I'd just put them back on the shelf and stare at them. "
            "Kobe was the reason I started taking sneakers seriously — not just as hype, but as history.\n\n"
            "These aren't just shoes. They're a piece of the man. Size 10, deadstock, never worn.\n\n"
            "Link in bio if you want to give them a home that'll appreciate them. 🐍💜💛\n\n"
            "#Kobe #Kobe6 #Grinch #MambaForever #NikeKobe #SneakerCommunity #KobeProtro #Reseller #Atlanta #SoleOps"
        ),
        "hashtags": "#Kobe #Kobe6 #Grinch #MambaForever #NikeKobe #SneakerCommunity #KobeProtro #Reseller #Atlanta #SoleOps",
        "post_type": "post",
        "status": "ready",
        "campaign": "Kobe & Gigi eBay Drop",
        "notes": "Pin this one. Personal story angle. Works best on Instagram & Facebook.",
    },
    {
        "title": "Kobe 6 Mambacita Sweet 16 — Gigi Tribute Post",
        "caption": (
            "These are for Gigi. 💜\n\n"
            "Nike made the Kobe 6 Protro 'Mambacita Sweet 16' for the birthday she never got to have. "
            "I copped them on her birthday drop and haven't touched them since.\n\n"
            "Now they're on eBay. Size 10. DS.\n\n"
            "I'm not just flipping these — whoever gets them, please take care of them. "
            "This colorway isn't a flex, it's a memorial. "
            "A little girl loved this game as much as her father did, and the world lost both of them.\n\n"
            "13 forever. 🕊️\n\n"
            "#Gigi #GiannaBryant #Mambacita #Kobe #KobeBryant #MambaForever #SneakerCulture #Sweet16 #NikeKobe #Kobe6Protro"
        ),
        "hashtags": "#Gigi #GiannaBryant #Mambacita #Kobe #KobeBryant #MambaForever #SneakerCulture #Sweet16 #NikeKobe #Kobe6Protro",
        "post_type": "post",
        "status": "ready",
        "campaign": "Kobe & Gigi eBay Drop",
        "notes": "This one is emotional and intentional. Caption should stand alone. Do NOT add extra promo text.",
    },
    {
        "title": "TikTok Hook — Kobe Drop Story (30 sec)",
        "caption": (
            "POV: You've had these Kobe 6 Grinches sitting on your shelf for 2 years and you finally decide to let them go 😮‍💨\n\n"
            "Not because you need the money. Because somebody out there will actually wear and appreciate them instead of watching them sit in a box.\n\n"
            "Kobe taught us to work, to be obsessed, to care about every detail. Even these shoes are a lesson.\n\n"
            "Live on eBay now. Link in bio.\n\n"
            "#KobeBryant #Kobe6 #Grinch #SneakerTok #NikeKobe #MambaForever #SneakerFlip #Reseller #FinanceAndSneakers #SoleOps"
        ),
        "hashtags": "#KobeBryant #Kobe6 #Grinch #SneakerTok #NikeKobe #MambaForever #SneakerFlip #Reseller #FinanceAndSneakers #SoleOps",
        "post_type": "reel",
        "status": "ready",
        "campaign": "Kobe & Gigi eBay Drop",
        "notes": "Film holding the shoe, rotating in hand, shelf background. VO the caption. Trending Kobe/tribute audio.",
    },
    {
        "title": "Twitter/X Thread — Kobe shoes & what they mean",
        "caption": (
            "1/ I've been in sneakers for years. Kobes hit different. Here's why I'm listing mine and what each one meant to me. 🧵\n\n"
            "2/ The Grinch Kobe 6. He wore these in 2010, went for 38 points on Christmas Day. "
            "Wore them with a broken finger. That's the Kobe nobody talks about.\n\n"
            "3/ The Mambacita Sweet 16. Nike made these for Gigi's 16th birthday. "
            "She never turned 16. But these exist. And they're beautiful. And they hurt to look at.\n\n"
            "4/ I'm not a museum. I'm a sneakerhead with rent. But I'm asking — whoever buys these, know what you have.\n\n"
            "5/ All 4 Kobes live on eBay now. Links in bio. "
            "I want them in the hands of people who feel what I feel when they look at them. Mamba forever. 🐍"
        ),
        "hashtags": "#KobeBryant #MambaForever #Sneakers #NikeKobe #GiannaBryant #Thread",
        "post_type": "thread",
        "status": "ready",
        "campaign": "Kobe & Gigi eBay Drop",
        "notes": "Post as a thread — 5 tweets. Tweet 5 is the CTA.",
    },
    {
        "title": "Instagram Carousel — 4 Kobes, 4 Stories",
        "caption": (
            "4 Kobes. 4 stories. All live on eBay.\n\n"
            "Slide through before they're gone. 👉\n\n"
            "Each one was copped with intention. "
            "Kobe 6 Grinch, Kobe 8 Court Purple (1/26 edition), Kobe 4 Wizenard, and the one that hits hardest — the Mambacita Sweet 16.\n\n"
            "I grew up watching #8 turn into #24. Watched him win 5 rings, write a book, coach his daughter, "
            "and become something way bigger than basketball.\n\n"
            "These shoes carry that story. They deserve a real home.\n\n"
            "eBay links in bio. 💜💛\n\n"
            "#Kobe #GiannaBryant #Mambacita #NikeKobe #Kobe6 #Kobe4 #Kobe8 #MambaForever #SneakerCollection #EbaySneakers"
        ),
        "hashtags": "#Kobe #GiannaBryant #Mambacita #NikeKobe #Kobe6 #Kobe4 #Kobe8 #MambaForever #SneakerCollection #EbaySneakers",
        "post_type": "carousel",
        "status": "ready",
        "campaign": "Kobe & Gigi eBay Drop",
        "notes": "Slide 1: All 4 shoes together. Slides 2-5: One shoe each with its story. Slide 6: eBay CTA.",
    },
]

# Also seed the campaign
def _ensure_campaign(name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM smm_campaigns WHERE name={ph}", (name,))
    if cur.fetchone()[0] == 0:
        cur.execute(f"""
            INSERT INTO smm_campaigns (name, description, goal, start_date, end_date, color)
            VALUES ({ph},{ph},{ph},{ph},{ph},{ph})
        """, (
            name,
            "Tribute listing drop — Kobe Bryant and Gigi. All 4 pairs listed on eBay with personal stories.",
            "Sell all 4 pairs. Tell the story right. Honor Kobe & Gigi.",
            "2026-03-21",
            "2026-04-30",
            "#552583",  # Lakers purple
        ))
        conn.commit()
        print(f"  ✅ Campaign created: {name}")
    else:
        print(f"  ⏭️  Campaign already exists: {name}")
    cur.close()
    conn.close()

try:
    _ensure_campaign("Kobe & Gigi eBay Drop")
except Exception as e:
    print(f"  ⚠️  Could not seed campaign: {e}")

conn = get_conn()
cur = conn.cursor()
smm_added = 0
for post in SMM_POSTS:
    cur.execute(f"SELECT COUNT(*) FROM smm_posts WHERE title={ph}", (post["title"],))
    if cur.fetchone()[0] > 0:
        print(f"  ⏭️  Post already exists: {post['title']}")
        continue

    cur.execute(f"""
        INSERT INTO smm_posts
        (title, caption, hashtags, post_type, status, account_ids,
         scheduled_at, media_urls, link, campaign, notes)
        VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})
    """, (
        post["title"],
        post["caption"],
        post["hashtags"],
        post["post_type"],
        post["status"],
        "",  # No specific account_ids — pick at post time
        None,
        "",
        "",
        post.get("campaign", ""),
        post.get("notes", ""),
    ))
    print(f"  ✅ SMM post created: {post['title']}")
    smm_added += 1

conn.commit()
cur.close()
conn.close()

print(f"\n📱 {smm_added} social media post(s) seeded into smm_posts.\n")
print("━" * 60)
print("All done! Go to:")
print("  → Peach State Savings Overview  — see the eBay banner")
print("  → Social Media Manager → Queue  — 5 posts marked READY")
print("━" * 60)
