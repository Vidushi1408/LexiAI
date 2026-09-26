# tests/test_billing.py
"""Unit tests for billing/subscription.py and billing/plans.py — the DB-backed plan/seat-limit
logic behind /billing and the add_user seat gate (see webapp/blueprints/main.py). Stripe itself
is never called here; billing/stripe_client.py is exercised (mocked) from tests/test_webapp.py
instead, at the route level."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import db
from auth import users
from billing import subscription
from billing.plans import PLANS, is_purchasable, seat_limit


@pytest.fixture
def db_session():
    """An isolated in-memory SQLite session per test — same tables as production Postgres."""
    db.reset_engine_for_tests()
    s = db.new_session()
    yield s
    s.close()


def test_get_subscription_creates_a_free_row_on_first_access(db_session):
    sub = subscription.get_subscription(session=db_session)
    assert sub == {"plan": "free", "status": "active", "stripe_customer_id": None,
                   "stripe_subscription_id": None, "current_period_end": None}


def test_set_plan_updates_the_singleton_row(db_session):
    subscription.set_plan("pro", status="active", stripe_customer_id="cus_123",
                          stripe_subscription_id="sub_456", session=db_session)
    sub = subscription.get_subscription(session=db_session)
    assert sub["plan"] == "pro"
    assert sub["stripe_customer_id"] == "cus_123"
    assert sub["stripe_subscription_id"] == "sub_456"


def test_set_plan_rejects_an_unknown_plan(db_session):
    with pytest.raises(ValueError):
        subscription.set_plan("ultra-deluxe", session=db_session)


def test_seats_used_counts_all_users(db_session):
    users.create_user("admin1", "a-long-password", "admin", session=db_session)
    users.create_user("viewer1", "a-long-password", "viewer", session=db_session)
    assert subscription.seats_used(session=db_session) == 2


def test_can_add_user_respects_the_free_plan_seat_limit(db_session):
    assert seat_limit("free") == 3
    for i in range(3):
        users.create_user(f"user{i}", "a-long-password", "viewer", session=db_session)
    assert subscription.seats_used(session=db_session) == 3
    assert subscription.can_add_user(session=db_session) is False


def test_can_add_user_true_under_the_limit(db_session):
    users.create_user("user0", "a-long-password", "viewer", session=db_session)
    assert subscription.can_add_user(session=db_session) is True


def test_enterprise_plan_has_no_seat_limit(db_session):
    subscription.set_plan("enterprise", session=db_session)
    assert seat_limit("enterprise") is None
    for i in range(50):
        users.create_user(f"user{i}", "a-long-password", "viewer", session=db_session)
    assert subscription.can_add_user(session=db_session) is True


def test_is_purchasable_false_for_free_plan():
    assert is_purchasable("free") is False


def test_is_purchasable_false_without_a_configured_price_id(monkeypatch):
    monkeypatch.setitem(PLANS["pro"], "price_id", None)
    assert is_purchasable("pro") is False


def test_is_purchasable_true_with_a_configured_price_id(monkeypatch):
    monkeypatch.setitem(PLANS["pro"], "price_id", "price_test123")
    assert is_purchasable("pro") is True
