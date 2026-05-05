# Deploying Alum to Render (free)

End result: a public URL like `https://alum.onrender.com` that anyone with the link can use.

This takes about 20 minutes the first time. After that, every change you push to GitHub auto-deploys.

---

## What you need before starting

- A GitHub account (free) — sign up at <https://github.com/signup>
- A Render account (free) — sign up at <https://render.com> (you can sign in with GitHub, easiest)
- GitHub Desktop installed (free, easier than command-line git) — <https://desktop.github.com>

---

## Step 1 — Put the code on GitHub

1. Open **GitHub Desktop**. Sign in with your GitHub account.
2. **File → New Repository**.
   - Name: `alum`
   - Local path: choose `/Users/ronkullashi/Documents/Claude/Projects/`. (GitHub Desktop will look for a folder named `alum` inside it — if it's already there, it'll use the existing folder. If not, point it directly at `/Users/ronkullashi/Documents/Claude/Projects/ALUM`.)
   - Initialize with README: **uncheck** (we already have one).
   - Git ignore: leave as None (we already have a `.gitignore`).
   - License: pick **MIT** if you want, or leave None.
3. Click **Create Repository**.
4. Click **Publish repository** (top of the window).
   - **Uncheck** "Keep this code private" if you want it public, or leave it checked for private. Either works on Render.
   - Click **Publish Repository**.

Your code is now on GitHub at `https://github.com/<your-username>/alum`.

> ⚠️ Before publishing, double-check that `instance/alum.db` is not included. It contains the local SQLite database with hashed passwords. The `.gitignore` excludes it, but verify in GitHub Desktop's "Changes" tab that it's not in the file list.

---

## Step 2 — Connect Render to GitHub

1. Go to <https://dashboard.render.com>.
2. Click **New** → **Blueprint**.
3. Click **Connect GitHub** if prompted, and authorize Render to access your repos.
4. Pick the `alum` repository.
5. Render reads `render.yaml` and shows you a preview: one **Web Service** (`alum`) and one **Postgres database** (`alum-db`). Both on the **Free** plan.
6. Click **Apply**.

Render now provisions the database and starts deploying the web app. The first deploy takes 3–5 minutes.

When it's done, you'll see your URL in the dashboard (something like `https://alum-xxxx.onrender.com`).

---

## Step 3 — Seed the production database (one time)

The seed script needs to run once to create York Prep, Bronx Science, and the demo alumni. On Render:

1. In the Render dashboard, open your **alum** web service.
2. Click the **Shell** tab on the left.
3. Run: `python seed.py`
4. You'll see the same demo logins printed that you got locally.

Visit your public URL — it should look exactly like your local version, but live.

---

## Step 4 — (When you're ready) Replace seed data with real data

The seed script is for the demo. To launch with your actual school:

1. Open the Render Shell on your web service.
2. Start a Python REPL: `python`
3. Create your school:
   ```python
   from app import create_app, db
   from app.models import School, User
   app = create_app(); app.app_context().push()

   db.drop_all(); db.create_all()  # ⚠️ wipes the demo data

   york = School(slug="york-prep", name="York Prep", city="New York", state="NY")
   db.session.add(york); db.session.commit()

   admin = User(school_id=york.id, email="you@yorkprep.org",
                first_name="Your", last_name="Name", is_admin=True)
   admin.set_password("change-me-immediately")
   db.session.add(admin); db.session.commit()
   ```
4. Log in at `https://your-app.onrender.com/auth/york-prep/admin/login` and change your password (this skeleton doesn't have a password-reset UI yet — you can add one or change it via the same shell).

---

## Pushing changes after the first deploy

Anytime you (or I) update files:

1. Open GitHub Desktop. You'll see the changed files.
2. Type a short commit message in the bottom-left.
3. Click **Commit to main**.
4. Click **Push origin** at the top.

Render auto-detects the push and redeploys within a minute.

---

## Things to know about the free tier

- **Cold starts.** The web service goes to sleep after 15 minutes of no traffic. The next visitor waits ~30 seconds for it to wake up. Pay $7/mo to remove this.
- **Postgres expires after 90 days.** The free database is a trial. Set a calendar reminder; either upgrade to the $7/mo Postgres, or export and import to a fresh free DB.
- **Custom domain.** Free tier supports custom domains (e.g. `alumni.yourschool.org`) — add it under your service's Settings → Custom Domains. You'll need DNS access to point a CNAME at Render.

---

## Adding a new school (without losing data)

Existing schools, their access codes, and all user signups are **never touched** on deploy. To add a new school:

1. Open `seed.py` in a text editor (or have me do it for you).
2. Append a new tuple to the `MANHATTAN_PRIVATE_HS` list near the top:
   ```python
   ("Saint Ann's School", "saint-anns", "Brooklyn Heights",
    "Coed K–12 independent school in Brooklyn."),
   ```
   The four fields are: `(name, slug, neighborhood, description)`. The slug must be unique, lowercase, and use only letters/digits/hyphens — it appears in the URL.
3. In GitHub Desktop: Commit → Push.
4. Render auto-redeploys. Watch the Logs tab — you'll see something like:
   ```
   Added 1 new school(s)
   Saint Ann's School        4827193   admin@saint-anns.alumtest
   ```
5. The new school's code is now active. Share it with their alumni office to let them sign up. Existing schools are unchanged.

You can add as many schools as you like in one push — each gets its own random code.

---

## Finding access codes anytime

Every deploy prints the full table of schools and codes to the Logs tab. Open Render → your alum service → Logs → search for `All schools in database`. The most recent deploy's logs always have the current list.

---

## Forcing a fresh re-seed (wipes all data)

The seed normally runs only once — on first boot of an empty database. To wipe everything and re-seed (after a schema change, or to start clean), use the `ALUM_RESEED` env var:

1. In Render dashboard, open your **alum** web service → **Environment** tab.
2. Click **Add Environment Variable**.
3. Key: `ALUM_RESEED`. Value: `true`. Click **Save Changes**.
4. Saving auto-triggers a redeploy. Watch the Logs tab — you'll see "ALUM_RESEED=true — wiping the database and re-seeding." followed by the school list with new access codes.
5. **Important:** once it succeeds, go back to **Environment** and **delete** the `ALUM_RESEED` variable (or change it to `false`). Otherwise every future deploy will wipe your data.
6. The next deploy with no `ALUM_RESEED` is normal — schools persist.

The school access codes are printed in the deploy logs every time the seed runs. You can also see your school's code in the admin dashboard once you're logged in.

---

## If something breaks

- **Build fails on Render.** Open the **Logs** tab — usually a missing dependency. Tell me the error and I'll fix `requirements.txt`.
- **App crashes on first request.** Open Logs again — almost always means tables aren't created or the seed didn't run. Re-run `python seed.py` in the Shell.
- **Login doesn't work.** The session cookie needs HTTPS in production — Render gives you HTTPS by default, so this should just work. If you see a redirect loop, check that you're hitting `https://` not `http://`.
