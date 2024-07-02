import datetime

import pytest

from pyflow import Family, Suite, Task
from pyflow.base import GenerateError


def test_suite():
    s = Suite("s", ECF_INCLUDE=12, ECF_HOME=23)

    f = s.add_node(Family("f"))
    t1 = f.add_node(Task("t1"))
    t2 = f.add_node(Task("t2"))

    t1.triggers = (t2 == "complete") | (t2 == "aborted")

    t1["DATE"] = 19900101

    t1.FOOO = 42
    t1.BAR = ["ab", "cd", "ef"]
    t2.YMD = (datetime.datetime(2000, 1, 1), datetime.datetime(2010, 1, 1))

    f += Family("g")
    f.g += Task("t4")
    f.g += Task("t5")
    f.g += Task("t6")
    f.g += Task("t7")

    f += Family("h")
    f.h += Task("t4")
    f.h += Task("t5")
    f.h += Task("t6")
    f.h += Task("t7")

    f.families += ["p", "q", "r", "s"]

    s += Task("t3")

    s.t3.triggers = t2.YMD > 2

    # s.t3.trigger = (f.g.t4 == "complete")
    s.t3.completes = f == "aborted"

    f.limits = {"l1": 2, "l2": 4}
    f.t1.limits = ("a", 2)
    f.t1.labels = ("info", "Hello, world!")

    # f.date = (datetime.datetime(2000, 1, 1), datetime.datetime(2010, 1, 1))

    s.limits = [("l1", 2), ("l2", 5)]
    s.t3.inlimits = [s.l1, s.l2]

    f.g.t4 >> f.g.t5 >> f.g.t6 >> f.g.t7

    f.h.t4 << f.h.t5 << f.h.t6 << f.h.t7

    now = datetime.datetime(2000, 1, 1)
    then = now + datetime.timedelta(days=365)

    s.families += "a"
    s.a.tasks += {
        "a": {
            "inlimits": s.l1,
            "FOO": 42,
            "YMD": (now, then),
            "labels": [("info", "hi"), ("status", "ok")],
            "meters": ("progress", 0, 100),
        }
    }

    s.check_definition()


def test_suite_builtin_triggers():
    s = Suite("s", ECF_INCLUDE=12, ECF_HOME=23)

    f = s.add_node(Family("f"))
    t1 = f.add_node(Task("t1"))
    t2 = f.add_node(Task("t2"))

    t1.triggers = t2.complete | t2.aborted

    t1["DATE"] = 19900101

    t1.FOOO = 42
    t1.BAR = ["ab", "cd", "ef"]
    t2.YMD = (datetime.datetime(2000, 1, 1), datetime.datetime(2010, 1, 1))

    f += Family("g")
    f.g += Task("t4")
    f.g += Task("t5")
    f.g += Task("t6")
    f.g += Task("t7")

    f += Family("h")
    f.h += Task("t4")
    f.h += Task("t5")
    f.h += Task("t6")
    f.h += Task("t7")

    f.families += ["p", "q", "r", "s"]

    s += Task("t3")

    s.t3.triggers = t2.YMD > 2

    # s.t3.trigger = (f.g.t4 == "complete")
    s.t3.completes = f.aborted

    f.limits = {"l1": 2, "l2": 4}
    f.t1.limits = ("a", 2)
    f.t1.labels = ("info", "Hello, world!")

    # f.date = (datetime.datetime(2000, 1, 1), datetime.datetime(2010, 1, 1))

    s.limits = [("l1", 2), ("l2", 5)]
    s.t3.inlimits = [s.l1, s.l2]

    f.g.t4 >> f.g.t5 >> f.g.t6 >> f.g.t7

    f.h.t4 << f.h.t5 << f.h.t6 << f.h.t7

    now = datetime.datetime(2000, 1, 1)
    then = now + datetime.timedelta(days=365)

    s.families += "a"
    s.a.tasks += {
        "a": {
            "inlimits": s.l1,
            "FOO": 42,
            "YMD": (now, then),
            "labels": [("info", "hi"), ("status", "ok")],
            "meters": ("progress", 0, 100),
        }
    }

    s.check_definition()


def test_find_node():
    with Suite("sss") as s:
        with Family("f1") as f1:
            with Family("f2") as f2:
                Task("t1")
                t2 = Task("t2")
        with Family("f3"):
            with Family("f4"):
                t3 = Task("t3")
                Task("t4")

    # Test relative paths from the root node

    assert s.find_node("f1/f2") is f2
    assert s.find_node("f3/f4/t3") is t3

    # Test absolute paths from the root node

    assert s.find_node("/sss") is s
    assert s.find_node("/sss/f1/f2") is f2
    assert s.find_node("/sss/f3/f4/t3") is t3

    # Test relative lookups from other nodes

    assert f1.find_node("f2/t2") is t2

    # And some invalid lookups

    with pytest.raises(KeyError):
        s.find_node("")
    with pytest.raises(AssertionError):
        s.find_node("/invalid_root/f1")
    with pytest.raises(KeyError):
        s.find_node("/sss/f4")


def test_exit_hook():
    """
    Propagate exit hook to children
    """

    with Family("f2", exit_hook="hook_f2") as f2:
        t2 = Task("t2", exit_hook="hook_t2")
        with Family("f3", exit_hook="hook_f3") as f3:
            t3 = Task("t3", exit_hook="hook_t3")
            t4 = Task("t4")

    t5 = Task("t5")

    with Suite("S", exit_hook="hook_s", families=f2, tasks=t5):
        with Family("f", exit_hook="hook_f") as f:
            t1 = Task("t1", exit_hook="hook_t1")

    assert f._exit_hook == ["hook_s", "hook_f"]
    assert t1._exit_hook == ["hook_s", "hook_f", "hook_t1"]
    assert f2._exit_hook == ["hook_f2", "hook_s"]
    assert t2._exit_hook == ["hook_f2", "hook_t2", "hook_s"]
    assert f3._exit_hook == ["hook_f2", "hook_f3", "hook_s"]
    assert t3._exit_hook == ["hook_f2", "hook_f3", "hook_t3", "hook_s"]
    assert t4._exit_hook == ["hook_f2", "hook_f3", "hook_s"]
    assert t5._exit_hook == ["hook_s"]


@pytest.mark.parametrize("child", [Task, Family])
def test_generate_error(child):
    with Suite("s") as s:
        with Task("t"):
            child("c")
    with pytest.raises(GenerateError):
        s.generate_node()


if __name__ == "__main__":
    from os import path

    import pytest

    pytest.main(path.abspath(__file__))
