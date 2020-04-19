import os
import io
import shutil
import pytest
import tempfile
from flask import Response, Request, Flask
from flask.testing import FlaskClient
from latex import create_app, time_service, session_manager, redis_client

from latex.config import TestConfig
from latex.session import Session, FINALIZED_TEXT, SUCCESS_TEXT, ERROR_TEXT, EDITABLE_TEXT
from latex.rendering import compile_latex, RenderResult
from tests.test_sessions import find_test_asset_folder, hash_file


def file_byte_stream(file_path):
    with open(file_path, "rb") as handle:
        return io.BytesIO(handle.read())


class TestFixture:
    def __init__(self, **kwargs):
        self.app: Flask = create_app(kwargs['config'])
        self.client: FlaskClient = None


@pytest.fixture(scope="session")
def fixture():
    with tempfile.TemporaryDirectory() as temp_path:
        config = TestConfig()
        config.WORKING_DIRECTORY = temp_path

        test_fixture = TestFixture(config=config)
        with test_fixture.app.test_client() as client:
            test_fixture.client = client

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


def finalize_session(fixture: TestFixture, session: Session):
    url = f"/api/sessions/{session.key}"
    response = fixture.client.post(url, json={"finalize": True}, follow_redirects=True)
    return response.json


def create_session_add_file(fixture: TestFixture, target_file: str, prefix=None) -> Session:
    data = {"compiler": "xelatex", "target": target_file}
    response: Response = fixture.client.post("/api/sessions", json=data, follow_redirects=True)
    session = session_manager.load_session(response.json["key"])

    file_url = f"/api/sessions/{session.key}/files"
    source_path = os.path.join(find_test_asset_folder(), target_file)
    if prefix:
        dest = os.path.join(prefix, target_file)
    else:
        dest = target_file
    data2 = {"file0": (file_byte_stream(source_path), dest)}
    response2: Response = fixture.client.post(file_url, data=data2, follow_redirects=True, content_type="multipart/form-data")
    return session


def test_api_root_endpoint_produces_expected(fixture: TestFixture):
    response: Response = fixture.client.get("/api", follow_redirects=True)
    assert response.is_json
    assert type(response.json) is dict
    assert "create_session" in response.json.keys()


def test_session_endpoint_routes_correctly(fixture: TestFixture):
    response: Response = fixture.client.get("/api/sessions", follow_redirects=True)
    assert response.status_code == 200


def test_post_session_fails_if_not_json(fixture: TestFixture):
    data = "text data"
    response: Response = fixture.client.post("/api/sessions", data=data, follow_redirects=True)
    assert response.status_code == 400


def test_post_session_fails_if_missing_compiler(fixture: TestFixture):
    data = {"target": "test.tex"}
    response: Response = fixture.client.post("/api/sessions", json=data, follow_redirects=True)
    assert response.status_code == 400


def test_post_session_fails_if_missing_target(fixture: TestFixture):
    data = {"compiler": "pdflatex" }
    response: Response = fixture.client.post("/api/sessions", json=data, follow_redirects=True)
    assert response.status_code == 400


def test_post_session_creates_new_session(fixture: TestFixture):
    data = {"compiler": "pdflatex", "target": "test.tex"}
    response: Response = fixture.client.post("/api/sessions", json=data, follow_redirects=True)
    assert response.json["status"] == "editable"
    assert response.status_code == 201


def test_create_session_has_timestamp(fixture: TestFixture):
    data = {"compiler": "pdflatex", "target": "test.tex"}
    time_service.test.set_time(24601)
    response: Response = fixture.client.post("/api/sessions", json=data, follow_redirects=True)
    assert response.json["created"] == 24601


def test_get_session_information(fixture: TestFixture):
    data = {"compiler": "pdflatex", "target": "test5.tex"}
    time_service.test.set_time(24601)
    response: Response = fixture.client.post("/api/sessions", json=data, follow_redirects=True)
    session_key = response.json["key"]
    session_url = f"/api/sessions/{session_key}"
    response2: Response = fixture.client.get(session_url)

    assert response2.json["compiler"] == "pdflatex"
    assert response2.json["target"] == "test5.tex"
    assert response2.json["created"] == 24601


def test_add_file_to_session(fixture: TestFixture):
    target_file = "sample1.tex"
    session = create_session_add_file(fixture, target_file, prefix="test")

    source_path = os.path.join(find_test_asset_folder(), target_file)
    expected_path = os.path.join(session.source_files.root_path, "test", target_file)
    assert hash_file(source_path) == hash_file(expected_path)


def test_get_template_form_url(fixture: TestFixture):
    data = {"compiler": "xelatex", "target": "test.tex"}
    post_response: Response = fixture.client.post("/api/sessions", json=data, follow_redirects=True)
    session_url = post_response.location
    session = session_manager.load_session(post_response.json["key"])

    get_response: Response = fixture.client.get(session_url)
    assert get_response.is_json
    assert type(get_response.json) is dict
    assert "add_templates" in get_response.json.keys()


def test_add_template(fixture: TestFixture):
    data = {"compiler": "xelatex", "target": "test.tex"}
    post_response: Response = fixture.client.post("/api/sessions", json=data, follow_redirects=True)
    session_url = post_response.location
    session = session_manager.load_session(post_response.json["key"])

    data2 = {
        "target": "test.tex",
        "text": "this is the template text\n",
        "data": {"test": "hello"}
     }

    template_url = f"/api/sessions/{session.key}/templates"
    template_post_response: Response = fixture.client.post(template_url, json=data2, follow_redirects=True)

    assert template_post_response.is_json
    assert type(template_post_response.json) is dict
    assert template_post_response.json["test.tex"]["target"] == data2["target"]
    assert template_post_response.json["test.tex"]["text"] == data2["text"]
    assert template_post_response.json["test.tex"]["data"] == data2["data"]


def test_set_session_finalized(fixture: TestFixture):
    session = create_session_add_file(fixture, "sample1.tex")
    finalize_session(fixture, session)
    reloaded_session = session_manager.load_session(session.key)
    assert reloaded_session.status == FINALIZED_TEXT


def test_not_editable_session_post_fails(fixture: TestFixture):
    session = create_session_add_file(fixture, "sample1.tex")
    finalize_session(fixture, session)

    post_url = f"/api/sessions/{session.key}"
    post_response: Response = fixture.client.post(post_url, json={"finalize": True}, follow_redirects=True)

    assert post_response.status_code == 403


def test_not_editable_session_file_add_fails(fixture: TestFixture):
    target_file = "sample1.tex"
    session = create_session_add_file(fixture, target_file)
    finalize_session(fixture, session)
    file_url = f"/api/sessions/{session.key}/files"
    source_path = os.path.join(find_test_asset_folder(), target_file)
    data2 = {"file0": (file_byte_stream(source_path), target_file)}
    response2: Response = fixture.client.post(file_url, data=data2, follow_redirects=True, content_type="multipart/form-data")
    assert response2.status_code == 403


def test_not_editable_session_template_add_fails(fixture: TestFixture):
    target_file = "sample1.tex"
    session = create_session_add_file(fixture, target_file)
    finalize_session(fixture, session)

    data2 = {
        "target": "test.tex",
        "text": "this is the template text\n",
        "data": {"test": "hello"}
    }

    template_url = f"/api/sessions/{session.key}/templates"
    template_post_response: Response = fixture.client.post(template_url, json=data2, follow_redirects=True)
    assert template_post_response.status_code == 403


def test_log_not_found_before_rendering(fixture: TestFixture):
    target_file = "sample1.tex"
    session = create_session_add_file(fixture, target_file)
    finalize_session(fixture, session)

    log_url = f"/api/sessions/{session.key}/log"
    response: Response = fixture.client.get(log_url, follow_redirects=True)
    assert response.status_code == 404


def test_product_not_found_before_rendering(fixture: TestFixture):
    target_file = "sample1.tex"
    session = create_session_add_file(fixture, target_file)
    finalize_session(fixture, session)

    product_url = f"/api/sessions/{session.key}/product"
    response: Response = fixture.client.get(product_url, follow_redirects=True)
    assert response.status_code == 404


def test_simple_rendering(fixture: TestFixture):
    session = create_session_add_file(fixture, "sample1.tex")
    queue_data = finalize_session(fixture, session)
    result: RenderResult = compile_latex(*queue_data)
    assert result.product is not None
    assert os.path.exists(result.product)
    assert os.path.exists(result.log)


def test_simple_rendering_sets_complete(fixture: TestFixture):
    session = create_session_add_file(fixture, "sample1.tex")
    queue_data = finalize_session(fixture, session)
    result: RenderResult = compile_latex(*queue_data)

    reloaded_session = session_manager.load_session(session.key)
    assert reloaded_session.status == SUCCESS_TEXT
    assert os.path.exists(reloaded_session.product)
    assert os.path.exists(reloaded_session.log)


def test_successful_session_retrieve_product(fixture: TestFixture):
    session = create_session_add_file(fixture, "sample1.tex")
    queue_data = finalize_session(fixture, session)
    compile_latex(*queue_data)

    session_url = f"/api/sessions/{session.key}"
    response: Response = fixture.client.get(session_url, follow_redirects=True)

    product_url = response.json['product']['href']
    product_fetch: Response = fixture.client.get(product_url, follow_redirects=True)

    assert len(product_fetch.data) > 2000


def test_failed_session_retrieve_logs(fixture: TestFixture):
    session = create_session_add_file(fixture, "bad_sample1.tex")
    queue_data = finalize_session(fixture, session)
    compile_latex(*queue_data)

    session_url = f"/api/sessions/{session.key}"
    response: Response = fixture.client.get(session_url, follow_redirects=True)

    assert response.json['status'] == ERROR_TEXT

    log_url = response.json['log']['href']
    log_fetch: Response = fixture.client.get(log_url, follow_redirects=True)

    assert "LaTeX Error: File `notarealarticle.cls' not found." in log_fetch.data.decode()


def test_status_endpoint(fixture: TestFixture):
    for n, finalize in ((3, False), (2, True)):
        for i in range(n):
            session = create_session_add_file(fixture, "sample1.tex")
            if finalize:
                finalize_session(fixture, session)

    status_url = "/api/status"
    response: Response = fixture.client.get(status_url, follow_redirects=True)

    assert response.is_json
    assert "sessions" in response.json.keys()
    assert "time" in response.json.keys()

