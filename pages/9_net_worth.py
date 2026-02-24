import streamlit as st
import pandas as pd
from datetime import datetime, date
from utils.db import get_conn, init_db, read_sql, execute, fetchone, load_investment_context
from utils.auth import require_login, require_pro, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Net Worth — Peach State Savings", page_icon="💎", layout="wide", initial_sidebar_state="auto")
init_db()
require_login()
require_pro("Net Worth Tracker")
inject_css()

# ── Sidebar ───────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview",          icon="📊")
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",          icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",            icon="💵")
st.sidebar.page_link("pages/3_sole_archive.py",   label="Business Tracker 🔒", icon="💼")
st.sidebar.page_link("pages/4_trends.py",         label="Monthly Trends",    icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",    label="Bank Import",       icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",       label="Receipts & HSA",    icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",    label="AI Insights 🔒",    icon="🤖")
st.sidebar.page_link("pages/8_goals.py",          label="Financial Goals",   icon="🎯")
st.sidebar.page_link("pages/9_net_worth.py",      label="Net Worth 🔒",      icon="💎")
st.sidebar.page_link("pages/0_pricing.py",        label="⭐ Upgrade to Pro", icon="⭐")
render_sidebar_user_widget()

st.title("💎 Net Worth Tracker")
st.caption("Log monthly snapshots of your assets and liabilities to track your net worth over time.")

# ── Load investment context to pre-fill ───────────────────────────────────────
_inv = load_investment_context()
_inv_401k      = float(_inv.get("bal_401k", 0) or 0)
_inv_roth      = float(_inv.get("bal_roth", 0) or 0)
_inv_hsa       = float(_inv.get("bal_hsa", 0) or 0)
_inv_brokerage = float(_inv.get("bal_brokerage", 0) or 0)

# ── Load all snapshots ────────────────────────────────────────────────────────
conn = get_conn()
snapshots = read_sql(
    "SELECT * FROM net_worth_snapshots ORDER BY snapshot_date DESC",
    conn
)
conn.close()

# ── KPI summary from latest snapshot ─────────────────────────────────────────
if not snapshots.empty:
    latest = snapshots.iloc[0]

    total_assets = (
        float(latest.get("checking", 0) or 0) +
        float(latest.get("savings", 0) or 0) +
        float(latest.get("cash_other", 0) or 0) +
        float(latest.get("bal_401k", 0) or 0) +
        float(latest.get("bal_roth", 0) or 0) +
        float(latest.get("bal_hsa", 0) or 0) +
        float(latest.get("bal_brokerage", 0) or 0) +
        float(latest.get("home_value", 0) or 0) +
        float(latest.get("vehicle_value", 0) or 0) +
        float(latest.get("other_assets", 0) or 0)
    )
    total_liabilities = (
        float(latest.get("credit_card_debt", 0) or 0) +
        float(latest.get("student_loans", 0) or 0) +
        float(latest.get("car_loan", 0) or 0) +
        float(latest.get("other_liabilities", 0) or 0)
    )
    net_worth = total_assets - total_liabilities

    # Change vs previous snapshot
    delta_str = None
    if len(snapshots) > 1:
        prev = snapshots.iloc[1]
        prev_assets = (
            float(prev.get("checking", 0) or 0) + float(prev.get("savings", 0) or 0) +
            float(prev.get("cash_other", 0) or 0) + float(prev.get("bal_401k", 0) or 0) +
            float(prev.get("bal_roth", 0) or 0) + float(prev.get("bal_hsa", 0) or 0) +
            float(prev.get("bal_brokerage", 0) or 0) + float(prev.get("home_value", 0) or 0) +
            float(prev.get("vehicle_value", 0) or 0) + float(prev.get("other_assets", 0) or 0)
        )
        prev_liabilities = (
            float(prev.get("credit_card_debt", 0) or 0) + float(prev.get("student_loans", 0) or 0) +
            float(prev.get("car_loan", 0) or 0) + float(prev.get("other_liabilities", 0) or 0)
        )
        prev_nw = prev_assets - prev_liabilities
        delta_str = f"${net_worth - prev_nw:+,.2f} vs last snapshot"

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💎 Net Worth",      f"${net_worth:,.2f}",      delta=delta_str)
    k2.metric("📈 Total Assets",   f"${total_assets:,.2f}")
    k3.metric("💳 Total Liabilities", f"${total_liabilities:,.2f}")
    k4.metric("📅 As of",          str(latest.get("snapshot_date", "—"))[:10])

    st.markdown("---")

    # ── Asset vs Liability breakdown ──────────────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("📈 Assets Breakdown")
        asset_items = {
            "🏦 Checking":          float(latest.get("checking", 0) or 0),
            "💰 Savings":           float(latest.get("savings", 0) or 0),
            "💵 Cash / Other":      float(latest.get("cash_other", 0) or 0),
            "📊 401(k)":            float(latest.get("bal_401k", 0) or 0),
            "📊 Roth IRA":          float(latest.get("bal_roth", 0) or 0),
            "🏥 HSA":               float(latest.get("bal_hsa", 0) or 0),
            "📈 Cash Mgmt / HY":    float(latest.get("bal_brokerage", 0) or 0),
            "🏠 Home Value":        float(latest.get("home_value", 0) or 0),
            "🚗 Vehicle Value":     float(latest.get("vehicle_value", 0) or 0),
            "📦 Other Assets":      float(latest.get("other_assets", 0) or 0),
        }
        asset_df = pd.DataFrame(
            [(k, v) for k, v in asset_items.items() if v > 0],
            columns=["Asset", "Value ($)"]
        )
        if not asset_df.empty:
            st.dataframe(
                asset_df.style.format({"Value ($)": "${:,.2f}"}),
                use_container_width=True, hide_index=True
            )
            st.bar_chart(asset_df.set_index("Asset"), use_container_width=True)
        else:
            st.info("No assets recorded in latest snapshot.")

    with col_b:
        st.subheader("💳 Liabilities Breakdown")
        liab_items = {
            "💳 Credit Card Debt":  float(latest.get("credit_card_debt", 0) or 0),
            "🎓 Student Loans":     float(latest.get("student_loans", 0) or 0),
            "🚗 Car Loan":          float(latest.get("car_loan", 0) or 0),
            "📦 Other Liabilities": float(latest.get("other_liabilities", 0) or 0),
        }
        liab_df = pd.DataFrame(
            [(k, v) for k, v in liab_items.items() if v > 0],
            columns=["Liability", "Balance ($)"]
        )
        if not liab_df.empty:
            st.dataframe(
                liab_df.style.format({"Balance ($)": "${:,.2f}"}),
                use_container_width=True, hide_index=True
            )
            st.bar_chart(liab_df.set_index("Liability"), use_container_width=True)
        else:
            st.success("✅ No liabilities recorded — debt free!")

    st.markdown("---")

    # ── Net Worth Over Time chart ──────────────────────────────────────────────
    if len(snapshots) > 1:
        st.subheader("📈 Net Worth Over Time")

        chart_rows = []
        for _, row in snapshots.iterrows():
            a = (
                float(row.get("checking", 0) or 0) + float(row.get("savings", 0) or 0) +
                float(row.get("cash_other", 0) or 0) + float(row.get("bal_401k", 0) or 0) +
                float(row.get("bal_roth", 0) or 0) + float(row.get("bal_hsa", 0) or 0) +
                float(row.get("bal_brokerage", 0) or 0) + float(row.get("home_value", 0) or 0) +
                float(row.get("vehicle_value", 0) or 0) + float(row.get("other_assets", 0) or 0)
            )
            l = (
                float(row.get("credit_card_debt", 0) or 0) + float(row.get("student_loans", 0) or 0) +
                float(row.get("car_loan", 0) or 0) + float(row.get("other_liabilities", 0) or 0)
            )
            label = str(row.get("label", "")).strip() or str(row.get("snapshot_date", ""))[:10]
            chart_rows.append({"Date": label, "Net Worth": a - l, "Assets": a, "Liabilities": l})

        chart_df = pd.DataFrame(chart_rows[::-1])  # chronological order
        st.line_chart(chart_df.set_index("Date")[["Net Worth", "Assets", "Liabilities"]], use_container_width=True)
        st.markdown("---")

else:
    st.info("📭 No snapshots yet. Add your first one below to start tracking your net worth.")
    st.markdown("---")

# ── Add New Snapshot ──────────────────────────────────────────────────────────
with st.expander("➕ Add New Net Worth Snapshot", expanded=snapshots.empty):
    st.caption("Fill in your current balances. Investment fields are pre-filled from your AI Insights page — update them there to keep them in sync.")

    snap_date  = st.date_input("Snapshot Date", value=date.today(), key="snap_date")
    snap_label = st.text_input("Label (optional)", placeholder="e.g. 'End of Q1 2026', 'After bonus'", key="snap_label")

    st.markdown("#### 🏦 Cash & Bank Accounts")
    c1, c2, c3 = st.columns(3)
    with c1:
        snap_checking  = st.number_input("Checking ($)",    min_value=0.0, step=100.0, key="snap_checking")
    with c2:
        snap_savings   = st.number_input("Savings ($)",     min_value=0.0, step=100.0, key="snap_savings")
    with c3:
        snap_cash_other = st.number_input("Cash / Other ($)", min_value=0.0, step=100.0, key="snap_cash_other")

    st.markdown("#### 📊 Investment Accounts")
    st.caption("Pre-filled from your saved investment context. Edit as needed.")
    i1, i2, i3, i4 = st.columns(4)
    with i1:
        snap_401k      = st.number_input("401(k) ($)",         min_value=0.0, step=100.0, value=_inv_401k,      key="snap_401k")
    with i2:
        snap_roth      = st.number_input("Roth IRA ($)",       min_value=0.0, step=100.0, value=_inv_roth,      key="snap_roth")
    with i3:
        snap_hsa       = st.number_input("HSA ($)",            min_value=0.0, step=100.0, value=_inv_hsa,       key="snap_hsa")
    with i4:
        snap_brokerage = st.number_input("Cash Mgmt / HY ($)", min_value=0.0, step=100.0, value=_inv_brokerage, key="snap_brokerage")

    st.markdown("#### 🏠 Physical Assets")
    p1, p2, p3 = st.columns(3)
    with p1:
        snap_home    = st.number_input("Home Value ($)",    min_value=0.0, step=1000.0, key="snap_home")
    with p2:
        snap_vehicle = st.number_input("Vehicle Value ($)", min_value=0.0, step=500.0,  key="snap_vehicle")
    with p3:
        snap_other_assets = st.number_input("Other Assets ($)", min_value=0.0, step=100.0, key="snap_other_assets",
                                             help="Sneaker inventory, equipment, etc.")

    st.markdown("#### 💳 Liabilities")
    l1, l2, l3, l4 = st.columns(4)
    with l1:
        snap_cc      = st.number_input("Credit Card Debt ($)", min_value=0.0, step=50.0,   key="snap_cc")
    with l2:
        snap_student = st.number_input("Student Loans ($)",    min_value=0.0, step=100.0,  key="snap_student")
    with l3:
        snap_car     = st.number_input("Car Loan ($)",         min_value=0.0, step=100.0,  key="snap_car")
    with l4:
        snap_other_liab = st.number_input("Other Liabilities ($)", min_value=0.0, step=50.0, key="snap_other_liab")

    snap_notes = st.text_area("Notes (optional)", placeholder="e.g. 'Got a raise this month', 'Paid off credit card'", key="snap_notes", height=60)

    # Live preview
    _preview_assets = (snap_checking + snap_savings + snap_cash_other +
                       snap_401k + snap_roth + snap_hsa + snap_brokerage +
                       snap_home + snap_vehicle + snap_other_assets)
    _preview_liabs  = snap_cc + snap_student + snap_car + snap_other_liab
    _preview_nw     = _preview_assets - _preview_liabs

    st.markdown("---")
    pv1, pv2, pv3 = st.columns(3)
    pv1.metric("📈 Total Assets",      f"${_preview_assets:,.2f}")
    pv2.metric("💳 Total Liabilities", f"${_preview_liabs:,.2f}")
    pv3.metric("💎 Net Worth",         f"${_preview_nw:,.2f}")

    if st.button("💾 Save Snapshot", type="primary", key="save_snapshot"):
        conn = get_conn()
        execute(conn,
            """INSERT INTO net_worth_snapshots
               (snapshot_date, label, checking, savings, cash_other,
                bal_401k, bal_roth, bal_hsa, bal_brokerage,
                home_value, vehicle_value, other_assets,
                credit_card_debt, student_loans, car_loan, other_liabilities, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (str(snap_date), snap_label.strip(),
             snap_checking, snap_savings, snap_cash_other,
             snap_401k, snap_roth, snap_hsa, snap_brokerage,
             snap_home, snap_vehicle, snap_other_assets,
             snap_cc, snap_student, snap_car, snap_other_liab,
             snap_notes.strip())
        )
        conn.commit()
        conn.close()
        st.success(f"✅ Snapshot saved for {snap_date}! Net worth: ${_preview_nw:,.2f}")
        st.rerun()

# ── Snapshot History ──────────────────────────────────────────────────────────
if not snapshots.empty:
    st.markdown("---")
    with st.expander("🗂️ Snapshot History", expanded=False):
        history_rows = []
        for _, row in snapshots.iterrows():
            a = (
                float(row.get("checking", 0) or 0) + float(row.get("savings", 0) or 0) +
                float(row.get("cash_other", 0) or 0) + float(row.get("bal_401k", 0) or 0) +
                float(row.get("bal_roth", 0) or 0) + float(row.get("bal_hsa", 0) or 0) +
                float(row.get("bal_brokerage", 0) or 0) + float(row.get("home_value", 0) or 0) +
                float(row.get("vehicle_value", 0) or 0) + float(row.get("other_assets", 0) or 0)
            )
            l = (
                float(row.get("credit_card_debt", 0) or 0) + float(row.get("student_loans", 0) or 0) +
                float(row.get("car_loan", 0) or 0) + float(row.get("other_liabilities", 0) or 0)
            )
            history_rows.append({
                "ID":          row["id"],
                "Date":        str(row.get("snapshot_date", ""))[:10],
                "Label":       str(row.get("label", "") or ""),
                "Assets ($)":  a,
                "Liabilities ($)": l,
                "Net Worth ($)": a - l,
                "Notes":       str(row.get("notes", "") or ""),
            })

        hist_df = pd.DataFrame(history_rows)

        def color_nw(val):
            if isinstance(val, (int, float)):
                return "color: #21c354" if val >= 0 else "color: #ff4b4b"
            return ""

        styled_hist = hist_df.drop(columns=["ID"]).style.format({
            "Assets ($)":       "${:,.2f}",
            "Liabilities ($)":  "${:,.2f}",
            "Net Worth ($)":    "${:,.2f}",
        }).map(color_nw, subset=["Net Worth ($)"])

        st.dataframe(styled_hist, use_container_width=True, hide_index=True)

        # Delete a snapshot
        st.markdown("---")
        del_id = st.selectbox(
            "Delete a snapshot",
            hist_df["ID"].tolist(),
            format_func=lambda x: f"#{x} — {hist_df[hist_df['ID']==x]['Date'].values[0]}  {hist_df[hist_df['ID']==x]['Label'].values[0]}"
        )
        if st.button("🗑️ Delete Snapshot", type="secondary", key="del_snapshot"):
            conn = get_conn()
            execute(conn, "DELETE FROM net_worth_snapshots WHERE id=?", (del_id,))
            conn.commit()
            conn.close()
            st.success("Deleted.")
            st.rerun()

    # ── CSV Export ────────────────────────────────────────────────────────────
    st.markdown("---")
    export_cols = ["snapshot_date", "label", "checking", "savings", "cash_other",
                   "bal_401k", "bal_roth", "bal_hsa", "bal_brokerage",
                   "home_value", "vehicle_value", "other_assets",
                   "credit_card_debt", "student_loans", "car_loan", "other_liabilities", "notes"]
    export_df = snapshots[[c for c in export_cols if c in snapshots.columns]].copy()
    st.download_button(
        "⬇️ Export All Snapshots as CSV",
        export_df.to_csv(index=False).encode(),
        file_name=f"net_worth_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
