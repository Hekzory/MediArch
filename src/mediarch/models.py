import enum
from datetime import date

from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from . import db


class AccountType(enum.Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    PATIENT = "patient"


class BloodType(enum.Enum):
    A_POSITIVE = "A+"
    A_NEGATIVE = "A-"
    B_POSITIVE = "B+"
    B_NEGATIVE = "B-"
    AB_POSITIVE = "AB+"
    AB_NEGATIVE = "AB-"
    O_POSITIVE = "O+"
    O_NEGATIVE = "O-"
    UNKNOWN = "Unknown"


class Patient(db.Model):
    """Patient medical record data."""

    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(nullable=False)
    last_name: Mapped[str] = mapped_column(nullable=False)
    birth_date: Mapped[date | None]

    # Medical information
    blood_type: Mapped[BloodType | None] = mapped_column(db.Enum(BloodType), nullable=True)
    allergies: Mapped[str | None] = mapped_column(db.Text, nullable=True)  # Using Text for potentially longer entries
    medical_conditions: Mapped[str | None] = mapped_column(db.Text, nullable=True)
    medications: Mapped[str | None] = mapped_column(db.Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(db.Text, nullable=True)  # General medical notes

    # The relationship is now primarily defined by User.patient_id
    user_account: Mapped["User | None"] = relationship(back_populates="patient_card", uselist=False)

    # Add more medical-record fields later (blood_type, notes, …)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Patient {self.id} – {self.last_name}, {self.first_name}>"


class User(UserMixin, db.Model):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    account_type: Mapped[AccountType] = mapped_column(default=AccountType.PATIENT, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # A user (if they are a patient) can be linked to their patient card
    # This patient_id refers to the id in the 'patients' table.
    patient_id: Mapped[int | None] = mapped_column(db.ForeignKey("patients.id"), unique=True, nullable=True)
    patient_card: Mapped["Patient | None"] = relationship(back_populates="user_account", foreign_keys=[patient_id],
                                                          uselist=False)

    def set_password(self, password: str) -> None:
        """Hashes and sets the password for the user."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Checks if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_globally_active(self) -> bool:
        """Determines if user account is active. The 'admin' user is always active."""
        if self.username == "admin":
            return True
        return self.is_active

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.account_type.value})>"
