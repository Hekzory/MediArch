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
        admin_user = User(username="admin", email="admin@example.com",
                          account_type=AccountType.ADMIN, is_active=True)
        admin_user.set_password("password123")
        db.session.add(admin_user)

        # Doctor User
        doctor_user = User(username="doctoruser", email="doctor@example.com",
                           account_type=AccountType.DOCTOR, is_active=True)
        doctor_user.set_password("password123")
        db.session.add(doctor_user)

        db.session.commit()

    return app


@pytest.fixture
def client(app):
    return app.test_client()


# Base class for tests
class BaseTest:
    """Base class for test scenarios."""

    def register_user(self, client, username="testuser", email="test@example.com",
                     password="password123", account_type_value=AccountType.PATIENT.value,
                     first_name="Test", last_name="User"):
        """Helper method to register a user."""
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

    def login_user(self, client, email="test@example.com", password="password123"):
        """Helper method to log in a user."""
        return client.post("/login", data={
            "email": email,
            "password": password
        }, follow_redirects=True)


class TestIndexRoute(BaseTest):
    def test_get_index_page_successfully(self, client):
        """Tests that the index page loads successfully."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"MediArch" in response.data


class TestPatientsListRoute(BaseTest):
    def test_admin_can_view_patients_list(self, client):
        """Tests that an admin can view the patients list."""
        self.login_user(client, email="admin@example.com")
        response = client.get("/patients")
        assert response.status_code == 200
        assert b"John" in response.data  # From fixture
        assert b"Doe" in response.data
        client.get("/logout")

    def test_doctor_can_view_patients_list(self, client):
        """Tests that a doctor can view the patients list."""
        self.login_user(client, email="doctor@example.com")
        response = client.get("/patients")
        assert response.status_code == 200
        assert b"John" in response.data
        assert b"Doe" in response.data
        client.get("/logout")

    def test_patient_cannot_view_patients_list(self, client):
        """Tests that a patient is forbidden from viewing the patients list."""
        self.register_user(client, username="patientuser", email="patient@example.com",
                           first_name="Pat", last_name="Ient")
        self.login_user(client, email="patient@example.com")
        response = client.get("/patients")
        assert response.status_code == 403  # Forbidden
        client.get("/logout")


class TestAddPatientRoute(BaseTest):
    def test_admin_can_add_patient(self, client):
        """Tests that an admin can add a new patient."""
        self.login_user(client, email="admin@example.com")
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

    def test_doctor_can_add_patient(self, client):
        """Tests that a doctor can add a new patient."""
        self.login_user(client, email="doctor@example.com")
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

    def test_patient_cannot_add_patient(self, client):
        """Tests that a patient is forbidden from adding a new patient."""
        self.register_user(client, username="patientadd", email="patientadd@example.com",
                           first_name="PatAdd", last_name="Test")
        self.login_user(client, email="patientadd@example.com")
        response = client.post("/patients/add", data={
            "first_name": "Try",
            "last_name": "Adding",
        }, follow_redirects=True)
        assert response.status_code == 403  # Forbidden
        client.get("/logout")


class TestViewPatientRoute(BaseTest):
    def test_admin_can_view_patient(self, client):
        """Tests that an admin can view a patient's details."""
        self.login_user(client, email="admin@example.com")
        response = client.get("/patients/1")
        assert response.status_code == 200
        assert b"John" in response.data
        assert b"Doe" in response.data
        client.get("/logout")

    def test_doctor_can_view_patient(self, client):
        """Tests that a doctor can view a patient's details."""
        self.login_user(client, email="doctor@example.com")
        response = client.get("/patients/1")
        assert response.status_code == 200
        assert b"John" in response.data
        assert b"Doe" in response.data
        client.get("/logout")

    def test_patient_can_view_own_card(self, client):
        """Tests that a patient can view their own patient card."""
        # Register a new patient user. Their patient card will be created.
        register_response = self.register_user(client, username="patientview", email="patientview@example.com",
                                            first_name="PatView", last_name="UserView")
        assert b"Congratulations, you are now a registered user!" in register_response.data

        self.login_user(client, email="patientview@example.com")

        # Find the patient ID for this new user
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
        client.get("/logout")

    def test_patient_cannot_view_another_card(self, client):
        """Tests that a patient cannot view another patient's card."""
        # Register a patient and login
        self.register_user(client, username="patientview2", email="patientview2@example.com",
                          first_name="PatView2", last_name="UserView2")
        self.login_user(client, email="patientview2@example.com")

        # Patient tries to view another patient's card (id=1, John Doe from fixture)
        response_other = client.get("/patients/1")
        assert response_other.status_code == 403  # Forbidden
        client.get("/logout")


class TestEditPatientRoute(BaseTest):
    def test_admin_can_edit_patient(self, client):
        """Tests that an admin can edit a patient's details."""
        self.login_user(client, email="admin@example.com")
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

    def test_doctor_can_edit_patient(self, client):
        """Tests that a doctor can edit a patient's details."""
        self.login_user(client, email="doctor@example.com")
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

    def test_patient_can_edit_own_card(self, client):
        """Tests that a patient can edit their own basic information."""
        self.register_user(client, username="patientedit", email="patientedit@example.com", first_name="PatEdit",
                          last_name="UserEditInitial")
        self.login_user(client, email="patientedit@example.com")

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
        client.get("/logout")

    def test_patient_cannot_edit_another_card(self, client):
        """Tests that a patient cannot edit another patient's card."""
        self.register_user(client, username="patientedit2", email="patientedit2@example.com",
                     first_name="PatEdit2", last_name="UserEdit2")
        self.login_user(client, email="patientedit2@example.com")

        # Patient tries to edit another patient's card (id=1)
        response_patient_other_edit = client.post("/patients/1/edit", data={
            "first_name": "AttemptHack",
            "last_name": "AttemptHack"
        }, follow_redirects=True)
        assert response_patient_other_edit.status_code == 403  # Forbidden
        client.get("/logout")


class TestDeletePatientRoute(BaseTest):
    def test_admin_can_delete_patient(self, client):
        """Tests that an admin can delete a patient."""
        self.login_user(client, email="admin@example.com")

        # Add a patient specifically for deletion
        add_response = client.post("/patients/add", data={
            "first_name": "ToDelete",
            "last_name": "ByAdmin",
            "birth_date": "2000-01-01"
        }, follow_redirects=True)
        assert add_response.status_code == 200
        assert b"Patient added successfully" in add_response.data

        # Find the ID of the newly added patient "ToDelete ByAdmin"
        patient_to_delete_id = None
        with client.application.app_context():
            # Assuming last names are unique enough for this test scenario
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
        client.get("/logout")

    def test_doctor_cannot_delete_patient(self, client):
        """Tests that a doctor cannot delete a patient."""
        self.login_user(client, email="doctor@example.com")
        delete_response_doctor = client.get("/patients/1/delete", follow_redirects=True)
        assert delete_response_doctor.status_code == 403  # Forbidden

        # Verify patient 1 still exists
        detail_response_doc_check = client.get("/patients/1")
        assert detail_response_doc_check.status_code == 200
        assert b"John" in detail_response_doc_check.data
        assert b"Doe" in detail_response_doc_check.data
        client.get("/logout")

    def test_patient_cannot_delete_patient(self, client):
        """Tests that a patient cannot delete a patient record."""
        self.register_user(client, username="patientdelete", email="patientdelete@example.com",
                     first_name="PatDel", last_name="UserDel")
        self.login_user(client, email="patientdelete@example.com")

        delete_response_patient = client.get("/patients/1/delete", follow_redirects=True)
        assert delete_response_patient.status_code == 403  # Forbidden
        client.get("/logout")

        # Verify patient 1 still exists (need to login as admin to check)
        self.login_user(client, email="admin@example.com")
        detail_response_admin_check = client.get("/patients/1")
        assert detail_response_admin_check.status_code == 200
        client.get("/logout")


class TestAdminToggleUserActiveRoute(BaseTest):
    def test_admin_can_activate_user(self, client, app):
        """Tests that an admin can activate an inactive user."""
        # Create an inactive doctor user
        with app.app_context():
            doctor_for_toggle = User(username="toggledoctor", email="toggle@doctor.com",
                                    account_type=AccountType.DOCTOR, is_active=False)
            doctor_for_toggle.set_password("password123")
            db.session.add(doctor_for_toggle)
            db.session.commit()
            user_to_toggle_id = doctor_for_toggle.id

        self.login_user(client, email="admin@example.com", password="password123")

        # Check initial state (inactive)
        with app.app_context():
            user_toggled = db.session.get(User, user_to_toggle_id)
            assert user_toggled is not None
            assert not user_toggled.is_active

        # Toggle to active
        response_activate = client.post(f"/admin/users/{user_to_toggle_id}/toggle_active", follow_redirects=True)
        assert response_activate.status_code == 200
        assert b"User toggledoctor has been activated." in response_activate.data

        with app.app_context():
            user_toggled = db.session.get(User, user_to_toggle_id)
            assert user_toggled.is_active

        client.get("/logout")

    def test_admin_can_deactivate_user(self, client, app):
        """Tests that an admin can deactivate an active user."""
        # Create an active doctor user
        with app.app_context():
            doctor_for_toggle = User(username="toggledoctor2", email="toggle2@doctor.com",
                                    account_type=AccountType.DOCTOR, is_active=True)
            doctor_for_toggle.set_password("password123")
            db.session.add(doctor_for_toggle)
            db.session.commit()
            user_to_toggle_id = doctor_for_toggle.id

        self.login_user(client, email="admin@example.com", password="password123")

        # Toggle to inactive
        response_deactivate = client.post(f"/admin/users/{user_to_toggle_id}/toggle_active", follow_redirects=True)
        assert response_deactivate.status_code == 200
        assert b"User toggledoctor2 has been deactivated." in response_deactivate.data

        with app.app_context():
            user_toggled = db.session.get(User, user_to_toggle_id)
            assert not user_toggled.is_active

        client.get("/logout")

    def test_admin_cannot_toggle_nonexistent_user(self, client):
        """Tests that an error is shown when trying to toggle a non-existent user."""
        self.login_user(client, email="admin@example.com", password="password123")

        non_existent_user_id = 99999
        response_toggle_non_existent = client.post(f"/admin/users/{non_existent_user_id}/toggle_active",
                                                follow_redirects=True)
        assert response_toggle_non_existent.status_code == 200  # Redirects to user list
        assert b"User with ID 99999 not found." in response_toggle_non_existent.data

        client.get("/logout")


class TestAdminDashboardRoute(BaseTest):
    def test_admin_can_access_dashboard(self, client):
        """Tests that an admin can access the admin dashboard."""
        self.login_user(client, email="admin@example.com", password="password123")
        response = client.get("/admin")
        assert response.status_code == 200
        assert b"Admin Dashboard" in response.data
        client.get("/logout")

    def test_doctor_cannot_access_dashboard(self, client):
        """Tests that a doctor cannot access the admin dashboard."""
        self.login_user(client, email="doctor@example.com", password="password123")
        response = client.get("/admin")
        assert response.status_code == 403
        client.get("/logout")

    def test_patient_cannot_access_dashboard(self, client):
        """Tests that a patient cannot access the admin dashboard."""
        self.register_user(client, username="patientdash", email="patientdash@example.com",
                    account_type_value=AccountType.PATIENT.value)
        self.login_user(client, email="patientdash@example.com", password="password123")
        response = client.get("/admin")
        assert response.status_code == 403
        client.get("/logout")

    def test_unauthenticated_user_redirected_from_dashboard(self, client):
        """Tests that an unauthenticated user is redirected from the admin dashboard."""
        response = client.get("/admin")
        assert response.status_code == 302  # Redirects to login
        assert b"Redirecting..." in response.data


class TestAdminListUsersRoute(BaseTest):
    def test_admin_can_list_users(self, client):
        """Tests that an admin can list all users."""
        self.login_user(client, email="admin@example.com", password="password123")
        response = client.get("/admin/users")
        assert response.status_code == 200
        assert b"admin@example.com" in response.data
        assert b"doctor@example.com" in response.data
        client.get("/logout")

    def test_doctor_cannot_list_users(self, client):
        """Tests that a doctor cannot list users."""
        self.login_user(client, email="doctor@example.com", password="password123")
        response = client.get("/admin/users")
        assert response.status_code == 403
        client.get("/logout")

    def test_patient_cannot_list_users(self, client):
        """Tests that a patient cannot list users."""
        self.register_user(client, username="patientlist", email="patientlist@example.com",
                    account_type_value=AccountType.PATIENT.value)
        self.login_user(client, email="patientlist@example.com", password="password123")
        response = client.get("/admin/users")
        assert response.status_code == 403
        client.get("/logout")

    def test_unauthenticated_user_redirected_from_list_users(self, client):
        """Tests that an unauthenticated user is redirected from the user list page."""
        response = client.get("/admin/users")
        assert response.status_code == 302  # Redirects to login
        assert b"Redirecting..." in response.data


class TestAdminEditUserRoute(BaseTest):
    def test_admin_can_edit_user_details(self, client, app):
        """Tests that an admin can successfully edit a user's details."""
        # Create a user to be edited
        with app.app_context():
            user_to_edit = User(username="editme", email="editme@example.com",
                                account_type=AccountType.PATIENT, is_active=False)
            user_to_edit.set_password("password123")
            db.session.add(user_to_edit)
            db.session.commit()
            user_id = user_to_edit.id

        self.login_user(client, email="admin@example.com", password="password123")

        edit_data = {
            "username": "editeduser",
            "email": "edited@example.com",
            "account_type": AccountType.DOCTOR.value,
            "is_active": "true"  # Form value for True
        }
        response = client.post(f"/admin/users/{user_id}/edit", data=edit_data, follow_redirects=True)

        assert response.status_code == 200
        assert b"User updated successfully." in response.data

        # Verify changes in the database
        with app.app_context():
            edited_user = db.session.get(User, user_id)
            assert edited_user is not None
            assert edited_user.username == "editeduser"
            assert edited_user.email == "edited@example.com"
            assert edited_user.account_type == AccountType.DOCTOR
            assert edited_user.is_active is True

        client.get("/logout")

    def test_admin_can_change_user_password(self, client, app):
        """Tests that an admin can change a user's password."""
        with app.app_context():
            user_to_edit = User(username="passchangeuser", email="passchange@example.com",
                                account_type=AccountType.PATIENT, is_active=True)
            user_to_edit.set_password("oldpassword")
            db.session.add(user_to_edit)
            db.session.commit()
            user_id = user_to_edit.id

        self.login_user(client, email="admin@example.com", password="password123")

        edit_data = {
            "username": "passchangeuser",  # Must provide other fields too
            "email": "passchange@example.com",
            "account_type": AccountType.PATIENT.value,
            "is_active": "true",
            "password": "newstrongpassword"
        }
        response = client.post(f"/admin/users/{user_id}/edit", data=edit_data, follow_redirects=True)

        assert response.status_code == 200
        assert b"User updated successfully." in response.data
        assert b"Password updated." in response.data

        # Verify password change by trying to log in with the new password
        with app.app_context():
            updated_user = db.session.get(User, user_id)
            assert updated_user.check_password("newstrongpassword") is True
            assert updated_user.check_password("oldpassword") is False

        client.get("/logout")

    def test_admin_cannot_edit_nonexistent_user(self, client):
        """Tests that an admin sees an error when trying to edit a non-existent user."""
        self.login_user(client, email="admin@example.com", password="password123")

        non_existent_user_id = 99999
        edit_data = {
            "username": "ghost",
            "email": "ghost@example.com",
            "account_type": AccountType.PATIENT.value,
            "is_active": "true"
        }
        response = client.post(f"/admin/users/{non_existent_user_id}/edit", data=edit_data, follow_redirects=True)

        assert response.status_code == 200  # Should redirect to admin_list_users
        assert b"User with ID 99999 not found." in response.data

        client.get("/logout")

    def test_doctor_cannot_access_admin_edit_user_page(self, client, app):
        """Tests that a doctor cannot access the admin edit user page (GET or POST)."""
        with app.app_context():
            # Create a user that could be edited if permissions allowed
            test_user = User(username="testedit", email="testedit@example.com",
                             account_type=AccountType.PATIENT, is_active=True)
            test_user.set_password("password123")
            db.session.add(test_user)
            db.session.commit()
            user_id_to_try_edit = test_user.id

        # Login as Doctor
        self.login_user(client, email="doctor@example.com", password="password123")

        # Attempt GET request
        response_get = client.get(f"/admin/users/{user_id_to_try_edit}/edit")
        assert response_get.status_code == 403  # Forbidden

        # Attempt POST request
        edit_data = {
            "username": "hacked",
            "email": "hacked@example.com",
            "account_type": AccountType.PATIENT.value,
            "is_active": "true"
        }
        response_post = client.post(f"/admin/users/{user_id_to_try_edit}/edit", data=edit_data, follow_redirects=True)
        assert response_post.status_code == 403  # Forbidden

        client.get("/logout")

    def test_patient_cannot_access_admin_edit_user_page(self, client, app):
        """Tests that a patient cannot access the admin edit user page (GET or POST)."""
        with app.app_context():
            # Create a user that could be edited if permissions allowed
            user_id_to_try_edit = User.query.filter_by(username="admin").first().id  # Try to edit admin

        # Register and Login as Patient
        self.register_user(client, username="patientaccess", email="patientaccess@example.com",
                           first_name="Pat", last_name="Acc")
        self.login_user(client, email="patientaccess@example.com", password="password123")

        # Attempt GET request
        response_get = client.get(f"/admin/users/{user_id_to_try_edit}/edit")
        assert response_get.status_code == 403  # Forbidden

        # Attempt POST request
        edit_data = {
            "username": "hackedpatient",
            "email": "hackedpatient@example.com",
            "account_type": AccountType.ADMIN.value,
            "is_active": "true"
        }
        response_post = client.post(f"/admin/users/{user_id_to_try_edit}/edit", data=edit_data, follow_redirects=True)
        assert response_post.status_code == 403  # Forbidden

        client.get("/logout")

    def test_admin_edit_user_with_invalid_account_type(self, client, app):
        """Tests submitting an invalid account type when admin edits a user."""
        with app.app_context():
            user_to_edit = User(username="invalidtypeuser", email="invalidtype@example.com",
                                account_type=AccountType.PATIENT, is_active=True)
            user_to_edit.set_password("password123")
            db.session.add(user_to_edit)
            db.session.commit()
            user_id = user_to_edit.id

        self.login_user(client, email="admin@example.com", password="password123")

        edit_data = {
            "username": "invalidtypeuser",
            "email": "invalidtype@example.com",
            "account_type": "INVALID_TYPE_STRING",
            "is_active": "true"
        }
        response = client.post(f"/admin/users/{user_id}/edit", data=edit_data, follow_redirects=True)

        assert response.status_code == 200  # Stays on the form page
        assert b"Invalid account type selected." in response.data
        assert b"User updated successfully." not in response.data

        # Verify account type was not changed
        with app.app_context():
            user_after_attempt = db.session.get(User, user_id)
            assert user_after_attempt.account_type == AccountType.PATIENT

        client.get("/logout")


class TestLoginRedirectRoute(BaseTest):
    def test_authenticated_user_redirected_from_login(self, client):
        """Tests that an authenticated user is redirected from the login page."""
        # Log in an admin user
        self.login_user(client, email="admin@example.com", password="password123")

        # Attempt to access the login page
        response = client.get("/login", follow_redirects=False)
        assert response.status_code == 302
        assert response.location == "/"  # Should redirect to index

        response_followed = client.get("/login", follow_redirects=True)
        assert response_followed.status_code == 200
        assert b"MediArch" in response_followed.data  # Index page content
        assert b"Login" not in response_followed.data  # Should not be on login page
        client.get("/logout")
