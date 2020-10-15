import os
import json
import subprocess
from collections import namedtuple
from typing import Dict
import jinja2
from jinja2 import Template
import redis

from latex.config import ConfigBase
from latex.services.time_service import TimeService
from latex.services.file_service import FileService
from latex.session import Session, SessionManager

import logging

COMPILERS = ['xelatex', 'pdflatex', 'lualatex']
RenderResult = namedtuple('RenderResult', 'success product log')

_latex_env = jinja2.Environment(
    block_start_string=r'\BLOCK{',
    block_end_string='}',
    variable_start_string='\EXPR{',
    variable_end_string='}',
    comment_start_string='\#{',
    comment_end_string='}',
    line_statement_prefix='%#',
    line_comment_prefix='%##',
    trim_blocks=True,
    autoescape=False,
    loader=jinja2.FileSystemLoader(os.path.abspath('.'))
)


def compile_latex(session_id: str, working_directory: str, instance_key: str):
    logging.debug("Starting compilation on session %s", session_id)
    client = redis.from_url(ConfigBase.REDIS_URL)
    manager = SessionManager(client, TimeService(), instance_key, working_directory)
    session = manager.load_session(session_id)
    result = _render_and_compile(session.key, session.compiler, session.target, session.source_files.root_path,
                                 session.template_files.root_path)

    # Check that the PDF was rendered as expected, if not return from here
    if not result.success:
        session.set_errored(result.log)
        logging.info("Compilation failed on session %s", session_id)
        return result

    # If we need to perform an image conversion, we do it now
    if session.convert is not None:
        logging.info("An image conversion to %s at %i dpi requested on session %s", session.convert["format"],
                     session.convert["dpi"], session_id)
        convert_result = _convert_image(result.product,
                                        session.convert["format"],
                                        session.convert["dpi"])
        if convert_result:
            result = RenderResult(success=True, product=convert_result, log=result.log)
        else:
            result = RenderResult(success=False, product=None, log=result.log + "\nFailed on conversion to image")

    # Check the overall success or failure and return the result
    if result.success:
        logging.info("Compilation successful on session %s", session_id)
        session.set_complete(result.product, result.log)
    else:
        logging.info("Compilation failed on session %s", session_id)
        session.set_errored(result.log)

    return result


def _render_templates(template_path: str, source_path: str):
    """
    Locate all templates in the template path and render them all to their targets
    in the source path
    """
    template_service = FileService(template_path)
    destination_service = FileService(source_path)

    for template_file in template_service.get_all_files("."):
        with template_service.open(template_file, "r") as handle:
            data = json.loads(handle.read())

        template: Template = _latex_env.from_string(data['text'])
        rendered_text = template.render(**data['data'])

        with destination_service.open(data['target'], "w") as handle:
            handle.write(rendered_text)


def _convert_image(target: str, format: str, dpi: int) -> str:
    working_dir, file_name = os.path.split(target)
    target_base, _ = os.path.splitext(file_name)
    command = ["pdftoppm", "-singlefile", f"-{format}", "-r", f"{dpi}",
               file_name, target_base]

    # Determine the files in the directory before running the conversion
    original_files = os.listdir(working_dir)

    # Run the conversion command
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=working_dir)
    stdout, stderr = process.communicate()

    # Find the new file
    new_files = [f for f in os.listdir(working_dir) if f not in original_files]
    if len(new_files) != 1:
        return None

    return os.path.join(working_dir, new_files[0])


def _render_and_compile(session_id: str, compiler: str, target: str, source_path: str,
                        template_path: str) -> RenderResult:
    if compiler not in COMPILERS:
        raise ValueError(f"compiler '{compiler}' not supported")

    # Render any templates
    _render_templates(template_path, source_path)

    command = [compiler,
               "-interaction=nonstopmode",
               f"-jobname={session_id}",
               target]

    # I'm not sure how many times a latex compiler should reasonably have to run in order to handle
    # a complex case, so I've conservatively set it to time out at 5
    run_count = 0
    expected_log = None  # prevent linting ref-before-assignment warning
    while run_count < 5:
        # Run the compiler
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, cwd=source_path)
        process.wait()
        run_count += 1

        # Check the log file to determine if a re-run is necessary
        expected_log = os.path.join(source_path, f"{session_id}.log")
        with open(expected_log, "r") as handle:
            if "Rerun" not in handle.read():
                break

    expected_product = os.path.join(source_path, f"{session_id}.pdf")

    if os.path.exists(expected_product):
        return RenderResult(success=True, product=expected_product, log=expected_log)
    else:
        return RenderResult(success=False, product=None, log=expected_log)
