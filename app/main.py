"""Public-facing routes.

Flow:
  /  (GET)         -> code entry page
  /  (POST)        -> validate code, store flag in session, redirect to school
  /s/<slug>/       -> if logged in: dashboard view
                       elif session-verified for this school: gateway view
                       else: redirect back to / with a flash
"""
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, abort
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
        raw = request.form.get("code", "").strip()
        # Strip non-digits so users can paste "123-4567" or "1234 567"
        code = "".join(c for c in raw if c.isdigit())

        if len(code) != 7:
            flash("Access codes are 7 digits. Double-check and try again.", "error")
            return render_template("landing.html")

        school = School.query.filter_by(access_code=code).first()
        if not school:
            flash("That code didn't match any school. Ask your school for the right code.", "error")
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
