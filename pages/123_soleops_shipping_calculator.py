import streamlit as st
import json
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps Shipping Calculator", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

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

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_shipping_profiles (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                profile_name VARCHAR(100) NOT NULL,
                shoe_type VARCHAR(100),
                box_length DECIMAL(5,2) NOT NULL,
                box_width DECIMAL(5,2) NOT NULL,
                box_height DECIMAL(5,2) NOT NULL,
                typical_weight DECIMAL(5,2) NOT NULL,
                preferred_carrier VARCHAR(50),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_shipping_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                shipment_date DATE NOT NULL,
                carrier VARCHAR(50) NOT NULL,
                service_type VARCHAR(100) NOT NULL,
                tracking_number VARCHAR(100),
                origin_zip VARCHAR(10) NOT NULL,
                destination_zip VARCHAR(10) NOT NULL,
                box_length DECIMAL(5,2) NOT NULL,
                box_width DECIMAL(5,2) NOT NULL,
                box_height DECIMAL(5,2) NOT NULL,
                weight DECIMAL(5,2) NOT NULL,
                shipping_cost DECIMAL(10,2) NOT NULL,
                sale_price DECIMAL(10,2),
                item_description VARCHAR(255),
                profile_id INTEGER REFERENCES soleops_shipping_profiles(id) ON DELETE SET NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_shipping_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                profile_name TEXT NOT NULL,
                shoe_type TEXT,
                box_length REAL NOT NULL,
                box_width REAL NOT NULL,
                box_height REAL NOT NULL,
                typical_weight REAL NOT NULL,
                preferred_carrier TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_shipping_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                shipment_date DATE NOT NULL,
                carrier TEXT NOT NULL,
                service_type TEXT NOT NULL,
                tracking_number TEXT,
                origin_zip TEXT NOT NULL,
                destination_zip TEXT NOT NULL,
                box_length REAL NOT NULL,
                box_width REAL NOT NULL,
                box_height REAL NOT NULL,
                weight REAL NOT NULL,
                shipping_cost REAL NOT NULL,
                sale_price REAL,
                item_description TEXT,
                profile_id INTEGER REFERENCES soleops_shipping_profiles(id) ON DELETE SET NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

# Carrier rate estimation functions (2024 estimated rates)
def calculate_dimensional_weight(length, width, height, dim_factor=139):
    """Calculate dimensional weight (DIM weight) for shipping"""
    return (length * width * height) / dim_factor

def get_usps_priority_rate(weight, length, width, height, zone=5):
    """Estimate USPS Priority Mail rate based on weight and dimensions"""
    dim_weight = calculate_dimensional_weight(length, width, height, 166)
    billable_weight = max(weight, dim_weight)
    
    # USPS Priority Mail approximate rates by weight (Zone 5 baseline)
    base_rates = {
        1: 8.70, 2: 9.45, 3: 10.20, 4: 11.50, 5: 12.80,
        6: 14.10, 7: 15.40, 8: 16.70, 9: 18.00, 10: 19.30,
        15: 25.50, 20: 31.70, 25: 37.90, 30: 44.10, 35: 50.30,
        40: 56.50, 45: 62.70, 50: 68.90, 55: 75.10, 60: 81.30, 70: 93.70
    }
    
    zone_multipliers = {1: 0.85, 2: 0.88, 3: 0.92, 4: 0.96, 5: 1.0, 6: 1.08, 7: 1.16, 8: 1.25, 9: 1.35}
    
    weight_lb = int(billable_weight) + (1 if billable_weight % 1 > 0 else 0)
    
    rate = None
    for w in sorted(base_rates.keys()):
        if weight_lb <= w:
            rate = base_rates[w]
            break
    
    if rate is None:
        rate = base_rates[70] + ((weight_lb - 70) * 1.25)
    
    return round(rate * zone_multipliers.get(zone, 1.0), 2)

def get_ups_ground_rate(weight, length, width, height, zone=5):
    """Estimate UPS Ground rate based on weight and dimensions"""
    dim_weight = calculate_dimensional_weight(length, width, height, 139)
    billable_weight = max(weight, dim_weight)
    
    # UPS Ground approximate rates by weight (Zone 5 baseline)
    base_rates = {
        1: 10.50, 2: 11.25, 3: 12.00, 4: 12.75, 5: 13.50,
        6: 14.25, 7: 15.00, 8: 15.75, 9: 16.50, 10: 17.25,
        15: 21.00, 20: 24.75, 25: 28.50, 30: 32.25, 35: 36.00,
        40: 39.75, 45: 43.50, 50: 47.25, 55: 51.00, 60: 54.75, 70: 62.25
    }
    
    zone_multipliers = {1: 0.82, 2: 0.86, 3: 0.90, 4: 0.95, 5: 1.0, 6: 1.10, 7: 1.20, 8: 1.32, 9: 1.45}
    
    weight_lb = int(billable_weight) + (1 if billable_weight % 1 > 0 else 0)
    
    rate = None
    for w in sorted(base_rates.keys()):
        if weight_lb <= w:
            rate = base_rates[w]
            break
    
    if rate is None:
        rate = base_rates[70] + ((weight_lb - 70) * 1.35)
    
    return round(rate * zone_multipliers.get(zone, 1.0), 2)

def get_fedex_home_rate(weight, length, width, height, zone=5):
    """Estimate FedEx Home Delivery rate based on weight and dimensions"""
    dim_weight = calculate_dimensional_weight(length, width, height, 139)
    billable_weight = max(weight, dim_weight)
    
    # FedEx Home Delivery approximate rates by weight (Zone 5 baseline)
    base_rates = {
        1: 10.25, 2: 11.00, 3: 11.75, 4: 12.50, 5: 13.25,
        6: 14.00, 7: 14.75, 8: 15.50, 9: 16.25, 10: 17.00,
        15: 20.50, 20: 24.00, 25: 27.50, 30: 31.00, 35: 34.50,
        40: 38.00, 45: 41.50, 50: 45.00, 55: 48.50, 60: 52.00, 70: 59.00
    }
    
    zone_multipliers = {1: 0.83, 2: 0.87, 3: 0.91, 4: 0.95, 5: 1.0, 6: 1.09, 7: 1.18, 8: 1.30, 9: 1.42}
    
    weight_lb = int(billable_weight) + (1 if billable_weight % 1 > 0 else 0)
    
    rate = None
    for w in sorted(base_rates.keys()):
        if weight_lb <= w:
            rate = base_rates[w]
            break
    
    if rate is None:
        rate = base_rates[70] + ((weight_lb - 70) * 1.30)
    
    return round(rate * zone_multipliers.get(zone, 1.0), 2)

def get_box_recommendation(shoe_size, quantity=1, shoe_type="standard"):
    """Recommend box size based on shoe size and type"""
    
    # Standard sneaker box dimensions (L x W x H in inches)
    box_sizes = {
        "small": {"name": "Small (Kids/Women's)", "length": 12, "width": 8, "height": 5, "weight": 2.5},
        "medium": {"name": "Medium (Men's 7-10)", "length": 14, "width": 10, "height": 6, "weight": 3.5},
        "large": {"name": "Large (Men's 10.5-13)", "length": 15, "width": 11, "height": 6, "weight": 4.0},
        "xl": {"name": "XL (Men's 13+)", "length": 16, "width": 12, "height": 7, "weight": 4.5},
    }
    
    # Shoe type adjustments
    type_adjustments = {
        "standard": {"height_add": 0, "weight_add": 0},
        "jordan_1_high": {"height_add": 1, "weight_add": 0.5},
        "yeezy_350": {"height_add": 0, "weight_add": 0},
        "yeezy_700": {"height_add": 1, "weight_add": 0.3},
        "dunk_low": {"height_add": 0, "weight_add": 0},
        "dunk_high": {"height_add": 0.5, "weight_add": 0.3},
        "new_balance_550": {"height_add": 0, "weight_add": 0.2},
        "boot": {"height_add": 2, "weight_add": 1.0},
    }
    
    # Determine base size
    if shoe_size <= 6:
        base = box_sizes["small"]
    elif shoe_size <= 10:
        base = box_sizes["medium"]
    elif shoe_size <= 13:
        base = box_sizes["large"]
    else:
        base = box_sizes["xl"]
    
    adj = type_adjustments.get(shoe_type, type_adjustments["standard"])
    
    # Adjust for quantity
    if quantity > 1:
        height_mult = min(quantity, 3)  # Stack up to 3 high
        width_mult = (quantity + 2) // 3  # Additional width for more
    else:
        height_mult = 1
        width_mult = 1
    
    return {
        "name": base["name"],
        "length": base["length"],
        "width": base["width"] * width_mult,
        "height": (base["height"] + adj["height_add"]) * height_mult,
        "weight": (base["weight"] + adj["weight_add"]) * quantity
    }

# Database operations
def get_profiles(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"SELECT * FROM soleops_shipping_profiles WHERE user_id = {ph} ORDER BY profile_name", (user_id,))
    cols = [desc[0] for desc in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    conn.close()
    return rows

def add_profile(user_id, profile_name, shoe_type, length, width, height, weight, carrier, notes):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        INSERT INTO soleops_shipping_profiles 
        (user_id, profile_name, shoe_type, box_length, box_width, box_height, typical_weight, preferred_carrier, notes)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, profile_name, shoe_type, length, width, height, weight, carrier, notes))
    conn.commit()
    conn.close()

def update_profile(profile_id, profile_name, shoe_type, length, width, height, weight, carrier, notes):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        UPDATE soleops_shipping_profiles SET
        profile_name = {ph}, shoe_type = {ph}, box_length = {ph}, box_width = {ph},
        box_height = {ph}, typical_weight = {ph}, preferred_carrier = {ph}, notes = {ph},
        updated_at = CURRENT_TIMESTAMP
        WHERE id = {ph}
    """, (profile_name, shoe_type, length, width, height, weight, carrier, notes, profile_id))
    conn.commit()
    conn.close()

def delete_profile(profile_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"DELETE FROM soleops_shipping_profiles WHERE id = {ph}", (profile_id,))
    conn.commit()
    conn.close()

def get_shipping_history(user_id, limit=50):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        SELECT h.*, p.profile_name 
        FROM soleops_shipping_history h
        LEFT JOIN soleops_shipping_profiles p ON h.profile_id = p.id
        WHERE h.user_id = {ph}
        ORDER BY h.shipment_date DESC, h.created_at DESC
        LIMIT {limit}
    """, (user_id,))
    cols = [desc[0] for desc in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    conn.close()
    return rows

def add_shipment(user_id, shipment_date, carrier, service_type, tracking, origin_zip, dest_zip,
                 length, width, height, weight, cost, sale_price, description, profile_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        INSERT INTO soleops_shipping_history
        (user_id, shipment_date, carrier, service_type, tracking_number, origin_zip, destination_zip,
         box_length, box_width, box_height, weight, shipping_cost, sale_price, item_description, profile_id)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    """, (user_id, shipment_date, carrier, service_type, tracking, origin_zip, dest_zip,
          length, width, height, weight, cost, sale_price, description, profile_id))
    conn.commit()
    conn.close()

def delete_shipment(shipment_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"DELETE FROM soleops_shipping_history WHERE id = {ph}", (shipment_id,))
    conn.commit()
    conn.close()

def get_shipping_analytics(user_id):
    conn = get_conn()
    cur = conn.cursor()
    ph = "%s" if USE_POSTGRES else "?"
    
    # Total shipments and costs
    cur.execute(f"""
        SELECT 
            COUNT(*) as total_shipments,
            COALESCE(SUM(shipping_cost), 0) as total_cost,
            COALESCE(AVG(shipping_cost), 0) as avg_cost,
            COALESCE(SUM(sale_price), 0) as total_revenue
        FROM soleops_shipping_history
        WHERE user_id = {ph}
    """, (user_id,))
    totals = cur.fetchone()
    
    # By carrier
    cur.execute(f"""
        SELECT carrier, COUNT(*) as count, SUM(shipping_cost) as total_cost, AVG(shipping_cost) as avg_cost
        FROM soleops_shipping_history
        WHERE user_id = {ph}
        GROUP BY carrier
        ORDER BY count DESC
    """, (user_id,))
    by_carrier = cur.fetchall()
    
    # Monthly trend
    if USE_POSTGRES:
        cur.execute(f"""
            SELECT TO_CHAR(shipment_date, 'YYYY-MM') as month, 
                   COUNT(*) as count, 
                   SUM(shipping_cost) as total_cost
            FROM soleops_shipping_history
            WHERE user_id = {ph}
            GROUP BY TO_CHAR(shipment_date, 'YYYY-MM')
            ORDER BY month DESC
            LIMIT 12
        """, (user_id,))
    else:
        cur.execute(f"""
            SELECT strftime('%Y-%m', shipment_date) as month,
                   COUNT(*) as count,
                   SUM(shipping_cost) as total_cost
            FROM soleops_shipping_history
            WHERE user_id = {ph}
            GROUP BY strftime('%Y-%m', shipment_date)
            ORDER BY month DESC
            LIMIT 12
        """, (user_id,))
    monthly = cur.fetchall()
    
    conn.close()
    
    return {
        "total_shipments": totals[0] or 0,
        "total_cost": float(totals[1] or 0),
        "avg_cost": float(totals[2] or 0),
        "total_revenue": float(totals[3] or 0),
        "by_carrier": by_carrier,
        "monthly": monthly
    }

# Main UI
st.title("📦 SoleOps Shipping Calculator")
st.caption("Calculate optimal shipping costs across carriers with box recommendations")

user_id = st.session_state.get("user_id", 1)

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["🧮 Calculator", "📋 Shipping Profiles", "📜 History", "📊 Analytics"])

# Tab 1: Calculator
with tab1:
    st.subheader("Calculate Shipping Costs")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### 📍 Shipping Details")
        
        origin_zip = st.text_input("Origin ZIP Code", value="30301", max_chars=5, help="Your shipping location")
        dest_zip = st.text_input("Destination ZIP Code", value="10001", max_chars=5, help="Buyer's ZIP code")
        
        # Zone estimation (simplified)
        zone = 5  # Default
        if origin_zip and dest_zip:
            try:
                origin_prefix = int(origin_zip[:3])
                dest_prefix = int(dest_zip[:3])
                diff = abs(origin_prefix - dest_prefix)
                if diff < 50:
                    zone = 2
                elif diff < 100:
                    zone = 3
                elif diff < 200:
                    zone = 4
                elif diff < 400:
                    zone = 5
                elif diff < 600:
                    zone = 6
                elif diff < 800:
                    zone = 7
                else:
                    zone = 8
            except:
                zone = 5
        
        st.info(f"📍 Estimated shipping zone: **Zone {zone}**")
        
        st.markdown("---")
        st.markdown("#### 📦 Package Dimensions")
        
        # Profile selection
        profiles = get_profiles(user_id)
        profile_options = {"Manual Entry": None}
        for p in profiles:
            profile_options[p["profile_name"]] = p
        
        selected_profile = st.selectbox("Load from Profile", options=list(profile_options.keys()))
        
        if selected_profile != "Manual Entry" and profile_options[selected_profile]:
            prof = profile_options[selected_profile]
            default_length = float(prof["box_length"])
            default_width = float(prof["box_width"])
            default_height = float(prof["box_height"])
            default_weight = float(prof["typical_weight"])
        else:
            default_length = 14.0
            default_width = 10.0
            default_height = 6.0
            default_weight = 3.5
        
        dim_col1, dim_col2, dim_col3 = st.columns(3)
        with dim_col1:
            length = st.number_input("Length (in)", min_value=1.0, max_value=50.0, value=default_length, step=0.5)
        with dim_col2:
            width = st.number_input("Width (in)", min_value=1.0, max_value=50.0, value=default_width, step=0.5)
        with dim_col3:
            height = st.number_input("Height (in)", min_value=1.0, max_value=50.0, value=default_height, step=0.5)
        
        weight = st.number_input("Package Weight (lbs)", min_value=0.1, max_value=70.0, value=default_weight, step=0.1)
        
        # Box size helper
        with st.expander("🎯 Box Size Recommender"):
            st.markdown("Get recommended box dimensions based on shoe details")
            
            rec_col1, rec_col2 = st.columns(2)
            with rec_col1:
                shoe_size = st.number_input("Shoe Size", min_value=1.0, max_value=20.0, value=10.0, step=0.5)
                quantity = st.number_input("Quantity", min_value=1, max_value=10, value=1)
            with rec_col2:
                shoe_types = ["standard", "jordan_1_high", "yeezy_350", "yeezy_700", "dunk_low", "dunk_high", "new_balance_550", "boot"]
                shoe_type = st.selectbox("Shoe Type", options=shoe_types, format_func=lambda x: x.replace("_", " ").title())
            
            if st.button("Get Recommendation", type="secondary"):
                rec = get_box_recommendation(shoe_size, quantity, shoe_type)
                st.success(f"""
                **Recommended: {rec['name']}**
                - 📏 Dimensions: {rec['length']}" × {rec['width']}" × {rec['height']}"
                - ⚖️ Est. Weight: {rec['weight']} lbs
                """)
                st.info("💡 Tip: Add 1-2 inches to each dimension for packing materials")
    
    with col2:
        st.markdown("#### 🚚 Carrier Comparison")
        
        if st.button("Calculate Rates", type="primary", use_container_width=True):
            with st.spinner("Calculating shipping rates..."):
                # Calculate dimensional weight
                dim_weight = calculate_dimensional_weight(length, width, height)
                billable_weight = max(weight, dim_weight)
                
                # Get rates for all carriers
                usps_rate = get_usps_priority_rate(weight, length, width, height, zone)
                ups_rate = get_ups_ground_rate(weight, length, width, height, zone)
                fedex_rate = get_fedex_home_rate(weight, length, width, height, zone)
                
                # Find best rate
                rates = [
                    ("USPS Priority Mail", usps_rate, "2-3 business days"),
                    ("UPS Ground", ups_rate, "1-5 business days"),
                    ("FedEx Home Delivery", fedex_rate, "1-5 business days")
                ]
                rates.sort(key=lambda x: x[1])
                
                # Store in session for logging
                st.session_state["last_calc"] = {
                    "rates": rates,
                    "length": length,
                    "width": width,
                    "height": height,
                    "weight": weight,
                    "origin_zip": origin_zip,
                    "dest_zip": dest_zip,
                    "dim_weight": dim_weight,
                    "billable_weight": billable_weight
                }
                
                st.success(f"✅ Best Rate: **{rates[0][0]}** at **${rates[0][1]:.2f}**")
                
                # Display comparison table
                st.markdown("##### Rate Comparison")
                
                for i, (carrier, rate, transit) in enumerate(rates):
                    if i == 0:
                        st.markdown(f"""
                        <div style="background-color: #d4edda; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                            <strong>🏆 {carrier}</strong> <span style="color: #28a745; float: right; font-size: 1.2em;">${rate:.2f}</span><br/>
                            <small>{transit}</small>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        diff = rate - rates[0][1]
                        st.markdown(f"""
                        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                            <strong>{carrier}</strong> <span style="float: right; font-size: 1.2em;">${rate:.2f}</span><br/>
                            <small>{transit} • +${diff:.2f} more</small>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Weight info
                st.markdown("---")
                st.markdown("##### 📐 Weight Analysis")
                wcol1, wcol2 = st.columns(2)
                with wcol1:
                    st.metric("Actual Weight", f"{weight:.1f} lbs")
                with wcol2:
                    st.metric("DIM Weight", f"{dim_weight:.1f} lbs")
                
                if dim_weight > weight:
                    st.warning(f"⚠️ DIM weight ({dim_weight:.1f} lbs) exceeds actual weight. You're paying for box size, not weight!")
        
        # Profit Impact Calculator
        st.markdown("---")
        st.markdown("#### 💰 Profit Impact Calculator")
        
        sale_price = st.number_input("Sale Price ($)", min_value=0.0, value=150.0, step=5.0)
        item_cost = st.number_input("Item Cost ($)", min_value=0.0, value=80.0, step=5.0)
        platform_fee_pct = st.slider("Platform Fee %", min_value=0.0, max_value=20.0, value=12.9, step=0.1)
        
        if "last_calc" in st.session_state and st.session_state["last_calc"]:
            best_rate = st.session_state["last_calc"]["rates"][0][1]
            
            platform_fee = sale_price * (platform_fee_pct / 100)
            total_costs = item_cost + best_rate + platform_fee
            gross_profit = sale_price - total_costs
            margin_pct = (gross_profit / sale_price * 100) if sale_price > 0 else 0
            
            st.markdown("##### Profit Breakdown")
            
            prof_col1, prof_col2 = st.columns(2)
            with prof_col1:
                st.metric("Sale Price", f"${sale_price:.2f}")
                st.metric("Item Cost", f"-${item_cost:.2f}")
                st.metric("Best Shipping", f"-${best_rate:.2f}")
            with prof_col2:
                st.metric("Platform Fee", f"-${platform_fee:.2f}")
                st.metric("**Gross Profit**", f"${gross_profit:.2f}", delta=f"{margin_pct:.1f}% margin")
            
            if gross_profit < 0:
                st.error("❌ This sale would result in a loss!")
            elif margin_pct < 15:
                st.warning("⚠️ Margin below 15% - consider raising price or finding cheaper shipping")
            else:
                st.success("✅ Healthy profit margin!")
        
        # Quick log shipment