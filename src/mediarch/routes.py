from datetime import datetime
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.exceptions import NotFound

from . import db
from .forms import LoginForm, RegistrationForm
from .models import AccountType, Patient, User

bp = Blueprint("main", __name__)


@bp.context_processor
def inject_account_types():
    """Inject AccountType enum into all templates."""
    return {"AccountType": AccountType}

# --- Role-based access control decorators ---


def role_required(role: AccountType):
    """Decorator to restrict access to routes based on user role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return abort(401)  # Unauthorized
            if current_user.account_type != role:
                return abort(403)  # Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def roles_required(roles: list[AccountType]):
    """Decorator to restrict access to routes based on a list of allowed user roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                # Or redirect to login page: return redirect(url_for('main.login', next=request.url))
                return abort(401)  # Unauthorized
            if current_user.account_type not in roles:
                return abort(403)  # Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator


admin_required = role_required(AccountType.ADMIN)
doctor_required = role_required(AccountType.DOCTOR)
patient_required = role_required(AccountType.PATIENT)
admin_or_doctor_required = roles_required([AccountType.ADMIN, AccountType.DOCTOR])

# --- End Role-based access control decorators ---


@bp.get("/")
def index() -> str:
    """Main landing page."""
    return render_template("index.html")


@bp.route("/patients")
@login_required
@admin_or_doctor_required
def patients() -> str:
    """List all patients. Accessible only by Admins and Doctors."""
    all_patients = Patient.query.all()
    return render_template("patient_list.html", patients=all_patients)


@bp.route("/patients/add", methods=["GET", "POST"])
@login_required
@admin_or_doctor_required
def add_patient() -> str:
    """Add a new patient. Accessible only by Admins and Doctors."""
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
    """View a specific patient.
    Admins and Doctors can view any patient.
    Patients can only view their own linked patient card.
    """
    patient = db.session.get(Patient, patient_id)
    if patient is None:
        raise NotFound

    if current_user.account_type in {AccountType.ADMIN, AccountType.DOCTOR}:
        # Admins and Doctors can view any patient
        pass
    elif current_user.account_type == AccountType.PATIENT:
        # Patients can only view their own card
        if current_user.patient_id != patient.id:
            abort(403)  # Forbidden
    else:
        # Should not happen if roles are correctly assigned
        abort(403)  # Forbidden

    return render_template("patient_detail.html", patient=patient)


@bp.route("/patients/<int:patient_id>/edit", methods=["GET", "POST"])
@login_required
def edit_patient(patient_id: int) -> str:
    """Edit a specific patient.
    Admins and Doctors can edit any patient.
    Patients can only edit basic information of their own linked patient card.
    """
    patient = db.session.get(Patient, patient_id)
    if patient is None:
        raise NotFound

    # Authorization checks
    can_edit_all_fields = False
    is_own_record_for_patient_user = False

    if current_user.account_type in {AccountType.ADMIN, AccountType.DOCTOR}:
        can_edit_all_fields = True
    elif current_user.account_type == AccountType.PATIENT:
        if current_user.patient_id == patient.id:
            is_own_record_for_patient_user = True
        else:
            abort(403)  # Patient trying to edit another patient's record
    else:
        abort(403)  # Unknown role or other issue

    if request.method == "POST":
        # Get common fields first
        new_first_name = request.form.get("first_name")
        new_last_name = request.form.get("last_name")

        if can_edit_all_fields:
            patient.first_name = new_first_name
            patient.last_name = new_last_name
            birth_date_str = request.form.get("birth_date")
            if birth_date_str:
                try:
                    patient.birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
                except ValueError:
                    flash("Invalid date format for birth date. Please use YYYY-MM-DD format.", "danger")
                    # Pass patient and can_edit_all_fields to template context
                    return render_template("patient_form.html", patient=patient,
                                           can_edit_all_fields=can_edit_all_fields,
                                           is_patient_editing_own=is_own_record_for_patient_user)
            else:
                patient.birth_date = None
        elif is_own_record_for_patient_user:
            # Patient can only edit their first_name and last_name
            patient.first_name = new_first_name
            patient.last_name = new_last_name
            # Any attempt to change birth_date by a patient is ignored
            if request.form.get("birth_date") != (patient.birth_date.strftime("%Y-%m-%d")
                                                  if patient.birth_date else ""):
                flash("Patients are not allowed to change their birth date. Contact an administrator.", "warning")
        else:
            # This case should have been caught by abort(403) earlier, but as a safeguard:
            abort(403)

        db.session.commit()
        flash("Patient updated successfully.", "success")
        return redirect(url_for("main.view_patient", patient_id=patient.id))

    # For GET request, pass flags to template to conditionally render fields/warnings
    return render_template("patient_form.html", patient=patient,
                           can_edit_all_fields=can_edit_all_fields,
                           is_patient_editing_own=is_own_record_for_patient_user)


@bp.route("/patients/<int:patient_id>/delete")
@login_required
@admin_required
def delete_patient(patient_id: int) -> str:
    """Delete a patient. Accessible only by Admins."""
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
        # Ensure account_type is a valid AccountType enum member
        try:
            account_type_value = form.account_type.data
            selected_account_type = AccountType(account_type_value)
        except ValueError:
            flash("Invalid account type selected.", "danger")
            return render_template("register.html", title="Register", form=form)

        user = User(
            username=form.username.data,
            email=form.email.data,
            account_type=selected_account_type,
            # First and Last names are now always required by the form
            # If we wanted to store them on the User model directly, we could add them here.
            # For now, they are primarily used for Patient record creation.
        )
        user.set_password(form.password.data)

        if selected_account_type == AccountType.PATIENT:
            # No longer need to check if form.first_name.data or form.last_name.data exist,
            # as they are DataRequired in the form itself.
            # The flash message for missing names is also removed.

            new_patient = Patient(
                first_name=form.first_name.data,  # These will be present
                last_name=form.last_name.data  # These will be present
            )
            user.patient_card = new_patient

        db.session.add(user)
        if selected_account_type == AccountType.PATIENT and 'new_patient' in locals() and new_patient not in db.session:
            db.session.add(new_patient)  # Ensure patient is added if not cascaded by user.patient_card assignment alone

        try:
            db.session.commit()
            flash("Congratulations, you are now a registered user!", "success")
            return redirect(url_for("main.login"))
        except Exception as e:  # Catch potential DB errors like unique constraints if relationships are tricky
            db.session.rollback()
            flash(f"Registration failed due to a database error: {e}. Please try again.", "danger")
            # Log the error e for admin review
            print(f"Error during registration commit: {e}")  # Basic logging

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
