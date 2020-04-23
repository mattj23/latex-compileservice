from latex import celery
from latex.rendering import compile_latex
from latex.session import clear_expired_sessions

import logging

@celery.task
def background_run_compile(session_id: str, working_directory: str, instance_key: str):
    compile_latex(session_id, working_directory, instance_key)


@celery.task
def background_clear_expired(working_directory: str, instance_key: str):
    clear_expired_sessions(working_directory, instance_key)


@celery.task
def test():
    logging.info("Test task was run")
