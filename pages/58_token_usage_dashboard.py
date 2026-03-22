"""
Page 57 — AI Token Usage Dashboard

Admin view:
  • Total tokens used across all users & sites
  • Per-user breakdown (calls, input/output tokens, last activity)
  • Recent call log with page, model, BYOK flag
  • Estimated cost calculator

User view (non-admin):
  • Their own token usage summary
  • BYOK (Bring Your Own Key) settings panel — key is session-only, never stored in DB
"""

import streamlit as st
from datetime import datetime

from utils.db import (
    get_conn, USE_POSTGRES, execute as db_exec, init_db,
    get_setting, set_setting,
    get_token_usage_summary, get_token_usage_detail,
    _OWNER_EMAILS,
)
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css
from utils.ai import render_byok_expander, get_api_key

# ── Anthropic pricing (per million tokens, as of 2025) ───────────────────────
PRICING = {
    "claude-opus-4-5":      {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-haiku-3-5":     {"input": 0.80,  "output": 4.00},
    "default":              {"input": 15.00, "output": 75.00},   # fallback
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    prices = PRICING.get(model, PRICING["default"])
    return (input_tokens / 1_000_000 * prices["input"]) + (output_tokens / 1_000_000 * prices["output"])


def _fmt_tokens(n) -> str:
    n = int(n or 0)
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def _is_owner(user: dict) -> bool:
    return user.get("email", "").strip().lower() in _OWNER_EMAILS


# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Token Usage | Peach State Savings",
    page_icon="📊",
    layout="wide",
)
init_db()
inject_css()
require_login()

# ── Sidebar ───────────────────────────────────────────────────────────────────
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                          label="Overview",          icon="📊")
st.sidebar.page_link("pages/22_todo.py",                label="Todo",           icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py",   label="Creator",        icon="🎬")
st.sidebar.page_link("pages/25_notes.py",               label="Notes",          icon="📝")
st.sidebar.page_link("pages/26_media_library.py",       label="Media Library",  icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py",  label="Personal Assistant",icon="🤖")

# BYOK widget — available to all users
st.sidebar.markdown("---")
render_byok_expander()

render_sidebar_user_widget()

# ── Auth ──────────────────────────────────────────────────────────────────────
user       = st.session_state.get("user", {})
user_email = user.get("email", "").strip().lower()
owner      = _is_owner(user)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📊 AI Token Usage")

if owner:
    st.caption("Admin view — showing all users across all sites.")
else:
    st.caption("Showing your personal AI usage. Only you can see this data.")

# ── BYOK status banner ────────────────────────────────────────────────────────
_, is_byok = get_api_key(user_email)
app_key    = get_setting("anthropic_api_key", "")

if is_byok:
    st.success(
        "🔑 **Using your own API key this session.** "
        "Your calls are billed to your own Anthropic account and still tracked here for your reference."
    )
elif app_key:
    st.info(
        "ℹ️ **Using the shared app key.** "
        "Want to use your own Anthropic key instead? Expand **🔑 Use Your Own API Key** in the sidebar."
    )
else:
    st.warning(
        "⚠️ **No API key available.** AI features are currently disabled. "
        "Add your own key via the sidebar to enable them."
    )

st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
if owner:
    tab_summary, tab_detail, tab_byok_settings = st.tabs(
        ["📈 Summary (All Users)", "🗒️ Call Log", "⚙️ Admin API Settings"]
    )
else:
    tab_summary, tab_byok_settings = st.tabs(
        ["📈 My Usage", "⚙️ API Key Settings"]
    )
    tab_detail = None

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Summary
# ══════════════════════════════════════════════════════════════════════════════
with tab_summary:
    if owner:
        rows = get_token_usage_summary()
    else:
        # Non-owners only see their own rows
        rows = [r for r in get_token_usage_summary() if r["user_email"] == user_email]

    if not rows:
        st.info("No AI calls have been made yet. Token usage will appear here after the first AI request.")
    else:
        # ── Grand totals ─────────────────────────────────────────────────────
        grand_input  = sum(int(r.get("total_input", 0) or 0)  for r in rows)
        grand_output = sum(int(r.get("total_output", 0) or 0) for r in rows)
        grand_total  = grand_input + grand_output
        grand_calls  = sum(int(r.get("calls", 0) or 0)        for r in rows)
        grand_byok   = sum(int(r.get("byok_calls", 0) or 0)   for r in rows)

        # Rough cost estimate — assume default pricing for mixed models
        est_cost = _estimate_cost("default", grand_input, grand_output)

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Calls",   f"{grand_calls:,}")
        c2.metric("Input Tokens",  _fmt_tokens(grand_input))
        c3.metric("Output Tokens", _fmt_tokens(grand_output))
        c4.metric("Total Tokens",  _fmt_tokens(grand_total))
        c5.metric("Est. Cost",     f"${est_cost:.4f}")

        st.markdown("---")

        # ── Per-user / per-site table ─────────────────────────────────────────
        st.subheader("Breakdown" if owner else "Your Usage by Site")

        table_rows = []
        for r in rows:
            in_t  = int(r.get("total_input", 0) or 0)
            out_t = int(r.get("total_output", 0) or 0)
            cost  = _estimate_cost("default", in_t, out_t)
            table_rows.append({
                "User":          r["user_email"] if owner else "you",
                "Site":          r.get("site", "pss").upper(),
                "Calls":         int(r.get("calls", 0) or 0),
                "Input Tokens":  _fmt_tokens(in_t),
                "Output Tokens": _fmt_tokens(out_t),
                "Total Tokens":  _fmt_tokens(in_t + out_t),
                "BYOK Calls":    int(r.get("byok_calls", 0) or 0),
                "Est. Cost":     f"${cost:.4f}",
                "Last Call":     str(r.get("last_call", ""))[:16],
            })

        st.dataframe(table_rows, use_container_width=True, hide_index=True)

        # ── Cost note ────────────────────────────────────────────────────────
        with st.expander("ℹ️ About cost estimates"):
            st.markdown(
                """
                Cost estimates use **claude-opus-4-5** pricing ($15 / $75 per M tokens) as the default.
                Actual costs depend on which model was called — see the **Call Log** tab for per-call detail.

                | Model | Input ($/M) | Output ($/M) |
                |-------|-------------|--------------|
                | claude-opus-4-5 | $15.00 | $75.00 |
                | claude-sonnet-4-20250514 | $3.00 | $15.00 |
                | claude-haiku-3-5 | $0.80 | $4.00 |

                BYOK calls are billed directly to **your** Anthropic account — not the app's key.
                """
            )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Detail call log (admin only)
# ══════════════════════════════════════════════════════════════════════════════
if tab_detail is not None:
    with tab_detail:
        st.subheader("🗒️ Recent AI Calls")

        # Filter controls
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            filter_email = st.text_input(
                "Filter by email",
                placeholder="Leave blank for all users",
                key="token_log_email_filter",
            ).strip().lower()
        with col_f2:
            limit = st.selectbox("Show last", [50, 100, 200, 500], index=1, key="token_log_limit")

        detail = get_token_usage_detail(
            user_email=filter_email if filter_email else None,
            limit=limit,
        )

        if not detail:
            st.info("No records found.")
        else:
            log_rows = []
            for r in detail:
                in_t  = int(r.get("input_tokens", 0) or 0)
                out_t = int(r.get("output_tokens", 0) or 0)
                cost  = _estimate_cost(r.get("model", "default"), in_t, out_t)
                log_rows.append({
                    "Timestamp":  str(r.get("created_at", ""))[:19],
                    "User":       r.get("user_email", ""),
                    "Site":       r.get("site", "pss").upper(),
                    "Page":       r.get("page", ""),
                    "Model":      r.get("model", ""),
                    "Input ↑":   in_t,
                    "Output ↓":  out_t,
                    "Total":     in_t + out_t,
                    "BYOK":      "✅" if r.get("used_byok") else "—",
                    "Est. Cost": f"${cost:.5f}",
                })

            st.dataframe(log_rows, use_container_width=True, hide_index=True)

            csv_lines = ["Timestamp,User,Site,Page,Model,Input,Output,Total,BYOK,Est Cost"]
            for row in log_rows:
                csv_lines.append(
                    f"{row['Timestamp']},{row['User']},{row['Site']},{row['Page']},"
                    f"{row['Model']},{row['Input ↑']},{row['Output ↓']},{row['Total']},"
                    f"{row['BYOK']},{row['Est. Cost']}"
                )
            st.download_button(
                "⬇️ Export CSV",
                data="\n".join(csv_lines),
                file_name=f"token_usage_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — API Key settings
# ══════════════════════════════════════════════════════════════════════════════
with tab_byok_settings:
    # ── BYOK section (all users) ──────────────────────────────────────────────
    st.subheader("🔑 Bring Your Own API Key (BYOK)")
    st.markdown(
        """
        You can provide your own Anthropic API key. It is **stored only in your browser session**
        and is **never saved to the database**. When you close or refresh the tab, it's gone.

        - Get your key at [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
        - Using your own key means AI calls are billed to **your** Anthropic account
        - Your usage is still tracked here so you can monitor it
        """
    )

    byok_current = st.session_state.get("byok_api_key", "")
    new_key = st.text_input(
        "Your Anthropic API Key",
        value=byok_current,
        type="password",
        placeholder="sk-ant-api03-...",
        help="This key is stored only in your browser session. Never saved to any database.",
        key="byok_main_input",
    )

    col_a, col_b, col_c = st.columns([2, 2, 3])
    with col_a:
        if st.button("✅ Activate Key", use_container_width=True):
            if new_key.strip().startswith("sk-ant"):
                st.session_state["byok_api_key"] = new_key.strip()
                st.success("✅ Your key is active for this session!")
                st.rerun()
            else:
                st.error("Key doesn't look right — should start with `sk-ant`.")
    with col_b:
        if st.button("🗑️ Remove Key", use_container_width=True):
            st.session_state.pop("byok_api_key", None)
            st.info("Key removed. Using shared app key (if configured).")
            st.rerun()
    with col_c:
        if byok_current:
            masked = byok_current[:10] + "•" * 10 + byok_current[-4:]
            st.success(f"Active key: `{masked}`")
        else:
            st.caption("No BYOK key active this session.")

    # ── Admin section: manage shared app key ─────────────────────────────────
    if owner:
        st.markdown("---")
        st.subheader("🛡️ Admin — Shared App API Key")
        st.markdown(
            "This key is stored in the app's database and is used by all users who don't provide their own key."
        )

        current_app_key = get_setting("anthropic_api_key", "")
        masked_app = (current_app_key[:10] + "•" * 10 + current_app_key[-4:]) if current_app_key else "Not set"

        st.info(f"Current stored key: `{masked_app}`")

        new_app_key = st.text_input(
            "Update shared API key",
            type="password",
            placeholder="sk-ant-...",
            key="admin_app_key_input",
            help="Stored in app_settings table. Visible to admins only.",
        )
        if st.button("💾 Save Shared Key", key="save_app_key"):
            if new_app_key.strip():
                set_setting("anthropic_api_key", new_app_key.strip())
                st.success("✅ Shared app key updated!")
                st.rerun()
            else:
                st.error("Key cannot be empty.")

        if current_app_key:
            if st.button("🗑️ Remove Shared Key", key="remove_app_key"):
                set_setting("anthropic_api_key", "")
                st.warning("Shared key removed. Users without BYOK will not be able to use AI.")
                st.rerun()
