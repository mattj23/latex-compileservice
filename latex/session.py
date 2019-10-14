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

"""

import os
import uuid
from datetime import datetime


def make_id():
    return str(uuid.uuid4()).replace("-", "")[:16]


class Session:

    def __init__(self, **kwargs):
        self.key: str = kwargs["key"]
        self.compiler: str = kwargs["compiler"]
        self.target: str = kwargs["target"]
        self.created: int = kwargs["created"]
        self.status: str = kwargs["status"]
        self.working_directory: str = kwargs["working_directory"]
        self.directory: str = os.path.join(self.working_directory, self.key)
        self.source_directory: str = os.path.join(self.directory, "source")

    @property
    def exists(self):
        return os.path.exists(self.directory)

    @property
    def files(self):
        if not self.exists:
            return []

        all_files = []
        for _, _, files in os.walk(self.source_directory):
            all_files += files
        return all_files

    @property
    def public(self):
        return {"key": self.key,
                "created": self.created,
                "compiler": self.compiler,
                "target": self.target,
                "files": self.files,
                "exists": self.exists,
                "status": self.status}

    def create_directory(self):
        os.makedirs(self.directory)
        os.makedirs(self.source_directory)

    @staticmethod
    def make_new(compiler: str, target: str, working_directory: str):
        kwargs = {
            "key": make_id(),
            "created": datetime.utcnow().timestamp(),
            "compiler": compiler,
            "target": target,
            "status": "created",
            "working_directory": working_directory
        }
        session = Session(**kwargs)
        return session

