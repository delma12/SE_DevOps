from fastapi.testclient import TestClient
from main import app 
import sys
import os


sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))


client = TestClient(app)


def test_dashboard_requires_login():
    response = client.get("/dashboard")
    assert response.status_code == 403
    assert "User not authenticated" in response.text
