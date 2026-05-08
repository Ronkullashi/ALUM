"""Public-facing routes.

Flow:
  /  (GET)         -> code entry page
  /  (POST)        -> validate code, store flag in session, redirect to school
  /s/<slug>/       -> if logged in: dashboard view
                       elif session-verified for this school: gateway view
                       else: redirect back to / with a flash
  /_debug/schools  -> private list of all schools + codes (gated by ?key=)
"""
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, abort,
    Response,
)
from flask_login import current_user
from .models import School, Announcement, User, Group

bp = Blueprint("main", __name__)


SCHOOL_ACCESS_KEY = "verified_school_id"  # session key


# ----- helpers -----

def _has_school_access(school):
    """True if the visitor either logged in to this school OR has entered the code."""
    if current_user.is_authenticated and current_user.school_id == school.id:
        return True
    return session.get(SCHOOL_ACCESS_KEY) == school.id


# ----- routes -----

@bp.route("/", methods=["GET", "POST"])
def landing():
    # If already logged in, fast-forward to the user's school.
    if current_user.is_authenticated:
        return redirect(url_for("main.school_home", school_slug=current_user.school.slug))

    if request.method == "POST":
        raw = request.form.get("code", "")
        # Strip non-digits so users can paste "123-4567" or "1234 567"
        code = "".join(c for c in raw if c.isdigit())

        if len(code) != 7:
            flash(
                f"Access codes are 7 digits. We received '{code}' "
                f"({len(code)} digit{'' if len(code) == 1 else 's'}).",
                "error",
            )
            return render_template("landing.html")

        school = School.query.filter_by(access_code=code).first()
        if not school:
            total = School.query.count()
            flash(
                f"Code '{code}' didn't match any of the {total} schools in "
                f"the database. View the current list at "
                f"/_debug/schools?key=alum-debug — those are the only codes "
                f"that work right now.",
                "error",
            )
            return render_template("landing.html")

        # Mark the visitor as verified for this school for the rest of their session.
        session[SCHOOL_ACCESS_KEY] = school.id
        return redirect(url_for("main.school_home", school_slug=school.slug))

    return render_template("landing.html")


@bp.route("/s/<school_slug>/")
def school_home(school_slug):
    school = School.query.filter_by(slug=school_slug).first_or_404()

    if not _has_school_access(school):
        flash("Enter your school's access code to continue.", "error")
        return redirect(url_for("main.landing"))

    # Logged-out, code-verified visitor sees the gateway.
    # Logged-in member sees the dashboard.
    if current_user.is_authenticated:
        announcements = (
            Announcement.query.filter_by(school_id=school.id)
            .order_by(Announcement.sent_at.desc())
            .limit(5)
            .all()
        )
        alum_count = User.query.filter_by(school_id=school.id, is_admin=False).count()
        group_count = Group.query.filter_by(school_id=school.id).count()
        return render_template(
            "school_home.html",
            school=school,
            view="dashboard",
            announcements=announcements,
            alum_count=alum_count,
            group_count=group_count,
        )

    return render_template("school_home.html", school=school, view="gateway")


@bp.route("/about")
def about():
    """Public About page — accessible without logging in or entering a code."""
    return render_template("about.html")


# ---------------------------------------------------------------------------
# Temporary debug route — lists every school + code straight from the DB.
# Gated by ?key=alum-debug. Remove this before opening the site to alumni.
# ---------------------------------------------------------------------------

@bp.route("/_debug/schools")
def debug_schools():
    if request.args.get("key") != "alum-debug":
        abort(404)
    schools = School.query.order_by(School.name).all()
    rows = []
    for s in schools:
        admin = User.query.filter_by(school_id=s.id, is_admin=True).first()
        admin_email = admin.email if admin else "(no admin)"
        rows.append((s.name, s.slug, s.access_code, admin_email))

    html = ["<!doctype html><meta charset=utf-8>",
            "<title>Alum debug · school codes</title>",
            "<style>",
            "body{font:14px/1.5 -apple-system,system-ui,sans-serif;",
            "background:#faf7f2;color:#1a1611;padding:24px;max-width:900px;margin:0 auto}",
            "h1{font-size:1.4rem}",
            "table{border-collapse:collapse;width:100%;background:#fff;",
            "border:1px solid #ece5d6;border-radius:8px;overflow:hidden}",
            "th,td{text-align:left;padding:10px 12px;border-bottom:1px solid #ece5d6}",
            "th{background:#f5f1e9;font-size:12px;text-transform:uppercase;",
            "letter-spacing:.06em;color:#6e6557}",
            "code{background:#fde8e0;padding:2px 6px;border-radius:4px;",
            "font-family:'SF Mono',Menlo,monospace;font-weight:600;color:#9a3a1f}",
            ".small{color:#6e6557;font-size:12.5px}",
            "</style>",
            f"<h1>Alum — schools in database ({len(rows)})</h1>",
            "<p class=small>This page reads directly from Postgres. ",
            "Whatever shows here is what the code-entry form will accept. ",
            "Remove this route before launch.</p>",
            "<table><thead><tr><th>School</th><th>Slug</th>",
            "<th>Access code</th><th>Admin email</th></tr></thead><tbody>"]
    for name, slug, code, admin_email in rows:
        html.append(
            f"<tr><td>{name}</td><td class=small>{slug}</td>"
            f"<td><code>{code}</code></td>"
            f"<td class=small>{admin_email}</td></tr>"
        )
    if not rows:
        html.append('<tr><td colspan="4" class=small>'
                    'No schools in the database. The seed never ran successfully.'
                    '</td></tr>')
    html.append("</tbody></table>")
    return Response("".join(html), mimetype="text/html")
