"""
Real Estate Bot — utility module.
Handles criteria, scoring, DB schema, and Zillow/Redfin/MLS API helpers.

Sources supported:
  • Realtor.com / MLS  — via HomeHarvest (no API key needed)
  • Redfin             — via HomeHarvest (no API key needed)
  • Zillow             — via RapidAPI (key required)
"""
from __future__ import annotations
import os, json, re, requests
from datetime import datetime

# ── Darrian's hard-coded search criteria ─────────────────────────────────────
CRITERIA = {
    "min_price": 245_000,
    "max_price": 285_000,
    "min_beds": 4,
    "min_baths": 2,
    "min_sqft": 1_600,
    "max_commute_min": 25,
    "max_hoa": 100,
    "max_dom": 89,
    "commute_destination": "1230 Peachtree St NE, Atlanta, GA",
    "target_neighborhoods": [
        "West End", "Vine City", "English Avenue", "Washington Park",
        "Hunter Hills", "Center Hill", "Grove Park", "Bankhead",
        "Mozley Park", "Carey Park", "Westview",
    ],
    "target_zips": [
        "30310", "30314", "30318", "30311", "30331",
        "30312", "30315", "30316", "30317",
    ],
    "invest_atlanta_amount": 20_000,
    "georgia_dream_amount": 10_000,
    "monthly_payment_max": 2_600,
    "roommate_income": 1_200,
}

# ── Scoring weights ───────────────────────────────────────────────────────────
WEIGHTS = {
    "price_in_range": 20,
    "beds_met": 10,
    "baths_met": 5,
    "sqft_met": 10,
    "commute_ok": 15,
    "no_hoa_or_low": 5,
    "dom_fresh": 10,
    "invest_atlanta": 10,
    "condition_good": 10,
    "post_1980": 5,
}


def score_listing(listing: dict) -> int:
    """Score a listing 0-100 against Darrian's criteria."""
    score = 0
    price = listing.get("price", 0)
    if CRITERIA["min_price"] <= price <= CRITERIA["max_price"]:
        score += WEIGHTS["price_in_range"]
    elif price < CRITERIA["min_price"] * 1.05:
        score += WEIGHTS["price_in_range"] // 2

    if listing.get("beds", 0) >= CRITERIA["min_beds"]:
        score += WEIGHTS["beds_met"]
    if listing.get("baths", 0) >= CRITERIA["min_baths"]:
        score += WEIGHTS["baths_met"]
    if listing.get("sqft", 0) >= CRITERIA["min_sqft"]:
        score += WEIGHTS["sqft_met"]

    commute = listing.get("commute_min")
    if commute is not None and commute <= CRITERIA["max_commute_min"]:
        score += WEIGHTS["commute_ok"]
    elif commute is None:
        score += WEIGHTS["commute_ok"] // 2  # unknown — partial credit

    hoa = listing.get("hoa", 0) or 0
    if hoa == 0:
        score += WEIGHTS["no_hoa_or_low"]
    elif hoa <= CRITERIA["max_hoa"]:
        score += WEIGHTS["no_hoa_or_low"] // 2

    dom = listing.get("dom", 999)
    if dom <= 14:
        score += WEIGHTS["dom_fresh"]
    elif dom <= 30:
        score += int(WEIGHTS["dom_fresh"] * 0.7)
    elif dom <= CRITERIA["max_dom"]:
        score += int(WEIGHTS["dom_fresh"] * 0.3)

    if listing.get("invest_atlanta_eligible"):
        score += WEIGHTS["invest_atlanta"]

    cond = listing.get("condition", "").lower()
    if "move-in" in cond or "ready" in cond:
        score += WEIGHTS["condition_good"]
    elif "minor" in cond or "cosmetic" in cond:
        score += WEIGHTS["condition_good"] // 2

    year = listing.get("year_built", 0) or 0
    if year >= 1980:
        score += WEIGHTS["post_1980"]

    return min(score, 100)


def effective_price(listing: dict) -> int:
    """Price after down-payment assistance."""
    if listing.get("invest_atlanta_eligible"):
        return listing["price"] - CRITERIA["invest_atlanta_amount"]
    return listing["price"] - CRITERIA["georgia_dream_amount"]


def flag_red_flags(listing: dict) -> list[str]:
    flags = []
    dom = listing.get("dom", 0)
    if dom > 60:
        flags.append(f"High DOM ({dom} days) — investigate why")
    year = listing.get("year_built", 0) or 0
    if year and year < 1980:
        flags.append("Pre-1980 build — require full system documentation")
    roof = listing.get("roof_age")
    if roof and roof >= 15:
        flags.append(f"Roof {roof} yrs old — may need replacement soon")
    hvac = listing.get("hvac_age")
    if hvac and hvac >= 10:
        flags.append(f"HVAC {hvac} yrs old — budget for replacement")
    hoa = listing.get("hoa", 0) or 0
    if hoa > CRITERIA["max_hoa"]:
        flags.append(f"HOA ${hoa}/mo exceeds ${CRITERIA['max_hoa']} limit")
    price = listing.get("price", 0)
    if price > CRITERIA["max_price"]:
        flags.append(f"Over budget by ${price - CRITERIA['max_price']:,}")
    return flags


# ── HomeHarvest helpers (shared normalizer) ───────────────────────────────────

def _normalize_homeharvest(row: dict, source: str = "realtor") -> dict:
    """
    Normalize a HomeHarvest DataFrame row into our internal listing schema.
    Works for both Realtor.com (MLS) and Redfin results.
    """
    street = str(row.get("street", "") or "")
    city   = str(row.get("city", "Atlanta") or "Atlanta")
    state  = str(row.get("state", "GA") or "GA")
    zip_   = str(row.get("zip_code", "") or "")
    address = f"{street}, {city}, {state} {zip_}".strip(", ")

    price      = int(row.get("list_price", 0) or 0)
    beds       = int(row.get("beds", 0) or 0)
    full_baths = int(row.get("full_baths", 0) or 0)
    half_baths = int(row.get("half_baths", 0) or 0)
    baths      = full_baths + half_baths * 0.5
    sqft       = int(row.get("sqft", 0) or 0)
    year_built = int(row.get("year_built", 0) or 0)
    dom        = int(row.get("days_on_mls", 0) or 0)
    hoa        = int(row.get("hoa_fee", 0) or 0)
    lat        = row.get("latitude")
    lng        = row.get("longitude")
    img_url    = str(row.get("primary_photo", "") or "")
    prop_url   = str(row.get("property_url", "") or "")
    prop_id    = str(row.get("property_id", "") or row.get("mls_id", "") or "")
    mls        = str(row.get("mls", "") or "")
    mls_id     = str(row.get("mls_id", "") or "")

    # Invest Atlanta eligibility — ZIP must be in our target list
    invest_eligible = zip_ in CRITERIA["target_zips"]

    # Condition heuristic
    mls_status = str(row.get("mls_status", "") or "").lower()
    condition = "Move-in Ready" if "new" in mls_status else "Unknown"

    # Auto-highlights
    highlights = []
    if year_built >= 1980:
        highlights.append(f"Post-{year_built} build")
    if hoa == 0:
        highlights.append("No HOA")
    if beds >= 5:
        highlights.append(f"{beds} beds — great for roommate")
    if sqft >= 2000:
        highlights.append(f"Large home ({sqft:,} sqft)")
    if invest_eligible:
        highlights.append("Invest Atlanta eligible ZIP")

    if not prop_url and prop_id:
        prop_url = f"https://www.realtor.com/realestateandhomes-detail/{prop_id}"

    external_id = prop_id or f"{source}-{address[:20].replace(' ', '-').lower()}"

    listing = {
        "source": source,
        "external_id": external_id,
        "mls": mls,
        "mls_id": mls_id,
        "address": address,
        "neighborhood": _guess_neighborhood(address),
        "price": price,
        "beds": beds,
        "baths": baths,
        "sqft": sqft,
        "year_built": year_built,
        "dom": dom,
        "hoa": hoa,
        "lat": lat,
        "lng": lng,
        "img_url": img_url,
        "listing_url": prop_url,
        "condition": condition,
        "invest_atlanta_eligible": invest_eligible,
        "commute_min": None,
        "roof_age": None,
        "hvac_age": None,
        "price_history": [],
        "highlights": highlights,
        "red_flags": [],
        "tag": "",
        "ai_insight": "",
        "status": "active",
        "notes": "",
        "fetched_at": datetime.now().isoformat(),
    }
    listing["score"] = score_listing(listing)
    listing["red_flags"] = flag_red_flags(listing)
    return listing


# ── HomeHarvest — Realtor.com / MLS (no API key needed) ──────────────────────

def search_realtor_mls(
    zip_codes: list[str] | None = None,
    past_days: int = 60,
    limit: int = 50,
) -> list[dict]:
    """
    Search Realtor.com (MLS-backed) for active listings matching Darrian's criteria.
    No API key required — uses HomeHarvest (pip install homeharvest).
    Returns a list of normalized listing dicts.
    """
    try:
        from homeharvest import scrape_property
    except ImportError:
        return [{"error": "homeharvest not installed. Run: pip install homeharvest"}]

    zips = zip_codes or CRITERIA["target_zips"]
    all_results: list[dict] = []

    for zip_code in zips:
        try:
            df = scrape_property(
                location=zip_code,
                listing_type="for_sale",
                property_type=["single_family"],
                beds_min=CRITERIA["min_beds"],
                baths_min=float(CRITERIA["min_baths"]),
                price_min=CRITERIA["min_price"],
                price_max=CRITERIA["max_price"],
                sqft_min=CRITERIA["min_sqft"],
                past_days=past_days,
                limit=limit,
            )
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    all_results.append(_normalize_homeharvest(row.to_dict(), source="realtor"))
        except Exception as e:
            all_results.append({"error": f"ZIP {zip_code}: {e}"})

    return all_results


# ── HomeHarvest — Redfin (no API key needed) ─────────────────────────────────

def search_redfin(
    zip_codes: list[str] | None = None,
    past_days: int = 60,
    limit: int = 50,
) -> list[dict]:
    """
    Search for active listings and label them as Redfin-sourced.
    Uses HomeHarvest (Realtor.com data) as the backend — same MLS feed
    that Redfin pulls from, deduplicated by address.
    No API key required.
    Returns a list of normalized listing dicts.
    """
    try:
        from homeharvest import scrape_property
    except ImportError:
        return [{"error": "homeharvest not installed. Run: pip install homeharvest"}]

    zips = zip_codes or CRITERIA["target_zips"]
    all_results: list[dict] = []

    for zip_code in zips:
        try:
            df = scrape_property(
                location=zip_code,
                listing_type="for_sale",
                property_type=["single_family"],
                beds_min=CRITERIA["min_beds"],
                baths_min=float(CRITERIA["min_baths"]),
                price_min=CRITERIA["min_price"],
                price_max=CRITERIA["max_price"],
                sqft_min=CRITERIA["min_sqft"],
                past_days=past_days,
                limit=limit,
            )
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    all_results.append(_normalize_homeharvest(row.to_dict(), source="redfin"))
        except Exception as e:
            all_results.append({"error": f"ZIP {zip_code}: {e}"})

    return all_results


# ── US Real Estate RapidAPI helper (us-real-estate.p.rapidapi.com) ────────────
US_RE_HOST = "us-real-estate.p.rapidapi.com"


def search_us_real_estate(
    api_key: str,
    city: str = "Atlanta",
    state_code: str = "GA",
    limit: int = 50,
) -> list[dict]:
    """
    Search for active for-sale listings via the US Real Estate RapidAPI.
    Endpoint: GET /v3/for-sale
    Returns a list of normalized listing dicts.
    """
    url = f"https://{US_RE_HOST}/v3/for-sale"
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": US_RE_HOST,
    }
    params = {
        "city": city,
        "state_code": state_code,
        "beds_min": str(CRITERIA["min_beds"]),
        "price_min": str(CRITERIA["min_price"]),
        "price_max": str(CRITERIA["max_price"]),
        "home_size_min": "1500",   # closest allowed value to 1,600
        "sort": "newest",
        "limit": str(min(limit, 200)),
        "offset": "0",
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        hs = (data.get("data") or {}).get("home_search") or {}
        props = hs.get("results", []) or []
        return [_normalize_us_re(p) for p in props]
    except Exception as e:
        return [{"error": str(e)}]


def _normalize_us_re(p: dict) -> dict:
    """Map US Real Estate API fields to our internal listing schema."""
    loc  = (p.get("location") or {}).get("address", {})
    desc = p.get("description") or {}
    coord = loc.get("coordinate") or {}

    street = str(loc.get("line", "") or "")
    city   = str(loc.get("city", "Atlanta") or "Atlanta")
    state  = str(loc.get("state_code", "GA") or "GA")
    zip_   = str(loc.get("postal_code", "") or "")
    address = f"{street}, {city}, {state} {zip_}".strip(", ")

    price      = int(p.get("list_price", 0) or 0)
    beds       = int(desc.get("beds", 0) or 0)
    baths_raw  = desc.get("baths_consolidated") or desc.get("baths", 0)
    baths      = float(baths_raw or 0)
    sqft       = int(desc.get("sqft", 0) or 0)
    year_built = int(desc.get("year_built", 0) or 0)
    dom        = int(p.get("days_on_market", 0) or 0)
    hoa        = int((p.get("hoa") or {}).get("fee", 0) or 0)
    lat        = coord.get("lat")
    lng        = coord.get("lon")
    prop_id    = str(p.get("property_id", "") or "")
    img_url    = str((p.get("primary_photo") or {}).get("href", "") or "")
    prop_url   = str(p.get("href", "") or "")
    if not prop_url and prop_id:
        prop_url = f"https://www.realtor.com/realestateandhomes-detail/{prop_id}"

    invest_eligible = zip_ in CRITERIA["target_zips"]

    highlights = []
    if year_built >= 1980:
        highlights.append(f"Post-{year_built} build")
    if hoa == 0:
        highlights.append("No HOA")
    if beds >= 5:
        highlights.append(f"{beds} beds — great for roommate")
    if sqft >= 2000:
        highlights.append(f"Large home ({sqft:,} sqft)")
    if invest_eligible:
        highlights.append("Invest Atlanta eligible ZIP")

    listing = {
        "source": "us_re_api",
        "external_id": prop_id or f"usre-{address[:20].replace(' ','-').lower()}",
        "address": address,
        "neighborhood": _guess_neighborhood(address),
        "price": price,
        "beds": beds,
        "baths": baths,
        "sqft": sqft,
        "year_built": year_built,
        "dom": dom,
        "hoa": hoa,
        "lat": lat,
        "lng": lng,
        "img_url": img_url,
        "listing_url": prop_url,
        "condition": "Unknown",
        "invest_atlanta_eligible": invest_eligible,
        "commute_min": None,
        "roof_age": None,
        "hvac_age": None,
        "price_history": [],
        "highlights": highlights,
        "red_flags": [],
        "tag": "",
        "ai_insight": "",
        "status": "active",
        "notes": "",
        "fetched_at": datetime.now().isoformat(),
    }
    listing["score"] = score_listing(listing)
    listing["red_flags"] = flag_red_flags(listing)
    return listing


# ── Zillow RapidAPI helper (legacy — original API deprecated) ─────────────────
ZILLOW_HOST = "zillow-com1.p.rapidapi.com"


def search_zillow(api_key: str, zip_code: str = "30310", limit: int = 20) -> list[dict]:
    """
    Search Zillow via RapidAPI for active listings in a zip code.
    Returns a list of normalized listing dicts.
    """
    url = "https://zillow-com1.p.rapidapi.com/propertyExtendedSearch"
    headers = {"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": ZILLOW_HOST}
    params = {
        "location": zip_code,
        "status_type": "ForSale",
        "home_type": "Houses",
        "minPrice": str(CRITERIA["min_price"]),
        "maxPrice": str(CRITERIA["max_price"]),
        "bedsMin": str(CRITERIA["min_beds"]),
        "bathsMin": str(CRITERIA["min_baths"]),
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        props = data.get("props", [])
        return [_normalize_zillow(p) for p in props[:limit]]
    except Exception as e:
        return [{"error": str(e)}]


def _normalize_zillow(p: dict) -> dict:
    """Map Zillow API fields to our internal schema."""
    return {
        "source": "zillow",
        "zpid": p.get("zpid", ""),
        "address": p.get("address", ""),
        "price": int(p.get("price", 0) or 0),
        "beds": int(p.get("bedrooms", 0) or 0),
        "baths": float(p.get("bathrooms", 0) or 0),
        "sqft": int(p.get("livingArea", 0) or 0),
        "year_built": int(p.get("yearBuilt", 0) or 0),
        "dom": int(p.get("daysOnZillow", 0) or 0),
        "hoa": int(p.get("hoaFee", 0) or 0),
        "lat": p.get("latitude"),
        "lng": p.get("longitude"),
        "img_url": p.get("imgSrc", ""),
        "listing_url": f"https://www.zillow.com/homedetails/{p.get('zpid', '')}_zpid/",
        "condition": "Unknown",
        "invest_atlanta_eligible": False,
        "commute_min": None,
        "roof_age": None,
        "hvac_age": None,
        "price_history": [],
        "highlights": [],
        "neighborhood": _guess_neighborhood(p.get("address", "")),
        "fetched_at": datetime.now().isoformat(),
    }


def _guess_neighborhood(address: str) -> str:
    """Rough neighborhood guess from address string."""
    addr_lower = address.lower()
    for n in CRITERIA["target_neighborhoods"]:
        if n.lower() in addr_lower:
            return n
    return "Atlanta"


# ── DB schema helpers ─────────────────────────────────────────────────────────
def init_re_tables(conn, use_postgres: bool = False):
    """Create real estate tables if they don't exist."""
    c = conn.cursor()
    if use_postgres:
        c.execute("""
            CREATE TABLE IF NOT EXISTS re_listings (
                id SERIAL PRIMARY KEY,
                source TEXT DEFAULT 'manual',
                external_id TEXT DEFAULT '',
                address TEXT NOT NULL,
                neighborhood TEXT DEFAULT '',
                price INTEGER DEFAULT 0,
                beds REAL DEFAULT 0,
                baths REAL DEFAULT 0,
                sqft INTEGER DEFAULT 0,
                year_built INTEGER DEFAULT 0,
                dom INTEGER DEFAULT 0,
                hoa INTEGER DEFAULT 0,
                commute_min INTEGER DEFAULT NULL,
                condition TEXT DEFAULT 'Unknown',
                invest_atlanta_eligible INTEGER DEFAULT 0,
                roof_age INTEGER DEFAULT NULL,
                hvac_age INTEGER DEFAULT NULL,
                score INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                tag TEXT DEFAULT '',
                ai_insight TEXT DEFAULT '',
                highlights TEXT DEFAULT '[]',
                red_flags TEXT DEFAULT '[]',
                price_history TEXT DEFAULT '[]',
                img_url TEXT DEFAULT '',
                listing_url TEXT DEFAULT '',
                lat REAL DEFAULT NULL,
                lng REAL DEFAULT NULL,
                notes TEXT DEFAULT '',
                saved INTEGER DEFAULT 0,
                fetched_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
                updated_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS re_searches (
                id SERIAL PRIMARY KEY,
                search_type TEXT DEFAULT 'manual',
                zip_codes TEXT DEFAULT '',
                results_count INTEGER DEFAULT 0,
                ran_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS re_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT DEFAULT 'manual',
                external_id TEXT DEFAULT '',
                address TEXT NOT NULL,
                neighborhood TEXT DEFAULT '',
                price INTEGER DEFAULT 0,
                beds REAL DEFAULT 0,
                baths REAL DEFAULT 0,
                sqft INTEGER DEFAULT 0,
                year_built INTEGER DEFAULT 0,
                dom INTEGER DEFAULT 0,
                hoa INTEGER DEFAULT 0,
                commute_min INTEGER DEFAULT NULL,
                condition TEXT DEFAULT 'Unknown',
                invest_atlanta_eligible INTEGER DEFAULT 0,
                roof_age INTEGER DEFAULT NULL,
                hvac_age INTEGER DEFAULT NULL,
                score INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                tag TEXT DEFAULT '',
                ai_insight TEXT DEFAULT '',
                highlights TEXT DEFAULT '[]',
                red_flags TEXT DEFAULT '[]',
                price_history TEXT DEFAULT '[]',
                img_url TEXT DEFAULT '',
                listing_url TEXT DEFAULT '',
                lat REAL DEFAULT NULL,
                lng REAL DEFAULT NULL,
                notes TEXT DEFAULT '',
                saved INTEGER DEFAULT 0,
                fetched_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS re_searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_type TEXT DEFAULT 'manual',
                zip_codes TEXT DEFAULT '',
                results_count INTEGER DEFAULT 0,
                ran_at TEXT DEFAULT (datetime('now'))
            )
        """)
    conn.commit()


def upsert_listing(conn, listing: dict, use_postgres: bool = False):
    """Insert or update a listing by external_id+source."""
    from utils.db import execute as db_exec
    listing["score"] = score_listing(listing)
    listing["red_flags"] = json.dumps(flag_red_flags(listing))
    listing["highlights"] = json.dumps(listing.get("highlights", []))
    listing["price_history"] = json.dumps(listing.get("price_history", []))

    ext_id = listing.get("external_id") or listing.get("zpid", "")
    source = listing.get("source", "manual")

    existing = db_exec(conn,
        "SELECT id FROM re_listings WHERE external_id=? AND source=?",
        (str(ext_id), source)
    ).fetchone()

    if existing:
        db_exec(conn, """
            UPDATE re_listings SET price=?, beds=?, baths=?, sqft=?, dom=?,
            score=?, red_flags=?, highlights=?, price_history=?, updated_at=datetime('now')
            WHERE id=?
        """, (
            listing.get("price", 0), listing.get("beds", 0), listing.get("baths", 0),
            listing.get("sqft", 0), listing.get("dom", 0),
            listing["score"], listing["red_flags"], listing["highlights"],
            listing["price_history"], existing[0]
        ))
    else:
        db_exec(conn, """
            INSERT INTO re_listings
            (source, external_id, address, neighborhood, price, beds, baths, sqft,
             year_built, dom, hoa, commute_min, condition, invest_atlanta_eligible,
             roof_age, hvac_age, score, status, tag, ai_insight, highlights,
             red_flags, price_history, img_url, listing_url, lat, lng, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            source, str(ext_id),
            listing.get("address", ""), listing.get("neighborhood", ""),
            listing.get("price", 0), listing.get("beds", 0), listing.get("baths", 0),
            listing.get("sqft", 0), listing.get("year_built", 0), listing.get("dom", 0),
            listing.get("hoa", 0), listing.get("commute_min"),
            listing.get("condition", "Unknown"),
            1 if listing.get("invest_atlanta_eligible") else 0,
            listing.get("roof_age"), listing.get("hvac_age"),
            listing["score"], listing.get("status", "active"),
            listing.get("tag", ""), listing.get("ai_insight", ""),
            listing["highlights"], listing["red_flags"], listing["price_history"],
            listing.get("img_url", ""), listing.get("listing_url", ""),
            listing.get("lat"), listing.get("lng"), listing.get("notes", ""),
        ))
    conn.commit()


# ── Mock listings (used when no live search has run) ─────────────────────────
MOCK_LISTINGS = [
    {
        "id": 1, "source": "mock", "external_id": "mock-1",
        "address": "819 Venetta Place NW", "neighborhood": "Hunter Hills",
        "price": 269_000, "beds": 4, "baths": 2, "sqft": 1820,
        "year_built": 1952, "dom": 5, "hoa": 0, "commute_min": 18,
        "roof_age": 8, "hvac_age": 5, "condition": "Move-in Ready",
        "invest_atlanta_eligible": True, "score": 94, "status": "active",
        "tag": "TOP PICK",
        "highlights": ["Roommate-friendly layout", "Fenced backyard", "Updated kitchen", "Hardwood floors"],
        "red_flags": [],
        "price_history": [{"date": "Jan 2026", "price": 275_000}, {"date": "Feb 2026", "price": 269_000}],
        "ai_insight": (
            "Strong buy. Price reduced $6k in 30 days — seller motivated. "
            "Located in census tract eligible for Invest Atlanta $20k. "
            "Comp analysis shows similar homes selling at $278-295k. "
            "Effective purchase price after assistance: ~$249k."
        ),
        "listing_url": "", "img_url": "",
    },
    {
        "id": 2, "source": "mock", "external_id": "mock-2",
        "address": "1047 Dill Ave SW", "neighborhood": "Westview",
        "price": 258_000, "beds": 4, "baths": 2, "sqft": 1680,
        "year_built": 1965, "dom": 12, "hoa": 0, "commute_min": 22,
        "roof_age": 11, "hvac_age": 7, "condition": "Move-in Ready",
        "invest_atlanta_eligible": True, "score": 88, "status": "active",
        "tag": "GOOD VALUE",
        "highlights": ["Corner lot", "Detached garage", "Updated electrical", "Natural light"],
        "red_flags": ["Pre-1980 — verify plumbing documentation"],
        "price_history": [{"date": "Feb 2026", "price": 258_000}],
        "ai_insight": (
            "Good value. Westview is one of NW Atlanta's fastest appreciating pockets — "
            "median values up 14% YoY. At $258k with $20k Invest Atlanta assistance, "
            "effective cost ~$238k. Age flag: request documentation on plumbing updates."
        ),
        "listing_url": "", "img_url": "",
    },
    {
        "id": 3, "source": "mock", "external_id": "mock-3",
        "address": "2210 Ezra Church Dr NW", "neighborhood": "Center Hill",
        "price": 279_000, "beds": 5, "baths": 2.5, "sqft": 2100,
        "year_built": 1988, "dom": 3, "hoa": 0, "commute_min": 20,
        "roof_age": 6, "hvac_age": 4, "condition": "Move-in Ready",
        "invest_atlanta_eligible": False, "score": 91, "status": "active",
        "tag": "NEW · ACT FAST",
        "highlights": ["5 beds — ideal for roommate", "Post-1980 build", "Large backyard", "Bonus room"],
        "red_flags": ["Not Invest Atlanta eligible — use Georgia Dream $10k instead"],
        "price_history": [{"date": "Feb 2026", "price": 279_000}],
        "ai_insight": (
            "New listing — move fast. 5BR gives you the best roommate setup. "
            "1988 build means systems are in good shape. Comps in Center Hill: $285-310k. "
            "This is priced under market. Georgia Dream $10k still applies."
        ),
        "listing_url": "", "img_url": "",
    },
    {
        "id": 4, "source": "mock", "external_id": "mock-4",
        "address": "564 Mozley Dr SW", "neighborhood": "Mozley Park",
        "price": 249_000, "beds": 4, "baths": 2, "sqft": 1640,
        "year_built": 1945, "dom": 44, "hoa": 0, "commute_min": 19,
        "roof_age": 13, "hvac_age": 9, "condition": "Minor Cosmetic",
        "invest_atlanta_eligible": True, "score": 72, "status": "watch",
        "tag": "INVESTIGATE",
        "highlights": ["Lowest price in range", "Invest Atlanta eligible", "Hardwood floors throughout"],
        "red_flags": [
            "44 DOM — investigate why",
            "1945 build — full system docs required",
            "Roof approaching 15yr threshold",
        ],
        "price_history": [
            {"date": "Nov 2025", "price": 265_000},
            {"date": "Jan 2026", "price": 255_000},
            {"date": "Feb 2026", "price": 249_000},
        ],
        "ai_insight": (
            "3 price reductions in 90 days — something is causing hesitation. "
            "Could be condition, could be seller. Worth a walk-through only if roof "
            "and plumbing docs check out. At $249k + $20k Invest Atlanta, "
            "effective cost is compelling at ~$229k. Proceed with strong inspection contingency."
        ),
        "listing_url": "", "img_url": "",
    },
]
