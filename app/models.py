"""SQLAlchemy models for Alum.

Design notes:
- A `School` is the unit of a network. Alumni belong to exactly one school.
- A `User` is an alum (or an alum who's also been promoted to school admin via
  `is_admin`). Email is unique within a school, not globally — two people at
  different schools can use the same address.
- `Group` is scoped to a school. `GroupMembership` is the join table.
- `Message` is a 1-on-1 DM between two users in the same school.
- `Announcement` is a school-wide post written by an admin.
- `Post` is included as a stub for a future group/feed feature.
"""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


class School(db.Model):
    __tablename__ = "schools"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    city = db.Column(db.String(120))
    state = db.Column(db.String(80))
    logo_url = db.Column(db.String(500))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship("User", back_populates="school", cascade="all, delete-orphan")
    groups = db.relationship("Group", back_populates="school", cascade="all, delete-orphan")
    announcements = db.relationship(
        "Announcement", back_populates="school", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<School {self.slug}>"


class User(UserMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = (
        db.UniqueConstraint("school_id", "email", name="uq_user_email_per_school"),
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)

    # Identity
    email = db.Column(db.String(200), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)

    # Profile
    grad_year = db.Column(db.Integer)
    current_role = db.Column(db.String(160))
    current_company = db.Column(db.String(160))
    location = db.Column(db.String(160))
    bio = db.Column(db.Text)
    profile_pic_url = db.Column(db.String(500))

    # Permissions
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    school = db.relationship("School", back_populates="users")
    memberships = db.relationship(
        "GroupMembership", back_populates="user", cascade="all, delete-orphan"
    )
    sent_messages = db.relationship(
        "Message", foreign_keys="Message.sender_id", back_populates="sender",
        cascade="all, delete-orphan",
    )
    received_messages = db.relationship(
        "Message", foreign_keys="Message.recipient_id", back_populates="recipient",
        cascade="all, delete-orphan",
    )

    # --- helpers ---
    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def is_member_of(self, group):
        return any(m.group_id == group.id for m in self.memberships)

    def __repr__(self):
        return f"<User {self.full_name} @ {self.school.slug if self.school else '?'}>"


class Group(db.Model):
    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    # Free-form category: "class_year", "club", "interest", "sport", etc.
    category = db.Column(db.String(40), default="interest")
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    school = db.relationship("School", back_populates="groups")
    memberships = db.relationship(
        "GroupMembership", back_populates="group", cascade="all, delete-orphan"
    )

    @property
    def member_count(self):
        return len(self.memberships)


class GroupMembership(db.Model):
    __tablename__ = "group_memberships"
    __table_args__ = (
        db.UniqueConstraint("user_id", "group_id", name="uq_user_group"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False, index=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="memberships")
    group = db.relationship("Group", back_populates="memberships")


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    body = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    read_at = db.Column(db.DateTime)

    sender = db.relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    recipient = db.relationship(
        "User", foreign_keys=[recipient_id], back_populates="received_messages"
    )


class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False, index=True)
    sent_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

    school = db.relationship("School", back_populates="announcements")
    sent_by = db.relationship("User")


class Post(db.Model):
    """Stub for a future group/feed feature. Not wired into the UI yet."""
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
