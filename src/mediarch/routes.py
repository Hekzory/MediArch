from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.exceptions import NotFound

from . import db
from .forms import LoginForm, RegistrationForm
from .models import Patient, User

bp = Blueprint("main", __name__)


@bp.get("/")
def index() -> str:
    """Main landing page."""
    return render_template("index.html")


@bp.route("/patients")
@login_required
def patients() -> str:
    """List all patients."""
    all_patients = Patient.query.all()
    return render_template("patient_list.html", patients=all_patients)


@bp.route("/patients/add", methods=["GET", "POST"])
@login_required
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
@login_required
def view_patient(patient_id: int) -> str:
    """View a specific patient."""
    patient = db.session.get(Patient, patient_id)
    if patient is None:
        raise NotFound
    return render_template("patient_detail.html", patient=patient)


@bp.route("/patients/<int:patient_id>/edit", methods=["GET", "POST"])
@login_required
def edit_patient(patient_id: int) -> str:
    """Edit a specific patient."""
    patient = db.session.get(Patient, patient_id)
    if patient is None:
        raise NotFound

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
@login_required
def delete_patient(patient_id: int) -> str:
    """Delete a patient."""
    patient = db.session.get(Patient, patient_id)
    if patient is None:
        raise NotFound

    db.session.delete(patient)
    db.session.commit()

    flash("Patient deleted successfully.", "success")
    return redirect(url_for("main.patients"))


@bp.route("/register", methods=["GET", "POST"])
def register() -> str:
    """Handle user registration."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Congratulations, you are now a registered user! Please log in.", "success")
        return redirect(url_for("main.login"))
    return render_template("register.html", title="Register", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login() -> str:
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("main.login"))
        login_user(user)
        flash("Login successful.", "success")
        # Redirect to the next page if it exists, otherwise to the index
        next_page = request.args.get("next")
        return redirect(next_page or url_for("main.index"))
    return render_template("login.html", title="Login", form=form)


@bp.route("/logout")
@login_required
def logout() -> str:
    """Handle user logout."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
