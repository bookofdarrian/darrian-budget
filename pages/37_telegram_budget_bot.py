import streamlit as st
import os
import json
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple
import requests
import re

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

st.set_page_config(page_title="Telegram Budget Bot", page_icon="🍑", layout="wide")
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

# Constants
EXPENSE_CATEGORIES = [
    "Food & Dining", "Transportation", "Shopping", "Entertainment",
    "Bills & Utilities", "Health & Medical", "Travel", "Education",
    "Personal Care", "Groceries", "Gas", "Subscriptions", "Other"
]

CATEGORY_KEYWORDS = {
    "Food & Dining": ["lunch", "dinner", "breakfast", "restaurant", "cafe", "coffee", "food", "meal", "ate", "eating", "drinks", "bar", "pizza", "burger", "sushi", "takeout", "delivery"],
    "Transportation": ["uber", "lyft", "taxi", "bus", "train", "metro", "subway", "parking", "toll", "ride"],
    "Shopping": ["amazon", "target", "walmart", "store", "bought", "purchase", "shopping", "clothes", "shoes", "electronics"],
    "Entertainment": ["movie", "netflix", "spotify", "concert", "game", "gaming", "entertainment", "theater", "show", "ticket"],
    "Bills & Utilities": ["electric", "water", "internet", "phone", "bill", "utility", "rent", "mortgage", "insurance"],
    "Health & Medical": ["doctor", "pharmacy", "medicine", "prescription", "hospital", "dentist", "medical", "health", "gym", "fitness"],
    "Travel": ["hotel", "flight", "airbnb", "vacation", "trip", "travel", "booking"],
    "Education": ["book", "course", "class", "tuition", "school", "learning", "udemy", "education"],
    "Personal Care": ["haircut", "salon", "spa", "beauty", "grooming", "personal"],
    "Groceries": ["grocery", "groceries", "supermarket", "whole foods", "kroger", "publix", "aldi", "trader joe"],
    "Gas": ["gas", "fuel", "gasoline", "shell", "chevron", "exxon", "bp"],
    "Subscriptions": ["subscription", "membership", "monthly", "annual", "recurring"]
}


def _ensure_tables():
    """Create required tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        # Telegram messages table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_messages (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                user_id BIGINT,
                username VARCHAR(255),
                message_text TEXT NOT NULL,
                parsed_amount DECIMAL(10, 2),
                parsed_category VARCHAR(100),
                parsed_description TEXT,
                processing_status VARCHAR(50) DEFAULT 'pending',
                expense_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            )
        """)
        
        # Telegram bot settings table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_bot_config (
                id SERIAL PRIMARY KEY,
                config_key VARCHAR(100) UNIQUE NOT NULL,
                config_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index for faster lookups
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_telegram_messages_chat_id 
            ON telegram_messages(chat_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_telegram_messages_status 
            ON telegram_messages(processing_status)
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER,
                username TEXT,
                message_text TEXT NOT NULL,
                parsed_amount REAL,
                parsed_category TEXT,
                parsed_description TEXT,
                processing_status TEXT DEFAULT 'pending',
                expense_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_bot_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    cur.close()
    conn.close()


def get_bot_config(key: str) -> Optional[str]:
    """Get bot configuration value."""
    conn = get_conn()
    cur = conn.cursor()
    
    placeholder = "%s" if USE_POSTGRES else "?"
    cur.execute(f"SELECT config_value FROM telegram_bot_config WHERE config_key = {placeholder}", (key,))
    row = cur.fetchone()
    
    cur.close()
    conn.close()
    
    return row[0] if row else None


def set_bot_config(key: str, value: str):
    """Set bot configuration value."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO telegram_bot_config (config_key, config_value, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (config_key) DO UPDATE SET 
                config_value = EXCLUDED.config_value,
                updated_at = CURRENT_TIMESTAMP
        """, (key, value))
    else:
        cur.execute("""
            INSERT OR REPLACE INTO telegram_bot_config (config_key, config_value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, value))
    
    conn.commit()
    cur.close()
    conn.close()


def parse_expense_with_ollama(message: str) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """
    Parse expense from natural language using Ollama NLP.
    Returns: (amount, category, description)
    """
    ollama_url = get_setting("ollama_url") or "http://localhost:11434"
    ollama_model = get_setting("ollama_model") or "llama2"
    
    prompt = f"""You are an expense parser. Extract the following from this message:
1. Amount (numeric value only, no currency symbols)
2. Category (one of: {', '.join(EXPENSE_CATEGORIES)})
3. Description (brief description of the expense)

Message: "{message}"

Respond ONLY in this exact JSON format:
{{"amount": 0.00, "category": "Category Name", "description": "Brief description"}}

If you cannot determine a value, use null. Always try to extract an amount if any number is mentioned."""

    try:
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "")
            
            # Extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                parsed = json.loads(json_match.group())
                return (
                    float(parsed.get("amount")) if parsed.get("amount") else None,
                    parsed.get("category"),
                    parsed.get("description")
                )
    except Exception as e:
        st.warning(f"Ollama parsing failed: {e}, falling back to rule-based parsing")
    
    # Fallback to rule-based parsing
    return parse_expense_fallback(message)


def parse_expense_fallback(message: str) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """
    Fallback rule-based parsing when Ollama is unavailable.
    Returns: (amount, category, description)
    """
    message_lower = message.lower()
    
    # Extract amount using regex
    amount = None
    amount_patterns = [
        r'\$(\d+(?:\.\d{2})?)',  # $25.00 or $25
        r'(\d+(?:\.\d{2})?)\s*(?:dollars?|bucks?)',  # 25 dollars
        r'(?:spent|paid|cost|bought for|for)\s*\$?(\d+(?:\.\d{2})?)',  # spent 25
        r'(\d+(?:\.\d{2})?)\s*(?:on|for)\s',  # 25 on lunch
        r'^(\d+(?:\.\d{2})?)\s',  # Starts with number
    ]
    
    for pattern in amount_patterns:
        match = re.search(pattern, message_lower)
        if match:
            try:
                amount = float(match.group(1))
                break
            except ValueError:
                continue
    
    # Detect category based on keywords
    category = "Other"
    max_matches = 0
    
    for cat, keywords in CATEGORY_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw in message_lower)
        if matches > max_matches:
            max_matches = matches
            category = cat
    
    # Generate description by removing amount-related text
    description = message
    if amount:
        description = re.sub(r'\$?\d+(?:\.\d{2})?', '', description).strip()
        description = re.sub(r'\s+', ' ', description)
    
    # Truncate description if too long
    if len(description) > 100:
        description = description[:97] + "..."
    
    return amount, category, description


def save_telegram_message(chat_id: int, user_id: int, username: str, message_text: str) -> int:
    """Save incoming Telegram message to database."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO telegram_messages (chat_id, user_id, username, message_text, processing_status)
            VALUES (%s, %s, %s, %s, 'pending')
            RETURNING id
        """, (chat_id, user_id, username, message_text))
        msg_id = cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO telegram_messages (chat_id, user_id, username, message_text, processing_status)
            VALUES (?, ?, ?, ?, 'pending')
        """, (chat_id, user_id, username, message_text))
        msg_id = cur.lastrowid
    
    conn.commit()
    cur.close()
    conn.close()
    
    return msg_id


def update_message_parsing(msg_id: int, amount: Optional[float], category: Optional[str], description: Optional[str]):
    """Update message with parsed values."""
    conn = get_conn()
    cur = conn.cursor()
    
    placeholder = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        UPDATE telegram_messages 
        SET parsed_amount = {placeholder}, 
            parsed_category = {placeholder}, 
            parsed_description = {placeholder},
            processing_status = 'parsed'
        WHERE id = {placeholder}
    """, (amount, category, description, msg_id))
    
    conn.commit()
    cur.close()
    conn.close()


def write_expense_to_db(amount: float, category: str, description: str, user_id: int = 1) -> Optional[int]:
    """Write parsed expense to the expenses table."""
    if not amount or amount <= 0:
        return None
    
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cur.execute("""
                INSERT INTO expenses (user_id, amount, category, description, date, created_at)
                VALUES (%s, %s, %s, %s, CURRENT_DATE, CURRENT_TIMESTAMP)
                RETURNING id
            """, (user_id, amount, category or "Other", description or "Telegram expense"))
            expense_id = cur.fetchone()[0]
        else:
            cur.execute("""
                INSERT INTO expenses (user_id, amount, category, description, date, created_at)
                VALUES (?, ?, ?, ?, DATE('now'), DATETIME('now'))
            """, (user_id, amount, category or "Other", description or "Telegram expense"))
            expense_id = cur.lastrowid
        
        conn.commit()
        return expense_id
    except Exception as e:
        conn.rollback()
        st.error(f"Failed to write expense: {e}")
        return None
    finally:
        cur.close()
        conn.close()


def update_message_expense(msg_id: int, expense_id: int):
    """Link message to created expense."""
    conn = get_conn()
    cur = conn.cursor()
    
    placeholder = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        UPDATE telegram_messages 
        SET expense_id = {placeholder}, 
            processing_status = 'completed',
            processed_at = {'CURRENT_TIMESTAMP' if USE_POSTGRES else "DATETIME('now')"}
        WHERE id = {placeholder}
    """, (expense_id, msg_id))
    
    conn.commit()
    cur.close()
    conn.close()


def process_telegram_message(chat_id: int, user_id: int, username: str, message_text: str) -> dict:
    """
    Full pipeline: save message, parse with NLP, write expense.
    Returns processing result.
    """
    # Save message
    msg_id = save_telegram_message(chat_id, user_id, username, message_text)
    
    # Parse with Ollama NLP
    amount, category, description = parse_expense_with_ollama(message_text)
    
    # Update message with parsed values
    update_message_parsing(msg_id, amount, category, description)
    
    result = {
        "message_id": msg_id,
        "parsed_amount": amount,
        "parsed_category": category,
        "parsed_description": description,
        "expense_created": False,
        "expense_id": None
    }
    
    # Write expense if we have valid data
    if amount and amount > 0:
        expense_id = write_expense_to_db(amount, category, description)
        if expense_id:
            update_message_expense(msg_id, expense_id)
            result["expense_created"] = True
            result["expense_id"] = expense_id
    
    return result


def send_telegram_message(chat_id: int, text: str) -> bool:
    """Send message via Telegram Bot API."""
    bot_token = get_bot_config("telegram_bot_token") or get_setting("telegram_bot_token")
    if not bot_token:
        return False
    
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
        return response.status_code == 200
    except Exception:
        return False


def get_bot_info() -> Optional[dict]:
    """Get Telegram bot info."""
    bot_token = get_bot_config("telegram_bot_token") or get_setting("telegram_bot_token")
    if not bot_token:
        return None
    
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getMe",
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("result")
    except Exception:
        pass
    return None


def set_webhook(webhook_url: str) -> Tuple[bool, str]:
    """Set Telegram bot webhook."""
    bot_token = get_bot_config("telegram_bot_token") or get_setting("telegram_bot_token")
    if not bot_token:
        return False, "Bot token not configured"
    
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/setWebhook",
            json={"url": webhook_url},
            timeout=10
        )
        result = response.json()
        if result.get("ok"):
            set_bot_config("webhook_url", webhook_url)
            return True, "Webhook set successfully"
        return False, result.get("description", "Unknown error")
    except Exception as e:
        return False, str(e)


def delete_webhook() -> Tuple[bool, str]:
    """Delete Telegram bot webhook."""
    bot_token = get_bot_config("telegram_bot_token") or get_setting("telegram_bot_token")
    if not bot_token:
        return False, "Bot token not configured"
    
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/deleteWebhook",
            timeout=10
        )
        result = response.json()
        if result.get("ok"):
            set_bot_config("webhook_url", "")
            return True, "Webhook deleted"
        return False, result.get("description", "Unknown error")
    except Exception as e:
        return False, str(e)


def get_recent_messages(limit: int = 50) -> list:
    """Get recent Telegram messages."""
    conn = get_conn()
    cur = conn.cursor()
    
    placeholder = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        SELECT id, chat_id, username, message_text, parsed_amount, parsed_category, 
               parsed_description, processing_status, expense_id, created_at
        FROM telegram_messages
        ORDER BY created_at DESC
        LIMIT {placeholder}
    """, (limit,))
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    return rows


def get_message_stats() -> dict:
    """Get message processing statistics."""
    conn = get_conn()
    cur = conn.cursor()
    
    stats = {}
    
    # Total messages
    cur.execute("SELECT COUNT(*) FROM telegram_messages")
    stats["total"] = cur.fetchone()[0]
    
    # By status
    cur.execute("""
        SELECT processing_status, COUNT(*) 
        FROM telegram_messages 
        GROUP BY processing_status
    """)
    stats["by_status"] = dict(cur.fetchall())
    
    # Today's messages
    if USE_POSTGRES:
        cur.execute("""
            SELECT COUNT(*) FROM telegram_messages 
            WHERE created_at >= CURRENT_DATE
        """)
    else:
        cur.execute("""
            SELECT COUNT(*) FROM telegram_messages 
            WHERE DATE(created_at) = DATE('now')
        """)
    stats["today"] = cur.fetchone()[0]
    
    # Total amount logged today
    if USE_POSTGRES:
        cur.execute("""
            SELECT COALESCE(SUM(parsed_amount), 0) FROM telegram_messages 
            WHERE created_at >= CURRENT_DATE AND parsed_amount IS NOT NULL
        """)
    else:
        cur.execute("""
            SELECT COALESCE(SUM(parsed_amount), 0) FROM telegram_messages 
            WHERE DATE(created_at) = DATE('now') AND parsed_amount IS NOT NULL
        """)
    stats["today_amount"] = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    
    return stats


def reprocess_message(msg_id: int):
    """Reprocess a message through NLP."""
    conn = get_conn()
    cur = conn.cursor()
    
    placeholder = "%s" if USE_POSTGRES else "?"
    cur.execute(f"SELECT message_text FROM telegram_messages WHERE id = {placeholder}", (msg_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if row:
        message_text = row[0]
        amount, category, description = parse_expense_with_ollama(message_text)
        update_message_parsing(msg_id, amount, category, description)
        return True
    return False


def create_expense_from_message(msg_id: int) -> bool:
    """Create expense from a parsed message."""
    conn = get_conn()
    cur = conn.cursor()
    
    placeholder = "%s" if USE_POSTGRES else "?"
    cur.execute(f"""
        SELECT parsed_amount, parsed_category, parsed_description 
        FROM telegram_messages WHERE id = {placeholder}
    """, (msg_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if row and row[0]:
        expense_id = write_expense_to_db(row[0], row[1], row[2])
        if expense_id:
            update_message_expense(msg_id, expense_id)
            return True
    return False


# Initialize tables
_ensure_tables()

# Main UI
st.title("📱 Telegram Budget Bot")
st.markdown("Log expenses naturally via Telegram — powered by Ollama NLP")

# Tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "⚙️ Bot Settings", "📝 Recent Messages", "🧪 Test Parser"])

with tab1:
    # Bot Status Card
    col1, col2, col3 = st.columns(3)
    
    bot_info = get_bot_info()
    stats = get_message_stats()
    
    with col1:
        if bot_info:
            st.success("🟢 Bot Online")
            st.metric("Bot Username", f"@{bot_info.get('username', 'Unknown')}")
        else:
            st.error("🔴 Bot Offline")
            st.caption("Configure bot token in settings")
    
    with col2:
        st.metric("Messages Today", stats.get("today", 0))
        st.metric("Amount Logged Today", f"${stats.get('today_amount', 0):.2f}")
    
    with col3:
        st.metric("Total Messages", stats.get("total", 0))
        completed = stats.get("by_status", {}).get("completed", 0)
        total = stats.get("total", 1) or 1
        st.metric("Success Rate", f"{(completed/total)*100:.1f}%")
    
    st.markdown("---")
    
    # Quick stats by status
    st.subheader("Processing Status")
    status_data = stats.get("by_status", {})
    if status_data:
        cols = st.columns(len(status_data))
        status_icons = {"pending": "⏳", "parsed": "📊", "completed": "✅", "failed": "❌"}
        for i, (status, count) in enumerate(status_data.items()):
            with cols[i]:
                icon = status_icons.get(status, "📌")
                st.metric(f"{icon} {status.title()}", count)
    else:
        st.info("No messages yet. Send your first expense via Telegram!")
    
    st.markdown("---")
    
    # How to use
    with st.expander("📖 How to Use", expanded=False):
        st.markdown("""
        ### Quick Start
        1. **Configure** your Telegram Bot Token in Settings
        2. **Set up** the webhook URL for your server
        3. **Message** the bot with natural language expenses
        
        ### Example Messages
        - "Spent $25 on lunch at Chipotle"
        - "Uber ride $12.50"
        - "$45 groceries at Kroger"
        - "Netflix subscription 15.99"
        - "Gas $40"
        
        ### Supported Formats
        The bot understands various ways to express expenses:
        - Dollar amounts: `$25`, `25 dollars`, `25 bucks`
        - With context: `spent`, `paid`, `bought`, `cost`
        - Categories are auto-detected from keywords
        """)

with tab2:
    st.subheader("⚙️ Bot Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Telegram Bot Token")
        current_token = get_bot_config("telegram_bot_token") or get_setting("telegram_bot_token") or ""
        token_display = current_token[:10] + "..." + current_token[-5:] if len(current_token) > 15 else current_token
        
        if current_token:
            st.success(f"Token configured: `{token_display}`")
        else:
            st.warning("No token configured")
        
        new_token = st.text_input(
            "Bot Token",
            type="password",
            placeholder="Enter your Telegram Bot Token",
            help="Get this from @BotFather on Telegram"
        )
        
        if st.button("💾 Save Token", use_container_width=True):
            if new_token:
                set_bot_config("telegram_bot_token", new_token)
                st.success("Token saved!")
                st.rerun()
            else:
                st.error("Please enter a token")
    
    with col2:
        st.markdown("### Webhook Configuration")
        current_webhook = get_bot_config("webhook_url") or ""
        
        if current_webhook:
            st.success(f"Webhook: `{current_webhook}`")
        else:
            st.info("No webhook configured")
        
        webhook_url = st.text_input(
            "Webhook URL",
            value=current_webhook,
            placeholder="https://yourdomain.com/telegram/webhook",
            help="Your server endpoint that receives Telegram updates"
        )
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔗 Set Webhook", use_container_width=True):
                if webhook_url:
                    success, message = set_webhook(webhook_url)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
                else:
                    st.error("Enter a webhook URL")
        
        with col_b:
            if st.button("🗑️ Delete Webhook", use_container_width=True):
                success, message = delete_webhook()
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    
    st.markdown("---")
    
    # Ollama settings
    st.markdown("### 🤖 Ollama NLP Settings")
    col1, col2 = st.columns(2)
    
    with col1:
        ollama_url = st.text_input(
            "Ollama URL",
            value=get_setting("ollama_url") or "http://localhost:11434",
            help="URL of your Ollama instance"
        )
        if st.button("Save Ollama URL"):
            set_setting("ollama_url", ollama_url)
            st.success("Ollama URL saved!")
    
    with col2:
        ollama_model = st.text_input(
            "Ollama Model",
            value=get_setting("ollama_model") or "llama2",
            help="Model to use for NLP parsing (e.g., llama2, mistral)"
        )
        if st.button("Save Ollama Model"):
            set_setting("ollama_model", ollama_model)
            st.success("Ollama model saved!")
    
    # Test Ollama connection
    if st.button("🧪 Test Ollama Connection"):
        try:
            ollama_base = get_setting("ollama_url") or "http://localhost:11434"
            response = requests.get(f"{ollama_base}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                st.success(f"✅ Connected! Available models: {', '.join([m['name'] for m in models])}")
            else:
                st.error(f"Connection failed: {response.status_code}")
        except Exception as e:
            st.error(f"Connection failed: {e}")
            st.info("Make sure Ollama is running and accessible")

with tab3:
    st.subheader("📝 Recent Telegram Messages")
    
    # Filters
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        status_filter = st.selectbox("Filter by Status", ["All", "pending", "parsed", "completed", "failed"])
    with col2:
        limit = st.slider("Show entries", 10, 100, 50)
    with col3:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    messages = get_recent_messages(limit)
    
    if messages:
        for msg in messages:
            msg_id, chat_id, username, text, amount, category, desc, status, expense_id, created = msg
            
            # Apply filter
            if status_filter != "All" and status != status_filter:
                continue
            
            status_icon = {"pending": "⏳", "parsed": "📊", "completed": "✅", "failed": "❌"}.get(status, "📌")
            
            with st.expander(f"{status_icon} {text[:50]}{'...' if len(text) > 50 else ''} | ${amount or 0:.2f}", expanded=False):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**Message:** {text}")
                    st.markdown(f"**From:** @{username or 'Unknown'} (Chat: {chat_id})")
                    st.markdown(f"**Received:** {created}")