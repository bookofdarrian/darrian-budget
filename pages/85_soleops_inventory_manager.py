"""
SoleOps Inventory Manager — Page 85
=====================================
Central hub for all active sneaker inventory:
  - Full CRUD: add, edit, delete pairs
  - Color-coded aging dashboard (Fresh → Critical)
  - Mark Sold → auto-transfers to P&L dashboard
  - Analytics: COGS at risk, potential revenue, size distribution, velocity
  - Quick actions: reprice, cross-list, move to listed
"""
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, date, timedelta

from utils.db import (
    get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
)
from utils.auth import (
    require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css
)

st.set_page_config(
    page_title="SoleOps Inventory Manager — Peach State Savings",
    page_icon="👟",
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
PLATFORMS  = ["eBay", "Mercari", "StockX", "GOAT", "Poshmark", "Not Listed"]
CONDITIONS = ["Deadstock / New", "Like New", "Good", "Fair", "Poor"]
SOURCES    = [
    "Nike SNKRS", "Foot Locker", "DTLR", "Finish Line", "DSW",
    "Outlet", "eBay", "Mercari", "StockX", "GOAT", "Poshmark",
    "Facebook Marketplace", "Craigslist", "Other",
]
SIZES = [str(s) for s in [
    4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5,
    10, 10.5, 11, 11.5, 12, 12.5, 13, 14, 15
]]

EBAY_FEE_RATE    = 0.129
EBAY_FEE_FLAT    = 0.30
MERCARI_FEE_RATE = 0.10
MERCARI_FEE_FLAT = 0.30

AGING_TIERS = [
    (0,  7,  "🟢 Fresh",    "#22c55e", 0.00),
    (7,  14, "🟡 Warm",     "#eab308", 0.05),
    (14, 21, "🟠 Aging",    "#f97316", 0.10),
    (21, 30, "🔴 Stale",    "#ef4444", 0.15),
    (30, 999,"⚫ Critical", "#6b7280", 0.20),
]


# ── DB helpers ─────────────────────────────────────────────────────────────────
def _ensure_tables() -> None:
    conn = get_conn()
    if USE_POSTGRES:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id              SERIAL PRIMARY KEY,
                user_id         INTEGER NOT NULL DEFAULT 1,
                shoe_name       TEXT NOT NULL,
                brand           TEXT DEFAULT '',
                colorway        TEXT DEFAULT '',
                sku             TEXT DEFAULT '',
                size            TEXT DEFAULT '',
                condition       TEXT DEFAULT 'Deadstock / New',
                cost_basis      REAL NOT NULL DEFAULT 0,
                date_purchased  TEXT DEFAULT '',
                source          TEXT DEFAULT '',
                listed_date     TEXT DEFAULT '',
                listed_price    REAL DEFAULT 0,
                listed_platform TEXT DEFAULT '',
                target_price    REAL DEFAULT 0,
                status          TEXT DEFAULT 'inventory',
                notes           TEXT DEFAULT '',
                created_at      TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
            )
        """)
    else:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS soleops_inventory (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL DEFAULT 1,
                shoe_name       TEXT NOT NULL,
                brand           TEXT DEFAULT '',
                colorway        TEXT DEFAULT '',
                sku             TEXT DEFAULT '',
                size            TEXT DEFAULT '',
                condition       TEXT DEFAULT 'Deadstock / New',
                cost_basis      REAL NOT NULL DEFAULT 0,
                date_purchased  TEXT DEFAULT '',
                source          TEXT DEFAULT '',
                listed_date     TEXT DEFAULT '',
                listed_price    REAL DEFAULT 0,
                listed_platform TEXT DEFAULT '',
                target_price    REAL DEFAULT 0,
                status          TEXT DEFAULT 'inventory',
                notes           TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now'))
            )
        """)
    conn.commit()
    conn.close()


_ensure_tables()


# ── Utility helpers ────────────────────────────────────────────────────────────
def _days_since(date_str: str) -> int:
    if not date_str:
        return 0
    try:
        d = datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
        return max(0, (date.today() - d).days)
    except Exception:
        return 0


def _get_tier(days: int) -> dict:
    for lo, hi, label, color, drop_pct in AGING_TIERS:
        if lo <= days < hi:
            return {"label": label, "color": color, "drop_pct": drop_pct}
    return {"label": "⚫ Critical", "color": "#6b7280", "drop_pct": 0.20}


def _calc_fee(platform: str, price: float) -> float:
    p = platform.lower()
    if "ebay" in p:
        return round(price * EBAY_FEE_RATE + EBAY_FEE_FLAT, 2)
    elif "mercari" in p:
        return round(price * MERCARI_FEE_RATE + MERCARI_FEE_FLAT, 2)
    elif "stockx" in p:
        return round(price * 0.115, 2)
    elif "goat" in p:
        return round(price * 0.095 + 5.0, 2)
    elif "poshmark" in p:
        return 2.95 if price < 15 else round(price * 0.20, 2)
    return round(price * 0.12, 2)


def _calc_profit(sale_price: float, cost_basis: float, platform: str) -> float:
    if sale_price <= 0:
        return 0.0
    fee = _calc_fee(platform, sale_price)
    return round(sale_price - fee - cost_basis, 2)


# ── Data loaders ───────────────────────────────────────────────────────────────
def _load_inventory(status: str = "inventory") -> pd.DataFrame:
    conn = get_conn()
    try:
        if USE_POSTGRES:
            import psycopg2.extras
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            c.execute(
                "SELECT * FROM soleops_inventory WHERE status = %s ORDER BY created_at DESC",
                (status,)
            )
            rows = c.fetchall()
            df = pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()
        else:
            import pandas as _pd
            df = _pd.read_sql(
                "SELECT * FROM soleops_inventory WHERE status = ? ORDER BY created_at DESC",
                conn, params=(status,)
            )
    except Exception:
        df = pd.DataFrame()
    conn.close()
    if df.empty:
        df = pd.DataFrame(columns=[
            "id", "user_id", "shoe_name", "brand", "colorway", "sku",
            "size", "condition", "cost_basis", "date_purchased", "source",
            "listed_date", "listed_price", "listed_platform", "target_price",
            "status", "notes", "created_at"
        ])
    for col in ["cost_basis", "listed_price", "target_price"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def _enrich_inventory(df: pd.DataFrame) -> pd.DataFrame:
    """Add computed columns: days_held, tier, suggested_price, potential_profit."""
    if df.empty:
        return df
    df = df.copy()
    # Days held = days since purchase; if not set, use listing date or today
    def _days(row):
        d = row.get("date_purchased") or row.get("listed_date") or ""
        return _days_since(str(d))

    df["days_held"] = df.apply(_days, axis=1)
    df["tier_info"] = df["days_held"].apply(_get_tier)
    df["tier"]      = df["tier_info"].apply(lambda t: t["label"])
    df["tier_color"]= df["tier_info"].apply(lambda t: t["color"])

    # Suggested price if stale: listed_price × (1 - drop_pct)
    def _sugg(row):
        lp = row.get("listed_price", 0) or row.get("target_price", 0)
        if not lp:
            return 0.0
        drop = row["tier_info"]["drop_pct"]
        return round(lp * (1 - drop), 2)

    df["suggested_price"] = df.apply(_sugg, axis=1)

    # Potential profit at target or listed price
    def _pot_profit(row):
        price = row.get("listed_price", 0) or row.get("target_price", 0)
        plat  = row.get("listed_platform", "eBay") or "eBay"
        cost  = row.get("cost_basis", 0) or 0
        return _calc_profit(price, cost, plat)

    df["potential_profit"] = df.apply(_pot_profit, axis=1)
    df.drop(columns=["tier_info"], inplace=True)
    return df


def _add_item(data: dict) -> None:
    conn = get_conn()
    db_exec(conn, """
        INSERT INTO soleops_inventory
            (user_id, shoe_name, brand, colorway, sku, size, condition, cost_basis,
             date_purchased, source, listed_date, listed_price, listed_platform,
             target_price, status, notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        1, data["shoe_name"], data["brand"], data["colorway"], data["sku"],
        data["size"], data["condition"], data["cost_basis"],
        data["date_purchased"], data["source"],
        data["listed_date"], data["listed_price"], data["listed_platform"],
        data["target_price"], data["status"], data["notes"],
    ))
    conn.commit()
    conn.close()


def _update_item(item_id: int, field: str, value) -> None:
    conn = get_conn()
    db_exec(conn, f"UPDATE soleops_inventory SET {field} = ? WHERE id = ?", (value, item_id))
    conn.commit()
    conn.close()


def _delete_item(item_id: int) -> None:
    conn = get_conn()
    db_exec(conn, "DELETE FROM soleops_inventory WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def _mark_sold(item_id: int, sale_price: float, platform: str, sale_date: str, shipping: float) -> None:
    """Move item to 'sold' status and add entry to soleops_sales."""
    conn = get_conn()
    # Fetch original item
    c = db_exec(conn, "SELECT * FROM soleops_inventory WHERE id = ?", (item_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return
    if USE_POSTGRES:
        cols = [d[0] for d in c.description]
        item = dict(zip(cols, row))
    else:
        item = dict(row)

    fee = _calc_fee(platform, sale_price)
    net = round(sale_price - fee - item["cost_basis"] - shipping, 2)
    shoe_full = item["shoe_name"]
    if item.get("size"):
        shoe_full += f" (Sz {item['size']})"

    # Insert into soleops_sales (for P&L dashboard)
    db_exec(conn, """
        INSERT INTO soleops_sales
            (shoe_name, sku, cogs, sale_price, platform, sale_date,
             shipping_cost, platform_fee, net_profit, notes)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (
        shoe_full, item.get("sku", ""),
        item["cost_basis"], sale_price, platform, sale_date,
        shipping, fee, net,
        f"Auto-imported from Inventory #{item_id}",
    ))

    # Update inventory status
    db_exec(conn, "UPDATE soleops_inventory SET status = 'sold' WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


# ── Page header ────────────────────────────────────────────────────────────────
st.title("📦 SoleOps Inventory Manager")
st.caption(
    "Your central hub for all active sneaker inventory. "
    "Track every pair — buy price, days held, listing status, and profit potential."
)
st.markdown("---")

# ── Load & enrich data ─────────────────────────────────────────────────────────
inv_df  = _enrich_inventory(_load_inventory("inventory"))
sold_df = _load_inventory("sold")

# ── Top KPIs ───────────────────────────────────────────────────────────────────
total_pairs     = len(inv_df)
total_cogs      = inv_df["cost_basis"].sum() if not inv_df.empty else 0.0
total_pot_rev   = inv_df["listed_price"].sum() + inv_df[inv_df["listed_price"] == 0]["target_price"].sum() if not inv_df.empty else 0.0
total_pot_profit= inv_df["potential_profit"].sum() if not inv_df.empty else 0.0
stale_count     = len(inv_df[inv_df["days_held"] >= 14]) if not inv_df.empty else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("📦 Active Pairs",         total_pairs)
k2.metric("💸 Total COGS at Risk",   f"${total_cogs:,.2f}")
k3.metric("💰 Potential Revenue",    f"${total_pot_rev:,.2f}")
k4.metric("📈 Potential Net Profit", f"${total_pot_profit:,.2f}")
delta_color = "inverse" if stale_count > 0 else "normal"
k5.metric("⏰ Aging Pairs (14d+)",   stale_count, delta_color=delta_color)

st.markdown("---")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_inv, tab_add, tab_analytics, tab_sell, tab_sold = st.tabs([
    "📦 Active Inventory",
    "➕ Add Pair",
    "📊 Analytics",
    "✅ Mark Sold",
    "🏁 Sold History",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ACTIVE INVENTORY
# ══════════════════════════════════════════════════════════════════════════════
with tab_inv:
    st.subheader("📦 Active Inventory")

    if inv_df.empty:
        st.info(
            "No inventory yet! Add your first pair using the **➕ Add Pair** tab. "
            "Every pair you add will appear here with aging status and profit projections."
        )
    else:
        # ── Filters ────────────────────────────────────────────────────────────
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            filter_status = st.multiselect(
                "Listing Status",
                ["Listed", "Not Listed", "All"],
                default=["All"],
            )
        with f2:
            filter_platform = st.multiselect("Platform", PLATFORMS, default=PLATFORMS)
        with f3:
            filter_tier = st.multiselect(
                "Age Tier",
                ["🟢 Fresh", "🟡 Warm", "🟠 Aging", "🔴 Stale", "⚫ Critical"],
                default=["🟢 Fresh", "🟡 Warm", "🟠 Aging", "🔴 Stale", "⚫ Critical"],
            )
        with f4:
            sort_by = st.selectbox("Sort by", ["days_held", "cost_basis", "potential_profit", "listed_price"], index=0)

        filtered = inv_df.copy()

        if "All" not in filter_status:
            if "Listed" in filter_status:
                filtered = filtered[filtered["listed_platform"].isin(
                    [p for p in PLATFORMS if p != "Not Listed"]
                ) & (filtered["listed_price"] > 0)]
            if "Not Listed" in filter_status:
                filtered = filtered[
                    (filtered["listed_platform"] == "Not Listed") | (filtered["listed_price"] == 0)
                ]

        if filter_platform:
            filtered = filtered[
                filtered["listed_platform"].isin(filter_platform) |
                (filtered["listed_platform"] == "")
            ]

        if filter_tier:
            filtered = filtered[filtered["tier"].isin(filter_tier)]

        filtered = filtered.sort_values(sort_by, ascending=False)

        st.caption(f"Showing **{len(filtered)}** of {total_pairs} pairs")

        # ── Per-pair cards ──────────────────────────────────────────────────────
        for _, row in filtered.iterrows():
            item_id    = int(row["id"])
            tier       = row["tier"]
            tier_color = row["tier_color"]
            days_held  = row["days_held"]
            lp         = row["listed_price"]
            tp         = row["target_price"]
            display_price = lp if lp > 0 else tp
            sugg       = row["suggested_price"]
            pot_profit = row["potential_profit"]

            with st.container():
                st.markdown(
                    f"<div style='border-left:4px solid {tier_color};"
                    f"background:#0e1117;padding:2px 0 2px 12px;margin-bottom:4px;'></div>",
                    unsafe_allow_html=True,
                )

                c1, c2, c3, c4, c5 = st.columns([4, 1, 1, 1, 2])

                with c1:
                    size_tag   = f" Sz **{row['size']}**" if row.get("size") else ""
                    brand_tag  = f" _{row['brand']}_" if row.get("brand") else ""
                    platform_tag = f"`{row['listed_platform']}`" if row.get("listed_platform") and row["listed_platform"] != "Not Listed" else "🔴 Not listed"
                    sku_tag = f" · `{row['sku']}`" if row.get("sku") else ""
                    st.markdown(
                        f"**👟 {row['shoe_name']}**{size_tag}{brand_tag}{sku_tag}"
                    )
                    cond = row.get("condition", "")
                    source = row.get("source", "")
                    info_parts = []
                    if cond:
                        info_parts.append(cond)
                    if source:
                        info_parts.append(f"Source: {source}")
                    if row.get("date_purchased"):
                        info_parts.append(f"Bought: {str(row['date_purchased'])[:10]}")
                    if info_parts:
                        st.caption(" · ".join(info_parts))
                    st.caption(f"Platform: {platform_tag}")

                with c2:
                    st.metric("COGS", f"${row['cost_basis']:.2f}")

                with c3:
                    st.metric(
                        "Listed / Target",
                        f"${display_price:.2f}" if display_price else "—",
                    )

                with c4:
                    st.metric(
                        "Days Held",
                        days_held,
                        delta=tier,
                        delta_color="off",
                    )

                with c5:
                    profit_icon = "💵" if pot_profit >= 0 else "📉"
                    st.metric(
                        f"{profit_icon} Est. Profit",
                        f"${pot_profit:.2f}" if display_price else "—",
                    )
                    if sugg > 0 and sugg < display_price and days_held >= 14:
                        st.caption(
                            f"💡 Drop to **${sugg:.2f}** (+{int(row['tier_info_drop'] * 100) if 'tier_info_drop' in row else ''}% markup strategy)"
                        )

                # ── Quick action row ────────────────────────────────────────────
                qa1, qa2, qa3, qa4, qa5 = st.columns(5)

                with qa1:
                    # Quick reprice
                    new_price = st.number_input(
                        "Reprice to $",
                        min_value=0.0,
                        value=float(display_price or 0),
                        step=5.0,
                        key=f"reprice_{item_id}",
                        label_visibility="collapsed",
                    )
                    if st.button("💲 Reprice", key=f"btn_reprice_{item_id}", use_container_width=True):
                        _update_item(item_id, "listed_price", new_price)
                        st.success(f"Repriced to ${new_price:.2f}")
                        st.rerun()

                with qa2:
                    platform_change = st.selectbox(
                        "Move to platform",
                        PLATFORMS,
                        index=PLATFORMS.index(row["listed_platform"]) if row.get("listed_platform") in PLATFORMS else 0,
                        key=f"plat_{item_id}",
                        label_visibility="collapsed",
                    )
                    if st.button("🔄 Move Platform", key=f"btn_plat_{item_id}", use_container_width=True):
                        _update_item(item_id, "listed_platform", platform_change)
                        if not row.get("listed_date"):
                            _update_item(item_id, "listed_date", str(date.today()))
                        st.success(f"Moved to {platform_change}")
                        st.rerun()

                with qa3:
                    if st.button("🤖 AI Listing", key=f"btn_listing_{item_id}", use_container_width=True):
                        st.session_state[f"prefill_listing_{item_id}"] = {
                            "shoe_name": row["shoe_name"],
                            "sku":       row.get("sku", ""),
                            "size":      row.get("size", ""),
                            "condition": row.get("condition", ""),
                            "cost":      row["cost_basis"],
                        }
                        st.info(
                            f"Go to **Page 86 — AI Listing Generator** to generate a listing for "
                            f"**{row['shoe_name']}** Sz {row.get('size', '')}."
                        )

                with qa4:
                    if st.button("📝 Notes", key=f"btn_notes_{item_id}", use_container_width=True):
                        st.session_state[f"edit_notes_{item_id}"] = True

                    if st.session_state.get(f"edit_notes_{item_id}"):
                        new_notes = st.text_area(
                            "Update notes",
                            value=row.get("notes", ""),
                            key=f"notes_val_{item_id}",
                        )
                        if st.button("💾 Save", key=f"save_notes_{item_id}"):
                            _update_item(item_id, "notes", new_notes)
                            st.session_state.pop(f"edit_notes_{item_id}", None)
                            st.success("Notes saved.")
                            st.rerun()

                with qa5:
                    if st.button("🗑️ Delete", key=f"btn_del_{item_id}", use_container_width=True):
                        st.session_state[f"confirm_del_{item_id}"] = True

                    if st.session_state.get(f"confirm_del_{item_id}"):
                        st.warning("⚠️ Delete this pair permanently?")
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            if st.button("Yes, delete", key=f"yes_del_{item_id}", type="primary"):
                                _delete_item(item_id)
                                st.session_state.pop(f"confirm_del_{item_id}", None)
                                st.success("Deleted.")
                                st.rerun()
                        with cc2:
                            if st.button("Cancel", key=f"no_del_{item_id}"):
                                st.session_state.pop(f"confirm_del_{item_id}", None)
                                st.rerun()

                # Notes display
                if row.get("notes"):
                    st.caption(f"📝 {row['notes']}")

                st.divider()

        # ── Flat table view toggle ──────────────────────────────────────────────
        with st.expander("📋 Flat Table View"):
            display_cols = [
                "shoe_name", "brand", "size", "condition", "cost_basis",
                "listed_price", "listed_platform", "days_held", "tier",
                "potential_profit", "source", "date_purchased",
            ]
            disp = filtered[[c for c in display_cols if c in filtered.columns]].copy()
            disp.columns = [c.replace("_", " ").title() for c in disp.columns]
            st.dataframe(disp, use_container_width=True, hide_index=True)

            csv = filtered.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Export Inventory CSV",
                data=csv,
                file_name=f"soleops_inventory_{date.today()}.csv",
                mime="text/csv",
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ADD PAIR
# ══════════════════════════════════════════════════════════════════════════════
with tab_add:
    st.subheader("➕ Add New Pair to Inventory")

    with st.form("add_pair_form", clear_on_submit=True):
        st.markdown("**Shoe Details**")
        row1_c1, row1_c2, row1_c3 = st.columns(3)
        with row1_c1:
            shoe_name = st.text_input("Shoe Name *", placeholder="Air Jordan 1 High OG Chicago")
            brand     = st.text_input("Brand",       placeholder="Jordan / Nike / Adidas")
        with row1_c2:
            colorway  = st.text_input("Colorway",    placeholder="Varsity Red/White/Black")
            sku       = st.text_input("SKU",         placeholder="555088-101")
        with row1_c3:
            size      = st.selectbox("Size",       SIZES, index=SIZES.index("10"))
            condition = st.selectbox("Condition",  CONDITIONS)

        st.markdown("---")
        st.markdown("**Purchase Info**")
        row2_c1, row2_c2, row2_c3 = st.columns(3)
        with row2_c1:
            cost_basis     = st.number_input("Buy Price (COGS) *", min_value=0.0, step=5.0, format="%.2f")
            date_purchased = st.date_input("Date Purchased",       value=date.today())
        with row2_c2:
            source = st.selectbox("Where Bought", SOURCES)
        with row2_c3:
            notes = st.text_area("Notes", placeholder="Receipt #, condition notes, etc.", height=80)

        st.markdown("---")
        st.markdown("**Listing Info** *(optional — fill in when you list)*)")
        row3_c1, row3_c2, row3_c3 = st.columns(3)
        with row3_c1:
            listed_platform = st.selectbox("Platform", PLATFORMS, index=PLATFORMS.index("Not Listed"))
            listed_date     = st.date_input("Date Listed", value=date.today())
        with row3_c2:
            listed_price    = st.number_input("Listed Price ($)",  min_value=0.0, step=5.0, format="%.2f")
            target_price    = st.number_input("Target Price ($)",  min_value=0.0, step=5.0, format="%.2f",
                                              help="What you want to sell for (used if not yet listed)")
        with row3_c3:
            is_listed = listed_platform != "Not Listed" and listed_price > 0
            if is_listed and listed_price > 0:
                fee = _calc_fee(listed_platform, listed_price)
                net = round(listed_price - fee - cost_basis, 2)
                st.markdown("**Live Profit Preview:**")
                st.markdown(f"Fee: `${fee:.2f}`")
                clr = "#21c354" if net >= 0 else "#ff4b4b"
                st.markdown(
                    f"Net Profit: <span style='color:{clr}; font-weight:700;'>**${net:.2f}**</span>",
                    unsafe_allow_html=True,
                )
            elif target_price > 0 and cost_basis > 0:
                fee = _calc_fee("eBay", target_price)
                net = round(target_price - fee - cost_basis, 2)
                st.markdown("**Profit at Target (eBay):**")
                clr = "#21c354" if net >= 0 else "#ff4b4b"
                st.markdown(
                    f"<span style='color:{clr}; font-weight:700;'>**${net:.2f}**</span>",
                    unsafe_allow_html=True,
                )

        submitted = st.form_submit_button("➕ Add to Inventory", type="primary", use_container_width=True)

        if submitted:
            if not shoe_name.strip():
                st.error("Shoe name is required.")
            elif cost_basis <= 0:
                st.error("Buy price must be greater than $0.")
            else:
                _add_item({
                    "shoe_name":       shoe_name.strip(),
                    "brand":           brand.strip(),
                    "colorway":        colorway.strip(),
                    "sku":             sku.strip(),
                    "size":            size,
                    "condition":       condition,
                    "cost_basis":      cost_basis,
                    "date_purchased":  str(date_purchased),
                    "source":          source,
                    "listed_date":     str(listed_date) if is_listed else "",
                    "listed_price":    listed_price if is_listed else 0.0,
                    "listed_platform": listed_platform if is_listed else "Not Listed",
                    "target_price":    target_price,
                    "status":          "inventory",
                    "notes":           notes.strip(),
                })
                st.success(
                    f"✅ Added **{shoe_name}** Sz {size} to inventory! "
                    f"COGS: **${cost_basis:.2f}**"
                )
                st.balloons()

    st.markdown("---")

    # ── Bulk CSV import ────────────────────────────────────────────────────────
    with st.expander("📤 Bulk Import from CSV"):
        st.caption(
            "Upload a CSV with columns: `shoe_name`, `size`, `cost_basis`, `condition`, "
            "`source`, `date_purchased`, `target_price`, `notes`. "
            "Other columns are optional."
        )
        csv_file = st.file_uploader("Upload CSV", type=["csv"], key="bulk_import_csv")
        if csv_file:
            try:
                import_df = pd.read_csv(csv_file)
                st.dataframe(import_df.head(5), use_container_width=True)
                st.caption(f"Preview: {len(import_df)} rows")

                if st.button("📥 Import All Rows", type="primary"):
                    count = 0
                    errors = []
                    for _, irow in import_df.iterrows():
                        try:
                            name = str(irow.get("shoe_name", "")).strip()
                            if not name:
                                continue
                            _add_item({
                                "shoe_name":       name,
                                "brand":           str(irow.get("brand", "")),
                                "colorway":        str(irow.get("colorway", "")),
                                "sku":             str(irow.get("sku", "")),
                                "size":            str(irow.get("size", "")),
                                "condition":       str(irow.get("condition", "Deadstock / New")),
                                "cost_basis":      float(irow.get("cost_basis", 0) or 0),
                                "date_purchased":  str(irow.get("date_purchased", "")),
                                "source":          str(irow.get("source", "")),
                                "listed_date":     str(irow.get("listed_date", "")),
                                "listed_price":    float(irow.get("listed_price", 0) or 0),
                                "listed_platform": str(irow.get("listed_platform", "Not Listed")),
                                "target_price":    float(irow.get("target_price", 0) or 0),
                                "status":          "inventory",
                                "notes":           str(irow.get("notes", "")),
                            })
                            count += 1
                        except Exception as e:
                            errors.append(str(e))
                    st.success(f"✅ Imported {count} pairs!")
                    if errors:
                        st.warning(f"{len(errors)} rows had errors: {errors[:3]}")
                    st.rerun()
            except Exception as e:
                st.error(f"Failed to read CSV: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
with tab_analytics:
    st.subheader("📊 Inventory Analytics")

    if inv_df.empty:
        st.info("Add some inventory to see analytics.")
    else:
        # ── KPI row ────────────────────────────────────────────────────────────
        unlisted  = inv_df[inv_df["listed_price"] == 0]
        listed    = inv_df[inv_df["listed_price"] > 0]
        avg_cogs  = inv_df["cost_basis"].mean()
        avg_days  = inv_df["days_held"].mean()
        total_sugg_rev = (
            inv_df["listed_price"].where(inv_df["listed_price"] > 0, inv_df["target_price"]).sum()
        )

        ak1, ak2, ak3, ak4 = st.columns(4)
        ak1.metric("📋 Listed Pairs",     len(listed),   delta=f"{len(unlisted)} unlisted", delta_color="inverse" if len(unlisted) > 0 else "normal")
        ak2.metric("💵 Avg COGS",        f"${avg_cogs:.2f}")
        ak3.metric("📅 Avg Days Held",   f"{avg_days:.0f}d")
        ak4.metric("📦 Total Pairs",      total_pairs)

        st.markdown("---")

        col_l, col_r = st.columns(2)

        # ── Aging distribution bar chart ────────────────────────────────────────
        with col_l:
            st.markdown("#### ⏰ Inventory Age Distribution")
            tier_counts = inv_df["tier"].value_counts().reset_index()
            tier_counts.columns = ["Tier", "Pairs"]
            tier_order = ["🟢 Fresh", "🟡 Warm", "🟠 Aging", "🔴 Stale", "⚫ Critical"]
            tier_color_map = {
                "🟢 Fresh":    "#22c55e",
                "🟡 Warm":     "#eab308",
                "🟠 Aging":    "#f97316",
                "🔴 Stale":    "#ef4444",
                "⚫ Critical": "#6b7280",
            }
            tier_counts["order"] = tier_counts["Tier"].apply(
                lambda t: tier_order.index(t) if t in tier_order else 99
            )
            tier_counts = tier_counts.sort_values("order")

            bar = (
                alt.Chart(tier_counts)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                .encode(
                    x=alt.X("Tier:N", sort=tier_order, title="Age Tier"),
                    y=alt.Y("Pairs:Q", title="# Pairs"),
                    color=alt.Color(
                        "Tier:N",
                        scale=alt.Scale(
                            domain=tier_order,
                            range=[tier_color_map[t] for t in tier_order],
                        ),
                        legend=None,
                    ),
                    tooltip=["Tier:N", "Pairs:Q"],
                )
                .properties(height=280)
            )
            st.altair_chart(bar, use_container_width=True)

        # ── COGS by platform ────────────────────────────────────────────────────
        with col_r:
            st.markdown("#### 🏪 COGS at Risk by Platform")
            plat_cogs = (
                inv_df.groupby("listed_platform")["cost_basis"]
                .sum()
                .reset_index()
                .rename(columns={"listed_platform": "Platform", "cost_basis": "COGS"})
                .sort_values("COGS", ascending=False)
            )
            plat_bar = (
                alt.Chart(plat_cogs)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                .encode(
                    x=alt.X("Platform:N", sort="-y"),
                    y=alt.Y("COGS:Q", title="COGS ($)", axis=alt.Axis(format="$,.0f")),
                    color=alt.Color("COGS:Q", scale=alt.Scale(scheme="orangered"), legend=None),
                    tooltip=[
                        alt.Tooltip("Platform:N"),
                        alt.Tooltip("COGS:Q", format="$,.2f", title="COGS"),
                    ],
                )
                .properties(height=280)
            )
            st.altair_chart(plat_bar, use_container_width=True)

        st.markdown("---")

        col_l2, col_r2 = st.columns(2)

        # ── Size distribution ──────────────────────────────────────────────────
        with col_l2:
            st.markdown("#### 👟 Inventory by Size")
            size_dist = inv_df["size"].value_counts().reset_index()
            size_dist.columns = ["Size", "Count"]
            size_dist["Size_num"] = pd.to_numeric(size_dist["Size"], errors="coerce")
            size_dist = size_dist.sort_values("Size_num")

            size_bar = (
                alt.Chart(size_dist)
                .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color="#FFAB76")
                .encode(
                    x=alt.X("Size:O", sort=None),
                    y=alt.Y("Count:Q"),
                    tooltip=["Size:O", "Count:Q"],
                )
                .properties(height=260)
            )
            st.altair_chart(size_bar, use_container_width=True)

        # ── Top 10 most valuable pairs ─────────────────────────────────────────
        with col_r2:
            st.markdown("#### 💰 Top 10 Most Valuable (by potential profit)")
            top10 = inv_df.nlargest(10, "potential_profit")[
                ["shoe_name", "size", "cost_basis", "listed_price", "target_price",
                 "potential_profit", "days_held", "tier"]
            ].copy()
            top10["listed_price"] = top10.apply(
                lambda r: r["listed_price"] if r["listed_price"] > 0 else r["target_price"], axis=1
            )
            top10 = top10.rename(columns={
                "shoe_name":       "Shoe",
                "size":            "Sz",
                "cost_basis":      "COGS",
                "listed_price":    "Price",
                "potential_profit":"Est. Profit",
                "days_held":       "Days",
                "tier":            "Status",
            })
            for col in ["COGS", "Price", "Est. Profit"]:
                top10[col] = top10[col].apply(lambda x: f"${x:,.2f}")
            top10.drop(columns=["target_price"], inplace=True, errors="ignore")
            st.dataframe(top10, use_container_width=True, hide_index=True)

        st.markdown("---")

        # ── AI Inventory Insights ──────────────────────────────────────────────
        st.markdown("#### 🤖 AI Inventory Insights")
        api_key = get_setting("anthropic_api_key", "")
        if not api_key:
            st.info("💡 Add your Anthropic API key in the P&L Dashboard to enable AI insights.")
        else:
            if st.button("✨ Generate AI Inventory Insights", type="primary"):
                with st.spinner("Claude is analyzing your inventory..."):
                    try:
                        import anthropic
                        client = anthropic.Anthropic(api_key=api_key)

                        unlisted_names = inv_df[inv_df["listed_price"] == 0]["shoe_name"].tolist()[:8]
                        top_profit = inv_df.nlargest(5, "potential_profit")[
                            ["shoe_name", "size", "cost_basis", "listed_price", "potential_profit"]
                        ].to_string(index=False)
                        aging_pairs = inv_df[inv_df["days_held"] >= 14][
                            ["shoe_name", "size", "days_held", "tier"]
                        ].to_string(index=False)

                        prompt = f"""You are a sneaker resale strategist reviewing active inventory.

INVENTORY SUMMARY:
- Total active pairs: {total_pairs}
- Total COGS at risk: ${total_cogs:,.2f}
- Avg days held: {avg_days:.0f} days
- Unlisted pairs: {len(unlisted)} ({', '.join(unlisted_names[:5]) if unlisted_names else 'none'})

TOP PROFIT POTENTIAL:
{top_profit}

AGING PAIRS (14d+):
{aging_pairs if not inv_df[inv_df['days_held'] >= 14].empty else 'None'}

Provide:
1. Top 3 pairs to list IMMEDIATELY and why
2. Any pairs to cross-list on a different platform
3. Which pairs are likely to need a price drop soon
4. One quick win to maximize this week's cash flow
5. Any concerning patterns in the inventory

Be specific with dollar amounts and platform recommendations. Use markdown. Max 250 words."""

                        msg = client.messages.create(
                            model="claude-opus-4-5",
                            max_tokens=1000,
                            messages=[{"role": "user", "content": prompt}],
                        )
                        st.markdown(msg.content[0].text)
                    except Exception as e:
                        st.error(f"AI insights failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — MARK SOLD
# ══════════════════════════════════════════════════════════════════════════════
with tab_sell:
    st.subheader("✅ Mark a Pair as Sold")
    st.caption(
        "Record a sale here — it automatically transfers to the **P&L Dashboard** "
        "with full fee calculation and net profit."
    )

    if inv_df.empty:
        st.info("No active inventory to mark as sold. Add pairs in the **➕ Add Pair** tab.")
    else:
        # ── Pair selector ──────────────────────────────────────────────────────
        pair_options = inv_df.apply(
            lambda r: f"{r['shoe_name']} Sz {r['size']} — COGS ${r['cost_basis']:.2f}",
            axis=1
        ).tolist()
        selected_idx = st.selectbox(
            "Select pair sold",
            range(len(pair_options)),
            format_func=lambda i: pair_options[i],
        )

        if selected_idx is not None:
            selected_row = inv_df.iloc[selected_idx]
            item_id = int(selected_row["id"])

            st.markdown("---")
            sc1, sc2, sc3, sc4 = st.columns(4)

            with sc1:
                sale_platform = st.selectbox(
                    "Sold on Platform",
                    [p for p in PLATFORMS if p != "Not Listed"],
                    index=0 if selected_row.get("listed_platform") not in PLATFORMS
                    else [p for p in PLATFORMS if p != "Not Listed"].index(selected_row["listed_platform"])
                    if selected_row["listed_platform"] in [p for p in PLATFORMS if p != "Not Listed"]
                    else 0,
                )

            with sc2:
                default_sale_price = float(selected_row["listed_price"]) if selected_row["listed_price"] > 0 else float(selected_row["target_price"]) if selected_row["target_price"] > 0 else 0.0
                sale_price = st.number_input(
                    "Final Sale Price ($)",
                    min_value=0.0,
                    value=default_sale_price,
                    step=5.0,
                    format="%.2f",
                )

            with sc3:
                sale_date     = st.date_input("Sale Date", value=date.today())
                shipping_cost = st.number_input("Shipping Cost ($)", min_value=0.0, value=12.0, step=0.50, format="%.2f")

            with sc4:
                if sale_price > 0:
                    fee = _calc_fee(sale_platform, sale_price)
                    net = round(sale_price - fee - selected_row["cost_basis"] - shipping_cost, 2)
                    st.markdown("**Sale Preview:**")
                    st.metric("Platform Fee",  f"${fee:.2f}")
                    clr = "normal" if net >= 0 else "inverse"
                    st.metric("Net Profit",    f"${net:.2f}", delta_color=clr)
                    roi = round(net / selected_row["cost_basis"] * 100, 1) if selected_row["cost_basis"] > 0 else 0
                    st.caption(f"ROI: {roi:+.1f}%")

            if st.button(
                f"✅ Mark '{selected_row['shoe_name']} Sz {selected_row['size']}' as SOLD",
                type="primary",
                use_container_width=True,
            ):
                if sale_price <= 0:
                    st.error("Sale price must be greater than $0.")
                else:
                    _mark_sold(
                        item_id=item_id,
                        sale_price=sale_price,
                        platform=sale_platform,
                        sale_date=str(sale_date),
                        shipping=shipping_cost,
                    )
                    st.success(
                        f"🎉 **{selected_row['shoe_name']} Sz {selected_row['size']}** marked as sold! "
                        f"Net profit: **${round(sale_price - _calc_fee(sale_platform, sale_price) - selected_row['cost_basis'] - shipping_cost, 2):.2f}** "
                        f"— Added to P&L Dashboard automatically."
                    )
                    st.balloons()
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — SOLD HISTORY
# ══════════════════════════════════════════════════════════════════════════════
with tab_sold:
    st.subheader("🏁 Sold Pairs History")
    st.caption("Pairs marked sold from inventory. Full details in the P&L Dashboard (page 69).")

    sold_enriched = _enrich_inventory(sold_df)

    if sold_enriched.empty:
        st.info("No sold pairs yet. Mark a pair as sold in the **✅ Mark Sold** tab.")
    else:
        sh_k1, sh_k2, sh_k3 = st.columns(3)
        sh_k1.metric("✅ Total Pairs Sold",    len(sold_enriched))
        sh_k2.metric("💸 Total COGS Deployed", f"${sold_enriched['cost_basis'].sum():,.2f}")
        sh_k3.metric("📅 Most Recent",
                     str(sold_enriched["created_at"].max())[:10] if "created_at" in sold_enriched.columns else "—")

        st.markdown("---")
        disp_sold = sold_enriched[[
            "shoe_name", "brand", "size", "condition",
            "cost_basis", "listed_price", "listed_platform",
            "date_purchased", "source", "notes",
        ]].copy()
        disp_sold.columns = [
            "Shoe", "Brand", "Sz", "Condition",
            "COGS", "Listed Price", "Platform",
            "Purchased", "Source", "Notes",
        ]
        disp_sold["COGS"]         = disp_sold["COGS"].apply(lambda x: f"${x:,.2f}")
        disp_sold["Listed Price"] = disp_sold["Listed Price"].apply(lambda x: f"${x:,.2f}" if x > 0 else "—")
        st.dataframe(disp_sold, use_container_width=True, hide_index=True)
