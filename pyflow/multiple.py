from .attributes import Attribute, Event, InLimit, Limit
from .nodes import Family, Node, Suite, Task


class MultipleNode(Node):
    def __init__(self, *names, **kwargs):
        super().__init__("_multi_" + "-".join(names))
        self._names = names
        self._kwargs = kwargs

    def _build(self, ecflow_parent):
        for n in self._names:
            node = self._class(n, **self._kwargs)
            node._nodes.update(self._nodes)
            self.parent.add_node(node)
            node._build(ecflow_parent)
            self.parent.remove_node(node)


class MultipleAttribute(Attribute):
    def __init__(self, *names, **kwargs):
        super().__init__("_multiattr_" + "-".join(names))
        self._names = names
        self._kwargs = kwargs

    def _build(self, ecflow_parent):
        for n in self._names:
            node = self._class(n, **self._kwargs)
            self.parent.add_node(node)
            node._build(ecflow_parent)
            self.parent.remove_node(node)


class Events(MultipleAttribute):
    _class = Event


class InLimits(MultipleAttribute):
    _class = InLimit


class Limits(MultipleAttribute):
    _class = Limit


class Tasks(MultipleNode):
    _class = Task


class Families(MultipleNode):
    _class = Family


class Suites(MultipleNode):
    _class = Suite
