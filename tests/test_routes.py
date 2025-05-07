import pytest

from mediarch import create_app, db
from mediarch.models import Patient


@pytest.fixture
def app():
    # Pass test configuration when creating the app to avoid PostgreSQL connection
    app = create_app(test_config={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })

    with app.app_context():
        db.create_all()

        # Add test data
        test_patient = Patient(first_name="John", last_name="Doe")
        db.session.add(test_patient)
        db.session.commit()

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"MediArch" in response.data


def test_patients_list(client):
    response = client.get("/patients")
    assert response.status_code == 200
    assert b"John" in response.data
    assert b"Doe" in response.data


def test_add_patient(client):
    response = client.post("/patients/add", data={
        "first_name": "Jane",
        "last_name": "Smith",
        "birth_date": "1990-01-01"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Patient added successfully" in response.data
    assert b"Jane" in response.data
    assert b"Smith" in response.data


def test_view_patient(client):
    # Get the first patient (John Doe from fixture)
    response = client.get("/patients/1")
    assert response.status_code == 200
    assert b"John" in response.data
    assert b"Doe" in response.data


def test_edit_patient(client):
    response = client.post("/patients/1/edit", data={
        "first_name": "Johnny",
        "last_name": "Doeson",
        "birth_date": "1985-05-15"
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Patient updated successfully" in response.data
    assert b"Johnny" in response.data
    assert b"Doeson" in response.data


def test_delete_patient(client):
    # First add a patient to delete
    client.post("/patients/add", data={
        "first_name": "Deleter",
        "last_name": "Me",
    })

    # Get all patients to find the ID of the new patient
    response = client.get("/patients")
    assert b"Deleter" in response.data

    # Delete the patient (assuming it's ID 2)
    response = client.get("/patients/2/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"Patient deleted successfully" in response.data

    # Verify the patient is no longer in the list
    response = client.get("/patients")
    assert b"Deleter" not in response.data
