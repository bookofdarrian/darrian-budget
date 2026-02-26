-- setup_db.sql — Run this ONCE on your Railway Postgres to create the tables
-- the Sole Alert Bot needs.
--
-- Run it from your Mac:
--   psql $DATABASE_URL -f setup_db.sql
--
-- Or from CT100:
--   psql $DATABASE_URL -f /opt/sole-alert/setup_db.sql
--
-- Safe to re-run — all statements use IF NOT EXISTS.

-- ── Inventory — your shoes + cost basis ──────────────────────────────────────
-- This is the same table the budget app uses (sole_archive).
-- The bot reads status='inventory' rows to know what to monitor.
CREATE TABLE IF NOT EXISTS sole_archive (
    id          SERIAL PRIMARY KEY,
    date        TEXT        NOT NULL,
    item        TEXT        NOT NULL,
    size        TEXT,
    buy_price   NUMERIC(10,2) NOT NULL DEFAULT 0,
    sell_price  NUMERIC(10,2) DEFAULT 0,
    platform    TEXT,
    fees        NUMERIC(10,2) DEFAULT 0,
    shipping    NUMERIC(10,2) DEFAULT 0,
    status      TEXT        DEFAULT 'inventory',   -- 'inventory' | 'sold'
    notes       TEXT
);

CREATE INDEX IF NOT EXISTS idx_sole_archive_status
    ON sole_archive (status);

-- ── App settings — key/value store for eBay credentials + bot thresholds ─────
-- Shared with the budget app (pages/3_business_tracker.py).
-- Keys used by the bot: ebay_client_id, ebay_client_secret,
--                       min_profit_threshold, ebay_fee_rate, mercari_fee_rate
CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

-- ── Price history — one row per check per item ────────────────────────────────
-- Used to draw price trend charts in the budget app.
CREATE TABLE IF NOT EXISTS price_history (
    id          SERIAL PRIMARY KEY,
    item        TEXT        NOT NULL,
    size        TEXT,
    ebay_avg    NUMERIC(10,2),
    ebay_low    NUMERIC(10,2),
    mercari_avg NUMERIC(10,2),
    mercari_low NUMERIC(10,2),
    checked_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_price_history_item
    ON price_history (item, size, checked_at DESC);

-- ── Alert log — prevents spam, one row per alert sent ────────────────────────
CREATE TABLE IF NOT EXISTS alert_log (
    id          SERIAL PRIMARY KEY,
    item        TEXT        NOT NULL,
    size        TEXT,
    platform    TEXT        NOT NULL,   -- 'ebay' | 'mercari' | 'arb'
    sell_price  NUMERIC(10,2),
    profit      NUMERIC(10,2),
    alerted_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_log_item
    ON alert_log (item, size, platform, alerted_at DESC);

-- ── Verify ────────────────────────────────────────────────────────────────────
SELECT table_name, COUNT(*) AS rows FROM (
    SELECT 'sole_archive'  AS table_name, COUNT(*) FROM sole_archive
    UNION ALL
    SELECT 'app_settings',                COUNT(*) FROM app_settings
    UNION ALL
    SELECT 'price_history',               COUNT(*) FROM price_history
    UNION ALL
    SELECT 'alert_log',                   COUNT(*) FROM alert_log
) t
GROUP BY table_name
ORDER BY table_name;
