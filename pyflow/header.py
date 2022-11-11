from __future__ import print_function

import os


class Header:
    def __init__(self, name, include_path=None, what="head"):
        self._name = name
        self._what = what
        assert include_path is not None
        self.include_path = include_path

    @property
    def include_name(self):
        return "{}_{}.h".format(self._name, self._what)


class FileHeader(Header):
    def __init__(self, name, path, home, **kwargs):
        super().__init__(name, **kwargs)
        self._path = os.path.join(os.path.dirname(home), "files", path)

    def install(self, target):
        target.copy(self._path, os.path.join(self.include_path, self.include_name))
        return self.include_name


class InlineCodeHeader(Header):
    def __init__(self, name, code, **kwargs):
        super().__init__(name, **kwargs)
        self._code = [r.strip() for r in code.split("\n")]

    def install(self, target):
        target.save(self._code, os.path.join(self.include_path, self.include_name))
        return self.include_name


class FileTail(FileHeader):
    def __init__(self, name, path, home):
        super().__init__(name, path, home, what="tail")


class InlineCodeTail(InlineCodeHeader):
    def __init__(self, name, code):
        super().__init__(name, code, what="tail")
