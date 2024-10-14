import os
from os import path

import pytest

import pyflow


@pytest.mark.parametrize("ECF_FILES", ["", "files"])
def test_deploy_filesystem(tmpdir, ECF_FILES):
    files = path.join(str(tmpdir), ECF_FILES)
    with pyflow.Suite("s", ECF_HOME=str(tmpdir), ECF_FILES=files) as s:
        with pyflow.Family("f1"):
            with pyflow.Task("t") as t1:
                t1.script = "echo foo"
        with pyflow.Family("f2"):
            with pyflow.Task("t2") as t2:
                t2.script = "echo bar"

    s.deploy_suite()
    s.deploy_suite(target=pyflow.Notebook)
    f1 = path.join(files, "t.ecf")
    assert path.exists(f1)
    with open(f1) as f:
        assert "echo foo" in f.read()
    f2 = path.join(files, "t2.ecf")
    assert path.exists(f2)
    with open(f2) as f:
        assert "echo bar" in f.read()

    # partial deployment
    t1.script = "echo new"
    t2.script = "echo new"
    s.deploy_suite(node="f2")
    with open(f1) as f:
        # shouldn't not be updated
        assert "echo foo" in f.read()
    with open(f2) as f:
        assert "echo new" in f.read()


def test_move_node(tmpdir):
    d = str(tmpdir)
    t = pyflow.Task("t")

    with pyflow.Suite("s", ECF_FILES=d) as s:
        with pyflow.Family("f1") as f:
            f += t
    s.deploy_suite()
    assert path.exists(path.join(d, "t.ecf"))

    with s:
        with pyflow.Family("f2") as f:
            f += t
    s.deploy_suite()
    assert path.exists(path.join(d, "t.ecf"))


def test_manual_task(tmpdir):
    class Documented(pyflow.Task):
        """This is a task with a manual"""

    d = str(tmpdir)
    with pyflow.Suite("s", ECF_FILES=d) as s:
        Documented("t", script="echo foo")
    s.deploy_suite()
    p = path.join(d, "t.ecf")
    assert path.exists(p)
    with open(p) as f:
        lines = f.read()
        assert "%manual" in lines
        assert "This is a task with a manual" in lines
        assert "%end" in lines
        assert "echo foo" in lines


def test_manual_family(tmpdir):
    class Documented(pyflow.Family):
        """This is a family with a manual"""

    d = str(tmpdir)
    with pyflow.Suite("s", ECF_FILES=d) as s:
        Documented("f")
    s.deploy_suite()
    p = path.join(d, "f.man")
    assert path.exists(p)
    with open(p) as f:
        lines = f.read()
        assert "%manual" in lines
        assert "This is a family with a manual" in lines
        assert "%end" in lines


def test_unique_scripts(tmpdir):
    basedir = str(tmpdir)

    # Identical scripts with the same name are allowed

    with pyflow.Suite("s1", ECF_FILES=basedir) as s:
        with pyflow.Family("f1"):
            t1 = pyflow.Task("t", script="abcd")
        with pyflow.Family("f2"):
            t2 = pyflow.Task("t", script="abcd")

    assert t1.deploy_path == os.path.join(basedir, "t.ecf")
    assert t2.deploy_path == os.path.join(basedir, "t.ecf")
    s.deploy_suite()
    with open(t1.deploy_path, "r") as f:
        assert "abcd" in f.read()

    # Differing scripts causes chaos

    with pyflow.Suite("s1", ECF_FILES=basedir) as s:
        with pyflow.Family("f1"):
            t1 = pyflow.Task("t", script="defg")
        with pyflow.Family("f2"):
            t2 = pyflow.Task("t", script="hijk")

    assert t1.deploy_path == os.path.join(basedir, "t.ecf")
    assert t2.deploy_path == os.path.join(basedir, "t.ecf")
    with pytest.raises(RuntimeError):
        s.deploy_suite()

    # This works again when we put Anchor families in

    with pyflow.Suite("s1", ECF_FILES=basedir) as s:
        with pyflow.AnchorFamily("f1"):
            t1 = pyflow.Task("t", script="lmno")
        with pyflow.AnchorFamily("f2"):
            t2 = pyflow.Task("t", script="pqrs")

    assert t1.deploy_path == os.path.join(basedir, "f1/t.ecf")
    assert t2.deploy_path == os.path.join(basedir, "f2/t.ecf")
    s.deploy_suite()
    with open(t1.deploy_path, "r") as f:
        assert "lmno" in f.read()
    with open(t2.deploy_path, "r") as f:
        assert "pqrs" in f.read()

    # Anchor families have similar restrictions on similarly named scripts

    with pyflow.Suite("s1", ECF_FILES=basedir) as s:
        with pyflow.AnchorFamily("f1"):
            t1 = pyflow.Task("t", script="tuvw")
        with pyflow.AnchorFamily("f2"):
            t2 = pyflow.Task("t", script="xyza")
            with pyflow.Family("f3"):
                t3 = pyflow.Task("t", script="abbc")

    assert t1.deploy_path == os.path.join(basedir, "f1/t.ecf")
    assert t2.deploy_path == os.path.join(basedir, "f2/t.ecf")
    assert t3.deploy_path == os.path.join(basedir, "f2/t.ecf")
    with pytest.raises(RuntimeError):
        s.deploy_suite()


if __name__ == "__main__":
    pytest.main(path.abspath(__file__))
