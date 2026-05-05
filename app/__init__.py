"""App factory. Wires up Flask, SQLAlchemy, Flask-Login, and the blueprints.

Database selection:
  - If env var DATABASE_URL is set (Render, Heroku, etc.) -> use it (Postgres).
  - Otherwise -> local SQLite at instance/alum.db.

Secret key:
  - In production, ALUM_SECRET (or SECRET_KEY) must be set.
  - In development, falls back to a default so you can boot quickly.
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()


def _resolve_db_uri(app):
    url = os.environ.get("DATABASE_URL")
    if url:
        # Render still hands out the legacy postgres:// scheme; SQLAlchemy 2
        # requires postgresql://.
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url
    return "sqlite:///" + os.path.join(app.instance_path, "alum.db")


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Make sure instance/ exists for the SQLite file (no-op on Postgres).
    os.makedirs(app.instance_path, exist_ok=True)

    secret = os.environ.get("ALUM_SECRET") or os.environ.get("SECRET_KEY")
    if not secret:
        if os.environ.get("RENDER") or os.environ.get("FLASK_ENV") == "production":
            raise RuntimeError(
                "Set ALUM_SECRET (or SECRET_KEY) in production. "
                "On Render, the render.yaml auto-generates this."
            )
        secret = "dev-secret-change-me"

    app.config.update(
        SECRET_KEY=secret,
        SQLALCHEMY_DATABASE_URI=_resolve_db_uri(app),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    db.init_app(app)
    login_manager.init_app(app)
    # When a @login_required view is hit while logged out, send the user to
    # the code-entry landing page. They'll enter the school code, get to the
    # gateway, and pick "Log in" from there.
    login_manager.login_view = "main.landing"

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Blueprints
    from .main import bp as main_bp
    from .auth import bp as auth_bp
    from .alumni import bp as alumni_bp
    from .groups import bp as groups_bp
    from .messages import bp as messages_bp
    from .admin import bp as admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(alumni_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(admin_bp)

    # Create tables on first run if they don't exist.
    with app.app_context():
        db.create_all()

    return app
