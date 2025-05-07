import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db: SQLAlchemy = SQLAlchemy()

# Default – overridden in prod by a DATABASE_URL env-var.
DEFAULT_DB_URI = (
    os.getenv("DATABASE_URL")                       # e.g. set by Heroku / Fly.io
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
    )

    # Override config with test config if provided
    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    from .routes import bp as main_bp  # noqa: PLC0415
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()

    return app
