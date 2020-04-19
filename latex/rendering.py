import os
import subprocess
from collections import namedtuple
from typing import Dict

import redis
from latex.config import ConfigBase
from latex.services.time_service import TimeService
from latex.session import Session, SessionManager

COMPILERS = ['xelatex', 'pdflatex', 'lualatex']

RenderResult = namedtuple('RenderResult', 'success product log')


def render_latex(session_id: str, working_directory: str, instance_key: str):
    client = redis.from_url(ConfigBase.REDIS_URL)
    manager = SessionManager(client, TimeService(), instance_key, working_directory)
    session = manager.load_session(session_id)
    result = _render_and_compile(session.key, session.compiler, session.target, session.source_files.root_path,
                                 session.template_files.root_path)

    if result.success:
        session.set_complete(result.product, result.log)
    else:
        session.set_errored(result.log)

    return result


def _render_and_compile(session_id: str, compiler: str, target: str, source_path: str, template_path: str) -> RenderResult:
    if compiler not in COMPILERS:
        raise ValueError(f"compiler '{compiler}' not supported")

    command = [compiler,
               "-interaction=nonstopmode",
               f"-jobname={session_id}",
               target]

    # I'm not sure how many times a latex compiler should reasonably have to run in order to handle
    # a complex case, so I've conservatively set it to time out at 5
    run_count = 0
    expected_log = None     # prevent linting ref-before-assignment warning
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

