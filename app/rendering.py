import os
import subprocess
from collections import namedtuple
from session import Session

COMPILERS = ['xelatex', 'pdflatex']

RenderResult = namedtuple('RenderResult', 'success product log')


def render_latex(session: Session) -> RenderResult:
    if session.compiler not in COMPILERS:
        raise ValueError(f"compiler '{session.compiler}' not supported")

    command = [session.compiler,
               "-interaction=nonstopmode",
               f"-jobname={session.key}",
               session.target]

    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, cwd=session.directory)
    process.wait()

    expected_log = os.path.join(session.directory, f"{session.key}.log")
    expected_product = os.path.join(session.directory, f"{session.key}.pdf")

    if os.path.exists(expected_product):
        return RenderResult(success=True, product=expected_product, log=expected_log)
    else:
        return RenderResult(success=False, product=None, log=expected_log)

