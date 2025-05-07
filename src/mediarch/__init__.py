import os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db: SQLAlchemy = SQLAlchemy()
login_manager = LoginManager()

# Default – overridden in prod by a DATABASE_URL env-var.
DEFAULT_DB_URI = (
    os.getenv("DATABASE_URL")
    or "postgresql+psycopg://mediarch:mediarch@localhost/mediarch"
)


def create_app(test_config=None) -> Flask:
    """Application factory.

    Args:
        test_config: Optional configuration dictionary for testing
    """
    app = Flask(__name__, template_folder="templates")
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "CHANGE-ME"),  # rotate in prod!
        SQLALCHEMY_DATABASE_URI=DEFAULT_DB_URI,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        # Consider adding other security-related configurations here, e.g.:
        # SESSION_COOKIE_SECURE=True,
        # SESSION_COOKIE_HTTPONLY=True,
        # SESSION_COOKIE_SAMESITE='Lax',
        # REMEMBER_COOKIE_SECURE=True,
        # REMEMBER_COOKIE_HTTPONLY=True,
        # REMEMBER_COOKIE_SAMESITE='Lax',
    )

    # Override config with test config if provided
    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "main.login"  # The route name for the login page
    login_manager.login_message_category = "info"  # Optional: category for flash messages

    from .models import User  # noqa: PLC0415

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        """Load user by ID for Flask-Login."""
        return db.session.get(User, int(user_id))

    from .routes import bp as main_bp  # noqa: PLC0415
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()

    return app
