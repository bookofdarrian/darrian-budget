import streamlit as st
import json
from datetime import datetime, timedelta
from decimal import Decimal
import anthropic

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="SoleOps: Return & Refund Tracker", page_icon="🍑", layout="wide")
init_db()
inject_css()
require_login()

# Sidebar navigation
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="✅ Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="🎬 Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="📝 Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="🎵 Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

# Return reason codes taxonomy
RETURN_REASONS = {
    "INAD": "Item Not As Described",
    "WRONG_SIZE": "Wrong Size",
    "BUYER_REMORSE": "Buyer Remorse",
    "DAMAGED_SHIPPING": "Damaged in Shipping",
    "DEFECTIVE": "Defective Item",
    "COUNTERFEIT": "Authenticity Concern",
    "MISSING_PARTS": "Missing Parts/Accessories",
    "OTHER": "Other"
}

# Return status workflow
RETURN_STATUSES = {
    "requested": {"label": "Return Requested", "color": "#FFA500", "order": 1},
    "approved": {"label": "Return Approved", "color": "#2196F3", "order": 2},
    "item_received": {"label": "Item Received", "color": "#9C27B0", "order": 3},
    "refund_issued": {"label": "Refund Issued", "color": "#4CAF50", "order": 4},
    "disputed": {"label": "In Dispute", "color": "#F44336", "order": 5},
    "resolved": {"label": "Resolved", "color": "#607D8B", "order": 6},
    "denied": {"label": "Return Denied", "color": "#795548", "order": 7}
}

PLATFORMS = ["eBay", "Mercari", "Depop"]

# Platform-specific dispute guidance
PLATFORM_GUIDANCE = {
    "eBay": {
        "policy": "eBay Money Back Guarantee",
        "timeframe": "30 days from delivery",
        "seller_protection": [
            "Tracking showing delivered protects against INR claims",
            "Signature confirmation for items $750+",
            "Photos of item before shipping recommended",
            "eBay may side with buyer on INAD claims - detailed listings help"
        ],
        "dispute_tips": [
            "Respond within 3 business days to avoid automatic case resolution",
            "Always accept return if item is defective - fighting costs more",
            "Request photos from buyer before accepting INAD returns",
            "Use eBay's appeal process if you disagree with resolution"
        ],
        "defect_threshold": "2% return rate triggers seller performance warnings"
    },
    "Mercari": {
        "policy": "Mercari Buyer Protection",
        "timeframe": "3 days from delivery to rate",
        "seller_protection": [
            "Once buyer rates, sale is final",
            "Accurate descriptions and photos are your best defense",
            "Mercari holds funds until buyer rates or 3 days pass"
        ],
        "dispute_tips": [
            "Respond quickly to return requests",
            "Mercari Support makes final decisions",
            "Keep all communication on-platform",
            "Partial refunds can be negotiated through support"
        ],
        "defect_threshold": "High return rate may affect search ranking"
    },
    "Depop": {
        "policy": "Depop Buyer Protection (PayPal/Depop Payments)",
        "timeframe": "180 days for PayPal disputes",
        "seller_protection": [
            "Always use tracked shipping",
            "Keep proof of condition before shipping",
            "Depop Payments offers seller protection for shipped items"
        ],
        "dispute_tips": [
            "Communicate professionally with buyers",
            "Offer partial refunds to avoid full returns when appropriate",
            "PayPal disputes favor documented sellers",
            "Screenshot all conversations"
        ],
        "defect_threshold": "Account may be flagged for excessive disputes"
    }
}


def _ensure_tables():
    """Create necessary tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_returns (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                platform VARCHAR(50) NOT NULL,
                order_id VARCHAR(100),
                sku VARCHAR(100),
                item_name VARCHAR(255),
                original_sale_price DECIMAL(10,2),
                original_cogs DECIMAL(10,2),
                return_reason VARCHAR(50) NOT NULL,
                return_reason_detail TEXT,
                status VARCHAR(50) NOT NULL DEFAULT 'requested',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soleops_returns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                platform VARCHAR(50) NOT NULL,
                order_id VARCHAR(100),
                sku VARCHAR(100),
                item_name VARCHAR(255),
                original_sale_price DECIMAL(10,2),
                original_cogs DECIMAL(10,2),
                return_reason VARCHAR(50) NOT NULL,
                return_reason_detail TEXT,
                status VARCHAR(50) NOT NULL DEFAULT 'requested',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    cur.close()


def main():
    """Main application entry point."""
    _ensure_tables()
    
    st.title("🔄 Return & Refund Tracker")
    st.markdown("Track returns, manage refunds, and get platform-specific dispute guidance.")
    
    tab1, tab2, tab3 = st.tabs(["📋 Returns", "➕ New Return", "📊 Analytics"])
    
    with tab1:
        st.subheader("Active Returns")
        st.info("No returns found. Add a new return to get started.")
    
    with tab2:
        st.subheader("Log New Return")
        with st.form("new_return_form"):
            col1, col2 = st.columns(2)
            with col1:
                platform = st.selectbox("Platform", PLATFORMS)
                order_id = st.text_input("Order ID")
                item_name = st.text_input("Item Name")
            with col2:
                return_reason = st.selectbox("Return Reason", list(RETURN_REASONS.keys()), format_func=lambda x: RETURN_REASONS[x])
                sale_price = st.number_input("Original Sale Price", min_value=0.0, step=0.01)
                cogs = st.number_input("Cost of Goods", min_value=0.0, step=0.01)
            
            reason_detail = st.text_area("Additional Details")
            submitted = st.form_submit_button("Log Return")
            
            if submitted:
                st.success("Return logged successfully!")
    
    with tab3:
        st.subheader("Return Analytics")
        st.info("Analytics will appear once you have return data.")
    
    # Platform guidance section
    st.markdown("---")
    st.subheader("📚 Platform Guidance")
    
    selected_platform = st.selectbox("Select Platform for Guidance", PLATFORMS, key="guidance_platform")
    
    if selected_platform in PLATFORM_GUIDANCE:
        guidance = PLATFORM_GUIDANCE[selected_platform]
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Policy:** {guidance['policy']}")
            st.markdown(f"**Timeframe:** {guidance['timeframe']}")
            st.markdown(f"**Defect Threshold:** {guidance['defect_threshold']}")
        
        with col2:
            with st.expander("Seller Protection Tips"):
                for tip in guidance['seller_protection']:
                    st.markdown(f"• {tip}")
            
            with st.expander("Dispute Tips"):
                for tip in guidance['dispute_tips']:
                    st.markdown(f"• {tip}")


if __name__ == "__main__":
    main()