import streamlit as st
import json
import datetime
import requests
from decimal import Decimal
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

st.set_page_config(page_title="Rent vs Buy Calculator", page_icon="🍑", layout="wide")

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
            CREATE TABLE IF NOT EXISTS rent_vs_buy_scenarios (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                scenario_name VARCHAR(255) NOT NULL,
                home_price DECIMAL(12, 2),
                down_payment_pct DECIMAL(5, 2),
                loan_term_years INTEGER,
                interest_rate DECIMAL(5, 3),
                property_tax_rate DECIMAL(5, 3),
                home_insurance_annual DECIMAL(10, 2),
                hoa_monthly DECIMAL(10, 2),
                maintenance_pct DECIMAL(5, 3),
                monthly_rent DECIMAL(10, 2),
                rent_increase_pct DECIMAL(5, 3),
                home_appreciation_pct DECIMAL(5, 3),
                investment_return_pct DECIMAL(5, 3),
                marginal_tax_rate DECIMAL(5, 3),
                time_horizon_years INTEGER,
                annual_income DECIMAL(12, 2),
                closing_costs_pct DECIMAL(5, 3),
                selling_costs_pct DECIMAL(5, 3),
                atlanta_neighborhood VARCHAR(255),
                recommendation TEXT,
                break_even_years DECIMAL(5, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS zillow_market_cache (
                id SERIAL PRIMARY KEY,
                neighborhood VARCHAR(255) NOT NULL,
                median_home_price DECIMAL(12, 2),
                median_rent DECIMAL(10, 2),
                price_to_rent_ratio DECIMAL(5, 2),
                yoy_appreciation DECIMAL(5, 3),
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(neighborhood)
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rent_vs_buy_scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                scenario_name TEXT NOT NULL,
                home_price REAL,
                down_payment_pct REAL,
                loan_term_years INTEGER,
                interest_rate REAL,
                property_tax_rate REAL,
                home_insurance_annual REAL,
                hoa_monthly REAL,
                maintenance_pct REAL,
                monthly_rent REAL,
                rent_increase_pct REAL,
                home_appreciation_pct REAL,
                investment_return_pct REAL,
                marginal_tax_rate REAL,
                time_horizon_years INTEGER,
                annual_income REAL,
                closing_costs_pct REAL,
                selling_costs_pct REAL,
                atlanta_neighborhood TEXT,
                recommendation TEXT,
                break_even_years REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS zillow_market_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                neighborhood TEXT NOT NULL UNIQUE,
                median_home_price REAL,
                median_rent REAL,
                price_to_rent_ratio REAL,
                yoy_appreciation REAL,
                fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    conn.close()

_ensure_tables()

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

# Atlanta neighborhoods with market data (simulated Zillow data)
ATLANTA_NEIGHBORHOODS = {
    "Midtown": {"median_price": 485000, "median_rent": 2400, "appreciation": 4.2},
    "Buckhead": {"median_price": 650000, "median_rent": 2800, "appreciation": 3.8},
    "Virginia-Highland": {"median_price": 575000, "median_rent": 2500, "appreciation": 4.5},
    "Decatur": {"median_price": 425000, "median_rent": 2100, "appreciation": 4.0},
    "East Atlanta": {"median_price": 380000, "median_rent": 1900, "appreciation": 5.1},
    "Grant Park": {"median_price": 450000, "median_rent": 2200, "appreciation": 4.8},
    "Kirkwood": {"median_price": 410000, "median_rent": 2000, "appreciation": 4.6},
    "Inman Park": {"median_price": 625000, "median_rent": 2700, "appreciation": 4.3},
    "Old Fourth Ward": {"median_price": 520000, "median_rent": 2450, "appreciation": 4.7},
    "West End": {"median_price": 320000, "median_rent": 1600, "appreciation": 5.5},
}

def calculate_mortgage_payment(principal, annual_rate, years):
    """Calculate monthly mortgage payment."""
    if annual_rate == 0:
        return principal / (years * 12)
    monthly_rate = annual_rate / 100 / 12
    num_payments = years * 12
    payment = principal * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
    return payment

def calculate_rent_vs_buy(params):
    """Calculate rent vs buy comparison over time horizon."""
    home_price = params["home_price"]
    down_payment = home_price * params["down_payment_pct"] / 100
    loan_amount = home_price - down_payment
    
    monthly_mortgage = calculate_mortgage_payment(
        loan_amount, 
        params["interest_rate"], 
        params["loan_term_years"]
    )
    
    closing_costs = home_price * params["closing_costs_pct"] / 100
    initial_buy_cost = down_payment + closing_costs
    
    results = []
    buy_total = initial_buy_cost
    rent_total = 0
    home_value = home_price
    loan_balance = loan_amount
    investment_balance = initial_buy_cost  # What renter invests instead
    
    current_rent = params["monthly_rent"]
    monthly_rate = params["interest_rate"] / 100 / 12
    
    for year in range(1, params["time_horizon_years"] + 1):
        # Annual costs for buying
        property_tax = home_value * params["property_tax_rate"] / 100
        insurance = params["home_insurance_annual"]
        hoa = params["hoa_monthly"] * 12
        maintenance = home_value * params["maintenance_pct"] / 100
        
        annual_mortgage = monthly_mortgage * 12
        
        # Calculate interest vs principal for the year
        interest_paid = 0
        principal_paid = 0
        for month in range(12):
            if loan_balance > 0:
                interest = loan_balance * monthly_rate
                principal = min(monthly_mortgage - interest, loan_balance)
                interest_paid += interest
                principal_paid += principal
                loan_balance -= principal
        
        annual_buy_cost = annual_mortgage + property_tax + insurance + hoa + maintenance
        buy_total += annual_buy_cost
        
        # Home appreciation
        home_value *= (1 + params["home_appreciation_pct"] / 100)
        
        # Annual costs for renting
        annual_rent = current_rent * 12
        rent_total += annual_rent
        current_rent *= (1 + params["rent_increase_pct"] / 100)
        
        # Investment growth for renter
        monthly_savings = (annual_buy_cost - annual_rent) / 12
        for month in range(12):
            investment_balance *= (1 + params["investment_return_pct"] / 100 / 12)
            if monthly_savings > 0:
                investment_balance += monthly_savings
        
        # Calculate equity
        equity = home_value - loan_balance
        selling_costs = home_value * params["selling_costs_pct"] / 100
        net_equity = equity - selling_costs
        
        # Net worth comparison
        buy_net_worth = net_equity
        rent_net_worth = investment_balance
        
        results.append({
            "year": year,
            "buy_total_cost": buy_total,
            "rent_total_cost": rent_total,
            "home_value": home_value,
            "loan_balance": loan_balance,
            "equity": equity,
            "net_equity": net_equity,
            "investment_balance": investment_balance,
            "buy_net_worth": buy_net_worth,
            "rent_net_worth": rent_net_worth,
            "annual_buy_cost": annual_buy_cost,
            "annual_rent_cost": annual_rent,
            "monthly_mortgage": monthly_mortgage,
            "current_rent": current_rent / (1 + params["rent_increase_pct"] / 100),
        })
    
    return results

def find_break_even(results):
    """Find the year when buying becomes better than renting."""
    for r in results:
        if r["buy_net_worth"] > r["rent_net_worth"]:
            return r["year"]
    return None

def get_recommendation(results, break_even_year, time_horizon):
    """Generate a recommendation based on the analysis."""
    final = results[-1]
    diff = final["buy_net_worth"] - final["rent_net_worth"]
    
    if break_even_year is None:
        return f"🏠 **Renting appears better** for your {time_horizon}-year horizon. You'd be ${abs(diff):,.0f} better off renting and investing the difference."
    elif break_even_year <= 3:
        return f"🏡 **Buying is strongly recommended!** Break-even in just {break_even_year} years. You'd be ${diff:,.0f} better off buying."
    elif break_even_year <= 5:
        return f"🏡 **Buying is recommended** if you plan to stay {break_even_year}+ years. You'd be ${diff:,.0f} better off buying."
    elif break_even_year <= time_horizon:
        return f"⚖️ **Consider carefully.** Break-even at year {break_even_year}. Buying slightly better by ${diff:,.0f} over {time_horizon} years."
    else:
        return f"🏠 **Renting may be better** for your timeline. Break-even would take {break_even_year} years."

# Main UI
st.title("🏠 Rent vs Buy Calculator")
st.markdown("### Atlanta Metro Area Analysis")

# Tabs for different sections
tab1, tab2, tab3 = st.tabs(["📊 Calculator", "📈 Market Data", "💾 Saved Scenarios"])

with tab1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🏡 Home Purchase Details")
        
        neighborhood = st.selectbox(
            "Atlanta Neighborhood",
            options=["Custom"] + list(ATLANTA_NEIGHBORHOODS.keys()),
            index=0
        )
        
        if neighborhood != "Custom":
            default_price = ATLANTA_NEIGHBORHOODS[neighborhood]["median_price"]
            default_rent = ATLANTA_NEIGHBORHOODS[neighborhood]["median_rent"]
            default_appreciation = ATLANTA_NEIGHBORHOODS[neighborhood]["appreciation"]
        else:
            default_price = 400000
            default_rent = 2000
            default_appreciation = 4.0
        
        home_price = st.number_input(
            "Home Price ($)", 
            min_value=50000, 
            max_value=2000000, 
            value=default_price, 
            step=10000
        )
        
        down_payment_pct = st.slider(
            "Down Payment (%)", 
            min_value=0, 
            max_value=50, 
            value=20
        )
        
        loan_term_years = st.selectbox(
            "Loan Term (Years)", 
            options=[15, 20, 30], 
            index=2
        )
        
        interest_rate = st.number_input(
            "Interest Rate (%)", 
            value=6.75, 
            step=0.125, 
            min_value=0.0, 
            max_value=15.0
        )
        
        st.subheader("🏠 Ownership Costs")
        
        property_tax_rate = st.number_input(
            "Property Tax Rate (%)", 
            value=1.0, 
            step=0.1, 
            min_value=0.0, 
            max_value=5.0
        )
        
        home_insurance_annual = st.number_input(
            "Home Insurance (Annual $)", 
            value=1500, 
            step=100
        )
        
        hoa_monthly = st.number_input(
            "HOA (Monthly $)", 
            value=0, 
            step=50
        )
        
        maintenance_pct = st.number_input(
            "Maintenance (% of home value/year)", 
            value=1.0, 
            step=0.1, 
            min_value=0.0, 
            max_value=5.0
        )
    
    with col2:
        st.subheader("🏢 Rental Details")
        
        monthly_rent = st.number_input(
            "Monthly Rent ($)", 
            value=default_rent, 
            step=50
        )
        
        rent_increase_pct = st.number_input(
            "Annual Rent Increase (%)", 
            value=3.0, 
            step=0.5, 
            min_value=0.0, 
            max_value=10.0
        )
        
        st.subheader("📈 Market Assumptions")
        
        home_appreciation_pct = st.number_input(
            "Home Appreciation (%/year)", 
            value=default_appreciation, 
            step=0.5, 
            min_value=-5.0, 
            max_value=15.0
        )
        
        investment_return_pct = st.number_input(
            "Investment Return (%/year)", 
            value=7.0, 
            step=0.5, 
            min_value=0.0, 
            max_value=15.0
        )
        
        st.subheader("⚙️ Other Parameters")
        
        time_horizon_years = st.slider(
            "Time Horizon (Years)", 
            min_value=1, 
            max_value=30, 
            value=10
        )
        
        closing_costs_pct = st.number_input(
            "Closing Costs (%)", 
            value=3.0, 
            step=0.5, 
            min_value=0.0, 
            max_value=10.0
        )
        
        selling_costs_pct = st.number_input(
            "Selling Costs (%)", 
            value=6.0, 
            step=0.5, 
            min_value=0.0, 
            max_value=10.0
        )
    
    # Calculate button
    if st.button("🧮 Calculate", type="primary", use_container_width=True):
        params = {
            "home_price": home_price,
            "down_payment_pct": down_payment_pct,
            "loan_term_years": loan_term_years,
            "interest_rate": interest_rate,
            "property_tax_rate": property_tax_rate,
            "home_insurance_annual": home_insurance_annual,
            "hoa_monthly": hoa_monthly,
            "maintenance_pct": maintenance_pct,
            "monthly_rent": monthly_rent,
            "rent_increase_pct": rent_increase_pct,
            "home_appreciation_pct": home_appreciation_pct,
            "investment_return_pct": investment_return_pct,
            "time_horizon_years": time_horizon_years,
            "closing_costs_pct": closing_costs_pct,
            "selling_costs_pct": selling_costs_pct,
        }
        
        results = calculate_rent_vs_buy(params)
        break_even_year = find_break_even(results)
        recommendation = get_recommendation(results, break_even_year, time_horizon_years)
        
        st.markdown("---")
        st.subheader("📊 Results")
        
        # Recommendation
        st.info(recommendation)
        
        # Key metrics
        final = results[-1]
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Monthly Mortgage", 
                f"${final['monthly_mortgage']:,.0f}",
                delta=f"${final['monthly_mortgage'] - monthly_rent:,.0f} vs rent"
            )
        
        with col2:
            st.metric(
                "Home Value (Year {})".format(time_horizon_years),
                f"${final['home_value']:,.0f}",
                delta=f"+${final['home_value'] - home_price:,.0f}"
            )
        
        with col3:
            st.metric(
                "Net Equity (Year {})".format(time_horizon_years),
                f"${final['net_equity']:,.0f}"
            )
        
        with col4:
            st.metric(
                "Break-Even Year",
                f"Year {break_even_year}" if break_even_year else "N/A"
            )
        
        # Charts
        df = pd.DataFrame(results)
        
        # Net worth comparison chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["year"], 
            y=df["buy_net_worth"],
            name="Buy Net Worth",
            line=dict(color="#2E86AB", width=3)
        ))
        fig.add_trace(go.Scatter(
            x=df["year"], 
            y=df["rent_net_worth"],
            name="Rent + Invest Net Worth",
            line=dict(color="#A23B72", width=3)
        ))
        fig.update_layout(
            title="Net Worth Comparison Over Time",
            xaxis_title="Year",
            yaxis_title="Net Worth ($)",
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Cost comparison chart
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=df["year"],
            y=df["annual_buy_cost"],
            name="Annual Buy Cost",
            marker_color="#2E86AB"
        ))
        fig2.add_trace(go.Bar(
            x=df["year"],
            y=df["annual_rent_cost"],
            name="Annual Rent Cost",
            marker_color="#A23B72"
        ))
        fig2.update_layout(
            title="Annual Cost Comparison",
            xaxis_title="Year",
            yaxis_title="Annual Cost ($)",
            barmode="group"
        )
        st.plotly_chart(fig2, use_container_width=True)
        
        # Detailed table
        with st.expander("📋 Detailed Year-by-Year Breakdown"):
            display_df = df[["year", "annual_buy_cost", "annual_rent_cost", "home_value", "loan_balance", "net_equity", "investment_balance", "buy_net_worth", "rent_net_worth"]].copy()
            display_df.columns = ["Year", "Buy Cost", "Rent Cost", "Home Value", "Loan Balance", "Net Equity", "Investment Balance", "Buy Net Worth", "Rent Net Worth"]
            for col in display_df.columns[1:]:
                display_df[col] = display_df[col].apply(lambda x: f"${x:,.0f}")
            st.dataframe(display_df, use_container_width=True)

with tab2:
    st.subheader("📈 Atlanta Neighborhood Market Data")
    st.markdown("*Data is simulated for demonstration purposes*")
    
    market_data = []
    for name, data in ATLANTA_NEIGHBORHOODS.items():
        price_to_rent = data["median_price"] / (data["median_rent"] * 12)
        market_data.append({
            "Neighborhood": name,
            "Median Home Price": f"${data['median_price']:,}",
            "Median Rent": f"${data['median_rent']:,}/mo",
            "Price-to-Rent Ratio": f"{price_to_rent:.1f}",
            "YoY Appreciation": f"{data['appreciation']}%"
        })
    
    market_df = pd.DataFrame(market_data)
    st.dataframe(market_df, use_container_width=True)
    
    st.markdown("""
    ### 📖 Understanding Price-to-Rent Ratio
    - **Under 15**: Buying is typically favorable
    - **15-20**: Consider both options carefully
    - **Over 20**: Renting may be more economical
    """)

with tab3:
    st.subheader("💾 Saved Scenarios")
    st.info("Save your scenarios to compare different options over time.")
    
    # Placeholder for saved scenarios
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM rent_vs_buy_scenarios ORDER BY created_at DESC LIMIT 10")
    scenarios = cur.fetchall()
    conn.close()
    
    if scenarios:
        for scenario in scenarios:
            st.write(f"**{scenario[2]}** - Created: {scenario[-2]}")
    else:
        st.write("No saved scenarios yet. Run a calculation and save it!")