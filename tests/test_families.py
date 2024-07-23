from pyflow import AnchorFamily, Family, Limit, Suite, Task, Variable


def test_families():
    s = Suite("s")

    s.families += ["p", "q", "r", "s"]

    names = ["a", "b", "c"]
    s.families = names

    assert [n.name for n in s.families] == names


def test_children():
    """
    Obtain the direct children of a given node (family)
    """
    with Suite("S"):
        with Family("f") as f:
            Limit("limit1", 15)
            Variable("VARIABLE1", 1234)
            with Family("f2"):
                Limit("limit2", 15)
                Task("t1")
                Variable("VARIABLE2", 1234)
                with Family("f3"):
                    Task("t2")
                    Task("t3")
                    Variable("VARIABLE3", 1234)

            Task("t4")
            Task("t5")

    children = f.children
    names = set([c.name for c in children])

    assert names == {
        "limit1",
        "VARIABLE1",
        "f2",
        "t4",
        "t5",
        "FAMILY",
        "FAMILY1",
    }


def test_executable_children():
    """
    Obtain the direct EXECUTABLE children of a given node (family)
    i.e. tasks and families
    """

    with Suite("S"):
        with Family("f") as f:
            Limit("limit1", 15)
            Variable("VARIABLE1", 1234)
            with Family("f2"):
                Limit("limit2", 15)
                Task("t1")
                Variable("VARIABLE2", 1234)
                with Family("f3"):
                    Task("t2")
                    Task("t3")
                    Variable("VARIABLE3", 1234)

            Task("t4")
            Task("t5")

    children = f.executable_children
    names = set([c.name for c in children])

    assert names == {"f2", "t4", "t5"}


def test_files_locations():
    with Suite("S", files="/a/base/path"):
        t1 = Task("t1")
        with Family("f1"):
            t2 = Task("t2")
            with Family("f2"):
                t3 = Task("t3")
        with AnchorFamily("f3"):
            t4 = Task("t4")
            with Family("f4"):
                t5 = Task("t5")
        with Family("f5"):
            t6 = Task("t6")
            with AnchorFamily("f6"):
                t7 = Task("t7")

    assert t1.deploy_path == "/a/base/path/t1.ecf"
    assert t2.deploy_path == "/a/base/path/t2.ecf"
    assert t3.deploy_path == "/a/base/path/t3.ecf"
    assert t4.deploy_path == "/a/base/path/f3/t4.ecf"
    assert t5.deploy_path == "/a/base/path/f3/t5.ecf"
    assert t6.deploy_path == "/a/base/path/t6.ecf"
    assert t7.deploy_path == "/a/base/path/f5/f6/t7.ecf"


def test_exit_hook():
    """
    Propagate exit hook to children of a given family
    """

    with Family("f3", exit_hook="hook_f3") as f3:
        t3 = Task("t3", exit_hook="hook_t3")
        t4 = Task("t4")

    t5 = Task("t5")

    with Suite("S"):
        with Family("f", exit_hook="hook_f", tasks=t5) as f:
            Limit("limit1", 15)
            Variable("VARIABLE1", 1234)
            t1 = Task("t1", exit_hook="hook_t1")
            with Family("f2", families=f3, exit_hook="hook_f2") as f2:
                t2 = Task("t2", exit_hook="hook_t2")

    assert f._exit_hook == ["hook_f"]
    assert t1._exit_hook == ["hook_f", "hook_t1"]
    assert f2._exit_hook == ["hook_f", "hook_f2"]
    assert t2._exit_hook == ["hook_f", "hook_f2", "hook_t2"]
    assert f3._exit_hook == ["hook_f3", "hook_f", "hook_f2"]
    assert t3._exit_hook == ["hook_f3", "hook_t3", "hook_f", "hook_f2"]
    assert t4._exit_hook == ["hook_f3", "hook_f", "hook_f2"]
    assert t5._exit_hook == ["hook_f"]


if __name__ == "__main__":
    from os import path

    import pytest

    pytest.main(path.abspath(__file__))
