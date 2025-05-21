from __future__ import absolute_import

import inspect
import os
import re
from collections import OrderedDict
from functools import reduce
from operator import add

from .adder import NodeAdder
from .anchor import AnchorMixin
from .attributes import (
    Autocancel,
    Complete,
    Cron,
    Date,
    Day,
    Defstatus,
    Event,
    Exportable,
    Follow,
    GeneratedVariable,
    InLimit,
    Label,
    Limit,
    Manual,
    Meter,
    RepeatDay,
    Time,
    Today,
    Trigger,
    Variable,
    Zombies,
    is_variable,
    make_variable,
)
from .base import STACK, Base, GenerateError
from .deployment import FileSystem
from .expressions import Eq, NodeName
from .graph import Dot
from .header import InlineCodeHeader
from .importer import ecflow
from .script import Script
from .state import MAP

# TODO: improve inhibit Trigger, Complete, Inlimit, Late (attributes)?


def ecflow_name(s):
    """
    Converts a string value to one that can be used in names of **ecFlow** objects, by removing or converting illegal
    characters.

    Parameters:
        s(str): A string value to convert.

    Returns:
        *str*: The string value safe for use in names of **ecFlow** objects.

    Example::

        pyflow.ecflow_name('hyphenated-name')
    """

    for c in ["-", " ", "/"]:
        s = s.replace(c, "_")
    return s


def _from_json(node, tree):
    builder = {"defstatus": lambda v: MAP[v]}

    def json_kids(tree):
        n = 0
        for k, v in tree.items():
            if is_variable(k) or _is_reserved(k):
                pass
            else:
                n += 1
        return n

    def json_build(cls, name, tree):
        node = cls(name)
        _from_json(node, tree)
        return node

    with node:
        for k, v in tree.items():
            if is_variable(k) or _is_reserved(k):
                node[k] = builder[k](v) if k in builder else v
            else:
                if json_kids(v):
                    json_build(Family, k, v)
                else:
                    json_build(Task, k, v)


class DuplicateNodeError(RuntimeError):
    def __init__(self, parent, new, existing):
        super().__init__(
            "Cannot add node '{}' to {}: duplicates '{}'".format(new, parent, existing)
        )


class Node(Base):
    def __init__(
        self,
        name,
        json=None,
        host=None,
        modules=None,
        purge_modules=False,
        extern=False,
        workdir=None,
        **kwargs,
    ):
        """
        Base class for all nodes.

        Parameters:
            name(str): Name of the node to create.
            json(dict): Parsed JSON for creation of the children node(s).
            host(Host_): The host to execute the node on.
            modules(tuple): The list of modules to load.
            purge_modules(bool): Causes the generated script to include the code to purge all loaded modules at script
                runtime.
            extern(bool): Whether the node is a shadow node created to satisfy an Extern_, and should not be
                generated.
            workdir(str): The working directory for the tasks, can be fixed or an **ecFlow** variable.
            autocancel(Autocancel_): An attribute for automatic removal of the node which has completed.
            completes(Complete_): An attribute for setting a condition for setting the node as complete depending on
                other tasks or families.
            cron(Cron_): An attribute for setting a cron dependency of the node for the current day.
            date(Date_): An attribute for setting a date dependency of the node.
            day(Day_): An attribute for setting a day of the week dependency of the node.
            defstatus(Defstatus_): An attribute for declaring the default status of the node.
            families(Family_): An attribute for adding a child family on the node.
            follow(Follow_): An attribute for setting a condition for running the node behind another repeated node
                which has completed.
            inlimits(InLimit_): An attribute for grouping of tasks to which a limit should be applied.
            labels(Label_): An attribute for a string value that can be set from a script.
            limits(Limit_): An attribute for a simple load management by limiting the number of tasks submitted by a
                specific **ecFlow** server.
            meters(Meter_): An attribute for a range of integer values that can be set from a script.
            repeat(RepeatDay_): An attribute that allows a node to be repeated infinitely.
            tasks(Task_): An attribute for adding a child task on the node.
            time(Time_): An attribute for setting a time dependency of the node.
            today(Today_): An attribute for setting a cron dependency of the node for the current day.
            triggers(Trigger_): An attribute for setting a condition for running the node depending on other tasks or
                families.
            variables(Variable_): An attribute for setting an **ecFlow** variable.
            generated_variables(GeneratedVariable_): An attribute for setting an **ecFlow** generated variable.
            zombies(Zombies_): An attribute that defines how a zombie should be handled in an automated fashion.
            events(Event_): An attribute for declaring an action that a task can trigger while it is running.
            **kwargs(str): Accept extra keyword arguments as variables to be set on the node.
        """

        super().__init__(name)
        self._nodes = OrderedDict()
        self._functions = set(dir(self))

        self._modules = modules or []
        self._purge_modules = purge_modules
        self._extern = extern

        # If we have changed the host, then set the relevant directories
        self._host = host
        if host is not None:
            for variable_name, variable_val in host.ecflow_variables.items():
                kwargs.setdefault(variable_name, variable_val)

            # If we have set/changed the host, then add a label as decided by the Host object
            with self:
                host.build_label()

        # working directory parameters
        self._workdir = workdir

        if self.__doc__:
            with self:
                Manual(self.__doc__)

        if json is not None:
            _from_json(self, json)

        for k, v in kwargs.items():
            if is_variable(k):
                make_variable(self, k, v)
            else:
                o = getattr(self, k)
                o += v

    def __enter__(self):
        STACK.append(self)
        return self

    def __exit__(self, type, value, traceback):
        assert STACK[-1] is self
        STACK.pop()

    def generate_node(self):
        """
        Generates node definition.

        Returns:
            *Node*: Generated **ecFlow** node object.
        """

        o = self.ecflow_object()

        # N.B. Important safety check. Do not remove. Extern nodes must never be played or generated.
        assert not self._extern, "Generating extern nodes is not permitted"

        for n in list(self._nodes.values()):
            n._build(o)

        return o

    def make_expression(self):
        """
        Generates node expression.

        Returns:
            *bool*: Whether the node is complete or not.
        """

        return self.complete

    def __iadd__(self, node):
        return self.append_node(node)

    def __getattr__(self, item):
        try:
            return self._nodes[item]
        except KeyError:
            raise AttributeError("Node {} does not exist".format(item))

    def _add_single_node(self, node):
        if node.name in self._nodes:
            raise DuplicateNodeError(
                self.fullname, node.name, self._nodes[node.name].fullname
            )

        node.parent.remove_node(node)
        self._nodes[node.name] = node
        node._parent = self

    def add_node(self, node):
        """
        Adds a child to current node.

        Parameters:
            node(*Node*): The child node to add.

        Returns:
            *Node*: Added child node.
        """

        if isinstance(node, list):
            for n in node:
                node = self.add_node(n)
            return node

        self._add_single_node(node)
        return node

    def clear_type(self, cls):
        """
        Removes child nodes of provided type.

        Parameters:
            cls(class): The node type class name.
        """

        for v in list(self._nodes.values()):
            if isinstance(v, cls):
                self.remove_node(v)

    def remove_node(self, node):
        """
        Removes specific child node.

        Parameters:
            node(*Node*): The child node to remove.
        """

        name = node.name
        if name in self._nodes:
            del self._nodes[name]

    def append_node(self, node):
        """
        Appends a child to current node.

        Parameters:
            node(*Node*): The child node to append.

        Returns:
            *Node*: The parent node.
        """

        self.add_node(node)
        return self

    @property
    def host(self):
        """
        Returns the currently active host object.
        If not found in current node, search in parents.

        Returns:
            Host_: Currently active host object.
        """

        if self._host is not None:
            return self._host
        return self.parent.host

    @property
    def workdir(self):
        """
        Returns the currently working directory for tasks.
        If not found in current node, search in parents.

        Returns:
            string: Currently active working directory for tasks.
        """

        if self._workdir is not None:
            return self._workdir
        return self.parent.workdir

    @property
    def all_tasks(self):
        """*list*: The list of all tasks directly contained within a Family_."""
        result = []
        self._get_nodes(Task, result)
        return result

    @property
    def all_families(self):
        """*list*: The list of all tasks directly contained within a Family_."""
        result = []
        self._get_nodes(Family, result)
        self._get_nodes(AnchorFamily, result)
        return result

    def has_variable(self, name):
        """
        Signals if the current node has a variable defined.

        Parameters:
            name(str): Name of the variable to search for.

        Returns:
            *bool*: Whether the current node has the variable defined or not.
        """

        return name in self._nodes and isinstance(self._nodes[name], Variable)

    def lookup_variable(self, name):
        """
        Looks up value of the variable in current or parent node.

        Parameters:
            name(str): Name of the variable to look up for.

        Returns:
            *str*: Variable value, if found.
        """

        if name in self._nodes:
            return self._nodes[name].value
        return self.parent.lookup_variable(name)

    def lookup_variable_value(self, name, default=None):
        """
        Looks up value of the variable in current or parent node, with fallback on the provided default value.

        Parameters:
            name(str): Name of the variable to look up for.
            default(str): Default valueName of the variable to look up for.

        Returns:
            *str*: Variable value, if found. Otherwise provided default value.
        """

        try:
            return self.lookup_variable(name)
        except AttributeError:
            if default is not None:
                return default
            raise ValueError("Variable {} is not defined".format(name))

    @property
    def all_variables(self):
        """*dict*: The dictionary of all variables in the current or parent node."""
        all_vars = self.parent.all_variables if isinstance(self.parent, Node) else {}
        for v in self.variables:
            all_vars[v.name] = v

        return all_vars

    @property
    def all_exportables(self):
        """*dict*: The dictionary of all exportable attributes in the current or parent node."""
        all_vars = self.parent.all_exportables if isinstance(self.parent, Node) else {}
        for v in self._get_accessor(Exportable):
            all_vars[v.name] = v

        return all_vars

    ##########################################################
    @property
    def aborted(self):
        """*bool*: The node aborted status."""
        return Eq(NodeName(self), "aborted")

    @property
    def complete(self):
        """*bool*: The node complete status."""
        return Eq(NodeName(self), "complete")

    @property
    def unknown(self):
        """*bool*: The node unknown status."""
        return Eq(NodeName(self), "unknown")

    @property
    def queued(self):
        """*bool*: The node queued status."""
        return Eq(NodeName(self), "queued")

    @property
    def submitted(self):
        """*bool*: The node submitted status."""
        return Eq(NodeName(self), "submitted")

    @property
    def active(self):
        """*bool*: The node active status."""
        return Eq(NodeName(self), "active")

    def __eq__(self, other):
        if isinstance(other, str):
            return Eq(NodeName(self), other)
        return super().__eq__(other)

    def __ne__(self, other):
        if isinstance(other, str):
            return Eq(NodeName(self), other)
        return super().__ne__(other)

    def __hash__(self):
        return hash(self.fullname)

    @property
    def manual(self):
        """*str,list*: The manual of the node, i.e. help text."""
        return self._get_accessor(Manual, False)

    @manual.setter
    def manual(self, value):
        self._set_accessor(Manual, value, False)

    def task_purge_modules(self):
        """
        Causes the generated script to include the code to purge all loaded modules at script runtime.

        Returns:
            *bool*: Whether the modules have been purged or not.
        """
        return self._purge_modules or (
            self.suite is not self and self.parent.task_purge_modules()
        )

    def task_modules(self):
        """
        Returns list of modules.

        Returns:
            *list*: List of modules.
        """

        parent_modules = self.parent.task_modules() if self.suite is not self else []
        return parent_modules + (self._modules or [])

    @property
    def modules(self):
        """*list*: The list of environment modules for the node."""
        return self._modules

    @modules.setter
    def modules(self, value):
        assert isinstance(value, list)
        self._modules = value

    ##########################################################
    @property
    def fullname(self):
        """*str*: The full path of the node from the root."""
        return "/".join([""] + self.path_list)

    def _relative_path(self, node):
        if self.suite is not node.suite:
            return self.fullname

        return os.path.relpath(self.fullname, node.parent.fullname)

    def relative_path(self, node):
        """
        Returns relative path of the node.

        Returns:
            *str*: Relative path of the node.
        """

        try:
            f = self._relative_path(node)
        except Exception:
            raise RuntimeError(
                "Cannot determine relative path between {} and {}".format(self, node)
            )

        if f[0].isdigit():
            f = "./" + f

        return f

    def find_node(self, subpath):
        """
        Returns node under provided path.

        Parameters:
            subpath(str): Path of the node to search for.

        Returns:
            *Node*: The found node object.
        """

        node_bits = subpath.split("/")

        node = self
        for subnode in node_bits:
            node = node[subnode]

        return node

    @property
    def path_list(self):
        """*list*: The list of node paths."""
        return self.parent.path_list + [self.name]

    def replace_on_server(self, host, port=None):
        """
        Replaces node on the target host.

        Parameters:
            host(Host_): Target host.
            port(str): Port number of the target host.
        """

        # N.B. Important safety check. Do not remove. Extern nodes must never be played or generated.
        assert (
            not self._extern
        ), "Attempting to play extern nodes to the server is not permitted"

        if "@" in host:
            h = host.split("@")
        else:
            h = host.split(":")
        if len(h) == 1:
            h.append(port or "3141")
        ci = ecflow.Client(*h)
        ci.replace(self.fullname, self.ecflow_definition(), True, True)

    def check_definition(self):
        """
        Checks **ecFlow** definitions of the node.

        Raises:
            *RuntimeError*: **ecFlow** definitions failed checks.
        """

        ret = self.ecflow_definition().check()
        if ret != "":
            raise RuntimeError("ecflow definitions failed checks: {}".format(ret))

    def ecflow_definition(self):
        """
        Returns node definition.

        Returns:
            *ecflow.Defs*: The node definition.
        """
        d = ecflow.Defs()
        d.add_suite(self.suite.generate_node())

        # Break a nasty circular dependency. Not clear how else to do it.
        # Check that any referenced externs are legit!
        from .extern import is_extern_known

        d.auto_add_externs(True)
        for ext in d.externs:
            assert is_extern_known(ext), "Attempting to add unknown extern reference"

        return d

    def __rshift__(self, other):
        if isinstance(other, Node):
            other.triggers &= self.complete
            return other
        super().__rshift__(other)

    def __lshift__(self, other):
        if isinstance(other, Node):
            self.triggers &= other.complete
            return other
        super().__lshift__(other)

    ####################################################

    def _get_accessor(self, cls, multiple=True):
        return NodeAdder(self, cls, multiple)

    def _set_accessor(self, cls, value, multiple=True):
        if value is None:
            return self

        if not isinstance(value, NodeAdder):
            NodeAdder(self, cls, multiple).replace(value)

        return self

    ################################################

    def __setattr__(self, name, value):
        if is_variable(name):
            # If the variable already exists, remove it first
            if name in self._nodes:
                del self._nodes[name]
            return make_variable(self, name, value)

        return object.__setattr__(self, name, value)

    def __setitem__(self, key, value):
        if isinstance(key, type):
            return self._set_accessor(type, value)

        return self.__setattr__(key, value)

    def __getitem__(self, key):
        if isinstance(key, slice) and key == slice(None):
            return self.children

        if isinstance(key, type):
            return self._get_accessor(key)

        return self._nodes[key]

    def __delitem__(self, key):
        del self._nodes[key]

    def __contains__(self, item):
        return item in self._nodes

    @property
    def children(self):
        """*list*: The list of all direct child nodes."""
        return self._nodes.values()

    @property
    def executable_children(self):
        """*list*: The list of all tasks and families directly contained within a Family_."""
        return [child for child in self.children if isinstance(child, (Family, Task))]

    @property
    def headers(self):
        """*list*: The current and parent node headers, including head and tail."""

        def convert(cls, code, what):
            if isinstance(code, tuple):
                return InlineCodeHeader(
                    *code, include_path=self.anchor.include_path, what=what
                )
            if isinstance(code, str):
                return InlineCodeHeader(
                    cls.__name__.lower(),
                    code,
                    include_path=self.anchor.include_path,
                    what=what,
                )
            return code

        head = []
        tail = []

        if "head" in self.__dict__:
            head.append(convert(self.__class__, self.__dict__["head"], "head"))
        if "tail" in self.__dict__:
            tail.append(convert(self.__class__, self.__dict__["tail"], "tail"))

        for cls in inspect.getmro(self.__class__):
            if "head" in cls.__dict__:
                head.append(convert(cls, cls.__dict__["head"], "head"))
            if "tail" in cls.__dict__:
                tail.append(convert(cls, cls.__dict__["tail"], "tail"))

        parent_head, parent_tail = self.parent.headers

        return parent_head + list(reversed(head)), tail + parent_tail

    ################################################

    shape = None

    def draw_tree(self):
        """
        Draws node tree as a DOT graph.

        Returns:
            *Dot*: The node DOT graph.
        """

        dot = Dot(fullnames=False)
        self._tree(dot)
        return dot

    def _tree(self, dot):
        try:
            dot.edge(self.parent, self)
        except Exception:
            pass
        for n in self._nodes.values():
            if n.name[0] != "_":
                try:
                    n._tree(dot)
                except Exception:
                    pass

    ################################################
    def draw_graph(self, view=True):
        """
        Draws the DOT graph.

        Parameters:
            view(bool): Unused.

        Returns:
            *Dot*: DOT graph.
        """

        dot = Dot()
        self._graph(dot)
        # dot.save("test.gv")
        return dot

    def _graph(self, dot):
        for n in self._nodes.values():
            n._graph(dot)

    @property
    def to_html(self):
        """*str*: The representation of the node in HTML."""
        from .html import HTMLWrapper

        return HTMLWrapper(str(self.generate_node()))

    def _repr_html_(self):
        return str(self.to_html)

    def __str__(self):
        return str(self.generate_node())

    def generate_stub(self, scripts):
        """Returns complete script by combining the fragments.

        Parameters:
            scripts(tuple): List of script fragments.

        Returns:
            *str*: Complete script.
        """

        return reduce(add, [n.generate_stub() for n in scripts], [])


################################################


class Family(Node):
    family_gen_vars = ["FAMILY", "FAMILY1"]

    def __init__(
        self,
        name,
        json=None,
        modules=None,
        purge_modules=False,
        extern=False,
        exit_hook=None,
        **kwargs,
    ):
        """
        Provides both visual and logical grouping of related families and tasks.

        Parameters:
            name(str): The name of the family to create.
            json(dict): Parsed JSON for creating the children node(s).
            host(Host_): The host to execute the family on.
            modules(tuple): The list of modules to load.
            purge_modules(bool): Causes the generated script to include the code to purge all loaded modules at script
                runtime.
            extern(bool): Whether the family is a shadow node created to satisfy an Extern_, and should not be
                generated.
            exit_hook(str,list): a script containing some commands to be called at exit time.
            workdir(string): Working directory for tasks.
            autocancel(Autocancel_): An attribute for automatic removal of the node which has completed.
            completes(Complete_): An attribute for setting a condition for setting the node as complete depending on
                other tasks or families.
            cron(Cron_): An attribute for setting a cron dependency of the node for the current day.
            date(Date_): An attribute for setting a date dependency of the node.
            day(Day_): An attribute for setting a day of the week dependency of the node.
            defstatus(Defstatus_): An attribute for declaring the default status of the node.
            families(Family_): An attribute for adding a child family on the node.
            follow(Follow_): An attribute for setting a condition for running the node behind another repeated node
                which has completed.
            inlimits(InLimit_): An attribute for grouping of tasks to which a limit should be applied.
            labels(Label_): An attribute for a string value that can be set from a script.
            limits(Limit_): An attribute for a simple load management by limiting the number of tasks submitted by a
                specific **ecFlow** server.
            meters(Meter_): An attribute for a range of integer values that can be set from a script.
            repeat(RepeatDay_): An attribute that allows a node to be repeated infinitely.
            tasks(Task_): An attribute for adding a child task on the node.
            time(Time_): An attribute for setting a time dependency of the node.
            today(Today_): An attribute for setting a cron dependency of the node for the current day.
            triggers(Trigger_): An attribute for setting a condition for running the node depending on other tasks or
                families.
            variables(Variable_): An attribute for setting an **ecFlow** variable.
            generated_variables(GeneratedVariable_): An attribute for setting an **ecFlow** generated variable.
            zombies(Zombies_): An attribute that defines how a zombie should be handled in an automated fashion.
            events(Event_): An attribute for declaring an action that a task can trigger while it is running.
            **kwargs(str): Accept extra keyword arguments as variables to be set on the family.

        Example::

            with pyflow.Family('f', labels={'foo': 'bar'}) as f:
                pass
        """

        self._exit_hook = []

        generated_variables = kwargs.pop("generated_variables", [])
        generated_variables += self.family_gen_vars
        super().__init__(
            name,
            json=json,
            modules=modules,
            purge_modules=purge_modules,
            extern=extern,
            generated_variables=generated_variables,
            **kwargs,
        )
        if exit_hook is not None:
            self._add_exit_hook(exit_hook)

    def ecflow_object(self):
        """
        Returns the corresponding **ecFlow** family object.

        Returns:
            *ecflow.Family*: **ecFlow** family object.
        """

        return ecflow.Family(str(self._name))

    @property
    def family(self):
        """Family_: The family object."""
        return self

    @property
    def manual_path(self):
        """*str*: The deployment path of the current task, may be `None`."""

        """
        n.b. we do permit generating a None deploy path, as this is acceptable when
        generating and deploying a suite to notebooks. The filesystem mechanism asserts
        aggressively on this.
        """
        try:
            return os.path.join(self.anchor.files_path, f"{self.name}.man")
        except ValueError:
            return None

    def _build(self, ecflow_parent):
        if isinstance(ecflow_parent, ecflow.Task):
            raise GenerateError(
                "Cannot add Family '{}' to Task '{}'".format(
                    self.name, ecflow_parent.name
                )
            )
        ecflow_parent.add_family(self.generate_node())

    def _add_single_node(self, node):
        if isinstance(node, (Family, Task)):
            node._add_exit_hook(self._exit_hook)
        super()._add_single_node(node)

    def _add_exit_hook(self, hook):
        if isinstance(hook, str):
            hook = [hook]
        for hk in hook:
            if hk not in self._exit_hook:
                self._exit_hook.append(hk)
        # Check if properly initialised
        if "_nodes" in self.__dict__:
            for chld in self.executable_children:
                chld._add_exit_hook(hook)


class AnchorFamily(AnchorMixin, Family):
    def __init__(
        self,
        name,
        json=None,
        modules=None,
        purge_modules=False,
        extern=False,
        exit_hook=None,
        **kwargs,
    ):
        """
        Provides grouping of tasks that require encapsulation.

        Parameters:
            name(str): Name of the anchor family to create.
            json(dict): Parsed JSON for creation of the children node(s).
            host(Host_): The host to execute the anchor family on.
            modules(tuple): The list of modules to load.
            purge_modules(bool): Causes the generated script to include the code to purge all loaded modules at script
                runtime.
            extern(bool): Whether the anchor family is a shadow node created to satisfy an Extern_, and should not be
                generated.
            exit_hook(str,list): a script containing some commands to be called at exit time.
            autocancel(Autocancel_): An attribute for automatic removal of the node which has completed.
            completes(Complete_): An attribute for setting a condition for setting the node as complete depending on
                other tasks or families.
            cron(Cron_): An attribute for setting a cron dependency of the node for the current day.
            date(Date_): An attribute for setting a date dependency of the node.
            day(Day_): An attribute for setting a day of the week dependency of the node.
            defstatus(Defstatus_): An attribute for declaring the default status of the node.
            families(Family_): An attribute for adding a child family on the node.
            follow(Follow_): An attribute for setting a condition for running the node behind another repeated node
                which has completed.
            inlimits(InLimit_): An attribute for grouping of tasks to which a limit should be applied.
            labels(Label_): An attribute for a string value that can be set from a script.
            limits(Limit_): An attribute for a simple load management by limiting the number of tasks submitted by a
                specific **ecFlow** server.
            meters(Meter_): An attribute for a range of integer values that can be set from a script.
            repeat(RepeatDay_): An attribute that allows a node to be repeated infinitely.
            tasks(Task_): An attribute for adding a child task on the node.
            time(Time_): An attribute for setting a time dependency of the node.
            today(Today_): An attribute for setting a cron dependency of the node for the current day.
            triggers(Trigger_): An attribute for setting a condition for running the node depending on other tasks or
                families.
            variables(Variable_): An attribute for setting an **ecFlow** variable.
            zombies(Zombies_): An attribute that defines how a zombie should be handled in an automated fashion.
            events(Event_): An attribute for declaring an action that a task can trigger while it is running.
            **kwargs(str): Accept extra keyword arguments as variables to be set on the anchor family.

        Example::

            with pyflow.AnchorFamily('af', labels={'foo': 'bar'}) as af:
                pass
        """

        super().__init__(
            name,
            json=json,
            modules=modules,
            purge_modules=purge_modules,
            extern=extern,
            exit_hook=exit_hook,
            **kwargs,
        )


class Suite(AnchorMixin, Node):
    suite_gen_vars = [
        "DATE",
        "DAY",
        "DD",
        "DOW",
        "DOY",
        "ECF_CLOCK",
        "ECF_DATE",
        "ECF_JULIAN",
        "ECF_TIME",
        "ECF_MM",
        "ECF_MONTH",
        "TIME",
        "YYYY",
    ]

    def __init__(self, name, host=None, exit_hook=None, *args, **kwargs):
        """
        Represents a collection of interrelated **ecFlow** tasks.

        Parameters:
            name(str): Name of the suite to create.
            host(Host_): The host to execute the suite on. If `None`, default **ecFlow** behaviour will be used.
            exit_hook(str,list): a script containing some commands to be called at exit time.
            json(dict): Parsed JSON for creation of the children node(s).
            workdir(str): The working directory for the tasks, can be fixed or an **ecFlow** variable.
            modules(tuple): The list of modules to load.
            purge_modules(bool): Causes the generated script to include the code to purge all loaded modules at script
                runtime.
            extern(bool): Whether the suite is a shadow node created to satisfy an Extern_, and should not be
                generated.
            autocancel(Autocancel_): An attribute for automatic removal of the node which has completed.
            completes(Complete_): An attribute for setting a condition for setting the node as complete depending on
                other tasks or families.
            cron(Cron_): An attribute for setting a cron dependency of the node for the current day.
            date(Date_): An attribute for setting a date dependency of the node.
            day(Day_): An attribute for setting a day of the week dependency of the node.
            defstatus(Defstatus_): An attribute for declaring the default status of the node.
            families(Family_): An attribute for adding a child family on the node.
            follow(Follow_): An attribute for setting a condition for running the node behind another repeated node
                which has completed.
            inlimits(InLimit_): An attribute for grouping of tasks to which a limit should be applied.
            labels(Label_): An attribute for a string value that can be set from a script.
            limits(Limit_): An attribute for a simple load management by limiting the number of tasks submitted by a
                specific **ecFlow** server.
            meters(Meter_): An attribute for a range of integer values that can be set from a script.
            repeat(RepeatDay_): An attribute that allows a node to be repeated infinitely.
            tasks(Task_): An attribute for adding a child task on the node.
            time(Time_): An attribute for setting a time dependency of the node.
            today(Today_): An attribute for setting a cron dependency of the node for the current day.
            triggers(Trigger_): An attribute for setting a condition for running the node depending on other tasks or
                families.
            variables(Variable_): An attribute for setting an **ecFlow** variable.
            generated_variables(GeneratedVariable_): An attribute for setting an **ecFlow** generated variable.
            zombies(Zombies_): An attribute that defines how a zombie should be handled in an automated fashion.
            events(Event_): An attribute for declaring an action that a task can trigger while it is running.
            **kwargs(str): Accept extra keyword arguments as variables to be set on the suite.

        Example::

            with pyflow.Suite('s',
                              host=pyflow.LocalHost(),
                              defstatus=pyflow.state.suspended,
                              FOO='BAR') as s:
                pass
        """

        """
        We must always have a host defined --> Use the default ecflow behaviour if none specified
        """
        if host is None:
            # We require a local import here to break a circular dependency.
            from .host import EcflowDefaultHost

            host = EcflowDefaultHost()

        self._exit_hook = []

        generated_variables = kwargs.pop("generated_variables", [])
        generated_variables += self.suite_gen_vars

        super().__init__(
            name,
            host=host,
            generated_variables=generated_variables,
            *args,
            **kwargs,
        )

        if exit_hook is not None:
            self._add_exit_hook(exit_hook)

    def ecflow_object(self):
        """
        Returns the corresponding **ecFlow** suite object.

        Returns:
            *ecflow.Suite*: **ecFlow** suite object.
        """

        n = ecflow.Suite(self._name)
        return n

    @property
    def suite(self):
        """Suite_: The suite object."""
        return self

    @property
    def family(self):
        return None

    @property
    def task(self):
        return None

    def relative_path(self, node):
        """
        Returns relative path of the suite.

        Parameters:
            node(*Node*): Unused.

        Returns:
            *str*: Relative path of the suite.
        """

        return self.fullname

    def find_node(self, subpath):
        """
        Returns node under provided relative path.

        Parameters:
            subpath(str): Relative path of the node to search for.

        Returns:
            *Node*: Found node object.
        """

        if len(subpath) > 0 and subpath[0] == "/":
            root_name = subpath[1:].split("/")[0]
            assert self.name == root_name

            if "/" not in subpath[1:]:
                return self
            else:
                subpath = subpath[2 + subpath[1:].index("/") :]

        return super().find_node(subpath)

    def deploy_suite(self, target=FileSystem, node=None, **options):
        """
        Deploys suite and its components.

        Parameters:
            target(Deployment): Deployment target for the suite.
            node(str): Path to node to limit deployment to a family/task.
            **options(dict): Accept extra keyword arguments as deployment options.

        Returns:
            *Deployment*: Deployment target object.
        """

        # N.B. Important safety check. Do not remove. Extern nodes must never be played or generated.
        assert not self._extern, "Attempting to deploy extern node not permitted"

        target = target(self, **options)
        node = self.find_node(node) if node is not None else self

        for t in node.all_tasks:
            script, includes = t.generate_script()
            try:
                target.deploy_task(t.deploy_path, script, includes)
            except RuntimeError:
                print(f"\nERROR when deploying task: {t.fullname}\n")
                raise
        for f in node.all_families:
            manual = self.generate_stub(f.manual)
            if manual:
                target.deploy_manual(f.manual_path, manual)

        target.deploy_headers()
        return target

    def _add_single_node(self, node):
        if isinstance(node, (Family, Task)):
            node._add_exit_hook(self._exit_hook)
        super()._add_single_node(node)

    def _add_exit_hook(self, hook):
        if isinstance(hook, str):
            hook = [hook]
        for hk in hook:
            if hk not in self._exit_hook:
                self._exit_hook.append(hk)
        # Check if properly initialised
        if "_nodes" in self.__dict__:
            for chld in self.executable_children:
                chld._add_exit_hook(hook)


class Task(Node):
    SHELLVAR = re.compile("\\$\\{?([A-Z_][A-Z0-9_]*)")
    task_gen_vars = [
        "ECF_JOB",
        "ECF_JOBOUT",
        "ECF_NAME",
        "ECF_PASS",
        "ECF_RID",
        "ECF_SCRIPT",
        "ECF_TRYNO",
        "TASK",
    ]

    def __init__(
        self,
        name,
        autolimit=True,
        submit_arguments=None,
        exit_hook=None,
        clean_workdir=False,
        **kwargs,
    ):
        """
        Describes what should be carried out as one executable unit within an **ecFlow** suite.

        Parameters:
            autolimit(bool): Whether to automatically add the task to the executing hosts limit, if it has one.
            submit_arguments(dict, str): Job submission arguments, can be passed as a dictionary or a string pointing
                to an entry in the dictionary given to the host.
            exit_hook(str,list): a script containing some commands to be called at exit time.
            clean_workdir(bool): Whether to ensure that the working directory is empty.+
            script(str,list): The script command or the list of script commands associated with the task.
            json(dict): Parsed JSON for creation of the children node(s).
            host(Host_): The host to execute the task on.
            modules(tuple): The list of modules to load.
            purge_modules(bool): Causes the generated script to include the code to purge all loaded modules at script
                runtime.
            extern(bool): Whether the task is a shadow node created to satisfy an Extern_, and should not be
                generated.
            autocancel(Autocancel_): An attribute for automatic removal of the node which has completed.
            completes(Complete_): An attribute for setting a condition for setting the node as complete depending on
                other tasks or families.
            cron(Cron_): An attribute for setting a cron dependency of the node for the current day.
            date(Date_): An attribute for setting a date dependency of the node.
            day(Day_): An attribute for setting a day of the week dependency of the node.
            defstatus(Defstatus_): An attribute for declaring the default status of the node.
            families(Family_): An attribute for adding a child family on the node.
            follow(Follow_): An attribute for setting a condition for running the node behind another repeated node
                which has completed.
            inlimits(InLimit_): An attribute for grouping of tasks to which a limit should be applied.
            labels(Label_): An attribute for a string value that can be set from a script.
            limits(Limit_): An attribute for a simple load management by limiting the number of tasks submitted by a
                specific **ecFlow** server.
            meters(Meter_): An attribute for a range of integer values that can be set from a script.
            repeat(RepeatDay_): An attribute that allows a node to be repeated infinitely.
            tasks(Task_): An attribute for adding a child task on the node.
            time(Time_): An attribute for setting a time dependency of the node.
            today(Today_): An attribute for setting a cron dependency of the node for the current day.
            triggers(Trigger_): An attribute for setting a condition for running the node depending on other tasks or
                families.
            variables(Variable_): An attribute for setting an **ecFlow** variable.
            generated_variables(GeneratedVariable_): An attribute for setting an **ecFlow** generated variable.
            zombies(Zombies_): An attribute that defines how a zombie should be handled in an automated fashion.
            events(Event_): An attribute for declaring an action that a task can trigger while it is running.
            **kwargs(str): Accept extra keyword arguments as variables to be set on the task.

        Example::

            with pyflow.Task('t', script='echo "Hello, world!"', FOO='bar') as t:
                pass
        """

        self.script = kwargs.pop("script", Script())
        self._clean_workdir = clean_workdir
        self._submit_arguments = submit_arguments or {}
        self._exit_hook = []

        generated_variables = kwargs.pop("generated_variables", [])
        generated_variables += self.task_gen_vars

        super().__init__(name, generated_variables=generated_variables, **kwargs)
        # Setting this here ensures that exit hooks inherited from parents are
        # ordered first
        if exit_hook is not None:
            self._add_exit_hook(exit_hook)

        # Get the host object, and attempt to add this task to its limits automatically.
        if autolimit:
            host = self.host
            if host is not None:
                host.host_postamble  # Unused, but access to trigger exception as early as possible
                host.add_to_limits(self)

    def ecflow_object(self):
        """
        Returns the corresponding **ecFlow** task object.

        Returns:
            *ecflow.Task*: **ecFlow** task object.
        """

        return ecflow.Task(str(self._name))

    def _build(self, ecflow_parent):
        if isinstance(ecflow_parent, ecflow.Task):
            raise GenerateError(
                "Cannot add '{}' to task '{}'".format(self.name, ecflow_parent.name())
            )
        ecflow_parent.add_task(self.generate_node())

    def add_family(self, item):
        raise GenerateError(
            "Cannot add family '{}' to task '{}'".format(item.name, self.name)
        )

    def add_task(self, item):
        raise GenerateError(
            "Cannot add task '{}' to task '{}'".format(item.name, self.name)
        )

    @property
    def task(self):
        """Task_: The task object."""
        return self

    @property
    def script(self):
        """Script_: The script object."""
        assert isinstance(self._script, Script)
        return self._script

    @script.setter
    def script(self, value):
        self._script = value if isinstance(value, Script) else Script(value)

    @property
    def submit_arguments(self):
        """*dict*: The dictionary of submit arguments."""
        return self._submit_arguments

    @submit_arguments.setter
    def submit_arguments(self, value):
        self._submit_arguments = value

    @property
    def deploy_extension(self):
        """*str*: The script file extension to be used during deployment of the task."""
        return self.lookup_variable_value("ECF_EXTN", ".ecf")

    @property
    def deploy_path(self):
        """*str*: The deployment path of the current task, may be `None`."""

        """
        n.b. we do permit generating a None deploy path, as this is acceptable when
        generating and deploying a suite to notebooks. The filesystem mechanism asserts
        aggressively on this.
        """
        try:
            return "{}{}".format(
                os.path.join(self.anchor.files_path, self.name),
                self.deploy_extension,
            )
        except ValueError:
            return None

    def task_modules(self):
        """
        Returns list of task modules.

        Returns:
            *list*: List of task modules.
        """

        return list(self.host.modules) + super().task_modules()

    def task_purge_modules(self):
        """
        Causes the generated script to include the code to purge all loaded modules at script runtime.

        Returns:
            *bool*: Whether the host or task modules have been purged or not.
        """

        return self.host.purge_modules or super().task_purge_modules()

    def _add_exit_hook(self, hook: str):
        if isinstance(hook, str):
            hook = [hook]
        for hk in hook:
            if hk not in self._exit_hook:
                self._exit_hook.append(hk)

    def generate_script(self):
        """
        Generates the complete script for the task.

        Returns:
            *str*: Complete script for the task.
        """
        try:
            script = self.generate_stub([self.script])
        except Exception as e:
            raise RuntimeError(
                "Failed to generate script for {}".format(self.fullname)
            ) from e
        manual = self.generate_stub(self.manual)
        heads, tails = self.headers

        lines = []

        if manual:
            lines += manual
            # There MUST NOT be a newline added here. This breaks job submission with SLURM
            # (must start with #! after %end after %manual)

        # Add the shebang. n.b. We ONLY support bash (for now). TODO: Other types of shell?
        # TODO: Submit arguments in script
        lines += ["#!/bin/bash", ""]
        lines += self.host.script_submit_arguments(self._submit_arguments)
        lines += [
            # '',
            'echo "Running on: $(hostname)" || true',
            "set -x # echo script lines as they are executed",
            "set -e # stop the shell on first error",
            "set -u # fail when using an undefined variable",
            "",
        ]

        lines += self.host.preamble(self._exit_hook)

        module_lines = []
        if self.host.module_source:
            module_lines.append('source "{}"'.format(self.host.module_source))
        if self.task_purge_modules():
            module_lines.append("module purge")
        for mod in self.task_modules():
            if mod[0] == "-":
                module_lines.append(
                    "module rm {} &> /dev/null".format(mod[1:].split("/")[0])
                )
            else:
                module_lines.append(
                    "module rm {} &> /dev/null || true".format(mod.split("/")[0])
                )
                module_lines.append("module load {} &> /dev/null".format(mod))

        # Generate the workdir code here, even if it is used later, as it is needed to evaluate the used variables
        if self.workdir is None:
            workdir = self.host.workdir
        else:
            workdir = self.workdir

        if workdir is not None:
            workdir_lines = []
            if self._clean_workdir:
                workdir_lines.append('[[ -d "{0}" ]] && rm -rf "{0}"'.format(workdir))
            workdir_lines += [
                '[[ -d "{0}" ]] || mkdir -p "{0}"'.format(workdir),
                'cd "{}"'.format(workdir),
            ]
        else:
            workdir_lines = []

        # Add the environment variables such as $FOO, ${BAR}, ${VAR:-'var'}, etc.
        # and check if they are in the list of ecflow variables
        # n.b. this is done before the heads, so that the heads can use these variables.

        all_scripts = "\n".join(script + workdir_lines + module_lines)
        used_vars = set(v for v in self.SHELLVAR.findall(all_scripts))
        used_vars |= set(e.name for e in self.script.required_exportables())

        exportables = self.all_exportables

        # Add nodes explicitly marked for exporting
        for name, n in exportables.items():
            if n.export:
                used_vars.add(name)

        used_vars = sorted(v for v in used_vars if v in exportables)

        if used_vars:
            lines += ['export {}="%{}%"'.format(v, v) for v in used_vars]
            lines += [""]

        # Add the heads
        if heads:
            lines += ["%include <{}>".format(h.include_name) for h in heads]
            lines.append("")

        # Select the current working directory, if set

        if module_lines:
            lines += module_lines + [""]

        lines += workdir_lines
        lines += ['echo "Current working directory: $(pwd)"', ""]

        # Add the script
        lines += ["%nopp", ""]
        lines += script
        lines += ["", "%end", ""]

        # Add the tails
        if tails:
            lines += ["%include <{}>".format(t.include_name) for t in tails]
            lines.append("")

        lines += self.host.host_postamble

        return lines, heads + tails


################################################


ACCESSORS = [
    ("autocancel", Autocancel),
    ("completes", Complete),
    ("cron", Cron),
    ("date", Date),
    ("day", Day),
    ("defstatus", Defstatus),
    ("families", Family),
    ("follow", Follow),
    ("inlimits", InLimit),
    ("labels", Label),
    ("limits", Limit),
    ("meters", Meter),
    ("repeat", RepeatDay),
    ("tasks", Task),
    ("time", Time),
    ("today", Today),
    ("triggers", Trigger),
    ("variables", Variable),
    ("generated_variables", GeneratedVariable),
    ("zombies", Zombies),
    ("events", Event),
]


def _get_accessor(cls):
    def wrapped(self):
        return self._get_accessor(cls)

    return wrapped


def _set_accessor(cls):
    def wrapped(self, value):
        return self._set_accessor(cls, value)

    return wrapped


def _get_doc(cls):
    doc = cls.__doc__

    if doc is None:
        return None

    return "%s_: %s" % (
        cls.__name__,
        doc.split("\n")[1],
    )  # prepend the first paragraph with a link to the class docs


RESERVED = {"script"}

for name, cls in ACCESSORS:
    RESERVED.add(name)
    setattr(Node, name, property(_get_accessor(cls), _set_accessor(cls)))
    setattr(getattr(Node, name), "__doc__", _get_doc(cls))


def _is_reserved(name):
    return name in RESERVED
