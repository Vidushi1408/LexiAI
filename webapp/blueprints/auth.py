# webapp/blueprints/auth.py
from flask import Blueprint, redirect, render_template, request, session, url_for

from audit import log as audit
from auth import users as auth_users
from webapp.security import audit_event
from webapp.state import drop_state

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect(url_for("main.dashboard"))

    if not auth_users.has_users():
        return redirect(url_for("auth.setup"))

    error = None
    if request.method == "POST":
        u, p = request.form.get("username", ""), request.form.get("password", "")
        user, msg = auth_users.authenticate(u, p)
        if user:
            session["user"] = user
            audit_event("login_success")
            dest = request.args.get("next") or url_for("main.dashboard")
            return redirect(dest)
        # log a fingerprint, not the typed text — people sometimes paste a password into the username box
        audit.record("login_failed", user="anonymous", attempted=audit.fingerprint(u.strip().lower()))
        error = msg
    return render_template("login.html", error=error)


@bp.route("/setup", methods=["GET", "POST"])
def setup():
    if auth_users.has_users():
        return redirect(url_for("auth.login"))

    error = None
    if request.method == "POST":
        u, p1, p2 = request.form.get("username", ""), request.form.get("password", ""), request.form.get("confirm", "")
        if p1 != p2:
            error = "Passwords do not match."
        else:
            try:
                auth_users.create_user(u, p1, "admin")
                session["user"] = {"username": u.strip().lower(), "role": "admin"}
                audit_event("user_created", target=u.strip().lower(), role="admin", first_run=True)
                audit_event("login_success")
                return redirect(url_for("main.dashboard"))
            except ValueError as e:
                error = str(e)
    return render_template("setup.html", error=error)


@bp.route("/logout", methods=["POST"])
def logout():
    audit_event("logout")
    drop_state()
    session.clear()
    return redirect(url_for("auth.login"))
