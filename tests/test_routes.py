import pytest

from mediarch import create_app, db
from mediarch.models import AccountType, Patient, User


@pytest.fixture
def app():
    # Pass test configuration when creating the app
    app = create_app(test_config={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,  # Disable CSRF for testing forms
        "SECRET_KEY": "test_secret_key",  # Required for session management
        "LOGIN_DISABLED": False  # Ensure login is not disabled by default for these tests
    })

    with app.app_context():
        db.create_all()

        # Patient record (unlinked to a user initially, for admin/doctor interaction)
        # Explicitly set id for predictability in tests
        patient1 = Patient(id=1, first_name="John", last_name="Doe", birth_date=None)
        db.session.add(patient1)

        # Admin User
        admin_user = User(username="adminuser", email="admin@example.com", account_type=AccountType.ADMIN)
        admin_user.set_password("password123")
        db.session.add(admin_user)

        # Doctor User
        doctor_user = User(username="doctoruser", email="doctor@example.com", account_type=AccountType.DOCTOR)
        doctor_user.set_password("password123")
        db.session.add(doctor_user)

        db.session.commit()

    return app


@pytest.fixture
def client(app):
    return app.test_client()


# Updated register_user helper to support account types and patient-specific fields
def register_user(client, username="testuser", email="test@example.com", password="password123",
                  account_type_value=AccountType.PATIENT.value, first_name="Test", last_name="User"):
    """Helper function to register a user."""
    data = {
        "username": username,
        "email": email,
        "password": password,
        "confirm_password": password,
        "account_type": account_type_value
    }
    # Add first_name and last_name only if registering a patient
    if account_type_value == AccountType.PATIENT.value:
        if first_name:  # Ensure not to send empty strings if None was intended, though form expects them.
            data["first_name"] = first_name
        if last_name:
            data["last_name"] = last_name

    return client.post("/register", data=data, follow_redirects=True)


def login_user(client, email="test@example.com", password="password123"):
    """Helper function to log in a user."""
    return client.post("/login", data={
        "email": email,
        "password": password
    }, follow_redirects=True)


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"MediArch" in response.data


def test_patients_list(client):
    # Test with Admin
    login_user(client, email="admin@example.com")
    response = client.get("/patients")
    assert response.status_code == 200
    assert b"John" in response.data  # From fixture
    assert b"Doe" in response.data
    client.get("/logout")  # Logout admin

    # Test with Doctor
    login_user(client, email="doctor@example.com")
    response = client.get("/patients")
    assert response.status_code == 200
    assert b"John" in response.data
    assert b"Doe" in response.data
    client.get("/logout")  # Logout doctor

    # Test with Patient (should be forbidden)
    register_user(client, username="patientuser", email="patient@example.com", first_name="Pat", last_name="Ient")
    login_user(client, email="patient@example.com")
    response = client.get("/patients")
    assert response.status_code == 403  # Forbidden
    client.get("/logout")


def test_add_patient(client):
    # Test with Admin
    login_user(client, email="admin@example.com")
    response = client.post("/patients/add", data={
        "first_name": "JaneAdmin",
        "last_name": "SmithAdmin",
        "birth_date": "1990-01-01"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Patient added successfully" in response.data
    assert b"JaneAdmin" in response.data
    assert b"SmithAdmin" in response.data
    # Verify in list
    list_response = client.get("/patients")
    assert b"JaneAdmin" in list_response.data
    client.get("/logout")

    # Test with Doctor
    login_user(client, email="doctor@example.com")
    response = client.post("/patients/add", data={
        "first_name": "JaneDoctor",
        "last_name": "SmithDoctor",
        "birth_date": "1991-02-02"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Patient added successfully" in response.data
    assert b"JaneDoctor" in response.data
    assert b"SmithDoctor" in response.data
    list_response = client.get("/patients")
    assert b"JaneDoctor" in list_response.data
    client.get("/logout")

    # Test with Patient (should be forbidden)
    register_user(client, username="patientadd", email="patientadd@example.com", first_name="PatAdd", last_name="Test")
    login_user(client, email="patientadd@example.com")
    response = client.post("/patients/add", data={
        "first_name": "Try",
        "last_name": "Adding",
    }, follow_redirects=True)
    assert response.status_code == 403  # Forbidden
    client.get("/logout")


def test_view_patient(client):
    # Test with Admin viewing fixture patient (id=1)
    login_user(client, email="admin@example.com")
    response = client.get("/patients/1")
    assert response.status_code == 200
    assert b"John" in response.data
    assert b"Doe" in response.data
    client.get("/logout")

    # Test with Doctor viewing fixture patient (id=1)
    login_user(client, email="doctor@example.com")
    response = client.get("/patients/1")
    assert response.status_code == 200
    assert b"John" in response.data
    assert b"Doe" in response.data
    client.get("/logout")

    # Test with Patient viewing their own card and another card
    # Register a new patient user. Their patient card will be created.
    register_response = register_user(client, username="patientview", email="patientview@example.com",
                                      first_name="PatView", last_name="UserView")
    assert b"Congratulations, you are now a registered user!" in register_response.data

    login_user(client, email="patientview@example.com")

    # Find the patient ID for this new user
    # This is a bit indirect. A better way would be to query the DB or have register_user return it.
    # For now, assume they are the latest user and patient card.
    with client.application.app_context():
        patient_user = User.query.filter_by(email="patientview@example.com").first()
        assert patient_user is not None
        assert patient_user.patient_id is not None
        own_patient_id = patient_user.patient_id
        # Ensure the patient card exists and has the correct name
        own_patient_card = db.session.get(Patient, own_patient_id)
        assert own_patient_card is not None
        assert own_patient_card.first_name == "PatView"

    # Patient views their own card
    response_own = client.get(f"/patients/{own_patient_id}")
    assert response_own.status_code == 200
    assert b"PatView" in response_own.data
    assert b"UserView" in response_own.data

    # Patient tries to view another patient's card (id=1, John Doe from fixture)
    response_other = client.get("/patients/1")
    assert response_other.status_code == 403  # Forbidden
    client.get("/logout")


def test_edit_patient(client):
    # Test with Admin editing fixture patient (id=1)
    login_user(client, email="admin@example.com")
    response_admin_edit = client.post("/patients/1/edit", data={
        "first_name": "JohnAdminEdited",
        "last_name": "DoeAdminEdited",
        "birth_date": "1985-05-15"
    }, follow_redirects=True)
    assert response_admin_edit.status_code == 200
    assert b"Patient updated successfully" in response_admin_edit.data
    # Verify data in detail view
    detail_response = client.get("/patients/1")
    assert b"JohnAdminEdited" in detail_response.data
    assert b"DoeAdminEdited" in detail_response.data
    assert b"1985-05-15" in detail_response.data  # Assuming format is YYYY-MM-DD in detail view
    client.get("/logout")

    # Test with Doctor editing fixture patient (id=1, previously edited by admin)
    login_user(client, email="doctor@example.com")
    response_doctor_edit = client.post("/patients/1/edit", data={
        "first_name": "JohnDoctorEdited",
        "last_name": "DoeDoctorEdited",
        "birth_date": "1986-06-16"
    }, follow_redirects=True)
    assert response_doctor_edit.status_code == 200
    assert b"Patient updated successfully" in response_doctor_edit.data
    detail_response_doc = client.get("/patients/1")
    assert b"JohnDoctorEdited" in detail_response_doc.data
    assert b"DoeDoctorEdited" in detail_response_doc.data
    assert b"1986-06-16" in detail_response_doc.data
    client.get("/logout")

    # Test with Patient editing their own card
    register_user(client, username="patientedit", email="patientedit@example.com", first_name="PatEdit",
                  last_name="UserEditInitial")
    login_user(client, email="patientedit@example.com")

    with client.application.app_context():
        patient_user = User.query.filter_by(email="patientedit@example.com").first()
        own_patient_id = patient_user.patient_id
        original_patient_card = db.session.get(Patient, own_patient_id)
        original_birth_date_str = original_patient_card.birth_date.strftime("%Y-%m-%d") \
                                  if original_patient_card.birth_date else ""

    # Patient edits own basic info (first, last name) and attempts to change birth_date
    response_patient_own_edit = client.post(f"/patients/{own_patient_id}/edit", data={
        "first_name": "PatEdited",
        "last_name": "UserEditedFinal",
        "birth_date": "2000-01-01"  # Attempt to change birth date
    }, follow_redirects=True)
    assert response_patient_own_edit.status_code == 200
    assert b"Patient updated successfully" in response_patient_own_edit.data
    # Check if warning about birth date change was flashed (optional, depends on exact flash message)
    assert b"Patients are not allowed to change their birth date" in response_patient_own_edit.data

    detail_response_patient = client.get(f"/patients/{own_patient_id}")
    assert b"PatEdited" in detail_response_patient.data
    assert b"UserEditedFinal" in detail_response_patient.data
    # Verify birth_date was NOT changed
    if original_birth_date_str:
        assert original_birth_date_str.encode() in detail_response_patient.data
    else:  # If original birth date was None, it should remain effectively None or empty in display
        # This check depends on how None birth_date is rendered. Assuming it's not "2000-01-01"
        assert b"2000-01-01" not in detail_response_patient.data

    # Patient tries to edit another patient's card (id=1)
    response_patient_other_edit = client.post("/patients/1/edit", data={
        "first_name": "AttemptHack",
        "last_name": "AttemptHack"
    }, follow_redirects=True)
    assert response_patient_other_edit.status_code == 403  # Forbidden
    client.get("/logout")


def test_delete_patient(client):
    # Add a patient specifically for deletion by Admin
    login_user(client, email="admin@example.com")
    add_response = client.post("/patients/add", data={
        "first_name": "ToDelete",
        "last_name": "ByAdmin",
        "birth_date": "2000-01-01"
    }, follow_redirects=True)
    assert add_response.status_code == 200
    assert b"Patient added successfully" in add_response.data

    # Find the ID of the newly added patient "ToDelete ByAdmin"
    # This requires inspecting the database state or parsing HTML, which can be brittle.
    # A more robust way is to query the DB directly within app_context.
    patient_to_delete_id = None
    with client.application.app_context():
        # Assuming last names are unique enough for this test scenario
        # Or find by combination of first/last name
        added_patient = Patient.query.filter_by(first_name="ToDelete", last_name="ByAdmin").first()
        assert added_patient is not None, "Patient 'ToDelete ByAdmin' was not found after adding."
        patient_to_delete_id = added_patient.id

    assert patient_to_delete_id is not None, "Could not retrieve ID for patient 'ToDelete ByAdmin'"

    # Admin deletes the patient they just added
    delete_response_admin = client.get(f"/patients/{patient_to_delete_id}/delete", follow_redirects=True)
    assert delete_response_admin.status_code == 200
    assert b"Patient deleted successfully" in delete_response_admin.data
    # Verify the patient is no longer in the list or accessible
    list_response_admin = client.get("/patients")
    assert b"ToDelete" not in list_response_admin.data
    assert b"ByAdmin" not in list_response_admin.data
    detail_response_admin = client.get(f"/patients/{patient_to_delete_id}")
    assert detail_response_admin.status_code == 404  # Should be Not Found after deletion
    client.get("/logout")  # Logout Admin

    # Doctor tries to delete fixture patient (id=1) - should be forbidden
    login_user(client, email="doctor@example.com")
    delete_response_doctor = client.get("/patients/1/delete", follow_redirects=True)
    assert delete_response_doctor.status_code == 403  # Forbidden
    # Verify patient 1 still exists
    detail_response_doc_check = client.get("/patients/1")
    assert detail_response_doc_check.status_code == 200
    # Patient 1 should have its original fixture name "John Doe",
    # as database state is reset for each test function.
    assert b"John Doe" in detail_response_doc_check.data
    client.get("/logout")  # Logout Doctor

    # Patient tries to delete fixture patient (id=1) - should be forbidden
    register_user(client, username="patientdelete", email="patientdelete@example.com",
                  first_name="PatDel", last_name="UserDel")
    login_user(client, email="patientdelete@example.com")
    delete_response_patient = client.get("/patients/1/delete", follow_redirects=True)
    assert delete_response_patient.status_code == 403  # Forbidden
    # Verify patient 1 still exists
    # Need to login as admin/doctor to check patient 1 again, or ensure patient login doesn't affect it.
    # For simplicity, assume patient 1 still exists and check after logging out patient and logging in admin.
    client.get("/logout")
    login_user(client, email="admin@example.com")
    detail_response_admin_check = client.get("/patients/1")
    assert detail_response_admin_check.status_code == 200
    client.get("/logout")
