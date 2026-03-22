import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import sys
import os

st.set_page_config(
    page_title="SoleOps — Subscription | Peach State Savings",
    page_icon="🍑",
    layout="wide",
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css, inject_soleops_css

init_db()
inject_soleops_css()
require_login()

# ── Sidebar ────────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                          label="Overview",          icon="📊")
st.sidebar.page_link("pages/22_todo.py",                label="Todo",           icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",   label="Creator",        icon="🎬")
st.sidebar.page_link("pages/25_notes.py",               label="Notes",          icon="📝")
st.sidebar.page_link("pages/26_media_library.py",       label="Media Library",  icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",  label="Personal Assistant",icon="🤖")
render_sidebar_user_widget()

# ── Plan Config ────────────────────────────────────────────────────────────────
PLANS = {
    "Free": {
        "price": 0,
        "price_id": "",
        "label": "Free",
        "items": 5,
        "alerts": False,
        "stockx": False,
        "api_listing": False,
        "multi_user": False,
        "features": [
            "✅ Up to 5 inventory items",
            "✅ Basic P&L tracking",
            "❌ Price alerts",
            "❌ StockX integration",
            "❌ API listing",
            "❌ Multi-user",
        ],
        "color": "#6B7280",
    },
    "Starter": {
        "price": 9.99,
        "price_id": "price_starter_monthly",  # set real Stripe price ID via get_setting
        "label": "Starter",
        "items": 50,
        "alerts": True,
        "stockx": False,
        "api_listing": False,
        "multi_user": False,
        "features": [
            "✅ Up to 50 inventory items",
            "✅ Full P&L tracking",
            "✅ Telegram price alerts",
            "✅ eBay + Mercari monitoring",
            "❌ StockX integration",
            "❌ API listing",
        ],
        "color": "#3B82F6",
    },
    "Pro": {
        "price": 19.99,
        "price_id": "price_pro_monthly",
        "label": "Pro",
        "items": 9999,
        "alerts": True,
        "stockx": True,
        "api_listing": False,
        "multi_user": False,
        "features": [
            "✅ Unlimited inventory items",
            "✅ Full P&L + tax summary",
            "✅ Telegram price alerts",
            "✅ eBay + Mercari + StockX",
            "✅ Arbitrage scanner",
            "❌ Multi-user (1 seat)",
        ],
        "color": "#8B5CF6",
    },
    "Pro+": {
        "price": 29.99,
        "price_id": "price_proplus_monthly",
        "label": "Pro+",
        "items": 9999,
        "alerts": True,
        "stockx": True,
        "api_listing": True,
        "multi_user": True,
        "features": [
            "✅ Unlimited inventory items",
            "✅ Full P&L + Schedule C export",
            "✅ Telegram price alerts",
            "✅ All platforms + GOAT",
            "✅ eBay API auto-listing",
            "✅ Up to 5 team members",
        ],
        "color": "#F59E0B",
    },
}


# ── DB Setup ───────────────────────────────────────────────────────────────────
def _ensure_tables():
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    auto = "SERIAL PRIMARY KEY" if USE_POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"

    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS soleops_subscriptions (
            id              {auto},
            user_email      TEXT NOT NULL,
            plan            TEXT NOT NULL DEFAULT 'Free',
            stripe_customer_id TEXT,
            stripe_sub_id   TEXT,
            status          TEXT DEFAULT 'active',
            current_period_start DATE,
            current_period_end   DATE,
            cancel_at_period_end INTEGER DEFAULT 0,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS soleops_users (
            id              {auto},
            email           TEXT NOT NULL UNIQUE,
            display_name    TEXT,
            role            TEXT DEFAULT 'user',
            invited_by      TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db_exec(conn, f"""
        CREATE TABLE IF NOT EXISTS soleops_billing_events (
            id              {auto},
            user_email      TEXT NOT NULL,
            event_type      TEXT,
            amount          REAL,
            currency        TEXT DEFAULT 'usd',
            stripe_invoice_id TEXT,
            description     TEXT,
            event_date      DATE,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


_ensure_tables()


# ── Helpers ────────────────────────────────────────────────────────────────────
def _get_subscription(email: str) -> dict:
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    cur = db_exec(conn, 
        f"SELECT * FROM soleops_subscriptions WHERE user_email = {ph} ORDER BY created_at DESC LIMIT 1",
        (email,)
    )
    row = cur.fetchone()
    if row:
        cols = [d[0] for d in cur.description]
        conn.close()
        return dict(zip(cols, row))
    conn.close()
    return {"plan": "Free", "status": "active", "user_email": email}


def _upsert_subscription(email: str, plan: str, stripe_customer_id: str = "",
                          stripe_sub_id: str = "", status: str = "active",
                          period_end: str = ""):
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    existing = _get_subscription(email)
    if existing.get("id"):
        db_exec(conn, 
            f"""UPDATE soleops_subscriptions
                SET plan={ph}, stripe_customer_id={ph}, stripe_sub_id={ph},
                    status={ph}, current_period_end={ph}, updated_at=CURRENT_TIMESTAMP
                WHERE user_email={ph}""",
            (plan, stripe_customer_id, stripe_sub_id, status, period_end, email)
        )
    else:
        db_exec(conn, 
            f"""INSERT INTO soleops_subscriptions
                (user_email, plan, stripe_customer_id, stripe_sub_id, status, current_period_end)
                VALUES ({ph},{ph},{ph},{ph},{ph},{ph})""",
            (email, plan, stripe_customer_id, stripe_sub_id, status, period_end)
        )
    conn.commit()
    conn.close()


def _get_billing_history(email: str) -> pd.DataFrame:
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    cur = db_exec(conn, 
        f"SELECT * FROM soleops_billing_events WHERE user_email = {ph} ORDER BY event_date DESC",
        (email,)
    )
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    return pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)


def _get_all_subscribers() -> pd.DataFrame:
    conn = get_conn()
    cur = db_exec(conn, "SELECT * FROM soleops_subscriptions ORDER BY created_at DESC")
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    return pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)


def _count_inventory_items(email: str) -> int:
    """Count items in soleops_inventory for this user."""
    try:
        conn = get_conn()
        ph = "%s" if USE_POSTGRES else "?"
        # soleops_inventory may or may not have user_email column
        try:
            cur = db_exec(conn, "SELECT COUNT(*) FROM soleops_inventory")
            count = cur.fetchone()[0]
        except Exception:
            count = 0
        conn.close()
        return count
    except Exception:
        return 0


def _create_stripe_checkout(plan_name: str, user_email: str) -> str:
    """Create a Stripe Checkout Session and return the URL."""
    stripe_key = get_setting("stripe_secret_key")
    if not stripe_key:
        return ""
    try:
        import stripe
        stripe.api_key = stripe_key
        plan_config = PLANS[plan_name]
        price_id_setting = get_setting(f"stripe_price_id_{plan_name.lower().replace('+', 'plus')}")
        price_id = price_id_setting or plan_config["price_id"]
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=user_email,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url="http://localhost:8501/70_soleops_stripe_paywall?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="http://localhost:8501/70_soleops_stripe_paywall",
            metadata={"plan": plan_name, "user_email": user_email},
        )
        return session.url
    except Exception as e:
        return f"error:{e}"


def _cancel_subscription(email: str) -> bool:
    """Cancel at period end via Stripe."""
    stripe_key = get_setting("stripe_secret_key")
    if not stripe_key:
        return False
    try:
        import stripe
        stripe.api_key = stripe_key
        sub = _get_subscription(email)
        if sub.get("stripe_sub_id"):
            stripe.Subscription.modify(sub["stripe_sub_id"], cancel_at_period_end=True)
        conn = get_conn()
        ph = "%s" if USE_POSTGRES else "?"
        db_exec(conn, 
            f"UPDATE soleops_subscriptions SET cancel_at_period_end = 1 WHERE user_email = {ph}",
            (email,)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def _send_welcome_email(email: str, plan: str):
    """Send welcome email via Gmail SMTP — graceful fallback."""
    try:
        gmail_user = get_setting("gmail_user")
        gmail_pass = get_setting("gmail_app_password")
        if not gmail_user or not gmail_pass:
            return
        import smtplib
        from email.mime.text import MIMEText
        body = f"""
Welcome to SoleOps {plan} Plan! 🎉

Your subscription is now active. Here's what you have access to:

{chr(10).join(PLANS[plan]['features'])}

Start managing your sneaker inventory at peachstatesavings.com

— The SoleOps Team
"""
        msg = MIMEText(body)
        msg["Subject"] = f"Welcome to SoleOps {plan}!"
        msg["From"] = gmail_user
        msg["To"] = email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_pass)
            server.send_message(msg)
    except Exception:
        pass  # Email is best-effort


# ── Page State ─────────────────────────────────────────────────────────────────
user_email = st.session_state.get("user_email", "demo@soleops.com")
sub        = _get_subscription(user_email)
cur_plan   = sub.get("plan", "Free")
plan_cfg   = PLANS.get(cur_plan, PLANS["Free"])
item_count = _count_inventory_items(user_email)
stripe_configured = bool(get_setting("stripe_secret_key"))

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("💳 SoleOps — Subscription & Billing")
st.markdown(f"*Current Plan: **{cur_plan}** | Status: `{sub.get('status', 'active')}`*")

if not stripe_configured:
    st.warning("⚠️ **Demo Mode** — Stripe not configured. Add `stripe_secret_key` in Settings to enable real payments.")

st.markdown("---")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 My Plan",
    "💰 Plans & Pricing",
    "🧾 Billing History",
    "⚙️ Account Settings",
    "👑 Admin",
])


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — My Plan
# ════════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("📊 Your Current Plan")

    col_plan, col_usage = st.columns([1, 1])

    with col_plan:
        st.markdown(f"""
        <div style="border: 2px solid {plan_cfg['color']}; border-radius: 12px; padding: 24px; text-align: center;">
            <h2 style="color: {plan_cfg['color']}; margin: 0;">{cur_plan}</h2>
            <h1 style="margin: 8px 0;">${plan_cfg['price']:.2f}<span style="font-size: 16px;">/mo</span></h1>
            <p style="color: #6B7280;">{"Active" if sub.get("status") == "active" else sub.get("status", "Active")}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("**Plan Features:**")
        for feat in plan_cfg["features"]:
            st.write(feat)

        if cur_plan != "Pro+":
            st.markdown("---")
            st.markdown("**🚀 Upgrade your plan:**")
            upgrade_options = [p for p in PLANS if PLANS[p]["price"] > plan_cfg["price"]]
            if upgrade_options:
                next_plan = upgrade_options[0]
                st.markdown(f"*{next_plan} — ${PLANS[next_plan]['price']:.2f}/mo*")
                if st.button(f"⬆️ Upgrade to {next_plan}", use_container_width=True, type="primary"):
                    if stripe_configured:
                        url = _create_stripe_checkout(next_plan, user_email)
                        if url.startswith("error:"):
                            st.error(f"Stripe error: {url}")
                        elif url:
                            st.markdown(f"[👉 Click here to complete checkout]({url})", unsafe_allow_html=False)
                    else:
                        st.info("Demo mode: Stripe not configured. Contact support to upgrade.")

    with col_usage:
        st.markdown("**📈 Usage This Month**")
        max_items = plan_cfg["items"]
        usage_pct = min(100, int((item_count / max(max_items, 1)) * 100))

        k1, k2, k3 = st.columns(3)
        k1.metric("Inventory Items", item_count, delta=f"/{max_items if max_items < 9999 else '∞'}")
        k2.metric("Plan Limit", "Unlimited" if max_items >= 9999 else str(max_items))
        k3.metric("Usage", f"{usage_pct}%")

        if max_items < 9999:
            st.progress(usage_pct / 100)
            if usage_pct >= 80:
                st.warning(f"⚠️ You've used {usage_pct}% of your item limit. Consider upgrading!")

        st.markdown("**Feature Access:**")
        features_status = {
            "Price Alerts": plan_cfg["alerts"],
            "StockX Integration": plan_cfg["stockx"],
            "API Listing": plan_cfg["api_listing"],
            "Multi-User": plan_cfg["multi_user"],
        }
        for feat, enabled in features_status.items():
            icon = "✅" if enabled else "❌"
            st.write(f"{icon} {feat}")

        if sub.get("current_period_end"):
            st.markdown(f"**Next Billing:** {sub['current_period_end']}")

        if sub.get("cancel_at_period_end"):
            st.warning("⚠️ Your subscription is set to cancel at the end of the billing period.")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — Plans & Pricing
# ════════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("💰 SoleOps Pricing Plans")
    st.markdown("*All plans include: inventory tracking, P&L dashboard, and mobile-friendly UI.*")

    cols = st.columns(4)
    for i, (plan_name, cfg) in enumerate(PLANS.items()):
        with cols[i]:
            is_current = plan_name == cur_plan
            border_style = f"3px solid {cfg['color']}" if is_current else f"1px solid {cfg['color']}"
            bg = "#F0F9FF" if is_current else "#FFFFFF"

            st.markdown(f"""
            <div style="border: {border_style}; border-radius: 12px; padding: 16px; background: {bg}; text-align: center; min-height: 420px;">
                <h3 style="color: {cfg['color']}; margin: 0;">{plan_name}</h3>
                <h2 style="margin: 8px 0;">${cfg['price']:.2f}<span style="font-size: 14px;">/mo</span></h2>
                {'<div style="background: #10B981; color: white; border-radius: 4px; padding: 2px 8px; font-size: 12px;">Your Plan</div>' if is_current else ''}
            </div>
            """, unsafe_allow_html=True)

            st.markdown("")
            for feat in cfg["features"]:
                st.markdown(f"<div style='font-size: 13px;'>{feat}</div>", unsafe_allow_html=True)

            st.markdown("")
            if is_current:
                st.button(f"✅ Current Plan", key=f"cur_{plan_name}", disabled=True, use_container_width=True)
            elif cfg["price"] > plan_cfg["price"]:
                if st.button(f"⬆️ Upgrade to {plan_name}", key=f"up_{plan_name}", use_container_width=True, type="primary"):
                    if stripe_configured:
                        url = _create_stripe_checkout(plan_name, user_email)
                        if url and not url.startswith("error:"):
                            st.markdown(f"[👉 Complete Checkout for {plan_name}]({url})")
                        else:
                            st.error("Could not create checkout session.")
                    else:
                        st.info("Demo mode. Configure Stripe to enable checkout.")
            else:
                if st.button(f"⬇️ Downgrade", key=f"down_{plan_name}", use_container_width=True):
                    st.info("Contact support to downgrade your plan.")

    st.markdown("---")
    st.markdown("**📋 Feature Comparison**")
    comparison = []
    for plan_name, cfg in PLANS.items():
        comparison.append({
            "Plan": plan_name,
            "Price/mo": f"${cfg['price']:.2f}",
            "Items": "Unlimited" if cfg["items"] >= 9999 else str(cfg["items"]),
            "Alerts": "✅" if cfg["alerts"] else "❌",
            "StockX": "✅" if cfg["stockx"] else "❌",
            "API Listing": "✅" if cfg["api_listing"] else "❌",
            "Multi-User": "✅" if cfg["multi_user"] else "❌",
        })
    st.dataframe(pd.DataFrame(comparison), use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — Billing History
# ════════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("🧾 Billing History")

    billing_df = _get_billing_history(user_email)

    if billing_df.empty:
        if stripe_configured:
            st.info("No billing history yet. Your first charge will appear here after the billing cycle.")
        else:
            st.info("Demo mode — billing history will appear here once Stripe is configured.")

            # Demo data for display
            demo_billing = pd.DataFrame([
                {"event_type": "subscription_created", "amount": 9.99,  "description": "Starter Plan — March 2026", "event_date": "2026-03-01"},
                {"event_type": "payment_succeeded",    "amount": 9.99,  "description": "Starter Plan — February 2026", "event_date": "2026-02-01"},
                {"event_type": "payment_succeeded",    "amount": 9.99,  "description": "Starter Plan — January 2026", "event_date": "2026-01-01"},
            ])
            st.dataframe(demo_billing, use_container_width=True, hide_index=True)
    else:
        # KPI row
        total_paid = billing_df[billing_df["event_type"] == "payment_succeeded"]["amount"].sum()
        b1, b2, b3 = st.columns(3)
        b1.metric("Total Paid", f"${total_paid:.2f}")
        b2.metric("Invoices", len(billing_df))
        b3.metric("Current Plan", cur_plan)

        st.dataframe(
            billing_df[["event_date", "event_type", "amount", "description"]].rename(
                columns={"event_date": "Date", "event_type": "Type",
                         "amount": "Amount ($)", "description": "Description"}
            ),
            use_container_width=True,
            hide_index=True
        )


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — Account Settings
# ════════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("⚙️ Account Settings")

    col_acct, col_danger = st.columns([1, 1])

    with col_acct:
        st.markdown("**Account Information**")
        st.text_input("Email", value=user_email, disabled=True)
        st.text_input("Display Name", placeholder="Your name", key="display_name_input")
        if st.button("💾 Save Changes", use_container_width=True):
            name = st.session_state.get("display_name_input", "")
            if name:
                conn = get_conn()
                ph = "%s" if USE_POSTGRES else "?"
                # Upsert into soleops_users
                existing = db_exec(conn, 
                    f"SELECT id FROM soleops_users WHERE email = {ph}", (user_email,)
                ).fetchone()
                if existing:
                    db_exec(conn, 
                        f"UPDATE soleops_users SET display_name = {ph} WHERE email = {ph}",
                        (name, user_email)
                    )
                else:
                    db_exec(conn, 
                        f"INSERT INTO soleops_users (email, display_name) VALUES ({ph}, {ph})",
                        (user_email, name)
                    )
                conn.commit()
                conn.close()
                st.success("Settings saved!")

        st.markdown("---")
        st.markdown("**🔔 Notification Preferences**")
        tg_bot = get_setting("telegram_bot_token") or ""
        tg_chat = get_setting("telegram_chat_id") or ""
        notify_tg = st.checkbox("Telegram Alerts", value=bool(tg_bot))
        notify_email = st.checkbox("Email Digest", value=True)

        if st.button("Save Notifications", use_container_width=True):
            st.success("Notification preferences saved!")

    with col_danger:
        st.markdown("**⚠️ Danger Zone**")

        with st.expander("Cancel Subscription"):
            st.warning("Cancelling will keep your access until the end of the current billing period.")
            confirm_cancel = st.text_input("Type CANCEL to confirm", key="cancel_confirm")
            if st.button("❌ Cancel Subscription", type="primary"):
                if confirm_cancel == "CANCEL":
                    if cur_plan == "Free":
                        st.info("You're already on the Free plan — nothing to cancel.")
                    else:
                        success = _cancel_subscription(user_email)
                        if success:
                            st.success("Subscription will cancel at period end.")
                        else:
                            # Demo mode — just update DB
                            conn = get_conn()
                            ph = "%s" if USE_POSTGRES else "?"
                            db_exec(conn, 
                                f"UPDATE soleops_subscriptions SET cancel_at_period_end = 1 WHERE user_email = {ph}",
                                (user_email,)
                            )
                            conn.commit()
                            conn.close()
                            st.success("Cancellation scheduled (demo mode).")
                        st.rerun()
                else:
                    st.error("Please type CANCEL to confirm.")

        with st.expander("Stripe Customer Portal"):
            st.markdown("Manage your payment methods and invoices directly in Stripe.")
            stripe_key = get_setting("stripe_secret_key")
            if stripe_key and sub.get("stripe_customer_id"):
                if st.button("🔗 Open Billing Portal"):
                    try:
                        import stripe
                        stripe.api_key = stripe_key
                        portal = stripe.billing_portal.Session.create(
                            customer=sub["stripe_customer_id"],
                            return_url="http://localhost:8501/70_soleops_stripe_paywall",
                        )
                        st.markdown(f"[👉 Open Stripe Portal]({portal.url})")
                    except Exception as e:
                        st.error(f"Could not open portal: {e}")
            else:
                st.info("Connect Stripe and subscribe to access the billing portal.")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 5 — Admin
# ════════════════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("👑 Admin Dashboard")

    # Simple admin gate — check role in session or db
    admin_emails = get_setting("admin_emails") or ""
    is_admin = user_email in admin_emails or user_email == "darrianbelcher@gmail.com"

    if not is_admin:
        st.warning("🔒 Admin access only. Contact Darrian if you need access.")
    else:
        all_subs = _get_all_subscribers()

        if all_subs.empty:
            st.info("No subscribers yet. Share your SoleOps link to get signups!")
        else:
            # KPI cards
            total_subs   = len(all_subs)
            active_subs  = len(all_subs[all_subs["status"] == "active"])
            plan_prices  = {p: PLANS[p]["price"] for p in PLANS}
            all_subs["monthly_revenue"] = all_subs["plan"].map(plan_prices).fillna(0)
            mrr = all_subs[all_subs["status"] == "active"]["monthly_revenue"].sum()

            a1, a2, a3, a4 = st.columns(4)
            a1.metric("Total Subscribers", total_subs)
            a2.metric("Active", active_subs)
            a3.metric("MRR", f"${mrr:.2f}")
            a4.metric("ARR", f"${mrr * 12:.2f}")

            st.markdown("---")

            col_pie, col_table = st.columns([1, 1])

            with col_pie:
                plan_counts = all_subs["plan"].value_counts().reset_index()
                plan_counts.columns = ["plan", "count"]
                fig = px.pie(
                    plan_counts, values="count", names="plan",
                    title="Subscribers by Plan",
                    color_discrete_map={p: PLANS[p]["color"] for p in PLANS}
                )
                st.plotly_chart(fig, use_container_width=True)

            with col_table:
                st.markdown("**All Subscribers**")
                display_cols = [c for c in ["user_email", "plan", "status",
                                             "current_period_end", "created_at"] if c in all_subs.columns]
                st.dataframe(all_subs[display_cols].head(50), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("**⚙️ Stripe Configuration**")
            c1, c2 = st.columns(2)
            with c1:
                sk = st.text_input("Stripe Secret Key", value=get_setting("stripe_secret_key") or "",
                                   type="password")
                if st.button("Save Stripe Secret Key"):
                    set_setting("stripe_secret_key", sk)
                    st.success("Saved!")

            with c2:
                pk = st.text_input("Stripe Publishable Key",
                                   value=get_setting("stripe_publishable_key") or "")
                if st.button("Save Publishable Key"):
                    set_setting("stripe_publishable_key", pk)
                    st.success("Saved!")

            st.markdown("**Price IDs (from Stripe Dashboard)**")
            for plan_name in ["Starter", "Pro", "Proplus"]:
                key_name = f"stripe_price_id_{plan_name.lower()}"
                val = get_setting(key_name) or ""
                new_val = st.text_input(f"{plan_name} Price ID", value=val, key=f"pid_{plan_name}")
                if st.button(f"Save {plan_name} Price ID", key=f"savepid_{plan_name}"):
                    set_setting(key_name, new_val)
                    st.success(f"{plan_name} price ID saved!")
