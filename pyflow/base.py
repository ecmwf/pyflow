from __future__ import absolute_import

from .expressions import Overloaded


class Root:
    def __init__(self):
        pass

    def __enter__(self):
        STACK.append(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        assert STACK[-1] is self
        STACK.pop()

    def remove_node(self, node):
        pass

    def add_node(self, node):
        pass

    @property
    def host(self):
        return None

    @property
    def workdir(self):
        return None

    @property
    def path_list(self):
        return []

    def relative_path(self, other):
        return "????"

    @property
    def headers(self):
        return [], []


STACK = [Root()]


class Unscoped:
    def __enter__(self):
        STACK.append(self)
        return self

    def add_node(self, node):
        pass

    def remove_node(self, node):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        assert STACK[-1] is self
        STACK.pop()


class Base(Overloaded):
    def __init__(self, name, value=None):
        assert name is not None
        assert isinstance(name, str)

        self._name = name
        self._parent = STACK[-1]
        self.parent.add_node(self)
        self._value = value

    @property
    def parent(self):
        """*Node*: The parent node object."""
        return self._parent

    def __repr__(self):
        try:
            return "%s(%s)" % (type(self).__name__, self.fullname)
        except Exception:
            return "%s(%s)" % (type(self).__name__, self.name)

    @property
    def name(self):
        """*str*: The visible name of the node."""
        return self._name

    @property
    def family(self):
        """Family_: The family object containing the node."""
        return self.parent.family

    @property
    def suite(self):
        """Suite_: The suite object containing the node."""
        return self.parent.suite

    @property
    def anchor(self):
        """*Anchor*: The current anchor (either Suite_ or AnchorFamily_ object) containing the node."""
        return self.parent.anchor

    @property
    def task(self):
        """Task_: The task object containing the node."""
        return self.parent.task

    @property
    def value(self):
        """*str*: The value of the node."""

        if not hasattr(self, "_value"):
            return None

        if callable(self._value):
            return self._value(self)
        return self._value

    def _get_nodes(self, cls, result):
        if isinstance(self, cls):
            result.append(self)
        for n in self.children:
            n._get_nodes(cls, result)


class GenerateError(RuntimeError):
    pass
