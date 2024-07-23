import textwrap

import pytest

import pyflow


def test_generate_variables():
    with pyflow.Suite("s", VARIABLE1="variable1"):
        with pyflow.Family("f", VARIABLE2="variable2"):
            t = pyflow.Task(
                "t1",
                VARIABLE3="variable3",
                script=textwrap.dedent(
                    """
                echo "$VARIABLE1"
                echo "$VARIABLE2"
                echo "$VARIABLE3"
                echo "$VARIABLE4
            """
                ),
            )

    script, includes = t.generate_script()
    script = "\n".join(script)

    assert len(includes) == 0

    assert 'export VARIABLE1="%VARIABLE1%' in script
    assert 'export VARIABLE2="%VARIABLE2%' in script
    assert 'export VARIABLE3="%VARIABLE3%' in script
    assert 'export VARIABLE4="%VARIABLE4%' not in script


def test_workdir():
    with pyflow.Suite("s", VARIABLE="/another/directory") as s:
        t1 = pyflow.Task("t1", script="test script")
        t2 = pyflow.Task("t2", workdir="/var/tmp/testing", script="test script")
        t3 = pyflow.Task(
            "t3", workdir=s.VARIABLE, clean_workdir=True, script="test script"
        )

    s1 = "\n".join(t1.generate_script()[0])
    s2 = "\n".join(t2.generate_script()[0])
    s3 = "\n".join(t3.generate_script()[0])

    assert "mkdir" not in s1
    assert '[[ -d "/var/tmp/testing" ]] && rm -rf "/var/tmp/testing"' not in s2
    assert (
        '[[ -d "/var/tmp/testing" ]] || mkdir -p "/var/tmp/testing"\ncd "/var/tmp/testing"'
        in s2
    )
    assert '[[ -d "$VARIABLE" ]] && rm -rf "$VARIABLE"' in s3
    assert '[[ -d "$VARIABLE" ]] || mkdir -p "$VARIABLE"\ncd "$VARIABLE"' in s3


def test_includes():
    class MySuite(pyflow.Suite):
        def __init__(self, name, *args, **kwargs):
            super().__init__(name, files="", include="")

        head = 'echo "A header"'
        tail = 'echa "a tail"'

    class Family2(pyflow.Family):
        head = 'echo "FAMILY2-HEAD"'
        tail = 'echo "FAMILY2-TAIL"'

    class Family3(pyflow.Family):
        head = 'echo "FAMILY3-HEAD"\necho "SECOND LINE"'
        tail = 'echo "FAMILY3-TAIL"'

    with MySuite("s"):
        t1 = pyflow.Task("t1", script="echo t1")

        with pyflow.Family("f1"):
            t2 = pyflow.Task("t2", script="echo t2")

        with Family2("f2"):
            t3 = pyflow.Task("t3", script="echo t3")

            with Family3("f3"):
                t4 = pyflow.Task("t4", script="echo t4")

    # Which headers are in task 1

    heads, tails = t1.headers

    assert len(heads) == 1
    assert len(tails) == 1

    assert heads[0]._name == "mysuite"
    assert tails[0]._name == "mysuite"

    assert [i._name for i in t1.generate_script()[1]] == ["mysuite", "mysuite"]
    assert [i._what for i in t1.generate_script()[1]] == ["head", "tail"]

    script = "\n".join(t1.generate_script()[0])
    assert "echo t1" in script
    assert "%include <mysuite_head.h>" in script and script.index(
        "%include <mysuite_head.h>"
    ) < script.index("echo t1")
    assert "%include <mysuite_tail.h>" in script and script.index(
        "%include <mysuite_tail.h>"
    ) > script.index("echo t1")

    # Which headers are in task 2

    heads, tails = t2.headers

    assert len(heads) == 1
    assert len(tails) == 1

    assert heads[0]._name == "mysuite"
    assert tails[0]._name == "mysuite"

    assert [i._name for i in t2.generate_script()[1]] == ["mysuite", "mysuite"]
    assert [i._what for i in t2.generate_script()[1]] == ["head", "tail"]

    script = "\n".join(t2.generate_script()[0])
    assert "echo t2" in script
    assert "%include <mysuite_head.h>" in script and script.index(
        "%include <mysuite_head.h>"
    ) < script.index("echo t2")
    assert "%include <mysuite_tail.h>" in script and script.index(
        "%include <mysuite_tail.h>"
    ) > script.index("echo t2")

    # Which headers are in task 3

    heads, tails = t3.headers

    assert len(heads) == 2
    assert len(tails) == 2

    assert [h._name for h in heads] == ["mysuite", "family2"]
    assert [t._name for t in tails] == ["family2", "mysuite"]

    assert [i._name for i in t3.generate_script()[1]] == [
        "mysuite",
        "family2",
        "family2",
        "mysuite",
    ]
    assert [i._what for i in t3.generate_script()[1]] == [
        "head",
        "head",
        "tail",
        "tail",
    ]

    script = "\n".join(t3.generate_script()[0])
    assert "echo t3" in script
    assert "%include <mysuite_head.h>" in script
    assert "%include <family2_head.h>" in script
    assert "%include <family2_tail.h>" in script
    assert "%include <mysuite_tail.h>" in script
    assert script.index("%include <mysuite_head.h>") < script.index(
        "%include <family2_head.h>"
    )
    assert script.index("%include <family2_head.h>") < script.index("echo t3")
    assert script.index("echo t3") < script.index("%include <family2_tail.h>")
    assert script.index("%include <family2_tail.h>") < script.index(
        "%include <mysuite_tail.h>"
    )

    # Which headers are in task 4

    heads, tails = t4.headers

    assert len(heads) == 3
    assert len(tails) == 3

    assert [h._name for h in heads] == ["mysuite", "family2", "family3"]
    assert [t._name for t in tails] == ["family3", "family2", "mysuite"]

    assert [i._name for i in t4.generate_script()[1]] == [
        "mysuite",
        "family2",
        "family3",
        "family3",
        "family2",
        "mysuite",
    ]
    assert [i._what for i in t4.generate_script()[1]] == [
        "head",
        "head",
        "head",
        "tail",
        "tail",
        "tail",
    ]

    script = "\n".join(t4.generate_script()[0])
    assert "echo t4" in script
    assert "%include <mysuite_head.h>" in script
    assert "%include <family2_head.h>" in script
    assert "%include <family3_head.h>" in script
    assert "%include <family3_tail.h>" in script
    assert "%include <family2_tail.h>" in script
    assert "%include <mysuite_tail.h>" in script
    assert script.index("%include <mysuite_head.h>") < script.index(
        "%include <family2_head.h>"
    )
    assert script.index("%include <family2_head.h>") < script.index(
        "%include <family3_head.h>"
    )
    assert script.index("%include <family3_head.h>") < script.index("echo t4")
    assert script.index("echo t4") < script.index("%include <family3_tail.h>")
    assert script.index("%include <family3_tail.h>") < script.index(
        "%include <family2_tail.h>"
    )
    assert script.index("%include <family2_tail.h>") < script.index(
        "%include <mysuite_tail.h>"
    )


def test_manual():
    class Documented(pyflow.Task):
        """This is a task with a manual"""

    with pyflow.Suite("s"):
        t1 = Documented("t1")
        t2 = Documented("t2", manual="\nManuals are additive")

    s1, includes = t1.generate_script()
    assert s1[0:3] == ["%manual", "This is a task with a manual", "%end"]

    s2, includes = t2.generate_script()
    assert s2[0:4] == [
        "%manual",
        "This is a task with a manual",
        "Manuals are additive",
        "%end",
    ]


def test_shebang():
    """
    The shebang must be first in the generated file (or immediately after the manual with no extra lines)
    """
    with pyflow.Suite("s"):
        t1 = pyflow.Task("t1", 'echo "Hi there"')
        t2 = pyflow.Task("t2", 'echo "Hi there"', manual="Some documentation")

    s1, includes = t1.generate_script()
    assert s1[0] == "#!/bin/bash"

    s2, includes = t2.generate_script()
    assert s2[0:4] == ["%manual", "Some documentation", "%end", "#!/bin/bash"]


def test_disable_ecflow_keywords():
    """
    After declaring the ecflow variables, we disable ecflow keywords for the duration
    of the script proper.
    """
    with pyflow.Suite("s"):
        t = pyflow.Task("t", script="Multiline\nscript")

    script, includes = t.generate_script()

    idx = script.index("%nopp")
    assert script[idx : idx + 6] == [
        "%nopp",
        "",
        "Multiline",
        "script",
        "",
        "%end",
    ]


def test_modules():
    h1 = pyflow.LocalHost()
    h2 = pyflow.LocalHost(modules=["mod1/123", "-mod2/321", "mod3/33"])
    h3 = pyflow.LocalHost(
        purge_modules=True, modules=["mod1/123", "-mod2/321", "mod3/33"]
    )

    with pyflow.Suite("s") as s:
        t1 = pyflow.Task("t1", host=h1, script="echo t1")
        t2 = pyflow.Task("t2", host=h2, script="echo t2")
        t3 = pyflow.Task("t3", host=h3, script="echo t3")

        with pyflow.Family("f", purge_modules=True, modules=["aaa/2"]) as f:
            t4 = pyflow.Task("t4", host=h1, script="echo t4")
            t5 = pyflow.Task("t5", host=h2, script="echo t5")
            t6 = pyflow.Task("t6", host=h3, script="echo t6")
            t7 = pyflow.Task("t7", host=h3, script="echo t6", modules=["newmod/44"])

    assert s.modules == []
    assert f.modules == ["aaa/2"]
    f.modules.append("-bbb/3")
    assert f.modules == ["aaa/2", "-bbb/3"]
    assert t7.modules == ["newmod/44"]

    script = "\n".join(t1.generate_script()[0])
    assert "module" not in script

    script = "\n".join(t2.generate_script()[0])
    assert "module purge" not in script
    assert "module load mod1/123" in script
    assert "module rm mod2" in script
    assert "module load mod3/33" in script
    assert "aaa" not in script
    assert "bbb" not in script
    assert script.index("rm mod1") < script.index("load mod1")
    assert script.index("load mod1") < script.index("rm mod2")
    assert script.index("rm mod2") < script.index("load mod3")

    script = "\n".join(t3.generate_script()[0])
    assert "module purge" in script
    assert "module load mod1/123" in script
    assert "module rm mod2" in script
    assert "module load mod3/33" in script
    assert "aaa" not in script
    assert "bbb" not in script
    assert script.index("module purge") < script.index("rm mod1")
    assert script.index("rm mod1") < script.index("load mod1")
    assert script.index("load mod1") < script.index("rm mod2")
    assert script.index("rm mod2") < script.index("load mod3")

    script = "\n".join(t4.generate_script()[0])
    assert "module purge" in script
    assert "module load aaa/2" in script
    assert "module rm bbb" in script
    assert script.index("module purge") < script.index("rm aaa")
    assert script.index("rm aaa") < script.index("load aaa")
    assert script.index("load aaa") < script.index("rm bbb")

    script = "\n".join(t5.generate_script()[0])
    assert "module purge" in script
    assert "module load aaa/2" in script
    assert "module rm bbb" in script
    assert "module load mod1/123" in script
    assert "module rm mod2" in script
    assert "module load mod3/33" in script
    assert script.index("module purge") < script.index("rm mod1")
    assert script.index("rm mod1") < script.index("load mod1")
    assert script.index("load mod1") < script.index("rm mod2")
    assert script.index("rm mod2") < script.index("load mod3")
    assert script.index("load mod3") < script.index("rm aaa")
    assert script.index("rm aaa") < script.index("load aaa")
    assert script.index("load aaa") < script.index("rm bbb")

    script = "\n".join(t6.generate_script()[0])
    assert "module purge" in script
    assert "module load aaa/2" in script
    assert "module rm bbb" in script
    assert "module load mod1/123" in script
    assert "module rm mod2" in script
    assert "module load mod3/33" in script
    assert script.index("module purge") < script.index("rm mod1")
    assert script.index("rm mod1") < script.index("load mod1")
    assert script.index("load mod1") < script.index("rm mod2")
    assert script.index("rm mod2") < script.index("load mod3")
    assert script.index("load mod3") < script.index("rm aaa")
    assert script.index("rm aaa") < script.index("load aaa")
    assert script.index("load aaa") < script.index("rm bbb")

    script = "\n".join(t7.generate_script()[0])
    assert "module purge" in script
    assert "module load aaa/2" in script
    assert "module rm bbb" in script
    assert "module load mod1/123" in script
    assert "module rm mod2" in script
    assert "module load mod3/33" in script
    assert "module load newmod/44" in script
    assert script.index("module purge") < script.index("rm mod1")
    assert script.index("rm mod1") < script.index("load mod1")
    assert script.index("load mod1") < script.index("rm mod2")
    assert script.index("rm mod2") < script.index("load mod3")
    assert script.index("load mod3") < script.index("rm aaa")
    assert script.index("rm aaa") < script.index("load aaa")
    assert script.index("load aaa") < script.index("rm bbb")
    assert script.index("rm bbb") < script.index("load newmod")
    assert script.index("rm newmod") < script.index("load newmod")

    # And test modifying the modules

    t6.modules = ["newmod/44"]

    script = "\n".join(t6.generate_script()[0])
    assert "module purge" in script
    assert "module load aaa/2" in script
    assert "module rm bbb" in script
    assert "module load mod1/123" in script
    assert "module rm mod2" in script
    assert "module load mod3/33" in script
    assert "module load newmod/44" in script
    assert script.index("module purge") < script.index("rm mod1")
    assert script.index("rm mod1") < script.index("load mod1")
    assert script.index("load mod1") < script.index("rm mod2")
    assert script.index("rm mod2") < script.index("load mod3")
    assert script.index("load mod3") < script.index("rm aaa")
    assert script.index("rm aaa") < script.index("load aaa")
    assert script.index("load aaa") < script.index("rm bbb")
    assert script.index("rm bbb") < script.index("load newmod")
    assert script.index("rm newmod") < script.index("load newmod")


if __name__ == "__main__":
    from os import path

    pytest.main(path.abspath(__file__))
