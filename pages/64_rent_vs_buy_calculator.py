import streamlit as st
import json
import requests
from datetime import datetime, date
from decimal import Decimal
import plotly.graph_objects as go
import plotly.express as px
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Rent vs Buy Calculator", page_icon="🍑", layout="wide")

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rent_vs_buy_scenarios (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                scenario_name VARCHAR(255) NOT NULL,
                home_price DECIMAL(12,2) NOT NULL,
                down_payment_percent DECIMAL(5,2) NOT NULL,
                interest_rate DECIMAL(5,3) NOT NULL,
                loan_term_years INTEGER NOT NULL,
                monthly_rent DECIMAL(10,2) NOT NULL,
                annual_rent_increase DECIMAL(5,2) DEFAULT 3.0,
                property_tax_rate DECIMAL(5,3) DEFAULT 1.0,
                home_insurance_annual DECIMAL(10,2) DEFAULT 1500,
                maintenance_percent DECIMAL(5,2) DEFAULT 1.0,
                hoa_monthly DECIMAL(10,2) DEFAULT 0,
                annual_appreciation DECIMAL(5,2) DEFAULT 3.0,
                investment_return DECIMAL(5,2) DEFAULT 7.0,
                closing_costs_percent DECIMAL(5,2) DEFAULT 3.0,
                selling_costs_percent DECIMAL(5,2) DEFAULT 6.0,
                marginal_tax_rate DECIMAL(5,2) DEFAULT 25.0,
                zip_code VARCHAR(10) DEFAULT '30301',
                city VARCHAR(100) DEFAULT 'Atlanta',
                break_even_months INTEGER,
                recommendation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS zillow_market_cache (
                id SERIAL PRIMARY KEY,
                zip_code VARCHAR(10) NOT NULL,
                city VARCHAR(100),
                median_home_price DECIMAL(12,2),
                median_rent DECIMAL(10,2),
                price_to_rent_ratio DECIMAL(6,2),
                yoy_appreciation DECIMAL(5,2),
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(zip_code)
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rent_vs_buy_scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                scenario_name TEXT NOT NULL,
                home_price REAL NOT NULL,
                down_payment_percent REAL NOT NULL,
                interest_rate REAL NOT NULL,
                loan_term_years INTEGER NOT NULL,
                monthly_rent REAL NOT NULL,
                annual_rent_increase REAL DEFAULT 3.0,
                property_tax_rate REAL DEFAULT 1.0,
                home_insurance_annual REAL DEFAULT 1500,
                maintenance_percent REAL DEFAULT 1.0,
                hoa_monthly REAL DEFAULT 0,
                annual_appreciation REAL DEFAULT 3.0,
                investment_return REAL DEFAULT 7.0,
                closing_costs_percent REAL DEFAULT 3.0,
                selling_costs_percent REAL DEFAULT 6.0,
                marginal_tax_rate REAL DEFAULT 25.0,
                zip_code TEXT DEFAULT '30301',
                city TEXT DEFAULT 'Atlanta',
                break_even_months INTEGER,
                recommendation TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS zillow_market_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zip_code TEXT NOT NULL UNIQUE,
                city TEXT,
                median_home_price REAL,
                median_rent REAL,
                price_to_rent_ratio REAL,
                yoy_appreciation REAL,
                fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()
    conn.close()

init_db()
inject_css()
require_login()
_ensure_tables()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

ATLANTA_ZIP_CODES = {
    "30301": {"name": "Downtown Atlanta", "median_price": 385000, "median_rent": 2100},
    "30305": {"name": "Buckhead", "median_price": 725000, "median_rent": 2800},
    "30306": {"name": "Virginia Highland", "median_price": 650000, "median_rent": 2500},
    "30307": {"name": "Candler Park/Lake Claire", "median_price": 580000, "median_rent": 2300},
    "30308": {"name": "Midtown", "median_price": 420000, "median_rent": 2200},
    "30309": {"name": "Midtown/Ansley Park", "median_price": 550000, "median_rent": 2400},
    "30310": {"name": "West End", "median_price": 320000, "median_rent": 1800},
    "30312": {"name": "Grant Park/Cabbagetown", "median_price": 475000, "median_rent": 2100},
    "30313": {"name": "Vine City", "median_price": 285000, "median_rent": 1600},
    "30314": {"name": "West Atlanta", "median_price": 295000, "median_rent": 1650},
    "30315": {"name": "East Point Adjacent", "median_price": 310000, "median_rent": 1700},
    "30316": {"name": "East Atlanta", "median_price": 385000, "median_rent": 1900},
    "30317": {"name": "Kirkwood", "median_price": 445000, "median_rent": 2000},
    "30318": {"name": "West Midtown", "median_price": 490000, "median_rent": 2200},
    "30319": {"name": "Brookhaven", "median_price": 585000, "median_rent": 2400},
    "30324": {"name": "Lindbergh/Morningside", "median_price": 520000, "median_rent": 2300},
    "30326": {"name": "Buckhead South", "median_price": 680000, "median_rent": 2700},
    "30327": {"name": "Chastain Park", "median_price": 950000, "median_rent": 3500},
    "30328": {"name": "Sandy Springs", "median_price": 520000, "median_rent": 2200},
    "30329": {"name": "Emory/Druid Hills", "median_price": 510000, "median_rent": 2100},
    "30030": {"name": "Decatur", "median_price": 495000, "median_rent": 2100},
    "30033": {"name": "North Decatur", "median_price": 445000, "median_rent": 1950},
    "30084": {"name": "Tucker", "median_price": 365000, "median_rent": 1750},
    "30022": {"name": "Alpharetta", "median_price": 525000, "median_rent": 2200},
    "30024": {"name": "Suwanee", "median_price": 475000, "median_rent": 2100},
    "30096": {"name": "Duluth", "median_price": 420000, "median_rent": 1900},
    "30097": {"name": "Johns Creek", "median_price": 550000, "median_rent": 2300},
    "30060": {"name": "Marietta", "median_price": 385000, "median_rent": 1850},
    "30062": {"name": "East Cobb", "median_price": 485000, "median_rent": 2100},
    "30067": {"name": "Smyrna", "median_price": 425000, "median_rent": 1950},
    "30339": {"name": "Vinings", "median_price": 495000, "median_rent": 2150},
}

def get_zillow_data(zip_code: str) -> dict:
    conn = get_conn()
    cur = conn.cursor()
    placeholder = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        SELECT median_home_price, median_rent, price_to_rent_ratio, yoy_appreciation, fetched_at
        FROM zillow_market_cache
        WHERE zip_code = {placeholder}
    """, (zip_code,))
    row = cur.fetchone()
    conn.close()
    if row:
        fetched_at = row[4]
        if isinstance(fetched_at, str):
            fetched_at = datetime.fromisoformat(fetched_at)
        if (datetime.now() - fetched_at).days < 7:
            return {
                "median_home_price": float(row[0]) if row[0] else None,
                "median_rent": float(row[1]) if row[1] else None,
                "price_to_rent_ratio": float(row[2]) if row[2] else None,
                "yoy_appreciation": float(row[3]) if row[3] else None,
                "source": "cache"
            }
    if zip_code in ATLANTA_ZIP_CODES:
        data = ATLANTA_ZIP_CODES[zip_code]
        median_price = data["median_price"]
        median_rent = data["median_rent"]
        price_to_rent = round(median_price / (median_rent * 12), 2)
        yoy_appreciation = 4.5
        conn = get_conn()
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute("""
                INSERT INTO zillow_market_cache (zip_code, city, median_home_price, median_rent, price_to_rent_ratio, yoy_appreciation)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (zip_code) DO UPDATE SET
                    median_home_price = EXCLUDED.median_home_price,
                    median_rent = EXCLUDED.median_rent,
                    price_to_rent_ratio = EXCLUDED.price_to_rent_ratio,
                    yoy_appreciation = EXCLUDED.yoy_appreciation,
                    fetched_at = CURRENT_TIMESTAMP
            """, (zip_code, data["name"], median_price, median_rent, price_to_rent, yoy_appreciation))
        else:
            cur.execute("""
                INSERT OR REPLACE INTO zillow_market_cache (zip_code, city, median_home_price, median_rent, price_to_rent_ratio, yoy_appreciation, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (zip_code, data["name"], median_price, median_rent, price_to_rent, yoy_appreciation))
        conn.commit()
        conn.close()
        return {
            "median_home_price": median_price,
            "median_rent": median_rent,
            "price_to_rent_ratio": price_to_rent,
            "yoy_appreciation": yoy_appreciation,
            "neighborhood": data["name"],
            "source": "atlanta_data"
        }
    return {
        "median_home_price": 400000,
        "median_rent": 2000,
        "price_to_rent_ratio": 16.67,
        "yoy_appreciation": 3.5,
        "source": "default"
    }

def calculate_monthly_mortgage(principal: float, annual_rate: float, years: int) -> float:
    if annual_rate == 0:
        return principal / (years * 12)
    monthly_rate = annual_rate / 100 / 12
    n_payments = years * 12
    payment = principal * (monthly_rate * (1 + monthly_rate) ** n_payments) / ((1 + monthly_rate) ** n_payments - 1)
    return payment

def calculate_amortization_schedule(principal: float, annual_rate: float, years: int) -> list:
    schedule = []
    monthly_rate = annual_rate / 100 / 12
    n_payments = years * 12
    monthly_payment = calculate_monthly_mortgage(principal, annual_rate, years)
    balance = principal
    for month in range(1, n_payments + 1):
        interest_payment = balance * monthly_rate
        principal_payment = monthly_payment - interest_payment
        balance -= principal_payment
        schedule.append({
            "month": month,
            "payment": monthly_payment,
            "principal": principal_payment,
            "interest": interest_payment,
            "balance": max(0, balance)
        })
    return schedule

def calculate_buy_costs(
    home_price: float,
    down_payment_percent: float,
    interest_rate: float,
    loan_term_years: int,
    property_tax_rate: float,
    home_insurance_annual: float,
    maintenance_percent: float,
    hoa_monthly: float,
    annual_appreciation: float,
    closing_costs_percent: float,
    selling_costs_percent: float,
    marginal_tax_rate: float,
    investment_return: float,
    months: int
) -> dict:
    down_payment = home_price * (down_payment_percent / 100)
    loan_amount = home_price - down_payment
    closing_costs = home_price * (closing_costs_percent / 100)
    initial_cash_outlay = down_payment + closing_costs
    monthly_mortgage = calculate_monthly_mortgage(loan_amount, interest_rate, loan_term_years)
    monthly_property_tax = (home_price * property_tax_rate / 100) / 12
    monthly_insurance = home_insurance_annual / 12
    monthly_maintenance = (home_price * maintenance_percent / 100) / 12
    amort_schedule = calculate_amortization_schedule(loan_amount, interest_rate, loan_term_years)
    monthly_costs = []
    cumulative_costs = []
    total_cost = initial_cash_outlay
    home_values = []
    equity_values = []
    current_home_value = home_price
    for month in range(1, months + 1):
        if month <= len(amort_schedule):
            amort = amort_schedule[month - 1]
            interest_paid = amort["interest"]
            principal_paid = amort["principal"]
            remaining_balance = amort["balance"]
        else:
            interest_paid = 0
            principal_paid = 0
            remaining_balance = 0
        year = (month - 1) // 12
        appreciation_factor = (1 + annual_appreciation / 100) ** (month / 12)
        current_home_value = home_price * appreciation_factor
        prop_tax = (home_price * appreciation_factor * property_tax_rate / 100) / 12
        maintenance = (home_price * appreciation_factor * maintenance_percent / 100) / 12
        tax_savings = interest_paid * (marginal_tax_rate / 100) * 0.5
        monthly_cost = monthly_mortgage + prop_tax + monthly_insurance + maintenance + hoa_monthly - tax_savings
        total_cost += monthly_cost
        monthly_costs.append({
            "month": month,
            "mortgage": monthly_mortgage,
            "property_tax": prop_tax,
            "insurance": monthly_insurance,
            "maintenance": maintenance,
            "hoa": hoa_monthly,
            "tax_savings": tax_savings,
            "total": monthly_cost,
            "interest_paid": interest_paid,
            "principal_paid": principal_paid
        })
        cumulative_costs.append(total_cost)
        home_values.append(current_home_value)
        equity = current_home_value - remaining_balance
        equity_values.append(equity)
    final_home_value = home_price * ((1 + annual_appreciation / 100) ** (months / 12))
    selling_costs = final_home_value * (selling_costs_percent / 100)
    final_balance = amort_schedule[min(months - 1, len(amort_schedule) - 1)]["balance"] if months <= len(amort_schedule) else 0
    net_proceeds = final_home_value - final_balance - selling_costs
    total_interest_paid = sum(m["interest_paid"] for m in monthly_costs)
    total_principal_paid = sum(m["principal_paid"] for m in monthly_costs)
    return {
        "initial_cash_outlay": initial_cash_outlay,
        "down_payment": down_payment,
        "closing_costs": closing_costs,
        "monthly_mortgage": monthly_mortgage,
        "monthly_costs": monthly_costs,
        "cumulative_costs": cumulative_costs,
        "home_values": home_values,
        "equity_values": equity_values,
        "total_cost": total_cost,
        "final_home_value": final_home_value,
        "selling_costs": selling_costs,
        "net_proceeds": net_proceeds,
        "total_interest_paid": total_interest_paid,
        "total_principal_paid": total_principal_paid,
        "net_wealth": net_proceeds - total_cost
    }

def calculate_rent_costs(
    monthly_rent: float,
    annual_rent_increase: float,
    initial_investment: float,
    monthly_savings: float,
    investment_return: float,
    months: int
) -> dict:
    monthly_costs = []
    cumulative_costs = []
    investment_values = []
    total_cost = 0
    current_rent = monthly_rent
    investment_balance = initial_investment
    monthly_return_rate = investment_return / 100 / 12
    for month in range(1, months + 1):
        if month > 1 and (month - 1) % 12 == 0:
            current_rent *= (1 + annual_rent_increase / 100)
        renters_insurance = 25
        monthly_cost = current_rent + renters_insurance
        total_cost += monthly_cost
        investment_growth = investment_balance * monthly_return_rate
        investment_balance += investment_growth + monthly_savings
        monthly_costs.append({
            "month": month,
            "rent": current_rent,
            "renters_insurance": renters_insurance,
            "total": monthly_cost,
            "investment_balance": investment_balance
        })
        cumulative_costs.append(total_cost)
        investment_values.append(investment_balance)
    return {
        "monthly_costs": monthly_costs,
        "cumulative_costs": cumulative_costs,
        "investment_values": investment_values,
        "total_cost": total_cost,
        "final_investment_value": investment_balance,
        "net_wealth": investment_balance - total_cost
    }

def find_break_even_month(buy_costs: dict, rent_costs: dict) -> int:
    for month in range(len(buy_costs["cumulative_costs"])):
        buy_net = buy_costs["equity_values"][month] - buy_costs["cumulative_costs"][month]
        rent_net = rent_costs["investment_values"][month] - rent_costs["cumulative_costs"][month]
        if buy_net >= rent_net:
            return month + 1
    return -1

def generate_ai_recommendation(
    buy_costs: dict,
    rent_costs: dict,
    break_even_months: int,
    inputs: dict,
    market_data: dict
) -> str:
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        if break_even_months == -1:
            return "📊 **Analysis Summary**: Based on your inputs, renting appears to be the better financial choice for the timeframe analyzed. You would build more wealth by investing the down payment and monthly savings difference in the market."
        elif break_even_months <= 36:
            return f"🏠 **Analysis Summary**: Buying makes financial sense! You would break even in just {break_even_months} months ({break_even_months // 12} years, {break_even_months % 12} months). If you plan to stay more than 3 years, buying is likely the better choice."
        elif break_even_months <= 60:
            return f"⚖️ **Analysis Summary**: The decision is close. Break-even occurs at {break_even_months} months ({break_even_months // 12} years, {break_even_months % 12} months). Consider your job stability, life plans, and preference for building equity vs. flexibility."
        else:
            return f"💰 **Analysis Summary**: Renting may be better for now. Break-even is at {break_even_months} months ({break_even_months // 12} years). Unless you're certain about staying long-term, the flexibility of renting combined with investing could serve you better."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        prompt = f"""You are a financial advisor analyzing a rent vs buy decision for Atlanta, Georgia.

Input Parameters:
- Home Price: ${inputs['home_price']:,.0f}
- Down Payment: {inputs['down_payment_percent']:.1f}%
- Mortgage Rate: {inputs['interest_rate']:.2f}%
- Loan Term: {inputs['loan_term_years']} years
- Monthly Rent: ${inputs['monthly_rent']:,.0f}
- Annual Rent Increase: {inputs['annual_rent_increase']:.1f}%
- Property Tax Rate: {inputs['property_tax_rate']:.2f}%
- Home Appreciation: {inputs['annual_appreciation']:.1f}%
- Investment Return: {inputs['investment_return']:.1f}%
- ZIP Code: {inputs['zip_code']} (Atlanta area)

Market Data:
- Median Home Price in Area: ${market_data.get('median_home_price', 'N/A'):,.0f}
- Median Rent in Area: ${market_data.get('median_rent', 'N/A'):,.0f}
- Price-to-Rent Ratio: {market_data.get('price_to_rent_ratio', 'N/A')}

Results:
- Break-even Point: {break_even_months if break_even_months > 0 else 'Not reached'} months
- Total Buy Cost (30 yr): ${buy_costs['total_cost']:,.0f}
- Total Rent Cost (30 yr): ${rent_costs['total_cost']:,.0f}
- Final Home Equity: ${buy_costs['equity_values'][-1]:,.0f}
- Final Investment Portfolio (Renting): ${rent_costs['final_investment_value']:,.0f}
- Buy Net Wealth: ${buy_costs['net_wealth']:,.0f}
- Rent Net Wealth: ${rent_costs['net_wealth']:,.0f}

Provide a personalized, actionable recommendation in 3-4 paragraphs. Consider:
1. The Atlanta housing market context
2. Financial implications based on break-even
3. Non-financial factors (flexibility, maintenance, equity building)
4. Specific advice for their situation

Use emojis sparingly for emphasis. Be direct and practical."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        if break_even_months == -1:
            return "📊 **Analysis Summary**: Based on your inputs, renting appears to be the better financial choice. The combination of investing your down payment and monthly savings difference would likely build more wealth than home ownership over this timeframe."
        elif break_even_months <= 36:
            return f"🏠 **Analysis Summary**: Buying looks favorable! You'd break even in {break_even_months} months. If you plan to stay at least 3-5 years, homeownership could be the better financial path for you."
        else:
            return f"⚖️ **Analysis Summary**: This is a nuanced decision. Break-even occurs at {break_even_months} months ({break_even_months // 12} years, {break_even_months % 12} months). Consider your career stability, family plans, and personal preference for equity building vs. flexibility."

def save_scenario(inputs: dict, break_even: int, recommendation: str, scenario_name: str = None):
    conn = get_conn()
    cur = conn.cursor()
    if not scenario_name:
        scenario_name = f"Scenario {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO rent_vs_buy_scenarios (
                scenario_name, home_price, down_payment_percent, interest_rate,
                loan_term_years, monthly_rent, annual_rent_increase, property_tax_rate,
                home_insurance_annual, maintenance_percent, hoa_monthly, annual_appreciation,
                investment_return, closing_costs_percent, selling_costs_percent,
                marginal_tax_rate, zip_code, break_even_months, recommendation
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            scenario_name, inputs["home_price"], inputs["down_payment_percent"],
            inputs["interest_rate"], inputs["loan_term_years"], inputs["monthly_rent"],
            inputs["annual_rent_increase"], inputs["property_tax_rate"],
            inputs["home_insurance_annual"], inputs["maintenance_percent"],
            inputs["hoa_monthly"], inputs["annual_appreciation"], inputs["investment_return"],
            inputs["closing_costs_percent"], inputs["selling_costs_percent"],
            inputs["marginal_tax_rate"], inputs["zip_code"], break_even, recommendation
        ))
        scenario_id = cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO rent_vs_buy_scenarios (
                scenario_name, home_price, down_payment_percent, interest_rate,
                loan_term_years, monthly_rent, annual_rent_increase, property_tax_rate,
                home_insurance_annual, maintenance_percent, hoa_monthly, annual_appreciation,
                investment_return, closing_costs_percent, selling_costs_percent,
                marginal_tax_rate, zip_code, break_even_months, recommendation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            scenario_name, inputs["home_price"], inputs["down_payment_percent"],
            inputs["interest_rate"], inputs["loan_term_years"], inputs["monthly_rent"],
            inputs["annual_rent_increase"], inputs["property_tax_rate"],
            inputs["home_insurance_annual"], inputs["maintenance_percent"],
            inputs["hoa_monthly"], inputs["annual_appreciation"], inputs["investment_return"],
            inputs["closing_costs_percent"], inputs["selling_costs_percent"],
            inputs["marginal_tax_rate"], inputs["zip_code"], break_even, recommendation
        ))
        scenario_id = cur.lastrowid
    conn.commit()
    conn.close()
    return scenario_id

def get_saved_scenarios():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, scenario_name, home_price, monthly_rent, break_even_months, created_at
        FROM rent_vs_buy_scenarios
        ORDER BY created_at DESC
        LIMIT 20
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def delete_scenario(scenario_id: int):
    conn = get_conn()
    cur = conn.cursor()
    placeholder = "%s" if USE_POSTGRES else "?"
    cur.execute(f"DELETE FROM rent_vs_buy_scenarios WHERE id = {placeholder}", (scenario_id,))
    conn.commit()
    conn.close()

def load_scenario(scenario_id: int):
    conn = get_conn()
    cur = conn.cursor()
    placeholder = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        SELECT home_price, down_payment_percent, interest_rate, loan_term_years,
               monthly_rent, annual_rent_increase, property_tax_rate, home_insurance_annual,
               maintenance_percent, hoa_monthly, annual_appreciation, investment_return,
               closing_costs_percent, selling_costs_percent, marginal_tax_rate, zip_code,
               recommendation
        FROM rent_vs_buy_scenarios
        WHERE id = {placeholder}
    """, (scenario_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "home_price": float(row[0]),
            "down_payment_percent": float(row[1]),
            "interest_rate": float(row[2]),
            "loan_term_years": int(row[3]),
            "monthly_rent": float(row[4]),
            "annual_rent_increase": float(row[5]),
            "property_tax_rate": float(row[6]),
            "home_insurance_annual": float(row[7]),
            "maintenance_percent": float(row[8]),
            "hoa_monthly": float(row[9]),
            "annual_appreciation": float(row[10]),
            "investment_return": float(row[11]),
            "closing_costs_percent": float(row[12]),
            "selling_costs_percent": float(row[13]),
            "marginal_tax_rate": float(row[14]),
            "zip_code": row[15],
            "recommendation": row[16]
        }
    return None

st.title("🏠 Rent vs Buy Calculator")
st.markdown("**Atlanta-specific analysis** with real market data and AI-powered recommendations")

tab1, tab2, tab3 = st.tabs(["📊 Calculator", "📈 Analysis", "💾 Saved Scenarios"])

with tab1:
    col1, col2 = st.columns([1, 2])
    with col1:
        st