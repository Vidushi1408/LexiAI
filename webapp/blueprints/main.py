# webapp/blueprints/main.py
"""Landing page, dashboard, billing, audit log and settings/user management."""
import json

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from audit import log as audit
from auth import roles as auth_roles
from auth import users as auth_users
from config import settings
from webapp.security import audit_event, current_role, current_user, login_required, role_required
from webapp.state import get_state

bp = Blueprint("main", __name__)


@bp.route("/")
def landing():
    return render_template("landing.html")


@bp.route("/dashboard")
@login_required
def dashboard():
    state = get_state()
    words = (state.pipeline_result or {}).get("word_count", 0)

    avg_grounding, avg_grounding_label = None, None
    if state.qa_confidences:
        from rag.citations import confidence_label
        avg = sum(state.qa_confidences) / len(state.qa_confidences)
        avg_grounding, avg_grounding_label = f"{avg:.0%}", confidence_label(avg)

    # FAIL only: REVIEW means "needs a human look", not "found to violate policy" — counting it
    # as a violation would overstate how many real problems the checker actually found.
    violations = (sum(i["status"] == "FAIL" for i in state.compliance_result)
                  if state.compliance_result is not None else None)

    return render_template("dashboard.html", state=state, words=words, chunks=len(state.chunks),
                           avg_grounding=avg_grounding, avg_grounding_label=avg_grounding_label,
                           violations=violations)


@bp.route("/billing")
def billing():
    return render_template("billing.html")


@bp.route("/audit")
@role_required("admin")
def audit_log():
    ok, msg = audit.verify()
    entries = list(reversed(audit.read(limit=200)))
    for e in entries:
        e["details_json"] = json.dumps(e["details"], ensure_ascii=False)
    return render_template("audit.html", chain_ok=ok, chain_msg=msg, entries=entries)


@bp.route("/audit/export.csv")
@role_required("admin")
def audit_export():
    from flask import Response
    return Response(audit.export_csv(), mimetype="text/csv",
                     headers={"Content-Disposition": "attachment; filename=lexi_audit_log.csv"})


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings_page():
    if request.method == "POST" and request.form.get("form") == "add_user":
        if not auth_roles.is_admin(current_role()):
            abort(403)
        nu, nr, npw = request.form.get("username", ""), request.form.get("role", ""), request.form.get("password", "")
        try:
            auth_users.create_user(nu, npw, nr)
            audit_event("user_created", target=nu.strip().lower(), role=nr)
            flash(f"User {nu.strip().lower()} created.", "success")
        except ValueError as e:
            flash(str(e), "error")
        return redirect(url_for("main.settings_page"))

    if request.method == "POST" and request.form.get("form") == "api_key":
        username = current_user()["username"]
        new_key = auth_users.set_api_key(username)
        audit_event("api_key_generated", target=username)
        flash("New API key generated below — copy it now, it won't be shown again.", "success")
        return render_template("settings.html", users=auth_users.list_users(), roles=auth_users.ROLES,
                               auth_enabled=settings.auth_enabled, new_api_key=new_key)

    if request.method == "POST" and request.form.get("form") == "change_password":
        username = current_user()["username"]
        current_pw, new_pw, confirm = (request.form.get("current_password", ""),
                                       request.form.get("new_password", ""), request.form.get("confirm", ""))
        if new_pw != confirm:
            flash("New passwords do not match.", "error")
        else:
            try:
                auth_users.change_password(username, current_pw, new_pw)
                audit_event("password_changed", target=username)
                flash("Password changed.", "success")
            except ValueError as e:
                flash(str(e), "error")
        return redirect(url_for("main.settings_page"))

    if request.method == "POST" and request.form.get("form") == "reset_password":
        if not auth_roles.is_admin(current_role()):
            abort(403)
        target, new_pw = request.form.get("username", ""), request.form.get("new_password", "")
        try:
            auth_users.set_password(target.strip().lower(), new_pw)
            audit_event("password_reset", target=target.strip().lower())
            flash(f"Password reset for {target.strip().lower()}.", "success")
        except ValueError as e:
            flash(str(e), "error")
        return redirect(url_for("main.settings_page"))

    if request.method == "POST" and request.form.get("form") == "delete_user":
        if not auth_roles.is_admin(current_role()):
            abort(403)
        target = request.form.get("username", "").strip().lower()
        if target == current_user()["username"]:
            flash("You can't delete your own account.", "error")
        else:
            try:
                auth_users.delete_user(target)
                audit_event("user_deleted", target=target)
                flash(f"User {target} deleted.", "success")
            except ValueError as e:
                flash(str(e), "error")
        return redirect(url_for("main.settings_page"))

    users_list = auth_users.list_users() if auth_roles.is_admin(current_role()) else None
    return render_template("settings.html", users=users_list, roles=auth_users.ROLES,
                           auth_enabled=settings.auth_enabled, new_api_key=None)
