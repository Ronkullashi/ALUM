"""Auth blueprint: alum signup/login, admin login, logout.

Login is scoped per-school. The route is /auth/<school_slug>/login so a user
authenticates into a specific school's network. (Two people at different
schools can share an email.)
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_user, logout_user, login_required, current_user
from . import db
from .models import School, User

bp = Blueprint("auth", __name__)


def _get_school(slug):
    school = School.query.filter_by(slug=slug).first()
    if not school:
        abort(404)
    return school


@bp.route("/login")
def alum_login_pick_school():
    """If the user hits /auth/login without a school, send them to the landing."""
    return redirect(url_for("main.landing"))


# ---------------- Alum signup ----------------

@bp.route("/<school_slug>/signup", methods=["GET", "POST"])
def alum_signup(school_slug):
    school = _get_school(school_slug)
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        first = request.form.get("first_name", "").strip()
        last = request.form.get("last_name", "").strip()
        grad_year = request.form.get("grad_year", "").strip()

        if not (email and password and first and last):
            flash("Please fill in all required fields.", "error")
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
            grad_year=int(grad_year) if grad_year.isdigit() else None,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Welcome to Alum.", "success")
        return redirect(url_for("main.school_home", school_slug=school.slug))

    return render_template("auth/alum_signup.html", school=school)


# ---------------- Alum login ----------------

@bp.route("/<school_slug>/login", methods=["GET", "POST"])
def alum_login(school_slug):
    school = _get_school(school_slug)
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(school_id=school.id, email=email).first()
        if user and user.check_password(password):
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
        if user and user.check_password(password) and user.is_admin:
            login_user(user)
            return redirect(url_for("admin.dashboard", school_slug=school.slug))
        flash("Invalid admin credentials.", "error")
    return render_template("auth/admin_login.html", school=school)


# ---------------- Logout ----------------

@bp.route("/logout")
@login_required
def logout():
    school_slug = current_user.school.slug
    logout_user()
    return redirect(url_for("main.school_home", school_slug=school_slug))
