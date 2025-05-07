from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from . import db
from .models import Patient

bp = Blueprint("main", __name__)


@bp.get("/")
def index() -> str:
    """Main landing page."""
    return render_template("index.html")


@bp.route("/patients")
def patients() -> str:
    """List all patients."""
    all_patients = Patient.query.all()
    return render_template("patient_list.html", patients=all_patients)


@bp.route("/patients/add", methods=["GET", "POST"])
def add_patient() -> str:
    """Add a new patient."""
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        birth_date_str = request.form.get("birth_date")

        # Convert birth_date to date object if provided
        birth_date = None
        if birth_date_str:
            try:
                birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Invalid date format for birth date. Please use YYYY-MM-DD format.", "danger")
                return render_template("patient_form.html")

        # Create new patient
        new_patient = Patient(
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date
        )

        db.session.add(new_patient)
        db.session.commit()

        flash("Patient added successfully.", "success")
        return redirect(url_for("main.patients"))

    return render_template("patient_form.html")


@bp.route("/patients/<int:patient_id>")
def view_patient(patient_id: int) -> str:
    """View a specific patient."""
    patient = Patient.query.get_or_404(patient_id)
    return render_template("patient_detail.html", patient=patient)


@bp.route("/patients/<int:patient_id>/edit", methods=["GET", "POST"])
def edit_patient(patient_id: int) -> str:
    """Edit a specific patient."""
    patient = Patient.query.get_or_404(patient_id)

    if request.method == "POST":
        patient.first_name = request.form.get("first_name")
        patient.last_name = request.form.get("last_name")
        birth_date_str = request.form.get("birth_date")

        # Convert birth_date to date object if provided
        if birth_date_str:
            try:
                patient.birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Invalid date format for birth date. Please use YYYY-MM-DD format.", "danger")
                return render_template("patient_form.html", patient=patient)
        else:
            patient.birth_date = None

        db.session.commit()

        flash("Patient updated successfully.", "success")
        return redirect(url_for("main.view_patient", patient_id=patient.id))

    return render_template("patient_form.html", patient=patient)


@bp.route("/patients/<int:patient_id>/delete")
def delete_patient(patient_id: int) -> str:
    """Delete a patient."""
    patient = Patient.query.get_or_404(patient_id)

    db.session.delete(patient)
    db.session.commit()

    flash("Patient deleted successfully.", "success")
    return redirect(url_for("main.patients"))
