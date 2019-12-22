import os
import io
import shutil
import pytest
import tempfile
from flask import Response, Request
from latex import create_app, time_service, session_manager, redis_client
from latex.config import TestConfig

from tests.test_sessions import find_test_asset_folder, hash_file


def file_byte_stream(file_path):
    with open(file_path, "rb") as handle:
        return io.BytesIO(handle.read())


class TestFixture:
    def __init__(self, **kwargs):
        self.app = create_app(TestConfig())
        self.client = None


@pytest.fixture(scope="module")
def fixture():
    test_fixture = TestFixture()

    with test_fixture.app.test_client() as client, tempfile.TemporaryDirectory() as temp_path:
        test_fixture.client = client
        session_manager.working_directory = temp_path

        with test_fixture.app.app_context():
            # any database stuff goes here
            pass

        # Return to caller
        yield test_fixture

    # Clean up here
    shutil.rmtree(temp_path, True)
    while True:
        element = redis_client.spop(session_manager.instance_key)
        if element is None:
            break

        element_key = f"session:{element.decode()}"
        redis_client.delete(element_key)


def test_api_root_endpoint_produces_expected(fixture):
    response: Response = fixture.client.get("/api", follow_redirects=True)
    assert response.is_json
    assert type(response.json) is dict
    assert "create_session" in response.json.keys()


def test_session_endpoint_routes_correctly(fixture):
    response: Response = fixture.client.get("/api/sessions", follow_redirects=True)
    assert response.status_code == 200


def test_post_session_fails_if_not_json(fixture):
    data = "text data"
    response: Response = fixture.client.post("/api/sessions", data=data, follow_redirects=True)
    assert response.status_code == 400


def test_post_session_fails_if_missing_compiler(fixture):
    data = {"target": "test.tex"}
    response: Response = fixture.client.post("/api/sessions", json=data, follow_redirects=True)
    assert response.status_code == 400


def test_post_session_fails_if_missing_target(fixture):
    data = {"compiler": "pdflatex" }
    response: Response = fixture.client.post("/api/sessions", json=data, follow_redirects=True)
    assert response.status_code == 400


def test_post_session_creates_new_session(fixture):
    data = {"compiler": "pdflatex", "target": "test.tex"}
    response: Response = fixture.client.post("/api/sessions", json=data, follow_redirects=True)
    assert response.json["status"] == "editable"
    assert response.status_code == 201


def test_create_session_has_timestamp(fixture):
    data = {"compiler": "pdflatex", "target": "test.tex"}
    time_service.test.set_time(24601)
    response: Response = fixture.client.post("/api/sessions", json=data, follow_redirects=True)
    assert response.json["created"] == 24601


def test_get_session_information(fixture):
    data = {"compiler": "pdflatex", "target": "test5.tex"}
    time_service.test.set_time(24601)
    response: Response = fixture.client.post("/api/sessions", json=data, follow_redirects=True)
    session_key = response.json["key"]
    session_url = f"/api/sessions/{session_key}"
    response2: Response = fixture.client.get(session_url)

    assert response2.json["compiler"] == "pdflatex"
    assert response2.json["target"] == "test5.tex"
    assert response2.json["created"] == 24601


def test_add_file_to_session(fixture):
    target_file = "sample1.tex"
    data = {"compiler": "xelatex", "target": target_file}
    response: Response = fixture.client.post("/api/sessions", json=data, follow_redirects=True)
    session = session_manager.load_session(response.json["key"])

    file_url = f"/api/sessions/{session.key}/files"
    source_path = os.path.join(find_test_asset_folder(), target_file)
    data2 = { "file0": (file_byte_stream(source_path), "test/" + target_file)}
    response2: Response = fixture.client.post(file_url, data=data2, follow_redirects=True, content_type="multipart/form-data")

    expected_path = os.path.join(session.source_directory, target_file)
    assert hash_file(source_path) == hash_file(expected_path)
