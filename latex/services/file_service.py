"""
    The file service abstracts interactions with the OS to allow for testing
"""

import os
import shutil
from typing import List


def check_contains(method):
    """ Decorator to prevent access to operations on files and directories outside of the root path of a file service
    object. This will only work on class methods of an object that contains a 'root_path' attribute, and where the
    second argument is the path of the object to be accessed. If the wrapped method is provided with a relative path,
    this decorator will interpret it as from the FileService root path and substitute it with the equivalent
    absolute path. """
    def wrapped_with_check(*args):
        args = list(args)
        instance: FileService = args[0]
        path: str = args[1]

        if not os.path.isabs(path):
            path = os.path.join(instance.root_path, path)
            args[1] = path

        if not instance.contains(path):
            raise ValueError(f"The specified path {path} is not contained by the root working directory {instance.root_path}")
        return method(*args)
    return wrapped_with_check


class FileService:
    def __init__(self, root_path):
        self.root_path = os.path.join(os.path.realpath(root_path), "")
        if not os.path.isdir(root_path):
            raise ValueError(f"The root path {root_path} provided to the file service is not a real directory")

    def contains(self, path: str) -> bool:
        """ Checks to see if the provided path is contained by the root path. Use to prevent ../ and symlinks
        from escaping the working directory. """
        test_path = os.path.realpath(path)

        # Special case for the root path
        if os.path.isdir(test_path):
            if os.path.join(test_path, "") == self.root_path:
                return True

        return os.path.commonprefix([test_path, self.root_path]) == self.root_path

    @check_contains
    def makedirs(self, path: str):
        os.makedirs(path)

    @check_contains
    def rmtree(self, path: str):
        shutil.rmtree(path, True)

    @check_contains
    def get_all_files(self, path: str) -> List[str]:
        all_files = []
        for root, _, files in os.walk(path):
            all_files += [os.path.join(root, f) for f in files]
        return [os.path.relpath(f, path) for f in all_files]

    @check_contains
    def open(self, path: str, mode: str):
        if "w" in mode or "+" in mode:
            directory = os.path.dirname(path)
            if not os.path.exists(directory):
                os.makedirs(directory)
        return open(path, mode)

    @check_contains
    def exists(self, path: str):
        return os.path.exists(path)

    @check_contains
    def create_from(self, path):
        return FileService(path)
