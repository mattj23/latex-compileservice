"""
    A Session is a single compilation/rendering task aimed at producing a single product, created by a single client.
    The session consists of a set of input files, some of which may be unrendered Jinja2 templates, a compiler, a root
    target for the compiler, a status, a timestamp, and products.

    When a Session is created a unique key must be assigned to it. At that point a folder structure is generated
    which houses the Session's information, source files, and unrendered templates.  A directory structure is created
    as follows:

        working_directory
            |
            +-- {session unique key}
                |
                +-- source
                |
                +-- templates
                |
                +-- info.json

    At this point files can be put into the "source" folder, templates and their render data can be put into the
    templates folder, and info.json can be updated.

    Templates consist of three portions:
        1.  A file content, which is a text file that will be run through the Jinja2 templating engine to produce
            a .tex file
        2.  A destination path, which is where the .tex file will be placed in the "source" directory after it is
            rendered
        3.  A json dictionary, the primary keys of which will be passed to the Jinja2 templating engine when rendering
            the template

    When a session is to be compiled, first the templates are rendered to .tex files and placed in the "source"
    directory.  Next, the selected latex compiler is invoked on the target in the "source" directory, and the log is
    watched to see if the compiler needs to be invoked again.  When the logs indicate that the compilation has ceased,
    or that a set number of recompiles have been used, the produced files are extracted and saved temporarily so that
    the working directory can be removed.

    Session possible status:
    1. editable - the session can be modified, files and templates added
    2. finalized - the session is finalized, and can no longer be edited; a worker will pick it up when it can
    3. success - the session was compiled successfully, and the product is available to retrieve
    4. error - the session did not complete successfully, but the log files can be retrieved for debugging

"""
import json
import os
import shutil
import uuid
from redis import Redis
from flask import Flask
from latex.time_service import TimeService
from latex.services.file_service import FileService


def make_id():
    return str(uuid.uuid4()).replace("-", "")[:16]


def to_key(session_id: str) -> str:
    """ converts a simple string key to the form used in redis """
    return f"session:{session_id}"


class Session:
    _source_directory = "source"
    _template_directory = "templates"

    def __init__(self, **kwargs):
        self.key: str = kwargs["key"]
        self.compiler: str = kwargs["compiler"]
        self.target: str = kwargs["target"]
        self.created: float = kwargs["created"]
        self.status: str = kwargs["status"]
        self._file_service: FileService = kwargs["file_service"]

        if not self._file_service.exists(Session._source_directory):
            self._file_service.makedirs(Session._source_directory)
        if not self._file_service.exists(Session._template_directory):
            self._file_service.makedirs(Session._template_directory)

        self.sources = self._file_service.create_from(Session._source_directory)
        self.templates = self._file_service.create_from(Session._template_directory)

    @property
    def _redis_key(self):
        """ the prefixed key used by redis to store this session information """
        return to_key(self.key)

    @property
    def files(self):
        return self.sources.get_all_files(".")

    @property
    def public(self):
        return {"key": self.key,
                "created": self.created,
                "compiler": self.compiler,
                "target": self.target,
                "files": self.files,
                "status": self.status}


class SessionManager:
    def __init__(self, redis_client: Redis, time_service: TimeService, instance_key: str=None, working_directory: str=None):
        self.time_service = time_service
        self.redis = redis_client
        self.working_directory = working_directory
        self.instance_key = instance_key
        self._init_file_service()

    def _init_file_service(self):
        if self.working_directory is not None:
            self.root_file_service = FileService(self.working_directory)

    def init_app(self, app: Flask, instance_id: str):
        self.working_directory = app.config["WORKING_DIRECTORY"]
        self._init_file_service()
        self.instance_key = instance_id

    def create_session(self, compiler: str, target: str) -> Session:
        key = make_id()

        # Create the working directory
        self.root_file_service.makedirs(key)

        # Create the session
        kwargs = {
            "key": key,
            "created": self.time_service.now,
            "compiler": compiler,
            "target": target,
            "status": "editable",
            "file_service": self.root_file_service.create_from(key)
        }
        session = Session(**kwargs)

        # Store to the redis collection of sessions for this instance
        self.redis.sadd(self.instance_key, session.key)

        # Also save the session to redis
        self.save_session(session)

        return session

    def delete_session(self, session: Session):
        # Remove from disk and from redis
        self.root_file_service.rmtree(session.key)
        self.redis.delete(session._redis_key)
        self.redis.srem(self.instance_key, session.key)

    def save_session(self, session: Session) -> None:
        self.redis.set(session._redis_key, json.dumps(session.public))

    def load_session(self, key: str) -> Session:
        data: bytes = self.redis.get(to_key(key))
        if data is None:
            return None

        kwargs = json.loads(data.decode())
        kwargs["file_service"] = self.root_file_service.create_from(key)
        return Session(**kwargs)