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
import json
from typing import List

working_directory = "/working"


class Session:
    def __init__(self, key: str, compiler: str = None, target: str = None):
        self.key = key
        self.directory = os.path.join(working_directory, self.key)
        self.info_file = os.path.join(self.directory, ".info.json")
        self.__info_dict = {
            "status": "unknown",
            "time": 0,
            "compiler": compiler,
            "target": target,
            "product": None
        }

        self.__read_info()

    @property
    def product(self):
        return self.__info_dict['product']

    @property
    def compiler(self):
        return self.__info_dict['compiler']

    @property
    def target(self):
        return self.__info_dict['target']

    @property
    def exists(self):
        return os.path.exists(self.directory)

    @property
    def status(self):
        return self.__info_dict["status"]

    @property
    def time(self):
        return datetime.utcfromtimestamp(self.__info_dict["time"])

    @property
    def files(self):
        if not self.exists:
            return []

        all_files = []
        for _, _, files in os.walk(self.directory):
            all_files += files
        return all_files

    @property
    def public(self):
        return {"key": self.key,
                "files": self.files,
                "exists": self.exists,
                "status": self.status}

    def set_product(self, product_name: str):
        self.__info_dict['product'] = os.path.basename(product_name)
        self.__write_info()

    def create(self):
        os.mkdir(self.directory)
        self.__info_dict['time'] = str(datetime.timestamp(datetime.utcnow()))
        self.__info_dict['status'] = "created"
        self.__write_info()

    def __write_info(self):
        with open(self.info_file, "w") as handle:
            handle.write(json.dumps(self.__info_dict))

    def __read_info(self):
        if os.path.exists(self.info_file):
            with open(self.info_file, "r") as handle:
                self.__info_dict = json.loads(handle.read())


def new_session(compiler: str, target: str) -> Session:
    session_id = str(uuid.uuid4()).replace("-", "")
    return Session(session_id, compiler, target)


def get_sessions_by_workspace() -> List[str]:
    return os.listdir(working_directory)