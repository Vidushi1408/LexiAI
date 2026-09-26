# billing/plans.py
"""Static plan definitions — the source of truth for pricing, seat limits, and which Stripe
Price ID a paid plan maps to. Adding a plan means adding an entry here and a matching Stripe
Price; nothing else needs to change."""
from config import settings

PLANS = {
    "free": {
        "name": "Free",
        "seat_limit": 3,
        "price_id": None,
        "price_display": "$0",
        "features": ["Up to 3 users", "Core document analysis", "Community support"],
    },
    "pro": {
        "name": "Pro",
        "seat_limit": 20,
        "price_id": settings.stripe_price_pro or None,
        "price_display": "$49/mo",
        "features": ["Up to 20 users", "All analysis features", "API access", "Email support"],
    },
    "enterprise": {
        "name": "Enterprise",
        "seat_limit": None,   # unlimited
        "price_id": settings.stripe_price_enterprise or None,
        "price_display": "Contact us",
        "features": ["Unlimited users", "All analysis features", "API access", "Dedicated support & SLA"],
    },
}

PLAN_ORDER = ["free", "pro", "enterprise"]


def seat_limit(plan: str) -> int | None:
    """None means unlimited."""
    return PLANS.get(plan, PLANS["free"])["seat_limit"]


def is_purchasable(plan: str) -> bool:
    """False for Free (nothing to check out) and for a paid plan with no Price ID configured."""
    return plan in PLANS and plan != "free" and PLANS[plan]["price_id"] is not None
