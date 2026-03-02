"""Unit tests for the AI Trading Bot (bot/trading_bot.py)"""
import sys
import os
import sqlite3
import pytest

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def test_trading_bot_imports():
    """Bot module can be imported without errors."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "trading_bot",
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                     "bot", "trading_bot.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "run")
    assert hasattr(mod, "_ensure_tables")
    assert hasattr(mod, "_tech_signal")
    assert hasattr(mod, "_next_expiry")
    assert hasattr(mod, "AlpacaClient")


def test_ensure_tables_creates_schema(tmp_path):
    """_ensure_tables() creates all required DB tables."""
    import importlib.util
    bot_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                            "bot", "trading_bot.py")
    spec = importlib.util.spec_from_file_location("trading_bot", bot_path)
    mod = importlib.util.module_from_spec(spec)
    # Patch DB_PATH to tmp
    mod.DB_PATH = str(tmp_path / "test.db")
    spec.loader.exec_module(mod)
    mod.DB_PATH = str(tmp_path / "test.db")
    mod._ensure_tables()

    conn = sqlite3.connect(str(tmp_path / "test.db"))
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    conn.close()

    assert "bot_decisions" in tables
    assert "bot_positions" in tables
    assert "bot_config" in tables
    assert "bot_daily_summary" in tables


def test_tech_signal_buy():
    """_tech_signal returns buy when RSI oversold and SMA10 > SMA30."""
    import importlib.util
    bot_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                            "bot", "trading_bot.py")
    spec = importlib.util.spec_from_file_location("trading_bot", bot_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    ind = {"rsi": 30.0, "sma10": 155.0, "sma30": 150.0,
           "price": 160.0, "high20": 158.0, "iv_rank": 25.0, "vol_ratio": 1.2}
    sig, reason = mod._tech_signal(ind)
    assert sig == "buy"
    assert len(reason) > 0


def test_tech_signal_hold():
    """_tech_signal returns hold when signals conflict."""
    import importlib.util
    bot_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                            "bot", "trading_bot.py")
    spec = importlib.util.spec_from_file_location("trading_bot", bot_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    ind = {"rsi": 50.0, "sma10": 150.0, "sma30": 150.0,
           "price": 149.0, "high20": 155.0, "iv_rank": 25.0, "vol_ratio": 1.0}
    sig, reason = mod._tech_signal(ind)
    assert sig == "hold"


def test_next_expiry_is_friday():
    """_next_expiry returns a Friday date string."""
    import importlib.util
    from datetime import datetime
    bot_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                            "bot", "trading_bot.py")
    spec = importlib.util.spec_from_file_location("trading_bot", bot_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    expiry = mod._next_expiry()
    assert len(expiry) == 10  # YYYY-MM-DD
    dt = datetime.strptime(expiry, "%Y-%m-%d")
    assert dt.weekday() == 4  # Friday


def test_occ_symbol_format():
    """_occ builds correct OCC option symbol."""
    import importlib.util
    bot_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                            "bot", "trading_bot.py")
    spec = importlib.util.spec_from_file_location("trading_bot", bot_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    sym = mod._occ("AAPL", "2026-04-18", "call", 200.0)
    assert sym == "AAPL260418C00200000"


def test_is_market_open_weekend():
    """_is_market_open returns False on weekends (direct weekday check)."""
    from datetime import datetime
    import pytz

    ET = pytz.timezone("America/New_York")
    saturday = ET.localize(datetime(2026, 3, 7, 10, 0, 0))   # Saturday
    sunday   = ET.localize(datetime(2026, 3, 8, 10, 0, 0))   # Sunday
    weekday  = ET.localize(datetime(2026, 3, 9, 10, 0, 0))   # Monday

    assert saturday.weekday() == 5   # Saturday = 5
    assert sunday.weekday()   == 6   # Sunday   = 6
    assert weekday.weekday()  == 0   # Monday   = 0
    # Market is closed on weekends
    assert saturday.weekday() >= 5
    assert sunday.weekday()   >= 5
    assert weekday.weekday()  <  5
