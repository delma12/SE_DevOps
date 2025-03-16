
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from starlette.staticfiles import StaticFiles

from models import User
from ..database import SessionLocal
from ..main import app

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_static_files():
    # Mock StaticFiles to avoid the error during tests
    app = FastAPI()
    app.mount = MagicMock()
    app.mount("/static", MagicMock(), name="static")
    return app


@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
@patch('fastapi.templating.Jinja2Templates.TemplateResponse')
def admin_login(mock_template, db_session):
    # Mock the template response for login
    mock_template.return_value = {
        "status_code": 200,
        "content": b"<html><body><h1>Dashboard</h1></body></html>"
    }

    admin_username = f"admin_{uuid.uuid4().hex[:6]}"  # Unique admin username
    admin_password = "test_admin_password"

    # Create a new admin user
    hashed_password = pwd_context.hash(admin_password)
    admin_user = User(
        username=admin_username, hashed_password=hashed_password, is_admin=True
    )
    db_session.add(admin_user)
    db_session.commit()

    print(f"Created admin user: {admin_username}")

    admin_credentials = {"username": admin_username, "password": admin_password}
    response = client.post("/login", data=admin_credentials)

    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.cookies


@patch('fastapi.templating.Jinja2Templates.TemplateResponse')
def test_admin_can_create_user(mock_template, db_session: Session, admin_login):
    """Test that an admin user can create a new user."""
    # Mock the template response for user creation
    mock_template.return_value = {
        "status_code": 201,
        "content": b"User created successfully"
    }

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
