"""Groups blueprint: list, create, view, join, leave."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from . import db
from .models import School, Group, GroupMembership

bp = Blueprint("groups", __name__)


def _require_same_school(school_slug):
    school = School.query.filter_by(slug=school_slug).first_or_404()
    if not current_user.is_authenticated or current_user.school_id != school.id:
        abort(403)
    return school


@bp.route("/s/<school_slug>/groups")
@login_required
def list_groups(school_slug):
    school = _require_same_school(school_slug)
    groups = Group.query.filter_by(school_id=school.id).order_by(Group.name).all()
    my_group_ids = {m.group_id for m in current_user.memberships}
    return render_template(
        "groups/list.html", school=school, groups=groups, my_group_ids=my_group_ids
    )


@bp.route("/s/<school_slug>/groups/new", methods=["GET", "POST"])
@login_required
def new_group(school_slug):
    school = _require_same_school(school_slug)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "interest").strip() or "interest"
        if not name:
            flash("Group name is required.", "error")
            return render_template("groups/new.html", school=school)
        group = Group(
            school_id=school.id,
            name=name,
            description=description,
            category=category,
            created_by_id=current_user.id,
        )
        db.session.add(group)
        db.session.flush()
        # Creator auto-joins.
        db.session.add(GroupMembership(user_id=current_user.id, group_id=group.id))
        db.session.commit()
        flash(f"Created group “{group.name}”.", "success")
        return redirect(url_for("groups.group_detail", school_slug=school.slug, group_id=group.id))
    return render_template("groups/new.html", school=school)


@bp.route("/s/<school_slug>/groups/<int:group_id>")
@login_required
def group_detail(school_slug, group_id):
    school = _require_same_school(school_slug)
    group = Group.query.filter_by(id=group_id, school_id=school.id).first_or_404()
    members = [m.user for m in group.memberships]
    is_member = current_user.is_member_of(group)
    return render_template(
        "groups/detail.html",
        school=school,
        group=group,
        members=members,
        is_member=is_member,
    )


@bp.route("/s/<school_slug>/groups/<int:group_id>/join", methods=["POST"])
@login_required
def join_group(school_slug, group_id):
    school = _require_same_school(school_slug)
    group = Group.query.filter_by(id=group_id, school_id=school.id).first_or_404()
    if not current_user.is_member_of(group):
        db.session.add(GroupMembership(user_id=current_user.id, group_id=group.id))
        db.session.commit()
    return redirect(url_for("groups.group_detail", school_slug=school.slug, group_id=group.id))


@bp.route("/s/<school_slug>/groups/<int:group_id>/leave", methods=["POST"])
@login_required
def leave_group(school_slug, group_id):
    school = _require_same_school(school_slug)
    group = Group.query.filter_by(id=group_id, school_id=school.id).first_or_404()
    membership = GroupMembership.query.filter_by(
        user_id=current_user.id, group_id=group.id
    ).first()
    if membership:
        db.session.delete(membership)
        db.session.commit()
    return redirect(url_for("groups.list_groups", school_slug=school.slug))
