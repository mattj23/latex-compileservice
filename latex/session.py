"""
    Sessions / SessionManager
    ==================================
    Sessions are conceptual structures used to represent the task of generating compiled LaTeX documents, and the
    SessionManager is an object which manages access to and the lifecycle of individual sessions.  See the sections
    below for more information.


    Sessions
    ==================================
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
                |     + file1.png
                |     + file2.tex
                |     + sub_folder/file3.tex
                |     + ...
                |
                +-- templates
                      + template1.json
                      + template2.json
                      + ...

    At this point files can be put into the "source" folder, templates and their render data can be put into the
    templates folder.

    Templates consist of three portions, which are all stored together in a json file:
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


    The SessionManager
    ==================================
    The SessionManager controls access to individual sessions and is responsible for their creation, deletion, and
    persistence.  All such lifecycle actions on a Session should be done through the SessionManager, as Sessions should
    not be directly created or deleted using the Session class itself.

    The SessionManager is an object available globally to the app.  It requires access to a Redis client for the
    storing of the Session metadata, and a FileService object for persistence of source files and template data.

    Of one last note is the instance_key, which is a string which is uniquely generated during app startup. The
    SessionManager keeps a set of session keys stored in Redis under the instance key, in order to allow multiple
    instances of the application to store a single Redis server, if desired.  When the instance is disposed, all
    session keys linked to it could theoretically be removed.

"""
import json
import uuid
from datetime import timedelta

import redis
from flask_redis import FlaskRedis
from flask import Flask

from latex.config import ConfigBase
from latex.services.time_service import TimeService
from latex.services.file_service import FileService

from typing import Callable, List, Set, Dict
import logging


EDITABLE_TEXT = "editable"
FINALIZED_TEXT = "finalized"
SUCCESS_TEXT = "success"
ERROR_TEXT = "error"


def make_id():
    return str(uuid.uuid4()).replace("-", "")[:16]


def to_key(session_id: str) -> str:
    """ converts a simple string key to the form used in redis """
    return f"session:{session_id}"


def validate_conversion_data(convert_data: Dict) -> Dict:
    """ Validate information for image conversion by checking that it is in the expected format and that the values
    are in the expected range.  If the input data is None, it will return None, as this is a valid option and indicates
    that no conversion is to take place.  If the input data is invalid, it throws a ValueError. Otherwise it
    returns a cleaned version of the data."""
    if convert_data is None:
        return None

    if not isinstance(convert_data, dict) or "format" not in convert_data or "dpi" not in convert_data:
        raise ValueError("Image conversion data must be a dictionary with the keys 'format' and 'dpi'")

    convert_format = convert_data["format"]
    convert_dpi = convert_data["dpi"]

    if convert_format not in ["jpeg", "png", "tiff"]:
        raise ValueError('Conversion format must be "jpeg", "png", or "tiff"')

    if not isinstance(convert_dpi, int) or convert_dpi > 10000 or convert_dpi < 10:
        raise ValueError('Image conversion dpi must be an integer between 10 and 10000')

    return {"format": convert_format, "dpi": convert_dpi}


class Session:
    _source_directory = "source"
    _template_directory = "templates"

    def __init__(self, **kwargs):
        self.key: str = kwargs["key"]
        self.compiler: str = kwargs["compiler"]
        self.target: str = kwargs["target"]
        self.created: float = kwargs["created"]
        self.expires_at: float = kwargs["expires_at"]
        self.status: str = kwargs["status"]
        self._file_service: FileService = kwargs["file_service"]
        self._save_callback: Callable = kwargs["save_callback"]
        self.product: str = kwargs.get("product", None)
        self.log: str = kwargs.get("log", None)
        self.convert = kwargs.get("convert", None)

        if not self._file_service.exists(Session._source_directory):
            self._file_service.makedirs(Session._source_directory)
        if not self._file_service.exists(Session._template_directory):
            self._file_service.makedirs(Session._template_directory)

        self.source_files = self._file_service.create_from(Session._source_directory)
        self.template_files = self._file_service.create_from(Session._template_directory)

    @property
    def _redis_key(self):
        """ the prefixed key used by redis to store this session information """
        return to_key(self.key)

    @property
    def is_editable(self) -> bool:
        return self.status == EDITABLE_TEXT

    @property
    def files(self):
        return self.source_files.get_all_files(".")

    @property
    def templates(self):
        files = self.template_files.get_all_files(".")
        template_data = {}
        for f in files:
            with self.template_files.open(f, "r") as handle:
                data = json.loads(handle.read())
                if "target" in data.keys():
                    template_data[data["target"]] = data
        return template_data

    @property
    def public(self):
        return {"key": self.key,
                "created": self.created,
                "expires_at": self.expires_at,
                "compiler": self.compiler,
                "target": self.target,
                "files": self.files,
                "templates": self.templates,
                "convert": self.convert,
                "status": self.status
                }

    @property
    def all_data(self):
        data = self.public
        data["product"] = self.product
        data["log"] = self.log
        return data

    def finalize(self):
        if not self.is_editable:
            raise ValueError("Session is no longer editable and so cannot be finalized")

        self.status = FINALIZED_TEXT
        self._save_callback(self)

    def set_complete(self, product, log):
        if self.status != FINALIZED_TEXT:
            raise ValueError("Session must be finalized in order to be set to complete")

        self.product = product
        self.log = log
        self.status = SUCCESS_TEXT
        self._save_callback(self)

    def set_errored(self, log):
        if self.status != FINALIZED_TEXT:
            raise ValueError("Session must be finalized in order to be set to error")

        self.log = log
        self.status = ERROR_TEXT
        self._save_callback(self)


class SessionManager:
    def __init__(self, redis_client: FlaskRedis, time_service: TimeService, instance_key: str=None, working_directory: str=None):
        self.time_service = time_service
        self.redis = redis_client
        self.working_directory = working_directory
        self.instance_key = instance_key
        self.session_ttl = int(ConfigBase.SESSION_TTL_SEC)
        self._init_file_service()

    def _init_file_service(self):
        if self.working_directory is not None:
            self.root_file_service = FileService(self.working_directory)

    def init_app(self, app: Flask, instance_id: str):
        self.working_directory = app.config["WORKING_DIRECTORY"]
        self.session_ttl = int(app.config["SESSION_TTL_SEC"])
        self._init_file_service()
        self.instance_key = instance_id

    def create_session(self, compiler: str, target: str, convert=None) -> Session:
        key = make_id()

        # Create the working directory
        self.root_file_service.makedirs(key)

        # Create the session
        kwargs = {
            "key": key,
            "created": self.time_service.now,
            "expires_at": self.time_service.now + float(self.session_ttl),
            "compiler": compiler,
            "target": target,
            "status": EDITABLE_TEXT,
            "convert": convert,
            "file_service": self.root_file_service.create_from(key),
            "save_callback": self.save_session
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
        self.redis.set(session._redis_key, json.dumps(session.all_data))

    def load_session(self, session_id: str) -> Session:
        data: bytes = self.redis.get(to_key(session_id))
        if data is None:
            return None

        kwargs = json.loads(data.decode())
        kwargs["file_service"] = self.root_file_service.create_from(session_id)
        kwargs["save_callback"] = self.save_session
        return Session(**kwargs)

    def get_all_session_ids(self) -> Set[str]:
        data = self.redis.smembers(self.instance_key)
        return set(d.decode() for d in data)


def clear_expired_sessions(working_directory: str, instance_key: str, **kwargs):
    """
    Go through and clear the data for any expired sessions
    :param working_directory:
    :param instance_key:
    :return:
    """
    logging.info("Clearing expired sessions")

    time_service = kwargs.get("time_service", TimeService())
    redis_client = redis.from_url(ConfigBase.REDIS_URL)
    manager = SessionManager(redis_client, time_service, instance_key, working_directory)

    for session_id in manager.get_all_session_ids():
        session = manager.load_session(session_id)
        if time_service.now >= session.expires_at:
            logging.info("Removing session %s", session.key)
            manager.delete_session(session)

