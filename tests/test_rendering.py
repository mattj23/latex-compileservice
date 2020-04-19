import os
import shutil
import tempfile

import pytest
from typing import Dict

from tests.test_latex_api import TestFixture, create_session_add_file, fixture, finalize_session

from latex import session_manager, redis_client
from latex.config import TestConfig
from latex.session import Session, SUCCESS_TEXT, ERROR_TEXT
from latex.rendering import render_latex, RenderResult



def test_simple_rendering(fixture: TestFixture):
    session = create_session_add_file(fixture, "sample1.tex")
    queue_data = finalize_session(fixture, session)
    result: RenderResult = render_latex(*queue_data)
    assert result.product is not None
    assert os.path.exists(result.product)
    assert os.path.exists(result.log)


def test_simple_rendering_sets_complete(fixture: TestFixture):
    session = create_session_add_file(fixture, "sample1.tex")
    queue_data = finalize_session(fixture, session)
    result: RenderResult = render_latex(*queue_data)

    reloaded_session = session_manager.load_session(session.key)
    assert reloaded_session.status == SUCCESS_TEXT
    assert os.path.exists(reloaded_session.product)
    assert os.path.exists(reloaded_session.log)






