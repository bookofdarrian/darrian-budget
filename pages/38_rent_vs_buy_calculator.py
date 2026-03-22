import streamlit as st
import requests
import json
import math
from datetime import datetime, date
from typing import Optional, Dict, Any, List, Tuple
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Rent vs Buy Calculator", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

# Sidebar navigation
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()


def _ensure_tables():
    """Create rent_vs_buy_scenarios table if not exists."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rent_vs_buy_scenarios (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                scenario_name VARCHAR(255) NOT NULL,
                home_price DECIMAL(12,2),
                down_payment_pct DECIMAL(5,2),
                mortgage_rate DECIMAL(5,3),
                loan_term_years INTEGER,
                property_tax_rate DECIMAL(5,3),
                home_insurance_annual DECIMAL(10,2),
                hoa_monthly DECIMAL(10,2),
                maintenance_pct DECIMAL(5,3),
                monthly_rent DECIMAL(10,2),
                rent_increase_pct DECIMAL(5,3),
                home_appreciation_pct DECIMAL(5,3),
                investment_return_pct DECIMAL(5,3),
                time_horizon_years INTEGER,
                closing_costs_pct DECIMAL(5,3),
                selling_costs_pct DECIMAL(5,3),
                marginal_tax_rate DECIMAL(5,3),
                atlanta_neighborhood VARCHAR(255),
                zillow_data JSONB,
                break_even_year INTEGER,
                analysis_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                mortgage_rate REAL,
                loan_term_years INTEGER,
                property_tax_rate REAL,
                home_insurance_annual REAL,
                hoa_monthly REAL,
                maintenance_pct REAL,
                monthly_rent REAL,
                rent_increase_pct REAL,
                home_appreciation_pct REAL,
                investment_return_pct REAL,
                time_horizon_years INTEGER,
                closing_costs_pct REAL,
                selling_costs_pct REAL,
                marginal_tax_rate REAL,
                atlanta_neighborhood TEXT,
                zillow_data TEXT,
                break_even_year INTEGER,
                analysis_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    cur.close()
    conn.close()


def get_zillow_market_data(neighborhood: str = "Atlanta") -> Dict[str, Any]:
    """
    Fetch Atlanta market data from Zillow API or return cached/default data.
    In production, this would use the Zillow API with proper authentication.
    """
    # Atlanta-specific market data (as of 2026)
    atlanta_neighborhoods = {
        "Atlanta (Metro)": {
            "median_home_price": 425000,
            "median_rent": 2100,
            "appreciation_rate": 4.2,
            "rent_growth_rate": 3.5,
            "property_tax_rate": 1.15,
            "avg_days_on_market": 32
        },
        "Buckhead": {
            "median_home_price": 750000,
            "median_rent": 2800,
            "appreciation_rate": 3.8,
            "rent_growth_rate": 3.2,
            "property_tax_rate": 1.18,
            "avg_days_on_market": 45
        },
        "Midtown": {
            "median_home_price": 550000,
            "median_rent": 2400,
            "appreciation_rate": 4.5,
            "rent_growth_rate": 3.8,
            "property_tax_rate": 1.15,
            "avg_days_on_market": 28
        },
        "Virginia-Highland": {
            "median_home_price": 680000,
            "median_rent": 2600,
            "appreciation_rate": 4.0,
            "rent_growth_rate": 3.5,
            "property_tax_rate": 1.15,
            "avg_days_on_market": 35
        }
    }
    
    return atlanta_neighborhoods.get(neighborhood, atlanta_neighborhoods["Atlanta (Metro)"])


def calculate_mortgage_payment(principal: float, annual_rate: float, years: int) -> float:
    """Calculate monthly mortgage payment."""
    if annual_rate == 0:
        return principal / (years * 12)
    monthly_rate = annual_rate / 100 / 12
    num_payments = years * 12
    payment = principal * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
    return payment


def run_rent_vs_buy_analysis(params: Dict[str, Any]) -> Dict[str, Any]:
    """Run the rent vs buy analysis and return results."""
    home_price = params["home_price"]
    down_payment_pct = params["down_payment_pct"]
    mortgage_rate = params["mortgage_rate"]
    loan_term_years = params["loan_term_years"]
    property_tax_rate = params["property_tax_rate"]
    home_insurance_annual = params["home_insurance_annual"]
    hoa_monthly = params["hoa_monthly"]
    maintenance_pct = params["maintenance_pct"]
    monthly_rent = params["monthly_rent"]
    rent_increase_pct = params["rent_increase_pct"]
    home_appreciation_pct = params["home_appreciation_pct"]
    investment_return_pct = params["investment_return_pct"]
    time_horizon_years = params["time_horizon_years"]
    closing_costs_pct = params["closing_costs_pct"]
    selling_costs_pct = params["selling_costs_pct"]
    
    down_payment = home_price * down_payment_pct / 100
    loan_amount = home_price - down_payment
    closing_costs = home_price * closing_costs_pct / 100
    
    monthly_mortgage = calculate_mortgage_payment(loan_amount, mortgage_rate, loan_term_years)
    monthly_property_tax = home_price * property_tax_rate / 100 / 12
    monthly_insurance = home_insurance_annual / 12
    monthly_maintenance = home_price * maintenance_pct / 100 / 12
    
    total_monthly_ownership = monthly_mortgage + monthly_property_tax + monthly_insurance + monthly_maintenance + hoa_monthly
    
    buy_costs = []
    rent_costs = []
    buy_equity = []
    rent_investment = []
    
    current_rent = monthly_rent
    current_home_value = home_price
    remaining_loan = loan_amount
    renter_investment = down_payment + closing_costs
    
    for year in range(1, time_horizon_years + 1):
        annual_rent = current_rent * 12
        rent_costs.append(annual_rent)
        
        annual_ownership = total_monthly_ownership * 12
        buy_costs.append(annual_ownership)
        
        current_home_value *= (1 + home_appreciation_pct / 100)
        buy_equity.append(current_home_value - remaining_loan)
        
        renter_investment *= (1 + investment_return_pct / 100)
        monthly_savings = total_monthly_ownership - current_rent
        if monthly_savings > 0:
            renter_investment += monthly_savings * 12 * (1 + investment_return_pct / 100 / 2)
        rent_investment.append(renter_investment)
        
        current_rent *= (1 + rent_increase_pct / 100)
    
    final_home_value = current_home_value
    selling_costs = final_home_value * selling_costs_pct / 100
    net_proceeds_buying = final_home_value - remaining_loan - selling_costs
    net_proceeds_renting = renter_investment
    
    break_even_year = None
    for i, (equity, investment) in enumerate(zip(buy_equity, rent_investment)):
        if equity > investment:
            break_even_year = i + 1
            break
    
    return {
        "buy_costs": buy_costs,
        "rent_costs": rent_costs,
        "buy_equity": buy_equity,
        "rent_investment": rent_investment,
        "net_proceeds_buying": net_proceeds_buying,
        "net_proceeds_renting": net_proceeds_renting,
        "break_even_year": break_even_year,
        "total_monthly_ownership": total_monthly_ownership,
        "monthly_mortgage": monthly_mortgage
    }


# Main UI
st.title("🏠 Rent vs Buy Calculator")
st.markdown("Compare the financial impact of renting versus buying a home in Atlanta.")

_ensure_tables()

# Input section
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏠 Home Purchase Details")
    
    neighborhood = st.selectbox(
        "Atlanta Neighborhood",
        ["Atlanta (Metro)", "Buckhead", "Midtown", "Virginia-Highland"]
    )
    
    market_data = get_zillow_market_data(neighborhood)
    
    home_price = st.number_input(
        "Home Price ($)",
        min_value=50000,
        max_value=5000000,
        value=market_data["median_home_price"],
        step=10000
    )
    
    down_payment_pct = st.slider(
        "Down Payment (%)",
        min_value=0.0,
        max_value=100.0,
        value=20.0,
        step=0.5
    )
    
    mortgage_rate = st.slider(
        "Mortgage Rate (%)",
        min_value=0.0,
        max_value=15.0,
        value=6.5,
        step=0.125
    )
    
    loan_term_years = st.selectbox(
        "Loan Term (Years)",
        [15, 20, 30],
        index=2
    )

with col2:
    st.subheader("🏢 Rental Details")
    
    monthly_rent = st.number_input(
        "Monthly Rent ($)",
        min_value=500,
        max_value=20000,
        value=market_data["median_rent"],
        step=50
    )
    
    rent_increase_pct = st.slider(
        "Annual Rent Increase (%)",
        min_value=0.0,
        max_value=10.0,
        value=market_data["rent_growth_rate"],
        step=0.1
    )
    
    investment_return_pct = st.slider(
        "Investment Return (%)",
        min_value=0.0,
        max_value=15.0,
        value=7.0,
        step=0.5
    )
    
    time_horizon_years = st.slider(
        "Time Horizon (Years)",
        min_value=1,
        max_value=30,
        value=10,
        step=1
    )

# Additional costs section
with st.expander("📊 Additional Costs & Assumptions"):
    col3, col4 = st.columns(2)
    
    with col3:
        property_tax_rate = st.slider(
            "Property Tax Rate (%)",
            min_value=0.0,
            max_value=5.0,
            value=market_data["property_tax_rate"],
            step=0.05
        )
        
        home_insurance_annual = st.number_input(
            "Annual Home Insurance ($)",
            min_value=0,
            max_value=20000,
            value=1800,
            step=100
        )
        
        hoa_monthly = st.number_input(
            "Monthly HOA ($)",
            min_value=0,
            max_value=2000,
            value=0,
            step=25
        )
    
    with col4:
        maintenance_pct = st.slider(
            "Annual Maintenance (%)",
            min_value=0.0,
            max_value=5.0,
            value=1.0,
            step=0.1
        )
        
        home_appreciation_pct = st.slider(
            "Home Appreciation (%)",
            min_value=-5.0,
            max_value=15.0,
            value=market_data["appreciation_rate"],
            step=0.1
        )
        
        closing_costs_pct = st.slider(
            "Closing Costs (%)",
            min_value=0.0,
            max_value=10.0,
            value=3.0,
            step=0.5
        )
        
        selling_costs_pct = st.slider(
            "Selling Costs (%)",
            min_value=0.0,
            max_value=10.0,
            value=6.0,
            step=0.5
        )

# Run analysis
if st.button("🔍 Analyze", type="primary"):
    params = {
        "home_price": home_price,
        "down_payment_pct": down_payment_pct,
        "mortgage_rate": mortgage_rate,
        "loan_term_years": loan_term_years,
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
        "selling_costs_pct": selling_costs_pct
    }
    
    results = run_rent_vs_buy_analysis(params)
    
    # Display results
    st.subheader("📈 Results")
    
    col_r1, col_r2, col_r3 = st.columns(3)
    
    with col_r1:
        st.metric(
            "Monthly Ownership Cost",
            f"${results['total_monthly_ownership']:,.0f}"
        )
    
    with col_r2:
        st.metric(
            "Net Proceeds (Buying)",
            f"${results['net_proceeds_buying']:,.0f}"
        )
    
    with col_r3:
        st.metric(
            "Net Proceeds (Renting)",
            f"${results['net_proceeds_renting']:,.0f}"
        )
    
    # Recommendation
    if results['net_proceeds_buying'] > results['net_proceeds_renting']:
        st.success(f"🏠 **Buying is better** by ${results['net_proceeds_buying'] - results['net_proceeds_renting']:,.0f} over {time_horizon_years} years.")
    else:
        st.info(f"🏢 **Renting is better** by ${results['net_proceeds_renting'] - results['net_proceeds_buying']:,.0f} over {time_horizon_years} years.")
    
    if results['break_even_year']:
        st.write(f"📅 Break-even year: **Year {results['break_even_year']}**")
    
    # Chart
    fig = go.Figure()
    years = list(range(1, time_horizon_years + 1))
    
    fig.add_trace(go.Scatter(x=years, y=results['buy_equity'], name='Home Equity', mode='lines'))
    fig.add_trace(go.Scatter(x=years, y=results['rent_investment'], name='Renter Investment', mode='lines'))
    
    fig.update_layout(
        title='Equity vs Investment Over Time',
        xaxis_title='Year',
        yaxis_title='Value ($)',
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)