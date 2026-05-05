"""School admin dashboard: roster, send announcements, basic stats."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from . import db
from .models import School, User, Group, Announcement, Message

bp = Blueprint("admin", __name__)


def _require_admin(school_slug):
    school = School.query.filter_by(slug=school_slug).first_or_404()
    if not current_user.is_authenticated:
        abort(401)
    if current_user.school_id != school.id or not current_user.is_admin:
        abort(403)
    return school


@bp.route("/s/<school_slug>/admin")
@login_required
def dashboard(school_slug):
    school = _require_admin(school_slug)
    alumni = User.query.filter_by(school_id=school.id).order_by(User.created_at.desc()).all()
    group_count = Group.query.filter_by(school_id=school.id).count()
    message_count = (
        Message.query.join(User, Message.sender_id == User.id)
        .filter(User.school_id == school.id)
        .count()
    )
    announcements = (
        Announcement.query.filter_by(school_id=school.id)
        .order_by(Announcement.sent_at.desc())
        .all()
    )
    return render_template(
        "admin/dashboard.html",
        school=school,
        alumni=alumni,
        group_count=group_count,
        message_count=message_count,
        announcements=announcements,
    )


@bp.route("/s/<school_slug>/admin/announce", methods=["POST"])
@login_required
def announce(school_slug):
    school = _require_admin(school_slug)
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if not (title and body):
        flash("Title and body are required.", "error")
        return redirect(url_for("admin.dashboard", school_slug=school.slug))
    db.session.add(
        Announcement(
            school_id=school.id,
            sent_by_id=current_user.id,
            title=title,
            body=body,
        )
    )
    db.session.commit()
    flash("Announcement sent.", "success")
    return redirect(url_for("admin.dashboard", school_slug=school.slug))


@bp.route("/s/<school_slug>/admin/promote/<int:user_id>", methods=["POST"])
@login_required
def toggle_admin(school_slug, user_id):
    school = _require_admin(school_slug)
    user = User.query.filter_by(id=user_id, school_id=school.id).first_or_404()
    if user.id == current_user.id:
        flash("You can't change your own admin status here.", "error")
        return redirect(url_for("admin.dashboard", school_slug=school.slug))
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(
        f"{user.full_name} is now {'an admin' if user.is_admin else 'a regular alum'}.",
        "success",
    )
    return redirect(url_for("admin.dashboard", school_slug=school.slug))
