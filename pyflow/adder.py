from __future__ import absolute_import

from .attributes import Attribute
from .base import Base, Unscoped


class NodeAdder:
    def __init__(self, owner, cls, multiple):
        self._owner = owner
        self._class = cls
        self._multiple = multiple

    def __iter__(self):
        return iter(
            [n for n in self._owner._nodes.values() if isinstance(n, self._class)]
        )

    def __iadd__(self, other):
        self.add(other)

    def __iand__(self, other):
        return self.add_and(other)

    def __ior__(self, other):
        return self.add_or(other)

    def add_and(self, other):
        with Unscoped():
            r = self._create(other)
        s = list(self)

        if len(s) == 0:
            self.replace(r[0].value)
            return

        assert len(r) == 1
        assert len(s) == 1
        self.replace(s[0].value & r[0].value)

    def add_or(self, other):
        with Unscoped():
            r = self._create(other)
        s = list(self)

        if len(s) == 0:
            self.replace(r[0].value)
            return

        assert len(r) == 1
        assert len(s) == 1
        self.replace(s[0].value | r[0].value)

    def replace(self, other):
        self._owner.clear_type(self._class)
        self.add(other)

    def _create(self, other):
        assert other is not None

        if isinstance(other, dict):
            other = [it for it in other.items()]

        if not isinstance(other, list):
            other = [other]

        result = []
        for o in other:
            if isinstance(o, tuple):
                if len(o) == 2 and isinstance(o[1], dict):
                    n, kw = o
                    result.append(self._class(n, **kw))
                else:
                    result.append(self._class(*o))
            elif isinstance(o, self._class):
                result.append(self._owner.add_node(o))
            else:
                result.append(self._class(o))

        return result

    def add(self, other):
        # Some attribute types have values that can be added to. Others do not.
        # Select the case where we are adding a non-node value to an existing attribute, and
        # try and add the value (using __iadd__ rather than __add__).
        #
        # If this fails, then use the normal approach
        s = list(self)
        if (
            len(s)
            and issubclass(self._class, Attribute)
            and not isinstance(other, Base)
        ):
            try:
                # Ensure we use __iadd__ rather than __add__ to avoid copies
                existing = s[0].value
                existing += other
                self.replace(existing)
                return self
            except TypeError:
                pass

        with self._owner:
            self._create(other)

        return self

    def __repr__(self):
        name = self._class.__name__
        if name[-1] == "y":
            name = name[:-1] + "ies"
        else:
            name = name + "s"
        return "%s<%s>" % (name, self._owner)

    def __getattr__(self, item):
        s = list(self)
        if len(s) == 1:
            return getattr(s[0], item)
        raise AttributeError
