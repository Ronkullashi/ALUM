"""Direct messaging: inbox + thread between two alumni in the same school."""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_login import login_required, current_user
from sqlalchemy import or_, and_
from . import db
from .models import School, User, Message

bp = Blueprint("messages", __name__)


def _require_same_school(school_slug):
    school = School.query.filter_by(slug=school_slug).first_or_404()
    if not current_user.is_authenticated or current_user.school_id != school.id:
        abort(403)
    return school


@bp.route("/s/<school_slug>/messages")
@login_required
def inbox(school_slug):
    school = _require_same_school(school_slug)

    # Build a list of conversation partners with the most recent message.
    msgs = (
        Message.query.filter(
            or_(
                Message.sender_id == current_user.id,
                Message.recipient_id == current_user.id,
            )
        )
        .order_by(Message.sent_at.desc())
        .all()
    )

    seen = set()
    threads = []
    for m in msgs:
        partner_id = m.recipient_id if m.sender_id == current_user.id else m.sender_id
        if partner_id in seen:
            continue
        seen.add(partner_id)
        partner = db.session.get(User, partner_id)
        if not partner:
            continue
        unread = (
            m.recipient_id == current_user.id and m.read_at is None
        )
        threads.append({"partner": partner, "last": m, "unread": unread})

    return render_template("messages/inbox.html", school=school, threads=threads)


@bp.route("/s/<school_slug>/messages/<int:user_id>", methods=["GET", "POST"])
@login_required
def thread(school_slug, user_id):
    school = _require_same_school(school_slug)
    partner = User.query.filter_by(id=user_id, school_id=school.id).first_or_404()
    if partner.id == current_user.id:
        abort(400)

    if request.method == "POST":
        body = request.form.get("body", "").strip()
        if body:
            db.session.add(
                Message(
                    sender_id=current_user.id,
                    recipient_id=partner.id,
                    body=body,
                )
            )
            db.session.commit()
        return redirect(url_for("messages.thread", school_slug=school.slug, user_id=partner.id))

    # Mark unread incoming messages as read.
    unread = Message.query.filter_by(
        sender_id=partner.id, recipient_id=current_user.id, read_at=None
    ).all()
    for m in unread:
        m.read_at = datetime.utcnow()
    if unread:
        db.session.commit()

    msgs = (
        Message.query.filter(
            or_(
                and_(Message.sender_id == current_user.id, Message.recipient_id == partner.id),
                and_(Message.sender_id == partner.id, Message.recipient_id == current_user.id),
            )
        )
        .order_by(Message.sent_at.asc())
        .all()
    )
    return render_template(
        "messages/thread.html", school=school, partner=partner, messages=msgs
    )
