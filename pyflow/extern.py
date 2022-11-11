import datetime

from .attributes import Event, Meter, RepeatDate
from .base import Root
from .nodes import Family, Suite, Task

KNOWN_EXTERNS = set()


def is_extern_known(ext):
    return ext in KNOWN_EXTERNS


def ExternNode(path, tail_cls=Family):
    """
    Maps an external node, i.e. a node that is not built from the same repository.

    Parameters:
        path(str): Path of the external node.
        tail_cls(class): Object class of the external node.

    Returns:
        *Node*: An object that corresponds to an external node.

    Example::

        pyflow.ExternNode('/a/b/c/d')
    """

    KNOWN_EXTERNS.add(path)

    path_cpts = [p for p in path.split("/") if p != ""]

    cls = Suite
    current = Root()
    for p in path_cpts[:-1]:
        with current:
            current = cls(p, extern=True)
        cls = Family

    with current:
        return tail_cls(path_cpts[-1], extern=True)


def ExternAttribute(path, cls, *args):
    KNOWN_EXTERNS.add(path)
    path, attr = path.split(":")
    with ExternNode(path):
        return cls(attr, *args)


def ExternYMD(path):
    """
    Maps an external repeat date, i.e. a repeat date that is not built from the same repository.

    Parameters:
        path(*str*): Path of the external repeat date.

    Returns:
        RepeatDate_: An object that corresponds to an external repeat date.

    Example::

        pyflow.ExternYMD('/a/b/c/d:YMD')
    """

    return ExternAttribute(
        path, RepeatDate, datetime.datetime.now(), datetime.datetime.now()
    )


def ExternEvent(path):
    """
    Maps an external event, i.e. a event that is not built from the same repository.

    Parameters:
        path(str): Path of the external event.

    Returns:
        Event_: An object that corresponds to an external event.

    Example::

        pyflow.ExternEvent('/e/f/g/h:ev')
    """

    return ExternAttribute(path, Event)


def ExternMeter(path):
    """
    Maps an external meter, i.e. a meter that is not built from the same repository.

    Parameters:
        path(str): Path of the external meter.

    Returns:
        Meter_: An object that corresponds to an external event.

    Example::

        pyflow.ExternMeter('/g/h/i/j:mt')
    """

    return ExternAttribute(path, Meter, 0)


def Extern(path):
    """
    Maps an external family, i.e. a family that is not built from the same repository.

    Parameters:
        path(str): Path of the external family.

    Returns:
        Family_: An object that corresponds to an external family.

    Example::

        pyflow.Extern('/f/g/h/i')
    """

    return ExternNode(path)


def ExternFamily(path):
    """
    Maps an external family, i.e. a family that is not built from the same repository.

    Parameters:
        path(str): Path of the external family.

    Returns:
        Family_: An object that corresponds to an external family.

    Example::

        pyflow.ExternFamily('/f/g/h/i')
    """

    return ExternNode(path)


def ExternTask(path):
    """
    Maps an external task, i.e. a task that is not built from the same repository.

    Parameters:
        path(str): Path of the external task.

    Returns:
        Task_: An object that corresponds to an external task.

    Example::

        pyflow.ExternTask('/a/b/c/d')
    """

    return ExternNode(path, tail_cls=Task)
