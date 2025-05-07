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
