"""Seed the database with two demo schools and a handful of alumni.

Run after install:  python seed.py
Re-running drops everything and re-creates it.
"""
from app import create_app, db
from app.models import School, User, Group, GroupMembership, Announcement, Message


SCHOOLS = [
    {
        "slug": "york-prep",
        "name": "York Prep",
        "city": "New York",
        "state": "NY",
        "description": (
            "An independent high school on the Upper West Side. Small classes, "
            "lots of personality, and a tight-knit alumni community."
        ),
    },
    {
        "slug": "bronx-science",
        "name": "Bronx High School of Science",
        "city": "Bronx",
        "state": "NY",
        "description": (
            "A specialized public high school known for its math, science, and "
            "research programs. Eight Nobel laureates and counting."
        ),
    },
]


YORK_PREP_ALUMNI = [
    # (first, last, email, grad_year, role, company, location, bio, is_admin)
    ("Dren", "Kullashi", "dren@yorkprep.example", 2024, "Investment Banking Analyst",
     "Baruch College", "New York, NY",
     "Studying finance at Baruch. Building Alum on the side.", False),
    ("Maya", "Chen", "maya@yorkprep.example", 2022, "Software Engineer",
     "Stripe", "San Francisco, CA",
     "Working on payments infra. Always happy to chat with younger alumni.", False),
    ("Jordan", "Levine", "jordan@yorkprep.example", 2020, "Medical Resident",
     "Mount Sinai", "New York, NY",
     "Pediatrics resident. Rowed varsity. Reach out if you're pre-med.", False),
    ("Priya", "Desai", "priya@yorkprep.example", 2018, "Founder & CEO",
     "Threadline (acquired)", "New York, NY",
     "Started a logistics startup, sold it last year. Now figuring out what's next.", False),
    ("Sam", "Okafor", "sam@yorkprep.example", 2024, "Freshman, undecided",
     "Vanderbilt University", "Nashville, TN",
     "Just got to college. Looking for advice on picking a major.", False),
    ("Ms. Alvarez", "Director of Alumni", "alvarez@yorkprep.example", None,
     "Director of Alumni Relations", "York Prep", "New York, NY",
     "I run the alumni office at York Prep. Email me with anything!", True),
]


BRONX_SCIENCE_ALUMNI = [
    ("Aisha", "Khan", "aisha@bxs.example", 2021, "PhD candidate, ML",
     "MIT", "Cambridge, MA", "ML research, mostly NLP.", False),
    ("Marco", "Rivera", "marco@bxs.example", 2019, "Software Engineer",
     "Google", "Mountain View, CA", "SRE on Search.", False),
    ("Mr. Park", "Alumni Office", "park@bxs.example", None,
     "Director of Alumni Relations", "Bronx Science", "Bronx, NY",
     "Running the alumni network for the school.", True),
]


YORK_PREP_GROUPS = [
    ("Class of 2024", "class_year",
     "For everyone who graduated in 2024. Senior trip memories live here forever."),
    ("Class of 2022", "class_year", "Class of 2022 — share what you're up to."),
    ("Pre-Med Mentors", "interest",
     "Med school applicants, residents, and current students helping juniors and seniors."),
    ("Varsity Crew", "sport", "Past and present rowers."),
    ("NYC Tech", "interest",
     "Alumni working in software, design, or data in New York."),
]


BRONX_SCIENCE_GROUPS = [
    ("Class of 2021", "class_year", "Class of 2021 alumni."),
    ("Research Program", "club", "Past students of the Bronx Science research program."),
]


def make_school(record):
    s = School(**record)
    db.session.add(s)
    return s


def make_user(school, first, last, email, grad_year, role, company, location, bio, is_admin):
    u = User(
        school_id=school.id,
        email=email.lower(),
        first_name=first,
        last_name=last,
        grad_year=grad_year,
        current_role=role,
        current_company=company,
        location=location,
        bio=bio,
        is_admin=is_admin,
    )
    u.set_password("password")  # all demo users: "password"
    db.session.add(u)
    return u


def make_group(school, name, category, description, creator):
    g = Group(
        school_id=school.id,
        name=name,
        category=category,
        description=description,
        created_by_id=creator.id,
    )
    db.session.add(g)
    db.session.flush()
    db.session.add(GroupMembership(user_id=creator.id, group_id=g.id))
    return g


def main():
    app = create_app()
    with app.app_context():
        # Reset.
        db.drop_all()
        db.create_all()

        # Schools
        york = make_school(SCHOOLS[0])
        bronx = make_school(SCHOOLS[1])
        db.session.flush()

        # York Prep alumni
        york_users = [make_user(york, *row) for row in YORK_PREP_ALUMNI]
        bronx_users = [make_user(bronx, *row) for row in BRONX_SCIENCE_ALUMNI]
        db.session.flush()

        # Groups
        york_groups = [
            make_group(york, name, cat, desc, york_users[0])
            for (name, cat, desc) in YORK_PREP_GROUPS
        ]
        bronx_groups = [
            make_group(bronx, name, cat, desc, bronx_users[0])
            for (name, cat, desc) in BRONX_SCIENCE_GROUPS
        ]
        db.session.flush()

        # Drop everyone into their class-year group + a couple interest groups.
        york_class_2024 = york_groups[0]
        york_class_2022 = york_groups[1]
        york_premed = york_groups[2]
        york_tech = york_groups[4]

        for u in york_users:
            if u.grad_year == 2024:
                db.session.add(GroupMembership(user_id=u.id, group_id=york_class_2024.id))
            if u.grad_year == 2022:
                db.session.add(GroupMembership(user_id=u.id, group_id=york_class_2022.id))

        # Topical groups
        for u in york_users:
            if u.current_role and "resident" in (u.current_role or "").lower():
                db.session.add(GroupMembership(user_id=u.id, group_id=york_premed.id))
            if u.current_role and any(k in (u.current_role or "").lower() for k in ["engineer", "founder"]):
                db.session.add(GroupMembership(user_id=u.id, group_id=york_tech.id))

        # Announcement from the York Prep admin.
        york_admin = next(u for u in york_users if u.is_admin)
        db.session.add(
            Announcement(
                school_id=york.id,
                sent_by_id=york_admin.id,
                title="Homecoming reunion — October 12",
                body=(
                    "Save the date — homecoming weekend is October 12. Tours, "
                    "alumni mixer, and the annual fall game. RSVP details soon."
                ),
            )
        )

        # A sample DM thread.
        dren = next(u for u in york_users if u.email.startswith("dren@"))
        maya = next(u for u in york_users if u.email.startswith("maya@"))
        db.session.add(Message(
            sender_id=dren.id, recipient_id=maya.id,
            body="Hey Maya — saw you're at Stripe. Mind if I ask about IB recruiting vs SWE for finance roles?"
        ))
        db.session.add(Message(
            sender_id=maya.id, recipient_id=dren.id,
            body="Of course, happy to chat. Free Sunday afternoon?"
        ))

        db.session.commit()

        print()
        print("Seed complete.")
        print()
        print("Demo logins (all passwords are: password)")
        print("-" * 60)
        print("York Prep — http://localhost:5000/s/york-prep/")
        for u in york_users:
            tag = " (ADMIN)" if u.is_admin else ""
            print(f"  {u.email:<35} {u.full_name}{tag}")
        print()
        print("Bronx Science — http://localhost:5000/s/bronx-science/")
        for u in bronx_users:
            tag = " (ADMIN)" if u.is_admin else ""
            print(f"  {u.email:<35} {u.full_name}{tag}")
        print()
        print("Admin login URL:  /auth/<school-slug>/admin/login")
        print("Alum login URL:   /auth/<school-slug>/login")
        print()


if __name__ == "__main__":
    main()
