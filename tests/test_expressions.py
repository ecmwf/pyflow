from functools import reduce
from operator import and_

import pytest

import pyflow


def test_triggers_and():
    with pyflow.Suite("s") as s:
        tasks = [pyflow.Task("t1"), pyflow.Task("t2")]
        with pyflow.Task("t3") as t:
            t.triggers = reduce(and_, tasks)
    s.check_definition()


def test_all_complete():
    with pyflow.Suite("s") as s:
        with pyflow.Family("f1"):
            with pyflow.Family("f1f1"):
                pyflow.Task("t1")
                pyflow.Task("t2")
            with pyflow.Family("f1f2"):
                pyflow.Task("t3")
                pyflow.Task("t4")
            pyflow.Task("t5")
        with pyflow.Family("f2"):
            pass

    # Test that this works for both enumeration of arguments, and providing the list

    assert "((/s/f1 eq complete) and (/s/f2 eq complete))" == str(
        pyflow.all_complete(s.executable_children)
    )


def test_trigger_chains():
    """
    Test that the << and >> operators generate chains of dependencies
    AND that they don't clobber existing dependencies
    """

    with pyflow.Suite("s") as s:
        s.tasks += ["t1", "t2", "t3"]

        s.t3.triggers = s.t1.complete

        s.t1 >> s.t2 >> s.t3

    assert "(/s/t1 eq complete)" == str(s.t2._trigger.value)
    assert "((/s/t1 eq complete) and (/s/t2 eq complete))" == str(s.t3._trigger.value)

    with pyflow.Suite("s") as s:
        s.tasks += ["t1", "t2", "t3"]

        s.t1.triggers = s.t3.complete

        s.t1 << s.t2 << s.t3

    assert "(/s/t3 eq complete)" == str(s.t2._trigger.value)
    assert "((/s/t3 eq complete) and (/s/t2 eq complete))" == str(s.t1._trigger.value)


def test_sequence():
    """
    Test the sequence function for folding a collection of nodes with
    the >> operator.

    """

    # Run 3 tasks one after another:
    with pyflow.Suite("s1") as s1:
        tasks = [pyflow.Task("t{}".format(i)) for i in range(3)]

    pyflow.sequence(tasks)
    assert str(s1.t1._trigger.value) == "(/s1/t0 eq complete)"
    assert str(s1.t2._trigger.value) == "(/s1/t1 eq complete)"

    # Run 3 tasks one after another, respecting their existing trigger:
    with pyflow.Suite("s2") as s2:
        main = pyflow.Task("main")
        tasks = [pyflow.Task("t{}".format(i), triggers=main.complete) for i in range(3)]

    pyflow.sequence(tasks)
    assert str(s2.t0._trigger.value) == "(/s2/main eq complete)"
    assert (
        str(s2.t1._trigger.value) == "((/s2/main eq complete) and (/s2/t0 eq complete))"
    )
    assert (
        str(s2.t2._trigger.value) == "((/s2/main eq complete) and (/s2/t1 eq complete))"
    )


if __name__ == "__main__":
    from os import path

    pytest.main(path.abspath(__file__))
