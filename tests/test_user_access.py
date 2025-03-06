import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import SessionLocal
from main import app
from models import User

client = TestClient(app)


@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def admin_login():
    admin_credentials = {"username": "admin", "password": "adminpassword"}
    response = client.post("/login", data=admin_credentials)
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.cookies  # Return session cookies for authentication


def test_admin_can_create_user(db_session: Session, admin_login):

    unique_username = f"testuser_{uuid.uuid4().hex[:6]}"

    new_user_data = {
        "username": unique_username,
        "password": "securepassword",
        "is_admin": False,
    }

    response = client.post("/users", json=new_user_data, cookies=admin_login)

    assert response.status_code in [200, 201], f"Unexpected response: {response.text}"
    assert (
        response.json()["username"] == unique_username
    ), "Username mismatch in response"

    created_user = db_session.query(User).filter_by(username=unique_username).first()
    assert created_user is not None, "User was not created in the database"
    assert created_user.is_admin is False
