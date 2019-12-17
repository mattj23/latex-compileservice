import pytest
from flask import Response, Request
from latex import create_app, time_service
from latex.config import TestConfig


@pytest.fixture(scope="module")
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


def test_post_session_fails_if_not_json(client):
    data = "text data"
    response: Response = client.post("/api/sessions", data=data, follow_redirects=True)
    assert response.status_code == 400


def test_post_session_fails_if_missing_compiler(client):
    data = {"target": "test.tex"}
    response: Response = client.post("/api/sessions", json=data, follow_redirects=True)
    assert response.status_code == 400


def test_post_session_fails_if_missing_target(client):
    data = {"compiler": "pdflatex" }
    response: Response = client.post("/api/sessions", json=data, follow_redirects=True)
    assert response.status_code == 400


def test_post_session_creates_new_session(client):
    data = {"compiler": "pdflatex", "target": "test.tex"}
    response: Response = client.post("/api/sessions", json=data, follow_redirects=True)
    assert response.status_code == 201


def test_create_session_has_timestamp(client):
    data = {"compiler": "pdflatex", "target": "test.tex"}
    time_service.test.set_time(24601)
    response: Response = client.post("/api/sessions", json=data, follow_redirects=True)
    assert response.json["creation"] == 24601

