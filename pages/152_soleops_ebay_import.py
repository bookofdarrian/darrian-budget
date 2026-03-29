"""
SoleOps eBay Live Listings Import — Page 152
Pull your active eBay listings directly into SoleOps inventory.
Uses eBay Browse API (app-level token — no user OAuth required).
"""
import streamlit as st

st.set_page_config(
    page_title="SoleOps eBay Import — Peach State Savings",
    page_icon="🍑",
    layout="wide",
)

import re
import json
import base64
import datetime
import requests

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

# ── Sidebar ───────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                                   label="Overview",           icon="📊")
st.sidebar.page_link("pages/22_todo.py",                         label="Todo",               icon="✅")
st.sidebar.page_link("pages/118_soleops_inventory_manager.py",   label="Inventory",          icon="📦")
st.sidebar.page_link("pages/116_soleops_comprehensive_inventory_manager.py", label="Full Inventory", icon="🗂️")
st.sidebar.page_link("pages/120_soleops_platform_sales_sync.py", label="Platform Sync",      icon="🔄")
st.sidebar.page_link("pages/122_soleops_cross_listing_manager.py", label="Cross-Listing",    icon="🛒")
st.sidebar.page_link("pages/152_soleops_ebay_import.py",         label="eBay Import",        icon="🛍️")
st.sidebar.page_link("pages/17_personal_assistant.py",           label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

# ── Constants ─────────────────────────────────────────────────────────────────
PH   = "%s" if USE_POSTGRES else "?"
AUTO = "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"

EBAY_TOKEN_URL  = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
EBAY_BROWSE_SCOPE = "https://api.ebay.com/oauth/api_scope"

# Known sneaker brands for title parsing
SNEAKER_BRANDS = [
    "Nike", "Jordan", "Air Jordan", "Adidas", "Yeezy", "New Balance",
    "Puma", "Reebok", "Converse", "Vans", "Asics", "Saucony", "Brooks",
    "On Running", "Salehe Bembury", "New Balance", "HOKA", "Clarks",
    "Timberland", "Crocs", "UGG", "Under Armour", "Fila", "Diadora",
    "Mizuno", "Onitsuka Tiger", "Salomon", "Arc'teryx", "Stone Island",
]


# ── DB Setup ──────────────────────────────────────────────────────────────────
def _ensure_tables():
    conn = get_conn()
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS ebay_import_log (
            id              {AUTO},
            user_id         INTEGER NOT NULL,
            ebay_item_id    TEXT NOT NULL,
            title           TEXT,
            price           REAL,
            condition       TEXT,
            listing_url     TEXT,
            image_url       TEXT,
            imported        INTEGER DEFAULT 0,
            inventory_id    INTEGER,
            import_date     TEXT,
            raw_json        TEXT,
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

_ensure_tables()


# ── Helper: eBay App Token ────────────────────────────────────────────────────
def _get_app_token(client_id: str, client_secret: str) -> str | None:
    """Get eBay application-level OAuth token (client credentials grant)."""
    # Check session cache first
    cached = st.session_state.get("_ebay_app_token")
    cached_exp = st.session_state.get("_ebay_token_exp", datetime.datetime.min)
    if cached and datetime.datetime.now() < cached_exp:
        return cached

    try:
        creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        resp = requests.post(
            EBAY_TOKEN_URL,
            headers={
                "Authorization": f"Basic {creds}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "client_credentials",
                "scope": EBAY_BROWSE_SCOPE,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data.get("access_token")
        expires_in = data.get("expires_in", 7200)
        if token:
            st.session_state["_ebay_app_token"] = token
            st.session_state["_ebay_token_exp"] = (
                datetime.datetime.now() + datetime.timedelta(seconds=expires_in - 60)
            )
        return token
    except Exception as e:
        st.error(f"❌ eBay token error: {e}")
        return None


# ── Helper: Fetch Seller Listings ─────────────────────────────────────────────
def _fetch_seller_listings(seller_username: str, token: str, max_results: int = 200) -> list[dict]:
    """
    Fetch all active listings for a given eBay seller username.
    Uses Browse API: GET /buy/browse/v1/item_summary/search?filter=sellers:{username}
    """
    all_items = []
    offset = 0
    limit = min(max_results, 200)

    while len(all_items) < max_results:
        try:
            resp = requests.get(
                EBAY_SEARCH_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
                    "Content-Type": "application/json",
                },
                params={
                    "q": "",
                    "filter": f"sellers:{{{seller_username}}}",
                    "limit": min(limit, 200),
                    "offset": offset,
                    "fieldgroups": "FULL",
                },
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("itemSummaries", [])
            if not items:
                break
            all_items.extend(items)
            total = data.get("total", 0)
            offset += len(items)
            if offset >= total or offset >= max_results:
                break
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 404:
                st.warning(f"⚠️ Seller '{seller_username}' not found or has no public listings.")
            else:
                st.error(f"❌ eBay API error {resp.status_code}: {resp.text[:300]}")
            break
        except Exception as e:
            st.error(f"❌ Fetch error: {e}")
            break

    return all_items


# ── Helper: Parse Title → Fields ──────────────────────────────────────────────
def _parse_title(title: str) -> dict:
    """
    Attempt to extract brand, model, size, colorway from eBay listing title.
    Works well for standard sneaker title formats.
    """
    result = {"brand": "", "model": "", "colorway": "", "size": ""}

    # Extract size — patterns: "Sz 10", "Size 10.5", "SZ10", "sz 9.5", "Men's 11"
    size_match = re.search(
        r"(?:sz|size|men'?s?|women'?s?|gs|ps|td|youth)\s*(\d{1,2}(?:\.\d)?)",
        title,
        re.IGNORECASE,
    )
    if size_match:
        result["size"] = size_match.group(1)

    # Extract brand
    title_lower = title.lower()
    for brand in SNEAKER_BRANDS:
        if brand.lower() in title_lower:
            result["brand"] = brand
            break

    # Extract colorway — usually in quotes: 'Chicago', "Bred", (University Red)
    colorway_match = re.search(r"['\"]([^'\"]{3,40})['\"]|'\s*([^']{3,40})\s*'", title)
    if colorway_match:
        result["colorway"] = (colorway_match.group(1) or colorway_match.group(2) or "").strip()

    # Model = title minus brand, size, colorway, common filler words
    model = title
    for filler in ["NEW", "DS", "DEADSTOCK", "IN HAND", "SHIPS FAST", "FREE SHIPPING",
                   "FAST SHIP", "AUTHENTIC", "OG ALL", "W/", "W/ BOX"]:
        model = re.sub(re.escape(filler), "", model, flags=re.IGNORECASE)
    if result["brand"]:
        model = re.sub(re.escape(result["brand"]), "", model, flags=re.IGNORECASE)
    if result["size"]:
        model = re.sub(rf"(?:sz|size|men'?s?|women'?s?)\s*{re.escape(result['size'])}", "", model,
                       flags=re.IGNORECASE)
    model = re.sub(r"\s{2,}", " ", model).strip(" -–|/,")
    result["model"] = model[:100] if model else title[:100]

    return result


# ── Helper: Import to soleops_inventory ──────────────────────────────────────
def _import_listing(item: dict, uid: int) -> int | None:
    """Import a single eBay listing to soleops_inventory. Returns new inventory ID."""
    title   = item.get("title", "")
    price   = float((item.get("price") or {}).get("value", 0) or 0)
    cond    = item.get("condition", "Used")
    item_id = item.get("itemId", "")

    parsed = _parse_title(title)
    brand  = parsed["brand"] or "Unknown"
    model  = parsed["model"] or title[:200]
    size   = parsed["size"] or "?"
    colorway = parsed["colorway"] or ""

    conn = get_conn()
    cur  = conn.cursor()

    # Check if already imported (by ebay_item_id in notes or source)
    cur.execute(
        f"SELECT id FROM soleops_inventory WHERE user_id={PH} AND notes LIKE {PH} LIMIT 1",
        (uid, f"%ebay:{item_id}%")
    )
    existing = cur.fetchone()
    if existing:
        conn.close()
        return existing[0]

    # Map eBay condition string
    cond_map = {
        "NEW": "New", "NEW_WITH_DEFECTS": "New w/ Defects",
        "NEW_OTHER": "New (Other)", "USED_EXCELLENT": "Used - Excellent",
        "USED_VERY_GOOD": "Used - Very Good", "USED_GOOD": "Used - Good",
        "USED_ACCEPTABLE": "Used - Acceptable",
    }
    clean_cond = cond_map.get(cond.upper().replace(" ", "_"), cond)

    db_exec(conn, f"""
        INSERT INTO soleops_inventory
            (user_id, brand, model, colorway, size, condition,
             list_prices, listed_platforms, status, notes, purchase_source)
        VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})
    """, (
        uid, brand, model, colorway, size, clean_cond,
        json.dumps({"eBay": price}),
        json.dumps(["eBay"]),
        "listed",
        f"Imported from eBay | ebay:{item_id}",
        "eBay (auto-import)",
    ))
    cur.execute(
        f"SELECT id FROM soleops_inventory WHERE user_id={PH} AND notes LIKE {PH} ORDER BY id DESC LIMIT 1",
        (uid, f"%ebay:{item_id}%")
    )
    row = cur.fetchone()
    new_id = row[0] if row else None
    conn.commit()
    conn.close()
    return new_id


# ── Helper: Log import ────────────────────────────────────────────────────────
def _log_import(uid: int, item: dict, inventory_id: int | None):
    price = float((item.get("price") or {}).get("value", 0) or 0)
    image = ((item.get("image") or {}).get("imageUrl") or
             (item.get("thumbnailImages") or [{}])[0].get("imageUrl", ""))
    conn = get_conn()
    # Upsert by ebay_item_id
    db_exec(conn, f"DELETE FROM ebay_import_log WHERE user_id={PH} AND ebay_item_id={PH}",
            (uid, item.get("itemId", "")))
    db_exec(conn, f"""
        INSERT INTO ebay_import_log
            (user_id, ebay_item_id, title, price, condition, listing_url, image_url,
             imported, inventory_id, import_date, raw_json)
        VALUES ({PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH},{PH})
    """, (
        uid,
        item.get("itemId", ""),
        item.get("title", ""),
        price,
        item.get("condition", ""),
        item.get("itemWebUrl", ""),
        image,
        1 if inventory_id else 0,
        inventory_id,
        datetime.date.today().isoformat(),
        json.dumps(item)[:4000],
    ))
    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="background: linear-gradient(135deg, #0a0a0a, #1a1a2e); border-left: 4px solid #3b82f6;
            padding: 18px 22px; border-radius: 10px; margin-bottom: 16px;">
    <h1 style="color: #3b82f6; margin: 0 0 6px 0;">🛍️ eBay Live Listings Import</h1>
    <p style="color: #94a3b8; margin: 0;">Pull your active eBay listings directly into SoleOps inventory.</p>
</div>
""", unsafe_allow_html=True)

uid = st.session_state.get("user_id", 1)

# ── Quick status bar ──────────────────────────────────────────────────────────
client_id     = get_setting("ebay_client_id", "")
client_secret = get_setting("ebay_client_secret", "")
seller_name   = get_setting("soleops_ebay_seller_username", "")

col1, col2, col3 = st.columns(3)
col1.metric("eBay Client ID", "✅ Set" if client_id else "❌ Not set")
col2.metric("eBay Client Secret", "✅ Set" if client_secret else "❌ Not set")
col3.metric("Seller Username", seller_name if seller_name else "❌ Not set")

st.divider()

# ── TABS ──────────────────────────────────────────────────────────────────────
tabs = st.tabs(["🔴 Live Listings", "📦 Import to SoleOps", "📋 Import Log", "⚙️ Settings"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 0 — LIVE LISTINGS (fetch & preview)
# ══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown("### 🔴 Your Live eBay Listings")

    if not client_id or not client_secret:
        st.error("⚠️ eBay API credentials not set. Go to **⚙️ Settings** tab to add them.")
    elif not seller_name:
        st.warning("⚠️ eBay seller username not set. Go to **⚙️ Settings** tab to add it.")
    else:
        col_fetch, col_count = st.columns([2, 1])
        with col_fetch:
            max_fetch = st.slider("Max listings to fetch", 10, 500, 200, step=10)
        with col_count:
            st.caption(f"Seller: **{seller_name}**")

        if st.button("🔄 Fetch Live eBay Listings", type="primary", use_container_width=True):
            with st.spinner(f"🔑 Getting eBay token..."):
                token = _get_app_token(client_id, client_secret)

            if token:
                with st.spinner(f"📡 Fetching listings for **{seller_name}**..."):
                    items = _fetch_seller_listings(seller_name, token, max_results=max_fetch)
                st.session_state["_ebay_fetched_items"] = items
                if items:
                    st.success(f"✅ Found **{len(items)}** active listings for @{seller_name}")
                else:
                    st.warning("No listings found. Check seller username and try again.")

        items = st.session_state.get("_ebay_fetched_items", [])
        if items:
            st.markdown(f"**{len(items)} listings fetched** — review before importing:")
            st.caption("💡 Prices shown are your current eBay listing prices.")

            # Search/filter
            search_q = st.text_input("🔍 Filter listings", placeholder="e.g. Jordan, Nike, Yeezy...")

            display_items = [
                i for i in items
                if not search_q or search_q.lower() in i.get("title", "").lower()
            ]

            # Table view
            import pandas as pd
            rows = []
            for item in display_items:
                price = (item.get("price") or {}).get("value", "—")
                image = ((item.get("image") or {}).get("imageUrl") or
                         (item.get("thumbnailImages") or [{}])[0].get("imageUrl", ""))
                parsed = _parse_title(item.get("title", ""))
                rows.append({
                    "Title": item.get("title", "")[:70],
                    "Brand": parsed["brand"] or "?",
                    "Size": parsed["size"] or "?",
                    "Price": f"${float(price):.2f}" if price != "—" else "—",
                    "Condition": item.get("condition", ""),
                    "Item ID": item.get("itemId", ""),
                    "URL": item.get("itemWebUrl", ""),
                })

            df = pd.DataFrame(rows)
            st.dataframe(df.drop(columns=["URL"]), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — IMPORT TO SOLEOPS
# ══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown("### 📦 Import to SoleOps Inventory")

    items = st.session_state.get("_ebay_fetched_items", [])

    if not items:
        st.info("First go to **🔴 Live Listings** tab and click **Fetch Live eBay Listings**.")
    else:
        st.markdown(f"**{len(items)} listings ready to import.**")
        st.caption("Imports as `status = 'listed'` with eBay price pre-filled. Won't duplicate — already-imported listings are skipped.")

        # Check which ones are already imported
        conn = get_conn()
        cur  = conn.cursor()
        cur.execute(
            f"SELECT ebay_item_id FROM ebay_import_log WHERE user_id={PH} AND imported=1",
            (uid,)
        )
        already_imported = {r[0] for r in cur.fetchall()}
        conn.close()

        new_items    = [i for i in items if i.get("itemId") not in already_imported]
        done_items   = [i for i in items if i.get("itemId") in already_imported]

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Total Fetched", len(items))
        col_b.metric("New (not yet imported)", len(new_items), delta=f"+{len(new_items)}")
        col_c.metric("Already Imported", len(done_items))

        if new_items:
            st.markdown("---")
            import_mode = st.radio(
                "Import mode:",
                ["Import ALL new listings", "Select specific listings to import"],
                horizontal=True,
            )

            selected_ids = set()
            if import_mode == "Select specific listings to import":
                import pandas as pd
                options = {
                    f"{i.get('title','')[:60]} — ${float((i.get('price') or {}).get('value', 0)):.2f}": i.get("itemId")
                    for i in new_items
                }
                chosen = st.multiselect("Select listings to import:", list(options.keys()))
                selected_ids = {options[c] for c in chosen}
                to_import = [i for i in new_items if i.get("itemId") in selected_ids]
            else:
                to_import = new_items

            if st.button(
                f"📥 Import {len(to_import)} Listing{'s' if len(to_import) != 1 else ''} to SoleOps",
                type="primary",
                use_container_width=True,
                disabled=len(to_import) == 0,
            ):
                progress = st.progress(0)
                imported_count = 0
                errors = []

                for idx, item in enumerate(to_import):
                    try:
                        inv_id = _import_listing(item, uid)
                        _log_import(uid, item, inv_id)
                        imported_count += 1
                    except Exception as e:
                        errors.append(f"{item.get('title','')[:40]}: {e}")
                    progress.progress((idx + 1) / len(to_import))

                progress.empty()

                if imported_count:
                    st.success(f"✅ Imported **{imported_count}** listings to SoleOps inventory!")
                    st.balloons()
                if errors:
                    with st.expander(f"⚠️ {len(errors)} errors"):
                        for e in errors:
                            st.write(e)

                # Clear fetched cache to refresh counts
                if "_ebay_fetched_items" in st.session_state:
                    del st.session_state["_ebay_fetched_items"]
                st.rerun()
        else:
            st.success("✅ All fetched listings have already been imported!")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — IMPORT LOG
# ══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown("### 📋 Import History")

    conn = get_conn()
    cur  = conn.cursor()
    cur.execute(
        f"""SELECT ebay_item_id, title, price, condition, listing_url, import_date, inventory_id
            FROM ebay_import_log
            WHERE user_id={PH} AND imported=1
            ORDER BY import_date DESC, id DESC
            LIMIT 500""",
        (uid,)
    )
    log_rows = cur.fetchall()
    conn.close()

    if not log_rows:
        st.info("No imports yet. Go to **📦 Import to SoleOps** to get started.")
    else:
        import pandas as pd
        df_log = pd.DataFrame(log_rows, columns=["eBay Item ID", "Title", "Price", "Condition",
                                                   "eBay URL", "Import Date", "Inv ID"])
        df_log["Price"] = df_log["Price"].apply(lambda x: f"${float(x):.2f}" if x else "—")
        df_log["Title"] = df_log["Title"].apply(lambda x: (x or "")[:65])

        st.metric("Total Imported", len(df_log))
        st.dataframe(df_log.drop(columns=["eBay URL"]), use_container_width=True, hide_index=True)

        # Quick links
        st.markdown("---")
        st.markdown("**Quick Links:**")
        c1, c2 = st.columns(2)
        c1.page_link("pages/118_soleops_inventory_manager.py", label="View SoleOps Inventory", icon="📦")
        c2.page_link("pages/116_soleops_comprehensive_inventory_manager.py", label="Full Inventory Manager", icon="🗂️")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown("### ⚙️ eBay Connection Settings")

    with st.form("ebay_settings_form"):
        st.markdown("#### eBay API Credentials")
        st.caption("Get these from [developer.ebay.com](https://developer.ebay.com) → My Account → Application Keys (Production)")

        new_client_id = st.text_input(
            "eBay Client ID (App ID)",
            value=get_setting("ebay_client_id", ""),
            type="password",
            placeholder="e.g. DarrianB-404Sole-PRD-xxxxxxxxxxxx",
        )
        new_client_secret = st.text_input(
            "eBay Client Secret (Cert ID)",
            value=get_setting("ebay_client_secret", ""),
            type="password",
            placeholder="PRD-xxxxxxxxxxxxxxxxxxxx",
        )

        st.markdown("---")
        st.markdown("#### Your eBay Seller Username")
        st.caption("This is your public eBay seller handle — visible on your eBay profile page.")
        new_seller = st.text_input(
            "eBay Seller Username",
            value=get_setting("soleops_ebay_seller_username", ""),
            placeholder="e.g. sole404ops or your eBay username",
        )

        saved = st.form_submit_button("💾 Save Settings", type="primary", use_container_width=True)
        if saved:
            if new_client_id.strip():
                set_setting("ebay_client_id", new_client_id.strip())
            if new_client_secret.strip():
                set_setting("ebay_client_secret", new_client_secret.strip())
            if new_seller.strip():
                set_setting("soleops_ebay_seller_username", new_seller.strip())
            st.success("✅ Settings saved!")
            # Clear cached token on credential change
            for k in ("_ebay_app_token", "_ebay_token_exp", "_ebay_fetched_items"):
                st.session_state.pop(k, None)
            st.rerun()

    st.markdown("---")
    st.markdown("#### 🔌 Test Connection")
    if st.button("🧪 Test eBay API Token", use_container_width=True):
        cid = get_setting("ebay_client_id", "")
        csec = get_setting("ebay_client_secret", "")
        if not cid or not csec:
            st.error("Set Client ID and Client Secret first.")
        else:
            # Clear cache to force fresh token
            st.session_state.pop("_ebay_app_token", None)
            with st.spinner("Testing..."):
                tok = _get_app_token(cid, csec)
            if tok:
                st.success(f"✅ Connected! Token length: {len(tok)} chars. eBay API is live.")
            else:
                st.error("❌ Could not get token. Check your credentials.")

    st.markdown("---")
    st.markdown("#### 📖 How This Works")
    st.markdown("""
1. **App-level token** — Uses your eBay Client ID + Secret to get an application OAuth token (no user login required)
2. **Browse API search** — Searches eBay's public catalog filtered to your seller username
3. **Auto-parse** — Extracts brand, model, size from listing titles using regex patterns
4. **One-click import** — Writes to `soleops_inventory` table as `status = 'listed'` with eBay price
5. **No duplicates** — Tracks imported listings by eBay Item ID in `ebay_import_log`

> ⚠️ **Limitation:** The Browse API only returns publicly visible listings. If your eBay store has
> restricted/private visibility settings, some listings may not appear. For 100% private seller access,
> a user-level OAuth token (Trading API) would be needed — contact Darrian to add this.
""")
