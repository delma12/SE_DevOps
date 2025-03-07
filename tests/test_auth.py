import os
import sys
import uuid

from fastapi.testclient import TestClient

from main import app

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))


client = TestClient(app)

valid_password = "Test@1234"


def test_register_user():
    unique_username = f"user_{uuid.uuid4().hex[:8]}"  # Random username
    response = client.post(
        "/register", data={"username": unique_username, "password": "Test@1234"}
    )
    assert response.status_code == 200


def test_login():
    unique_username = "testuser123"
    client.post(
        "/register", data={"username": unique_username, "password": valid_password}
    )

    response = client.post(
        "/login", data={"username": unique_username, "password": valid_password}
    )

    assert (
        response.status_code == 200
    ), f"Expected 200, got {response.status_code}, Response: {response.text}"

    assert "dashboard" in response.text.lower(), "Expected login to show the dashboard"


def test_invalid_login():
    response = client.post(
        "/login", data={"username": "wronguser", "password": "wrongpass"}
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.text
