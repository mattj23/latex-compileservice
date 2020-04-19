import os

import pytest
from typing import Dict

from tests.test_latex_api import ( TestFixture, fixture, file_byte_stream,
                                   create_session_add_file)

from latex.session import Session
from latex.rendering import render_latex, RenderResult


def finalize_session(fixture: TestFixture, session: Session):
    url = f"/api/sessions/{session.key}"
    response = fixture.client.post(url, json={"finalize": True}, follow_redirects=True)
    return response.json


def test_simple_rendering(fixture: TestFixture):
    session = create_session_add_file(fixture, "sample1.tex")
    queue_data = finalize_session(fixture, session)
    result: RenderResult = render_latex(*queue_data)
    assert result.product is not None
    assert os.path.exists(result.product)
    assert os.path.exists(result.log)








