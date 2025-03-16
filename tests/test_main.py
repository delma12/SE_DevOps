
import os
import sys
from unittest.mock import patch
from fastapi.testclient import TestClient
from ..main import app

client = TestClient(app)

# Mock the template rendering for all tests
@patch('fastapi.templating.Jinja2Templates.TemplateResponse')
def test_health_check(mock_template):
    mock_template.return_value = {"status_code": 200}
    response = client.head("/")
    assert response.status_code == 200

@patch('fastapi.templating.Jinja2Templates.TemplateResponse')
def test_index_page(mock_template):
    mock_template.return_value = {
        "status_code": 200,
        "headers": {"content-type": "text/html"},
        "content": b"mocked content"
    }
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers.get("content-type") is not None

@patch('fastapi.templating.Jinja2Templates.TemplateResponse')
def test_homepage(mock_template):
    mock_template.return_value = {
        "status_code": 200,
        "content": b"mocked content"
    }
    response = client.get("/")
    assert response.status_code == 200
    assert len(response.content) > 0
