"""Unit tests for page 70 — SoleOps Stripe Subscription Paywall."""
import os

ROOT      = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGE_PATH = os.path.join(ROOT, "pages/70_soleops_stripe_paywall.py")


def _source() -> str:
    with open(PAGE_PATH) as f:
        return f.read()


def test_page_file_exists_and_syntax():
    """Page file exists on disk and compiles without syntax errors."""
    assert os.path.exists(PAGE_PATH), f"Missing: {PAGE_PATH}"
    src = _source()
    assert len(src) > 500, "Page file is suspiciously short (<500 chars)"
    compile(src, PAGE_PATH, "exec")


def test_required_patterns():
    """SoleOps Stripe Paywall follows peachstatesavings.com coding standards."""
    src = _source()
    assert "def _ensure_tables" in src,       "Missing _ensure_tables() function"
    assert "get_conn"           in src,       "Missing get_conn import/usage"
    assert "require_login"      in src,       "Missing require_login"
    assert "render_sidebar_brand" in src,     "Missing render_sidebar_brand"
    assert "USE_POSTGRES"       in src,       "Missing USE_POSTGRES flag"
    assert "init_db"            in src,       "Missing init_db()"
    assert "inject_css"         in src,       "Missing inject_css()"
    assert "conn.close()"       in src,       "Missing conn.close() — potential connection leak"


def test_db_table_names():
    """Required subscription DB tables are referenced in source."""
    src = _source()
    assert "soleops_subscriptions" in src, "Missing soleops_subscriptions table"
    assert "soleops_users"         in src, "Missing soleops_users table"


def test_no_hardcoded_stripe_keys():
    """No hardcoded Stripe keys — must use get_setting()."""
    src = _source()
    assert "sk_live_" not in src,  "Hardcoded live Stripe key found!"
    assert "sk_test_" not in src,  "Hardcoded test Stripe key found!"
    assert "stripe_secret_key" in src, "Missing get_setting('stripe_secret_key')"


def test_plan_tiers():
    """All 4 SoleOps subscription tiers are defined."""
    src = _source()
    assert "Free"    in src
    assert "Starter" in src
    assert "9.99"    in src, "Missing Starter price $9.99"
    assert "19.99"   in src, "Missing Pro price $19.99"
    assert "29.99"   in src, "Missing Pro+ price $29.99"


def test_stripe_checkout():
    """Stripe checkout session creation is implemented."""
    src = _source()
    assert "checkout.Session" in src or "stripe.checkout" in src.lower(), \
        "Missing Stripe checkout session creation"
    assert "mode" in src and "subscription" in src, \
        "Missing subscription mode in Stripe checkout"


def test_stripe_guard():
    """Stripe calls are guarded against missing API key."""
    src = _source()
    assert "stripe_key" in src or "stripe_secret_key" in src
    assert "if not stripe_key" in src or "stripe_configured" in src, \
        "Missing Stripe key null-check"


def test_sidebar_links():
    """All required sidebar page_link calls are present."""
    src = _source()
    assert 'page_link("app.py"'                         in src
    assert 'page_link("pages/22_todo.py"'               in src
    assert 'page_link("pages/24_creator_companion.py"'  in src
    assert 'page_link("pages/25_notes.py"'              in src
    assert 'page_link("pages/26_media_library.py"'      in src
    assert 'page_link("pages/17_personal_assistant.py"' in src


def test_tabs_present():
    """Required subscription management tabs are defined."""
    src = _source()
    assert "My Plan"   in src or "Plan"    in src
    assert "Pricing"   in src or "pricing" in src.lower()
    assert "Billing"   in src or "billing" in src.lower()
    assert "Settings"  in src or "Account" in src
    assert "Admin"     in src


def test_welcome_email():
    """Welcome email function is implemented with graceful fallback."""
    src = _source()
    assert "_send_welcome_email" in src or "welcome" in src.lower(), \
        "Missing welcome email function"
    assert "smtp" in src.lower() or "gmail" in src.lower(), \
        "Missing SMTP/Gmail email sending"


def test_cancel_subscription():
    """Subscription cancellation is implemented."""
    src = _source()
    assert "cancel" in src.lower(), "Missing cancellation logic"
    assert "cancel_at_period_end" in src, "Missing cancel_at_period_end flag"


def test_create_table_statements():
    """CREATE TABLE IF NOT EXISTS statements exist."""
    src = _source()
    assert "CREATE TABLE IF NOT EXISTS soleops_subscriptions" in src
    assert "CREATE TABLE IF NOT EXISTS soleops_users"         in src
