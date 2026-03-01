"""
Stripe integration utilities for Peach State Savings.

Environment variables required:
  STRIPE_SECRET_KEY        — sk_live_... (production)
  STRIPE_PRICE_ID          — price_...   (live $4.99/month recurring price)
  STRIPE_WEBHOOK_SECRET    — whsec_...   (from Stripe dashboard → Webhooks)
  APP_URL                  — https://peachstatesavings.com (no trailing slash)

Optional — sandbox/test mode (used automatically for TEST_MODE_EMAILS):
  STRIPE_TEST_SECRET_KEY   — sk_test_...
  STRIPE_TEST_PRICE_ID     — price_...   (test $4.99/month recurring price)
"""

import os
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Live keys ─────────────────────────────────────────────────────────────────
STRIPE_SECRET_KEY     = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_ID       = os.environ.get("STRIPE_PRICE_ID", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
APP_URL               = os.environ.get("APP_URL", "http://localhost:8501")

# ── Test/sandbox keys ─────────────────────────────────────────────────────────
STRIPE_TEST_SECRET_KEY = os.environ.get("STRIPE_TEST_SECRET_KEY", "")
STRIPE_TEST_PRICE_ID   = os.environ.get("STRIPE_TEST_PRICE_ID", "")

# ── Accounts that always use Stripe test/sandbox mode ─────────────────────────
# These users will be routed to test keys so real cards are never charged.
_SANDBOX_EMAILS = {
    "dbelcher003@gmail.com",
}

STRIPE_ENABLED      = bool(STRIPE_SECRET_KEY or STRIPE_TEST_SECRET_KEY)
STRIPE_LIVE_ENABLED = bool(STRIPE_SECRET_KEY and STRIPE_PRICE_ID)
STRIPE_TEST_ENABLED = bool(STRIPE_TEST_SECRET_KEY and STRIPE_TEST_PRICE_ID)


def stripe_enabled_for(user_email: str) -> bool:
    """Return True if Stripe is configured for this specific user."""
    if _is_sandbox(user_email):
        return STRIPE_TEST_ENABLED
    return STRIPE_LIVE_ENABLED


def _is_sandbox(user_email: str) -> bool:
    """Return True if this account should use Stripe test mode."""
    return (user_email or "").strip().lower() in _SANDBOX_EMAILS


def _get_keys(user_email: str) -> tuple[str, str]:
    """
    Return (secret_key, price_id) for the given user.
    Sandbox accounts use test keys; everyone else uses live keys.

    SAFETY: Never mix test keys with live prices or vice versa.
    If a sandbox user is missing STRIPE_TEST_PRICE_ID, return ("", "")
    so the caller shows a config error instead of hitting Stripe with
    mismatched key/price pairs.
    """
    if _is_sandbox(user_email):
        # Sandbox path — both test key AND test price must be present
        if STRIPE_TEST_SECRET_KEY and STRIPE_TEST_PRICE_ID:
            return STRIPE_TEST_SECRET_KEY, STRIPE_TEST_PRICE_ID
        # Missing test price — refuse to fall back to live price with test key
        return "", ""
    return STRIPE_SECRET_KEY, STRIPE_PRICE_ID


def get_stripe(user_email: str = ""):
    """Return the stripe module configured for the correct key, or None if not configured."""
    secret_key, _ = _get_keys(user_email)
    if not secret_key:
        return None
    try:
        import stripe
        stripe.api_key = secret_key
        return stripe
    except ImportError:
        return None


def create_checkout_session(user_email: str, user_id: int) -> str | None:
    """
    Create a Stripe Checkout session for the Pro plan.
    Sandbox accounts (dbelcher003@gmail.com) automatically use test keys.
    Returns the checkout URL, or None on failure.
    """
    secret_key, price_id = _get_keys(user_email)
    if not secret_key or not price_id:
        # Give a clear config error rather than silently returning None
        if _is_sandbox(user_email):
            st.error(
                "⚙️ Sandbox config incomplete — `STRIPE_TEST_PRICE_ID` is not set. "
                "Add it to your `.env` on CT100 and restart the app."
            )
        return None

    try:
        import stripe
        stripe.api_key = secret_key

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            customer_email=user_email,
            client_reference_id=str(user_id),
            # {CHECKOUT_SESSION_ID} is a Stripe template variable — filled in by Stripe
            success_url=f"{APP_URL}/?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{APP_URL}/?checkout=cancelled",
            metadata={"user_id": str(user_id)},
        )
        return session.url
    except Exception as e:
        st.error(f"Stripe error: {e}")
        return None


def create_billing_portal_session(stripe_customer_id: str, user_email: str = "") -> str | None:
    """
    Create a Stripe Customer Portal session so users can manage/cancel.
    Returns the portal URL, or None on failure.
    """
    secret_key, _ = _get_keys(user_email)
    if not secret_key or not stripe_customer_id:
        return None

    try:
        import stripe
        stripe.api_key = secret_key

        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=f"{APP_URL}/",
        )
        return session.url
    except Exception as e:
        st.error(f"Stripe portal error: {e}")
        return None


def verify_webhook(payload: bytes, sig_header: str, user_email: str = "") -> dict | None:
    """
    Verify a Stripe webhook signature and return the event dict.
    Returns None if verification fails.
    """
    secret_key, _ = _get_keys(user_email)
    if not secret_key or not STRIPE_WEBHOOK_SECRET:
        return None

    try:
        import stripe
        stripe.api_key = secret_key

        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        return event
    except Exception:
        return None


def get_subscription_status(stripe_customer_id: str, user_email: str = "") -> str:
    """
    Live-check a customer's subscription status from Stripe.
    Returns: 'active', 'trialing', 'past_due', 'canceled', or 'none'
    """
    secret_key, _ = _get_keys(user_email)
    if not secret_key or not stripe_customer_id:
        return "none"

    try:
        import stripe
        stripe.api_key = secret_key

        subs = stripe.Subscription.list(customer=stripe_customer_id, limit=1)
        if not subs.data:
            return "none"
        return subs.data[0].status
    except Exception:
        return "none"


def poll_checkout_and_activate(session_id: str, user_id: int, user_email: str) -> bool:
    """
    Poll a Stripe Checkout Session by ID and, if payment is complete,
    immediately update the user's DB record to Pro.

    Returns True if the user was successfully upgraded to Pro, False otherwise.

    This is the "polling" approach — no webhook server required.
    Call this when Stripe redirects back with ?checkout=success&session_id=<id>.
    """
    secret_key, _ = _get_keys(user_email)
    if not secret_key or not session_id:
        return False

    try:
        import stripe
        stripe.api_key = secret_key

        # Retrieve the checkout session with subscription expanded
        session = stripe.checkout.Session.retrieve(
            session_id,
            expand=["subscription", "customer"],
        )

        # Only activate if payment is confirmed
        if session.payment_status not in ("paid", "no_payment_required"):
            return False

        # Extract IDs from the session
        customer = session.customer
        customer_id = customer.id if hasattr(customer, "id") else str(customer)

        subscription = session.subscription
        if subscription is None:
            return False

        sub_id     = subscription.id if hasattr(subscription, "id") else str(subscription)
        sub_status = subscription.status if hasattr(subscription, "status") else "active"

        # Write Pro status to the database immediately
        from utils.db import update_user_subscription
        update_user_subscription(
            user_id=user_id,
            plan="pro",
            stripe_customer_id=customer_id,
            stripe_subscription_id=sub_id,
            subscription_status=sub_status,
        )
        return True

    except Exception as e:
        # Log but don't crash — caller will handle the False return
        try:
            import streamlit as st
            st.warning(f"Stripe poll error (non-fatal): {e}")
        except Exception:
            pass
        return False


def get_latest_checkout_session_for_user(user_email: str, user_id: int) -> str | None:
    """
    Look up the most recent completed Checkout Session for this user by
    client_reference_id (which we set to user_id at session creation).

    Useful as a fallback when the session_id query param is missing.
    Returns the session ID string, or None.
    """
    secret_key, _ = _get_keys(user_email)
    if not secret_key:
        return None

    try:
        import stripe
        stripe.api_key = secret_key

        sessions = stripe.checkout.Session.list(limit=5)
        for s in sessions.data:
            if (
                str(s.get("client_reference_id", "")) == str(user_id)
                and s.payment_status in ("paid", "no_payment_required")
            ):
                return s.id
        return None
    except Exception:
        return None


def is_sandbox_mode(user_email: str) -> bool:
    """Public helper — returns True if this user is in Stripe sandbox/test mode."""
    return _is_sandbox(user_email) and bool(STRIPE_TEST_SECRET_KEY)
