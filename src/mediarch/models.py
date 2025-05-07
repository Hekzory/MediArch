from datetime import date

from sqlalchemy.orm import Mapped, mapped_column

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
