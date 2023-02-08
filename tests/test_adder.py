from pyflow import Family, Suite, Task


def test_tasks():
    s = Suite("s")
    s.tasks += "t1"
    assert isinstance(s.t1, Task)
    s.tasks += ["t2", "t3"]
    assert isinstance(s.t2, Task) and isinstance(s.t3, Task)
    s.tasks += ["t4"]
    assert isinstance(s.t4, Task)
    s.tasks += ("t5", {"VAR": "val"})
    assert isinstance(s.t5, Task) and s.t5.VAR.value == "val"
    s.tasks += Task("t6")
    assert isinstance(s.t6, Task)
    s.tasks += [Task("t7"), Task("t8")]
    assert isinstance(s.t7, Task) and isinstance(s.t8, Task)
    s.tasks += ["t9"]
    assert isinstance(s.t9, Task)
    s.tasks += Task("t10", VAR="val")
    assert isinstance(s.t10, Task) and s.t10.VAR.value == "val"


def test_families():
    s = Suite("s")
    s.families += "f1"
    assert isinstance(s.f1, Family)
    s.families += ["f2", "f3"]
    assert isinstance(s.f2, Family) and isinstance(s.f3, Family)
    s.families += ["f4"]
    assert isinstance(s.f4, Family)
    s.families += ("f5", {"VAR": "val"})
    assert isinstance(s.f5, Family) and s.f5.VAR.value == "val"
    s.families += Family("f6")
    assert isinstance(s.f6, Family)
    s.families += [Family("f7"), Family("f8")]
    assert isinstance(s.f7, Family) and isinstance(s.f8, Family)
    s.families += ["f9"]
    assert isinstance(s.f9, Family)
    s.families += Family("f10", VAR="val")
    assert isinstance(s.f10, Family) and s.f10.VAR.value == "val"


def test_triggers():
    with Suite("s") as s:
        s.tasks += ["t1", "t2", "t3", "t4"]

        s.t1.triggers &= s.t3
        s.t1.triggers &= s.t4.complete

        s.t2.triggers |= s.t3
        s.t2.triggers |= s.t4.complete

    assert "((/s/t3 eq complete) and (/s/t4 eq complete))" == str(s.t1._trigger.value)
    assert "((/s/t3 eq complete) or (/s/t4 eq complete))" == str(s.t2._trigger.value)


if __name__ == "__main__":
    from os import path

    import pytest

    pytest.main(path.abspath(__file__))
