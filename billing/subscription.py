# billing/subscription.py
"""The single Subscription row (id=1) that holds this deployment's plan and Stripe state —
see db.py's Subscription model for why this is per-deployment, not per-user."""
import datetime as dt

from sqlalchemy.orm import Session

from billing.plans import PLANS, seat_limit
from db import Subscription, User, new_session

_SINGLETON_ID = 1


def _session(session: Session | None):
    return (session, False) if session is not None else (new_session(), True)


def get_subscription(session: Session | None = None) -> dict:
    """Always returns a dict, creating the Free-plan row on first access."""
    s, owns = _session(session)
    try:
        row = s.get(Subscription, _SINGLETON_ID)
        if row is None:
            row = Subscription(id=_SINGLETON_ID, plan="free", status="active")
            s.add(row)
            s.commit()
        return _row_to_dict(row)
    finally:
        if owns:
            s.close()


def _row_to_dict(row: Subscription) -> dict:
    return {
        "plan": row.plan,
        "status": row.status,
        "stripe_customer_id": row.stripe_customer_id,
        "stripe_subscription_id": row.stripe_subscription_id,
        "current_period_end": row.current_period_end,
    }


def set_plan(plan: str, status: str = "active", stripe_customer_id: str | None = None,
             stripe_subscription_id: str | None = None,
             current_period_end: dt.datetime | None = None, session: Session | None = None) -> None:
    if plan not in PLANS:
        raise ValueError(f"Unknown plan: {plan}")
    s, owns = _session(session)
    try:
        row = s.get(Subscription, _SINGLETON_ID)
        if row is None:
            row = Subscription(id=_SINGLETON_ID)
            s.add(row)
        row.plan = plan
        row.status = status
        if stripe_customer_id is not None:
            row.stripe_customer_id = stripe_customer_id
        if stripe_subscription_id is not None:
            row.stripe_subscription_id = stripe_subscription_id
        if current_period_end is not None:
            row.current_period_end = current_period_end
        s.commit()
    finally:
        if owns:
            s.close()


def set_stripe_customer_id(customer_id: str, session: Session | None = None) -> None:
    """Records a Customer before checkout completes, so a later webhook (or a retried checkout)
    can find the same Customer instead of creating a duplicate."""
    s, owns = _session(session)
    try:
        row = s.get(Subscription, _SINGLETON_ID)
        if row is None:
            row = Subscription(id=_SINGLETON_ID, plan="free", status="active")
            s.add(row)
        row.stripe_customer_id = customer_id
        s.commit()
    finally:
        if owns:
            s.close()


def seats_used(session: Session | None = None) -> int:
    s, owns = _session(session)
    try:
        return s.query(User).count()
    finally:
        if owns:
            s.close()


def can_add_user(session: Session | None = None) -> bool:
    """False once the current plan's seat limit is reached. Unlimited plans always return True."""
    s, owns = _session(session)
    try:
        limit = seat_limit(get_subscription(session=s)["plan"])
        return limit is None or seats_used(session=s) < limit
    finally:
        if owns:
            s.close()
