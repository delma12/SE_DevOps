import os
import sys

from fastapi.testclient import TestClient

from ..main import app

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

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
