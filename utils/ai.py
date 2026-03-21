"""
utils/ai.py — Shared AI call wrapper for all PSS / SoleOps pages.

Features:
  1. BYOK (Bring Your Own Key): users can supply their own Anthropic key via
     st.session_state["byok_api_key"]. That key is NEVER written to the DB —
     it only lives in the browser session.
  2. Automatic token tracking: every successful call is logged to the
     token_usage table in the shared auth DB via log_token_usage().
  3. Simple helper to resolve which key to use and whether it's BYOK.
"""

from __future__ import annotations

import streamlit as st

from utils.db import get_setting, log_token_usage

# Default model used across the app
DEFAULT_MODEL = "claude-opus-4-5"


# ── Key resolution ─────────────────────────────────────────────────────────────

def get_api_key(user_email: str = "") -> tuple[str, bool]:
    """
    Return (api_key, is_byok).

    Priority order:
      1. User's own key stored in session state (byok_api_key) — never persisted to DB
      2. App-level key from app_settings (admin key, shared by all users)

    If neither is available, returns ("", False).
    """
    # 1. Session-level BYOK key (highest priority — never touches the DB)
    byok_key = st.session_state.get("byok_api_key", "").strip()
    if byok_key:
        return byok_key, True

    # 2. App-level key stored in DB by admin
    app_key = get_setting("anthropic_api_key", "").strip()
    if app_key:
        return app_key, False

    return "", False


# ── Tracked Anthropic call ─────────────────────────────────────────────────────

def call_claude(
    messages: list[dict],
    system: str = "",
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1024,
    page: str = "",
    site: str = "pss",
    user_email: str = "",
) -> tuple[str, dict]:
    """
    Make a tracked Anthropic API call.

    Args:
        messages:    List of {"role": "user"|"assistant", "content": "..."} dicts.
        system:      Optional system prompt string.
        model:       Claude model name (defaults to DEFAULT_MODEL).
        max_tokens:  Maximum tokens in the response.
        page:        Page name / identifier for logging (e.g. "55_ai_budget_chat").
        site:        Site identifier ("pss", "soleops", "cc").
        user_email:  Logged-in user's email for tracking.

    Returns:
        (response_text, usage_dict)
        usage_dict contains {"input_tokens": int, "output_tokens": int, "used_byok": bool}

    On error, response_text starts with "⚠️ " and usage_dict contains zeros.
    """
    import anthropic

    api_key, is_byok = get_api_key(user_email)

    if not api_key:
        return (
            "⚠️ No API key configured. Ask the admin to add an Anthropic key, "
            "or add your own key via **AI Settings** → Bring Your Own Key.",
            {"input_tokens": 0, "output_tokens": 0, "used_byok": False},
        )

    try:
        client = anthropic.Anthropic(api_key=api_key)

        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        response = client.messages.create(**kwargs)

        text = response.content[0].text
        in_tok  = response.usage.input_tokens
        out_tok = response.usage.output_tokens

        # Log to DB (fire-and-forget, don't crash the page if logging fails)
        try:
            if user_email:
                log_token_usage(
                    user_email=user_email,
                    page=page,
                    model=model,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    site=site,
                    used_byok=is_byok,
                )
        except Exception:
            pass

        return text, {"input_tokens": in_tok, "output_tokens": out_tok, "used_byok": is_byok}

    except anthropic.AuthenticationError:
        return (
            "⚠️ Invalid API key. Please check the key in AI Settings.",
            {"input_tokens": 0, "output_tokens": 0, "used_byok": is_byok},
        )
    except anthropic.RateLimitError:
        return (
            "⚠️ Rate limit exceeded. Please wait a moment and try again.",
            {"input_tokens": 0, "output_tokens": 0, "used_byok": is_byok},
        )
    except Exception as exc:
        return (
            f"⚠️ AI error: {exc}",
            {"input_tokens": 0, "output_tokens": 0, "used_byok": is_byok},
        )


# ── BYOK sidebar widget ────────────────────────────────────────────────────────

def render_byok_expander(label: str = "🔑 Use Your Own API Key (BYOK)"):
    """
    Render a sidebar expander that lets users enter their own Anthropic key.
    The key is stored ONLY in st.session_state — never written to the database.
    Call this from any AI page's sidebar section.
    """
    with st.sidebar.expander(label, expanded=False):
        st.markdown(
            "Enter your own [Anthropic API key](https://console.anthropic.com/settings/keys). "
            "It is **never saved** — it only lasts for this browser session."
        )
        byok_input = st.text_input(
            "Anthropic API Key",
            value=st.session_state.get("byok_api_key", ""),
            type="password",
            placeholder="sk-ant-...",
            key="byok_input_widget",
            label_visibility="collapsed",
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Use this key", use_container_width=True):
                st.session_state["byok_api_key"] = byok_input.strip()
                st.success("Key saved for this session!")
                st.rerun()
        with col2:
            if st.button("🗑️ Clear key", use_container_width=True):
                st.session_state.pop("byok_api_key", None)
                st.rerun()

        if st.session_state.get("byok_api_key"):
            st.success("✅ Using your own key this session.")
        else:
            _, is_byok = get_api_key()
            app_key = get_setting("anthropic_api_key", "")
            if app_key:
                st.info("ℹ️ Using shared app key.")
            else:
                st.warning("⚠️ No key available — AI features will be disabled.")
