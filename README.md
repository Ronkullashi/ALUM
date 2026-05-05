# Alum

A social network for high school alumni. Each high school gets its own private network: a school admin dashboard, alumni profiles, a directory, groups, and direct messaging — built around the looser, more personal tone of high school relationships rather than the LinkedIn-style polish of college and career networks.

## What's in this skeleton

- **Per-school networks.** Every school has its own slug (`/s/york-prep`), its own admin login, its own alumni, its own groups.
- **Alumni profiles & directory.** Sign up, fill out a profile (grad year, current role, company, location, bio), browse and search classmates.
- **Groups.** Create class-year groups, clubs, or interest groups. Join, leave, see members.
- **Direct messaging.** 1-on-1 DMs between alumni in the same school.
- **School admin dashboard.** Per-school admin login, alumni roster, send school-wide announcements, basic engagement stats.

This is intentionally a skeleton — the data model, routing, auth, and templates are all in place, but UI polish, file uploads, email verification, password reset, and similar production features are not. Everything renders as plain HTML so it's easy to read and modify.

## Stack

- Flask 3 + Jinja templates (vanilla HTML/CSS/JS — no build step, no JS framework)
- SQLAlchemy + SQLite (single file at `instance/alum.db`)
- Flask-Login for sessions, Werkzeug for password hashing

## Run it

```bash
# 1. (optional but recommended) make a virtual env
python3 -m venv venv
source venv/bin/activate

# 2. install dependencies
pip install -r requirements.txt

# 3. seed the database with York Prep + a second school + sample alumni
python seed.py

# 4. start the dev server
python run.py
```

Then open <http://localhost:5000>. The seed script prints the demo logins.

## Project layout

```
app/
├── __init__.py          # create_app, db, login_manager
├── models.py            # School, User, Group, GroupMembership, Message, Announcement
├── auth.py              # alum signup/login, admin login, logout
├── main.py              # landing, school home, school list
├── alumni.py            # directory, profile view, edit profile
├── groups.py            # list/create/join/leave/detail
├── messages.py          # inbox and thread
├── admin.py             # admin dashboard, send announcement
├── templates/           # Jinja templates (one base.html, then per-feature folders)
└── static/              # styles.css and app.js
run.py                   # entry point
seed.py                  # sample data
requirements.txt
```

## Adding a new school

The skeleton ships with two seeded schools. To add another, either run `seed.py` again with edits, or add rows to the `schools` table directly. A future iteration would expose a "School signup" flow where a school admin requests a network for their school.

## What to build next

- Email verification on alum signup (and a verified-grads-only flag the school can require)
- File uploads for profile photos and school logos
- Group posts / a feed (the model layer has a stub `Post` table you can wire up)
- Job board scoped to a school
- Admin invite flow (so admins can grant admin to other alumni)
- Move auth to OAuth (Google) so you don't have to manage passwords at all
