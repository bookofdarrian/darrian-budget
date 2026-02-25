import os
import streamlit as st
import pandas as pd
import anthropic
import requests
from datetime import datetime, timedelta
from utils.db import init_db, get_setting, set_setting, load_investment_context
from utils.auth import require_login, require_pro, render_sidebar_brand, render_sidebar_user_widget, inject_css

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(page_title="Market News — Peach State Savings", page_icon="📰", layout="wide", initial_sidebar_state="auto")
init_db()
require_login()
require_pro("Market News & Sentiment Analysis")
inject_css()

render_sidebar_brand()
st.sidebar.markdown("---")
st.sidebar.page_link("app.py",                    label="Overview",          icon="📊")
st.sidebar.page_link("pages/1_expenses.py",       label="Expenses",          icon="📋")
st.sidebar.page_link("pages/2_income.py",         label="Income",            icon="💵")
st.sidebar.page_link("pages/3_business_tracker.py",   label="Business Tracker 🔒", icon="💼")
st.sidebar.page_link("pages/4_trends.py",         label="Monthly Trends",    icon="📈")
st.sidebar.page_link("pages/5_bank_import.py",    label="Bank Import",       icon="🏦")
st.sidebar.page_link("pages/6_receipts.py",       label="Receipts & HSA",    icon="🧾")
st.sidebar.page_link("pages/7_ai_insights.py",    label="AI Insights 🔒",    icon="🤖")
st.sidebar.page_link("pages/8_goals.py",          label="Financial Goals",   icon="🎯")
st.sidebar.page_link("pages/9_net_worth.py",      label="Net Worth 🔒",      icon="💎")
st.sidebar.page_link("pages/10_rsu_espp.py",      label="RSU/ESPP Advisor 🔒", icon="📈")
st.sidebar.page_link("pages/11_portfolio.py",     label="Portfolio Analysis 🔒", icon="🗂️")
st.sidebar.page_link("pages/12_market_news.py",   label="Market News 🔒",    icon="📰")
st.sidebar.page_link("pages/13_backtesting.py",   label="Strategy Backtest 🔒", icon="🔬")
st.sidebar.page_link("pages/14_trading_bot.py",   label="Paper Trading Bot 🔒", icon="🤖")
st.sidebar.page_link("pages/0_pricing.py",        label="⭐ Upgrade to Pro", icon="⭐")
render_sidebar_user_widget()

# ── API Keys ──────────────────────────────────────────────────────────────────
_env_claude = os.environ.get("ANTHROPIC_API_KEY", "")
_env_finnhub = os.environ.get("FINNHUB_API_KEY", "")

if "api_key" not in st.session_state:
    if _env_claude:
        st.session_state["api_key"] = _env_claude
    else:
        _db_key = get_setting("anthropic_api_key", "")
        if _db_key:
            st.session_state["api_key"] = _db_key

if "finnhub_key" not in st.session_state:
    if _env_finnhub:
        st.session_state["finnhub_key"] = _env_finnhub
    else:
        _db_fh = get_setting("finnhub_api_key", "")
        if _db_fh:
            st.session_state["finnhub_key"] = _db_fh

api_key      = st.session_state.get("api_key", "")
finnhub_key  = st.session_state.get("finnhub_key", "")

st.title("📰 Market News & Sentiment Analysis")
st.caption("Curated news filtered to YOUR tickers — Claude summarizes each story neutrally and flags signal vs noise.")

# ── API Key Setup ─────────────────────────────────────────────────────────────
with st.expander("🔑 API Key Setup", expanded=not (api_key and finnhub_key)):
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Anthropic (Claude)**")
        if api_key:
            st.success("✅ Claude key loaded")
        else:
            st.warning("⚠️ No Claude key — go to AI Insights to save it")

    with col_b:
        st.markdown("**Finnhub API Key**")
        st.caption("Free at [finnhub.io](https://finnhub.io) — takes 2 minutes, no credit card")
        fh_input = st.text_input("Finnhub API Key", type="password",
                                  value=finnhub_key,
                                  placeholder="d1abc123...",
                                  key="fh_key_input")
        if st.button("💾 Save Finnhub Key", key="save_fh"):
            if fh_input.strip():
                st.session_state["finnhub_key"] = fh_input.strip()
                set_setting("finnhub_api_key", fh_input.strip())
                finnhub_key = fh_input.strip()
                st.success("✅ Finnhub key saved!")
                st.rerun()

if not api_key:
    st.info("👆 Save your Anthropic API key in AI Insights first.")
    st.stop()

# ── Ticker Watchlist ──────────────────────────────────────────────────────────
st.subheader("📋 Your Watchlist")
st.caption("Add tickers you care about — your RSU company, ETFs, individual stocks.")

_inv = load_investment_context()
_inv_notes = _inv.get("notes", "") or ""

if "watchlist" not in st.session_state:
    # Pre-seed with common tickers
    st.session_state["watchlist"] = ["AAPL", "MSFT", "SPY", "QQQ"]

wl_col1, wl_col2 = st.columns([3, 1])
with wl_col1:
    new_ticker_input = st.text_input("Add ticker", placeholder="e.g. NVDA, TSLA, META", key="new_watch_ticker")
with wl_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("➕ Add", key="add_watch"):
        tickers_to_add = [t.strip().upper() for t in new_ticker_input.replace(",", " ").split() if t.strip()]
        for t in tickers_to_add:
            if t and t not in st.session_state["watchlist"]:
                st.session_state["watchlist"].append(t)
        st.rerun()

# Display watchlist as removable chips
if st.session_state["watchlist"]:
    chip_cols = st.columns(min(len(st.session_state["watchlist"]), 8))
    for i, ticker in enumerate(st.session_state["watchlist"]):
        with chip_cols[i % 8]:
            if st.button(f"✕ {ticker}", key=f"rm_{ticker}", help=f"Remove {ticker}"):
                st.session_state["watchlist"].remove(ticker)
                st.rerun()

st.markdown("---")

# ── News Fetch Functions ───────────────────────────────────────────────────────
def fetch_finnhub_news(ticker: str, api_key_fh: str, days_back: int = 7) -> list:
    """Fetch company news from Finnhub for a given ticker."""
    if not api_key_fh:
        return []
    end_date   = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    try:
        url = f"https://finnhub.io/api/v1/company-news"
        params = {"symbol": ticker, "from": start_date, "to": end_date, "token": api_key_fh}
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()[:10]  # cap at 10 per ticker
        return []
    except Exception:
        return []

def fetch_finnhub_market_news(api_key_fh: str, category: str = "general") -> list:
    """Fetch general market news from Finnhub."""
    if not api_key_fh:
        return []
    try:
        url = f"https://finnhub.io/api/v1/news"
        params = {"category": category, "token": api_key_fh}
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()[:15]
        return []
    except Exception:
        return []

def fetch_yahoo_rss(ticker: str) -> list:
    """Fetch news from Yahoo Finance RSS (no API key needed)."""
    try:
        import feedparser
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
        feed = feedparser.parse(url)
        articles = []
        for entry in feed.entries[:5]:
            articles.append({
                "headline": entry.get("title", ""),
                "summary":  entry.get("summary", ""),
                "url":      entry.get("link", ""),
                "datetime": entry.get("published", ""),
                "source":   "Yahoo Finance",
                "ticker":   ticker,
            })
        return articles
    except Exception:
        return []

def summarize_with_claude(articles: list, watchlist: list) -> str:
    """Send articles to Claude for neutral summarization and signal scoring."""
    if not articles:
        return "No articles to summarize."
    client = anthropic.Anthropic(api_key=api_key)
    article_text = ""
    for i, a in enumerate(articles[:20], 1):
        article_text += f"\n{i}. [{a.get('ticker','MARKET')}] {a.get('headline','')}\n   Source: {a.get('source','')} | {str(a.get('datetime',''))[:16]}\n   {a.get('summary','')[:200]}\n"

    prompt = f"""You are a financial news analyst. I track these tickers: {', '.join(watchlist)}.

Here are today's news articles:
{article_text}

For each article that is relevant to my watchlist, provide:
- Ticker affected
- 2-sentence neutral summary (no hype, no clickbait)
- Signal rating: HIGH SIGNAL / LOW SIGNAL / NOISE
- Confirmed fact or speculation? (one word: CONFIRMED / SPECULATIVE / MIXED)
- Bull/Bear implication (one line)

Skip articles that are clearly irrelevant to my watchlist.
Format each as:
[TICKER] SIGNAL_LEVEL | CONFIRMED/SPECULATIVE
Summary: ...
Implication: ...

No markdown. No dollar signs."""

    try:
        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text.replace("$", "＄"), msg.usage
    except Exception as e:
        return f"Error calling Claude: {e}", None

# ── Main News Feed ─────────────────────────────────────────────────────────────
st.subheader("📡 Live News Feed")

days_back = st.slider("Look back (days)", 1, 30, 7, key="news_days")
news_source = st.radio("News source", ["Finnhub (requires API key)", "Yahoo Finance RSS (free, no key)"], horizontal=True, key="news_source")

col_fetch, col_ai = st.columns([1, 1])
with col_fetch:
    fetch_btn = st.button("🔄 Fetch Latest News", type="primary", key="btn_fetch_news")
with col_ai:
    ai_btn = st.button("🤖 AI Summarize All", type="secondary", key="btn_ai_news",
                        disabled=not api_key)

if fetch_btn or "news_articles" not in st.session_state:
    all_articles = []
    use_yahoo = "Yahoo" in news_source

    if use_yahoo:
        try:
            import feedparser
            with st.spinner("Fetching from Yahoo Finance RSS..."):
                for ticker in st.session_state["watchlist"]:
                    articles = fetch_yahoo_rss(ticker)
                    all_articles.extend(articles)
            st.session_state["news_articles"] = all_articles
        except ImportError:
            st.warning("feedparser not installed. Run: pip install feedparser")
            st.session_state["news_articles"] = []
    else:
        if not finnhub_key:
            st.warning("⚠️ No Finnhub API key. Add it above or switch to Yahoo Finance RSS.")
            st.session_state["news_articles"] = []
        else:
            with st.spinner(f"Fetching news for {len(st.session_state['watchlist'])} tickers from Finnhub..."):
                for ticker in st.session_state["watchlist"]:
                    articles = fetch_finnhub_news(ticker, finnhub_key, days_back)
                    for a in articles:
                        a["ticker"] = ticker
                    all_articles.extend(articles)
                # Also fetch general market news
                market_news = fetch_finnhub_market_news(finnhub_key)
                for a in market_news:
                    a["ticker"] = "MARKET"
                all_articles.extend(market_news)
            st.session_state["news_articles"] = all_articles

articles = st.session_state.get("news_articles", [])

if not articles:
    st.info("📭 No articles fetched yet. Click 'Fetch Latest News' above.")
else:
    st.success(f"✅ {len(articles)} articles fetched across {len(st.session_state['watchlist'])} tickers")

    # ── AI Summary ────────────────────────────────────────────────────────────
    if ai_btn and articles:
        with st.spinner("Claude is reading and summarizing the news..."):
            result = summarize_with_claude(articles, st.session_state["watchlist"])
            if isinstance(result, tuple):
                summary_text, usage = result
            else:
                summary_text, usage = result, None

        st.markdown("### 🤖 Claude's News Briefing")
        st.text(summary_text)
        if usage:
            cost = (usage.input_tokens / 1_000_000 * 3.0) + (usage.output_tokens / 1_000_000 * 15.0)
            st.caption(f"📊 ${cost:.4f} — {usage.input_tokens + usage.output_tokens:,} tokens")
        st.markdown("---")

    # ── Raw Article Feed ──────────────────────────────────────────────────────
    st.subheader("📋 Raw Articles")

    # Filter by ticker
    all_tickers_in_feed = sorted(set(a.get("ticker", "MARKET") for a in articles))
    selected_filter = st.multiselect("Filter by ticker", all_tickers_in_feed, default=all_tickers_in_feed, key="news_filter")

    filtered = [a for a in articles if a.get("ticker", "MARKET") in selected_filter]

    for article in filtered[:30]:
        ticker_tag = article.get("ticker", "MARKET")
        headline   = article.get("headline", article.get("title", "No headline"))
        source     = article.get("source", "Unknown")
        url        = article.get("url", "#")
        dt_raw     = article.get("datetime", article.get("published", ""))
        summary    = article.get("summary", "")[:200]

        # Format timestamp
        try:
            if isinstance(dt_raw, (int, float)):
                dt_str = datetime.fromtimestamp(dt_raw).strftime("%b %d, %Y %H:%M")
            else:
                dt_str = str(dt_raw)[:16]
        except Exception:
            dt_str = str(dt_raw)[:16]

        with st.container():
            col_tag, col_content = st.columns([1, 8])
            with col_tag:
                st.markdown(f"**`{ticker_tag}`**")
            with col_content:
                st.markdown(f"**[{headline}]({url})**")
                st.caption(f"{source} · {dt_str}")
                if summary:
                    st.caption(summary)
            st.markdown("---")

# ── SEC EDGAR Feed ─────────────────────────────────────────────────────────────
st.subheader("📄 SEC EDGAR Filings (Free, No Key)")
st.caption("Official 8-K and 10-Q filings — pure signal, zero noise.")

if st.button("📄 Fetch Recent SEC Filings", key="btn_sec"):
    try:
        import feedparser
        sec_articles = []
        with st.spinner("Fetching SEC EDGAR RSS..."):
            for ticker in st.session_state["watchlist"][:5]:  # limit to 5 to avoid rate limits
                # SEC EDGAR full-text search RSS
                url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt={(datetime.now()-timedelta(days=30)).strftime('%Y-%m-%d')}&enddt={datetime.now().strftime('%Y-%m-%d')}&forms=8-K,10-Q"
                try:
                    resp = requests.get(
                        f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={ticker}&type=8-K&dateb=&owner=include&count=5&search_text=&output=atom",
                        timeout=10,
                        headers={"User-Agent": "PeachStateSavings research@peachstatesavings.com"}
                    )
                    if resp.status_code == 200:
                        feed = feedparser.parse(resp.text)
                        for entry in feed.entries[:3]:
                            sec_articles.append({
                                "ticker": ticker,
                                "headline": entry.get("title", ""),
                                "url": entry.get("link", ""),
                                "datetime": entry.get("updated", ""),
                                "source": "SEC EDGAR",
                                "summary": entry.get("summary", "")[:200],
                            })
                except Exception:
                    pass

        if sec_articles:
            st.success(f"✅ {len(sec_articles)} SEC filings found")
            for a in sec_articles:
                st.markdown(f"**`{a['ticker']}`** — [{a['headline']}]({a['url']})")
                st.caption(f"SEC EDGAR · {str(a['datetime'])[:16]}")
                st.markdown("---")
        else:
            st.info("No recent SEC filings found for your watchlist tickers.")
    except ImportError:
        st.warning("feedparser not installed. Run: pip install feedparser")
