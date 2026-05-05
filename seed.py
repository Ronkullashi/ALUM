"""Seed the database.

Modes:
  python seed.py                 wipe and re-seed (DESTRUCTIVE — local dev only)
  python seed.py --if-empty      seed only if no schools exist (safe for boot)
  python seed.py --add-only      add any new schools to MANHATTAN_PRIVATE_HS
                                 that aren't in the DB yet (idempotent, safe)
  ALUM_RESEED=true python seed.py --if-empty
                                 forces a full wipe-and-reseed
                                 (only use this if you really mean it)

How the live site stays stable:
  render.yaml runs `--if-empty` (no-op once seeded) then `--add-only` (adds
  schools you've appended to the list since last deploy). Existing schools,
  their access codes, and all user signups are NEVER touched.

Adding a new school: append a tuple to MANHATTAN_PRIVATE_HS below, push to
GitHub. The next deploy adds it with a fresh code and prints the code in the
deploy logs. No data is lost.

Schools seeded: 27 Manhattan private high schools. Each gets a random unique
7-digit access code and one admin user (no other alumni; users sign up via
the UI).
"""
import os
import sys
import random
import string

from app import create_app, db
from app.models import School, User, Group, GroupMembership, Announcement, Message


# (name, slug, neighborhood, short description)
# Append new schools to the end of this list. Slugs must be unique and use
# only lowercase letters, digits, and hyphens (they appear in the URL).
MANHATTAN_PRIVATE_HS = [
    ("York Preparatory School", "york-prep", "Upper West Side",
     "Independent coed school, grades 6–12."),
    ("Trinity School", "trinity", "Upper West Side",
     "K–12 independent school, founded 1709."),
    ("Collegiate School", "collegiate", "Upper West Side",
     "K–12 all-boys, founded 1628 — oldest school in the U.S."),
    ("Dalton School", "dalton", "Upper East Side",
     "Progressive K–12 coed independent school."),
    ("The Brearley School", "brearley", "Upper East Side",
     "All-girls K–12 independent school."),
    ("Chapin School", "chapin", "Upper East Side",
     "All-girls K–12 independent school."),
    ("The Spence School", "spence", "Upper East Side",
     "All-girls K–12 independent school."),
    ("Nightingale-Bamford School", "nightingale", "Upper East Side",
     "All-girls K–12 independent school."),
    ("Marymount School of New York", "marymount", "Upper East Side",
     "All-girls Catholic K–12 school."),
    ("Convent of the Sacred Heart", "sacred-heart", "Upper East Side",
     "All-girls Catholic K–12 school."),
    ("The Browning School", "browning", "Upper East Side",
     "All-boys K–12 independent school."),
    ("The Calhoun School", "calhoun", "Upper West Side",
     "Progressive coed school, grades 3–12."),
    ("The Hewitt School", "hewitt", "Upper East Side",
     "All-girls K–12 independent school."),
    ("Birch Wathen Lenox School", "bwl", "Upper East Side",
     "Coed K–12 independent school."),
    ("Loyola School", "loyola", "Upper East Side",
     "Catholic Jesuit coed high school, grades 9–12."),
    ("Regis High School", "regis", "Upper East Side",
     "Tuition-free Jesuit all-boys high school, grades 9–12."),
    ("Xavier High School", "xavier", "Chelsea",
     "Catholic Jesuit all-boys high school, grades 9–12."),
    ("Friends Seminary", "friends-seminary", "East Village",
     "Quaker K–12 coed independent school."),
    ("Avenues: The World School", "avenues", "Chelsea",
     "Coed K–12 international school."),
    ("Léman Manhattan Preparatory School", "leman", "Financial District",
     "Coed PreK–12 independent school."),
    ("Trevor Day School", "trevor", "Upper East Side",
     "Coed N–12 progressive independent school."),
    ("Lycée Français de New York", "lycee-francais", "Upper East Side",
     "French bilingual PreK–12 coed school."),
    ("The Beekman School", "beekman", "Murray Hill",
     "Coed independent high school, grades 9–12."),
    ("Dwight School", "dwight", "Upper West Side",
     "Coed PreK–12 IB World School."),
    ("Ramaz School", "ramaz", "Upper East Side",
     "Modern Orthodox Jewish coed N–12 day school."),
    ("The Heschel School", "heschel", "Upper West Side",
     "Pluralist Jewish coed N–12 day school."),
    ("Professional Children's School", "pcs", "Lincoln Square",
     "Coed independent school for student artists & athletes, grades 6–12."),
]


# -------------------------------- helpers --------------------------------

def generate_access_code(used: set) -> str:
    """Return a 7-digit code not already in `used`. Mutates `used`."""
    while True:
        code = "".join(random.choices(string.digits, k=7))
        if code not in used:
            used.add(code)
            return code


def make_school(name, slug, neighborhood, description, used_codes):
    s = School(
        name=name,
        slug=slug,
        neighborhood=neighborhood,
        city="New York",
        state="NY",
        description=description,
        access_code=generate_access_code(used_codes),
    )
    db.session.add(s)
    return s


def make_admin(school):
    """Create the single admin user for a school."""
    email = f"admin@{school.slug}.alumtest"
    u = User(
        school_id=school.id,
        email=email,
        first_name="Alumni",
        last_name="Office",
        is_admin=True,
        is_verified=True,  # admins skip the approval queue
        current_role=f"{school.name} Alumni Office",
        location=f"{school.neighborhood}, New York, NY",
    )
    u.set_password("admin")  # demo password — change after first login
    db.session.add(u)
    return u


def print_school_table(schools, admins, header="Schools"):
    print()
    print("=" * 72)
    print(f" {header}")
    print("=" * 72)
    print(f" {'School':<42}{'Code':<10}Admin email")
    print("-" * 72)
    for school, admin in zip(schools, admins):
        admin_email = admin.email if admin else "—"
        print(f" {school.name[:40]:<42}{school.access_code:<10}{admin_email}")
    print()
    print(" Admin password (default): admin")
    print()


def print_all_schools_in_db():
    schools = School.query.order_by(School.name).all()
    admins_by_school = {
        u.school_id: u
        for u in User.query.filter_by(is_admin=True).all()
    }
    admins = [admins_by_school.get(s.id) for s in schools]
    print_school_table(schools, admins, header=f"All schools in database ({len(schools)})")


# --------------------------------- seed ----------------------------------

def populate_full():
    """Insert schools + admins from scratch. Assumes empty tables."""
    used_codes = set()
    schools = []

    for (name, slug, neighborhood, description) in MANHATTAN_PRIVATE_HS:
        schools.append(make_school(name, slug, neighborhood, description, used_codes))
    db.session.flush()  # assign IDs

    admins = [make_admin(school) for school in schools]
    db.session.commit()
    return schools, admins


def populate_add_only():
    """Insert only schools whose slug isn't already in the DB.
    Idempotent — safe to run on every boot. Returns the newly added schools."""
    existing_slugs = {s.slug for s, in db.session.query(School.slug).all()}
    existing_codes = {s.access_code for s, in db.session.query(School.access_code).all()}

    new_records = [
        rec for rec in MANHATTAN_PRIVATE_HS if rec[1] not in existing_slugs
    ]
    if not new_records:
        return [], []

    new_schools = []
    for (name, slug, neighborhood, description) in new_records:
        new_schools.append(
            make_school(name, slug, neighborhood, description, existing_codes)
        )
    db.session.flush()

    new_admins = [make_admin(school) for school in new_schools]
    db.session.commit()
    return new_schools, new_admins


# ------------------------------- entrypoint -------------------------------

def main():
    if_empty = "--if-empty" in sys.argv
    add_only = "--add-only" in sys.argv
    force_reseed = os.environ.get("ALUM_RESEED", "").lower() == "true"

    app = create_app()
    with app.app_context():
        if force_reseed:
            print("ALUM_RESEED=true — wiping the database and re-seeding.")
            db.drop_all()
            db.create_all()
            schools, admins = populate_full()
            print_school_table(schools, admins, "Seed complete.")
            return

        if add_only:
            # Idempotent. Adds only schools that don't already exist by slug.
            new_schools, new_admins = populate_add_only()
            if new_schools:
                print_school_table(new_schools, new_admins,
                                   f"Added {len(new_schools)} new school(s)")
            else:
                print("--add-only: no new schools to add.")
            # Always print the full current list so codes are easy to find.
            print_all_schools_in_db()
            return

        if if_empty:
            # Note: db.create_all() is a no-op if tables exist. It does NOT
            # add new columns — schema changes require a real migration.
            db.create_all()
            if School.query.count() > 0:
                print("Database already populated; skipping --if-empty seed.")
                return
            print("Database is empty — running initial seed…")
            schools, admins = populate_full()
            print_school_table(schools, admins, "Initial seed complete.")
            return

        # Default (no flags): destructive. Local dev only — never run on
        # production data.
        confirm = os.environ.get("ALUM_DESTRUCTIVE_OK", "").lower() == "true"
        if not confirm:
            print(
                "Refusing to drop and re-seed without confirmation. "
                "Set ALUM_DESTRUCTIVE_OK=true to override, or use "
                "--if-empty / --add-only for safe modes."
            )
            sys.exit(1)
        print("WARNING: dropping all data and re-seeding from scratch.")
        db.drop_all()
        db.create_all()
        schools, admins = populate_full()
        print_school_table(schools, admins, "Seed complete.")


if __name__ == "__main__":
    main()
