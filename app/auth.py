"""Auth blueprint: alum signup/login, admin login, logout.

Signup is gated on the visitor having entered the school's access code on /.
The verification is stored in the Flask session under SCHOOL_ACCESS_KEY.

Login (alum or admin) does NOT require the access code — the email + password
is sufficient, since existing accounts were already vetted.

Logout clears the verification, so the next visit starts at code entry again.
"""
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort, session
)
from flask_login import login_user, logout_user, login_required, current_user
from . import db
from .models import School, User
from .main import SCHOOL_ACCESS_KEY

bp = Blueprint("auth", __name__)


def _get_school(slug):
    school = School.query.filter_by(slug=slug).first()
    if not school:
        abort(404)
    return school


def _has_verified_code_for(school):
    return session.get(SCHOOL_ACCESS_KEY) == school.id


# ---------------- Alum signup ----------------

@bp.route("/<school_slug>/signup", methods=["GET", "POST"])
def alum_signup(school_slug):
    school = _get_school(school_slug)

    if not _has_verified_code_for(school):
        flash("Enter your school's access code first.", "error")
        return redirect(url_for("main.landing"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        first = request.form.get("first_name", "").strip()
        last = request.form.get("last_name", "").strip()
        grad_year = request.form.get("grad_year", "").strip()

        if not (email and password and first and last and grad_year.isdigit()):
            flash("Please fill in every field, including your graduation year.", "error")
            return render_template("auth/alum_signup.html", school=school)

        existing = User.query.filter_by(school_id=school.id, email=email).first()
        if existing:
            flash("An account with that email already exists for this school.", "error")
            return render_template("auth/alum_signup.html", school=school)

        user = User(
            school_id=school.id,
            email=email,
            first_name=first,
            last_name=last,
            grad_year=int(grad_year),
            current_role=request.form.get("current_role", "").strip() or None,
            current_company=request.form.get("current_company", "").strip() or None,
            location=request.form.get("location", "").strip() or None,
            is_admin=False,        # alums are never admins via signup
            is_verified=False,     # the school admin has to approve them
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        # Do NOT log them in yet — their account is pending the school's review.
        return render_template("auth/pending.html", school=school, just_signed_up=True)

    return render_template("auth/alum_signup.html", school=school)


# ---------------- Alum login ----------------

@bp.route("/<school_slug>/login", methods=["GET", "POST"])
def alum_login(school_slug):
    school = _get_school(school_slug)
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(school_id=school.id, email=email).first()
        if user and not user.is_admin and user.check_password(password):
            if not user.is_verified:
                # Credentials are correct but the school hasn't approved them yet.
                return render_template(
                    "auth/pending.html", school=school, just_signed_up=False
                )
            login_user(user)
            return redirect(url_for("main.school_home", school_slug=school.slug))
        flash("Wrong email or password.", "error")
    return render_template("auth/alum_login.html", school=school)


# ---------------- Admin login ----------------

@bp.route("/<school_slug>/admin/login", methods=["GET", "POST"])
def admin_login(school_slug):
    school = _get_school(school_slug)
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(school_id=school.id, email=email).first()
        if user and user.is_admin and user.check_password(password):
            login_user(user)
            return redirect(url_for("admin.dashboard", school_slug=school.slug))
        flash("Invalid admin credentials.", "error")
    return render_template("auth/admin_login.html", school=school)


# ---------------- Logout ----------------

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    # Clear the school-access flag so they're sent back to code entry.
    session.pop(SCHOOL_ACCESS_KEY, None)
    return redirect(url_for("main.landing"))
