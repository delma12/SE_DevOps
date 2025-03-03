from fastapi.testclient import TestClient
import sys
import os

# Ensure the root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from main import app  # Now it should work

client = TestClient(app)

def test_dashboard_requires_login():
    response = client.get("/dashboard")
    assert response.status_code == 403
    assert "User not authenticated" in response.text
