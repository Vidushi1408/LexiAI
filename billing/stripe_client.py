# billing/stripe_client.py
"""Thin wrapper around the Stripe SDK — Checkout for buying/upgrading a plan, the Billing Portal
for self-service management (cancel, change payment method), and webhook handling to keep
billing.subscription in sync with what Stripe actually charged. Every Stripe SDK import here is
local to a function, not at module level, so importing this module (or the routes that use it)
never requires the `stripe` package to be installed unless a Stripe call is actually made — the
rest of the app, and most of the test suite, don't need it."""
import datetime as dt
import logging

from config import settings

log = logging.getLogger("lexi.billing.stripe")


def _client():
    import stripe
    stripe.api_key = settings.stripe_secret_key
    return stripe


def create_checkout_session(plan: str, success_url: str, cancel_url: str) -> str:
    """Returns the Checkout Session URL to redirect the browser to."""
    from billing.plans import PLANS
    from billing.subscription import get_subscription

    stripe = _client()
    price_id = PLANS[plan]["price_id"]
    existing_customer = get_subscription()["stripe_customer_id"]

    kwargs = dict(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"plan": plan},
        subscription_data={"metadata": {"plan": plan}},
    )
    if existing_customer:
        kwargs["customer"] = existing_customer
    else:
        kwargs["customer_creation"] = "always"

    session = stripe.checkout.Session.create(**kwargs)
    return session.url


def create_portal_session(return_url: str) -> str:
    """Returns the Billing Portal URL. Raises ValueError if there's no Stripe customer yet —
    the caller should only offer this once a checkout has completed."""
    from billing.subscription import get_subscription

    customer_id = get_subscription()["stripe_customer_id"]
    if not customer_id:
        raise ValueError("No billing account yet — subscribe to a plan first.")

    stripe = _client()
    session = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
    return session.url


def handle_webhook_event(payload: bytes, sig_header: str) -> None:
    """Verifies the signature, then updates billing.subscription for the events we care about.
    Raises on a bad signature or unparseable payload — the route turns that into a 400."""
    import stripe
    from billing.subscription import set_plan, set_stripe_customer_id

    event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    obj = event["data"]["object"]
    event_type = event["type"]

    if event_type == "checkout.session.completed":
        plan = (obj.get("metadata") or {}).get("plan", "pro")
        customer_id = obj.get("customer")
        if customer_id:
            set_stripe_customer_id(customer_id)
        set_plan(plan, status="active", stripe_customer_id=customer_id,
                 stripe_subscription_id=obj.get("subscription"))
        log.info("Stripe checkout completed: plan=%s customer=%s", plan, customer_id)

    elif event_type == "customer.subscription.updated":
        plan = (obj.get("metadata") or {}).get("plan")
        status = obj.get("status", "active")
        period_end = obj.get("current_period_end")
        set_plan(plan or _current_plan_fallback(), status=status, stripe_subscription_id=obj.get("id"),
                 current_period_end=dt.datetime.utcfromtimestamp(period_end) if period_end else None)
        log.info("Stripe subscription updated: status=%s", status)

    elif event_type == "customer.subscription.deleted":
        set_plan("free", status="canceled")
        log.info("Stripe subscription canceled — reverted to Free plan")

    else:
        log.info("Unhandled Stripe webhook event: %s", event_type)


def _current_plan_fallback() -> str:
    """customer.subscription.updated should carry the plan in its metadata (we set it at
    checkout), but fall back to whatever's already stored rather than guessing if it's ever
    missing — e.g. a subscription edited directly in the Stripe dashboard."""
    from billing.subscription import get_subscription
    return get_subscription()["plan"]
