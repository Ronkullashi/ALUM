"""Public landing + per-school home."""
from flask import Blueprint, render_template, abort
from flask_login import current_user
from .models import School, Announcement, User, Group

bp = Blueprint("main", __name__)


@bp.route("/")
def landing():
    schools = School.query.order_by(School.name).all()
    return render_template("landing.html", schools=schools)


@bp.route("/s/<school_slug>/")
def school_home(school_slug):
    school = School.query.filter_by(slug=school_slug).first_or_404()
    announcements = (
        Announcement.query.filter_by(school_id=school.id)
        .order_by(Announcement.sent_at.desc())
        .limit(5)
        .all()
    )
    alum_count = User.query.filter_by(school_id=school.id).count()
    group_count = Group.query.filter_by(school_id=school.id).count()
    return render_template(
        "school_home.html",
        school=school,
        announcements=announcements,
        alum_count=alum_count,
        group_count=group_count,
    )
