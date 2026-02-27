"""
Real Estate Bot — Page 18
Darrian's personal home-buying assistant for Atlanta, GA.
"""
import json
import streamlit as st
from utils.db import get_conn, USE_POSTGRES
from utils.real_estate import (
    CRITERIA, MOCK_LISTINGS, score_listing, effective_price,
    flag_red_flags, search_zillow, search_realtor_mls, search_redfin,
    init_re_tables,
)

st.set_page_config(page_title="🏠 Real Estate Bot",
    page_icon="🍑", layout="wide")

# ── Auth guard ────────────────────────────────────────────────────────────────
if not st.session_state.get("authenticated"):
    st.warning("Please log in from the Home page.")
    st.stop()

# ── DB init ───────────────────────────────────────────────────────────────────
conn = get_conn()
init_re_tables(conn, use_postgres=USE_POSTGRES)

# ── DB helpers for persistent saved listings ──────────────────────────────────
from utils.db import execute as db_exec

def _load_saved_from_db() -> list[dict]:
    """Load all saved listings from the DB."""
    try:
        c = db_exec(conn, "SELECT * FROM re_listings WHERE saved = 1 OR status = 'saved'")
        rows = c.fetchall()
        if not rows:
            return []
        if USE_POSTGRES:
            cols = [d[0] for d in c.description]
            results = [dict(zip(cols, r)) for r in rows]
        else:
            results = [dict(r) for r in rows]
        for r in results:
            for field in ("highlights", "red_flags", "price_history"):
                if isinstance(r.get(field), str):
                    try:
                        r[field] = json.loads(r[field] or "[]")
                    except Exception:
                        r[field] = []
        return results
    except Exception:
        return []

def _save_listing_to_db(listing: dict):
    """Upsert a listing into re_listings with saved=1."""
    import json as _json
    ext_id = str(listing.get("external_id") or listing.get("id") or "")
    source  = listing.get("source", "manual")
    highlights   = _json.dumps(listing.get("highlights", []) if isinstance(listing.get("highlights"), list) else [])
    red_flags    = _json.dumps(listing.get("red_flags", []) if isinstance(listing.get("red_flags"), list) else [])
    price_history= _json.dumps(listing.get("price_history", []) if isinstance(listing.get("price_history"), list) else [])
    try:
        c = db_exec(conn, "SELECT id FROM re_listings WHERE external_id=? AND source=?", (ext_id, source))
        row = c.fetchone()
        if row:
            db_exec(conn, "UPDATE re_listings SET saved=1, status='saved' WHERE external_id=? AND source=?", (ext_id, source))
        else:
            db_exec(conn, """
                INSERT INTO re_listings
                (source, external_id, address, neighborhood, price, beds, baths, sqft,
                 year_built, dom, hoa, condition, invest_atlanta_eligible, score,
                 status, tag, ai_insight, highlights, red_flags, price_history,
                 img_url, listing_url, notes, saved)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)
            """, (
                source, ext_id,
                listing.get("address",""), listing.get("neighborhood",""),
                listing.get("price",0), listing.get("beds",0), listing.get("baths",0),
                listing.get("sqft",0), listing.get("year_built",0), listing.get("dom",0),
                listing.get("hoa",0), listing.get("condition","Unknown"),
                1 if listing.get("invest_atlanta_eligible") else 0,
                listing.get("score",0), "saved",
                listing.get("tag",""), listing.get("ai_insight",""),
                highlights, red_flags, price_history,
                listing.get("img_url",""), listing.get("listing_url",""),
                listing.get("notes",""),
            ))
        conn.commit()
    except Exception:
        pass

def _unsave_listing_in_db(ext_id: str, source: str):
    """Mark a listing as unsaved in the DB."""
    try:
        db_exec(conn, "UPDATE re_listings SET saved=0, status='active' WHERE external_id=? AND source=?", (ext_id, source))
        conn.commit()
    except Exception:
        pass

# ── Helpers ───────────────────────────────────────────────────────────────────
def score_color(score: int) -> str:
    if score >= 85:
        return "#00c853"
    if score >= 70:
        return "#ffd600"
    return "#ff5252"

def parse_json_field(val):
    if isinstance(val, list):
        return val
    try:
        return json.loads(val or "[]")
    except Exception:
        return []

def monthly_payment(price: int, rate: float = 0.0699, years: int = 30,
                    down_pct: float = 0.035) -> float:
    principal = price * (1 - down_pct)
    r = rate / 12
    n = years * 12
    if r == 0:
        return principal / n
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🏠 Real Estate Bot")
st.caption("Atlanta home-buying assistant · $245k–$285k · 4+ beds · NW/SW Atlanta")

# ── Sidebar — criteria summary ────────────────────────────────────────────────
# ── Load editable criteria from session state (falls back to defaults) ────────
if "criteria" not in st.session_state:
    import copy
    st.session_state["criteria"] = copy.deepcopy(CRITERIA)
C = st.session_state["criteria"]  # shorthand

with st.sidebar:
    st.subheader("🎯 Your Criteria")
    with st.expander("✏️ Edit Criteria", expanded=False):
        C["min_price"]          = st.number_input("Min Price ($)", 100_000, 500_000, C["min_price"], 5_000)
        C["max_price"]          = st.number_input("Max Price ($)", 100_000, 600_000, C["max_price"], 5_000)
        C["min_beds"]           = st.number_input("Min Beds", 1, 10, C["min_beds"])
        C["min_baths"]          = st.number_input("Min Baths", 1, 10, C["min_baths"])
        C["min_sqft"]           = st.number_input("Min Sqft", 500, 5_000, C["min_sqft"], 100)
        C["max_hoa"]            = st.number_input("Max HOA ($/mo)", 0, 1_000, C["max_hoa"], 25)
        C["max_commute_min"]    = st.number_input("Max Commute (min)", 5, 120, C["max_commute_min"], 5)
        C["monthly_payment_max"]= st.number_input("Max Net Payment ($/mo)", 500, 5_000, C["monthly_payment_max"], 100)
        C["roommate_income"]    = st.number_input("Roommate Income ($/mo)", 0, 3_000, C["roommate_income"], 50)
        C["invest_atlanta_amount"] = st.number_input("Invest Atlanta DPA ($)", 0, 50_000, C["invest_atlanta_amount"], 1_000)
        C["georgia_dream_amount"]  = st.number_input("Georgia Dream DPA ($)", 0, 30_000, C["georgia_dream_amount"], 1_000)
        if st.button("↩️ Reset to Defaults", use_container_width=True):
            import copy
            st.session_state["criteria"] = copy.deepcopy(CRITERIA)
            st.rerun()

    st.markdown(f"""
| | |
|---|---|
| **Budget** | ${C['min_price']:,} – ${C['max_price']:,} |
| **Beds** | {C['min_beds']}+ |
| **Baths** | {C['min_baths']}+ |
| **Sqft** | {C['min_sqft']:,}+ |
| **Max commute** | {C['max_commute_min']} min |
| **Max HOA** | ${C['max_hoa']}/mo |
| **Invest Atlanta** | ${C['invest_atlanta_amount']:,} |
| **Georgia Dream** | ${C['georgia_dream_amount']:,} |
| **Roommate income** | ${C['roommate_income']:,}/mo |
""")
    st.divider()
    st.subheader("🔍 Live Search")
    zip_input = st.text_input("ZIP codes (comma-separated)",
                              value=", ".join(CRITERIA["target_zips"][:5]))

    run_mls    = st.button("🏠 Search MLS (Realtor.com)", use_container_width=True,
                           help="Free — no API key needed. Pulls from Realtor.com MLS feed.")
    run_redfin = st.button("🔴 Search Redfin", use_container_width=True,
                           help="Free — no API key needed. Same MLS data, Redfin-labeled.")

    st.divider()
    st.subheader("🔑 Zillow / US Real Estate API (optional)")
    zillow_key = st.text_input("RapidAPI key", type="password",
                               help="Get a free key at rapidapi.com → search 'US Real Estate' or 'Zillow Com1'")
    run_zillow = st.button("🟡 Search via RapidAPI", use_container_width=True,
                           disabled=not zillow_key,
                           help="Requires a RapidAPI key.")
    st.caption("💡 The free MLS search above works without any key.")

# ── Merge DB-saved listings into session state on first load ──────────────────
if "live_listings" not in st.session_state:
    import copy
    base = copy.deepcopy(MOCK_LISTINGS)
    # Load any previously saved listings from DB and merge them in
    db_saved = _load_saved_from_db()
    db_ids = {str(r.get("external_id","")) for r in db_saved}
    # Keep mock listings that aren't already in DB, then append DB saved ones
    merged = [l for l in base if str(l.get("external_id","")) not in db_ids]
    merged.extend(db_saved)
    st.session_state["live_listings"] = merged

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_listings, tab_add, tab_saved, tab_calc, tab_criteria = st.tabs([
    "📋 Listings", "➕ Add Listing", "⭐ Saved", "🧮 Calculator", "📌 Criteria"
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — LISTINGS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_listings:
    zips = [z.strip() for z in zip_input.split(",") if z.strip()]

    # ── MLS / Realtor.com search (free) ──────────────────────────────────────
    if run_mls:
        all_results = []
        with st.spinner(f"🏠 Searching MLS (Realtor.com) across {len(zips)} ZIPs… this may take 30–60s"):
            all_results = search_realtor_mls(zip_codes=zips)
        errors = [r for r in all_results if "error" in r]
        good   = [r for r in all_results if "error" not in r]
        if errors:
            st.warning(f"Some ZIPs had errors: {errors[0].get('error')}")
        if good:
            st.success(f"✅ MLS: Found {len(good)} listings across {len(zips)} ZIPs")
            st.session_state["live_listings"] = good
        else:
            st.warning("No MLS results — check ZIPs or try again.")

    # ── Redfin search (free) ──────────────────────────────────────────────────
    elif run_redfin:
        all_results = []
        with st.spinner(f"🔴 Searching Redfin across {len(zips)} ZIPs… this may take 30–60s"):
            all_results = search_redfin(zip_codes=zips)
        errors = [r for r in all_results if "error" in r]
        good   = [r for r in all_results if "error" not in r]
        if errors:
            st.warning(f"Some ZIPs had errors: {errors[0].get('error')}")
        if good:
            st.success(f"✅ Redfin: Found {len(good)} listings across {len(zips)} ZIPs")
            st.session_state["live_listings"] = good
        else:
            st.warning("No Redfin results — check ZIPs or try again.")

    # ── Zillow search (API key required) ─────────────────────────────────────
    elif run_zillow and zillow_key:
        all_results = []
        with st.spinner(f"🟡 Searching {len(zips)} ZIP codes via Zillow…"):
            for z in zips:
                results = search_zillow(zillow_key, z)
                all_results.extend(results)
        errors = [r for r in all_results if "error" in r]
        good   = [r for r in all_results if "error" not in r]
        if errors:
            st.error(f"Zillow API error: {errors[0].get('error')}")
        if good:
            st.success(f"✅ Zillow: Found {len(good)} listings across {len(zips)} ZIPs")
            st.session_state["live_listings"] = good
        else:
            st.warning("No Zillow results — showing demo listings.")

    # Choose data source
    listings = st.session_state.get("live_listings", MOCK_LISTINGS)

    # Sort / filter controls
    col_sort, col_filter, col_status = st.columns(3)
    with col_sort:
        sort_by = st.selectbox("Sort by", ["Score ↓", "Price ↑", "Price ↓", "DOM ↑", "Sqft ↓"])
    with col_filter:
        min_score = st.slider("Min score", 0, 100, 0, 5)
    with col_status:
        status_filter = st.multiselect("Status", ["active", "watch", "passed", "saved"],
                                       default=["active", "watch", "saved"])

    # Apply filters
    filtered = [l for l in listings
                if l.get("score", 0) >= min_score
                and l.get("status", "active") in status_filter]

    sort_map = {
        "Score ↓": lambda x: -x.get("score", 0),
        "Price ↑": lambda x: x.get("price", 0),
        "Price ↓": lambda x: -x.get("price", 0),
        "DOM ↑": lambda x: x.get("dom", 0),
        "Sqft ↓": lambda x: -x.get("sqft", 0),
    }
    filtered.sort(key=sort_map[sort_by])

    if not filtered:
        st.info("No listings match your filters.")
    else:
        st.caption(f"Showing {len(filtered)} listing(s)")

    for listing in filtered:
        score = listing.get("score", 0)
        tag = listing.get("tag", "")
        highlights = parse_json_field(listing.get("highlights", []))
        red_flags = parse_json_field(listing.get("red_flags", []))
        price_history = parse_json_field(listing.get("price_history", []))
        eff_price = effective_price(listing)
        payment = monthly_payment(eff_price)
        net_payment = payment - CRITERIA["roommate_income"]

        # Source badge — bright solid colors so they're always visible
        _src = listing.get("source", "mock")
        _src_styles = {
            "realtor": ("background:#00c853;color:#000;", "🏠 MLS"),
            "redfin":  ("background:#f44336;color:#fff;", "🔴 Redfin"),
            "zillow":  ("background:#ff9800;color:#000;", "🟡 Zillow"),
            "manual":  ("background:#2196f3;color:#fff;", "✏️ Manual"),
            "mock":    ("background:#9e9e9e;color:#000;", "📋 Demo"),
        }
        _style, _label = _src_styles.get(_src, ("background:#9e9e9e;color:#000;", _src.title()))
        source_badge = (
            f'<span style="{_style}padding:3px 10px;border-radius:12px;'
            f'font-size:12px;font-weight:bold;margin-right:6px">{_label}</span>'
        )

        # Card header
        tag_html = f'<span style="background:#1565c0;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;margin-left:4px">{tag}</span>' if tag else ""
        score_html = f'<span style="background:{score_color(score)};color:#000;padding:3px 10px;border-radius:12px;font-weight:bold;font-size:14px">{score}/100</span>'

        st.markdown(f"""
<div style="border:1px solid #333;border-radius:10px;padding:16px 20px;margin-bottom:16px;background:#1a1a2e">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
    <div>
      <div style="margin-bottom:6px">{source_badge}{tag_html}</div>
      <span style="font-size:17px;font-weight:bold">🏡 {listing.get('address','')}</span>
      <br><span style="color:#aaa;font-size:13px">{listing.get('neighborhood','Atlanta')} · {listing.get('condition','Unknown')}</span>
    </div>
    <div style="text-align:right">
      {score_html}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

        # Stats row
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("List Price", f"${listing.get('price',0):,}")
        c2.metric("Eff. Price", f"${eff_price:,}", help="After down-payment assistance")
        c3.metric("Beds / Baths", f"{listing.get('beds',0)}bd / {listing.get('baths',0)}ba")
        c4.metric("Sqft", f"{listing.get('sqft',0):,}")
        c5.metric("DOM", str(listing.get("dom", "?")))
        c6.metric("Commute", f"{listing.get('commute_min','?')} min" if listing.get("commute_min") else "Unknown")

        # Payment row
        p1, p2, p3 = st.columns(3)
        p1.metric("Est. Payment", f"${payment:,.0f}/mo", help="3.5% down, 6.99% rate, 30yr")
        p2.metric("After Roommate", f"${net_payment:,.0f}/mo",
                  delta=f"-${CRITERIA['roommate_income']:,} roommate",
                  delta_color="normal")
        ia = "✅ Yes" if listing.get("invest_atlanta_eligible") else "❌ No"
        p3.metric("Invest Atlanta", ia)

        # Highlights & red flags
        col_h, col_r = st.columns(2)
        with col_h:
            if highlights:
                st.markdown("**✅ Highlights**")
                for h in highlights:
                    st.markdown(f"- {h}")
        with col_r:
            if red_flags:
                st.markdown("**⚠️ Red Flags**")
                for f in red_flags:
                    st.markdown(f"- {f}")

        # Price history
        if price_history:
            with st.expander("📈 Price History"):
                for ph in price_history:
                    st.markdown(f"- **{ph.get('date','')}**: ${ph.get('price',0):,}")

        # AI insight
        ai = listing.get("ai_insight", "")
        if ai:
            with st.expander("🤖 AI Analysis"):
                st.info(ai)

        # Action buttons
        btn1, btn2, btn3, btn4 = st.columns(4)
        listing_url = listing.get("listing_url", "")
        if listing_url:
            btn1.link_button("🔗 View Listing", listing_url)

        listing_key = str(listing.get("id", listing.get("external_id", "")))
        current_status = listing.get("status", "active")

        with btn2:
            save_label = "✅ Saved" if current_status == "saved" else "⭐ Save"
            if st.button(save_label, key=f"save_{listing_key}"):
                for l in st.session_state["live_listings"]:
                    if str(l.get("id", l.get("external_id", ""))) == listing_key:
                        l["status"] = "saved"
                        l["saved"] = True
                        _save_listing_to_db(l)  # persist to DB
                        break
                st.toast(f"⭐ Saved {listing.get('address', '')}")
                st.rerun()
        with btn3:
            pass_label = "❌ Passed" if current_status == "passed" else "❌ Pass"
            if st.button(pass_label, key=f"pass_{listing_key}"):
                for l in st.session_state["live_listings"]:
                    if str(l.get("id", l.get("external_id", ""))) == listing_key:
                        l["status"] = "passed"
                        break
                st.toast(f"Passed on {listing.get('address', '')}")
                st.rerun()
        with btn4:
            if st.button("📋 Schedule Tour", key=f"tour_{listing_key}"):
                st.toast("Tour request noted — contact your agent!")

        st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ADD LISTING
# ═══════════════════════════════════════════════════════════════════════════════
with tab_add:
    st.subheader("➕ Add a Listing Manually")
    st.caption("Found something on Zillow/Redfin? Enter the details here to score it.")

    with st.form("add_listing_form"):
        a1, a2 = st.columns(2)
        address = a1.text_input("Address *", placeholder="123 Main St SW, Atlanta, GA 30310")
        neighborhood = a2.selectbox("Neighborhood", [""] + CRITERIA["target_neighborhoods"] + ["Other"])

        b1, b2, b3, b4 = st.columns(4)
        price = b1.number_input("List Price ($)", 100_000, 500_000, 265_000, 1_000)
        beds = b2.number_input("Beds", 1, 10, 4)
        baths = b3.number_input("Baths", 1.0, 10.0, 2.0, 0.5)
        sqft = b4.number_input("Sqft", 500, 5_000, 1_700, 50)

        c1, c2, c3, c4 = st.columns(4)
        year_built = c1.number_input("Year Built", 1900, 2025, 1975)
        dom = c2.number_input("Days on Market", 0, 365, 10)
        hoa = c3.number_input("HOA ($/mo)", 0, 1_000, 0)
        commute_min = c4.number_input("Commute (min)", 0, 120, 20)

        d1, d2, d3 = st.columns(3)
        condition = d1.selectbox("Condition", ["Unknown", "Move-in Ready", "Minor Cosmetic", "Needs Work", "Major Rehab"])
        roof_age = d2.number_input("Roof Age (yrs)", 0, 50, 0)
        hvac_age = d3.number_input("HVAC Age (yrs)", 0, 30, 0)

        invest_eligible = st.checkbox("Invest Atlanta Eligible ($20k DPA)")
        listing_url = st.text_input("Listing URL (optional)")
        notes = st.text_area("Notes", height=80)

        submitted = st.form_submit_button("📊 Score & Save Listing", use_container_width=True)

    if submitted and address:
        new_listing = {
            "source": "manual",
            "external_id": f"manual-{address[:20].replace(' ','-').lower()}",
            "address": address,
            "neighborhood": neighborhood or "Atlanta",
            "price": int(price),
            "beds": int(beds),
            "baths": float(baths),
            "sqft": int(sqft),
            "year_built": int(year_built),
            "dom": int(dom),
            "hoa": int(hoa),
            "commute_min": int(commute_min),
            "condition": condition,
            "roof_age": int(roof_age) if roof_age else None,
            "hvac_age": int(hvac_age) if hvac_age else None,
            "invest_atlanta_eligible": invest_eligible,
            "listing_url": listing_url,
            "notes": notes,
            "highlights": [],
            "price_history": [],
            "status": "active",
            "tag": "",
            "ai_insight": "",
        }
        sc = score_listing(new_listing)
        flags = flag_red_flags(new_listing)
        eff = effective_price(new_listing)
        pay = monthly_payment(eff)

        st.success(f"✅ Score: **{sc}/100** · Eff. price: **${eff:,}** · Est. payment: **${pay:,.0f}/mo**")
        if flags:
            st.warning("⚠️ Red Flags:\n" + "\n".join(f"- {f}" for f in flags))
        else:
            st.info("No red flags detected.")

        # Add to session state for display
        new_listing["score"] = sc
        new_listing["red_flags"] = flags
        new_listing["id"] = f"manual-{address[:10]}"
        existing = st.session_state.get("live_listings", [])
        st.session_state["live_listings"] = existing + [new_listing]
        st.info("Listing added to your session. Switch to the Listings tab to view it.")
    elif submitted:
        st.error("Address is required.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SAVED
# ═══════════════════════════════════════════════════════════════════════════════
with tab_saved:
    st.subheader("⭐ Saved Listings")
    st.caption("Listings you've starred for follow-up.")
    saved = [l for l in st.session_state["live_listings"]
             if l.get("status") == "saved" or l.get("saved")]
    if not saved:
        st.info("No saved listings yet. Star a listing from the Listings tab.")
    else:
        st.caption(f"{len(saved)} saved listing(s)")
    for l in saved:
        score = l.get("score", 0)
        eff_price = effective_price(l)
        payment = monthly_payment(eff_price)
        net_payment = payment - CRITERIA["roommate_income"]
        highlights = parse_json_field(l.get("highlights", []))
        red_flags = parse_json_field(l.get("red_flags", []))
        tag = l.get("tag", "")
        tag_html = f'<span style="background:#1565c0;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;margin-left:8px">{tag}</span>' if tag else ""
        score_html = f'<span style="background:{score_color(score)};color:#000;padding:3px 10px;border-radius:12px;font-weight:bold;font-size:14px">{score}/100</span>'

        st.markdown(f"""
<div style="border:1px solid #FFAB76;border-radius:10px;padding:16px 20px;margin-bottom:16px;background:#1a1a2e">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
    <div>
      <span style="font-size:17px;font-weight:bold">⭐ {l.get('address','')}</span>
      {tag_html}
      <br><span style="color:#aaa;font-size:13px">{l.get('neighborhood','Atlanta')} · {l.get('condition','Unknown')}</span>
    </div>
    <div style="text-align:right">{score_html}</div>
  </div>
</div>
""", unsafe_allow_html=True)

        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("List Price", f"${l.get('price',0):,}")
        s2.metric("Eff. Price", f"${eff_price:,}")
        s3.metric("Beds/Baths", f"{l.get('beds',0)}bd/{l.get('baths',0)}ba")
        s4.metric("Est. Payment", f"${payment:,.0f}/mo")
        s5.metric("After Roommate", f"${net_payment:,.0f}/mo")

        col_h, col_r = st.columns(2)
        with col_h:
            if highlights:
                st.markdown("**✅ Highlights**")
                for h in highlights:
                    st.markdown(f"- {h}")
        with col_r:
            if red_flags:
                st.markdown("**⚠️ Red Flags**")
                for rf in red_flags:
                    st.markdown(f"- {rf}")

        ai = l.get("ai_insight", "")
        if ai:
            with st.expander("🤖 AI Analysis"):
                st.info(ai)

        lkey = str(l.get("id", l.get("external_id", "")))
        sb1, sb2, sb3 = st.columns(3)
        lurl = l.get("listing_url", "")
        if lurl:
            sb1.link_button("🔗 View Listing", lurl)
        with sb2:
            if st.button("🗑️ Unsave", key=f"unsave_{lkey}"):
                _src = l.get("source", "manual")
                _unsave_listing_in_db(lkey, _src)  # persist to DB
                for item in st.session_state["live_listings"]:
                    if str(item.get("id", item.get("external_id", ""))) == lkey:
                        item["status"] = "active"
                        item["saved"] = False
                        break
                st.rerun()
        with sb3:
            if st.button("📋 Schedule Tour", key=f"saved_tour_{lkey}"):
                st.toast("Tour request noted — contact your agent!")

        st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════
with tab_calc:
    st.subheader("🧮 Mortgage & Affordability Calculator")

    k1, k2 = st.columns(2)
    with k1:
        calc_price = st.number_input("Home Price ($)", 100_000, 600_000, 265_000, 1_000)
        calc_down_pct = st.slider("Down Payment %", 3.0, 20.0, 3.5, 0.5)
        calc_rate = st.slider("Interest Rate %", 3.0, 10.0, 6.99, 0.01)
        calc_years = st.selectbox("Loan Term", [30, 20, 15], index=0)
        calc_dpa = st.number_input("Down Payment Assistance ($)", 0, 50_000, 20_000, 1_000)
        calc_roommate = st.number_input("Roommate Income ($/mo)", 0, 3_000, 1_200, 50)

    with k2:
        effective = calc_price - calc_dpa
        down_amt = effective * (calc_down_pct / 100)
        loan_amt = effective - down_amt
        r = calc_rate / 100 / 12
        n = calc_years * 12
        if r > 0:
            pmt = loan_amt * r * (1 + r) ** n / ((1 + r) ** n - 1)
        else:
            pmt = loan_amt / n
        net_pmt = pmt - calc_roommate
        total_paid = pmt * n
        total_interest = total_paid - loan_amt

        st.metric("List Price", f"${calc_price:,}")
        st.metric("After DPA", f"${effective:,}", delta=f"-${calc_dpa:,} assistance")
        st.metric("Down Payment", f"${down_amt:,.0f}", help=f"{calc_down_pct}% of ${effective:,}")
        st.metric("Loan Amount", f"${loan_amt:,.0f}")
        st.metric("Monthly Payment", f"${pmt:,.0f}/mo")
        st.metric("After Roommate", f"${net_pmt:,.0f}/mo",
                  delta=f"-${calc_roommate:,} roommate", delta_color="normal")
        st.metric("Total Interest (life of loan)", f"${total_interest:,.0f}")

        budget_ok = net_pmt <= CRITERIA["monthly_payment_max"]
        if budget_ok:
            st.success(f"✅ Net payment ${net_pmt:,.0f} is within your ${CRITERIA['monthly_payment_max']:,}/mo budget")
        else:
            st.error(f"❌ Net payment ${net_pmt:,.0f} exceeds your ${CRITERIA['monthly_payment_max']:,}/mo budget")

    # Amortization preview
    with st.expander("📊 First 12 Months Amortization"):
        rows = []
        bal = loan_amt
        for mo in range(1, 13):
            interest = bal * r
            principal_paid = pmt - interest
            bal -= principal_paid
            rows.append({
                "Month": mo,
                "Payment": f"${pmt:,.0f}",
                "Principal": f"${principal_paid:,.0f}",
                "Interest": f"${interest:,.0f}",
                "Balance": f"${max(bal,0):,.0f}",
            })
        import pandas as pd
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — CRITERIA
# ═══════════════════════════════════════════════════════════════════════════════
with tab_criteria:
    st.subheader("📌 Search Criteria & Strategy")

    st.markdown("### 💰 Budget")
    st.markdown(f"""
- **List price range:** ${CRITERIA['min_price']:,} – ${CRITERIA['max_price']:,}
- **Invest Atlanta DPA:** ${CRITERIA['invest_atlanta_amount']:,} (eligible census tracts)
- **Georgia Dream DPA:** ${CRITERIA['georgia_dream_amount']:,} (statewide fallback)
- **Effective price target:** ~$229k–$265k after assistance
- **Max monthly payment (net of roommate):** ${CRITERIA['monthly_payment_max']:,}/mo
- **Roommate income offset:** ${CRITERIA['roommate_income']:,}/mo
""")

    st.markdown("### 🏡 Property Requirements")
    st.markdown(f"""
- **Beds:** {CRITERIA['min_beds']}+ (4BR minimum for roommate strategy)
- **Baths:** {CRITERIA['min_baths']}+
- **Sqft:** {CRITERIA['min_sqft']:,}+
- **Max HOA:** ${CRITERIA['max_hoa']}/mo (prefer $0)
- **Max DOM:** {CRITERIA['max_dom']} days
- **Condition:** Move-in ready preferred; minor cosmetic OK
- **Year built:** 1980+ preferred (systems documentation required for older)
""")

    st.markdown("### 📍 Target Areas")
    cols = st.columns(2)
    with cols[0]:
        st.markdown("**Neighborhoods:**")
        for n in CRITERIA["target_neighborhoods"]:
            st.markdown(f"- {n}")
    with cols[1]:
        st.markdown("**ZIP Codes:**")
        for z in CRITERIA["target_zips"]:
            st.markdown(f"- {z}")

    st.markdown("### 🚗 Commute")
    st.markdown(f"""
- **Destination:** {CRITERIA['commute_destination']}
- **Max commute:** {CRITERIA['max_commute_min']} minutes
""")

    st.markdown("### 🏆 Scoring Weights")
    import pandas as pd
    from utils.real_estate import WEIGHTS
    weight_df = pd.DataFrame([
        {"Factor": k.replace("_", " ").title(), "Max Points": v}
        for k, v in WEIGHTS.items()
    ])
    st.dataframe(weight_df, use_container_width=True, hide_index=True)

    st.markdown("### 🔴 Auto Red Flags")
    st.markdown("""
- DOM > 60 days
- Year built < 1980 (without documentation)
- Roof age ≥ 15 years
- HVAC age ≥ 10 years
- HOA > $100/mo
- Price over $285,000
""")
