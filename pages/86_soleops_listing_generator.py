"""
SoleOps AI Listing Generator — Page 86
=========================================
AI-powered eBay + Mercari listing generator for sneaker resellers.
  - Claude generates: eBay title (80 chars), eBay description, Mercari description
  - Live market price fetch (eBay + Mercari comps)
  - AI-suggested price strategy (5% below avg for fast sale)
  - One-click copy for every section
  - Saved drafts with full CRUD
  - Platform-specific tone (eBay vs Mercari buyers are different)
"""
import base64
import random
import streamlit as st
import pandas as pd
from datetime import datetime, date

import requests

from utils.db import (
    get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
)
from utils.auth import (
    require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css
)

st.set_page_config(
    page_title="SoleOps AI Listing Generator — Peach State Savings",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="auto",
)
init_db()
inject_soleops_css()
require_login()

# ── Sidebar ────────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                          label="Overview",           icon="📊")
st.sidebar.page_link("pages/22_todo.py",                label="✅ Todo",            icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",   label="🎬 Creator",         icon="🎬")
st.sidebar.page_link("pages/25_notes.py",               label="📝 Notes",           icon="📝")
st.sidebar.page_link("pages/26_media_library.py",       label="🎵 Media Library",   icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",  label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

# ── Constants ──────────────────────────────────────────────────────────────────
CONDITIONS = ["Deadstock / New (DS)", "Like New (VNDS)", "Good (worn 1-3x)", "Fair (worn)", "Poor (heavy wear)"]
SIZES      = [str(s) for s in [
    4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5,
    10, 10.5, 11, 11.5, 12, 12.5, 13, 14, 15
]]
PLATFORMS  = ["eBay", "Mercari", "Both (eBay + Mercari)"]

EBAY_TOKEN_URL  = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
EBAY_CATEGORY   = "15709"
EBAY_FEE_RATE   = 0.129
EBAY_FEE_FLAT   = 0.30
MERCARI_FEE_RATE= 0.10
MERCARI_FEE_FLAT= 0.30

MERCARI_HEADERS = {
    "Content-Type": "application/json",
    "X-Platform":   "web",
    "Accept":       "application/json, text/plain, */*",
    "User-Agent":   "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Origin":       "https://www.mercari.com",
    "Referer":      "https://www.mercari.com/",
}


# ── DB helpers ─────────────────────────────────────────────────────────────────
def _ensure_tables() -> None:
    conn = get_conn()
    if USE_POSTGRES:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS soleops_listing_drafts (
                id                  SERIAL PRIMARY KEY,
                user_id             INTEGER NOT NULL DEFAULT 1,
                shoe_name           TEXT NOT NULL,
                sku                 TEXT DEFAULT '',
                size                TEXT DEFAULT '',
                condition           TEXT DEFAULT '',
                colorway            TEXT DEFAULT '',
                extra_notes         TEXT DEFAULT '',
                target_platform     TEXT DEFAULT 'Both',
                cogs                REAL DEFAULT 0,
                ebay_avg_price      REAL DEFAULT 0,
                mercari_avg_price   REAL DEFAULT 0,
                suggested_price     REAL DEFAULT 0,
                ebay_title          TEXT DEFAULT '',
                ebay_description    TEXT DEFAULT '',
                mercari_description TEXT DEFAULT '',
                pricing_strategy    TEXT DEFAULT '',
                keywords            TEXT DEFAULT '',
                status              TEXT DEFAULT 'draft',
                created_at          TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
                updated_at          TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
            )
        """)
    else:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS soleops_listing_drafts (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id             INTEGER NOT NULL DEFAULT 1,
                shoe_name           TEXT NOT NULL,
                sku                 TEXT DEFAULT '',
                size                TEXT DEFAULT '',
                condition           TEXT DEFAULT '',
                colorway            TEXT DEFAULT '',
                extra_notes         TEXT DEFAULT '',
                target_platform     TEXT DEFAULT 'Both',
                cogs                REAL DEFAULT 0,
                ebay_avg_price      REAL DEFAULT 0,
                mercari_avg_price   REAL DEFAULT 0,
                suggested_price     REAL DEFAULT 0,
                ebay_title          TEXT DEFAULT '',
                ebay_description    TEXT DEFAULT '',
                mercari_description TEXT DEFAULT '',
                pricing_strategy    TEXT DEFAULT '',
                keywords            TEXT DEFAULT '',
                status              TEXT DEFAULT 'draft',
                created_at          TEXT DEFAULT (datetime('now')),
                updated_at          TEXT DEFAULT (datetime('now'))
            )
        """)
    conn.commit()
    conn.close()


_ensure_tables()


# ── Price fetching (reused from page 68 pattern) ────────────────────────────────
def _get_ebay_token() -> str | None:
    client_id     = get_setting("ebay_app_id", "")
    client_secret = get_setting("ebay_cert_id", "")
    if not client_id or not client_secret:
        return None
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    try:
        r = requests.post(
            EBAY_TOKEN_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type":  "application/x-www-form-urlencoded",
            },
            data="grant_type=client_credentials&scope=https%3A%2F%2Fapi.ebay.com%2Foauth%2Fapi_scope",
            timeout=15,
        )
        return r.json().get("access_token") if r.status_code == 200 else None
    except Exception:
        return None


def _fetch_ebay_avg(query: str) -> dict:
    token = _get_ebay_token()
    if not token:
        # Mock fallback
        seed  = sum(ord(c) for c in query)
        rng   = random.Random(seed + 1)
        base  = rng.randint(100, 400)
        prices = [base + rng.randint(-40, 40) for _ in range(10)]
        return {"avg": round(sum(prices) / len(prices), 2), "low": min(prices), "count": len(prices), "mock": True}
    try:
        r = requests.get(
            EBAY_SEARCH_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={
                "q":            query,
                "category_ids": EBAY_CATEGORY,
                "filter":       "buyingOptions:{FIXED_PRICE}",
                "limit":        20,
            },
            timeout=15,
        )
        items  = r.json().get("itemSummaries", []) if r.status_code == 200 else []
        prices = [float(i.get("price", {}).get("value", 0)) for i in items if i.get("price")]
        prices = [p for p in prices if p > 0]
        return {
            "avg":   round(sum(prices) / len(prices), 2) if prices else 0.0,
            "low":   round(min(prices), 2) if prices else 0.0,
            "count": len(prices),
            "mock":  False,
        }
    except Exception:
        return {"avg": 0.0, "low": 0.0, "count": 0, "mock": True}


def _fetch_mercari_avg(query: str) -> dict:
    payload = {
        "pageSize": 30,
        "searchCondition": {
            "keyword":    query,
            "status":     ["STATUS_ON_SALE"],
            "sort":       "SORT_SCORE",
            "order":      "ORDER_DESC",
        },
        "defaultDatasets": ["DATASET_TYPE_MERCARI"],
    }
    try:
        r = requests.post(
            "https://api.mercari.com/v2/entities:search",
            headers=MERCARI_HEADERS,
            json=payload,
            timeout=20,
        )
        items  = r.json().get("items", []) if r.status_code == 200 else []
        prices = [int(i.get("price", 0)) for i in items if i.get("price")]
        prices = [p for p in prices if p > 0]
        if prices:
            return {"avg": round(sum(prices) / len(prices), 2), "low": min(prices), "count": len(prices), "mock": False}
    except Exception:
        pass
    # Mock fallback
    seed   = sum(ord(c) for c in query)
    rng    = random.Random(seed + 2)
    base   = rng.randint(80, 350)
    prices = [base + rng.randint(-30, 30) for _ in range(10)]
    return {"avg": round(sum(prices) / len(prices), 2), "low": min(prices), "count": len(prices), "mock": True}


# ── Claude AI listing generator ────────────────────────────────────────────────
def _generate_listing(
    shoe_name: str,
    sku: str,
    size: str,
    condition: str,
    colorway: str,
    extra_notes: str,
    target_platform: str,
    cogs: float,
    ebay_avg: float,
    mercari_avg: float,
    api_key: str,
) -> dict:
    """Call Claude to generate complete listing content. Returns dict with all fields."""
    if not api_key:
        return {"error": "No Anthropic API key configured."}

    ebay_fee     = round(ebay_avg * EBAY_FEE_RATE + EBAY_FEE_FLAT, 2) if ebay_avg > 0 else 0
    mercari_fee  = round(mercari_avg * MERCARI_FEE_RATE + MERCARI_FEE_FLAT, 2) if mercari_avg > 0 else 0
    ebay_net     = round(ebay_avg - ebay_fee, 2) if ebay_avg > 0 else 0
    mercari_net  = round(mercari_avg - mercari_fee, 2) if mercari_avg > 0 else 0
    suggested    = round(ebay_avg * 0.95, 2) if ebay_avg > 0 else 0  # 5% below avg for fast sale

    # Pick best platform suggestion
    best_plat = "eBay" if ebay_net >= mercari_net else "Mercari"

    prompt = f"""You are an expert sneaker reseller copywriter who writes high-converting eBay and Mercari listings.

SHOE DETAILS:
- Name: {shoe_name}
- SKU: {sku if sku else "Unknown"}
- Size: {size}
- Condition: {condition}
- Colorway: {colorway if colorway else "Standard"}
- Seller Notes: {extra_notes if extra_notes else "None"}

MARKET DATA:
- eBay avg listing price: ${ebay_avg:.2f} (net after fees: ${ebay_net:.2f})
- Mercari avg listing price: ${mercari_avg:.2f} (net after fees: ${mercari_net:.2f})
- Seller's cost basis (COGS): ${cogs:.2f}
- Suggested listing price: ${suggested:.2f} (5% below eBay avg for fast sale)
- Best platform: {best_plat}

Generate a complete listing package. Respond ONLY in this exact JSON format with no other text:

{{
  "ebay_title": "<80 chars max, keyword-rich, Title Case, NO ALL CAPS, include key details like size and condition>",
  "ebay_description": "<3-4 paragraphs: 1) Shoe description + key features, 2) Condition details being honest, 3) What's included (box? laces? extra insoles?), 4) Shipping + buyer assurance. Professional tone. Include key search keywords naturally.>",
  "mercari_description": "<Shorter, more casual/conversational than eBay. 2-3 paragraphs. Mercari buyers respond to friendly, transparent descriptions. Include condition details, size, and a fair price justification.>",
  "pricing_strategy": "<2-3 sentences: Specific recommended list price, which platform to list on first, and why. Include break-even analysis and expected days to sell.>",
  "keywords": "<10-15 comma-separated keywords for eBay title/description optimization>",
  "suggested_price": {suggested}
}}"""

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()

        # Parse JSON response
        import json
        # Strip markdown code block if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        result["suggested_price"] = float(result.get("suggested_price", suggested))
        return result
    except Exception as e:
        return {"error": str(e)}


# ── Draft DB helpers ────────────────────────────────────────────────────────────
def _save_draft(data: dict) -> int:
    conn = get_conn()
    c = db_exec(conn, """
        INSERT INTO soleops_listing_drafts
            (user_id, shoe_name, sku, size, condition, colorway, extra_notes,
             target_platform, cogs, ebay_avg_price, mercari_avg_price,
             suggested_price, ebay_title, ebay_description, mercari_description,
             pricing_strategy, keywords, status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        1, data["shoe_name"], data.get("sku", ""), data.get("size", ""),
        data.get("condition", ""), data.get("colorway", ""), data.get("extra_notes", ""),
        data.get("target_platform", "Both"), data.get("cogs", 0),
        data.get("ebay_avg_price", 0), data.get("mercari_avg_price", 0),
        data.get("suggested_price", 0), data.get("ebay_title", ""),
        data.get("ebay_description", ""), data.get("mercari_description", ""),
        data.get("pricing_strategy", ""), data.get("keywords", ""),
        data.get("status", "draft"),
    ))
    conn.commit()
    last_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0] if not USE_POSTGRES else 0
    conn.close()
    return last_id


def _load_drafts() -> pd.DataFrame:
    conn = get_conn()
    try:
        if USE_POSTGRES:
            import psycopg2.extras
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            c.execute("SELECT * FROM soleops_listing_drafts ORDER BY created_at DESC")
            rows = c.fetchall()
            df = pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()
        else:
            import pandas as _pd
            df = _pd.read_sql("SELECT * FROM soleops_listing_drafts ORDER BY created_at DESC", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def _delete_draft(draft_id: int) -> None:
    conn = get_conn()
    db_exec(conn, "DELETE FROM soleops_listing_drafts WHERE id = ?", (draft_id,))
    conn.commit()
    conn.close()


def _update_draft_status(draft_id: int, status: str) -> None:
    conn = get_conn()
    db_exec(conn, "UPDATE soleops_listing_drafts SET status = ? WHERE id = ?", (status, draft_id))
    conn.commit()
    conn.close()


# ── Page header ────────────────────────────────────────────────────────────────
st.title("✍️ SoleOps AI Listing Generator")
st.caption(
    "Stop writing listings from scratch. Enter your shoe details → "
    "Claude generates a complete eBay title, eBay description, and Mercari description in seconds."
)
st.markdown("---")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_gen, tab_drafts, tab_tips = st.tabs([
    "✨ Generate Listing",
    "📋 Saved Drafts",
    "💡 Listing Tips",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — GENERATE
# ══════════════════════════════════════════════════════════════════════════════
with tab_gen:
    st.subheader("✨ AI-Powered Listing Generator")

    api_key = get_setting("anthropic_api_key", "")
    if not api_key:
        st.warning(
            "⚠️ No Anthropic API key found. Add it in the P&L Dashboard → Tax Summary → "
            "AI Tax & Settings. You need Claude to generate listings."
        )

    # ── Input form ─────────────────────────────────────────────────────────────
    with st.form("listing_form"):
        st.markdown("**📋 Shoe Details**")
        r1c1, r1c2, r1c3 = st.columns(3)
        with r1c1:
            shoe_name = st.text_input(
                "Shoe Name *",
                placeholder="Air Jordan 4 Retro Red Thunder",
                help="Be specific — include brand, model, and colorway name",
            )
            sku = st.text_input("SKU / Style Code", placeholder="CT8527-016")
        with r1c2:
            size      = st.selectbox("Size (Men's)", SIZES, index=SIZES.index("10"))
            condition = st.selectbox("Condition", CONDITIONS)
        with r1c3:
            colorway    = st.text_input("Colorway", placeholder="Black/Fire Red-Cement Grey")
            extra_notes = st.text_area(
                "Additional Notes",
                placeholder="OG box included. Tried on once. No yellowing. All insoles + extra lace set.",
                height=80,
                help="Any condition details, what's included, defects to disclose honestly",
            )

        st.markdown("---")
        st.markdown("**💰 Pricing Context**")
        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1:
            cogs = st.number_input(
                "Your Buy Price (COGS) $",
                min_value=0.0, value=150.0, step=5.0, format="%.2f",
                help="What you paid for this pair",
            )
        with r2c2:
            target_platform = st.selectbox("Target Platform", PLATFORMS, index=2)
        with r2c3:
            fetch_prices = st.checkbox(
                "🔍 Fetch live market prices",
                value=True,
                help="Pulls current eBay + Mercari prices to inform AI pricing strategy",
            )

        st.markdown("---")
        submitted = st.form_submit_button(
            "✨ Generate Listing with Claude",
            type="primary",
            use_container_width=True,
        )

    # ── Process form submission ─────────────────────────────────────────────────
    if submitted:
        if not shoe_name.strip():
            st.error("Shoe name is required.")
            st.stop()
        if not api_key:
            st.error("Add your Anthropic API key to generate listings.")
            st.stop()

        # Fetch market prices
        ebay_data     = {"avg": 0.0, "low": 0.0, "count": 0, "mock": True}
        mercari_data  = {"avg": 0.0, "low": 0.0, "count": 0, "mock": True}
        search_query  = f"{shoe_name} size {size}" if "size" not in shoe_name.lower() else shoe_name

        if fetch_prices:
            price_cols = st.columns(2)
            with price_cols[0]:
                with st.spinner("🔍 Fetching eBay prices..."):
                    ebay_data = _fetch_ebay_avg(search_query)
                mock_label = " (mock)" if ebay_data.get("mock") else " ✅"
                st.metric(f"eBay Avg{mock_label}", f"${ebay_data['avg']:.2f}", delta=f"{ebay_data['count']} listings")
            with price_cols[1]:
                with st.spinner("🔍 Fetching Mercari prices..."):
                    mercari_data = _fetch_mercari_avg(search_query)
                mock_label = " (mock)" if mercari_data.get("mock") else " ✅"
                st.metric(f"Mercari Avg{mock_label}", f"${mercari_data['avg']:.2f}", delta=f"{mercari_data['count']} listings")

        st.markdown("---")

        # Generate listing with Claude
        with st.spinner("🤖 Claude is writing your listing..."):
            result = _generate_listing(
                shoe_name=shoe_name.strip(),
                sku=sku.strip(),
                size=size,
                condition=condition,
                colorway=colorway.strip(),
                extra_notes=extra_notes.strip(),
                target_platform=target_platform,
                cogs=cogs,
                ebay_avg=ebay_data["avg"],
                mercari_avg=mercari_data["avg"],
                api_key=api_key,
            )

        if "error" in result:
            st.error(f"❌ Generation failed: {result['error']}")
            st.stop()

        # ── Store result in session ────────────────────────────────────────────
        st.session_state["last_generated"] = {
            "shoe_name":            shoe_name.strip(),
            "sku":                  sku.strip(),
            "size":                 size,
            "condition":            condition,
            "colorway":             colorway.strip(),
            "extra_notes":          extra_notes.strip(),
            "target_platform":      target_platform,
            "cogs":                 cogs,
            "ebay_avg_price":       ebay_data["avg"],
            "mercari_avg_price":    mercari_data["avg"],
            "suggested_price":      result.get("suggested_price", 0),
            "ebay_title":           result.get("ebay_title", ""),
            "ebay_description":     result.get("ebay_description", ""),
            "mercari_description":  result.get("mercari_description", ""),
            "pricing_strategy":     result.get("pricing_strategy", ""),
            "keywords":             result.get("keywords", ""),
        }

    # ── Display generated listing ──────────────────────────────────────────────
    gen = st.session_state.get("last_generated")
    if gen:
        st.success("✅ Listing generated! Copy any section with one click.")
        st.markdown("---")

        # ── Pricing Strategy Banner ───────────────────────────────────────────
        if gen.get("pricing_strategy"):
            st.markdown(
                f"<div style='background:#1a2e1a;border:1px solid #3a6b3a;border-radius:10px;"
                f"padding:16px 20px;margin-bottom:20px;'>"
                f"<div style='color:#7ec87e;font-weight:700;font-size:1rem;margin-bottom:6px;'>"
                f"💡 AI Pricing Strategy</div>"
                f"<div style='color:#e8e8e8;font-size:0.9rem;line-height:1.6;'>"
                f"{gen['pricing_strategy']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # ── Suggested Price + Market Comps ─────────────────────────────────────
        pc1, pc2, pc3, pc4 = st.columns(4)
        pc1.metric("🎯 Suggested List Price", f"${gen['suggested_price']:.2f}" if gen['suggested_price'] else "—")
        pc2.metric("📦 eBay Market Avg",     f"${gen['ebay_avg_price']:.2f}" if gen['ebay_avg_price'] else "—")
        pc3.metric("🏷️ Mercari Market Avg",  f"${gen['mercari_avg_price']:.2f}" if gen['mercari_avg_price'] else "—")
        if gen['suggested_price'] > 0 and gen.get("cogs", 0) > 0:
            ebay_fee = round(gen['suggested_price'] * EBAY_FEE_RATE + EBAY_FEE_FLAT, 2)
            est_profit = round(gen['suggested_price'] - ebay_fee - gen['cogs'], 2)
            pc4.metric("💵 Est. Net Profit", f"${est_profit:.2f}", delta=f"{round(est_profit / gen['cogs'] * 100, 1)}% ROI" if gen['cogs'] > 0 else None)

        st.markdown("---")

        # ── eBay Title ─────────────────────────────────────────────────────────
        ebay_title = gen.get("ebay_title", "")
        st.markdown("#### 📦 eBay Title")
        char_count  = len(ebay_title)
        char_color  = "#21c354" if char_count <= 80 else "#ff4b4b"
        st.markdown(
            f"<div style='background:#12151c;border:1px solid #1e2330;border-radius:8px;padding:16px;'>"
            f"<div style='font-size:1.05rem;font-weight:700;color:#fff;margin-bottom:8px;'>{ebay_title}</div>"
            f"<div style='color:{char_color};font-size:0.8rem;'>{char_count}/80 characters</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        title_edit = st.text_input(
            "Edit title if needed",
            value=ebay_title,
            max_chars=80,
            key="ebay_title_edit",
            label_visibility="collapsed",
        )
        if title_edit != ebay_title:
            st.session_state["last_generated"]["ebay_title"] = title_edit
        st.code(title_edit or ebay_title, language=None)
        st.caption("👆 Click the copy icon on the code block above to copy the title")

        st.markdown("---")

        # ── eBay Description ───────────────────────────────────────────────────
        st.markdown("#### 📝 eBay Description")
        ebay_desc = gen.get("ebay_description", "")
        with st.expander("📄 View Full eBay Description", expanded=True):
            st.markdown(ebay_desc)
            st.code(ebay_desc, language=None)
            st.caption("👆 Click copy icon above to copy the full description")

        st.markdown("---")

        # ── Mercari Description ────────────────────────────────────────────────
        if target_platform_val := gen.get("target_platform", "Both"):
            if "Mercari" in target_platform_val or "Both" in target_platform_val:
                st.markdown("#### 🏷️ Mercari Description")
                mercari_desc = gen.get("mercari_description", "")
                with st.expander("📄 View Full Mercari Description", expanded=True):
                    st.markdown(mercari_desc)
                    st.code(mercari_desc, language=None)
                    st.caption("👆 Click copy icon above to copy the Mercari description")
                st.markdown("---")

        # ── Keywords ──────────────────────────────────────────────────────────
        if gen.get("keywords"):
            st.markdown("#### 🔑 SEO Keywords")
            keywords_str = gen["keywords"]
            st.markdown(
                f"<div style='background:#12151c;border:1px solid #1e2330;border-radius:8px;"
                f"padding:12px 16px;font-size:0.85rem;color:#FFAB76;'>"
                f"{keywords_str}</div>",
                unsafe_allow_html=True,
            )
            st.caption(
                "Use these in your eBay description and item specifics. "
                "eBay's algorithm picks up on keywords in the description."
            )
            st.markdown("---")

        # ── Save draft ─────────────────────────────────────────────────────────
        save_col, clear_col = st.columns(2)
        with save_col:
            if st.button("💾 Save as Draft", type="primary", use_container_width=True, key="save_draft_btn"):
                _save_draft(gen)
                st.success(
                    f"✅ Draft saved for **{gen['shoe_name']}**! "
                    "View it in the **📋 Saved Drafts** tab."
                )
        with clear_col:
            if st.button("🔄 Generate New Listing", use_container_width=True, key="clear_gen_btn"):
                st.session_state.pop("last_generated", None)
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — SAVED DRAFTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_drafts:
    st.subheader("📋 Saved Listing Drafts")

    drafts_df = _load_drafts()

    if drafts_df.empty:
        st.info(
            "No saved drafts yet. Generate a listing in the **✨ Generate Listing** tab, "
            "then click **Save as Draft** to store it here."
        )
    else:
        # ── Stats row ──────────────────────────────────────────────────────────
        dk1, dk2, dk3 = st.columns(3)
        dk1.metric("📋 Total Drafts", len(drafts_df))
        active_count = len(drafts_df[drafts_df.get("status", "draft") == "active"] if "status" in drafts_df.columns else drafts_df)
        dk2.metric("✅ Published",
                   len(drafts_df[drafts_df["status"] == "published"]) if "status" in drafts_df.columns else 0)
        dk3.metric("📝 Draft",
                   len(drafts_df[drafts_df["status"] == "draft"]) if "status" in drafts_df.columns else len(drafts_df))

        st.markdown("---")

        # ── Draft cards ────────────────────────────────────────────────────────
        for _, draft in drafts_df.iterrows():
            draft_id = int(draft["id"])
            d_name   = draft.get("shoe_name", "")
            d_size   = draft.get("size", "")
            d_cond   = draft.get("condition", "")
            d_status = draft.get("status", "draft")
            d_date   = str(draft.get("created_at", ""))[:10]
            d_sugg   = float(draft.get("suggested_price", 0) or 0)
            d_ebay_t = draft.get("ebay_title", "")

            status_icon = {"draft": "📝", "published": "✅", "sold": "🏁"}.get(d_status, "📝")

            with st.expander(
                f"{status_icon} **{d_name}** Sz {d_size} — "
                f"Suggested: ${d_sugg:.2f} | {d_date}",
                expanded=False,
            ):
                col_info, col_actions = st.columns([3, 1])

                with col_info:
                    st.caption(f"Condition: {d_cond} | SKU: {draft.get('sku', '—')}")
                    if d_ebay_t:
                        st.markdown(f"**eBay Title:** `{d_ebay_t}`")
                    if draft.get("pricing_strategy"):
                        st.info(f"💡 {draft['pricing_strategy']}")

                with col_actions:
                    status_options = ["draft", "published", "sold"]
                    new_status = st.selectbox(
                        "Status",
                        status_options,
                        index=status_options.index(d_status) if d_status in status_options else 0,
                        key=f"draft_status_{draft_id}",
                    )
                    if new_status != d_status:
                        if st.button("Save Status", key=f"save_status_{draft_id}"):
                            _update_draft_status(draft_id, new_status)
                            st.rerun()

                    if st.button("🗑️ Delete", key=f"del_draft_{draft_id}", use_container_width=True):
                        _delete_draft(draft_id)
                        st.success("Deleted.")
                        st.rerun()

                # Full content
                tabs_draft = st.tabs(["📦 eBay Title", "📝 eBay Description", "🏷️ Mercari Description"])
                with tabs_draft[0]:
                    if d_ebay_t:
                        st.code(d_ebay_t, language=None)
                    else:
                        st.caption("No eBay title saved.")

                with tabs_draft[1]:
                    ebay_desc = draft.get("ebay_description", "")
                    if ebay_desc:
                        st.code(ebay_desc, language=None)
                    else:
                        st.caption("No eBay description saved.")

                with tabs_draft[2]:
                    merc_desc = draft.get("mercari_description", "")
                    if merc_desc:
                        st.code(merc_desc, language=None)
                    else:
                        st.caption("No Mercari description saved.")

                # Market data
                if draft.get("ebay_avg_price") or draft.get("mercari_avg_price"):
                    st.markdown("---")
                    mc1, mc2, mc3 = st.columns(3)
                    mc1.metric("Suggested Price", f"${d_sugg:.2f}" if d_sugg else "—")
                    mc2.metric("eBay Avg (at time)", f"${float(draft.get('ebay_avg_price', 0)):.2f}")
                    mc3.metric("Mercari Avg (at time)", f"${float(draft.get('mercari_avg_price', 0)):.2f}")

                if draft.get("keywords"):
                    st.markdown(f"**Keywords:** {draft['keywords']}")

        st.markdown("---")

        # ── Export drafts ──────────────────────────────────────────────────────
        csv_data = drafts_df[["shoe_name", "size", "condition", "sku", "suggested_price",
                               "ebay_title", "status", "created_at"]].to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Export Drafts as CSV",
            data=csv_data,
            file_name=f"soleops_listing_drafts_{date.today()}.csv",
            mime="text/csv",
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — LISTING TIPS
# ══════════════════════════════════════════════════════════════════════════════
with tab_tips:
    st.subheader("💡 Listing Best Practices")

    st.markdown("""
### 📦 eBay Listing Tips

**Title (80 chars max):**
- Start with Brand + Model (e.g., "Nike Air Jordan 4 Retro")
- Include colorway name AND color codes (buyers search both)
- Add size: "Size 10" or "Men's 10"
- Include condition: "Deadstock DS" or "VNDS"
- Skip filler words: "🔥 RARE", "L@@K", "WOW" — they hurt search ranking
- ✅ Good: `Nike Air Jordan 4 Retro Red Thunder CT8527-016 Size 10 Deadstock DS`
- ❌ Bad: `🔥 RARE Jordan 4 SIZE 10 MUST SEE🔥`

**Description:**
- Be brutally honest about condition — photos and description should match perfectly
- Include ALL measurements or just confirm "true to size"
- List EXACTLY what's included: box (OG/replacement), insoles, extra laces
- Add a buyer protection statement: "I carefully pack all orders with bubble wrap"
- Use keywords naturally — eBay's algorithm reads descriptions

**Pricing:**
- List 5-10% below current lowest comp for fast sale
- Use **Free Shipping** on shoes — buyers filter for it (build it into price)
- Set 30-day returns accepted to boost search visibility
- Auction works well for hyped/limited pairs (starts at $0.99 drives bidding war)
    """)

    st.markdown("---")

    st.markdown("""
### 🏷️ Mercari Listing Tips

**Tone:**
- Mercari buyers are deal hunters — sound friendly and approachable
- Be transparent: "Wore these once to church 😂 — like new condition"
- Include size chart if you can: "These fit true to size, I'm an 11 and size 10 fit perfect"
- Mention you accept offers: "Open to offers! Serious buyers only 🙏"

**Pricing:**
- List slightly higher than eBay (Mercari buyers expect to negotiate)
- Use the "Offer" feature — many buyers won't buy unless they can negotiate
- Mercari Smart Pricing can help but can drop price too fast — use with caution

**Photos (applies to both):**
- Always shoot on a plain white or grey background
- 5-7 photos minimum: pair together, each shoe solo, sole (bottom), box label, any defects
- Natural light or a lightbox — avoid yellow/orange indoor lighting
- Defects: photograph EVERYTHING even if minor. Buyers who know what they're getting never complain.
    """)

    st.markdown("---")

    st.markdown("""
### 💰 Fee Reference (Quick Look)

| Platform | Fee Rate | Flat Fee | Net on $200 sale |
|----------|----------|----------|-----------------|
| eBay | 12.9% | $0.30 | $174.50 |
| Mercari | 10% | $0.30 | $179.70 |
| StockX | 11.5% | None | $177.00 |
| GOAT | 9.5% | $5.00 | $176.00 |
| Poshmark | 20% | None | $160.00 |

> **Takeaway:** Mercari wins on most shoes. eBay wins on high-ticket/rare pairs where buyers want protection.
    """)

    st.markdown("---")

    st.markdown("""
### ⚡ Quick Wins for More Sales

1. **Same-day or next-day shipping** — set it and stick to it. Top-rated seller status unlocks higher search ranking.
2. **Bulk discounts** — if someone buys 2+ pairs, waive shipping. Mercari makes this easy with bundle offers.
3. **Cross-list everything** — list on eBay AND Mercari. The first sale wins, cancel the other. More eyeballs = faster sales.
4. **Repost stale listings** — delete and relist after 14-21 days. Fresh listings get more views.
5. **Reply fast** — eBay and Mercari both boost sellers who respond to messages within 1 hour.
    """)
