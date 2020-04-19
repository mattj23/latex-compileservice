import os
import shutil
import tempfile

import pytest
from typing import Dict

from tests.test_sessions import find_test_asset_folder
from latex.rendering import _render_and_compile, RenderResult


class RenderFixture:
    def __init__(self, temp_path):
        self.source_dir = os.path.join(temp_path, "source")
        self.template_dir = os.path.join(temp_path, "templates")
        os.makedirs(self.source_dir)
        os.makedirs(self.template_dir)


@pytest.fixture()
def render_fixture() -> RenderFixture:
    with tempfile.TemporaryDirectory() as temp_path:
        fixture = RenderFixture(temp_path)
        yield fixture

    shutil.rmtree(temp_path, True)


def copy_test_file(file_name, dest_folder):
    target = os.path.join(find_test_asset_folder(), file_name)
    file_name_only = os.path.basename(target)
    shutil.copy(target, os.path.join(dest_folder, file_name_only))


def test_simple_rendering_xelatex(render_fixture: RenderFixture):
    target_file = "sample1.tex"
    copy_test_file(target_file, render_fixture.source_dir)
    result = _render_and_compile("temp", "xelatex", target_file, render_fixture.source_dir, render_fixture.template_dir)

    assert result.product is not None
    assert os.path.exists(result.product)
    assert os.path.exists(result.log)


def test_simple_rendering_pdflatex(render_fixture: RenderFixture):
    target_file = "sample1.tex"
    copy_test_file(target_file, render_fixture.source_dir)
    result = _render_and_compile("temp", "pdflatex", target_file, render_fixture.source_dir, render_fixture.template_dir)

    assert result.product is not None
    assert os.path.exists(result.product)
    assert os.path.exists(result.log)


def test_simple_rendering_lualatex(render_fixture: RenderFixture):
    target_file = "sample1.tex"
    copy_test_file(target_file, render_fixture.source_dir)
    result = _render_and_compile("temp", "lualatex", target_file, render_fixture.source_dir, render_fixture.template_dir)

    assert result.product is not None
    assert os.path.exists(result.product)
    assert os.path.exists(result.log)







