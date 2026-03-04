import streamlit as st
import json
import numpy as np
from datetime import datetime, date
from typing import Optional, List, Dict, Tuple
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

st.set_page_config(page_title="Financial Goal Simulator", page_icon="🍑", layout="wide")

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
            CREATE TABLE IF NOT EXISTS goal_simulations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                goal_name VARCHAR(255) NOT NULL,
                target_amount DECIMAL(15,2) NOT NULL,
                current_savings DECIMAL(15,2) DEFAULT 0,
                monthly_contribution DECIMAL(15,2) NOT NULL,
                timeframe_months INTEGER NOT NULL,
                expected_return DECIMAL(5,4) DEFAULT 0.07,
                return_std_dev DECIMAL(5,4) DEFAULT 0.15,
                inflation_rate DECIMAL(5,4) DEFAULT 0.03,
                num_simulations INTEGER DEFAULT 1000,
                success_probability DECIMAL(5,4),
                median_outcome DECIMAL(15,2),
                percentile_10 DECIMAL(15,2),
                percentile_25 DECIMAL(15,2),
                percentile_75 DECIMAL(15,2),
                percentile_90 DECIMAL(15,2),
                simulation_results JSON,
                ai_insights TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_goal_simulations_user 
            ON goal_simulations(user_id)
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS goal_simulations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                goal_name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_savings REAL DEFAULT 0,
                monthly_contribution REAL NOT NULL,
                timeframe_months INTEGER NOT NULL,
                expected_return REAL DEFAULT 0.07,
                return_std_dev REAL DEFAULT 0.15,
                inflation_rate REAL DEFAULT 0.03,
                num_simulations INTEGER DEFAULT 1000,
                success_probability REAL,
                median_outcome REAL,
                percentile_10 REAL,
                percentile_25 REAL,
                percentile_75 REAL,
                percentile_90 REAL,
                simulation_results TEXT,
                ai_insights TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_goal_simulations_user 
            ON goal_simulations(user_id)
        """)
    conn.commit()
    conn.close()

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

def run_monte_carlo_simulation(
    current_savings: float,
    monthly_contribution: float,
    timeframe_months: int,
    expected_annual_return: float,
    return_std_dev: float,
    inflation_rate: float,
    num_simulations: int = 1000
) -> Dict:
    monthly_return = expected_annual_return / 12
    monthly_std = return_std_dev / np.sqrt(12)
    monthly_inflation = inflation_rate / 12
    
    final_values = []
    all_paths = []
    inflation_adjusted_values = []
    
    np.random.seed(42)
    
    for sim in range(num_simulations):
        portfolio_value = current_savings
        path = [portfolio_value]
        
        for month in range(timeframe_months):
            monthly_return_realized = np.random.normal(monthly_return, monthly_std)
            portfolio_value = portfolio_value * (1 + monthly_return_realized) + monthly_contribution
            portfolio_value = max(0, portfolio_value)
            path.append(portfolio_value)
        
        final_values.append(portfolio_value)
        inflation_factor = (1 + monthly_inflation) ** timeframe_months
        inflation_adjusted_values.append(portfolio_value / inflation_factor)
        
        if sim < 100:
            all_paths.append(path)
    
    final_values = np.array(final_values)
    inflation_adjusted_values = np.array(inflation_adjusted_values)
    
    return {
        "final_values": final_values,
        "inflation_adjusted_values": inflation_adjusted_values,
        "all_paths": all_paths,
        "median": np.median(final_values),
        "mean": np.mean(final_values),
        "percentile_10": np.percentile(final_values, 10),
        "percentile_25": np.percentile(final_values, 25),
        "percentile_75": np.percentile(final_values, 75),
        "percentile_90": np.percentile(final_values, 90),
        "std_dev": np.std(final_values)
    }


def save_simulation(
    user_id: int,
    goal_name: str,
    target_amount: float,
    current_savings: float,
    monthly_contribution: float,
    timeframe_months: int,
    expected_return: float,
    return_std_dev: float,
    inflation_rate: float,
    num_simulations: int,
    success_probability: float,
    median_outcome: float,
    percentile_10: float,
    percentile_25: float,
    percentile_75: float,
    percentile_90: float,
    simulation_results: str,
    ai_insights: str
) -> int:
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO goal_simulations (
                user_id, goal_name, target_amount, current_savings, monthly_contribution,
                timeframe_months, expected_return, return_std_dev, inflation_rate,
                num_simulations, success_probability, median_outcome, percentile_10,
                percentile_25, percentile_75, percentile_90, simulation_results, ai_insights
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (user_id, goal_name, target_amount, current_savings, monthly_contribution,
              timeframe_months, expected_return, return_std_dev, inflation_rate,
              num_simulations, success_probability, median_outcome, percentile_10,
              percentile_25, percentile_75, percentile_90, simulation_results, ai_insights))
        sim_id = cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO goal_simulations (
                user_id, goal_name, target_amount, current_savings, monthly_contribution,
                timeframe_months, expected_return, return_std_dev, inflation_rate,
                num_simulations, success_probability, median_outcome, percentile_10,
                percentile_25, percentile_75, percentile_90, simulation_results, ai_insights
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, goal_name, target_amount, current_savings, monthly_contribution,
              timeframe_months, expected_return, return_std_dev, inflation_rate,
              num_simulations, success_probability, median_outcome, percentile_10,
              percentile_25, percentile_75, percentile_90, simulation_results, ai_insights))
        sim_id = cur.lastrowid
    conn.commit()
    conn.close()
    return sim_id


def get_user_simulations(user_id: int) -> List[Dict]:
    conn = get_conn()
    cur = conn.cursor()
    placeholder = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        SELECT id, goal_name, target_amount, success_probability, median_outcome, created_at
        FROM goal_simulations
        WHERE user_id = {placeholder}
        ORDER BY created_at DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "goal_name": r[1],
            "target_amount": r[2],
            "success_probability": r[3],
            "median_outcome": r[4],
            "created_at": r[5]
        }
        for r in rows
    ]


st.title("🎯 Financial Goal Simulator")
st.markdown("Use Monte Carlo simulation to estimate the probability of reaching your financial goals.")

user_id = st.session_state.get("user_id", 1)

tab1, tab2 = st.tabs(["New Simulation", "Past Simulations"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        goal_name = st.text_input("Goal Name", value="Retirement Fund")
        target_amount = st.number_input("Target Amount ($)", min_value=1000.0, value=100000.0, step=1000.0)
        current_savings = st.number_input("Current Savings ($)", min_value=0.0, value=10000.0, step=500.0)
        monthly_contribution = st.number_input("Monthly Contribution ($)", min_value=0.0, value=500.0, step=50.0)
    
    with col2:
        timeframe_years = st.slider("Timeframe (years)", min_value=1, max_value=40, value=10)
        timeframe_months = timeframe_years * 12
        expected_return = st.slider("Expected Annual Return (%)", min_value=0.0, max_value=15.0, value=7.0) / 100
        return_std_dev = st.slider("Return Volatility (%)", min_value=5.0, max_value=30.0, value=15.0) / 100
        inflation_rate = st.slider("Inflation Rate (%)", min_value=0.0, max_value=10.0, value=3.0) / 100
        num_simulations = st.selectbox("Number of Simulations", [100, 500, 1000, 5000], index=2)
    
    if st.button("Run Simulation", type="primary"):
        with st.spinner("Running Monte Carlo simulation..."):
            results = run_monte_carlo_simulation(
                current_savings=current_savings,
                monthly_contribution=monthly_contribution,
                timeframe_months=timeframe_months,
                expected_annual_return=expected_return,
                return_std_dev=return_std_dev,
                inflation_rate=inflation_rate,
                num_simulations=num_simulations
            )
            
            success_count = np.sum(results["final_values"] >= target_amount)
            success_probability = success_count / num_simulations
            
            st.subheader("Simulation Results")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Success Probability", f"{success_probability:.1%}")
            col2.metric("Median Outcome", f"${results['median']:,.0f}")
            col3.metric("10th Percentile", f"${results['percentile_10']:,.0f}")
            col4.metric("90th Percentile", f"${results['percentile_90']:,.0f}")
            
            # Distribution chart
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=results["final_values"], nbinsx=50, name="Final Values"))
            fig.add_vline(x=target_amount, line_dash="dash", line_color="red", annotation_text="Target")
            fig.add_vline(x=results["median"], line_dash="dash", line_color="green", annotation_text="Median")
            fig.update_layout(title="Distribution of Final Portfolio Values", xaxis_title="Portfolio Value ($)", yaxis_title="Frequency")
            st.plotly_chart(fig, use_container_width=True)
            
            # Path chart
            fig2 = go.Figure()
            for i, path in enumerate(results["all_paths"][:50]):
                fig2.add_trace(go.Scatter(y=path, mode='lines', opacity=0.3, showlegend=False))
            fig2.add_hline(y=target_amount, line_dash="dash", line_color="red", annotation_text="Target")
            fig2.update_layout(title="Sample Portfolio Paths", xaxis_title="Months", yaxis_title="Portfolio Value ($)")
            st.plotly_chart(fig2, use_container_width=True)
            
            # Save simulation
            simulation_results_json = json.dumps({
                "median": float(results["median"]),
                "mean": float(results["mean"]),
                "percentile_10": float(results["percentile_10"]),
                "percentile_25": float(results["percentile_25"]),
                "percentile_75": float(results["percentile_75"]),
                "percentile_90": float(results["percentile_90"])
            })
            
            sim_id = save_simulation(
                user_id=user_id,
                goal_name=goal_name,
                target_amount=target_amount,
                current_savings=current_savings,
                monthly_contribution=monthly_contribution,
                timeframe_months=timeframe_months,
                expected_return=expected_return,
                return_std_dev=return_std_dev,
                inflation_rate=inflation_rate,
                num_simulations=num_simulations,
                success_probability=success_probability,
                median_outcome=results["median"],
                percentile_10=results["percentile_10"],
                percentile_25=results["percentile_25"],
                percentile_75=results["percentile_75"],
                percentile_90=results["percentile_90"],
                simulation_results=simulation_results_json,
                ai_insights=""
            )
            
            st.success(f"Simulation saved with ID: {sim_id}")

with tab2:
    simulations = get_user_simulations(user_id)
    
    if simulations:
        for sim in simulations:
            with st.expander(f"{sim['goal_name']} - {sim['created_at']}"):
                col1, col2, col3 = st.columns(3)
                col1.metric("Target", f"${sim['target_amount']:,.0f}")
                col2.metric("Success Probability", f"{sim['success_probability']:.1%}" if sim['success_probability'] else "N/A")
                col3.metric("Median Outcome", f"${sim['median_outcome']:,.0f}" if sim['median_outcome'] else "N/A")
    else:
        st.info("No past simulations found. Run a new simulation to get started!")