import streamlit as st
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Recurring Income Tracker", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS recurring_income (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                source_name VARCHAR(255) NOT NULL,
                amount DECIMAL(12,2) NOT NULL,
                frequency VARCHAR(50) NOT NULL,
                next_date DATE NOT NULL,
                category VARCHAR(100),
                is_active BOOLEAN DEFAULT TRUE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS income_entries (
                id SERIAL PRIMARY KEY,
                recurring_income_id INTEGER REFERENCES recurring_income(id) ON DELETE CASCADE,
                user_id INTEGER,
                amount DECIMAL(12,2) NOT NULL,
                received_date DATE NOT NULL,
                expected_amount DECIMAL(12,2),
                variance DECIMAL(12,2),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS recurring_income (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                source_name TEXT NOT NULL,
                amount REAL NOT NULL,
                frequency TEXT NOT NULL,
                next_date TEXT NOT NULL,
                category TEXT,
                is_active INTEGER DEFAULT 1,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS income_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recurring_income_id INTEGER,
                user_id INTEGER,
                amount REAL NOT NULL,
                received_date TEXT NOT NULL,
                expected_amount REAL,
                variance REAL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recurring_income_id) REFERENCES recurring_income(id) ON DELETE CASCADE
            )
        """)
    conn.commit()
    conn.close()

_ensure_tables()

FREQUENCY_OPTIONS = {
    "Weekly": 7,
    "Bi-Weekly": 14,
    "Semi-Monthly": 15,
    "Monthly": 30,
    "Quarterly": 90,
    "Annually": 365
}

INCOME_CATEGORIES = [
    "Salary/Wages",
    "Side Hustle",
    "Freelance",
    "Dividends",
    "Rental Income",
    "Interest",
    "Royalties",
    "Pension",
    "Social Security",
    "Other"
]

def get_next_occurrence(current_date, frequency):
    if frequency == "Weekly":
        return current_date + timedelta(days=7)
    elif frequency == "Bi-Weekly":
        return current_date + timedelta(days=14)
    elif frequency == "Semi-Monthly":
        if current_date.day <= 15:
            next_day = 15 if current_date.day < 15 else 1
            if next_day == 1:
                return (current_date + relativedelta(months=1)).replace(day=1)
            return current_date.replace(day=next_day)
        else:
            return (current_date + relativedelta(months=1)).replace(day=1)
    elif frequency == "Monthly":
        return current_date + relativedelta(months=1)
    elif frequency == "Quarterly":
        return current_date + relativedelta(months=3)
    elif frequency == "Annually":
        return current_date + relativedelta(years=1)
    return current_date + timedelta(days=30)

def calculate_monthly_amount(amount, frequency):
    if frequency == "Weekly":
        return amount * 52 / 12
    elif frequency == "Bi-Weekly":
        return amount * 26 / 12
    elif frequency == "Semi-Monthly":
        return amount * 2
    elif frequency == "Monthly":
        return amount
    elif frequency == "Quarterly":
        return amount / 3
    elif frequency == "Annually":
        return amount / 12
    return amount

def calculate_annual_amount(amount, frequency):
    if frequency == "Weekly":
        return amount * 52
    elif frequency == "Bi-Weekly":
        return amount * 26
    elif frequency == "Semi-Monthly":
        return amount * 24
    elif frequency == "Monthly":
        return amount * 12
    elif frequency == "Quarterly":
        return amount * 4
    elif frequency == "Annually":
        return amount
    return amount * 12

def get_all_income_sources(user_id=1):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        SELECT id, source_name, amount, frequency, next_date, category, is_active, notes, created_at
        FROM recurring_income
        WHERE user_id = {ph}
        ORDER BY is_active DESC, next_date ASC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def add_income_source(user_id, source_name, amount, frequency, next_date, category, notes=""):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        INSERT INTO recurring_income (user_id, source_name, amount, frequency, next_date, category, notes)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, source_name, amount, frequency, next_date, category, notes))
    conn.commit()
    conn.close()

def update_income_source(income_id, source_name, amount, frequency, next_date, category, is_active, notes):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    now = datetime.now().isoformat() if not USE_POSTGRES else datetime.now()
    cur.execute(f"""
        UPDATE recurring_income
        SET source_name = {ph}, amount = {ph}, frequency = {ph}, next_date = {ph},
            category = {ph}, is_active = {ph}, notes = {ph}, updated_at = {ph}
        WHERE id = {ph}
    """, (source_name, amount, frequency, next_date, category, is_active, notes, now, income_id))
    conn.commit()
    conn.close()

def delete_income_source(income_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"DELETE FROM recurring_income WHERE id = {ph}", (income_id,))
    conn.commit()
    conn.close()

def record_income_entry(recurring_income_id, user_id, amount, received_date, expected_amount, notes=""):
    variance = amount - expected_amount
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        INSERT INTO income_entries (recurring_income_id, user_id, amount, received_date, expected_amount, variance, notes)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (recurring_income_id, user_id, amount, received_date, expected_amount, variance, notes))
    conn.commit()
    conn.close()

def get_income_entries(user_id=1, income_id=None, days_back=90):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    start_date = (datetime.now() - timedelta(days=days_back)).date()
    if income_id:
        cur.execute(f"""
            SELECT ie.id, ie.recurring_income_id, ri.source_name, ie.amount, ie.received_date,
                   ie.expected_amount, ie.variance, ie.notes
            FROM income_entries ie
            JOIN recurring_income ri ON ie.recurring_income_id = ri.id
            WHERE ie.user_id = {ph} AND ie.recurring_income_id = {ph} AND ie.received_date >= {ph}
            ORDER BY ie.received_date DESC
        """, (user_id, income_id, start_date))
    else:
        cur.execute(f"""
            SELECT ie.id, ie.recurring_income_id, ri.source_name, ie.amount, ie.received_date,
                   ie.expected_amount, ie.variance, ie.notes
            FROM income_entries ie
            JOIN recurring_income ri ON ie.recurring_income_id = ri.id
            WHERE ie.user_id = {ph} AND ie.received_date >= {ph}
            ORDER BY ie.received_date DESC
        """, (user_id, start_date))
    rows = cur.fetchall()
    conn.close()
    return rows

def generate_forecast(income_sources, months_ahead=12):
    forecast_data = []
    today = datetime.now().date()
    end_date = today + relativedelta(months=months_ahead)
    
    for source in income_sources:
        if not source[6]:  # is_active
            continue
        source_id, source_name, amount, frequency, next_date, category = source[:6]
        
        if isinstance(next_date, str):
            current_date = datetime.strptime(next_date, "%Y-%m-%d").date()
        else:
            current_date = next_date
        
        while current_date <= end_date:
            if current_date >= today:
                forecast_data.append({
                    "source_id": source_id,
                    "source_name": source_name,
                    "amount": float(amount),
                    "date": current_date,
                    "category": category,
                    "month": current_date.strftime("%Y-%m")
                })
            current_date = get_next_occurrence(current_date, frequency)
    
    return forecast_data

def detect_variances(user_id=1, threshold_percent=10):
    entries = get_income_entries(user_id, days_back=180)
    variances = []
    for entry in entries:
        entry_id, recurring_id, source_name, amount, date, expected, variance, notes = entry
        if expected and expected > 0:
            variance_percent = abs(variance / expected * 100) if variance else 0
            if variance_percent >= threshold_percent:
                variances.append({
                    "source": source_name,
                    "date": date,
                    "expected": expected,
                    "actual": amount,
                    "variance": variance,
                    "variance_percent": variance_percent
                })
    return variances

# Sidebar
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

# Main Content
st.title("💵 Recurring Income Tracker")
st.markdown("Track and forecast your recurring income sources with automatic scheduling and variance alerts.")

user_id = 1
income_sources = get_all_income_sources(user_id)

# Summary Widgets
st.markdown("### 📊 Income Summary")
col1, col2, col3, col4 = st.columns(4)

total_monthly = 0
total_annual = 0
active_sources = 0

for source in income_sources:
    if source[6]:  # is_active
        active_sources += 1
        monthly = calculate_monthly_amount(float(source[2]), source[3])
        total_monthly += monthly
        total_annual += calculate_annual_amount(float(source[2]), source[3])

with col1:
    st.metric("Active Sources", active_sources)

with col2:
    st.metric("Monthly Income", f"${total_monthly:,.2f}")

with col3:
    st.metric("Annual Income", f"${total_annual:,.2f}")

with col4:
    upcoming_count = sum(1 for s in income_sources if s[6] and (
        (datetime.strptime(s[4], "%Y-%m-%d").date() if isinstance(s[4], str) else s[4]) - datetime.now().date()
    ).days <= 7)
    st.metric("Due This Week", upcoming_count)

st.markdown("---")

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Income Sources", "📆 Calendar View", "📈 12-Month Forecast", "📝 Record Entry", "⚠️ Variance Alerts"])

with tab1:
    st.markdown("### Manage Income Sources")
    
    with st.expander("➕ Add New Income Source", expanded=False):
        with st.form("add_income_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_source_name = st.text_input("Source Name", placeholder="e.g., Main Job Salary")
                new_amount = st.number_input("Amount ($)", min_value=0.0, step=100.0, value=0.0)
                new_frequency = st.selectbox("Frequency", options=list(FREQUENCY_OPTIONS.keys()))
            with col2:
                new_category = st.selectbox("Category", options=INCOME_CATEGORIES)
                new_next_date = st.date_input("Next Payment Date", value=datetime.now().date())
                new_notes = st.text_area("Notes (optional)", height=68)
            
            if st.form_submit_button("Add Income Source", type="primary"):
                if new_source_name and new_amount > 0:
                    add_income_source(user_id, new_source_name, new_amount, new_frequency, new_next_date, new_category, new_notes)
                    st.success(f"✅ Added '{new_source_name}' as recurring income!")
                    st.rerun()
                else:
                    st.error("Please enter a source name and amount greater than 0.")
    
    st.markdown("### Current Income Sources")
    
    if not income_sources:
        st.info("No recurring income sources yet. Add your first one above!")
    else:
        for source in income_sources:
            source_id, source_name, amount, frequency, next_date, category, is_active, notes, created_at = source
            
            if isinstance(next_date, str):
                next_date_obj = datetime.strptime(next_date, "%Y-%m-%d").date()
            else:
                next_date_obj = next_date
            
            days_until = (next_date_obj - datetime.now().date()).days
            status_color = "🟢" if is_active else "🔴"
            urgency = "🔔" if days_until <= 3 and is_active else ""
            
            monthly_equiv = calculate_monthly_amount(float(amount), frequency)
            
            with st.expander(f"{status_color} {source_name} - ${amount:,.2f} ({frequency}) {urgency}"):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.markdown(f"**Category:** {category}")
                    st.markdown(f"**Monthly Equivalent:** ${monthly_equiv:,.2f}")
                    st.markdown(f"**Annual Equivalent:** ${calculate_annual_amount(float(amount), frequency):,.2f}")
                
                with col2:
                    st.markdown(f"**Next Payment:** {next_date_obj.strftime('%B %d, %Y')}")
                    if days_until < 0:
                        st.markdown(f"**Status:** ⚠️ Overdue by {abs(days_until)} days")
                    elif days_until == 0:
                        st.markdown("**Status:** 📅 Due Today!")
                    else:
                        st.markdown(f"**Status:** {days_until} days until next payment")
                    if notes:
                        st.markdown(f"**Notes:** {notes}")
                
                with col3:
                    if st.button("🗑️ Delete", key=f"del_{source_id}"):
                        delete_income_source(source_id)
                        st.success("Deleted!")
                        st.rerun()
                
                st.markdown("---")
                st.markdown("**Edit Source:**")
                
                with st.form(f"edit_form_{source_id}"):
                    ecol1, ecol2 = st.columns(2)
                    with ecol1:
                        edit_name = st.text_input("Source Name", value=source_name, key=f"name_{source_id}")
                        edit_amount = st.number_input("Amount", value=float(amount), key=f"amt_{source_id}")
                        edit_freq = st.selectbox("Frequency", options=list(FREQUENCY_OPTIONS.keys()), 
                                                  index=list(FREQUENCY_OPTIONS.keys()).index(frequency) if frequency in FREQUENCY_OPTIONS else 0,
                                                  key=f"freq_{source_id}")
                    with ecol2:
                        edit_cat = st.selectbox("Category", options=INCOME_CATEGORIES,
                                                 index=INCOME_CATEGORIES.index(category) if category in INCOME_CATEGORIES else 0,
                                                 key=f"cat_{source_id}")
                        edit_next = st.date_input("Next Date", value=next_date_obj, key=f"next_{source_id}")
                        edit_active = st.checkbox("Active", value=bool(is_active), key=f"active_{source_id}")
                    edit_notes = st.text_area("Notes", value=notes or "", key=f"notes_{source_id}")
                    
                    if st.form_submit_button("Update"):
                        update_income_source(source_id, edit_name, edit_amount, edit_freq, edit_next, 
                                            edit_cat, 1 if edit_active else 0, edit_notes)
                        st.success("Updated!")
                        st.rerun()

with tab2:
    st.markdown("### 📆 Upcoming Income Calendar")
    
    view_months = st.slider("Months to View", 1, 6, 3)
    
    forecast = generate_forecast(income_sources, view_months)
    
    if not forecast:
        st.info("No upcoming income scheduled. Add income sources to see the calendar.")
    else:
        df_forecast = pd.DataFrame(forecast)
        df_forecast['date'] = pd.to_datetime(df_forecast['date'])
        df_forecast = df_forecast.sort_values('date')
        
        # Group by week
        df_forecast['week'] = df_forecast['date'].dt.isocalendar().week
        df_forecast['year'] = df_forecast['date'].dt.year
        
        # Calendar-like display
        current_month = None
        for _, row in df_forecast.iterrows():
            month_name = row['date'].strftime('%B %Y')
            if month_name != current_month:
                current_month = month_name
                st.markdown(f"#### {month_name}")
            
            days_away = (row['date'].date() - datetime.now().date()).days
            if days_away == 0:
                badge = "🔔 TODAY"
            elif days_away == 1:
                badge = "📅 Tomorrow"
            elif days_away <= 7:
                badge = f"⏰ In {days_away} days"
            else:
                badge = ""
            
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            with col1:
                st.markdown(f"**{row['date'].strftime('%a, %b %d')}** {badge}")
            with col2:
                st.markdown(f"{row['source_name']}")
            with col3:
                st.markdown(f"${row['amount']:,.2f}")
            with col4:
                st.markdown(f"*{row['category']}*")

with tab3:
    st.markdown("### 📈 12-Month Income Forecast")
    
    forecast = generate_forecast(income_sources, 12)
    
    if not forecast:
        st.info("Add income sources to see your 12-month forecast.")
    else:
        df_forecast = pd.DataFrame(forecast)
        
        # Monthly aggregation
        monthly_totals = df_forecast.groupby('month')['amount'].sum().reset_index()
        monthly_totals['month_date'] = pd.to_datetime(monthly_totals['month'] + '-01')
        monthly_totals = monthly_totals.sort_values('month_date')
        
        # Total forecast chart
        fig = px.bar(monthly_totals, x='month', y='amount',
                     title="Monthly Income Forecast",
                     labels={'amount': 'Income ($)', 'month': 'Month'},
                     color_discrete_sequence=['#2ecc71'])
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # By category breakdown
        category_monthly = df_forecast.groupby(['month', 'category'])['amount'].sum().reset_index()
        fig2 = px.bar(category_monthly, x='month', y='amount', color='category',
                      title="Income by Category",
                      labels={'amount': 'Income ($)', 'month': 'Month'})
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, use_container_width=True)
        
        # Summary stats
        st.markdown("### Forecast Summary")
        col1, col2, col3 = st.columns(3)
        
        total_forecast = df_forecast['amount'].sum()
        avg_monthly = monthly_totals['amount'].mean()
        
        with col1:
            st.metric("Total 12-Month Forecast", f"${total_forecast:,.2f}")
        with col2:
            st.metric("Average Monthly", f"${avg_monthly:,.2f}")
        with col3:
            # By source breakdown
            by_source = df_forecast.groupby('source_name')['amount'].sum().sort_values(ascending=False)
            if len(by_source) > 0:
                top_source = by_source.index[0]
                st.metric("Top Source", top_source, f"${by_source.iloc[0]:,.2f}")

with tab4:
    st.markdown("### 📝 Record Actual Income Entry")
    st.markdown("Track actual income received and compare against expected amounts.")
    
    active_sources = [s for s in income_sources if s[6]]
    
    if not active_sources:
        st.info("Add active income sources first to record entries.")
    else:
        with st.form("record_entry_form"):
            source_options = {f"{s[1]} (${s[2]:,.2f} {s[3]})": s[0] for s in active_sources}
            selected_source = st.selectbox("Income Source", options=list(source_options.keys()))
            
            source_id = source_options[selected_source]
            source_data = next(s for s in active_sources if s[0] == source_id)
            expected_amount = float(source_data[2])
            
            col1, col2 = st.columns(2)
            with col1:
                actual_amount = st.number_input("Actual Amount Received ($)", value=expected_amount, step=10.0)
                received_date = st.date_input("Date Received", value=datetime.now().date())
            with col2:
                st.markdown(f"**Expected:** ${expected_amount:,.2f}")
                variance = actual_amount - expected_amount
                variance_pct = (variance / expected_amount * 100) if expected_amount > 0 else 0
                if variance > 0:
                    st.markdown(f"**Variance:** +${variance:,.2f} (+{variance_pct:.1f}%) 📈")
                elif variance < 0:
                    st.markdown(f"**Variance:** -${abs(variance):,.2f} ({variance_pct:.1f}%) 📉")
                else:
                    st.markdown("**Variance:** $0.00 (As expected) ✅")
            
            entry_notes = st.text_area("Notes (optional)")
            
            if st.form_submit_button("Record Entry", type="primary"):
                record_income_entry(source_id, user_id, actual_amount, received_date, expected_amount, entry_notes)
                
                # Update next date
                new_next_date = get_next_occurrence(received_date, source_data[3])
                update_income_source(source_id, source_data[1], source_data[2], source_data[3],
                                    new_next_date, source_data[5], source_data[6], source_data[7])
                
                st.success(f"✅ Recorded ${actual_amount:,.2f} from {source_data[1]}!")
                st.rerun()
    
    st.markdown("---")
    st.markdown("### Recent Entries")
    
    entries = get_income_entries(user_id, days_back=90)
    
    if not entries:
        st.info("No income entries recorded yet.")
    else:
        df_entries = pd.DataFrame(entries, columns=['ID', 'Source ID', 'Source', 'Amount', 'Date', 'Expected', 'Variance', 'Notes'])
        df_entries['Date'] = pd.to_datetime(df_entries['Date']).dt.strftime('%Y-%m-%d')
        df_entries['Amount'] = df_entries['Amount'].apply(lambda x: f"${x:,.2f}")
        df_entries['Expected'] = df_entries['Expected'].apply(lambda x: f"${x:,.2f}" if x else "-")
        df_entries['Variance'] = df_entries['Variance'].apply(lambda x: f"${x:+,.2f}" if x else "$0.00")
        
        st.dataframe(df_entries[['Date', 'Source', 'Amount', 'Expected', 'Variance', 'Notes']], 
                     use_container_width=True, hide_index=True)

with tab5:
    st.markdown("### ⚠️ Variance Detection & Alerts")
    
    threshold = st.slider("Variance Threshold (%)", 1, 50, 10)
    
    variances = detect_variances(user_id, threshold)
    
    if not variances:
        st.success(f"✅ No significant variances detected (>{threshold}% difference)")
    else:
        st.warning(f"Found {len(variances)} income entries with variances above {threshold}%")
        
        for v in variances:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                with col1:
                    st.markdown(f"**{v['source']}**")
                    st.caption(f"Date: {v['date']}")
                with col2:
                    st.markdown(f"Expected: ${v['expected']:,.2f}")
                with col3:
                    st.markdown(f"Actual: ${v['actual']:,.2f}")
                with col4:
                    if v['variance'] > 0:
                        st.markdown(f"📈 +{v['variance_percent']:.1f}%")
                    else:
                        st.markdown(f"📉 {v['variance_percent']:.1f}%")
                st.markdown("---")
    
    # Variance trends
    entries = get_income_entries(user_id, days_back=180)
    if entries:
        df_entries = pd.DataFrame(entries, columns=['ID', 'Source ID', 'Source', 'Amount', 'Date', 'Expected', 'Variance', 'Notes'])
        df_entries['Date'] = pd.to_datetime(df_entries['Date'])
        df_entries['Variance'] = df_entries['Variance'].fillna(0)
        
        fig = px.scatter(df_entries, x='Date', y='Variance', color='Source',
                        title="Income Variance Over Time",
                        labels={'Variance': 'Variance ($)', 'Date': 'Date'})
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption("💵 Recurring Income Tracker | Track, forecast, and optimize your income streams")