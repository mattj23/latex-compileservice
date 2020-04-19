import os
import json
import shutil
import tempfile
from hashlib import md5

import pytest

from tests.test_sessions import find_test_asset_folder
from latex.rendering import _render_and_compile, _render_templates, RenderResult


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


def copy_template(file_name, data, template_folder):
    target = os.path.join(find_test_asset_folder(), file_name)
    with open(target, "r") as handle:
        text = handle.read()

    file_name_only = os.path.basename(target)

    output = {
        "target": file_name_only,
        "data": data,
        "text": text
    }

    with open(os.path.join(template_folder, md5(file_name_only.encode()).hexdigest()), "w") as handle:
        handle.write(json.dumps(output, indent=4))


def test_simple_compile_xelatex(render_fixture: RenderFixture):
    target_file = "sample1.tex"
    copy_test_file(target_file, render_fixture.source_dir)
    result = _render_and_compile("temp", "xelatex", target_file, render_fixture.source_dir, render_fixture.template_dir)

    assert result.product is not None
    assert os.path.exists(result.product)
    assert os.path.exists(result.log)


def test_simple_compile_pdflatex(render_fixture: RenderFixture):
    target_file = "sample1.tex"
    copy_test_file(target_file, render_fixture.source_dir)
    result = _render_and_compile("temp", "pdflatex", target_file, render_fixture.source_dir, render_fixture.template_dir)

    assert result.product is not None
    assert os.path.exists(result.product)
    assert os.path.exists(result.log)


def test_simple_compile_lualatex(render_fixture: RenderFixture):
    target_file = "sample1.tex"
    copy_test_file(target_file, render_fixture.source_dir)
    result = _render_and_compile("temp", "lualatex", target_file, render_fixture.source_dir, render_fixture.template_dir)

    assert result.product is not None
    assert os.path.exists(result.product)
    assert os.path.exists(result.log)


def test_render(render_fixture: RenderFixture):
    target_name = "sample_template1.tex"
    data = {"name_1": "This is a Section Name"}
    copy_template(target_name, data, render_fixture.template_dir)
    _render_templates(render_fixture.template_dir, render_fixture.source_dir)

    with open(os.path.join(render_fixture.source_dir, target_name), "r") as handle:
        rendered_text = handle.read()

    assert data['name_1'] in rendered_text
    for i in range(5):
        assert f"This is the {i}-th item" in rendered_text







