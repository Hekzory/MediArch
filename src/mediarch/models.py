from datetime import date

from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import check_password_hash, generate_password_hash

from . import db


class Patient(db.Model):
    """Very simple patient model (extend later)."""

    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(nullable=False)
    last_name: Mapped[str] = mapped_column(nullable=False)
    birth_date: Mapped[date | None]
    # Add more medical-record fields later (blood_type, notes, …)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Patient {self.id} – {self.last_name}, {self.first_name}>"


class User(UserMixin, db.Model):
    """User model for authentication."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(nullable=False)

    def set_password(self, password: str) -> None:
        """Hashes and sets the password for the user."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Checks if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.username}>"
