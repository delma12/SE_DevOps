import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from passlib.context import CryptContext


from ..database import SessionLocal
from ..main import app
from models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

client = TestClient(app)


@pytest.fixture
def db_session():

    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def admin_login(db_session):
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


def test_admin_can_create_user(db_session: Session, admin_login):
    """Test that an admin user can create a new user."""
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
