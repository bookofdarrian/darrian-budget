import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, date
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(
    page_title="SoleOps P&L Dashboard — Peach State Savings",
    page_icon="👟",
    layout="wide",
    initial_sidebar_state="auto",
)
init_db()
inject_css()
require_login()

# ── Sidebar ────────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()


# ── DB Helpers ─────────────────────────────────────────────────────────────────
def _ensure_tables():
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sales (
                id SERIAL PRIMARY KEY,
                shoe_name TEXT NOT NULL,
                sku TEXT DEFAULT '',
                cogs REAL NOT NULL DEFAULT 0,
                sale_price REAL NOT NULL DEFAULT 0,
                platform TEXT NOT NULL DEFAULT 'eBay',
                sale_date TEXT NOT NULL,
                shipping_cost REAL NOT NULL DEFAULT 0,
                platform_fee REAL NOT NULL DEFAULT 0,
                net_profit REAL NOT NULL DEFAULT 0,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS soleops_mileage (
                id SERIAL PRIMARY KEY,
                log_date TEXT NOT NULL,
                miles REAL NOT NULL DEFAULT 0,
                purpose TEXT DEFAULT '',
                created_at TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS'))
            )
        """)
    else:
        c.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shoe_name TEXT NOT NULL,
                sku TEXT DEFAULT '',
                cogs REAL NOT NULL DEFAULT 0,
                sale_price REAL NOT NULL DEFAULT 0,
                platform TEXT NOT NULL DEFAULT 'eBay',
                sale_date TEXT NOT NULL,
                shipping_cost REAL NOT NULL DEFAULT 0,
                platform_fee REAL NOT NULL DEFAULT 0,
                net_profit REAL NOT NULL DEFAULT 0,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS soleops_mileage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_date TEXT NOT NULL,
                miles REAL NOT NULL DEFAULT 0,
                purpose TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
    conn.commit()
    conn.close()


_ensure_tables()


# ── Platform fee calculator ────────────────────────────────────────────────────
PLATFORMS = ["eBay", "Mercari", "StockX", "GOAT", "Poshmark"]

def calc_platform_fee(platform: str, sale_price: float) -> float:
    """Return the platform fee in dollars for a given sale price."""
    if platform == "eBay":
        return round(sale_price * 0.129 + 0.30, 2)
    elif platform == "Mercari":
        return round(sale_price * 0.10 + 0.30, 2)
    elif platform == "StockX":
        return round(sale_price * 0.115, 2)
    elif platform == "GOAT":
        return round(sale_price * 0.095 + 5.00, 2)
    elif platform == "Poshmark":
        if sale_price < 15:
            return 2.95
        return round(sale_price * 0.20, 2)
    return 0.0


def calc_net_profit(cogs: float, sale_price: float, platform: str, shipping: float) -> tuple[float, float]:
    """Returns (platform_fee, net_profit)."""
    fee = calc_platform_fee(platform, sale_price)
    net = sale_price - cogs - fee - shipping
    return round(fee, 2), round(net, 2)


# ── Data loaders ───────────────────────────────────────────────────────────────
def load_sales() -> pd.DataFrame:
    conn = get_conn()
    try:
        if USE_POSTGRES:
            import psycopg2.extras
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            c.execute("SELECT * FROM soleops_sales ORDER BY sale_date DESC")
            rows = c.fetchall()
            df = pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()
        else:
            import pandas as _pd
            df = _pd.read_sql("SELECT * FROM soleops_sales ORDER BY sale_date DESC", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    if df.empty:
        df = pd.DataFrame(columns=[
            "id", "shoe_name", "sku", "cogs", "sale_price",
            "platform", "sale_date", "shipping_cost",
            "platform_fee", "net_profit", "notes", "created_at"
        ])
    for col in ["cogs", "sale_price", "shipping_cost", "platform_fee", "net_profit"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def load_mileage() -> pd.DataFrame:
    conn = get_conn()
    try:
        if USE_POSTGRES:
            import psycopg2.extras
            c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            c.execute("SELECT * FROM soleops_mileage ORDER BY log_date DESC")
            rows = c.fetchall()
            df = pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()
        else:
            import pandas as _pd
            df = _pd.read_sql("SELECT * FROM soleops_mileage ORDER BY log_date DESC", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    if df.empty:
        df = pd.DataFrame(columns=["id", "log_date", "miles", "purpose", "created_at"])
    if "miles" in df.columns:
        df["miles"] = pd.to_numeric(df["miles"], errors="coerce").fillna(0.0)
    return df


# ── Page header ───────────────────────────────────────────────────────────────
st.title("👟 SoleOps P&L Dashboard")
st.caption("Track sneaker resale profits, platform fees, monthly trends, and Schedule C taxes.")
st.markdown("---")

# ── Load data ──────────────────────────────────────────────────────────────────
sales_df = load_sales()
mileage_df = load_mileage()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_overview, tab_sales_log, tab_platform, tab_monthly, tab_tax = st.tabs([
    "📊 Overview",
    "📝 Sales Log",
    "🏪 Platform Breakdown",
    "📅 Monthly P&L",
    "🧾 Tax Summary",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
with tab_overview:
    st.subheader("📊 Business Overview")

    if sales_df.empty:
        st.info("No sales recorded yet. Use the **Sales Log** tab to add your first sale.")
    else:
        total_revenue   = sales_df["sale_price"].sum()
        total_cogs      = sales_df["cogs"].sum()
        total_fees      = sales_df["platform_fee"].sum()
        total_shipping  = sales_df["shipping_cost"].sum()
        gross_profit    = total_revenue - total_cogs
        net_profit      = sales_df["net_profit"].sum()
        roi_pct         = (net_profit / total_cogs * 100) if total_cogs > 0 else 0.0
        total_units     = len(sales_df)

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("💰 Total Revenue",       f"${total_revenue:,.2f}")
        c2.metric("📦 Total COGS",          f"${total_cogs:,.2f}")
        c3.metric("📈 Gross Profit",        f"${gross_profit:,.2f}")
        c4.metric("🏁 Net Profit (After Fees)", f"${net_profit:,.2f}")
        c5.metric("🎯 ROI %",               f"{roi_pct:.1f}%")

        st.markdown("---")
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("#### 💸 Fee & Cost Breakdown")
            breakdown_data = {
                "Category": ["COGS", "Platform Fees", "Shipping", "Net Profit"],
                "Amount":   [total_cogs, total_fees, total_shipping, max(net_profit, 0)],
            }
            bd_df = pd.DataFrame(breakdown_data)
            bd_df["Pct of Revenue"] = bd_df["Amount"].apply(
                lambda x: f"{x / total_revenue * 100:.1f}%" if total_revenue > 0 else "—"
            )
            bd_df["Amount"] = bd_df["Amount"].apply(lambda x: f"${x:,.2f}")
            st.dataframe(bd_df, use_container_width=True, hide_index=True)

        with col_r:
            st.markdown("#### 🏅 Platform Summary")
            plat_summary = (
                sales_df.groupby("platform")
                .agg(
                    Units=("id", "count"),
                    Revenue=("sale_price", "sum"),
                    Net_Profit=("net_profit", "sum"),
                )
                .reset_index()
                .rename(columns={"Net_Profit": "Net Profit"})
            )
            plat_summary["Avg Margin %"] = plat_summary.apply(
                lambda r: f"{r['Net Profit'] / r['Revenue'] * 100:.1f}%" if r["Revenue"] > 0 else "—",
                axis=1,
            )
            plat_summary["Revenue"]    = plat_summary["Revenue"].apply(lambda x: f"${x:,.2f}")
            plat_summary["Net Profit"] = plat_summary["Net Profit"].apply(lambda x: f"${x:,.2f}")
            st.dataframe(plat_summary, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### 🤖 AI P&L Insights")
        api_key = get_setting("anthropic_api_key", "")
        if not api_key:
            st.info("💡 Save your Anthropic API key in the Tax Summary tab to enable AI-generated reports.")
        else:
            if st.button("✨ Generate AI P&L Report", type="primary"):
                with st.spinner("Claude is analyzing your P&L data..."):
                    try:
                        import anthropic
                        client = anthropic.Anthropic(api_key=api_key)

                        # Build summary for Claude
                        top_pairs = (
                            sales_df.sort_values("net_profit", ascending=False)
                            .head(5)[["shoe_name", "platform", "cogs", "sale_price", "net_profit"]]
                            .to_string(index=False)
                        )
                        worst_pairs = (
                            sales_df.sort_values("net_profit", ascending=True)
                            .head(3)[["shoe_name", "platform", "cogs", "sale_price", "net_profit"]]
                            .to_string(index=False)
                        )

                        prompt = f"""You are a financial analyst for a sneaker resale business called SoleOps.
Analyze the following P&L data and provide actionable insights:

BUSINESS SUMMARY:
- Total Revenue: ${total_revenue:,.2f}
- Total COGS: ${total_cogs:,.2f}
- Gross Profit: ${gross_profit:,.2f}
- Net Profit (after all fees): ${net_profit:,.2f}
- ROI: {roi_pct:.1f}%
- Total Units Sold: {total_units}

TOP 5 BEST PERFORMERS:
{top_pairs}

WORST PERFORMERS:
{worst_pairs}

PLATFORM BREAKDOWN:
{plat_summary.to_string(index=False)}

Please provide:
1. A brief executive summary (2-3 sentences)
2. Top 3 actionable recommendations to increase profit margins
3. Platform strategy advice (which platforms to prioritize)
4. Any red flags or concerns in the data
5. Tax planning tip for Schedule C

Keep it concise, specific, and actionable. Use markdown formatting."""

                        message = client.messages.create(
                            model="claude-opus-4-5",
                            max_tokens=1024,
                            messages=[{"role": "user", "content": prompt}],
                        )
                        st.markdown(message.content[0].text)
                    except Exception as e:
                        st.error(f"AI report failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: SALES LOG
# ═══════════════════════════════════════════════════════════════════════════════
with tab_sales_log:
    st.subheader("📝 Sales Log")

    # ── Add new sale form ──────────────────────────────────────────────────────
    with st.expander("➕ Add Completed Sale", expanded=True):
        with st.form("add_sale_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                shoe_name = st.text_input("Shoe Name *", placeholder="Air Jordan 1 Chicago")
                sku       = st.text_input("SKU", placeholder="555088-101")
                platform  = st.selectbox("Platform *", PLATFORMS)
            with col2:
                cogs       = st.number_input("COGS / Buy Price ($) *", min_value=0.0, step=5.0, format="%.2f")
                sale_price = st.number_input("Sale Price ($) *", min_value=0.0, step=5.0, format="%.2f")
                sale_date  = st.date_input("Sale Date *", value=date.today())
            with col3:
                shipping_cost = st.number_input("Shipping Cost ($)", min_value=0.0, step=0.50, format="%.2f")
                notes         = st.text_input("Notes", placeholder="Deadstock, size 10")

                # Live fee preview
                if sale_price > 0:
                    preview_fee, preview_net = calc_net_profit(cogs, sale_price, platform, shipping_cost)
                    st.markdown(f"**Platform Fee:** `${preview_fee:.2f}`")
                    color = "#21c354" if preview_net >= 0 else "#ff4b4b"
                    st.markdown(f"**Net Profit:** <span style='color:{color}'>**${preview_net:.2f}**</span>", unsafe_allow_html=True)

            submitted = st.form_submit_button("➕ Add Sale", type="primary")
            if submitted:
                if not shoe_name.strip():
                    st.error("Shoe name is required.")
                elif sale_price <= 0:
                    st.error("Sale price must be greater than $0.")
                else:
                    fee, net = calc_net_profit(cogs, sale_price, platform, shipping_cost)
                    conn = get_conn()
                    db_exec(conn,
                        """INSERT INTO soleops_sales
                           (shoe_name, sku, cogs, sale_price, platform, sale_date,
                            shipping_cost, platform_fee, net_profit, notes)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (shoe_name.strip(), sku.strip(), cogs, sale_price, platform,
                         str(sale_date), shipping_cost, fee, net, notes.strip())
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Added: **{shoe_name}** — Net Profit: **${net:.2f}**")
                    st.rerun()

    st.markdown("---")

    # ── Sales table ────────────────────────────────────────────────────────────
    if sales_df.empty:
        st.info("No sales yet. Add your first sale above.")
    else:
        # Filters
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            plat_filter = st.multiselect("Filter by Platform", PLATFORMS, default=PLATFORMS)
        with col_f2:
            sort_col = st.selectbox("Sort by", ["sale_date", "net_profit", "sale_price", "cogs"], index=0)
        with col_f3:
            sort_asc = st.radio("Order", ["Descending", "Ascending"], horizontal=True) == "Ascending"

        filtered = sales_df[sales_df["platform"].isin(plat_filter)].copy()
        filtered = filtered.sort_values(sort_col, ascending=sort_asc)

        display = filtered[[
            "shoe_name", "sku", "platform", "sale_date",
            "cogs", "sale_price", "shipping_cost", "platform_fee", "net_profit", "notes"
        ]].copy()
        display.columns = [
            "Shoe", "SKU", "Platform", "Date",
            "COGS", "Sale Price", "Shipping", "Platform Fee", "Net Profit", "Notes"
        ]

        for money_col in ["COGS", "Sale Price", "Shipping", "Platform Fee"]:
            display[money_col] = display[money_col].apply(lambda x: f"${x:,.2f}")

        def _color_net(val):
            try:
                return "color: #21c354" if float(val) >= 0 else "color: #ff4b4b"
            except Exception:
                return ""

        styled = display.style.format({"Net Profit": "${:.2f}"}).map(_color_net, subset=["Net Profit"])
        st.dataframe(styled, use_container_width=True, hide_index=True)

        # Delete a sale
        with st.expander("🗑️ Delete a Sale"):
            if not filtered.empty:
                del_id = st.selectbox(
                    "Select sale to delete",
                    filtered["id"].tolist(),
                    format_func=lambda x: (
                        filtered[filtered["id"] == x]["shoe_name"].values[0]
                        + " — "
                        + filtered[filtered["id"] == x]["sale_date"].values[0]
                    )
                )
                if st.button("🗑️ Delete Selected Sale", type="secondary"):
                    conn = get_conn()
                    db_exec(conn, "DELETE FROM soleops_sales WHERE id = ?", (int(del_id),))
                    conn.commit()
                    conn.close()
                    st.success("Sale deleted.")
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: PLATFORM BREAKDOWN
# ═══════════════════════════════════════════════════════════════════════════════
with tab_platform:
    st.subheader("🏪 Platform Breakdown")

    # ── Platform fee comparison table ──────────────────────────────────────────
    st.markdown("#### 💳 Platform Fee Reference")
    fee_ref = []
    test_prices = [50, 100, 150, 200, 300]
    for p in PLATFORMS:
        row = {"Platform": p}
        for tp in test_prices:
            fee = calc_platform_fee(p, tp)
            margin = fee / tp * 100
            row[f"${tp} sale"] = f"${fee:.2f} ({margin:.1f}%)"
        fee_ref.append(row)
    fee_ref_df = pd.DataFrame(fee_ref)
    st.dataframe(fee_ref_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    if sales_df.empty:
        st.info("Add some sales in the Sales Log to see platform analytics.")
    else:
        st.markdown("#### 📊 Net Profit by Platform")
        plat_profit = (
            sales_df.groupby("platform")
            .agg(
                Net_Profit=("net_profit", "sum"),
                Units=("id", "count"),
                Avg_Net=("net_profit", "mean"),
                Total_Revenue=("sale_price", "sum"),
                Total_Fees=("platform_fee", "sum"),
            )
            .reset_index()
        )
        plat_profit["Margin_%"] = plat_profit.apply(
            lambda r: r["Net_Profit"] / r["Total_Revenue"] * 100 if r["Total_Revenue"] > 0 else 0,
            axis=1
        )

        bar_chart = (
            alt.Chart(plat_profit)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("platform:N", title="Platform", sort="-y"),
                y=alt.Y("Net_Profit:Q", title="Net Profit ($)"),
                color=alt.Color(
                    "Net_Profit:Q",
                    scale=alt.Scale(scheme="tealblues"),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("platform:N", title="Platform"),
                    alt.Tooltip("Units:Q", title="Units Sold"),
                    alt.Tooltip("Net_Profit:Q", title="Net Profit ($)", format="$.2f"),
                    alt.Tooltip("Avg_Net:Q", title="Avg Net/Sale ($)", format="$.2f"),
                    alt.Tooltip("Margin_%:Q", title="Margin %", format=".1f"),
                ],
            )
            .properties(height=320)
        )
        st.altair_chart(bar_chart, use_container_width=True)

        st.markdown("#### 📋 Platform Detail Table")
        plat_display = plat_profit.copy()
        plat_display["Net_Profit"]     = plat_display["Net_Profit"].apply(lambda x: f"${x:,.2f}")
        plat_display["Avg_Net"]        = plat_display["Avg_Net"].apply(lambda x: f"${x:,.2f}")
        plat_display["Total_Revenue"]  = plat_display["Total_Revenue"].apply(lambda x: f"${x:,.2f}")
        plat_display["Total_Fees"]     = plat_display["Total_Fees"].apply(lambda x: f"${x:,.2f}")
        plat_display["Margin_%"]       = plat_display["Margin_%"].apply(lambda x: f"{x:.1f}%")
        plat_display.columns = ["Platform", "Net Profit", "Units Sold", "Avg Net/Sale", "Total Revenue", "Total Fees", "Margin %"]
        st.dataframe(plat_display, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### 📦 Per-Pair Profit Breakdown")
        st.caption("Select a specific sale to see the full COGS → Sale Price → Fees → Net breakdown.")

        if not sales_df.empty:
            pair_options = sales_df.apply(
                lambda r: f"{r['shoe_name']} ({r['sale_date']}) — ${r['net_profit']:.2f}",
                axis=1
            ).tolist()
            selected_idx = st.selectbox("Choose a sale", range(len(pair_options)), format_func=lambda i: pair_options[i])
            row = sales_df.iloc[selected_idx]

            pc1, pc2, pc3, pc4, pc5 = st.columns(5)
            pc1.metric("COGS",         f"${row['cogs']:.2f}")
            pc2.metric("Sale Price",   f"${row['sale_price']:.2f}")
            pc3.metric("Platform Fee", f"${row['platform_fee']:.2f}", delta=f"-{row['platform_fee']/row['sale_price']*100:.1f}% of sale" if row['sale_price'] > 0 else "")
            pc4.metric("Shipping",     f"${row['shipping_cost']:.2f}")
            net_color = "normal" if row['net_profit'] >= 0 else "inverse"
            pc5.metric("Net Profit",   f"${row['net_profit']:.2f}", delta=f"{row['net_profit']/row['sale_price']*100:.1f}% margin" if row['sale_price'] > 0 else "", delta_color=net_color)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: MONTHLY P&L
# ═══════════════════════════════════════════════════════════════════════════════
with tab_monthly:
    st.subheader("📅 Monthly P&L Trend")

    if sales_df.empty:
        st.info("Add sales data in the Sales Log to see monthly trends.")
    else:
        monthly_df = sales_df.copy()
        monthly_df["sale_date"] = pd.to_datetime(monthly_df["sale_date"], errors="coerce")
        monthly_df["month"] = monthly_df["sale_date"].dt.to_period("M").astype(str)

        monthly = (
            monthly_df.groupby("month")
            .agg(
                Revenue=("sale_price", "sum"),
                COGS=("cogs", "sum"),
                Fees=("platform_fee", "sum"),
                Shipping=("shipping_cost", "sum"),
                Net_Profit=("net_profit", "sum"),
                Units=("id", "count"),
            )
            .reset_index()
            .sort_values("month")
        )
        monthly["Gross_Profit"] = monthly["Revenue"] - monthly["COGS"]
        monthly["Margin_%"] = monthly.apply(
            lambda r: r["Net_Profit"] / r["Revenue"] * 100 if r["Revenue"] > 0 else 0,
            axis=1,
        )

        # KPI summary
        if not monthly.empty:
            best_month_row  = monthly.loc[monthly["Net_Profit"].idxmax()]
            worst_month_row = monthly.loc[monthly["Net_Profit"].idxmin()]

            mk1, mk2, mk3, mk4 = st.columns(4)
            mk1.metric("📅 Months Tracked", len(monthly))
            mk2.metric("🏆 Best Month",  best_month_row["month"],  delta=f"${best_month_row['Net_Profit']:,.2f}")
            mk3.metric("📉 Worst Month", worst_month_row["month"], delta=f"${worst_month_row['Net_Profit']:,.2f}", delta_color="inverse")
            mk4.metric("📈 Avg Monthly Net", f"${monthly['Net_Profit'].mean():,.2f}")

        st.markdown("---")
        st.markdown("#### 📈 Monthly Net Profit Trend")

        line_chart = (
            alt.Chart(monthly)
            .mark_line(point=True, strokeWidth=3, color="#FFAB76")
            .encode(
                x=alt.X("month:O", title="Month", sort=None),
                y=alt.Y("Net_Profit:Q", title="Net Profit ($)"),
                tooltip=[
                    alt.Tooltip("month:O", title="Month"),
                    alt.Tooltip("Revenue:Q", title="Revenue ($)", format="$.2f"),
                    alt.Tooltip("COGS:Q", title="COGS ($)", format="$.2f"),
                    alt.Tooltip("Net_Profit:Q", title="Net Profit ($)", format="$.2f"),
                    alt.Tooltip("Units:Q", title="Units Sold"),
                    alt.Tooltip("Margin_%:Q", title="Margin %", format=".1f"),
                ],
            )
            .properties(height=300)
        )
        zero_line = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(strokeDash=[4, 4], color="#ff4b4b", opacity=0.5).encode(y="y:Q")
        st.altair_chart(line_chart + zero_line, use_container_width=True)

        st.markdown("#### 📊 Revenue vs COGS vs Net Profit (Stacked)")
        melted = monthly.melt(
            id_vars=["month"],
            value_vars=["Revenue", "COGS", "Net_Profit"],
            var_name="Metric",
            value_name="Amount",
        )
        bar_group = (
            alt.Chart(melted)
            .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
            .encode(
                x=alt.X("month:O", title="Month", sort=None),
                y=alt.Y("Amount:Q", title="Amount ($)"),
                color=alt.Color("Metric:N", scale=alt.Scale(
                    domain=["Revenue", "COGS", "Net_Profit"],
                    range=["#FFAB76", "#e05252", "#21c354"],
                )),
                xOffset="Metric:N",
                tooltip=[
                    alt.Tooltip("month:O", title="Month"),
                    alt.Tooltip("Metric:N", title="Metric"),
                    alt.Tooltip("Amount:Q", title="Amount ($)", format="$.2f"),
                ],
            )
            .properties(height=300)
        )
        st.altair_chart(bar_group, use_container_width=True)

        st.markdown("---")
        col_best, col_worst = st.columns(2)
        with col_best:
            st.markdown("#### 🏆 Best Performers (All Time)")
            best = (
                sales_df.sort_values("net_profit", ascending=False)
                .head(10)[["shoe_name", "platform", "sale_date", "cogs", "sale_price", "net_profit"]]
                .copy()
            )
            best["net_profit"]  = best["net_profit"].apply(lambda x: f"${x:,.2f}")
            best["cogs"]        = best["cogs"].apply(lambda x: f"${x:,.2f}")
            best["sale_price"]  = best["sale_price"].apply(lambda x: f"${x:,.2f}")
            best.columns = ["Shoe", "Platform", "Date", "COGS", "Sale Price", "Net Profit"]
            st.dataframe(best, use_container_width=True, hide_index=True)

        with col_worst:
            st.markdown("#### 📉 Worst Performers (All Time)")
            worst = (
                sales_df.sort_values("net_profit", ascending=True)
                .head(10)[["shoe_name", "platform", "sale_date", "cogs", "sale_price", "net_profit"]]
                .copy()
            )
            worst["net_profit"]  = worst["net_profit"].apply(lambda x: f"${x:,.2f}")
            worst["cogs"]        = worst["cogs"].apply(lambda x: f"${x:,.2f}")
            worst["sale_price"]  = worst["sale_price"].apply(lambda x: f"${x:,.2f}")
            worst.columns = ["Shoe", "Platform", "Date", "COGS", "Sale Price", "Net Profit"]
            st.dataframe(worst, use_container_width=True, hide_index=True)

        # Monthly detail table
        st.markdown("---")
        st.markdown("#### 📋 Monthly Detail Table")
        monthly_display = monthly.copy()
        for col in ["Revenue", "COGS", "Fees", "Shipping", "Net_Profit", "Gross_Profit"]:
            monthly_display[col] = monthly_display[col].apply(lambda x: f"${x:,.2f}")
        monthly_display["Margin_%"] = monthly_display["Margin_%"].apply(lambda x: f"{x:.1f}%")
        monthly_display.columns = ["Month", "Revenue", "COGS", "Fees", "Shipping", "Net Profit", "Units", "Gross Profit", "Margin %"]
        st.dataframe(monthly_display, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5: TAX SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
with tab_tax:
    st.subheader("🧾 Schedule C Tax Summary")
    st.caption("Estimated tax summary for sole proprietor / self-employed sneaker resale (Schedule C).")

    # ── Tax year filter ────────────────────────────────────────────────────────
    current_year = datetime.today().year
    tax_year = st.selectbox("Tax Year", list(range(current_year, current_year - 6, -1)), index=0)

    if not sales_df.empty:
        tax_df = sales_df.copy()
        tax_df["sale_date"] = pd.to_datetime(tax_df["sale_date"], errors="coerce")
        tax_df = tax_df[tax_df["sale_date"].dt.year == tax_year]
    else:
        tax_df = pd.DataFrame()

    st.markdown("---")

    # ── Gross Revenue, COGS, Fees ──────────────────────────────────────────────
    gross_revenue   = tax_df["sale_price"].sum()    if not tax_df.empty else 0.0
    total_cogs_tax  = tax_df["cogs"].sum()          if not tax_df.empty else 0.0
    total_fees_tax  = tax_df["platform_fee"].sum()  if not tax_df.empty else 0.0
    total_ship_tax  = tax_df["shipping_cost"].sum() if not tax_df.empty else 0.0
    net_profit_tax  = tax_df["net_profit"].sum()    if not tax_df.empty else 0.0

    # ── Mileage ────────────────────────────────────────────────────────────────
    st.markdown("#### 🚗 Mileage Log (Business Travel)")
    with st.expander("➕ Log Business Miles"):
        with st.form("mileage_form", clear_on_submit=True):
            mc1, mc2, mc3 = st.columns(3)
            with mc1:
                m_date    = st.date_input("Date", value=date.today())
                m_miles   = st.number_input("Miles", min_value=0.0, step=0.1, format="%.1f")
            with mc2:
                m_purpose = st.text_input("Purpose", placeholder="Pickup at outlet, shipped at UPS")
            with mc3:
                st.markdown("<br>", unsafe_allow_html=True)
                m_submit = st.form_submit_button("➕ Log Miles", type="primary")

            if m_submit:
                if m_miles > 0:
                    conn = get_conn()
                    db_exec(conn,
                        "INSERT INTO soleops_mileage (log_date, miles, purpose) VALUES (?, ?, ?)",
                        (str(m_date), m_miles, m_purpose.strip())
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Logged {m_miles:.1f} miles on {m_date}")
                    st.rerun()
                else:
                    st.error("Miles must be greater than 0.")

    # IRS standard mileage rate (2024)
    IRS_MILEAGE_RATE = float(get_setting("irs_mileage_rate", "0.67"))
    with st.expander("⚙️ IRS Mileage Rate"):
        new_rate = st.number_input(
            "IRS Standard Mileage Rate ($/mile)",
            value=IRS_MILEAGE_RATE, min_value=0.0, max_value=2.0, step=0.01, format="%.2f"
        )
        if st.button("💾 Save Rate"):
            set_setting("irs_mileage_rate", str(new_rate))
            st.success(f"Rate saved: ${new_rate:.2f}/mile")
            st.rerun()

    # Filter mileage by tax year
    if not mileage_df.empty:
        mileage_year = mileage_df.copy()
        mileage_year["log_date"] = pd.to_datetime(mileage_year["log_date"], errors="coerce")
        mileage_year = mileage_year[mileage_year["log_date"].dt.year == tax_year]
        total_miles   = mileage_year["miles"].sum()
    else:
        mileage_year = pd.DataFrame()
        total_miles  = 0.0

    mileage_deduction = total_miles * IRS_MILEAGE_RATE

    if not mileage_year.empty:
        m_disp = mileage_year[["log_date", "miles", "purpose"]].copy()
        m_disp["log_date"] = m_disp["log_date"].dt.strftime("%Y-%m-%d")
        m_disp.columns = ["Date", "Miles", "Purpose"]
        st.dataframe(m_disp, use_container_width=True, hide_index=True)
    else:
        st.info(f"No mileage logged for {tax_year}.")

    st.markdown("---")
    st.markdown(f"#### 📋 Schedule C Summary — Tax Year {tax_year}")

    # SE tax: 92.35% of net × 15.3%, then deduct half
    se_net = max(net_profit_tax - mileage_deduction, 0)
    se_tax_base = se_net * 0.9235
    se_tax = se_tax_base * 0.153
    se_deduction_half = se_tax / 2  # deductible on Form 1040

    t1, t2, t3 = st.columns(3)
    with t1:
        st.markdown("**📥 Income**")
        st.metric("Gross Revenue",       f"${gross_revenue:,.2f}")
        st.metric("Total Units Sold",    f"{len(tax_df)}")

    with t2:
        st.markdown("**📤 Deductions**")
        st.metric("COGS (Inventory Cost)",  f"${total_cogs_tax:,.2f}")
        st.metric("Platform Fees",          f"${total_fees_tax:,.2f}")
        st.metric("Shipping Costs",         f"${total_ship_tax:,.2f}")
        st.metric(f"Mileage Deduction ({total_miles:.1f} mi × ${IRS_MILEAGE_RATE:.2f})", f"${mileage_deduction:,.2f}")

    with t3:
        st.markdown("**🧾 Net & Tax Estimate**")
        st.metric("Net Profit (Line 31)",            f"${net_profit_tax:,.2f}")
        st.metric("After Mileage Deduction",         f"${se_net:,.2f}")
        st.metric("Est. Self-Employment Tax (15.3%)", f"${se_tax:,.2f}")
        st.metric("½ SE Tax (1040 Deduction)",       f"${se_deduction_half:,.2f}")

    st.markdown("---")

    # ── Full Schedule C breakdown table ───────────────────────────────────────
    sch_c_rows = [
        ("Gross Receipts (Line 1)",          gross_revenue),
        ("COGS — Inventory / Cost of Goods (Line 42)", -total_cogs_tax),
        ("Gross Profit",                     gross_revenue - total_cogs_tax),
        ("Platform Fees (Line 10)",          -total_fees_tax),
        ("Shipping / Postage (Line 27a)",    -total_ship_tax),
        (f"Car & Truck — Mileage (Line 9)", -mileage_deduction),
        ("Net Profit / Loss (Line 31)",      net_profit_tax - mileage_deduction),
        ("Est. Self-Employment Tax",         -se_tax),
        ("½ SE Tax Deduction (Form 1040)",   se_deduction_half),
    ]

    sch_df = pd.DataFrame(sch_c_rows, columns=["Line Item", "Amount"])
    sch_df["Amount ($)"] = sch_df["Amount"].apply(lambda x: f"${x:,.2f}" if x >= 0 else f"-${abs(x):,.2f}")
    st.dataframe(sch_df[["Line Item", "Amount ($)"]], use_container_width=True, hide_index=True)

    st.caption(
        "⚠️ This is an estimate only — not legal or tax advice. "
        "Consult a CPA or tax professional for your actual Schedule C filing."
    )

    st.markdown("---")

    # ── AI Tax Narrative ───────────────────────────────────────────────────────
    st.markdown("#### 🤖 AI Tax & Settings")

    api_key = get_setting("anthropic_api_key", "")
    with st.expander("⚙️ Anthropic API Key"):
        new_key = st.text_input("Claude API Key", value=api_key, type="password",
                                placeholder="sk-ant-...")
        if st.button("💾 Save API Key"):
            if new_key.strip():
                set_setting("anthropic_api_key", new_key.strip())
                st.success("API key saved.")
                st.rerun()
            else:
                st.error("API key cannot be empty.")

    if not api_key:
        st.info("💡 Save your Anthropic API key above to enable AI tax insights.")
    else:
        if st.button("🤖 Generate AI Tax Insights", type="primary", key="ai_tax_btn"):
            with st.spinner("Claude is reviewing your tax situation..."):
                try:
                    import anthropic
                    client = anthropic.Anthropic(api_key=api_key)

                    prompt = f"""You are a CPA specializing in small business and self-employment taxes.
Review the following Schedule C data for a sneaker reseller and provide actionable tax advice.

TAX YEAR: {tax_year}
Gross Revenue: ${gross_revenue:,.2f}
COGS: ${total_cogs_tax:,.2f}
Platform Fees: ${total_fees_tax:,.2f}
Shipping Costs: ${total_ship_tax:,.2f}
Mileage Deduction: ${mileage_deduction:,.2f} ({total_miles:.1f} miles at ${IRS_MILEAGE_RATE:.2f}/mile)
Net Profit (Schedule C Line 31): ${net_profit_tax - mileage_deduction:,.2f}
Estimated Self-Employment Tax: ${se_tax:,.2f}
½ SE Tax Deduction: ${se_deduction_half:,.2f}

Please provide:
1. Key observations about this tax profile
2. Additional deductions they may be missing (home office, phone, storage, tools/supplies)
3. Mileage tracking tips to maximize the deduction
4. Quarterly estimated tax payment advice
5. One actionable tip to reduce their tax burden next year

Be concise, specific, and practical. Use markdown formatting."""

                    msg = client.messages.create(
                        model="claude-opus-4-5",
                        max_tokens=900,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    st.markdown(msg.content[0].text)
                except Exception as e:
                    st.error(f"AI tax insight failed: {e}")

    # ── Export CSV ─────────────────────────────────────────────────────────────
    if not tax_df.empty:
        st.markdown("---")
        csv_data = tax_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label=f"📥 Download {tax_year} Sales as CSV",
            data=csv_data,
            file_name=f"soleops_sales_{tax_year}.csv",
            mime="text/csv",
        )
