import streamlit as st
import json
import os
import re
import requests
from datetime import datetime, timedelta
from decimal import Decimal
import threading
import time

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

# Placeholder helper
def ph(count=1):
    if USE_POSTGRES:
        return ", ".join(["%s"] * count)
    return ", ".join(["?"] * count)

def ph_single():
    return "%s" if USE_POSTGRES else "?"

def _ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_expense_logs (
                id SERIAL PRIMARY KEY,
                telegram_user_id BIGINT NOT NULL,
                telegram_username VARCHAR(255),
                chat_id BIGINT NOT NULL,
                raw_message TEXT NOT NULL,
                parsed_amount DECIMAL(12, 2),
                currency VARCHAR(10) DEFAULT 'USD',
                category VARCHAR(100),
                merchant VARCHAR(255),
                description TEXT,
                confidence_score DECIMAL(3, 2),
                parsing_status VARCHAR(50) DEFAULT 'pending',
                linked_expense_id INTEGER,
                conversation_context JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_bot_conversations (
                id SERIAL PRIMARY KEY,
                telegram_user_id BIGINT NOT NULL,
                chat_id BIGINT NOT NULL,
                conversation_state VARCHAR(50) DEFAULT 'idle',
                pending_expense_data JSONB,
                last_message_id BIGINT,
                context_messages JSONB DEFAULT '[]'::jsonb,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_bot_settings (
                id SERIAL PRIMARY KEY,
                setting_key VARCHAR(100) UNIQUE NOT NULL,
                setting_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_authorized_users (
                id SERIAL PRIMARY KEY,
                telegram_user_id BIGINT UNIQUE NOT NULL,
                telegram_username VARCHAR(255),
                app_user_id INTEGER,
                is_authorized BOOLEAN DEFAULT TRUE,
                authorized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active_at TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_telegram_logs_user 
            ON telegram_expense_logs(telegram_user_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_telegram_logs_created 
            ON telegram_expense_logs(created_at DESC)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_telegram_conv_user 
            ON telegram_bot_conversations(telegram_user_id, chat_id)
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_expense_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                telegram_username TEXT,
                chat_id INTEGER NOT NULL,
                raw_message TEXT NOT NULL,
                parsed_amount REAL,
                currency TEXT DEFAULT 'USD',
                category TEXT,
                merchant TEXT,
                description TEXT,
                confidence_score REAL,
                parsing_status TEXT DEFAULT 'pending',
                linked_expense_id INTEGER,
                conversation_context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_bot_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                conversation_state TEXT DEFAULT 'idle',
                pending_expense_data TEXT,
                last_message_id INTEGER,
                context_messages TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_bot_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_authorized_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER UNIQUE NOT NULL,
                telegram_username TEXT,
                app_user_id INTEGER,
                is_authorized INTEGER DEFAULT 1,
                authorized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active_at TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()

_ensure_tables()

# Categories for expense classification
EXPENSE_CATEGORIES = [
    "Groceries", "Dining", "Transportation", "Entertainment", "Shopping",
    "Utilities", "Healthcare", "Personal Care", "Education", "Travel",
    "Subscriptions", "Gifts", "Home", "Clothing", "Electronics",
    "Fitness", "Pets", "Insurance", "Taxes", "Other"
]

def get_bot_setting(key, default=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"SELECT setting_value FROM telegram_bot_settings WHERE setting_key = {ph_single()}", (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else default

def set_bot_setting(key, value):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO telegram_bot_settings (setting_key, setting_value, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (setting_key) DO UPDATE SET 
                setting_value = EXCLUDED.setting_value,
                updated_at = CURRENT_TIMESTAMP
        """, (key, value))
    else:
        cur.execute("""
            INSERT OR REPLACE INTO telegram_bot_settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, value))
    conn.commit()
    conn.close()

def parse_expense_with_ollama(message: str, conversation_context: list = None) -> dict:
    """Parse natural language expense using Ollama NLP."""
    ollama_url = get_bot_setting("ollama_url", "http://localhost:11434")
    ollama_model = get_bot_setting("ollama_model", "llama3.2")
    
    context_str = ""
    if conversation_context:
        context_str = "\n".join([f"- {msg}" for msg in conversation_context[-5:]])
        context_str = f"\nPrevious conversation:\n{context_str}\n"
    
    prompt = f"""You are an expense parsing assistant. Parse the following message into structured expense data.
{context_str}
Message: "{message}"

Extract:
1. amount (number only, no currency symbol)
2. currency (default USD)
3. category (one of: {', '.join(EXPENSE_CATEGORIES)})
4. merchant (store/business name if mentioned)
5. description (brief description of the expense)
6. confidence (0.0 to 1.0 how confident you are in the parsing)

If the message is unclear or you need more information, set needs_clarification to true and provide a clarification_question.

Respond ONLY with valid JSON in this exact format:
{{
    "amount": 45.99,
    "currency": "USD",
    "category": "Groceries",
    "merchant": "Kroger",
    "description": "Weekly grocery shopping",
    "confidence": 0.95,
    "needs_clarification": false,
    "clarification_question": null
}}"""

    try:
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": ollama_model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            parsed = json.loads(result.get("response", "{}"))
            return {
                "success": True,
                "data": parsed,
                "raw_response": result.get("response")
            }
        else:
            return {
                "success": False,
                "error": f"Ollama returned status {response.status_code}",
                "data": None
            }
    except requests.exceptions.ConnectionError:
        return fallback_regex_parser(message)
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse Ollama response: {str(e)}",
            "data": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": None
        }

def fallback_regex_parser(message: str) -> dict:
    """Fallback regex parser when Ollama is unavailable."""
    amount_pattern = r'\$?(\d+(?:\.\d{2})?)'
    amount_match = re.search(amount_pattern, message)
    amount = float(amount_match.group(1)) if amount_match else None
    
    category = "Other"
    category_keywords = {
        "Groceries": ["grocery", "groceries", "kroger", "publix", "walmart", "aldi", "whole foods", "trader joe"],
        "Dining": ["restaurant", "dinner", "lunch", "breakfast", "coffee", "starbucks", "mcdonalds", "chipotle", "ate", "food"],
        "Transportation": ["gas", "uber", "lyft", "parking", "transit", "metro", "fuel"],
        "Entertainment": ["movie", "netflix", "spotify", "concert", "game", "entertainment"],
        "Shopping": ["amazon", "target", "shopping", "bought", "purchased"],
        "Utilities": ["electric", "water", "internet", "phone", "utility"],
        "Healthcare": ["doctor", "pharmacy", "medicine", "cvs", "walgreens", "medical"],
    }
    
    message_lower = message.lower()
    for cat, keywords in category_keywords.items():
        if any(kw in message_lower for kw in keywords):
            category = cat
            break
    
    merchant_patterns = [
        r'at\s+([A-Z][a-zA-Z\s]+?)(?:\s+for|\s+on|\.|$)',
        r'(?:from|to)\s+([A-Z][a-zA-Z\s]+?)(?:\s+for|\s+on|\.|$)',
    ]
    merchant = None
    for pattern in merchant_patterns:
        match = re.search(pattern, message)
        if match:
            merchant = match.group(1).strip()
            break
    
    if amount:
        return {
            "success": True,
            "data": {
                "amount": amount,
                "currency": "USD",
                "category": category,
                "merchant": merchant,
                "description": message[:100],
                "confidence": 0.6,
                "needs_clarification": False,
                "clarification_question": None
            },
            "fallback": True
        }
    else:
        return {
            "success": True,
            "data": {
                "amount": None,
                "currency": "USD",
                "category": None,
                "merchant": None,
                "description": message[:100],
                "confidence": 0.0,
                "needs_clarification": True,
                "clarification_question": "I couldn't find an amount. How much did you spend?"
            },
            "fallback": True
        }

def get_or_create_conversation(telegram_user_id: int, chat_id: int) -> dict:
    """Get or create conversation state for a user."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        SELECT id, conversation_state, pending_expense_data, context_messages
        FROM telegram_bot_conversations
        WHERE telegram_user_id = {ph_single()} AND chat_id = {ph_single()}
    """, (telegram_user_id, chat_id))
    
    row = cur.fetchone()
    
    if row:
        conv_id, state, pending_data, context = row
        if isinstance(pending_data, str):
            pending_data = json.loads(pending_data) if pending_data else {}
        if isinstance(context, str):
            context = json.loads(context) if context else []
        conn.close()
        return {
            "id": conv_id,
            "state": state,
            "pending_data": pending_data or {},
            "context": context or []
        }
    else:
        cur.execute(f"""
            INSERT INTO telegram_bot_conversations 
            (telegram_user_id, chat_id, conversation_state, pending_expense_data, context_messages)
            VALUES ({ph(5)})
        """, (telegram_user_id, chat_id, "idle", json.dumps({}), json.dumps([])))
        conn.commit()
        new_id = cur.lastrowid if not USE_POSTGRES else None
        if USE_POSTGRES:
            cur.execute("SELECT lastval()")
            new_id = cur.fetchone()[0]
        conn.close()
        return {
            "id": new_id,
            "state": "idle",
            "pending_data": {},
            "context": []
        }

def update_conversation(conv_id: int, state: str = None, pending_data: dict = None, context: list = None):
    """Update conversation state."""
    conn = get_conn()
    cur = conn.cursor()
    
    updates = ["updated_at = CURRENT_TIMESTAMP"]
    params = []
    
    if state is not None:
        updates.append(f"conversation_state = {ph_single()}")
        params.append(state)
    if pending_data is not None:
        updates.append(f"pending_expense_data = {ph_single()}")
        params.append(json.dumps(pending_data))
    if context is not None:
        updates.append(f"context_messages = {ph_single()}")
        params.append(json.dumps(context[-10:]))
    
    params.append(conv_id)
    
    cur.execute(f"""
        UPDATE telegram_bot_conversations
        SET {', '.join(updates)}
        WHERE id = {ph_single()}
    """, tuple(params))
    
    conn.commit()
    conn.close()

def log_telegram_expense(telegram_user_id: int, telegram_username: str, chat_id: int,
                         raw_message: str, parsed_data: dict, status: str = "parsed") -> int:
    """Log a telegram expense to the database."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        INSERT INTO telegram_expense_logs
        (telegram_user_id, telegram_username, chat_id, raw_message, parsed_amount,
         currency, category, merchant, description, confidence_score, parsing_status)
        VALUES ({ph(11)})
    """, (
        telegram_user_id,
        telegram_username,
        chat_id,
        raw_message,
        parsed_data.get("amount"),
        parsed_data.get("currency", "USD"),
        parsed_data.get("category"),
        parsed_data.get("merchant"),
        parsed_data.get("description"),
        parsed_data.get("confidence"),
        status
    ))
    
    conn.commit()
    log_id = cur.lastrowid if not USE_POSTGRES else None
    if USE_POSTGRES:
        cur.execute("SELECT lastval()")
        log_id = cur.fetchone()[0]
    conn.close()
    
    return log_id

def insert_to_main_expenses(log_id: int, parsed_data: dict, app_user_id: int = None):
    """Insert parsed expense into main expenses table."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'expenses'
    """ if USE_POSTGRES else """
        PRAGMA table_info(expenses)
    """)
    
    columns = cur.fetchall()
    has_expenses_table = len(columns) > 0
    
    if has_expenses_table and parsed_data.get("amount"):
        try:
            if USE_POSTGRES:
                cur.execute("""
                    INSERT INTO expenses (amount, category, description, date, source)
                    VALUES (%s, %s, %s, CURRENT_DATE, 'telegram_bot')
                    RETURNING id
                """, (
                    parsed_data.get("amount"),
                    parsed_data.get("category", "Other"),
                    f"{parsed_data.get('merchant', '')} - {parsed_data.get('description', '')}"[:255]
                ))
                expense_id = cur.fetchone()[0]
            else:
                cur.execute("""
                    INSERT INTO expenses (amount, category, description, date, source)
                    VALUES (?, ?, ?, DATE('now'), 'telegram_bot')
                """, (
                    parsed_data.get("amount"),
                    parsed_data.get("category", "Other"),
                    f"{parsed_data.get('merchant', '')} - {parsed_data.get('description', '')}"[:255]
                ))
                expense_id = cur.lastrowid
            
            cur.execute(f"""
                UPDATE telegram_expense_logs
                SET linked_expense_id = {ph_single()}, parsing_status = 'synced'
                WHERE id = {ph_single()}
            """, (expense_id, log_id))
            
            conn.commit()
            conn.close()
            return expense_id
        except Exception as e:
            conn.rollback()
            conn.close()
            return None
    
    conn.close()
    return None

def process_telegram_message(message: dict) -> str:
    """Process incoming Telegram message and return response."""
    telegram_user_id = message.get("from", {}).get("id")
    telegram_username = message.get("from", {}).get("username", "")
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    
    if not text or not telegram_user_id:
        return "I couldn't process that message. Please try again."
    
    if text.startswith("/"):
        return handle_command(text, telegram_user_id, chat_id, telegram_username)
    
    conversation = get_or_create_conversation(telegram_user_id, chat_id)
    
    context = conversation.get("context", [])
    context.append(f"User: {text}")
    
    if conversation["state"] == "awaiting_amount":
        pending = conversation.get("pending_data", {})
        amount_match = re.search(r'\$?(\d+(?:\.\d{2})?)', text)
        if amount_match:
            pending["amount"] = float(amount_match.group(1))
            pending["confidence"] = 0.8
            
            log_id = log_telegram_expense(
                telegram_user_id, telegram_username, chat_id,
                pending.get("original_message", text), pending, "parsed"
            )
            insert_to_main_expenses(log_id, pending)
            
            update_conversation(conversation["id"], "idle", {}, context)
            
            return f"✅ Got it! Logged ${pending['amount']:.2f} for {pending.get('category', 'Other')}."
        else:
            return "I still couldn't find an amount. Please enter just the number (e.g., '45.99')."
    
    elif conversation["state"] == "awaiting_category":
        pending = conversation.get("pending_data", {})
        matched_category = None
        text_lower = text.lower()
        for cat in EXPENSE_CATEGORIES:
            if cat.lower() in text_lower or text_lower in cat.lower():
                matched_category = cat
                break
        
        if matched_category:
            pending["category"] = matched_category
            log_id = log_telegram_expense(
                telegram_user_id, telegram_username, chat_id,
                pending.get("original_message", text), pending, "parsed"
            )
            insert_to_main_expenses(log_id, pending)
            
            update_conversation(conversation["id"], "idle", {}, context)
            
            return f"✅ Logged ${pending['amount']:.2f} under {matched_category}."
        else:
            categories_list = ", ".join(EXPENSE_CATEGORIES[:10])
            return f"Please choose a category: {categories_list}, etc."
    
    parsed = parse_expense_with_ollama(text, context)
    
    if parsed["success"] and parsed.get("data"):
        data = parsed["data"]
        data["original_message"] = text
        
        if data.get("needs_clarification") or not data.get("amount"):
            pending_data = {**data, "original_message": text}
            
            if not data.get("amount"):
                update_conversation(conversation["id"], "awaiting_amount", pending_data, context)
                question = data.get("clarification_question", "How much did you spend?")
                return f"💬 {question}"
            elif not data.get("category"):
                update_conversation(conversation["id"], "awaiting_category", pending_data, context)
                return "What category does this expense belong to?"
        
        log_id = log_telegram_expense(
            telegram_user_id, telegram_username, chat_id,
            text, data, "parsed"
        )
        
        insert_to_main_expenses(log_id, data)
        
        update_conversation(conversation["id"], "idle", {}, context)
        
        response_parts = [f"✅ Expense logged!"]
        response_parts.append(f"💰 Amount: ${data['amount']:.2f}")
        if data.get("category"):
            response_parts.append(f"📂 Category: {data['category']}")
        if data.get("merchant"):
            response_parts.append(f"🏪 Merchant: {data['merchant']}")
        if data.get("confidence", 0) < 0.7:
            response_parts.append("\n⚠️ Low confidence - please verify in the app.")
        
        return "\n".join(response_parts)
    else:
        log_telegram_expense(
            telegram_user_id, telegram_username, chat_id,
            text, {"description": text}, "failed"
        )
        return f"❌ I couldn't parse that expense. Error: {parsed.get('error', 'Unknown')}\n\nTry something like: 'Spent $45 at Kroger for groceries'"

def handle_command(command: str, user_id: int, chat_id: int, username: str) -> str:
    """Handle Telegram bot commands."""
    cmd = command.lower().split()[0]
    
    if cmd == "/start":
        return """👋 Welcome to the Budget Bot!

I can help you track expenses through natural language. Just tell me what you spent!

Examples:
• "Spent $45 at Kroger for groceries"
• "Uber ride $12.50"
• "$200 electric bill"

Commands:
/help - Show this help message
/summary - View today's expenses
/categories - List expense categories
/cancel - Cancel current operation"""
    
    elif cmd == "/help":
        return """💡 How to use the Budget Bot:

Just type your expense naturally:
• "Spent $45 at Kroger for groceries"
• "Coffee at Starbucks $5.75"
• "$200 electric bill"

I'll parse the amount, category, and merchant automatically!

Commands:
/summary - Today's expense summary
/week - This week's summary
/categories - List all categories
/cancel - Cancel current conversation"""
    
    elif cmd == "/summary":
        conn = get_conn()
        cur = conn.cursor()
        
        if USE_POSTGRES:
            cur.execute("""
                SELECT COALESCE(SUM(parsed_amount), 0), COUNT(*)
                FROM telegram_expense_logs
                WHERE telegram_user_id = %s
                AND DATE(created_at) = CURRENT_DATE
                AND parsing_status = 'synced'
            """, (user_id,))
        else:
            cur.execute("""
                SELECT COALESCE(SUM(parsed_amount), 0), COUNT(*)
                FROM telegram_expense_logs
                WHERE telegram_user_id = ?
                AND DATE(created_at) = DATE('now')
                AND parsing_status = 'synced'
            """, (user_id,))
        
        total, count = cur.fetchone()
        conn.close()
        
        return f"📊 Today's Summary:\n\n💰 Total: ${float(total):.2f}\n📝 Transactions: {count}"
    
    elif cmd == "/week":
        conn = get_conn()
        cur = conn.cursor()
        
        if USE_POSTGRES:
            cur.execute("""
                SELECT COALESCE(SUM(parsed_amount), 0), COUNT(*)
                FROM telegram_expense_logs
                WHERE telegram_user_id = %s
                AND created_at >= CURRENT_DATE - INTERVAL '7 days'
                AND parsing_status = 'synced'
            """, (user_id,))
        else:
            cur.execute("""
                SELECT COALESCE(SUM(parsed_amount), 0), COUNT(*)
                FROM telegram_expense_logs
                WHERE telegram_user_id = ?
                AND created_at >= DATE('now', '-7 days')
                AND parsing_status = 'synced'
            """, (user_id,))
        
        total, count = cur.fetchone()
        conn.close()
        
        return f"📊 This Week's Summary:\n\n💰 Total: ${float(total):.2f}\n📝 Transactions: {count}"
    
    elif cmd == "/categories":
        cats = "\n".join([f"• {cat}" for cat in EXPENSE_CATEGORIES])
        return f"📂 Available Categories:\n\n{cats}"
    
    elif cmd == "/cancel":
        conversation = get_or_create_conversation(user_id, chat_id)
        update_conversation(conversation["id"], "idle", {}, [])
        return "✅ Conversation cancelled. Ready for a new expense!"
    
    else:
        return "Unknown command. Type /help for available commands."

def handle_webhook(update: dict) -> str:
    """Handle incoming Telegram webhook update."""
    if "message" in update:
        return process_telegram_message(update["message"])
    return ""

def send_telegram_message(chat_id: int, text: str) -> bool:
    """Send a message via Telegram Bot API."""
    bot_token = get_bot_setting("telegram_bot_token")
    if not bot_token:
        return False
    
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML"
            },
            timeout=10
        )
        return response.status_code == 200
    except Exception:
        return False

def get_recent_logs(limit: int = 50, status_filter: str = None):
    """Get recent telegram expense logs."""
    conn = get_conn()
    cur = conn.cursor()
    
    query = """
        SELECT id, telegram_user_id, telegram_username, raw_message, parsed_amount,
               category, merchant, parsing_status, created_at
        FROM telegram_expense_logs
    """
    params = []
    
    if status_filter:
        query += f" WHERE parsing_status = {ph_single()}"
        params.append(status_filter)
    
    query += " ORDER BY created_at DESC"
    query += f" LIMIT {ph_single()}"
    params.append(limit)
    
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    conn.close()
    
    return [{
        "id": r[0],
        "telegram_user_id": r[1],
        "telegram_username": r[2],
        "raw_message": r[3],
        "parsed_amount": r[4],
        "category": r[5],
        "merchant": r[6],
        "status": r[7],
        "created_at": r[8]
    } for r in rows]

def update_expense_log(log_id: int, amount: float, category: str, merchant: str):
    """Update an expense log entry."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"""
        UPDATE telegram_expense_logs
        SET parsed_amount = {ph_single()}, category = {ph_single()}, merchant = {ph_single()},
            parsing_status = 'edited', updated_at = CURRENT_TIMESTAMP
        WHERE id = {ph_single()}
    """, (amount, category, merchant, log_id))
    
    conn.commit()
    conn.close()

def delete_expense_log(log_id: int):
    """Delete an expense log entry."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute(f"DELETE FROM telegram_expense_logs WHERE id = {ph_single()}", (log_id,))
    
    conn.commit()
    conn.close()

def get_authorized_users():
    """Get list of authorized Telegram users."""
    conn = get_conn()
    cur = conn.cursor()