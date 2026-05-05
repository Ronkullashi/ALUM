"""Seed the database.

Modes:
  python seed.py                 wipe and re-seed (destructive)
  python seed.py --if-empty      only seed if no schools exist (safe for boot)
  ALUM_RESEED=true python ...    forces a wipe-and-reseed even with --if-empty

In production on Render, render.yaml runs `python seed.py --if-empty` on every
boot, so seed only happens once. To re-seed with new schemas, flip the
ALUM_RESEED env var to "true" in the Render dashboard once, redeploy, then
turn it off again.

Schools seeded: 27 Manhattan private high schools.
Each school gets:
  - a randomly generated unique 7-digit access code (printed at the end)
  - one admin user (no other alumni; users sign up via the UI)
"""
import os
import sys
import random
import string

from app import create_app, db
from app.models import School, User, Group, GroupMembership, Announcement, Message


# (name, slug, neighborhood, short description)
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
        current_role=f"{school.name} Alumni Office",
        location=f"{school.neighborhood}, New York, NY",
    )
    u.set_password("admin")  # demo password — change after first login
    db.session.add(u)
    return u


# --------------------------------- seed ----------------------------------

def populate():
    """Insert schools + admins. Tables must already exist and be empty."""
    used_codes = set()
    schools = []
    admins = []

    for (name, slug, neighborhood, description) in MANHATTAN_PRIVATE_HS:
        school = make_school(name, slug, neighborhood, description, used_codes)
        schools.append(school)

    db.session.flush()  # assign IDs

    for school in schools:
        admin = make_admin(school)
        admins.append(admin)

    db.session.commit()
    return schools, admins


def main():
    if_empty = "--if-empty" in sys.argv
    force_reseed = os.environ.get("ALUM_RESEED", "").lower() == "true"

    app = create_app()
    with app.app_context():
        if force_reseed:
            print("ALUM_RESEED=true — wiping the database and re-seeding.")
            db.drop_all()
            db.create_all()
        elif if_empty:
            db.create_all()
            try:
                count = School.query.count()
            except Exception as e:
                # Schema mismatch: old tables don't have the new columns we
                # added (e.g. access_code). db.create_all() doesn't ALTER
                # existing tables, so the only safe move is to drop and start
                # over. This is destructive but acceptable for a skeleton.
                print(f"Schema out of date ({type(e).__name__}: {e}).")
                print("Dropping and recreating tables to match the new schema.")
                db.session.rollback()
                db.drop_all()
                db.create_all()
                count = 0

            if count > 0:
                print("Database already populated; skipping seed.")
                print("(Set ALUM_RESEED=true and redeploy to force a reset.)")
                return
            print("Database is empty — running seed…")
        else:
            db.drop_all()
            db.create_all()

        schools, admins = populate()

        print()
        print("=" * 72)
        print(" Seed complete. Manhattan private high schools loaded.")
        print("=" * 72)
        print()
        print(f" {'School':<42}{'Code':<10}Admin email")
        print("-" * 72)
        for school, admin in zip(schools, admins):
            print(f" {school.name[:40]:<42}{school.access_code:<10}{admin.email}")
        print()
        print(" All admin passwords are: admin (change after first login)")
        print()


if __name__ == "__main__":
    main()
