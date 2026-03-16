"""
SoleOps: Stale Inventory Alert System — Page 84
================================================
Autonomous stale inventory monitor with:
  - AI-powered markdown strategy per pair (Claude)
  - Telegram alerts (individual + bulk digest)
  - Weekly email digest via Gmail SMTP
  - Cross-listing recommendations (eBay ↔ Mercari)
  - Scheduled agent integration (auto-seeds weekly scan task)
  - Alert history log
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, timedelta
import sys
import os

st.set_page_config(
    page_title="SoleOps — Stale Inventory | Peach State Savings",
    page_icon="🍑",
    layout="wide",
    initial_sidebar_state="auto",
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_soleops_css

init_db()
inject_soleops_css()
require_login()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                          label="Overview",           icon="📊")
st.sidebar.page_link("pages/22_todo.py",                label="✅ Todo",            icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",   label="🎬 Creator",         icon="🎬")
st.sidebar.page_link("pages/25_notes.py",               label="📝 Notes",           icon="📝")
st.sidebar.page_link("pages/26_media_library.py",       label="🎵 Media Library",   icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",  label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()

# ── Constants ──────────────────────────────────────────────────────────────────
EBAY_FEE_RATE     = 0.129
EBAY_FEE_FIXED    = 0.30
MERCARI_FEE_RATE  = 0.10
MERCARI_FEE_FIXED = 0.30

AGING_TIERS = [
    (0,  7,  "🟢 Fresh",    0.00, 0),
    (7,  14, "🟡 Warm",     0.05, 1),
    (14, 21, "🟠 Aging",    0.10, 2),
    (21, 30, "🔴 Stale",    0.15, 3),
    (30, 999,"⚫ Critical", 0.20, 4),
]

TIER_COLORS = {
    "🟢 Fresh":    "#22c55e",
    "🟡 Warm":     "#eab308",
    "🟠 Aging":    "#f97316",
    "🔴 Stale":    "#ef4444",
    "⚫ Critical": "#6b7280",
}

DEFAULT_STALE_DAYS = 14


# ══════════════════════════════════════════════════════════════════════════════
# ── DB helpers ────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _ensure_tables() -> None:
    conn = get_conn()
    if USE_POSTGRES:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS soleops_stale_alerts (
                id              SERIAL PRIMARY KEY,
                inventory_id    INTEGER NOT NULL,
                user_id         INTEGER NOT NULL,
                shoe_name       TEXT NOT NULL,
                size            TEXT NOT NULL,
                days_listed     INTEGER NOT NULL,
                listed_price    REAL DEFAULT 0,
                suggested_price REAL DEFAULT 0,
                ai_strategy     TEXT DEFAULT '',
                alert_type      TEXT DEFAULT 'telegram',
                sent_at         TEXT DEFAULT (to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
                acknowledged    INTEGER DEFAULT 0,
                action_taken    TEXT DEFAULT ''
            )
        """)
    else:
        db_exec(conn, """
            CREATE TABLE IF NOT EXISTS soleops_stale_alerts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id    INTEGER NOT NULL,
                user_id         INTEGER NOT NULL,
                shoe_name       TEXT NOT NULL,
                size            TEXT NOT NULL,
                days_listed     INTEGER NOT NULL,
                listed_price    REAL DEFAULT 0,
                suggested_price REAL DEFAULT 0,
                ai_strategy     TEXT DEFAULT '',
                alert_type      TEXT DEFAULT 'telegram',
                sent_at         TEXT DEFAULT (datetime('now')),
                acknowledged    INTEGER DEFAULT 0,
                action_taken    TEXT DEFAULT ''
            )
        """)
    conn.commit()
    conn.close()


def _seed_scheduled_task() -> None:
    """Auto-seed a weekly stale inventory scan into agent_scheduled_tasks if not already there."""
    try:
        conn = get_conn()
        ph = "%s" if USE_POSTGRES else "?"
        row = conn.execute(
            f"SELECT id FROM agent_scheduled_tasks WHERE task_name = {ph}",
            ("SoleOps Stale Inventory Weekly Scan",)
        ).fetchone()
        if not row:
            now = datetime.now()
            days_ahead = 7 - now.weekday()  # Next Monday
            if days_ahead <= 0:
                days_ahead += 7
            next_run = (now + timedelta(days=days_ahead)).replace(
                hour=9, minute=0, second=0, microsecond=0
            )
            db_exec(conn, f"""
                INSERT INTO agent_scheduled_tasks
                    (task_name, description, backlog_item, schedule_type,
                     schedule_day, schedule_hour, next_run, created_by)
                VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})
            """, (
                "SoleOps Stale Inventory Weekly Scan",
                "Scan all SoleOps inventory for pairs 14+ days old. Generate AI markdown strategy and send Telegram digest.",
                "SoleOps: Stale Inventory Alert System (page 84)",
                "weekly", 0, 9,
                next_run.strftime("%Y-%m-%d %H:%M:%S"),
                "system",
            ))
            conn.commit()
        conn.close()
    except Exception:
        pass  # agent_scheduled_tasks may not exist in all envs


_ensure_tables()
_seed_scheduled_task()


# ── Inventory helpers ──────────────────────────────────────────────────────────

def _calc_days_listed(listed_date_val) -> int:
    if not listed_date_val:
        return 0
    try:
        if isinstance(listed_date_val, str):
            listed = datetime.strptime(str(listed_date_val)[:10], "%Y-%m-%d").date()
        else:
            listed = listed_date_val
        return max(0, (date.today() - listed).days)
    except Exception:
        return 0


def _get_aging_tier(days: int) -> dict:
    for lo, hi, label, drop_pct, tier_idx in AGING_TIERS:
        if lo <= days < hi:
            return {"label": label, "drop_pct": drop_pct, "tier": tier_idx}
    return {"label": "⚫ Critical", "drop_pct": 0.20, "tier": 4}


def _calc_profit(sell_price: float, cost_basis: float, platform: str) -> float:
    p = (platform or "").lower()
    if "ebay" in p:
        fees = (sell_price * EBAY_FEE_RATE) + EBAY_FEE_FIXED
    elif "mercari" in p:
        fees = (sell_price * MERCARI_FEE_RATE) + MERCARI_FEE_FIXED
    else:
        fees = sell_price * 0.12
    return round(sell_price - fees - cost_basis, 2)


def _load_stale_inventory(user_id: int, min_days: int = DEFAULT_STALE_DAYS) -> list[dict]:
    """Load all active inventory items older than min_days, enriched with tier data."""
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    cur = conn.execute(f"""
        SELECT id, shoe_name, brand, colorway, size, cost_basis, condition,
               listed_date, listed_price, listed_platform, notes
        FROM soleops_inventory
        WHERE user_id = {ph} AND status = 'inventory'
        ORDER BY listed_date ASC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()

    items = []
    for r in rows:
        days = _calc_days_listed(r[7])
        if days < min_days:
            continue
        tier = _get_aging_tier(days)
        listed_price = float(r[8]) if r[8] else 0.0
        cost_basis   = float(r[5]) if r[5] else 0.0
        sugg_price   = round(listed_price * (1 - tier["drop_pct"]), 2) if listed_price and tier["drop_pct"] > 0 else listed_price
        profit_sugg  = _calc_profit(sugg_price, cost_basis, r[9] or "ebay") if sugg_price > 0 else 0.0
        items.append({
            "id":                  r[0],
            "shoe_name":           r[1],
            "brand":               r[2] or "",
            "colorway":            r[3] or "",
            "size":                r[4],
            "cost_basis":          cost_basis,
            "condition":           r[6] or "",
            "listed_date":         r[7],
            "listed_price":        listed_price,
            "listed_platform":     r[9] or "Unknown",
            "notes":               r[10] or "",
            "days_listed":         days,
            "aging_tier":          tier,
            "suggested_price":     sugg_price,
            "profit_at_suggested": profit_sugg,
        })
    return sorted(items, key=lambda x: x["days_listed"], reverse=True)


def _load_full_inventory(user_id: int) -> list[dict]:
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    cur = conn.execute(f"""
        SELECT id, shoe_name, size, cost_basis, listed_date, listed_price, listed_platform
        FROM soleops_inventory
        WHERE user_id = {ph} AND status = 'inventory'
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    items = []
    for r in rows:
        days = _calc_days_listed(r[4])
        tier = _get_aging_tier(days)
        items.append({
            "id":              r[0],
            "shoe_name":       r[1],
            "size":            r[2],
            "cost_basis":      float(r[3]) if r[3] else 0.0,
            "days_listed":     days,
            "aging_tier":      tier,
            "listed_price":    float(r[5]) if r[5] else 0.0,
            "listed_platform": r[6] or "Unknown",
        })
    return items


def _log_alert_sent(
    inventory_id: int,
    user_id: int,
    shoe_name: str,
    size: str,
    days_listed: int,
    listed_price: float,
    suggested_price: float,
    ai_strategy: str,
    alert_type: str = "telegram",
) -> None:
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    db_exec(conn, f"""
        INSERT INTO soleops_stale_alerts
            (inventory_id, user_id, shoe_name, size, days_listed,
             listed_price, suggested_price, ai_strategy, alert_type)
        VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})
    """, (inventory_id, user_id, shoe_name, size, days_listed,
          listed_price, suggested_price, ai_strategy, alert_type))
    conn.commit()
    conn.close()


def _load_alert_history(user_id: int, limit: int = 40) -> list[dict]:
    conn = get_conn()
    ph = "%s" if USE_POSTGRES else "?"
    cur = conn.execute(f"""
        SELECT shoe_name, size, days_listed, listed_price,
               suggested_price, alert_type, sent_at, action_taken
        FROM soleops_stale_alerts
        WHERE user_id = {ph}
        ORDER BY sent_at DESC LIMIT {ph}
    """, (user_id, limit))
    rows = cur.fetchall()
    conn.close()
    cols = ["shoe_name", "size", "days_listed", "listed_price",
            "suggested_price", "alert_type", "sent_at", "action_taken"]
    return [dict(zip(cols, r)) for r in rows]


# ── AI helpers ─────────────────────────────────────────────────────────────────

def _get_ai_bulk_strategy(items: list[dict]) -> str:
    """Claude generates a comprehensive markdown strategy for all stale inventory."""
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "⚠️ Anthropic API key not configured. Add it in Settings."
    if not items:
        return "No stale inventory to analyze."

    import anthropic as _ant
    summary_lines = [
        f"- {i['shoe_name']} Sz {i['size']} | {i['days_listed']}d listed on {i['listed_platform']} "
        f"| Cost: ${i['cost_basis']:.0f} | Listed: ${i['listed_price']:.0f} | "
        f"Suggested: ${i['suggested_price']:.0f} ({i['aging_tier']['label']})"
        for i in items[:10]
    ]
    try:
        client = _ant.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=900,
            messages=[{"role": "user", "content":
                "You are a sneaker resale strategist. Here is stale inventory for a reseller:\n\n"
                + "\n".join(summary_lines)
                + "\n\nFor each pair give ONE specific action:\n"
                "- Exact new price to list\n"
                "- Should they switch platforms (eBay↔Mercari)?\n"
                "- Auction vs BIN recommendation\n"
                "- Any bundle opportunities?\n"
                "Be direct and use real dollar amounts. Max 200 words total."}]
        )
        return resp.content[0].text
    except Exception as e:
        return f"AI error: {str(e)}"


def _get_ai_single_strategy(item: dict) -> str:
    """Claude one-liner strategy for a single stale pair."""
    api_key = get_setting("anthropic_api_key")
    if not api_key:
        return "Configure Anthropic API key in Settings."
    import anthropic as _ant
    try:
        client = _ant.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=180,
            messages=[{"role": "user", "content":
                f"{item['shoe_name']} Sz {item['size']} | "
                f"Cost ${item['cost_basis']:.0f} | Listed ${item['listed_price']:.0f} "
                f"on {item['listed_platform']} | {item['days_listed']} days | "
                f"{item['aging_tier']['label']}\n\n"
                "Give one specific pricing action in 2 sentences. Include exact new price."}]
        )
        return resp.content[0].text
    except Exception as e:
        return f"AI error: {str(e)}"


# ── Notifications ──────────────────────────────────────────────────────────────

def _send_telegram(message: str) -> bool:
    token   = get_setting("telegram_bot_token")
    chat_id = get_setting("telegram_chat_id")
    if not token or not chat_id:
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False


def _send_single_telegram_alert(item: dict, strategy: str = "") -> bool:
    tier = item["aging_tier"]
    msg = (
        f"⏰ <b>STALE INVENTORY ALERT</b>\n\n"
        f"👟 <b>{item['shoe_name']}</b> (Sz {item['size']})\n"
        f"📅 {item['days_listed']} days on {item['listed_platform']}\n"
        f"💰 Listed: ${item['listed_price']:.0f} | Cost: ${item['cost_basis']:.0f}\n"
        f"💡 Suggested: <b>${item['suggested_price']:.0f}</b> ({tier['label']})\n"
        f"💵 Profit at drop: ${item['profit_at_suggested']:.0f} after fees"
    )
    if strategy:
        msg += f"\n\n🤖 <b>Strategy:</b> {strategy[:200]}"
    return _send_telegram(msg)


def _send_bulk_digest_telegram(items: list[dict], ai_strategy: str = "") -> bool:
    if not items:
        return False
    total_at_risk = sum(i["listed_price"] - i["cost_basis"] for i in items if i["listed_price"])
    lines = [
        "⏰ <b>SOLEOPS WEEKLY STALE DIGEST</b>",
        f"📊 {len(items)} pairs need attention\n",
    ]
    for item in items[:10]:
        tier = item["aging_tier"]
        lines.append(
            f"{tier['label']} <b>{item['shoe_name']}</b> Sz {item['size']} — "
            f"{item['days_listed']}d → drop to <b>${item['suggested_price']:.0f}</b>"
        )
    if len(items) > 10:
        lines.append(f"...and {len(items) - 10} more pairs")
    lines.append(f"\n💰 Total $ at risk: ${total_at_risk:,.0f}")
    if ai_strategy:
        lines.append(f"\n🤖 <b>AI Strategy:</b>\n{ai_strategy[:350]}")
    lines.append("\n📱 Open SoleOps → peachstatesavings.com")
    return _send_telegram("\n".join(lines))


def _send_email_digest(items: list[dict], ai_strategy: str, user_email: str) -> bool:
    """Email the weekly stale inventory digest with HTML table + AI strategy."""
    gmail_user = get_setting("gmail_user")
    gmail_pass = get_setting("gmail_app_password")
    if not gmail_user or not gmail_pass:
        return False
    try:
        rows_html = "".join([
            f"<tr>"
            f"<td style='padding:6px 10px;'><b>{i['shoe_name']}</b></td>"
            f"<td style='padding:6px 10px;'>{i['size']}</td>"
            f"<td style='padding:6px 10px;'>{i['days_listed']}d</td>"
            f"<td style='padding:6px 10px;'>${i['listed_price']:.0f}</td>"
            f"<td style='padding:6px 10px; color:#e8924f;'><b>${i['suggested_price']:.0f}</b></td>"
            f"<td style='padding:6px 10px;'>{i['aging_tier']['label']}</td>"
            f"</tr>"
            for i in items
        ])
        body = f"""
<html><body style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;color:#222;">
<h2 style="color:#e8924f;">⏰ SoleOps Stale Inventory Report</h2>
<p>You have <strong>{len(items)}</strong> pairs that need attention.
<em>{date.today().strftime('%B %d, %Y')}</em></p>
<table border="0" cellpadding="0" cellspacing="0"
  style="border-collapse:collapse;width:100%;background:#fff;border:1px solid #eee;">
<thead style="background:#f5f5f5;">
  <tr>
    <th style="padding:8px 10px;text-align:left;">Shoe</th>
    <th style="padding:8px 10px;text-align:left;">Size</th>
    <th style="padding:8px 10px;text-align:left;">Days</th>
    <th style="padding:8px 10px;text-align:left;">Listed $</th>
    <th style="padding:8px 10px;text-align:left;color:#e8924f;">Suggested $</th>
    <th style="padding:8px 10px;text-align:left;">Status</th>
  </tr>
</thead>
<tbody>{rows_html}</tbody>
</table>
<h3 style="color:#e8924f;margin-top:28px;">🤖 AI Markdown Strategy</h3>
<div style="background:#fdf6f0;border-left:4px solid #e8924f;padding:14px 18px;
  border-radius:0 8px 8px 0;font-size:14px;line-height:1.6;">
{ai_strategy.replace(chr(10), '<br>')}
</div>
<p style="margin-top:24px;">
  <a href="https://peachstatesavings.com/84_soleops_stale_inventory"
     style="background:#e8924f;color:#fff;padding:10px 22px;text-decoration:none;
     border-radius:6px;font-weight:bold;">Open SoleOps →</a>
</p>
<p style="color:#aaa;font-size:11px;margin-top:20px;">
  Sent by SoleOps Automated Agent · peachstatesavings.com
</p>
</body></html>"""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = (
            f"SoleOps: {len(items)} stale pairs — "
            f"{date.today().strftime('%b %d')}"
        )
        msg["From"]    = gmail_user
        msg["To"]      = user_email
        msg.attach(MIMEText(body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_pass)
            server.send_message(msg)
        return True
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# ── Page ──────────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

user          = st.session_state.get("user", {})
user_id       = user.get("id", 1)
user_email_str = user.get("email", "")

st.title("⏰ SoleOps — Stale Inventory Alert System")
st.caption(
    "Autonomous monitoring for aging sneaker inventory. "
    "AI-powered markdown strategy + Telegram alerts before your profit evaporates."
)

# ── Alert threshold ────────────────────────────────────────────────────────────
with st.expander("⚙️ Alert Thresholds", expanded=False):
    c1, c2 = st.columns(2)
    alert_threshold = c1.slider(
        "Minimum days listed to trigger alert", 7, 30, DEFAULT_STALE_DAYS, 1,
        help="Pairs listed longer than this will appear in the alert center"
    )
    critical_threshold = c2.slider(
        "Critical threshold (days)", 21, 60, 30, 1,
        help="Pairs listed longer than this are marked ⚫ Critical"
    )

stale_items = _load_stale_inventory(user_id, min_days=alert_threshold)
all_items   = _load_full_inventory(user_id)
critical    = [i for i in stale_items if i["days_listed"] >= critical_threshold]
total_at_risk = sum(i["listed_price"] - i["cost_basis"] for i in stale_items if i["listed_price"])
avg_days    = int(sum(i["days_listed"] for i in stale_items) / max(len(stale_items), 1)) if stale_items else 0
est_recover = sum(i["profit_at_suggested"] for i in stale_items if i["profit_at_suggested"] > 0)

# ── KPI row ────────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("⏰ Stale Pairs",       len(stale_items), delta=f"of {len(all_items)} total")
k2.metric("⚫ Critical (30d+)",   len(critical),
          delta_color="inverse" if critical else "normal")
k3.metric("💰 $ At Risk",        f"${total_at_risk:,.0f}",
          help="Listed value minus cost basis on stale pairs")
k4.metric("📅 Avg Days Listed",  f"{avg_days}d" if stale_items else "—")
k5.metric("💵 Est. Recover (drops)", f"${est_recover:,.0f}",
          help="Estimated total profit if all drops are applied")

st.markdown("---")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_alert, tab_overview, tab_ai, tab_history, tab_sched = st.tabs([
    "⚠️ Alert Center",
    "📊 Overview",
    "🤖 AI Strategy",
    "📜 Alert History",
    "⏰ Auto-Schedule",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Alert Center
# ══════════════════════════════════════════════════════════════════════════════
with tab_alert:
    if not stale_items:
        st.success(
            f"🎉 All inventory is fresh! No pairs have been listed for "
            f"{alert_threshold}+ days. Come back later."
        )
    else:
        # ── Bulk action buttons ───────────────────────────────────────────────
        bc1, bc2, bc3 = st.columns(3)

        with bc1:
            if st.button(
                f"📱 Telegram All ({len(stale_items)} pairs)",
                type="primary",
                use_container_width=True,
            ):
                with st.spinner("Sending individual Telegram alerts..."):
                    sent = 0
                    for item in stale_items:
                        ok = _send_single_telegram_alert(item)
                        if ok:
                            _log_alert_sent(
                                item["id"], user_id, item["shoe_name"], item["size"],
                                item["days_listed"], item["listed_price"],
                                item["suggested_price"], "", "telegram"
                            )
                            sent += 1
                if sent > 0:
                    st.success(f"✅ Sent {sent} Telegram alerts!")
                else:
                    st.warning("⚠️ Configure Telegram bot token + chat ID in Settings.")

        with bc2:
            if st.button("📧 Email Digest", use_container_width=True):
                if not user_email_str:
                    st.warning("No email on your account.")
                else:
                    with st.spinner("Generating AI strategy + emailing digest..."):
                        strategy_bulk = _get_ai_bulk_strategy(stale_items)
                        ok = _send_email_digest(stale_items, strategy_bulk, user_email_str)
                    if ok:
                        st.success(f"✅ Digest emailed to {user_email_str}")
                    else:
                        st.warning("⚠️ Configure Gmail credentials in Settings.")

        with bc3:
            if st.button("📱 Bulk Digest (1 message)", use_container_width=True):
                with st.spinner("Generating digest..."):
                    strategy_bulk = _get_ai_bulk_strategy(stale_items)
                    ok = _send_bulk_digest_telegram(stale_items, strategy_bulk)
                if ok:
                    st.success("✅ Bulk digest sent via Telegram!")
                else:
                    st.warning("⚠️ Configure Telegram in Settings.")

        st.markdown("---")

        # ── Per-pair cards by tier ─────────────────────────────────────────────
        tier_groups: dict[str, list] = {}
        for item in stale_items:
            tier_groups.setdefault(item["aging_tier"]["label"], []).append(item)

        for tier_label in ["⚫ Critical", "🔴 Stale", "🟠 Aging", "🟡 Warm"]:
            group = tier_groups.get(tier_label, [])
            if not group:
                continue
            color = TIER_COLORS.get(tier_label, "#888")
            st.markdown(
                f"<h3 style='color:{color};'>{tier_label} — "
                f"{len(group)} pair{'s' if len(group) != 1 else ''}</h3>",
                unsafe_allow_html=True,
            )
            for item in group:
                with st.container():
                    ic1, ic2, ic3, ic4, ic5 = st.columns([3, 1, 1, 1, 2])
                    ic1.markdown(
                        f"**👟 {item['shoe_name']}** Sz {item['size']}\n\n"
                        f"`{item['listed_platform']}`"
                    )
                    ic2.metric("Days", item["days_listed"])
                    ic3.metric(
                        "Listed $",
                        f"${item['listed_price']:.0f}" if item["listed_price"] else "—",
                    )
                    drop_pct = int(item["aging_tier"]["drop_pct"] * 100)
                    ic4.metric(
                        "Drop to",
                        f"${item['suggested_price']:.0f}" if item["suggested_price"] else "—",
                        delta=f"-{drop_pct}%" if drop_pct else None,
                        delta_color="inverse",
                    )
                    with ic5:
                        profit_icon = "💵" if item["profit_at_suggested"] > 0 else "📉"
                        st.metric(
                            f"{profit_icon} Profit @ drop",
                            f"${item['profit_at_suggested']:.0f}",
                        )

                    btn1, btn2, btn3 = st.columns(3)
                    with btn1:
                        if st.button(
                            "📱 Alert", key=f"tg_{item['id']}", use_container_width=True
                        ):
                            ok = _send_single_telegram_alert(item)
                            if ok:
                                _log_alert_sent(
                                    item["id"], user_id, item["shoe_name"], item["size"],
                                    item["days_listed"], item["listed_price"],
                                    item["suggested_price"], "", "telegram"
                                )
                                st.success("✅ Sent!")
                            else:
                                st.warning("Configure Telegram in Settings.")
                    with btn2:
                        if st.button(
                            "🤖 AI Strategy", key=f"ai_{item['id']}", use_container_width=True
                        ):
                            with st.spinner("Asking Claude..."):
                                strategy = _get_ai_single_strategy(item)
                            st.info(f"**Claude:** {strategy}")
                    with btn3:
                        alt_plat = "Mercari" if "ebay" in item["listed_platform"].lower() else "eBay"
                        st.markdown(f"💡 Cross-list on **{alt_plat}**?")

                    st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Overview Charts
# ══════════════════════════════════════════════════════════════════════════════
with tab_overview:
    if not all_items:
        st.info("No inventory yet. Add pairs in SoleOps Inventory Analyzer (page 65).")
    else:
        tier_counts: dict[str, int] = {}
        for item in all_items:
            tier_counts[item["aging_tier"]["label"]] = tier_counts.get(item["aging_tier"]["label"], 0) + 1

        tier_df = pd.DataFrame(
            [{"Status": k, "Pairs": v} for k, v in tier_counts.items()]
        )

        ch1, ch2 = st.columns(2)
        with ch1:
            fig = px.pie(
                tier_df, values="Pairs", names="Status",
                title="Inventory Age Distribution",
                color="Status",
                color_discrete_map=TIER_COLORS,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(template="plotly_dark", showlegend=True)
            st.plotly_chart(fig, use_container_width=True)

        with ch2:
            scatter_data = pd.DataFrame([{
                "Shoe":        f"{i['shoe_name'][:22]} Sz{i['size']}",
                "Days Listed": i["days_listed"],
                "Listed Price": i["listed_price"],
                "Status":      i["aging_tier"]["label"],
                "Platform":    i["listed_platform"],
            } for i in all_items if i["listed_price"] > 0])

            if not scatter_data.empty:
                fig2 = px.scatter(
                    scatter_data, x="Days Listed", y="Listed Price",
                    color="Status", hover_data=["Shoe", "Platform"],
                    title="Price vs. Days Listed",
                    color_discrete_map=TIER_COLORS,
                )
                fig2.update_layout(template="plotly_dark")
                st.plotly_chart(fig2, use_container_width=True)

        if stale_items:
            st.subheader("📊 Stale Pairs by Platform")
            plat_data: dict[str, int] = {}
            for i in stale_items:
                plat_data[i["listed_platform"]] = plat_data.get(i["listed_platform"], 0) + 1
            plat_df = pd.DataFrame(list(plat_data.items()), columns=["Platform", "Stale Pairs"])
            fig3 = px.bar(
                plat_df, x="Platform", y="Stale Pairs",
                title=f"Stale Inventory by Platform ({alert_threshold}d+)",
                color="Platform",
            )
            fig3.update_layout(template="plotly_dark", showlegend=False)
            st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — AI Strategy
# ══════════════════════════════════════════════════════════════════════════════
with tab_ai:
    st.subheader("🤖 Claude AI Markdown Strategy")
    st.caption(
        "Claude analyzes all your stale inventory at once and gives "
        "a specific, dollar-amount action for each pair."
    )

    if not stale_items:
        st.success("🎉 No stale inventory — nothing for Claude to analyze!")
    else:
        st.markdown(f"**{len(stale_items)} stale pairs ready for AI review:**")
        for item in stale_items[:6]:
            tier = item["aging_tier"]
            st.markdown(
                f"- {tier['label']} **{item['shoe_name']}** Sz {item['size']} — "
                f"{item['days_listed']}d on {item['listed_platform']} @ ${item['listed_price']:.0f}"
            )
        if len(stale_items) > 6:
            st.caption(f"...and {len(stale_items) - 6} more")

        st.markdown("---")

        if st.button(
            "🤖 Generate Full AI Markdown Strategy",
            type="primary",
            use_container_width=True,
        ):
            with st.spinner("Claude is analyzing your stale inventory..."):
                strategy_full = _get_ai_bulk_strategy(stale_items)

            st.markdown("### 📋 Claude's Recommendations")
            st.markdown(strategy_full)
            st.markdown("---")

            send1, send2 = st.columns(2)
            with send1:
                if st.button(
                    "📱 Send via Telegram", key="send_strat_tg", use_container_width=True
                ):
                    ok = _send_bulk_digest_telegram(stale_items, strategy_full)
                    st.success("✅ Sent!") if ok else st.warning("Configure Telegram in Settings.")
            with send2:
                if st.button(
                    "📧 Email to Me", key="send_strat_email", use_container_width=True
                ):
                    if user_email_str:
                        ok = _send_email_digest(stale_items, strategy_full, user_email_str)
                        st.success(f"✅ Emailed to {user_email_str}") if ok else st.warning("Configure Gmail in Settings.")

        st.markdown("---")
        st.subheader("💡 Cross-Listing Opportunities")
        for item in stale_items:
            platform = item["listed_platform"].lower()
            if "ebay" in platform:
                cross = "Mercari"
                tip = "Mercari buyers are deal-focused — try 5% below eBay listing."
            elif "mercari" in platform:
                cross = "eBay"
                tip = "eBay reaches more collectors. Auction works well for hyped pairs."
            else:
                cross = "eBay + Mercari"
                tip = "Multi-platform listing increases buyer exposure 3×."
            st.markdown(
                f"- **{item['shoe_name']}** Sz {item['size']} on `{item['listed_platform']}` → "
                f"**Cross-list on {cross}**: *{tip}*"
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Alert History
# ══════════════════════════════════════════════════════════════════════════════
with tab_history:
    st.subheader("📜 Alert History")
    history = _load_alert_history(user_id)

    if not history:
        st.info("No alerts sent yet. Send your first alert in the ⚠️ Alert Center tab.")
    else:
        hm1, hm2, hm3 = st.columns(3)
        hm1.metric("Total Alerts Sent", len(history))
        tg_count = sum(1 for h in history if h.get("alert_type") == "telegram")
        hm2.metric("Telegram Alerts", tg_count)
        hm3.metric("Email Digests", len(history) - tg_count)

        hist_df = pd.DataFrame(history)
        col_rename = {
            "shoe_name":       "Shoe",
            "size":            "Size",
            "days_listed":     "Days Listed",
            "listed_price":    "Listed $",
            "suggested_price": "Suggested $",
            "alert_type":      "Channel",
            "sent_at":         "Sent At",
        }
        disp_cols = [c for c in col_rename if c in hist_df.columns]
        st.dataframe(
            hist_df[disp_cols].rename(columns=col_rename),
            use_container_width=True,
            hide_index=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Auto-Schedule
# ══════════════════════════════════════════════════════════════════════════════
with tab_sched:
    st.subheader("⏰ Automated Weekly Stale Inventory Scan")
    st.caption(
        "The scheduled agent runner checks this task every 15 minutes. "
        "When next_run arrives, it scans inventory and fires the Telegram digest automatically."
    )

    # ── Show scheduled task status ────────────────────────────────────────────
    try:
        conn = get_conn()
        ph = "%s" if USE_POSTGRES else "?"
        task_row = conn.execute(
            f"SELECT * FROM agent_scheduled_tasks WHERE task_name = {ph}",
            ("SoleOps Stale Inventory Weekly Scan",)
        ).fetchone()
        conn.close()

        if task_row:
            td = dict(task_row)
            enabled = bool(td.get("enabled", True))
            status_icon = "🟢" if enabled else "⚫"
            st.success(
                f"{status_icon} **Scheduled task active:** "
                f"SoleOps Stale Inventory Weekly Scan — Every Monday @ 9:00 AM"
            )
            tc1, tc2, tc3, tc4 = st.columns(4)
            tc1.metric("Next Run",  (td.get("next_run") or "—")[:16])
            tc2.metric("Last Run",  (td.get("last_run") or "Never")[:16])
            tc3.metric("Run Count", td.get("run_count", 0))
            tc4.metric("Enabled",   "Yes" if enabled else "No")
        else:
            st.warning("Scheduled task not yet seeded. Reload this page to create it.")
    except Exception as e:
        st.info(f"Agent scheduler not available: {e}")

    st.markdown("---")

    # ── Manual trigger ────────────────────────────────────────────────────────
    st.subheader("🔄 Manual Trigger")
    if st.button(
        "▶️ Run Stale Scan Now",
        type="primary",
        use_container_width=True,
    ):
        with st.spinner("Running stale inventory scan..."):
            strategy_manual = _get_ai_bulk_strategy(stale_items) if stale_items else ""
            ok = _send_bulk_digest_telegram(stale_items, strategy_manual) if stale_items else False

        if not stale_items:
            st.success("✅ Scan complete — no stale inventory right now!")
        elif ok:
            st.success(f"✅ Digest sent for {len(stale_items)} stale pairs via Telegram!")
            for item in stale_items:
                _log_alert_sent(
                    item["id"], user_id, item["shoe_name"], item["size"],
                    item["days_listed"], item["listed_price"],
                    item["suggested_price"], strategy_manual, "telegram"
                )
        else:
            st.warning(
                f"Found {len(stale_items)} stale pairs but Telegram not configured. "
                "Add telegram_bot_token + telegram_chat_id in Settings."
            )

    st.markdown("---")

    # ── Cron setup instructions ───────────────────────────────────────────────
    st.subheader("⚙️ CT100 Cron Setup")
    st.code(
        "# SSH into CT100 and add this crontab entry:\n"
        "ssh root@100.95.125.112\n\n"
        "# Add to /etc/crontab — checks for due tasks every 15 minutes:\n"
        'echo "*/15 * * * * root cd /app && python3 run_scheduled_agents.py '
        '>> /var/log/sched-agents.log 2>&1" >> /etc/crontab\n\n'
        "# Or systemd timer — more reliable:\n"
        "# See AUTONOMOUS_AI_DEV_SYSTEM.md for full setup\n\n"
        "# Test the stale scan manually:\n"
        'python3 run_scheduled_agents.py --force "SoleOps Stale Inventory Weekly Scan" --verbose',
        language="bash",
    )
