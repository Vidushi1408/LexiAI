# webapp/security.py
"""Login/role enforcement, CSRF tokens, and an audit-log helper bound to the current user."""
import logging
from functools import wraps

from flask import abort, flash, redirect, request, session, url_for

from audit import log as audit
from auth import roles as auth_roles
from config import settings

log = logging.getLogger("lexi.web.security")


def current_user() -> dict | None:
    return session.get("user")


def current_role() -> str:
    user = current_user()
    return user["role"] if user else "admin"  # auth disabled => full access


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if settings.auth_enabled and not current_user():
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles: str):
    """Restrict a route to the given roles (e.g. @role_required("admin"))."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_role() not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def analyst_required(view):
    """Restrict a route to roles that may upload documents and run analyses (analyst, admin) —
    a viewer can ask questions and search, but not see or run the other feature pages."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not auth_roles.can_upload(current_role()):
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def audit_event(action: str, **details) -> None:
    """Record an audit event for the signed-in user (metadata only — never document text)."""
    try:
        audit.record(action, user=(current_user() or {}).get("username", "anonymous"), **details)
    except OSError as e:
        log.warning("could not write audit log: %s", e)


def csrf_token() -> str:
    token = session.get("_csrf_token")
    if not token:
        import secrets
        token = secrets.token_hex(16)
        session["_csrf_token"] = token
    return token


def validate_csrf() -> bool:
    submitted = request.form.get("csrf_token", "")
    expected = session.get("_csrf_token", "")
    import hmac
    return bool(expected) and hmac.compare_digest(submitted, expected)


def init_app(app) -> None:
    """Reject any state-changing POST/PUT/DELETE without a valid CSRF token."""
    @app.before_request
    def _check_csrf():
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and not validate_csrf():
            log.warning("CSRF check failed for %s %s", request.method, request.path)
            flash("Your session expired or the form was resubmitted. Please try again.", "error")
            return redirect(request.referrer or url_for("main.landing"))

    app.jinja_env.globals["csrf_token"] = csrf_token
    app.jinja_env.globals["current_user"] = current_user
    app.jinja_env.globals["current_role"] = current_role
    app.jinja_env.globals["can_upload"] = lambda: auth_roles.can_upload(current_role())
    app.jinja_env.globals["is_admin"] = lambda: auth_roles.is_admin(current_role())
    app.jinja_env.globals["auth_enabled"] = settings.auth_enabled
