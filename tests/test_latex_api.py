import pytest
from flask import Response, Request
from latex import create_app
from latex.config import TestConfig


@pytest.fixture
def client():
    app = create_app(TestConfig())
    with app.test_client() as client:
        with app.app_context():
            pass # init db?
        yield client

    # Clean up here
    pass


def test_api_root_endpoint_produces_expected(client):
    response: Response = client.get("/api", follow_redirects=True)
    assert response.is_json
    assert type(response.json) is dict
    assert "create_session" in response.json.keys()


def test_session_endpoint_routes_correctly(client):
    response: Response = client.get("/api/sessions", follow_redirects=True)
    assert response.status_code == 200

