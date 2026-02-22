"""
Stripe integration utilities for 404 Finance.

Environment variables required:
  STRIPE_SECRET_KEY        — sk_live_... or sk_test_...
  STRIPE_PRICE_ID          — price_... (the $9-12/month recurring price)
  STRIPE_WEBHOOK_SECRET    — whsec_... (from Stripe dashboard → Webhooks)
  APP_URL                  — https://your-app.railway.app (no trailing slash)
"""

import os
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

STRIPE_SECRET_KEY     = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_ID       = os.environ.get("STRIPE_PRICE_ID", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
APP_URL               = os.environ.get("APP_URL", "http://localhost:8501")

STRIPE_ENABLED = bool(STRIPE_SECRET_KEY)


def get_stripe():
    """Return the stripe module, or None if not configured."""
    if not STRIPE_ENABLED:
        return None
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        return stripe
    except ImportError:
        return None


def create_checkout_session(user_email: str, user_id: int) -> str | None:
    """
    Create a Stripe Checkout session for the Pro plan.
    Returns the checkout URL, or None on failure.
    """
    stripe = get_stripe()
    if not stripe or not STRIPE_PRICE_ID:
        return None

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            customer_email=user_email,
            client_reference_id=str(user_id),
            success_url=f"{APP_URL}/?checkout=success",
            cancel_url=f"{APP_URL}/0_pricing?checkout=cancelled",
            metadata={"user_id": str(user_id)},
        )
        return session.url
    except Exception as e:
        st.error(f"Stripe error: {e}")
        return None


def create_billing_portal_session(stripe_customer_id: str) -> str | None:
    """
    Create a Stripe Customer Portal session so users can manage/cancel.
    Returns the portal URL, or None on failure.
    """
    stripe = get_stripe()
    if not stripe or not stripe_customer_id:
        return None

    try:
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=f"{APP_URL}/",
        )
        return session.url
    except Exception as e:
        st.error(f"Stripe portal error: {e}")
        return None


def verify_webhook(payload: bytes, sig_header: str) -> dict | None:
    """
    Verify a Stripe webhook signature and return the event dict.
    Returns None if verification fails.
    """
    stripe = get_stripe()
    if not stripe or not STRIPE_WEBHOOK_SECRET:
        return None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        return event
    except Exception:
        return None


def get_subscription_status(stripe_customer_id: str) -> str:
    """
    Live-check a customer's subscription status from Stripe.
    Returns: 'active', 'trialing', 'past_due', 'canceled', or 'none'
    """
    stripe = get_stripe()
    if not stripe or not stripe_customer_id:
        return "none"

    try:
        subs = stripe.Subscription.list(customer=stripe_customer_id, limit=1)
        if not subs.data:
            return "none"
        return subs.data[0].status  # active | trialing | past_due | canceled | etc.
    except Exception:
        return "none"
