"""Alumni directory + profile pages."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from . import db
from .models import School, User

bp = Blueprint("alumni", __name__)


def _require_same_school(school_slug):
    """Helper: load the school by slug and confirm the logged-in user is in it."""
    school = School.query.filter_by(slug=school_slug).first_or_404()
    if not current_user.is_authenticated or current_user.school_id != school.id:
        abort(403)
    return school


@bp.route("/s/<school_slug>/directory")
@login_required
def directory(school_slug):
    school = _require_same_school(school_slug)
    q = request.args.get("q", "").strip()
    grad_year = request.args.get("grad_year", "").strip()

    query = User.query.filter_by(school_id=school.id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                User.first_name.ilike(like),
                User.last_name.ilike(like),
                User.current_role.ilike(like),
                User.current_company.ilike(like),
                User.location.ilike(like),
            )
        )
    if grad_year.isdigit():
        query = query.filter(User.grad_year == int(grad_year))

    alumni = query.order_by(User.last_name, User.first_name).all()

    # Distinct grad years for the filter dropdown.
    years = sorted(
        {u.grad_year for u in school.users if u.grad_year}, reverse=True
    )

    return render_template(
        "alumni/directory.html",
        school=school,
        alumni=alumni,
        q=q,
        grad_year=grad_year,
        years=years,
    )


@bp.route("/s/<school_slug>/profile/<int:user_id>")
@login_required
def profile(school_slug, user_id):
    school = _require_same_school(school_slug)
    user = User.query.filter_by(id=user_id, school_id=school.id).first_or_404()
    return render_template("alumni/profile.html", school=school, user=user)


@bp.route("/s/<school_slug>/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile(school_slug):
    school = _require_same_school(school_slug)
    if request.method == "POST":
        current_user.first_name = request.form.get("first_name", current_user.first_name).strip()
        current_user.last_name = request.form.get("last_name", current_user.last_name).strip()
        gy = request.form.get("grad_year", "").strip()
        current_user.grad_year = int(gy) if gy.isdigit() else None
        current_user.current_role = request.form.get("current_role", "").strip() or None
        current_user.current_company = request.form.get("current_company", "").strip() or None
        current_user.location = request.form.get("location", "").strip() or None
        current_user.bio = request.form.get("bio", "").strip() or None
        current_user.profile_pic_url = request.form.get("profile_pic_url", "").strip() or None
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("alumni.profile", school_slug=school.slug, user_id=current_user.id))

    return render_template("alumni/edit_profile.html", school=school, user=current_user)
