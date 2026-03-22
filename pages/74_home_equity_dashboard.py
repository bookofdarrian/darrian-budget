import streamlit as st
import datetime
import json
from decimal import Decimal

st.set_page_config(page_title="Home Equity Dashboard", page_icon="🍑", layout="wide")

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
            CREATE TABLE IF NOT EXISTS properties (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                address TEXT NOT NULL,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                zillow_id TEXT,
                purchase_price DECIMAL(12,2),
                purchase_date DATE,
                property_type TEXT DEFAULT 'Single Family',
                bedrooms INTEGER,
                bathrooms DECIMAL(3,1),
                sqft INTEGER,
                lot_size INTEGER,
                year_built INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mortgages (
                id SERIAL PRIMARY KEY,
                property_id INTEGER REFERENCES properties(id) ON DELETE CASCADE,
                lender TEXT NOT NULL,
                loan_type TEXT DEFAULT 'Conventional',
                original_principal DECIMAL(12,2) NOT NULL,
                current_balance DECIMAL(12,2),
                interest_rate DECIMAL(5,3) NOT NULL,
                term_months INTEGER NOT NULL,
                start_date DATE NOT NULL,
                monthly_payment DECIMAL(10,2),
                escrow_amount DECIMAL(10,2) DEFAULT 0,
                pmi_amount DECIMAL(10,2) DEFAULT 0,
                is_primary BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS property_valuations (
                id SERIAL PRIMARY KEY,
                property_id INTEGER REFERENCES properties(id) ON DELETE CASCADE,
                valuation_date DATE NOT NULL,
                zestimate DECIMAL(12,2),
                rent_zestimate DECIMAL(10,2),
                source TEXT DEFAULT 'Manual',
                confidence_score DECIMAL(5,2),
                value_change DECIMAL(12,2),
                value_change_pct DECIMAL(6,3),
                raw_response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mortgage_payments (
                id SERIAL PRIMARY KEY,
                mortgage_id INTEGER REFERENCES mortgages(id) ON DELETE CASCADE,
                payment_date DATE NOT NULL,
                payment_amount DECIMAL(10,2) NOT NULL,
                principal_paid DECIMAL(10,2) NOT NULL,
                interest_paid DECIMAL(10,2) NOT NULL,
                escrow_paid DECIMAL(10,2) DEFAULT 0,
                extra_principal DECIMAL(10,2) DEFAULT 0,
                balance_after DECIMAL(12,2) NOT NULL,
                payment_number INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS equity_milestones (
                id SERIAL PRIMARY KEY,
                property_id INTEGER REFERENCES properties(id) ON DELETE CASCADE,
                milestone_type TEXT NOT NULL,
                milestone_value DECIMAL(5,2) NOT NULL,
                achieved_date DATE,
                notified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                address TEXT NOT NULL,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                zillow_id TEXT,
                purchase_price REAL,
                purchase_date TEXT,
                property_type TEXT DEFAULT 'Single Family',
                bedrooms INTEGER,
                bathrooms REAL,
                sqft INTEGER,
                lot_size INTEGER,
                year_built INTEGER,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mortgages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id INTEGER REFERENCES properties(id) ON DELETE CASCADE,
                lender TEXT NOT NULL,
                loan_type TEXT DEFAULT 'Conventional',
                original_principal REAL NOT NULL,
                current_balance REAL,
                interest_rate REAL NOT NULL,
                term_months INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                monthly_payment REAL,
                escrow_amount REAL DEFAULT 0,
                pmi_amount REAL DEFAULT 0,
                is_primary INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS property_valuations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id INTEGER REFERENCES properties(id) ON DELETE CASCADE,
                valuation_date TEXT NOT NULL,
                zestimate REAL,
                rent_zestimate REAL,
                source TEXT DEFAULT 'Manual',
                confidence_score REAL,
                value_change REAL,
                value_change_pct REAL,
                raw_response TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mortgage_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mortgage_id INTEGER REFERENCES mortgages(id) ON DELETE CASCADE,
                payment_date TEXT NOT NULL,
                payment_amount REAL NOT NULL,
                principal_paid REAL NOT NULL,
                interest_paid REAL NOT NULL,
                escrow_paid REAL DEFAULT 0,
                extra_principal REAL DEFAULT 0,
                balance_after REAL NOT NULL,
                payment_number INTEGER,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS equity_milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id INTEGER REFERENCES properties(id) ON DELETE CASCADE,
                milestone_type TEXT NOT NULL,
                milestone_value REAL NOT NULL,
                achieved_date TEXT,
                notified INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    cur.close()
    conn.close()

_ensure_tables()

# Sidebar
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

# Helper functions
def get_placeholder():
    return "%s" if USE_POSTGRES else "?"

def calculate_monthly_payment(principal, annual_rate, term_months):
    """Calculate monthly mortgage payment using amortization formula."""
    if annual_rate == 0:
        return principal / term_months
    monthly_rate = annual_rate / 100 / 12
    payment = principal * (monthly_rate * (1 + monthly_rate) ** term_months) / ((1 + monthly_rate) ** term_months - 1)
    return payment

def calculate_remaining_balance(original_principal, annual_rate, term_months, months_paid):
    """Calculate remaining mortgage balance after n payments."""
    if months_paid >= term_months:
        return 0
    if annual_rate == 0:
        return original_principal - (original_principal / term_months * months_paid)
    monthly_rate = annual_rate / 100 / 12
    balance = original_principal * ((1 + monthly_rate) ** term_months - (1 + monthly_rate) ** months_paid) / ((1 + monthly_rate) ** term_months - 1)
    return max(0, balance)

def calculate_amortization_schedule(principal, annual_rate, term_months, start_date, extra_monthly=0):
    """Generate full amortization schedule."""
    schedule = []
    balance = principal
    monthly_rate = annual_rate / 100 / 12 if annual_rate > 0 else 0
    monthly_payment = calculate_monthly_payment(principal, annual_rate, term_months)
    
    current_date = start_date
    payment_num = 0
    
    while balance > 0.01 and payment_num < term_months + 120:  # Safety limit
        payment_num += 1
        interest_payment = balance * monthly_rate
        principal_payment = min(monthly_payment - interest_payment + extra_monthly, balance)
        balance -= principal_payment
        
        schedule.append({
            'payment_num': payment_num,
            'date': current_date,
            'payment': monthly_payment + extra_monthly,
            'principal': principal_payment,
            'interest': interest_payment,
            'balance': max(0, balance)
        })
        
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    return schedule

def calculate_appreciation_cagr(purchase_price, current_value, years):
    """Calculate Compound Annual Growth Rate."""
    if years <= 0 or purchase_price <= 0:
        return 0
    cagr = ((current_value / purchase_price) ** (1 / years) - 1) * 100
    return cagr

def fetch_zillow_zestimate(address, city, state, zip_code):
    """Fetch Zestimate from Zillow via RapidAPI."""
    import requests
    
    api_key = get_setting("rapidapi_key")
    if not api_key:
        return None, "RapidAPI key not configured. Go to Settings to add your API key."
    
    try:
        url = "https://zillow-com1.p.rapidapi.com/property"
        full_address = f"{address}, {city}, {state} {zip_code}"
        
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com"
        }
        
        params = {"address": full_address}
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            zestimate = data.get("zestimate")
            rent_zestimate = data.get("rentZestimate")
            zillow_id = data.get("zpid")
            
            return {
                "zestimate": zestimate,
                "rent_zestimate": rent_zestimate,
                "zillow_id": zillow_id,
                "raw_response": json.dumps(data)
            }, None
        else:
            return None, f"API Error: {response.status_code}"
    except Exception as e:
        return None, f"Error fetching Zestimate: {str(e)}"

def get_user_id():
    return st.session_state.get("user_id", 1)

def get_properties():
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"SELECT * FROM properties WHERE user_id = {ph} ORDER BY created_at DESC", (get_user_id(),))
    cols = [desc[0] for desc in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return rows

def get_property_by_id(property_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"SELECT * FROM properties WHERE id = {ph}", (property_id,))
    cols = [desc[0] for desc in cur.description]
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(zip(cols, row)) if row else None

def get_mortgages_for_property(property_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"SELECT * FROM mortgages WHERE property_id = {ph} ORDER BY is_primary DESC, created_at", (property_id,))
    cols = [desc[0] for desc in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return rows

def get_valuations_for_property(property_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"SELECT * FROM property_valuations WHERE property_id = {ph} ORDER BY valuation_date DESC", (property_id,))
    cols = [desc[0] for desc in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return rows

def get_latest_valuation(property_id):
    valuations = get_valuations_for_property(property_id)
    return valuations[0] if valuations else None

def get_payments_for_mortgage(mortgage_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"SELECT * FROM mortgage_payments WHERE mortgage_id = {ph} ORDER BY payment_date DESC", (mortgage_id,))
    cols = [desc[0] for desc in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return rows

def add_property(data):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"""
        INSERT INTO properties (user_id, address, city, state, zip_code, zillow_id, purchase_price, 
                               purchase_date, property_type, bedrooms, bathrooms, sqft, lot_size, year_built, notes)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (get_user_id(), data['address'], data['city'], data['state'], data['zip_code'], 
          data.get('zillow_id'), data['purchase_price'], data['purchase_date'], data['property_type'],
          data.get('bedrooms'), data.get('bathrooms'), data.get('sqft'), data.get('lot_size'), 
          data.get('year_built'), data.get('notes')))
    
    if USE_POSTGRES:
        cur.execute("SELECT lastval()")
        property_id = cur.fetchone()[0]
    else:
        property_id = cur.lastrowid
    
    conn.commit()
    cur.close()
    conn.close()
    return property_id

def add_mortgage(data):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    monthly_payment = calculate_monthly_payment(
        float(data['original_principal']), 
        float(data['interest_rate']), 
        int(data['term_months'])
    )
    
    cur.execute(f"""
        INSERT INTO mortgages (property_id, lender, loan_type, original_principal, current_balance,
                              interest_rate, term_months, start_date, monthly_payment, escrow_amount, 
                              pmi_amount, is_primary)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (data['property_id'], data['lender'], data['loan_type'], data['original_principal'],
          data.get('current_balance', data['original_principal']), data['interest_rate'], 
          data['term_months'], data['start_date'], monthly_payment, data.get('escrow_amount', 0),
          data.get('pmi_amount', 0), data.get('is_primary', True)))
    
    conn.commit()
    cur.close()
    conn.close()

def add_valuation(data):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"""
        INSERT INTO property_valuations (property_id, valuation_date, zestimate, rent_zestimate, 
                                        source, confidence_score, value_change, value_change_pct, raw_response)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (data['property_id'], data['valuation_date'], data['zestimate'], data.get('rent_zestimate'),
          data.get('source', 'Manual'), data.get('confidence_score'), data.get('value_change'),
          data.get('value_change_pct'), data.get('raw_response')))
    conn.commit()
    cur.close()
    conn.close()

def add_payment(data):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"""
        INSERT INTO mortgage_payments (mortgage_id, payment_date, payment_amount, principal_paid,
                                      interest_paid, escrow_paid, extra_principal, balance_after, payment_number, notes)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (data['mortgage_id'], data['payment_date'], data['payment_amount'], data['principal_paid'],
          data['interest_paid'], data.get('escrow_paid', 0), data.get('extra_principal', 0),
          data['balance_after'], data.get('payment_number'), data.get('notes')))
    
    # Update current balance on mortgage
    cur.execute(f"UPDATE mortgages SET current_balance = {ph}, updated_at = CURRENT_TIMESTAMP WHERE id = {ph}",
                (data['balance_after'], data['mortgage_id']))
    
    conn.commit()
    cur.close()
    conn.close()

def delete_property(property_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    cur.execute(f"DELETE FROM properties WHERE id = {ph}", (property_id,))
    conn.commit()
    cur.close()
    conn.close()

def check_equity_milestones(property_id, ltv_ratio):
    """Check and record equity milestones (PMI removal at 80%, etc.)."""
    milestones = [
        (80, "PMI Removal Eligible (80% LTV)"),
        (75, "75% LTV Achieved"),
        (50, "50% Equity"),
        (25, "25% LTV - Strong Equity Position")
    ]
    
    conn = get_conn()
    cur = conn.cursor()
    ph = get_placeholder()
    
    for threshold, milestone_type in milestones:
        if ltv_ratio <= threshold:
            # Check if milestone already achieved
            cur.execute(f"""
                SELECT id FROM equity_milestones 
                WHERE property_id = {ph} AND milestone_value = {ph}
            """, (property_id, threshold))
            
            if not cur.fetchone():
                cur.execute(f"""
                    INSERT INTO equity_milestones (property_id, milestone_type, milestone_value, achieved_date)
                    VALUES ({ph}, {ph}, {ph}, {ph})
                """, (property_id, milestone_type, threshold, datetime.date.today().isoformat()))
    
    conn.commit()
    cur.close()
    conn.close()

# Main UI
st.title("🏠 Home Equity Dashboard")
st.markdown("Track home value, mortgage balance, and equity growth over time.")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🏡 Properties", "💰 Payments", "📈 Analytics"])

with tab1:
    properties = get_properties()
    
    if not properties:
        st.info("👋 Welcome! Add your first property to start tracking your home equity.")
        st.markdown("""
        **What you can track:**
        - 🏠 Home value via Zillow Zestimate or manual entry
        - 💵 Mortgage balance and payments
        - 📈 Equity growth and appreciation rate
        - 🎯 PMI removal eligibility (80% LTV milestone)
        """)
    else:
        # Property selector if multiple
        if len(properties) > 1:
            selected_prop = st.selectbox(
                "Select Property",
                options=properties,
                format_func=lambda x: f"{x['address']}, {x['city']}, {x['state']}"
            )
        else:
            selected_prop = properties[0]
        
        prop_id = selected_prop['id']
        mortgages = get_mortgages_for_property(prop_id)
        latest_val = get_latest_valuation(prop_id)
        
        # Calculate key metrics
        purchase_price = float(selected_prop['purchase_price'] or 0)
        current_value = float(latest_val['zestimate']) if latest_val else purchase_price
        
        total_mortgage_balance = sum(float(m['current_balance'] or m['original_principal'] or 0) for m in mortgages)
        equity = current_value - total_mortgage_balance
        equity_pct = (equity / current_value * 100) if current_value > 0 else 0
        ltv_ratio = (total_mortgage_balance / current_value * 100) if current_value > 0 else 0
        
        # Calculate appreciation
        purchase_date = selected_prop['purchase_date']
        if purchase_date:
            if isinstance(purchase_date, str):
                purchase_date = datetime.datetime.strptime(purchase_date, "%Y-%m-%d").date()
            years_owned = (datetime.date.today() - purchase_date).days / 365.25
            appreciation = current_value - purchase_price
            appreciation_pct = ((current_value / purchase_price) - 1) * 100 if purchase_price > 0 else 0
            cagr = calculate_appreciation_cagr(purchase_price, current_value, years_owned)
        else:
            years_owned = 0
            appreciation = 0
            appreciation_pct = 0
            cagr = 0
        
        # Check milestones
        check_equity_milestones(prop_id, ltv_ratio)
        
        # Dashboard cards
        st.subheader(f"📍 {selected_prop['address']}")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "🏠 Current Value",
                f"${current_value:,.0f}",
                f"+${appreciation:,.0f} ({appreciation_pct:.1f}%)" if appreciation > 0 else f"${appreciation:,.0f}"
            )
        
        with col2:
            st.metric(
                "💵 Mortgage Balance",
                f"${total_mortgage_balance:,.0f}",
                f"-${purchase_price - total_mortgage_balance:,.0f} paid" if mortgages else None
            )
        
        with col3:
            st.metric(
                "📈 Equity",
                f"${equity:,.0f}",
                f"{equity_pct:.1f}% of value"
            )
        
        with col4:
            pmi_status = "✅ PMI Eligible" if ltv_ratio <= 80 else f"🔸 {80 - ltv_ratio:.1f}% to PMI removal"
            st.metric(
                "📊 LTV Ratio",
                f"{ltv_ratio:.1f}%",
                pmi_status
            )
        
        st.markdown("---")
        
        # Appreciation metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📅 Years Owned", f"{years_owned:.1f}")
        
        with col2:
            st.metric("📈 Annual Appreciation (CAGR)", f"{cagr:.2f}%")
        
        with col3:
            if latest_val:
                val_date = latest_val['valuation_date']
                if isinstance(val_date, str):
                    val_date = datetime.datetime.strptime(val_date[:10], "%Y-%m-%d").date()
                st.metric("🔄 Last Updated", val_date.strftime("%b %d, %Y"))
        
        # Equity Growth Chart
        st.subheader("📈 Equity Growth Over Time")
        
        valuations = get_valuations_for_property(prop_id)
        
        if valuations and mortgages:
            import plotly.graph_objects as go
            
            # Get historical data
            val_dates = []
            val_values = []
            for v in reversed(valuations):
                vd = v['valuation_date']
                if isinstance(vd, str):
                    vd = datetime.datetime.strptime(vd[:10], "%Y-%m-%d").date()
                val_dates.append(vd)
                val_values.append(float(v['zestimate'] or 0))
            
            # Calculate mortgage balance at each valuation date
            primary_mortgage = mortgages[0] if mortgages else None
            mortgage_balances = []
            
            if primary_mortgage:
                start_date = primary_mortgage['start_date']
                if isinstance(start_date, str):
                    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
                
                for vd in val_dates:
                    months_elapsed = (vd.year - start_date.year) * 12 + (vd.month - start_date.month)
                    balance = calculate_remaining_balance(
                        float(primary_mortgage['original_principal']),
                        float(primary_mortgage['interest_rate']),
                        int(primary_mortgage['term_months']),
                        max(0, months_elapsed)
                    )
                    mortgage_balances.append(balance)
            else:
                mortgage_balances = [0] * len(val_dates)
            
            # Calculate equity at each point
            equity_values = [v - m for v, m in zip(val_values, mortgage_balances)]
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=val_dates,
                y=val_values,
                name="Home Value",
                line=dict(color="#2ecc71", width=3),
                fill='tozeroy',
                fillcolor='rgba(46, 204, 113, 0.1)'
            ))
            
            fig.add_trace(go.Scatter(
                x=val_dates,
                y=mortgage_balances,
                name="Mortgage Balance",
                line=dict(color="#e74c3c", width=3),
                fill='tozeroy',
                fillcolor='rgba(231, 76, 60, 0.1)'
            ))
            
            fig.add_trace(go.Scatter(
                x=val_dates,
                y=equity_values,
                name="Equity",
                line=dict(color="#3498db", width=3, dash='dash')
            ))
            
            fig.update_layout(
                title="Home Value vs Mortgage Balance",
                xaxis_title="Date",
                yaxis_title="Amount ($)",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                yaxis_tickformat="$,.0f"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Add valuations to see the equity growth chart.")
        
        # Quick actions
        st.subheader("⚡ Quick Actions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Fetch Zestimate", use_container_width=True):
                with st.spinner("Fetching from Zillow..."):
                    result, error = fetch_zillow_zestimate(
                        selected_prop['address'],
                        selected_prop['city'],
                        selected_prop['state'],
                        selected_prop['zip_code']
                    )
                    
                    if result:
                        prev_val = latest_val['zestimate'] if latest_val else purchase_price
                        value_change = result['zestimate'] - prev_val if result['zestimate'] else 0
                        value_change_pct = (value_change / prev_val * 100) if prev_val else 0
                        
                        add_valuation({
                            'property_id': prop_id,
                            'valuation_date': datetime.date.today().isoformat(),
                            'zestimate': result['zestimate'],
                            'rent_zestimate': result.get('rent_zestimate'),
                            'source': 'Zillow API',
                            'value_change': value_change,
                            'value_change_pct': value_change_pct,
                            'raw_response': result.get('raw_response')
                        })
                        
                        # Update zillow_id if we got one
                        if result.get('zillow_id'):
                            conn = get_conn()
                            cur = conn.cursor()
                            ph = get_placeholder()
                            cur.execute(f"UPDATE properties SET zillow_id = {ph} WHERE id = {ph}",
                                       (result['zillow_id'], prop_id))
                            conn.commit()
                            cur.close()
                            conn.close()