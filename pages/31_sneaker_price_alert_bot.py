import streamlit as st
import os
import sys
import json
import time
import re
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="Sneaker Price Alert Bot", page_icon="🍑", layout="wide")

from utils.db import get_conn, USE_POSTGRES, execute as db_exec, init_db, get_setting, set_setting
from utils.auth import require_login, render_sidebar_brand, render_sidebar_user_widget, inject_css

init_db()
inject_css()
require_login()

# Sidebar
render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py", label="Overview", icon="📊")
st.sidebar.page_link("pages/22_todo.py", label="Todo", icon="✅")
st.sidebar.page_link("pages/24_creator_companion.py", label="Creator", icon="🎬")
st.sidebar.page_link("pages/25_notes.py", label="Notes", icon="📝")
st.sidebar.page_link("pages/26_media_library.py", label="Media Library", icon="🎵")
st.sidebar.page_link("pages/17_personal_assistant.py", label="Personal Assistant", icon="🤖")
render_sidebar_user_widget()


def _ph(count: int = 1) -> str:
    """Return placeholder(s) for SQL queries based on database type."""
    if USE_POSTGRES:
        return ", ".join(["%s"] * count)
    return ", ".join(["?"] * count)


def _ensure_tables():
    """Create required database tables if they don't exist."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_watchlist (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku VARCHAR(100) NOT NULL,
                name VARCHAR(255),
                target_buy_price DECIMAL(10, 2),
                target_sell_price DECIMAL(10, 2),
                size VARCHAR(20),
                condition VARCHAR(50) DEFAULT 'any',
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, sku, size)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_price_history (
                id SERIAL PRIMARY KEY,
                watchlist_id INTEGER REFERENCES sneaker_watchlist(id) ON DELETE CASCADE,
                sku VARCHAR(100) NOT NULL,
                platform VARCHAR(50) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                condition VARCHAR(50),
                listing_url TEXT,
                listing_title TEXT,
                size VARCHAR(20),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_alerts (
                id SERIAL PRIMARY KEY,
                watchlist_id INTEGER REFERENCES sneaker_watchlist(id) ON DELETE CASCADE,
                alert_type VARCHAR(20) NOT NULL,
                platform VARCHAR(50) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                listing_url TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                acknowledged BOOLEAN DEFAULT FALSE
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_poll_log (
                id SERIAL PRIMARY KEY,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                items_found INTEGER DEFAULT 0,
                alerts_sent INTEGER DEFAULT 0,
                status VARCHAR(50) DEFAULT 'running',
                error_message TEXT
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sku TEXT NOT NULL,
                name TEXT,
                target_buy_price REAL,
                target_sell_price REAL,
                size TEXT,
                condition TEXT DEFAULT 'any',
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, sku, size)
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watchlist_id INTEGER,
                sku TEXT NOT NULL,
                platform TEXT NOT NULL,
                price REAL NOT NULL,
                condition TEXT,
                listing_url TEXT,
                listing_title TEXT,
                size TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (watchlist_id) REFERENCES sneaker_watchlist(id) ON DELETE CASCADE
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watchlist_id INTEGER,
                alert_type TEXT NOT NULL,
                platform TEXT NOT NULL,
                price REAL NOT NULL,
                listing_url TEXT,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                acknowledged INTEGER DEFAULT 0,
                FOREIGN KEY (watchlist_id) REFERENCES sneaker_watchlist(id) ON DELETE CASCADE
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sneaker_poll_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                items_found INTEGER DEFAULT 0,
                alerts_sent INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running',
                error_message TEXT
            )
        """)
    
    conn.commit()
    conn.close()


_ensure_tables()


# ============================================================================
# eBay API Helper
# ============================================================================
class EbayHelper:
    """Helper class for eBay API interactions."""
    
    @staticmethod
    def search_by_sku(sku: str, size: Optional[str] = None, condition: str = "any") -> List[Dict]:
        """
        Search eBay for sneaker listings by SKU.
        Uses eBay Browse API (requires app credentials).
        """
        app_id = get_setting("ebay_app_id")
        if not app_id:
            return []
        
        try:
            # Build search query
            query = f"{sku} sneakers"
            if size:
                query += f" size {size}"
            
            # eBay Browse API endpoint
            url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
            
            headers = {
                "Authorization": f"Bearer {EbayHelper._get_oauth_token(app_id)}",
                "Content-Type": "application/json",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"
            }
            
            params = {
                "q": query,
                "category_ids": "93427",  # Athletic Shoes category
                "limit": 50,
                "sort": "price"
            }
            
            if condition.lower() == "new":
                params["filter"] = "conditionIds:{1000}"
            elif condition.lower() == "used":
                params["filter"] = "conditionIds:{3000|4000|5000|6000}"
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                listings = []
                
                for item in data.get("itemSummaries", []):
                    price_info = item.get("price", {})
                    listings.append({
                        "platform": "eBay",
                        "title": item.get("title", ""),
                        "price": float(price_info.get("value", 0)),
                        "condition": item.get("condition", "Unknown"),
                        "url": item.get("itemWebUrl", ""),
                        "image": item.get("image", {}).get("imageUrl", ""),
                        "item_id": item.get("itemId", "")
                    })
                
                return listings
            else:
                st.warning(f"eBay API returned status {response.status_code}")
                return []
                
        except Exception as e:
            st.error(f"eBay search error: {str(e)}")
            return []
    
    @staticmethod
    def _get_oauth_token(app_id: str) -> str:
        """Get eBay OAuth token using client credentials."""
        cert_id = get_setting("ebay_cert_id")
        if not cert_id:
            return ""
        
        try:
            import base64
            credentials = base64.b64encode(f"{app_id}:{cert_id}".encode()).decode()
            
            url = "https://api.ebay.com/identity/v1/oauth2/token"
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {credentials}"
            }
            data = {
                "grant_type": "client_credentials",
                "scope": "https://api.ebay.com/oauth/api_scope"
            }
            
            response = requests.post(url, headers=headers, data=data, timeout=30)
            if response.status_code == 200:
                return response.json().get("access_token", "")
            return ""
        except Exception:
            return ""
    
    @staticmethod
    def search_mock(sku: str, size: Optional[str] = None) -> List[Dict]:
        """Mock eBay search for testing/demo purposes."""
        import random
        
        base_prices = {
            "DD1391-100": 180,  # Jordan 1 Retro High OG
            "CW2288-111": 130,  # Air Force 1
            "FQ8060-121": 220,  # Air Jordan 4
            "DV0833-105": 200,  # Dunk Low
        }
        
        base_price = base_prices.get(sku, random.randint(100, 300))
        listings = []
        
        for i in range(random.randint(3, 8)):
            variance = random.uniform(-0.2, 0.3)
            price = round(base_price * (1 + variance), 2)
            condition = random.choice(["New", "Pre-owned", "Open box"])
            
            listings.append({
                "platform": "eBay",
                "title": f"Nike/Jordan {sku} {'Size ' + size if size else ''} {condition}",
                "price": price,
                "condition": condition,
                "url": f"https://www.ebay.com/itm/{random.randint(100000000, 999999999)}",
                "image": "",
                "item_id": str(random.randint(100000000, 999999999))
            })
        
        return sorted(listings, key=lambda x: x["price"])


# ============================================================================
# Mercari Scraper Helper
# ============================================================================
class MercariHelper:
    """Helper class for Mercari web scraping."""
    
    @staticmethod
    def search_by_sku(sku: str, size: Optional[str] = None, condition: str = "any") -> List[Dict]:
        """
        Search Mercari for sneaker listings by SKU.
        Uses web scraping since Mercari doesn't have a public API.
        """
        try:
            query = f"{sku}"
            if size:
                query += f" size {size}"
            
            url = f"https://www.mercari.com/search/?keyword={requests.utils.quote(query)}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return MercariHelper._parse_search_results(response.text, sku)
            else:
                return []
                
        except Exception as e:
            st.error(f"Mercari search error: {str(e)}")
            return []
    
    @staticmethod
    def _parse_search_results(html: str, sku: str) -> List[Dict]:
        """Parse Mercari search results HTML."""
        listings = []
        
        try:
            # Simple regex-based parsing (BeautifulSoup would be better for production)
            price_pattern = r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)'
            prices = re.findall(price_pattern, html)
            
            for i, price_str in enumerate(prices[:20]):  # Limit to 20 results
                price = float(price_str.replace(",", ""))
                listings.append({
                    "platform": "Mercari",
                    "title": f"{sku} Listing #{i+1}",
                    "price": price,
                    "condition": "Unknown",
                    "url": f"https://www.mercari.com/search/?keyword={sku}",
                    "image": "",
                    "item_id": f"mercari_{i}"
                })
        except Exception:
            pass
        
        return listings
    
    @staticmethod
    def search_mock(sku: str, size: Optional[str] = None) -> List[Dict]:
        """Mock Mercari search for testing/demo purposes."""
        import random
        
        base_prices = {
            "DD1391-100": 165,
            "CW2288-111": 110,
            "FQ8060-121": 195,
            "DV0833-105": 175,
        }
        
        base_price = base_prices.get(sku, random.randint(80, 250))
        listings = []
        
        for i in range(random.randint(2, 6)):
            variance = random.uniform(-0.25, 0.25)
            price = round(base_price * (1 + variance), 2)
            condition = random.choice(["New with tags", "Like new", "Good", "Fair"])
            
            listings.append({
                "platform": "Mercari",
                "title": f"{sku} Sneakers {'Size ' + size if size else ''} - {condition}",
                "price": price,
                "condition": condition,
                "url": f"https://www.mercari.com/us/item/{random.randint(100000, 999999)}",
                "image": "",
                "item_id": f"m{random.randint(100000, 999999)}"
            })
        
        return sorted(listings, key=lambda x: x["price"])


# ============================================================================
# Telegram Bot Helper
# ============================================================================
class TelegramHelper:
    """Helper class for Telegram bot notifications."""
    
    @staticmethod
    def send_alert(alert_type: str, sneaker_name: str, sku: str, price: float, 
                   target_price: float, platform: str, listing_url: str) -> bool:
        """Send a formatted buy/sell alert via Telegram."""
        bot_token = get_setting("telegram_bot_token")
        chat_id = get_setting("telegram_chat_id")
        
        if not bot_token or not chat_id:
            return False
        
        try:
            emoji = "🟢" if alert_type == "BUY" else "🔴"
            action = "BUY SIGNAL" if alert_type == "BUY" else "SELL SIGNAL"
            
            message = f"""
{emoji} *SNEAKER {action}* {emoji}

👟 *{sneaker_name}*
📦 SKU: `{sku}`
💰 Current Price: *${price:.2f}*
🎯 Target: ${target_price:.2f}
📍 Platform: {platform}

🔗 [View Listing]({listing_url})

_Peach State Savings - Sneaker Bot_
"""
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False
            }
            
            response = requests.post(url, json=payload, timeout=30)
            return response.status_code == 200
            
        except Exception as e:
            st.error(f"Telegram send error: {str(e)}")
            return False
    
    @staticmethod
    def send_summary(total_items: int, buy_signals: int, sell_signals: int) -> bool:
        """Send a polling summary via Telegram."""
        bot_token = get_setting("telegram_bot_token")
        chat_id = get_setting("telegram_chat_id")
        
        if not bot_token or not chat_id:
            return False
        
        try:
            message = f"""
📊 *Sneaker Bot Summary*

🔍 Items Scanned: {total_items}
🟢 Buy Signals: {buy_signals}
🔴 Sell Signals: {sell_signals}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload, timeout=30)
            return response.status_code == 200
            
        except Exception:
            return False
    
    @staticmethod
    def test_connection() -> tuple[bool, str]:
        """Test Telegram bot connection."""
        bot_token = get_setting("telegram_bot_token")
        chat_id = get_setting("telegram_chat_id")
        
        if not bot_token:
            return False, "Bot token not configured"
        if not chat_id:
            return False, "Chat ID not configured"
        
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": "🍑 Sneaker Bot connected successfully!",
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                return True, "Connected successfully!"
            else:
                error = response.json().get("description", "Unknown error")
                return False, f"API Error: {error}"
                
        except Exception as e:
            return False, f"Connection error: {str(e)}"


# ============================================================================
# Price Signal Logic
# ============================================================================
class PriceSignalEngine:
    """Engine for analyzing prices and generating buy/sell signals."""
    
    @staticmethod
    def analyze_listings(watchlist_item: Dict, listings: List[Dict]) -> List[Dict]:
        """
        Compare current listings against watchlist thresholds.
        Returns list of signals (buy/sell alerts).
        """
        signals = []
        
        target_buy = watchlist_item.get("target_buy_price")
        target_sell = watchlist_item.get("target_sell_price")
        
        for listing in listings:
            price = listing.get("price", 0)
            
            # Buy signal: price is at or below target buy price
            if target_buy and price <= target_buy:
                signals.append({
                    "type": "BUY",
                    "listing": listing,
                    "target_price": target_buy,
                    "savings": target_buy - price
                })
            
            # Sell signal: price is at or above target sell price
            # (Useful if user owns inventory and wants to know when to list)
            elif target_sell and price >= target_sell:
                signals.append({
                    "type": "SELL",
                    "listing": listing,
                    "target_price": target_sell,
                    "profit_potential": price - target_sell
                })
        
        return signals
    
    @staticmethod
    def get_price_statistics(listings: List[Dict]) -> Dict:
        """Calculate price statistics from listings."""
        if not listings:
            return {"min": 0, "max": 0, "avg": 0, "median": 0, "count": 0}
        
        prices = [l["price"] for l in listings if l.get("price", 0) > 0]
        
        if not prices:
            return {"min": 0, "max": 0, "avg": 0, "median": 0, "count": 0}
        
        prices_sorted = sorted(prices)
        n = len(prices_sorted)
        
        return {
            "min": min(prices),
            "max": max(prices),
            "avg": sum(prices) / n,
            "median": prices_sorted[n // 2] if n % 2 else (prices_sorted[n // 2 - 1] + prices_sorted[n // 2]) / 2,
            "count": n
        }


# ============================================================================
# Background Polling Job
# ============================================================================
def run_polling_job(use_mock: bool = True) -> Dict:
    """
    Run the background polling job.
    Scans all active watchlist items and checks for price signals.
    """
    conn = get_conn()
    cur = conn.cursor()
    
    # Log poll start
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO sneaker_poll_log (status) VALUES ('running') RETURNING id
        """)
        poll_id = cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO sneaker_poll_log (status) VALUES ('running')
        """)
        poll_id = cur.lastrowid
    conn.commit()
    
    results = {
        "items_found": 0,
        "alerts_sent": 0,
        "buy_signals": 0,
        "sell_signals": 0,
        "errors": []
    }
    
    try:
        # Get all active watchlist items
        if USE_POSTGRES:
            cur.execute("""
                SELECT id, user_id, sku, name, target_buy_price, target_sell_price, size, condition
                FROM sneaker_watchlist WHERE active = TRUE
            """)
        else:
            cur.execute("""
                SELECT id, user_id, sku, name, target_buy_price, target_sell_price, size, condition
                FROM sneaker_watchlist WHERE active = 1
            """)
        
        watchlist_items = cur.fetchall()
        
        for item in watchlist_items:
            item_id, user_id, sku, name, target_buy, target_sell, size, condition = item
            
            # Search both platforms
            if use_mock:
                ebay_listings = EbayHelper.search_mock(sku, size)
                mercari_listings = MercariHelper.search_mock(sku, size)
            else:
                ebay_listings = EbayHelper.search_by_sku(sku, size, condition or "any")
                mercari_listings = MercariHelper.search_by_sku(sku, size, condition or "any")
            
            all_listings = ebay_listings + mercari_listings
            results["items_found"] += len(all_listings)
            
            # Save price history
            for listing in all_listings:
                if USE_POSTGRES:
                    cur.execute(f"""
                        INSERT INTO sneaker_price_history 
                        (watchlist_id, sku, platform, price, condition, listing_url, listing_title, size)
                        VALUES ({_ph(8)})
                    """, (item_id, sku, listing["platform"], listing["price"], 
                          listing["condition"], listing["url"], listing["title"], size))
                else:
                    cur.execute(f"""
                        INSERT INTO sneaker_price_history 
                        (watchlist_id, sku, platform, price, condition, listing_url, listing_title, size)
                        VALUES ({_ph(8)})
                    """, (item_id, sku, listing["platform"], listing["price"], 
                          listing["condition"], listing["url"], listing["title"], size))
            
            # Check for signals
            watchlist_dict = {
                "target_buy_price": target_buy,
                "target_sell_price": target_sell
            }
            
            signals = PriceSignalEngine.analyze_listings(watchlist_dict, all_listings)
            
            for signal in signals:
                listing = signal["listing"]
                
                # Send Telegram alert
                alert_sent = TelegramHelper.send_alert(
                    alert_type=signal["type"],
                    sneaker_name=name or sku,
                    sku=sku,
                    price=listing["price"],
                    target_price=signal["target_price"],
                    platform=listing["platform"],
                    listing_url=listing["url"]
                )
                
                # Log alert
                if USE_POSTGRES:
                    cur.execute(f"""
                        INSERT INTO sneaker_alerts 
                        (watchlist_id, alert_type, platform, price, listing_url)
                        VALUES ({_ph(5)})
                    """, (item_id, signal["type"], listing["platform"], 
                          listing["price"], listing["url"]))
                else:
                    cur.execute(f"""
                        INSERT INTO sneaker_alerts 
                        (watchlist_id, alert_type, platform, price, listing_url)
                        VALUES ({_ph(5)})
                    """, (item_id, signal["type"], listing["platform"], 
                          listing["price"], listing["url"]))
                
                if alert_sent:
                    results["alerts_sent"] += 1
                
                if signal["type"] == "BUY":
                    results["buy_signals"] += 1
                else:
                    results["sell_signals"] += 1
        
        conn.commit()
        
        # Update poll log
        if USE_POSTGRES:
            cur.execute(f"""
                UPDATE sneaker_poll_log 
                SET completed_at = CURRENT_TIMESTAMP, 
                    items_found = {_ph()}, 
                    alerts_sent = {_ph()}, 
                    status = 'completed'
                WHERE id = {_ph()}
            """, (results["items_found"], results["alerts_sent"], poll_id))
        else:
            cur.execute(f"""
                UPDATE sneaker_poll_log 
                SET completed_at = CURRENT_TIMESTAMP, 
                    items_found = {_ph()}, 
                    alerts_sent = {_ph()}, 
                    status = 'completed'
                WHERE id = {_ph()}
            """, (results["items_found"], results["alerts_sent"], poll_id))
        
        conn.commit()
        
    except Exception as e:
        results["errors"].append(str(e))
        
        if USE_POSTGRES:
            cur.execute(f"""
                UPDATE sneaker_poll_log 
                SET completed_at = CURRENT_TIMESTAMP, 
                    status = 'error',
                    error_message = {_ph()}
                WHERE id = {_ph()}
            """, (str(e), poll_id))
        else:
            cur.execute(f"""
                UPDATE sneaker_poll_log 
                SET completed_at = CURRENT_TIMESTAMP, 
                    status = 'error',
                    error_message = {_ph()}
                WHERE id = {_ph()}
            """, (str(e), poll_id))
        
        conn.commit()
    
    conn.close()
    return results


# ============================================================================
# CRUD Operations
# ============================================================================
def get_watchlist(user_id: int) -> List[Dict]:
    """Get all watchlist items for a user."""
    conn = get_conn()
    cur = conn.cursor()
    
    if USE_POSTGRES:
        cur.execute("""
            SELECT id, sku, name, target_buy_price, target_sell_price, size, condition, active, created_at
            FROM sneaker_watchlist 
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (user_id,))
    else:
        cur.execute("""
            SELECT id, sku, name, target_buy_price, target_sell_price, size, condition, active, created_at
            FROM sneaker_watchlist 
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
    
    rows = cur.fetchall()
    conn.close()
    
    return [
        {
            "id": r[0],
            "sku": r[1],
            "name": r[2],
            "target_buy_price": r[3],
            "target_sell_price": r[4],
            "size": r[5],
            "condition": r[6],
            "active": r[7] if USE_POSTGRES else bool(r[7]),
            "created_at": r[8]
        }
        for r in rows
    ]


def add_to_watchlist(user_id: int, sku: str, name: str, target_buy: float, 
                     target_sell: float, size: str, condition: str) -> bool:
    """Add a sneaker to the watchlist."""
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cur.execute(f"""
                INSERT INTO sneaker_watchlist 
                (user_id, sku, name, target_buy_price, target_sell_price, size, condition)
                VALUES ({_ph(7)})
                ON CONFLICT (user_id, sku, size) DO UPDATE SET
                    name = EXCLUDED.name,
                    target_buy_price = EXCLUDED.target_buy_price,
                    target_sell_price = EXCLUDED.target_sell_price,
                    condition = EXCLUDED.condition,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, sku, name, target_buy, target_sell, size, condition))
        else:
            cur.execute(f"""
                INSERT OR REPLACE INTO sneaker_watchlist 
                (user_id, sku, name, target_buy_price, target_sell_price, size, condition)
                VALUES ({_ph(7)})
            """, (user_id, sku, name, target_buy, target_sell, size, condition))
        
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False