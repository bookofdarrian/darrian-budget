import streamlit as st
import datetime
from decimal import Decimal
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Side Income Tracker", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

SELF_EMPLOYMENT_TAX_RATE = 0.25

INCOME_CATEGORIES = [
    "Freelance",
    "Gig Work",
    "Reselling",
    "Rental Income",
    "Consulting",
    "Content Creation",
    "Affiliate Marketing",
    "Tutoring",
    "Photography",
    "Crafts/Handmade",
    "Investments",
    "Other"
]


def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS side_income (
                id SERIAL PRIMARY KEY,
                source_name VARCHAR(255) NOT NULL,
                category VARCHAR(100) NOT NULL,
                amount DECIMAL(12, 2) NOT NULL,
                date_received DATE NOT NULL,
                notes TEXT,
                is_recurring BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS side_income (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                date_received DATE NOT NULL,
                notes TEXT,
                is_recurring INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    conn.close()


def add_income(source_name: str, category: str, amount: float, date_received: datetime.date, notes: str, is_recurring: bool):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO side_income (source_name, category, amount, date_received, notes, is_recurring)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (source_name, category, amount, date_received, notes, is_recurring))
    else:
        cur.execute("""
            INSERT INTO side_income (source_name, category, amount, date_received, notes, is_recurring)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (source_name, category, amount, date_received, notes, 1 if is_recurring else 0))
    conn.commit()
    conn.close()


def get_all_income():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            SELECT id, source_name, category, amount, date_received, notes, is_recurring, created_at
            FROM side_income
            ORDER BY date_received DESC
        """)
    else:
        cur.execute("""
            SELECT id, source_name, category, amount, date_received, notes, is_recurring, created_at
            FROM side_income
            ORDER BY date_received DESC
        """)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_income_by_id(income_id: int):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            SELECT id, source_name, category, amount, date_received, notes, is_recurring, created_at
            FROM side_income WHERE id = %s
        """, (income_id,))
    else:
        cur.execute("""
            SELECT id, source_name, category, amount, date_received, notes, is_recurring, created_at
            FROM side_income WHERE id = ?
        """, (income_id,))
    row = cur.fetchone()
    conn.close()
    return row


def update_income(income_id: int, source_name: str, category: str, amount: float, date_received: datetime.date, notes: str, is_recurring: bool):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            UPDATE side_income
            SET source_name = %s, category = %s, amount = %s, date_received = %s, notes = %s, is_recurring = %s
            WHERE id = %s
        """, (source_name, category, amount, date_received, notes, is_recurring, income_id))
    else:
        cur.execute("""
            UPDATE side_income
            SET source_name = ?, category = ?, amount = ?, date_received = ?, notes = ?, is_recurring = ?
            WHERE id = ?
        """, (source_name, category, amount, date_received, notes, 1 if is_recurring else 0, income_id))
    conn.commit()
    conn.close()


def delete_income(income_id: int):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("DELETE FROM side_income WHERE id = %s", (income_id,))
    else:
        cur.execute("DELETE FROM side_income WHERE id = ?", (income_id,))
    conn.commit()
    conn.close()


def get_monthly_breakdown():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            SELECT 
                TO_CHAR(date_received, 'YYYY-MM') as month,
                SUM(amount) as total
            FROM side_income
            GROUP BY TO_CHAR(date_received, 'YYYY-MM')
            ORDER BY month DESC
            LIMIT 12
        """)
    else:
        cur.execute("""
            SELECT 
                strftime('%Y-%m', date_received) as month,
                SUM(amount) as total
            FROM side_income
            GROUP BY strftime('%Y-%m', date_received)
            ORDER BY month DESC
            LIMIT 12
        """)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_category_breakdown():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            SELECT category, SUM(amount) as total
            FROM side_income
            GROUP BY category
            ORDER BY total DESC
        """)
    else:
        cur.execute("""
            SELECT category, SUM(amount) as total
            FROM side_income
            GROUP BY category
            ORDER BY total DESC
        """)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_source_breakdown():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            SELECT source_name, SUM(amount) as total, COUNT(*) as count
            FROM side_income
            GROUP BY source_name
            ORDER BY total DESC
        """)
    else:
        cur.execute("""
            SELECT source_name, SUM(amount) as total, COUNT(*) as count
            FROM side_income
            GROUP BY source_name
            ORDER BY total DESC
        """)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_ytd_income():
    conn = get_conn()
    cur = conn.cursor()
    current_year = datetime.date.today().year
    if USE_POSTGRES:
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM side_income
            WHERE EXTRACT(YEAR FROM date_received) = %s
        """, (current_year,))
    else:
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM side_income
            WHERE strftime('%Y', date_received) = ?
        """, (str(current_year),))
    result = cur.fetchone()
    conn.close()
    return float(result[0]) if result else 0.0


def get_current_month_income():
    conn = get_conn()
    cur = conn.cursor()
    today = datetime.date.today()
    if USE_POSTGRES:
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM side_income
            WHERE EXTRACT(YEAR FROM date_received) = %s
            AND EXTRACT(MONTH FROM date_received) = %s
        """, (today.year, today.month))
    else:
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM side_income
            WHERE strftime('%Y', date_received) = ?
            AND strftime('%m', date_received) = ?
        """, (str(today.year), str(today.month).zfill(2)))
    result = cur.fetchone()
    conn.close()
    return float(result[0]) if result else 0.0


def get_total_income():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(amount), 0) FROM side_income")
    result = cur.fetchone()
    conn.close()
    return float(result[0]) if result else 0.0


def calculate_tax_estimate(income: float) -> dict:
    self_employment_tax = income * 0.153
    estimated_income_tax = income * 0.22
    total_tax = self_employment_tax + estimated_income_tax
    quarterly_payment = total_tax / 4
    return {
        "self_employment_tax": self_employment_tax,
        "estimated_income_tax": estimated_income_tax,
        "total_tax": total_tax,
        "quarterly_payment": quarterly_payment,
        "effective_rate": (total_tax / income * 100) if income > 0 else 0
    }


_ensure_tables()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

st.title("💰 Side Income Tracker")
st.markdown("Track and analyze your side hustles, freelance work, and alternative income streams.")

ytd_income = get_ytd_income()
current_month_income = get_current_month_income()
total_income = get_total_income()
tax_estimate = calculate_tax_estimate(ytd_income)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("YTD Income", f"${ytd_income:,.2f}")
with col2:
    st.metric("This Month", f"${current_month_income:,.2f}")
with col3:
    st.metric("Est. Tax (YTD)", f"${tax_estimate['total_tax']:,.2f}")
with col4:
    st.metric("Quarterly Payment", f"${tax_estimate['quarterly_payment']:,.2f}")

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["📝 Add Income", "📊 Analytics", "📋 All Records", "💵 Tax Estimates"])

with tab1:
    st.subheader("Log New Side Income")
    
    with st.form("add_income_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            source_name = st.text_input("Income Source *", placeholder="e.g., Fiverr, Uber, eBay Sale")
            category = st.selectbox("Category *", INCOME_CATEGORIES)
            amount = st.number_input("Amount ($) *", min_value=0.01, step=0.01, format="%.2f")
        
        with col2:
            date_received = st.date_input("Date Received *", value=datetime.date.today())
            is_recurring = st.checkbox("Recurring Income?", help="Check if this is a regular/recurring income source")
            notes = st.text_area("Notes", placeholder="Optional notes about this income...")
        
        submitted = st.form_submit_button("💾 Save Income", use_container_width=True)
        
        if submitted:
            if not source_name:
                st.error("Please enter an income source name.")
            elif amount <= 0:
                st.error("Please enter a valid amount greater than $0.")
            else:
                try:
                    add_income(source_name, category, amount, date_received, notes, is_recurring)
                    st.success(f"✅ Added ${amount:,.2f} from {source_name}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving income: {str(e)}")

with tab2:
    st.subheader("Income Analytics")
    
    monthly_data = get_monthly_breakdown()
    category_data = get_category_breakdown()
    source_data = get_source_breakdown()
    
    if not monthly_data and not category_data:
        st.info("📭 No income data yet. Add some income records to see analytics!")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📈 Monthly Income Trend")
            if monthly_data:
                df_monthly = pd.DataFrame(monthly_data, columns=["Month", "Total"])
                df_monthly = df_monthly.sort_values("Month")
                
                fig_monthly = px.bar(
                    df_monthly,
                    x="Month",
                    y="Total",
                    title="Monthly Side Income",
                    labels={"Total": "Income ($)", "Month": "Month"},
                    color_discrete_sequence=["#FF6B6B"]
                )
                fig_monthly.update_layout(
                    xaxis_tickangle=-45,
                    showlegend=False
                )
                st.plotly_chart(fig_monthly, use_container_width=True)
            else:
                st.info("No monthly data available yet.")
        
        with col2:
            st.markdown("### 🥧 Income by Category")
            if category_data:
                df_category = pd.DataFrame(category_data, columns=["Category", "Total"])
                
                fig_category = px.pie(
                    df_category,
                    values="Total",
                    names="Category",
                    title="Income Distribution by Category",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_category.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_category, use_container_width=True)
            else:
                st.info("No category data available yet.")
        
        st.markdown("### 🏆 Top Income Sources")
        if source_data:
            df_sources = pd.DataFrame(source_data, columns=["Source", "Total", "Count"])
            df_sources["Avg per Entry"] = df_sources["Total"] / df_sources["Count"]
            
            fig_sources = px.bar(
                df_sources.head(10),
                x="Source",
                y="Total",
                title="Top 10 Income Sources",
                labels={"Total": "Total Income ($)", "Source": "Income Source"},
                color="Total",
                color_continuous_scale="Greens"
            )
            fig_sources.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_sources, use_container_width=True)
            
            st.markdown("#### Source Details")
            st.dataframe(
                df_sources.style.format({
                    "Total": "${:,.2f}",
                    "Count": "{:.0f}",
                    "Avg per Entry": "${:,.2f}"
                }),
                use_container_width=True,
                hide_index=True
            )
        
        st.markdown("### 📊 Income Diversification Score")
        if category_data:
            num_categories = len(category_data)
            total = sum([c[1] for c in category_data])
            
            if total > 0:
                proportions = [c[1] / total for c in category_data]
                hhi = sum([p**2 for p in proportions])
                diversification_score = (1 - hhi) * 100
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Active Categories", num_categories)
                with col2:
                    st.metric("Active Sources", len(source_data) if source_data else 0)
                with col3:
                    if diversification_score >= 70:
                        status = "🟢 Well Diversified"
                    elif diversification_score >= 40:
                        status = "🟡 Moderately Diversified"
                    else:
                        status = "🔴 Concentrated"
                    st.metric("Diversification", f"{diversification_score:.1f}%", status)

with tab3:
    st.subheader("All Income Records")
    
    all_income = get_all_income()
    
    if not all_income:
        st.info("📭 No income records yet. Start by adding your first side income!")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_category = st.selectbox("Filter by Category", ["All"] + INCOME_CATEGORIES)
        with col2:
            filter_recurring = st.selectbox("Filter by Type", ["All", "Recurring Only", "One-time Only"])
        with col3:
            sort_by = st.selectbox("Sort by", ["Date (Newest)", "Date (Oldest)", "Amount (High to Low)", "Amount (Low to High)"])
        
        filtered_income = []
        for row in all_income:
            income_id, source_name, category, amount, date_received, notes, is_recurring, created_at = row
            
            if filter_category != "All" and category != filter_category:
                continue
            
            if filter_recurring == "Recurring Only" and not is_recurring:
                continue
            elif filter_recurring == "One-time Only" and is_recurring:
                continue
            
            filtered_income.append(row)
        
        if sort_by == "Date (Oldest)":
            filtered_income = sorted(filtered_income, key=lambda x: x[4])
        elif sort_by == "Amount (High to Low)":
            filtered_income = sorted(filtered_income, key=lambda x: float(x[3]), reverse=True)
        elif sort_by == "Amount (Low to High)":
            filtered_income = sorted(filtered_income, key=lambda x: float(x[3]))
        
        st.markdown(f"**Showing {len(filtered_income)} records**")
        
        for row in filtered_income:
            income_id, source_name, category, amount, date_received, notes, is_recurring, created_at = row
            
            with st.expander(f"💵 {source_name} - ${float(amount):,.2f} ({date_received})"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Category:** {category}")
                    st.write(f"**Amount:** ${float(amount):,.2f}")
                with col2:
                    st.write(f"**Date:** {date_received}")
                    st.write(f"**Type:** {'🔄 Recurring' if is_recurring else '📌 One-time'}")
                with col3:
                    if notes:
                        st.write(f"**Notes:** {notes}")
                
                col_edit, col_delete = st.columns(2)
                with col_edit:
                    if st.button("✏️ Edit", key=f"edit_{income_id}"):
                        st.session_state[f"editing_{income_id}"] = True
                        st.rerun()
                
                with col_delete:
                    if st.button("🗑️ Delete", key=f"delete_{income_id}"):
                        delete_income(income_id)
                        st.success("Income record deleted!")
                        st.rerun()
                
                if st.session_state.get(f"editing_{income_id}", False):
                    st.markdown("---")
                    st.markdown("**Edit Income Record**")
                    
                    with st.form(f"edit_form_{income_id}"):
                        edit_source = st.text_input("Source", value=source_name, key=f"edit_source_{income_id}")
                        edit_category = st.selectbox("Category", INCOME_CATEGORIES, index=INCOME_CATEGORIES.index(category) if category in INCOME_CATEGORIES else 0, key=f"edit_cat_{income_id}")
                        edit_amount = st.number_input("Amount", value=float(amount), min_value=0.01, step=0.01, key=f"edit_amt_{income_id}")
                        edit_date = st.date_input("Date", value=date_received if isinstance(date_received, datetime.date) else datetime.datetime.strptime(str(date_received), "%Y-%m-%d").date(), key=f"edit_date_{income_id}")
                        edit_recurring = st.checkbox("Recurring?", value=bool(is_recurring), key=f"edit_rec_{income_id}")
                        edit_notes = st.text_area("Notes", value=notes or "", key=f"edit_notes_{income_id}")
                        
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.form_submit_button("💾 Save Changes"):
                                update_income(income_id, edit_source, edit_category, edit_amount, edit_date, edit_notes, edit_recurring)
                                del st.session_state[f"editing_{income_id}"]
                                st.success("Income updated!")
                                st.rerun()
                        with col_cancel:
                            if st.form_submit_button("❌ Cancel"):
                                del st.session_state[f"editing_{income_id}"]
                                st.rerun()

with tab4:
    st.subheader("💵 Tax Estimates & Planning")
    
    st.markdown("""
    > **Note:** These are estimates based on self-employment tax rates. 
    > Consult a tax professional for accurate tax planning.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### YTD Tax Breakdown")
        
        if ytd_income > 0:
            tax_data = calculate_tax_estimate(ytd_income)
            
            st.markdown(f"""
            | Item | Amount |
            |------|--------|
            | **Gross Side Income (YTD)** | ${ytd_income:,.2f} |
            | Self-Employment Tax (15.3%) | ${tax_data['self_employment_tax']:,.2f} |
            | Est. Federal Income Tax (22%) | ${tax_data['estimated_income_tax']:,.2f} |
            | **Total Estimated Tax** | **${tax_data['total_tax']:,.2f}** |
            | Effective Tax Rate | {tax_data['effective_rate']:.1f}% |
            | **Net After Tax** | **${ytd_income - tax_data['total_tax']:,.2f}** |
            """)
            
            st.markdown("### Quarterly Payment Schedule")
            quarterly = tax_data['quarterly_payment']
            
            today = datetime.date.today()
            year = today.year
            
            deadlines = [
                (f"Q1 {year}", datetime.date(year, 4, 15), quarterly),
                (f"Q2 {year}", datetime.date(year, 6, 15), quarterly),
                (f"Q3 {year}", datetime.date(year, 9, 15), quarterly),
                (f"Q4 {year}", datetime.date(year + 1, 1, 15), quarterly),
            ]
            
            for quarter, deadline, amount in deadlines:
                status = "✅ Past" if today > deadline else ("⚠️ Upcoming" if (deadline - today).days <= 30 else "📅 Future")
                st.markdown(f"- **{quarter}**: ${amount:,.2f} due by {deadline.strftime('%B %d, %Y')} {status}")
        else:
            st.info("No YTD income recorded. Add income to see tax estimates.")
    
    with col2:
        st.markdown("### 🧮 Tax Calculator")
        
        with st.form("tax_calculator"):
            calc_income = st.number_input("Annual Side Income ($)", min_value=0.0, value=ytd_income, step=100.0)
            calc_state_rate = st.slider("State Tax Rate (%)", min_value=0.0, max_value=15.0, value=5.5, step=0.5)
            calc_deductions = st.number_input("Estimated Deductions ($)", min_value=0.0, value=0.0, step=100.0)
            
            if st.form_submit_button("Calculate"):
                net_income = calc_income - calc_deductions
                if net_income > 0:
                    se_tax = net_income * 0.153
                    fed_tax = net_income * 0.22
                    state_tax = net_income * (calc_state_rate / 100)
                    total_tax = se_tax + fed_tax + state_tax
                    
                    st.markdown("### Results")
                    st.metric("Net Taxable Income", f"${net_income:,.2f}")
                    st.metric("Self-Employment Tax", f"${se_tax:,.2f}")
                    st.metric("Federal Tax (Est.)", f"${fed_tax:,.2f}")
                    st.metric("State Tax (Est.)", f"${state_tax:,.2f}")
                    st.metric("Total Tax Liability", f"${total_tax:,.2f}")
                    st.metric("Take-Home (After All Taxes)", f"${calc_income - total_tax:,.2f}")
                else:
                    st.warning("Net income after deductions is $0 or less.")
        
        st.markdown("### 💡 Tax Saving Tips")
        st.markdown("""
        - **Track all business expenses** - Tools, supplies, software
        - **Home office deduction** - If you have dedicated workspace
        - **Mileage deduction** - $0.67/mile for 2024
        - **SEP IRA contributions** - Up to 25% of net self-employment income
        - **Health insurance premiums** - Deductible for self-employed
        - **Quarterly payments** - Avoid penalties by paying on time
        """)

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; font-size: 0.8em;'>"
    "Side Income Tracker | Track • Analyze • Optimize"
    "</div>",
    unsafe_allow_html=True
)