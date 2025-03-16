import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from fastapi.testclient import TestClient

from ..main import app

client = TestClient(app)


from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles


@pytest.fixture(autouse=True)
def mock_static_files():
    # Mock StaticFiles to avoid the error during tests
    app = FastAPI()
    app.mount = MagicMock()
    app.mount("/static", MagicMock(), name="static")
    return app


def test_dashboard_requires_login():
    response = client.get("/dashboard")
    assert response.status_code == 403
    assert "User not authenticated" in response.text
