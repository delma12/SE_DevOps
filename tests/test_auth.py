
import os
import sys
import uuid
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.staticfiles import StaticFiles

from ..main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_static_files():
    # Mock StaticFiles to avoid the error during tests
    app = FastAPI()
    app.mount = MagicMock()
    app.mount("/static", MagicMock(), name="static")
    return app


valid_password = "Test@1234"


@patch('fastapi.templating.Jinja2Templates.TemplateResponse')
def test_register_user(mock_template):
    mock_template.return_value = {
        "status_code": 200,
        "content": b"Registration successful"
    }
    unique_username = f"user_{uuid.uuid4().hex[:8]}"  # Random username
    response = client.post(
        "/register", data={"username": unique_username, "password": "Test@1234"}
    )
    assert response.status_code == 200


@patch('fastapi.templating.Jinja2Templates.TemplateResponse')
def test_login(mock_template):
    # Mock the template response for registration
    mock_template.return_value = {
        "status_code": 200,
        "content": b"<html><body><h1>Dashboard</h1></body></html>"
    }
    
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
