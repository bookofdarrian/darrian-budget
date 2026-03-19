import streamlit as st
import json
from datetime import datetime, timedelta
from decimal import Decimal
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="SoleOps Cross-Platform Analytics", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()


def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_platform_analytics (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                platform VARCHAR(50) NOT NULL,
                period_start DATE NOT NULL,
                period_end DATE NOT NULL,
                revenue DECIMAL(12,2) DEFAULT 0,
                items_sold INTEGER DEFAULT 0,
                avg_days_to_sell DECIMAL(8,2) DEFAULT 0,
                sell_through_rate DECIMAL(5,2) DEFAULT 0,
                fees_paid DECIMAL(12,2) DEFAULT 0,
                net_profit DECIMAL(12,2) DEFAULT 0,
                avg_shipping_cost DECIMAL(8,2) DEFAULT 0,
                return_count INTEGER DEFAULT 0,
                return_rate DECIMAL(5,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, platform, period_start, period_end)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sold_orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                platform VARCHAR(50) NOT NULL,
                sku VARCHAR(100),
                item_name VARCHAR(255),
                category VARCHAR(100),
                sale_price DECIMAL(12,2),
                cost_basis DECIMAL(12,2),
                platform_fees DECIMAL(12,2),
                shipping_cost DECIMAL(12,2),
                net_profit DECIMAL(12,2),
                listed_date DATE,
                sold_date DATE,
                days_to_sell INTEGER,
                is_returned BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_platform_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                revenue REAL DEFAULT 0,
                items_sold INTEGER DEFAULT 0,
                avg_days_to_sell REAL DEFAULT 0,
                sell_through_rate REAL DEFAULT 0,
                fees_paid REAL DEFAULT 0,
                net_profit REAL DEFAULT 0,
                avg_shipping_cost REAL DEFAULT 0,
                return_count INTEGER DEFAULT 0,
                return_rate REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, platform, period_start, period_end)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_sold_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                sku TEXT,
                item_name TEXT,
                category TEXT,
                sale_price REAL,
                cost_basis REAL,
                platform_fees REAL,
                shipping_cost REAL,
                net_profit REAL,
                listed_date TEXT,
                sold_date TEXT,
                days_to_sell INTEGER,
                is_returned INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()


def get_date_range(period: str):
    today = datetime.now().date()
    if period == "7d":
        start_date = today - timedelta(days=7)
    elif period == "30d":
        start_date = today - timedelta(days=30)
    elif period == "90d":
        start_date = today - timedelta(days=90)
    elif period == "YTD":
        start_date = datetime(today.year, 1, 1).date()
    else:
        start_date = datetime(2020, 1, 1).date()
    return start_date, today


def aggregate_sales_by_platform(user_id: int, start_date, end_date):
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    
    query = f"""
        SELECT 
            platform,
            COUNT(*) as items_sold,
            COALESCE(SUM(sale_price), 0) as revenue,
            COALESCE(SUM(platform_fees), 0) as fees_paid,
            COALESCE(SUM(shipping_cost), 0) as shipping_costs,
            COALESCE(SUM(net_profit), 0) as net_profit,
            COALESCE(AVG(days_to_sell), 0) as avg_days_to_sell,
            COALESCE(SUM(CASE WHEN is_returned = {'TRUE' if USE_POSTGRES else '1'} THEN 1 ELSE 0 END), 0) as return_count
        FROM soleops_sold_orders
        WHERE user_id = {ph}
        AND sold_date >= {ph}
        AND sold_date <= {ph}
        GROUP BY platform
    """
    
    cur.execute(query, (user_id, str(start_date), str(end_date)))
    rows = cur.fetchall()
    conn.close()
    
    results = {}
    for row in rows:
        platform = row[0]
        results[platform] = {
            'items_sold': row[1] or 0,
            'revenue': float(row[2] or 0),
            'fees_paid': float(row[3] or 0),
            'shipping_costs': float(row[4] or 0),
            'net_profit': float(row[5] or 0),
            'avg_days_to_sell': float(row[6] or 0),
            'return_count': row[7] or 0
        }
    
    return results


def calculate_platform_metrics(user_id: int, start_date, end_date):
    platform_data = aggregate_sales_by_platform(user_id, start_date, end_date)
    
    platform_fees = {
        'eBay': {'selling_fee': 0.1325, 'payment_fee': 0.029, 'fixed_fee': 0.30},
        'Mercari': {'selling_fee': 0.10, 'payment_fee': 0.029, 'fixed_fee': 0.50},
        'Depop': {'selling_fee': 0.10, 'payment_fee': 0.029, 'fixed_fee': 0.30}
    }
    
    metrics = {}
    for platform in ['eBay', 'Mercari', 'Depop']:
        data = platform_data.get(platform, {
            'items_sold': 0,
            'revenue': 0,
            'fees_paid': 0,
            'shipping_costs': 0,
            'net_profit': 0,
            'avg_days_to_sell': 0,
            'return_count': 0
        })
        
        items_sold = data['items_sold']
        revenue = data['revenue']
        
        if items_sold > 0:
            sell_through_rate = min(100, (items_sold / max(items_sold * 1.5, 1)) * 100)
            return_rate = (data['return_count'] / items_sold) * 100
            avg_sale_price = revenue / items_sold
        else:
            sell_through_rate = 0
            return_rate = 0
            avg_sale_price = 0
        
        fee_info = platform_fees.get(platform, platform_fees['eBay'])
        effective_fee_rate = (data['fees_paid'] / revenue * 100) if revenue > 0 else 0
        
        metrics[platform] = {
            'items_sold': items_sold,
            'revenue': revenue,
            'fees_paid': data['fees_paid'],
            'shipping_costs': data['shipping_costs'],
            'net_profit': data['net_profit'],
            'avg_days_to_sell': data['avg_days_to_sell'],
            'sell_through_rate': sell_through_rate,
            'return_count': data['return_count'],
            'return_rate': return_rate,
            'avg_sale_price': avg_sale_price,
            'effective_fee_rate': effective_fee_rate,
            'fee_structure': fee_info
        }
    
    return metrics


def get_revenue_trend(user_id: int, start_date, end_date):
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    
    if USE_POSTGRES:
        date_format = "TO_CHAR(sold_date::date, 'YYYY-MM-DD')"
    else:
        date_format = "DATE(sold_date)"
    
    query = f"""
        SELECT 
            {date_format} as sale_date,
            platform,
            COALESCE(SUM(sale_price), 0) as revenue
        FROM soleops_sold_orders
        WHERE user_id = {ph}
        AND sold_date >= {ph}
        AND sold_date <= {ph}
        GROUP BY {date_format}, platform
        ORDER BY sale_date
    """
    
    cur.execute(query, (user_id, str(start_date), str(end_date)))
    rows = cur.fetchall()
    conn.close()
    
    data = []
    for row in rows:
        data.append({
            'date': row[0],
            'platform': row[1],
            'revenue': float(row[2] or 0)
        })
    
    return data


def get_category_performance(user_id: int, start_date, end_date):
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    
    query = f"""
        SELECT 
            platform,
            COALESCE(category, 'Uncategorized') as category,
            COUNT(*) as items_sold,
            COALESCE(SUM(sale_price), 0) as revenue,
            COALESCE(SUM(net_profit), 0) as profit,
            COALESCE(AVG(CASE WHEN sale_price > 0 THEN (net_profit / sale_price) * 100 ELSE 0 END), 0) as profit_margin
        FROM soleops_sold_orders
        WHERE user_id = {ph}
        AND sold_date >= {ph}
        AND sold_date <= {ph}
        GROUP BY platform, category
        ORDER BY profit DESC
    """
    
    cur.execute(query, (user_id, str(start_date), str(end_date)))
    rows = cur.fetchall()
    conn.close()
    
    data = []
    for row in rows:
        data.append({
            'platform': row[0],
            'category': row[1],
            'items_sold': row[2],
            'revenue': float(row[3] or 0),
            'profit': float(row[4] or 0),
            'profit_margin': float(row[5] or 0)
        })
    
    return data


def calculate_fee_comparison(sale_price: float):
    platforms = {
        'eBay': {
            'selling_fee_rate': 0.1325,
            'payment_processing': 0.029,
            'fixed_fee': 0.30
        },
        'Mercari': {
            'selling_fee_rate': 0.10,
            'payment_processing': 0.029,
            'fixed_fee': 0.50
        },
        'Depop': {
            'selling_fee_rate': 0.10,
            'payment_processing': 0.029,
            'fixed_fee': 0.30
        }
    }
    
    results = {}
    for platform, fees in platforms.items():
        selling_fee = sale_price * fees['selling_fee_rate']
        payment_fee = sale_price * fees['payment_processing'] + fees['fixed_fee']
        total_fees = selling_fee + payment_fee
        net_after_fees = sale_price - total_fees
        fee_percentage = (total_fees / sale_price) * 100 if sale_price > 0 else 0
        
        results[platform] = {
            'selling_fee': round(selling_fee, 2),
            'payment_fee': round(payment_fee, 2),
            'total_fees': round(total_fees, 2),
            'net_after_fees': round(net_after_fees, 2),
            'fee_percentage': round(fee_percentage, 2)
        }
    
    return results


def get_ai_recommendations(metrics: dict, category_data: list):
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ Configure your Anthropic API key in Settings to get AI recommendations."
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        metrics_summary = json.dumps(metrics, indent=2, default=str)
        top_categories = category_data[:10] if category_data else []
        categories_summary = json.dumps(top_categories, indent=2, default=str)
        
        prompt = f"""You are a sneaker resale business analyst. Analyze this cross-platform performance data and provide specific, actionable recommendations.

PLATFORM METRICS:
{metrics_summary}

TOP PERFORMING CATEGORIES:
{categories_summary}

Provide recommendations in these areas:
1. **Platform Optimization**: Which platform should they focus on and why?
2. **Pricing Strategy**: Based on fees and sell-through rates
3. **Inventory Focus**: Which categories/types to prioritize
4. **Quick Wins**: 2-3 immediate actions to improve profitability

Keep recommendations specific, data-driven, and actionable. Format with clear headers and bullet points."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.content[0].text
        
    except Exception as e:
        return f"⚠️ Error getting AI recommendations: {str(e)}"


def add_sample_data(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    
    ph = "%s" if USE_POSTGRES else "?"
    
    import random
    
    platforms = ['eBay', 'Mercari', 'Depop']
    categories = ['Jordan 1', 'Jordan 4', 'Dunk Low', 'Yeezy', 'New Balance']
    
    cur.execute(f"SELECT COUNT(*) FROM soleops_sold_orders WHERE user_id = {ph}", (user_id,))
    count = cur.fetchone()[0]
    
    if count == 0:
        for i in range(50):
            platform = random.choice(platforms)
            category = random.choice(categories)
            sale_price = round(random.uniform(80, 400), 2)
            cost_basis = round(sale_price * random.uniform(0.4, 0.7), 2)
            
            if platform == 'eBay':
                platform_fees = round(sale_price * 0.1325 + sale_price * 0.029 + 0.30, 2)
            elif platform == 'Mercari':
                platform_fees = round(sale_price * 0.10 + sale_price * 0.029 + 0.50, 2)
            else:
                platform_fees = round(sale_price * 0.10 + sale_price * 0.029 + 0.30, 2)
            
            shipping_cost = round(random.uniform(8, 18), 2)
            net_profit = round(sale_price - cost_basis - platform_fees - shipping_cost, 2)
            
            days_ago = random.randint(1, 90)
            sold_date = (datetime.now() - timedelta(days=days_ago)).date()
            days_to_sell = random.randint(1, 30)
            listed_date = sold_date - timedelta(days=days_to_sell)
            is_returned = 1 if random.random() < 0.05 else 0
            
            cur.execute(f"""
                INSERT INTO soleops_sold_orders 
                (user_id, platform, sku, item_name, category, sale_price, cost_basis, 
                 platform_fees, shipping_cost, net_profit, listed_date, sold_date, 
                 days_to_sell, is_returned)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """, (
                user_id, platform, f"SKU-{i+1000}", f"{category} Size {random.randint(8, 13)}",
                category, sale_price, cost_basis, platform_fees, shipping_cost, net_profit,
                str(listed_date), str(sold_date), days_to_sell, is_returned
            ))
        
        conn.commit()
    
    conn.close()


_ensure_tables()

user_id = st.session_state.get("user_id", 1)

st.title("📊 SoleOps Cross-Platform Analytics")
st.markdown("Compare performance across eBay, Mercari, and Depop in one unified dashboard.")

col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    period = st.selectbox(
        "Time Period",
        options=["7d", "30d", "90d", "YTD", "All Time"],
        index=1,
        help="Select the time period for analytics"
    )

with col3:
    if st.button("🔄 Refresh Data"):
        st.rerun()

start_date, end_date = get_date_range(period)

with st.expander("🧪 Demo Mode - Add Sample Data"):
    st.info("Click below to populate sample sales data for demonstration purposes.")
    if st.button("Generate Sample Data"):
        add_sample_data(user_id)
        st.success("✅ Sample data added!")
        st.rerun()

with st.spinner("Loading analytics..."):
    metrics = calculate_platform_metrics(user_id, start_date, end_date)
    revenue_trend = get_revenue_trend(user_id, start_date, end_date)
    category_data = get_category_performance(user_id, start_date, end_date)

st.markdown("### 📈 Platform Performance Overview")

total_revenue = sum(m['revenue'] for m in metrics.values())
total_items = sum(m['items_sold'] for m in metrics.values())
total_profit = sum(m['net_profit'] for m in metrics.values())

if total_items == 0:
    st.info("📭 No sales data found for the selected period. Add some sales or generate sample data to see analytics.")
else:
    summary_cols = st.columns(4)
    with summary_cols[0]:
        st.metric("Total Revenue", f"${total_revenue:,.2f}")
    with summary_cols[1]:
        st.metric("Total Items Sold", f"{total_items:,}")
    with summary_cols[2]:
        st.metric("Total Profit", f"${total_profit:,.2f}")
    with summary_cols[3]:
        avg_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
        st.metric("Avg Profit Margin", f"{avg_margin:.1f}%")

    st.markdown("### 🏪 Platform Comparison Cards")
    
    platform_cols = st.columns(3)
    
    platform_colors = {'eBay': '#0064D2', 'Mercari': '#FF0211', 'Depop': '#FF2300'}
    platform_icons = {'eBay': '🛒', 'Mercari': '📱', 'Depop': '👗'}
    
    for idx, (platform, data) in enumerate(metrics.items()):
        with platform_cols[idx]:
            color = platform_colors.get(platform, '#666')
            icon = platform_icons.get(platform, '📦')
            
            st.markdown(f"""
            <div style="border: 2px solid {color}; border-radius: 10px; padding: 15px; margin-bottom: 10px;">
                <h3 style="color: {color}; margin: 0;">{icon} {platform}</h3>
            </div>
            """, unsafe_allow_html=True)
            
            st.metric("Revenue", f"${data['revenue']:,.2f}")
            st.metric("Items Sold", f"{data['items_sold']:,}")
            st.metric("Net Profit", f"${data['net_profit']:,.2f}")
            
            profit_margin = (data['net_profit'] / data['revenue'] * 100) if data['revenue'] > 0 else 0
            st.metric("Profit Margin", f"{profit_margin:.1f}%")
            st.metric("Avg Days to Sell", f"{data['avg_days_to_sell']:.1f}")
            st.metric("Sell-Through Rate", f"{data['sell_through_rate']:.1f}%")
            st.metric("Return Rate", f"{data['return_rate']:.1f}%")
            st.metric("Effective Fee Rate", f"{data['effective_fee_rate']:.1f}%")

    st.markdown("### 📊 Revenue Trends")
    
    if revenue_trend:
        import pandas as pd
        df_trend = pd.DataFrame(revenue_trend)
        
        fig = px.line(
            df_trend,
            x='date',
            y='revenue',
            color='platform',
            title='Revenue by Platform Over Time',
            color_discrete_map=platform_colors
        )
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Revenue ($)",
            legend_title="Platform",
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No trend data available for the selected period.")

    chart_cols = st.columns(2)
    
    with chart_cols[0]:
        st.markdown("#### 📦 Sell-Through Rate by Platform")
        
        sell_through_data = {
            'Platform': list(metrics.keys()),
            'Sell-Through Rate': [m['sell_through_rate'] for m in metrics.values()]
        }
        
        fig_str = px.bar(
            x=sell_through_data['Platform'],
            y=sell_through_data['Sell-Through Rate'],
            color=sell_through_data['Platform'],
            color_discrete_map=platform_colors,
            labels={'x': 'Platform', 'y': 'Sell-Through Rate (%)'}
        )
        fig_str.update_layout(showlegend=False)
        st.plotly_chart(fig_str, use_container_width=True)
    
    with chart_cols[1]:
        st.markdown("#### 💰 Net Profit by Platform")
        
        profit_data = {
            'Platform': list(metrics.keys()),
            'Net Profit': [m['net_profit'] for m in metrics.values()]
        }
        
        fig_profit = px.pie(
            values=profit_data['Net Profit'],
            names=profit_data['Platform'],
            color=profit_data['Platform'],
            color_discrete_map=platform_colors
        )
        st.plotly_chart(fig_profit, use_container_width=True)

    st.markdown("### 🏆 Best Performing Categories by Platform")
    
    if category_data:
        import pandas as pd
        df_cat = pd.DataFrame(category_data)
        
        for platform in ['eBay', 'Mercari', 'Depop']:
            platform_cats = df_cat[df_cat['platform'] == platform].head(5)
            if not platform_cats.empty:
                with st.expander(f"{platform_icons.get(platform, '📦')} {platform} Top Categories", expanded=True):
                    st.dataframe(
                        platform_cats[['category', 'items_sold', 'revenue', 'profit', 'profit_margin']].rename(columns={
                            'category': 'Category',
                            'items_sold': 'Items Sold',
                            'revenue': 'Revenue ($)',
                            'profit': 'Profit ($)',
                            'profit_margin': 'Margin (%)'
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
    else:
        st.info("No category data available.")

    st.markdown("### 💵 Platform Fee Comparison Calculator")
    
    fee_col1, fee_col2 = st.columns([1, 2])
    
    with fee_col1:
        calc_price = st.number_input(
            "Enter Sale Price ($)",
            min_value=1.0,
            max_value=10000.0,
            value=100.0,
            step=5.0,
            help="Calculate fees and net profit for a hypothetical sale"
        )
    
    fee_comparison = calculate_fee_comparison(calc_price)
    
    with fee_col2:
        fee_df_data = []
        for platform, fees in fee_comparison.items():
            fee_df_data.append({
                'Platform': platform,
                'Selling Fee': f"${fees['selling_fee']:.2f}",
                'Payment Fee': f"${fees['payment_fee']:.2f}",
                'Total Fees': f"${fees['total_fees']:.2f}",
                'Net After Fees': f"${fees['net_after_fees']:.2f}",
                'Fee %': f"{fees['fee_percentage']:.1f}%"
            })
        
        import pandas as pd
        fee_df = pd.DataFrame(fee_df_data)
        st.dataframe(fee_df, use_container_width=True, hide_index=True)
    
    best_platform = max(fee_comparison.items(), key=lambda x: x[1]['net_after_fees'])
    st.success(f"💡 **Best platform for a ${calc_price:.2f} sale:** {best_platform[0]} (Net: ${best_platform[1]['net_after_fees']:.2f})")

    st.markdown("### 🤖 AI Platform Optimization Recommendations")
    
    if st.button("🔮 Get AI Recommendations", type="primary"):
        with st.spinner("Analyzing your cross-platform performance..."):
            recommendations = get_ai_recommendations(metrics, category_data)
            st.markdown(recommendations)
    else:
        st.info("Click the button above to get personalized AI recommendations based on your sales data.")

    st.markdown("### 📋 Detailed Metrics Export")
    
    with st.expander("View Raw Metrics Data"):
        st.json(metrics)
        
        export_data = {
            'period': period,
            'start_date': str(start_date),
            'end_date': str(end_date),
            'metrics': metrics,
            'total_revenue': total_revenue,
            'total_items': total_items,
            'total_profit': total_profit
        }
        
        st.download_button(
            label="📥 Download Analytics JSON",
            data=json.dumps(export_data, indent=2, default=str),
            file_name=f"soleops_analytics_{period}_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json"
        )

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9em;">
    📊 SoleOps Cross-Platform Analytics | Compare eBay • Mercari • Depop Performance
</div>
""", unsafe_allow_html=True)