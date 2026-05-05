"""Seed the database.

Modes:
  python seed.py                 wipe and re-seed (DESTRUCTIVE — local dev only,
                                 requires ALUM_DESTRUCTIVE_OK=true)
  python seed.py --if-empty      seed only if no schools exist (safe for boot).
                                 Always prints the current codes at the end.
  ALUM_RESEED=true python ...    forces a full wipe-and-reseed

Production startup runs --if-empty, which is a no-op once you've seeded.
The current schools and their codes are always printed at the end of every
run, so you can find your codes in any deploy log.
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


def generate_access_code(used: set) -> str:
    while True:
        code = "".join(random.choices(string.digits, k=7))
        if code not in used:
            used.add(code)
            return code


def make_school(name, slug, neighborhood, description, used_codes):
    s = School(
        name=name, slug=slug, neighborhood=neighborhood,
        city="New York", state="NY", description=description,
        access_code=generate_access_code(used_codes),
    )
    db.session.add(s)
    return s


def make_admin(school):
    email = f"admin@{school.slug}.alumtest"
    u = User(
        school_id=school.id, email=email,
        first_name="Alumni", last_name="Office",
        is_admin=True, is_verified=True,
        current_role=f"{school.name} Alumni Office",
        location=f"{school.neighborhood}, New York, NY",
    )
    u.set_password("admin")
    db.session.add(u)
    return u


def populate():
    used_codes = set()
    schools = []
    for (name, slug, neighborhood, description) in MANHATTAN_PRIVATE_HS:
        schools.append(make_school(name, slug, neighborhood, description, used_codes))
    db.session.flush()
    admins = [make_admin(s) for s in schools]
    db.session.commit()
    return schools, admins


def print_current_codes():
    """Print every school + code currently in the database. Always reads
    from the DB so the printed codes are guaranteed to match what the form
    accepts — no stale logs, no surprises."""
    schools = School.query.order_by(School.name).all()
    admins_by_school = {
        u.school_id: u
        for u in User.query.filter_by(is_admin=True).all()
    }

    print()
    print("=" * 72)
    print(f" CURRENT SCHOOLS IN DATABASE ({len(schools)})")
    print(" These are the codes that work on the live site right now.")
    print("=" * 72)
    print(f" {'School':<42}{'Code':<10}Admin email")
    print("-" * 72)
    for school in schools:
        admin = admins_by_school.get(school.id)
        admin_email = admin.email if admin else "—"
        print(f" {school.name[:40]:<42}{school.access_code:<10}{admin_email}")
    print()
    print(" Admin password (default): admin")
    print()


def main():
    if_empty = "--if-empty" in sys.argv
    force_reseed = os.environ.get("ALUM_RESEED", "").lower() == "true"

    app = create_app()
    with app.app_context():
        if force_reseed:
            print("ALUM_RESEED=true — wiping the database and re-seeding.")
            db.drop_all()
            db.create_all()
            populate()
        elif if_empty:
            db.create_all()
            if School.query.count() > 0:
                print("Database already populated; skipping --if-empty seed.")
            else:
                print("Database is empty — running initial seed…")
                populate()
        else:
            if os.environ.get("ALUM_DESTRUCTIVE_OK", "").lower() != "true":
                print(
                    "Refusing to drop and re-seed without confirmation. "
                    "Set ALUM_DESTRUCTIVE_OK=true to override, or use --if-empty."
                )
                sys.exit(1)
            print("WARNING: dropping all data and re-seeding.")
            db.drop_all()
            db.create_all()
            populate()

        # Always print the current codes at the end of every run, so they're
        # never out of sync with what's actually in the database.
        print_current_codes()


if __name__ == "__main__":
    main()
