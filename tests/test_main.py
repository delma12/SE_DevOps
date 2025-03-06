from fastapi.testclient import TestClient
import sys
import os

# Ensure the root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from main import app  # Now it should work

client = TestClient(app)


def test_health_check():
    response = client.head("/")
    assert response.status_code == 200


def test_index_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_homepage():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
