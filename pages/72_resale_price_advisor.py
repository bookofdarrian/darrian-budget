"""
Resale Price Advisor — Page 72
Upload an item photo + optional details → AI identifies the product →
searches eBay & Mercari for comps → recommends optimal listing price,
listing type (BIN vs Auction), and shipping strategy.
"""
import streamlit as st
import base64
import json
import re
import time
from datetime import datetime
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(
    page_title="💰 Resale Price Advisor — Peach State Savings",
    page_icon="🍑",
    layout="wide",
    initial_sidebar_state="auto",
)
init_db()
inject_css()
require_login()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                          label="Overview",            icon="📊")
st.sidebar.page_link("pages/22_todo.py",                label="✅ Todo",             icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",   label="🎬 Creator",          icon="🎬")
st.sidebar.page_link("pages/25_notes.py",               label="📝 Notes",            icon="📝")
st.sidebar.page_link("pages/26_media_library.py",       label="🎵 Media Library",    icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",  label="Personal Assistant",  icon="🤖")
render_sidebar_user_widget()

# ── Constants ─────────────────────────────────────────────────────────────────
CONDITIONS = ["New with tags", "New without tags", "Like New", "Very Good",
              "Good", "Acceptable", "For parts / not working"]

EBAY_FEE_RATE  = 0.1325   # 13.25% final value fee (most categories)
MERCARI_FEE    = 0.10     # 10% selling fee
DEPOP_FEE      = 0.10     # 10% selling fee
PAYPAL_FEE     = 0.029    # 2.9% + $0.30 (approximation for eBay managed payments)

PLATFORMS = ["eBay", "Mercari", "Depop", "StockX", "GOAT"]
LISTING_TYPES = ["Buy It Now (BIN)", "Auction / Bid", "Both — start with auction, BIN fallback"]

SHIPPING_OPTIONS = [
    "Buyer pays actual shipping",
    "Flat rate — $5 (USPS First Class)",
    "Flat rate — $8 (USPS Priority Small Box)",
    "Flat rate — $10 (USPS Priority Medium Box)",
    "Free shipping (baked into price)",
]


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _ensure_tables():
    conn = get_conn()
    if USE_POSTGRES:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS resale_price_lookups (
                id SERIAL PRIMARY KEY,
                product_name TEXT,
                brand TEXT,
                condition TEXT,
                image_provided BOOLEAN DEFAULT FALSE,
                recommended_price REAL,
                listing_type TEXT,
                shipping_recommendation TEXT,
                platform TEXT,
                ai_analysis TEXT,
                ebay_comps TEXT,
                mercari_comps TEXT,
                created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
            )
        """)
    else:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS resale_price_lookups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT,
                brand TEXT,
                condition TEXT,
                image_provided INTEGER DEFAULT 0,
                recommended_price REAL,
                listing_type TEXT,
                shipping_recommendation TEXT,
                platform TEXT,
                ai_analysis TEXT,
                ebay_comps TEXT,
                mercari_comps TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
    conn.commit()
    conn.close()


def _save_lookup(data: dict):
    conn = get_conn()
    ph = "?" if not USE_POSTGRES else "%s"
    db_exec(conn, f"""
        INSERT INTO resale_price_lookups
            (product_name, brand, condition, image_provided, recommended_price,
             listing_type, shipping_recommendation, platform, ai_analysis,
             ebay_comps, mercari_comps)
        VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})
    """, (
        data.get("product_name", ""),
        data.get("brand", ""),
        data.get("condition", ""),
        1 if data.get("image_provided") else 0,
        data.get("recommended_price"),
        data.get("listing_type", ""),
        data.get("shipping_recommendation", ""),
        data.get("platform", ""),
        data.get("ai_analysis", ""),
        json.dumps(data.get("ebay_comps", [])),
        json.dumps(data.get("mercari_comps", [])),
    ))
    conn.commit()
    conn.close()


def _load_history(limit: int = 10) -> list:
    conn = get_conn()
    ph = "?" if not USE_POSTGRES else "%s"
    c = db_exec(conn, f"SELECT * FROM resale_price_lookups ORDER BY created_at DESC LIMIT {ph}", (limit,))
    rows = c.fetchall()
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        results = [dict(zip(cols, r)) for r in rows]
    else:
        results = [dict(r) for r in rows]
    conn.close()
    return results


# ── Market search helpers ──────────────────────────────────────────────────────

def _search_ebay(query: str, max_results: int = 10) -> list:
    """Search eBay completed/sold listings for price comps via public API."""
    try:
        import requests
        # Use eBay's Finding API (requires app ID) or fall back to scraping
        app_id = get_setting("ebay_app_id", "")
        if app_id:
            url = "https://svcs.ebay.com/services/search/FindingService/v1"
            params = {
                "OPERATION-NAME": "findCompletedItems",
                "SERVICE-VERSION": "1.0.0",
                "SECURITY-APPNAME": app_id,
                "RESPONSE-DATA-FORMAT": "JSON",
                "keywords": query,
                "paginationInput.entriesPerPage": max_results,
                "sortOrder": "EndTimeSoonest",
            }
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                items = (data.get("findCompletedItemsResponse", [{}])[0]
                             .get("searchResult", [{}])[0]
                             .get("item", []))
                results = []
                for item in items:
                    sold_price = float(item.get("sellingStatus", [{}])[0]
                                           .get("convertedCurrentPrice", [{}])[0]
                                           .get("__value__", 0))
                    title = item.get("title", [query])[0]
                    condition = item.get("condition", [{}])[0].get("conditionDisplayName", ["Unknown"])[0]
                    sold = item.get("sellingStatus", [{}])[0].get("sellingState", ["Unknown"])[0]
                    results.append({
                        "title": title,
                        "price": sold_price,
                        "condition": condition,
                        "sold": "Sold" in sold,
                        "platform": "eBay",
                    })
                return results
        # Fallback: scrape eBay sold listings (public)
        return _scrape_ebay_sold(query, max_results)
    except Exception:
        return _scrape_ebay_sold(query, max_results)


def _scrape_ebay_sold(query: str, max_results: int = 10) -> list:
    """Fallback: scrape eBay sold listings."""
    try:
        import requests
        from html.parser import HTMLParser

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
        }
        q = query.replace(" ", "+")
        url = f"https://www.ebay.com/sch/i.html?_nkw={q}&LH_Sold=1&LH_Complete=1&_sop=13"
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code != 200:
            return []

        # Simple extraction with regex — no BS4 dependency
        text = resp.text
        prices = re.findall(r'\$([0-9,]+\.[0-9]{2})', text)
        titles = re.findall(r'class="s-item__title[^"]*"[^>]*>([^<]{10,120})<', text)

        results = []
        for i, price_str in enumerate(prices[:max_results]):
            price = float(price_str.replace(",", ""))
            if price < 1.0:
                continue
            title = titles[i] if i < len(titles) else query
            results.append({
                "title": title.strip(),
                "price": price,
                "condition": "Unknown",
                "sold": True,
                "platform": "eBay",
            })
        return results
    except Exception:
        return []


def _search_mercari(query: str, max_results: int = 10) -> list:
    """Search Mercari sold listings via public API."""
    try:
        import requests
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            ),
            "X-Platform": "web",
        }
        url = "https://api.mercari.com/v2/entities:search"
        payload = {
            "pageSize": max_results,
            "pageToken": "",
            "searchCondition": {
                "keyword": query,
                "status": ["STATUS_SOLD_OUT"],
                "sortBy": "SORT_SCORE",
                "order": "ORDER_DESC",
            },
            "userId": "",
            "fromPage": "search",
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            results = []
            for item in items[:max_results]:
                results.append({
                    "title": item.get("name", query),
                    "price": float(item.get("price", 0)),
                    "condition": item.get("itemCondition", "Unknown"),
                    "sold": True,
                    "platform": "Mercari",
                })
            return results
    except Exception:
        pass
    return []


# ── AI helpers ────────────────────────────────────────────────────────────────

def _identify_product_with_ai(image_b64: str, mime_type: str,
                               brand: str, model_hint: str,
                               condition: str, size: str,
                               weight: str, extra_notes: str) -> dict:
    """Use Claude Vision to identify the product and return structured info."""
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return {"error": "No Anthropic API key set. Go to Settings to add it."}
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        context_parts = []
        if brand:
            context_parts.append(f"Brand: {brand}")
        if model_hint:
            context_parts.append(f"Model/Name: {model_hint}")
        if condition:
            context_parts.append(f"Condition: {condition}")
        if size:
            context_parts.append(f"Size: {size}")
        if weight:
            context_parts.append(f"Weight: {weight}")
        if extra_notes:
            context_parts.append(f"Additional details: {extra_notes}")

        context_str = "\n".join(context_parts) if context_parts else "No additional details provided."

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            f"You are a resale marketplace expert. Analyze this product image and the details below, "
                            f"then identify the product as specifically as possible.\n\n"
                            f"User-provided details:\n{context_str}\n\n"
                            f"Return ONLY a valid JSON object with these fields:\n"
                            f'{{"product_name": "Full product name (brand + model + variant if detectable)",\n'
                            f'"brand": "Brand name",\n'
                            f'"category": "Category (e.g. Sneakers, Electronics, Clothing, etc.)",\n'
                            f'"search_query": "Best eBay/Mercari search query to find sold comps (concise, no filler words)",\n'
                            f'"key_identifiers": "Any serial numbers, colorways, sizes, or model numbers visible",\n'
                            f'"condition_notes": "Any condition observations from the photo",\n'
                            f'"confidence": "high|medium|low"}}\n\n'
                            f"Do not include any explanation — just the JSON object."
                        ),
                    },
                ],
            }
        ]

        resp = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=512,
            messages=messages,
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        return {"error": str(e)}


def _generate_pricing_recommendation(product_info: dict, ebay_comps: list,
                                     mercari_comps: list, condition: str,
                                     user_purchase_price: float,
                                     target_platforms: list) -> dict:
    """Use Claude to synthesize market data and generate a full pricing recommendation."""
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return {"error": "No Anthropic API key set."}
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        ebay_prices  = [c["price"] for c in ebay_comps  if c.get("price", 0) > 0]
        merc_prices  = [c["price"] for c in mercari_comps if c.get("price", 0) > 0]

        ebay_avg  = sum(ebay_prices) / len(ebay_prices)   if ebay_prices  else 0
        merc_avg  = sum(merc_prices) / len(merc_prices)   if merc_prices  else 0
        ebay_low  = min(ebay_prices)  if ebay_prices  else 0
        ebay_high = max(ebay_prices)  if ebay_prices  else 0
        merc_low  = min(merc_prices)  if merc_prices  else 0
        merc_high = max(merc_prices)  if merc_prices  else 0

        prompt = f"""You are an expert resale marketplace analyst. Given the following data, provide a comprehensive pricing and listing strategy.

PRODUCT: {product_info.get('product_name', 'Unknown')}
BRAND: {product_info.get('brand', 'Unknown')}
CATEGORY: {product_info.get('category', 'Unknown')}
CONDITION: {condition}
USER PURCHASE PRICE: ${user_purchase_price:.2f} (0 = unknown)
TARGET PLATFORMS: {', '.join(target_platforms)}

MARKET COMPS (SOLD LISTINGS):
eBay sold — avg: ${ebay_avg:.2f} | low: ${ebay_low:.2f} | high: ${ebay_high:.2f} | n={len(ebay_prices)}
Mercari sold — avg: ${merc_avg:.2f} | low: ${merc_low:.2f} | high: ${merc_high:.2f} | n={len(merc_prices)}

PLATFORM FEES:
- eBay: ~13.25% final value fee
- Mercari: 10%
- Depop: 10%

Return ONLY a valid JSON object with these fields:
{{
  "recommended_price": <float — the price to start listing at, before fees>,
  "price_range_low": <float — acceptable low end>,
  "price_range_high": <float — ceiling price>,
  "listing_type": "Buy It Now" | "Auction" | "Auction with BIN",
  "auction_start_price": <float | null — if auction recommended>,
  "best_platform": "<platform name>",
  "platform_ranking": ["platform1", "platform2"],
  "shipping_recommendation": "<specific shipping recommendation>",
  "buyer_pays_shipping": <true | false>,
  "estimated_net_after_fees": <float — estimated net profit after all fees, per platform>,
  "roi_percent": <float | null — return on investment if purchase price known>,
  "listing_tips": ["tip1", "tip2", "tip3"],
  "urgency": "sell now" | "hold" | "either",
  "urgency_reason": "<brief explanation>",
  "market_summary": "<2-3 sentence market overview>"
}}

Do not include any explanation — just the JSON object."""

        resp = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        return {"error": str(e)}


# ── Init ──────────────────────────────────────────────────────────────────────
_ensure_tables()

# ── Page header ───────────────────────────────────────────────────────────────
st.title("💰 Resale Price Advisor")
st.caption(
    "Upload a photo of any item → AI identifies it → searches eBay & Mercari sold comps → "
    "recommends the best price, listing type, and shipping strategy."
)

# ══════════════════════════════════════════════════════════════════════════════
# ── MAIN TABS ─────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
tab_analyze, tab_history = st.tabs(["🔍 Analyze Item", "📋 History"])

# ──────────────────────────────────────────────────────────────────────────────
# TAB 1 — ANALYZE
# ──────────────────────────────────────────────────────────────────────────────
with tab_analyze:
    col_left, col_right = st.columns([1, 1], gap="large")

    # ── LEFT — Inputs ─────────────────────────────────────────────────────────
    with col_left:
        st.markdown("### 📸 Item Photo")
        uploaded_image = st.file_uploader(
            "Upload a clear photo of the item",
            type=["jpg", "jpeg", "png", "webp"],
            key="rpa_image_upload",
            help="Clearer photos = better AI identification. Multiple angles work best.",
        )
        if uploaded_image:
            st.image(uploaded_image, caption="Uploaded image", use_container_width=True)

        st.markdown("### 📋 Item Details *(optional but improves accuracy)*")

        c1, c2 = st.columns(2)
        brand       = c1.text_input("Brand", placeholder="Nike, Apple, Levi's...", key="rpa_brand")
        model_hint  = c2.text_input("Model / Name", placeholder="Air Force 1, iPhone 13...", key="rpa_model")

        condition   = st.selectbox("Condition", CONDITIONS, index=2, key="rpa_condition")

        c3, c4 = st.columns(2)
        size        = c3.text_input("Size (if apparel/shoes)", placeholder="10.5, XL...", key="rpa_size")
        weight      = c4.text_input("Weight (if shipping matters)", placeholder="2 lbs, 500g...", key="rpa_weight")

        purchase_price = st.number_input(
            "Your purchase price ($) — used to calculate ROI",
            min_value=0.0, value=0.0, step=1.0, format="%.2f", key="rpa_cost"
        )

        extra_notes = st.text_area(
            "Any other details",
            placeholder="Limited edition, missing box, original receipt included, minor scratch on left side...",
            height=80, key="rpa_notes"
        )

        target_platforms = st.multiselect(
            "Where are you planning to sell?",
            PLATFORMS,
            default=["eBay", "Mercari"],
            key="rpa_platforms",
        )

        analyze_btn = st.button(
            "🔍 Analyze & Get Price Recommendation",
            type="primary",
            use_container_width=True,
            key="rpa_analyze_btn",
        )

    # ── RIGHT — Results ───────────────────────────────────────────────────────
    with col_right:
        st.markdown("### 📊 Price Recommendation")

        if analyze_btn:
            if not uploaded_image and not brand and not model_hint:
                st.error("❌ Please upload a photo or enter at least the brand/model to continue.")
            else:
                # ── Step 1: Identify product ──────────────────────────────────
                with st.status("🤖 Identifying product with Claude Vision...", expanded=True) as status:
                    if uploaded_image:
                        uploaded_image.seek(0)
                        img_bytes  = uploaded_image.read()
                        img_b64    = base64.b64encode(img_bytes).decode("utf-8")
                        mime_map   = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                                      "png": "image/png", "webp": "image/webp"}
                        ext        = uploaded_image.name.rsplit(".", 1)[-1].lower()
                        mime_type  = mime_map.get(ext, "image/jpeg")

                        st.write("📸 Analyzing image...")
                        product_info = _identify_product_with_ai(
                            img_b64, mime_type, brand, model_hint,
                            condition, size, weight, extra_notes
                        )
                    else:
                        # No image — build from text inputs
                        product_info = {
                            "product_name": f"{brand} {model_hint}".strip(),
                            "brand": brand,
                            "category": "General",
                            "search_query": f"{brand} {model_hint} {condition}".strip(),
                            "key_identifiers": size or "",
                            "condition_notes": extra_notes or "",
                            "confidence": "medium",
                        }

                    if "error" in product_info:
                        st.error(f"❌ {product_info['error']}")
                        status.update(label="❌ Failed", state="error")
                        st.stop()

                    st.write(f"✅ Identified: **{product_info.get('product_name', 'Unknown')}**")
                    search_query = product_info.get("search_query", f"{brand} {model_hint}".strip())

                    # ── Step 2: Search market comps ───────────────────────────
                    st.write(f"🔎 Searching eBay sold listings for: `{search_query}`...")
                    ebay_comps = _search_ebay(search_query, max_results=12)
                    st.write(f"   → Found {len(ebay_comps)} eBay comp(s)")

                    st.write(f"🔎 Searching Mercari sold listings...")
                    mercari_comps = _search_mercari(search_query, max_results=10)
                    st.write(f"   → Found {len(mercari_comps)} Mercari comp(s)")

                    # ── Step 3: AI pricing recommendation ─────────────────────
                    st.write("💡 Generating pricing recommendation...")
                    recommendation = _generate_pricing_recommendation(
                        product_info, ebay_comps, mercari_comps,
                        condition, purchase_price, target_platforms
                    )

                    if "error" in recommendation:
                        st.error(f"❌ Pricing error: {recommendation['error']}")
                        status.update(label="❌ Failed", state="error")
                        st.stop()

                    status.update(label="✅ Analysis complete!", state="complete", expanded=False)

                # ── Save to history ───────────────────────────────────────────
                _save_lookup({
                    "product_name": product_info.get("product_name", ""),
                    "brand": product_info.get("brand", brand),
                    "condition": condition,
                    "image_provided": uploaded_image is not None,
                    "recommended_price": recommendation.get("recommended_price"),
                    "listing_type": recommendation.get("listing_type", ""),
                    "shipping_recommendation": recommendation.get("shipping_recommendation", ""),
                    "platform": recommendation.get("best_platform", ""),
                    "ai_analysis": json.dumps(recommendation),
                    "ebay_comps": ebay_comps,
                    "mercari_comps": mercari_comps,
                })

                # Store in session state for display
                st.session_state["rpa_product_info"]   = product_info
                st.session_state["rpa_recommendation"]  = recommendation
                st.session_state["rpa_ebay_comps"]      = ebay_comps
                st.session_state["rpa_mercari_comps"]   = mercari_comps

        # ── Display results from session state ────────────────────────────────
        product_info  = st.session_state.get("rpa_product_info")
        recommendation = st.session_state.get("rpa_recommendation")
        ebay_comps    = st.session_state.get("rpa_ebay_comps", [])
        mercari_comps = st.session_state.get("rpa_mercari_comps", [])

        if product_info and recommendation:
            # Product identification card
            with st.container(border=True):
                st.markdown(f"#### 🏷️ {product_info.get('product_name', 'Product')}")
                id_c1, id_c2 = st.columns(2)
                id_c1.caption(f"**Brand:** {product_info.get('brand', '—')}")
                id_c2.caption(f"**Category:** {product_info.get('category', '—')}")
                if product_info.get("key_identifiers"):
                    st.caption(f"**Identifiers:** {product_info['key_identifiers']}")
                if product_info.get("condition_notes"):
                    st.caption(f"**Condition notes:** {product_info['condition_notes']}")
                conf = product_info.get("confidence", "medium")
                conf_color = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(conf, "🟡")
                st.caption(f"{conf_color} Identification confidence: **{conf.title()}**")

            st.markdown("---")

            # ── Primary recommendation ────────────────────────────────────────
            rec_price = recommendation.get("recommended_price", 0)
            low_price = recommendation.get("price_range_low", 0)
            high_price = recommendation.get("price_range_high", 0)
            net_after  = recommendation.get("estimated_net_after_fees", 0)

            p1, p2, p3 = st.columns(3)
            p1.metric("💰 Recommended Price", f"${rec_price:.2f}")
            p2.metric("📉 Range", f"${low_price:.2f} — ${high_price:.2f}")
            if net_after:
                p3.metric("🟢 Est. Net (after fees)", f"${net_after:.2f}")
            elif recommendation.get("roi_percent") is not None:
                roi = recommendation["roi_percent"]
                p3.metric("📈 ROI", f"{roi:.1f}%", delta=f"{roi:.1f}%")

            st.markdown("---")

            # ── Listing strategy ──────────────────────────────────────────────
            st.markdown("#### 📋 Listing Strategy")
            ls1, ls2 = st.columns(2)

            with ls1:
                listing_type = recommendation.get("listing_type", "Buy It Now")
                st.markdown(f"**Listing Type:** `{listing_type}`")
                if recommendation.get("auction_start_price"):
                    st.markdown(f"**Auction Start:** `${recommendation['auction_start_price']:.2f}`")
                best_platform = recommendation.get("best_platform", "")
                st.markdown(f"**Best Platform:** `{best_platform}`")
                platforms_ranked = recommendation.get("platform_ranking", [])
                if platforms_ranked:
                    st.caption("Ranked: " + " → ".join(platforms_ranked))

            with ls2:
                shipping_rec  = recommendation.get("shipping_recommendation", "")
                buyer_pays    = recommendation.get("buyer_pays_shipping", True)
                st.markdown(f"**Shipping:** {shipping_rec}")
                ship_label = "Buyer pays shipping" if buyer_pays else "Offer free shipping (baked into price)"
                st.markdown(f"**Approach:** `{ship_label}`")

            st.markdown("---")

            # ── Urgency ───────────────────────────────────────────────────────
            urgency     = recommendation.get("urgency", "either")
            urge_reason = recommendation.get("urgency_reason", "")
            urgency_colors = {"sell now": "🔴", "hold": "🟢", "either": "🟡"}
            st.markdown(
                f"**{urgency_colors.get(urgency, '🟡')} Market Timing:** `{urgency.title()}`  \n"
                f"_{urge_reason}_"
            )

            # ── Market summary ────────────────────────────────────────────────
            market_summary = recommendation.get("market_summary", "")
            if market_summary:
                st.info(f"📈 **Market Summary:** {market_summary}")

            # ── Listing tips ──────────────────────────────────────────────────
            tips = recommendation.get("listing_tips", [])
            if tips:
                st.markdown("#### 💡 Listing Tips")
                for tip in tips:
                    st.markdown(f"- {tip}")

            st.markdown("---")

            # ── Market comps ──────────────────────────────────────────────────
            with st.expander(f"📦 eBay Sold Comps ({len(ebay_comps)} results)"):
                if ebay_comps:
                    for comp in ebay_comps[:10]:
                        cc1, cc2 = st.columns([5, 1])
                        cc1.caption(comp.get("title", "")[:80])
                        cc2.metric("", f"${comp.get('price', 0):.2f}", label_visibility="collapsed")
                else:
                    st.info("No eBay comps found. Search query may need refinement.")

            with st.expander(f"🛍️ Mercari Sold Comps ({len(mercari_comps)} results)"):
                if mercari_comps:
                    for comp in mercari_comps[:10]:
                        cc1, cc2 = st.columns([5, 1])
                        cc1.caption(comp.get("title", "")[:80])
                        cc2.metric("", f"${comp.get('price', 0):.2f}", label_visibility="collapsed")
                else:
                    st.info("No Mercari comps found. Market may be thin on this platform.")

        elif not analyze_btn:
            st.info(
                "👈 Upload a photo and click **Analyze & Get Price Recommendation** to get started.\n\n"
                "**What you'll get:**\n"
                "- ✅ AI product identification from your photo\n"
                "- ✅ Real sold-listing comps from eBay & Mercari\n"
                "- ✅ Recommended starting price\n"
                "- ✅ Auction vs. Buy It Now recommendation\n"
                "- ✅ Shipping strategy (who pays, what method)\n"
                "- ✅ Platform ranking (where you'll make the most)\n"
                "- ✅ ROI calculation if you enter your cost"
            )

# ──────────────────────────────────────────────────────────────────────────────
# TAB 2 — HISTORY
# ──────────────────────────────────────────────────────────────────────────────
with tab_history:
    st.markdown("### 📋 Recent Price Lookups")
    history = _load_history(limit=20)

    if not history:
        st.info("No lookups yet. Analyze an item to see history here.")
    else:
        st.caption(f"{len(history)} recent lookup(s)")
        for row in history:
            with st.container(border=True):
                h1, h2, h3 = st.columns([3, 1, 1])
                h1.markdown(f"**{row.get('product_name', 'Unknown')}**")
                price = row.get("recommended_price")
                if price:
                    h2.metric("Rec. Price", f"${price:.2f}")
                h3.caption(f"📅 {str(row.get('created_at', ''))[:10]}")

                detail_c1, detail_c2 = st.columns(2)
                detail_c1.caption(f"Platform: {row.get('platform', '—')} | Type: {row.get('listing_type', '—')}")
                detail_c2.caption(f"Condition: {row.get('condition', '—')} | Image: {'✅' if row.get('image_provided') else '❌'}")

                if row.get("ai_analysis"):
                    with st.expander("View full analysis"):
                        try:
                            analysis = json.loads(row["ai_analysis"])
                            st.json(analysis)
                        except Exception:
                            st.text(row["ai_analysis"])


# ── Sidebar: eBay API key setup ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    with st.expander("⚙️ eBay API Key (optional)"):
        st.caption(
            "Add your eBay App ID to use the official Finding API for more accurate comps. "
            "Without it, we scrape public eBay search results (less reliable)."
        )
        current_key = get_setting("ebay_app_id", "")
        new_key = st.text_input(
            "eBay App ID",
            value=current_key,
            type="password",
            placeholder="YourApp-XXXXX-XXX...",
            key="sidebar_ebay_key",
        )
        if st.button("💾 Save eBay App ID", key="save_ebay_key"):
            set_setting("ebay_app_id", new_key.strip())
            st.success("Saved!")
