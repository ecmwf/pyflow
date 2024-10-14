import os
import textwrap

import pyflow


def test_script_adder():
    with pyflow.Suite("s"):
        with pyflow.Family("f"):
            t1 = pyflow.Task("t1")
            t2 = pyflow.Task("t2")

    t1.script = "echo 'bit1'"
    t1.script += "echo 'bit2'"
    t1.script += "echo 'bit3'"

    t2.script = "echo 'bit1'"
    t2.script += "echo 'bit2'"
    t2.script = "echo 'bit3'"  # n.b. assignment

    assert "echo 'bit1'\necho 'bit2'\necho 'bit3'" in t1.script.value

    assert "echo 'bit1'" not in t2.script.value
    assert "echo 'bit2'" not in t2.script.value
    assert "echo 'bit3'" in t2.script.value


def test_script_lists():
    with pyflow.Suite("s"):
        with pyflow.Family("f"):
            t1 = pyflow.Task("t1")
            t2 = pyflow.Task(
                "t2",
                script=[
                    "echo 'bit1'",
                    pyflow.Script(["echo 'bit2'", "echo 'bit3'"]),
                ],
            )

    t1.script = ["echo 'bit1'", pyflow.Script(["echo 'bit2'", "echo 'bit3'"])]
    t1.script += "echo 'bit4'"
    t1.script += ["echo 'bit5'", "echo 'bit6'"]

    t2.script += "echo 'bit4'"
    t2.script += ["echo 'bit5'", "echo 'bit6'"]

    checkscript = os.linesep.join(
        line
        for line in textwrap.dedent(
            """
        echo 'bit1'
        echo 'bit2'
        echo 'bit3'
        echo 'bit4'
        echo 'bit5'
        echo 'bit6'
    """
        ).splitlines()
        if line
    )

    assert t1.script.value == checkscript
    assert t2.script.value == checkscript


def test_script_objects():
    with pyflow.Suite("s"):
        with pyflow.Family("f"):
            s1 = pyflow.Script("echo 'bit1'")
            s2 = pyflow.Script("echo 'bit2'")
            s3 = pyflow.Script("echo 'bit3'")

            # Ensure we test __iadd__ and __add__
            s1 += s2
            total_script = s1 + s3

            t = pyflow.Task("t")
            t.script = total_script

    assert "echo 'bit1'\necho 'bit2'\necho 'bit3'" in t.script.value


def test_lazy_generation():
    """
    n.b. change in val in object --> the output script is lazily generated.
    """

    obj = {"val": 7}

    class DerivedScript(pyflow.Script):
        def __init__(self):
            super().__init__()

        def generate(self):
            return ["derived", "{}".format(obj)]

    with pyflow.Suite("s"):
        with pyflow.Family("f"):
            # A derived script in the middle

            t = pyflow.Task("t")
            t.script = pyflow.Script("---LINE1---")

            s = pyflow.Script("---LINE2---") + DerivedScript()
            s += pyflow.Script("---LINE3---")

            t.script += s

            # A derived script first in a chain

            s = DerivedScript()
            s += pyflow.Script("---LINE2---")

            t2 = pyflow.Task("t2", script=s)

            # And using the binary addition operator

            s = DerivedScript() + pyflow.Script("---LINE2---")

            t3 = pyflow.Task("t3", script=s)

    obj["val"] = 99

    assert (
        t.script.value == "---LINE1---\n---LINE2---\nderived\n{'val': 99}\n---LINE3---"
    )
    assert t2.script.value == "derived\n{'val': 99}\n---LINE2---"
    assert t3.script.value == "derived\n{'val': 99}\n---LINE2---"


def test_filescript():
    with pyflow.Suite("s"):
        with pyflow.Family("f"):
            scriptfile = os.path.join(
                os.path.dirname(__file__),
                "fixtures",
                "fixture_for_test_script_filescript.sh",
            )
            s1 = pyflow.FileScript(scriptfile)

            t = pyflow.Task("t", script=s1)

    checkscript = "echo 'I am a script in a file'"

    assert checkscript == t.script.value


def test_python_script():
    with pyflow.Suite("s"):
        with pyflow.Family("f"):
            s1 = pyflow.Script("echo 'bit1'")
            s2 = pyflow.PythonScript('print "I am in Python (default)"')
            s3 = pyflow.PythonScript('print "I am a Python 2.7 script"', python=2.7)
            s4 = pyflow.PythonScript('print("I am a python 3 script")', python=3)
            s5 = pyflow.Script("echo 'bit3'")

            t = pyflow.Task("t", script=[s1, s2, s3, s4, s5])

    checkscript = os.linesep.join(
        line
        for line in textwrap.dedent(
            """
        echo 'bit1'
        python3 -u - <<EOS
        print "I am in Python (default)"
        EOS
        python2.7 -u - <<EOS
        print "I am a Python 2.7 script"
        EOS
        python3 -u - <<EOS
        print("I am a python 3 script")
        EOS
        echo 'bit3'
    """
        ).splitlines()
        if line
    )

    assert checkscript == t.script.value


def test_script_exportables():
    with pyflow.Suite("s"):
        v1 = pyflow.Variable("VARIABLE1", "1234")
        with pyflow.Family("f", VARIABLE2=4321) as f:
            subscript = pyflow.Script("uninteresting2")
            with pyflow.Task(
                "t",
                script=['echo "uninteresting script', subscript],
                VARIABLE3=9999,
            ) as t:
                v4 = pyflow.Variable("VARIABLE4", 8888)

            subscript.add_required_exportables(v1, f.VARIABLE2)
            t.script.force_exported(t.VARIABLE3)
            t.script.force_exported(v4)

    vs = subscript.required_exportables()
    assert len(vs) == 2
    vs_names = set(v.name for v in vs)
    assert "VARIABLE1" in vs_names
    assert "VARIABLE2" in vs_names

    vs = t.script.required_exportables()
    assert len(vs) == 4
    vs_names = set(v.name for v in vs)
    assert "VARIABLE1" in vs_names
    assert "VARIABLE2" in vs_names
    assert "VARIABLE3" in vs_names
    assert "VARIABLE4" in vs_names


def test_template_script():
    # n.b. we can nest these...

    with pyflow.Suite("s", VARIABLE1=1234) as s:
        with pyflow.Family("f"):
            lab = pyflow.Label("A_LABEL", "lll")
            var = pyflow.Variable("VARIABLE2", "v2")

            task = pyflow.Task("t")

    task.script = pyflow.TemplateScript(
        pyflow.PythonScript(
            textwrap.dedent(
                """
                import ecflow
                print("Static text {{ TEXT_STRING }}")
                print("Contents of variable ({{ TEMPLATE_VARIABLE.fullname }}): {{ TEMPLATE_VARIABLE }}")
                print("Contents of another ({{ ANOTHER_VARIABLE.fullname }}): {{ ANOTHER_VARIABLE }}")
                ci = ecflow.Client()
                ci.alter("{{ LABEL.parent.fullname }}", "change", "label", "{{ LABEL.name }}", "value")
            """
            ),
            python=3,
        ),
        TEXT_STRING="some text",
        TEMPLATE_VARIABLE=var,
        ANOTHER_VARIABLE=s.VARIABLE1,
        LABEL=lab,
    )

    checkscript = textwrap.dedent(
        """
        python3 -u - <<EOS
        import ecflow
        print("Static text some text")
        print("Contents of variable (/s/f:VARIABLE2): $VARIABLE2")
        print("Contents of another (/s:VARIABLE1): $VARIABLE1")
        ci = ecflow.Client()
        ci.alter("/s/f", "change", "label", "A_LABEL", "value")
        EOS
    """
    )[1:-1]

    assert task.script.value == checkscript


def test_variable_detection_script():
    s_vars = {"S_FOO": "hello", "S_BAR": 1, "S_FOO_S_BAR": "3"}
    with pyflow.Suite("s", variables=s_vars):
        t_vars = {"T_FOO": "salut", "T_BAR": 2, "T_FOO_T_BAR": "4"}
        t_script = pyflow.Script(
            """
                echo S_BAR is $S_BAR
                echo S_FOO_S_BAR is ${S_FOO_S_BAR}
                echo T_FOO is ${T_FOO:-2}
                echo T_BAR is ${T_BAR=10}
            """
        )
        t = pyflow.Task("t", variables=t_vars, script=t_script)

    full_script = t.generate_script()
    for line in full_script[0]:
        print(line)

    in_script = [
        'export S_BAR="%S_BAR%"',
        'export S_FOO_S_BAR="%S_FOO_S_BAR%"',
        'export T_FOO="%T_FOO%"',
        'export T_BAR="%T_BAR%"',
    ]
    for var in in_script:
        check = False
        for line in full_script[0]:
            if var in line:
                check = True
        assert check

    not_in_script = [
        'export S_FOO="%S_FOO%"',
        'export T_FOO_T_BAR="%T_FOO_T_BAR%"',
    ]
    for var in not_in_script:
        check = False
        for line in full_script[0]:
            if var in line:
                check = True
        assert not check


# def test_script_headers():
#     assert False


# def test_pre_post_amble():
#     assert False


if __name__ == "__main__":
    from os import path

    import pytest

    pytest.main(path.abspath(__file__))
