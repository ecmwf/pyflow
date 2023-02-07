import datetime
import os

import pytest

from pyflow import (
    Event,
    ExternEvent,
    ExternFamily,
    ExternMeter,
    ExternTask,
    ExternYMD,
    Family,
    Meter,
    Notebook,
    RepeatDate,
    Suite,
    Task,
)
from pyflow.extern import KNOWN_EXTERNS

now = datetime.datetime.now()


def test_extern():
    with Suite("s") as s:
        t1 = Task("t1", YMD=(now, now))

        et = ExternTask("/a/b/c/d")
        ef = ExternFamily("/f/g/h/i")

        t1.triggers = et & ef

    # Check that the externs have real types --> will have correct functionality available

    assert isinstance(et, Task)
    assert et.name == "d"
    assert et.fullname == "/a/b/c/d"
    assert isinstance(ef, Family)
    assert ef.name == "i"
    assert ef.fullname == "/f/g/h/i"

    # Check that they work!

    s.check_definition()
    s.generate_node()
    s.deploy_suite(target=Notebook)

    # Check that externs are correctly added to the nodes

    defs = str(s.ecflow_definition())

    assert "extern /a/b/c/d\n" in defs
    assert "extern /f/g/h/i\n" in defs
    assert defs.index("extern /a/b/c/d") < defs.index("suite s")
    assert defs.index("extern /f/g/h/i") < defs.index("suite s")

    # Check that if an external reference has slipped in incorrectly, it doesn't get added
    # to the defs without a fight

    KNOWN_EXTERNS.remove("/a/b/c/d")

    with pytest.raises(AssertionError) as excinfo:
        s.ecflow_definition()
    assert excinfo.value.args == ("Attempting to add unknown extern reference",)


def test_extern_attributes():
    with Suite("s") as s:
        eymd = ExternYMD("/a/b/c/d:YMD")
        eevent = ExternEvent("/e/f/g/h:ev")
        emeter = ExternMeter("/g/h/i/j:mt")

        Task("t1", YMD=(now, now)).follow = eymd
        Task("t2").triggers = eevent
        Task("t3").triggers = emeter == 10

    # Check that the externs have real types --> will have correct functionality available

    assert isinstance(eymd, RepeatDate)
    assert eymd.name == "YMD"
    assert eymd.fullname == "/a/b/c/d:YMD"

    assert isinstance(eevent, Event)
    assert eevent.name == "ev"
    assert eevent.fullname == "/e/f/g/h:ev"

    assert isinstance(emeter, Meter)
    assert emeter.name == "mt"
    assert emeter.fullname == "/g/h/i/j:mt"

    # Check that they work!

    s.check_definition()
    s.generate_node()
    s.deploy_suite(target=Notebook)

    # Check that externs are correctly added to the nodes

    defs = str(s.ecflow_definition())

    assert "extern /a/b/c/d:YMD\n" in defs
    assert "extern /e/f/g/h:ev\n" in defs
    assert "extern /g/h/i/j:mt\n" in defs
    assert defs.index("extern /a/b/c/d:YMD") < defs.index("suite s")
    assert defs.index("extern /e/f/g/h:ev") < defs.index("suite s")
    assert defs.index("extern /g/h/i/j:mt") < defs.index("suite s")


def test_extern_safety():
    externs = []

    with Suite("s"):
        externs.append(ExternTask("/a/b/c/d"))
        externs.append(ExternFamily("/e/f/g/h"))

        with externs[-1]:
            # n.b. should never do this in reality, but trying to break things...
            externs.append(Task("e3"))

        externs.append(ExternYMD("i/j/k/l:YMD"))
        externs.append(ExternEvent("m/n/o/p:ev"))
        externs.append(ExternMeter("q/s/t/u:mt"))

    for extern in externs:
        with pytest.raises(AssertionError) as excinfo:
            extern.suite.ecflow_definition()
        assert excinfo.value.args == ("Generating extern nodes is not permitted",)
        with pytest.raises(AssertionError) as excinfo:
            extern.suite.check_definition()
        assert excinfo.value.args == ("Generating extern nodes is not permitted",)
        with pytest.raises(AssertionError) as excinfo:
            extern.suite.deploy_suite(target=Notebook)
        assert excinfo.value.args == ("Attempting to deploy extern node not permitted",)
        with pytest.raises(AssertionError) as excinfo:
            extern.suite.replace_on_server("localhost", 31415)
        assert excinfo.value.args == (
            "Attempting to play extern nodes to the server is not permitted",
        )


if __name__ == "__main__":
    pytest.main(os.path.abspath(__file__))
