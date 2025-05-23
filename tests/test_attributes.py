import json
import os
from datetime import date, datetime, timedelta

import pytest

import pyflow
from pyflow.base import GenerateError


def test_defstatus():
    with pyflow.Suite("s") as s:
        with pyflow.Family("f"):
            for i, state in enumerate(pyflow.state.MAP.values()):
                t = pyflow.Task("t{}".format(i))
                t.defstatus = state
            t = pyflow.Task("exception")
            with pytest.raises(ValueError):
                t.defstatus = "aborted"
    s.check_definition()


def test_variable_constructor():
    v = pyflow.Variable("VAR", "val")
    assert v.name == "VAR"
    assert v.value == "val"


def test_variable_constructor_fail():
    with pytest.raises(ValueError):
        pyflow.Variable("illegal", "val")


def test_edit():
    with pyflow.Suite("s") as s:
        pyflow.Edit(FOO="foo", BAR="bar", BAZ="baz")
    assert s.FOO.value == "foo"
    assert s.BAR.value == "bar"
    assert s.BAZ.value == "baz"


def test_reassign_variable():
    """
    Reassigning variables should yield same value, see ECFLOW-1006
    """
    with pyflow.Suite("s") as s:
        with pyflow.Task("t1") as t:
            t.FOO = 61
            t.FOO = (1, 10)
        with pyflow.Task("t2") as t:
            t.FOO = (1, 10)
    assert s.t1.FOO.value == s.t2.FOO.value


def test_add_attributes():
    """
    Reassigning variables should yield same value, see ECFLOW-1006
    """
    with pyflow.Suite("s"):
        with pyflow.Task("t") as t:
            t.script = 'echo "Hello"'
            t.script += 'echo "World"'
            script = t.script.value
            assert 'echo "Hello"' in script
            assert 'echo "World"' in script


def test_add_node_attributes():
    """
    If attributes are constructed from _named_ nodes (rather than freestanding
    containing non-pyflow values) then adding an attribute to a NodeAdder
    creates a new attribute with a different name (from the node), rather than
    combining the values in the nodes.
    """
    with pyflow.Suite("s"):
        l1 = pyflow.Limit("l1", 3)
        l2 = pyflow.Limit("l2", 4)

        with pyflow.Task("t") as t:
            t.inlimits += l1
            t.inlimits += l2

        assert isinstance(t["_Limit(/s:l1)"], pyflow.InLimit)
        assert isinstance(t["_Limit(/s:l2)"], pyflow.InLimit)


def test_add_limits():
    """
    ECFLOW-1252: += operator on limits only works once
    """
    with pyflow.Suite("s"):
        f = pyflow.Family("f")

        f.limits += ("name1", 3)
        f.limits += ("name2", 2)

    assert isinstance(f.name1, pyflow.Limit)
    assert isinstance(f.name2, pyflow.Limit)


def test_variable_script_expansions():
    with pyflow.Suite("s", SUITE_VAR="s") as s:
        pyflow.Variable("V", 1234)
        with pyflow.Family("f", FAMILY_VAR="f"):
            t = pyflow.Task("t", TASK_VAR="t")
            t.IAM_AVAR = 4321

    assert str(s.SUITE_VAR) == "$SUITE_VAR"
    assert str(s.V) == "$V"
    assert str(s.f.FAMILY_VAR) == "$FAMILY_VAR"
    assert str(s.f.t.TASK_VAR) == "$TASK_VAR"
    assert str(s.f.t.IAM_AVAR) == "$IAM_AVAR"

    assert repr(s.SUITE_VAR) == "%SUITE_VAR%"
    assert repr(s.V) == "%V%"
    assert repr(s.f.FAMILY_VAR) == "%FAMILY_VAR%"
    assert repr(s.f.t.TASK_VAR) == "%TASK_VAR%"
    assert repr(s.f.t.IAM_AVAR) == "%IAM_AVAR%"


def test_all_variables():
    with pyflow.Suite("s", SUITE_VAR="s") as s:
        with pyflow.Family("f", FAMILY_VAR="f", SUITE_VAR="sf") as f:
            t = pyflow.Task("t", TASK_VAR="t", FAMILY_VAR="ft", SUITE_VAR="st")

    assert "SUITE_VAR" in s.all_variables and s.all_variables["SUITE_VAR"].value == "s"
    assert "FAMILY_VAR" not in s.all_variables
    assert "TASK_VAR" not in s.all_variables

    assert "SUITE_VAR" in f.all_variables and f.all_variables["SUITE_VAR"].value == "sf"
    assert (
        "FAMILY_VAR" in f.all_variables and f.all_variables["FAMILY_VAR"].value == "f"
    )
    assert "TASK_VAR" not in f.all_variables

    assert "SUITE_VAR" in t.all_variables and t.all_variables["SUITE_VAR"].value == "st"
    assert (
        "FAMILY_VAR" in t.all_variables and t.all_variables["FAMILY_VAR"].value == "ft"
    )
    assert "TASK_VAR" in t.all_variables and t.all_variables["TASK_VAR"].value == "t"


def test_restricted_variables():
    """
    These restricted variables are only allowed at the suite level, unless
    they are undefined at the suite level in which case they are also allowed
    in first-level families.

    n.b. Test both defining variables at family creation, and inside.
    """

    # Test that the variable is not allowed

    variables = ["ECF_HOME", "ECF_FILES", "ECF_INCLUDE"]
    toplevel_complete = {k: "foo" for k in variables}

    # We are not allowed to redefine the restricted variables at any point if
    # defined at the suite level.

    for var in variables:
        with pyflow.Suite("s", **toplevel_complete):
            with pytest.raises(RuntimeError):
                with pyflow.Family("f1", **{var: "bar"}):
                    pass
            with pyflow.Family("f2") as f2:
                with pytest.raises(RuntimeError):
                    f2[var] = "bar"

            # And with one more level of nesting

            with pyflow.Family("f3"):
                with pytest.raises(RuntimeError):
                    with pyflow.Family("f4", **{var: "bar"}):
                        pass
                with pyflow.Family("f5") as f5:
                    with pytest.raises(RuntimeError):
                        f5[var] = "bar"

        # However, if the variable is _not_ defined at the suite level, then
        # it is allowed in top-level families

        toplevel_reduced = {k: v for k, v in toplevel_complete.items() if k != var}

        with pyflow.Suite("s", **toplevel_reduced):
            with pyflow.Family("f1", **{var: "bar"}):
                pass
            with pyflow.Family("f2") as f2:
                f2[var] = "bar"

            # And with one more level of nesting

            with pyflow.Family("f3"):
                with pytest.raises(RuntimeError):
                    with pyflow.Family("f4", **{var: "bar"}):
                        pass
                with pyflow.Family("f5") as f5:
                    with pytest.raises(RuntimeError):
                        f5[var] = "bar"


def test_manual():
    """A node with docstring cannot also have an explicit manual."""

    class Documented(pyflow.Task):
        """This is a task with a manual"""

    with Documented("t", script="echo foo", manual="Some more documentation") as t:
        manual = t.manual.value
        assert "This is a task with a manual" in manual
        assert "Some more documentation" in manual


def test_validate_trigger():
    """
    Triggers are simplified during generation, but should not be allowed to
    simplify fully to True or False (which is invalid within ecflow).
    """
    with pyflow.Suite("s") as s:
        with pyflow.Family("f"):
            t1 = pyflow.Task("t1")
            t2 = pyflow.Task("t2")

            # This will simplify to True, as 1 is always < 2...
            t2.triggers = t1.complete | (1 < 2)

    with pytest.raises(GenerateError):
        s.check_definition()


def test_relative_path():
    """
    Paths relative to attributes should always include the name of the node
    the attribute is attached to.

    """

    with pyflow.Suite("s"):
        with pyflow.Family("a0", VAR="foo") as a0:
            with pyflow.Family("a1") as a1:
                a2 = pyflow.Family("a2")

    assert a0.VAR.relative_path(a0) == "a0:VAR"
    assert a0.VAR.relative_path(a1) == "../a0:VAR"
    assert a0.VAR.relative_path(a2) == "../../a0:VAR"


def test_relative_path_suite():
    """
    Paths relative to attributes defined at the suite level should resolve
    to the absolute path.

    """
    with pyflow.Suite("s", VAR="foo") as s:
        with pyflow.Family("a0") as a0:
            with pyflow.Family("a1") as a1:
                a2 = pyflow.Family("a2")

    assert s.VAR.relative_path(s) == "/s:VAR"
    assert s.VAR.relative_path(a0) == "/s:VAR"
    assert s.VAR.relative_path(a1) == "/s:VAR"
    assert s.VAR.relative_path(a2) == "/s:VAR"


def test_date():
    """
    n.b. DATE= in the argument --> RepeatString or RepeateEnumerated as appropriated.
    A Date object --> creates a "date" entry in the ecf definitions. Not the same.
    """
    with pyflow.Suite("s") as s:
        with pyflow.Task("t1") as t1:
            pyflow.Date("*.*.3")
            # d = pyflow.Date(datetime(year='*', month='*', day=5))
            # d = pyflow.Date(datetime(year=2018, month=1, day=5), datetime(year=2018, month=2, day=6))

    assert "DATE" not in t1._nodes
    assert "date *.*.3" in str(s.ecflow_definition())

    with pyflow.Suite("s") as s:
        t1 = pyflow.Task("t1", DATE=("20180105", "20180206"))

    assert t1.DATE.value == ("20180105", "20180206")
    assert 'repeat string DATE "20180105" "20180206"' in str(s.ecflow_definition())


class TestRepeats:
    """A set of tests for repeats."""

    def test_string_repeat(self):
        with pyflow.Suite("s") as s:
            with pyflow.Family("f1") as f1:
                f1.STRING_REPEAT = [str(v) for v in reversed(range(10))]

                t1 = pyflow.Task("t1")
                t1.triggers = (f1.STRING_REPEAT == "7") & (f1.STRING_REPEAT == 3)
                t1.triggers |= (f1.STRING_REPEAT + 2 == 7) & (f1.STRING_REPEAT - 1 == 6)

                assert (
                    str(t1.triggers.value) == "(((/s/f1:STRING_REPEAT eq 2)"
                    " and (/s/f1:STRING_REPEAT eq 3))"
                    " or (((/s/f1:STRING_REPEAT + 2) eq 7)"
                    " and ((/s/f1:STRING_REPEAT - 1) eq 6)))"
                )

        s.check_definition()

    def test_combined_string_repeats(self):
        with pyflow.Suite("s") as s:
            t1 = pyflow.Task("t1", YMD=["20170101", "20180101"])
            t2 = pyflow.Task("t2", YMD=["20170101", "20180101"])
        t2.triggers = t1.YMD >= t2.YMD
        assert str(t2.triggers.value) == "(/s/t1:YMD ge /s/t2:YMD)"

        s.check_definition()

    def test_enumerated_repeat(self):
        with pyflow.Suite("s") as s:
            with pyflow.Family("f2") as f2:
                f2.ENUMERATED_REPEAT = list(reversed(range(10)))

                t2 = pyflow.Task("t2")
                t2.triggers = (f2.ENUMERATED_REPEAT == "7") & (
                    f2.ENUMERATED_REPEAT == 3
                )
                t2.triggers |= (f2.ENUMERATED_REPEAT + 2 == 7) & (
                    f2.ENUMERATED_REPEAT - 1 == 6
                )

                assert (
                    str(t2.triggers.value) == "(((/s/f2:ENUMERATED_REPEAT eq 7) and "
                    "(/s/f2:ENUMERATED_REPEAT eq 3)) or "
                    "(((/s/f2:ENUMERATED_REPEAT + 2) eq 7) and "
                    "((/s/f2:ENUMERATED_REPEAT - 1) eq 6)))"
                )

        s.check_definition()

    def test_combined_enumerated_repeats(self):
        with pyflow.Suite("s") as s:
            t1 = pyflow.Task("t1", ENUMERATED_REPEAT=list(range(10)))
            t2 = pyflow.Task("t2", ENUMERATED_REPEAT=list(range(10)))
        t2.triggers = t1.ENUMERATED_REPEAT >= t2.ENUMERATED_REPEAT
        assert (
            str(t2.triggers.value)
            == "(/s/t1:ENUMERATED_REPEAT ge /s/t2:ENUMERATED_REPEAT)"
        )

        s.check_definition()

    def test_integer_repeat(self):
        with pyflow.Suite("s") as s:
            with pyflow.Family("f3") as f3:
                pyflow.RepeatInteger("INTEGER_REPEAT", 0, 9)

                t3 = pyflow.Task("t3")
                t3.triggers = (f3.INTEGER_REPEAT == "7") & (f3.INTEGER_REPEAT == 3)
                t3.triggers |= (f3.INTEGER_REPEAT + 2 == 7) & (
                    f3.INTEGER_REPEAT - 1 == 6
                )

                assert (
                    str(t3.triggers.value) == "(((/s/f3:INTEGER_REPEAT eq 7) and "
                    "(/s/f3:INTEGER_REPEAT eq 3)) or "
                    "(((/s/f3:INTEGER_REPEAT + 2) eq 7) and "
                    "((/s/f3:INTEGER_REPEAT - 1) eq 6)))"
                )

        s.check_definition()

    def test_combined_integer_repeats(self):
        with pyflow.Suite("s") as s:
            with pyflow.Task("t1") as t1:
                pyflow.RepeatInteger("INTEGER_REPEAT", 10, 15)
            with pyflow.Task("t2") as t2:
                pyflow.RepeatInteger("INTEGER_REPEAT", 10, 15)
        t2.triggers = t1.INTEGER_REPEAT < t2.INTEGER_REPEAT
        assert (
            str(t2.triggers.value) == "(/s/t1:INTEGER_REPEAT lt /s/t2:INTEGER_REPEAT)"
        )

        s.check_definition()

    def test_date_datetime_repeat(self):
        with pyflow.Suite("s") as s:
            with pyflow.Family("f4") as f4:
                f4.DATE_REPEAT = (datetime(2018, 1, 1), datetime(2019, 12, 31))

                t4 = pyflow.Task("t4")
                t4.triggers = (f4.DATE_REPEAT >= "20180301") & (
                    f4.DATE_REPEAT < "20180401"
                )
                t4.triggers |= f4.DATE_REPEAT + 2 == "20190101"
                t4.triggers |= f4.DATE_REPEAT - 5 == "20190819"

                assert (
                    str(t4.triggers.value) == "((((/s/f4:DATE_REPEAT ge 20180301) "
                    "and (/s/f4:DATE_REPEAT lt 20180401)) "
                    "or ((/s/f4:DATE_REPEAT + 2) eq 20190101)) "
                    "or ((/s/f4:DATE_REPEAT - 5) eq 20190819))"
                )

        s.check_definition()

    def test_date_date_repeat(self):
        with pyflow.Suite("s") as s:
            with pyflow.Family("f4") as f4:
                f4.DATE_REPEAT = (date(2018, 1, 1), date(2019, 12, 31))

                t4 = pyflow.Task("t4")
                t4.triggers = (f4.DATE_REPEAT >= "20180301") & (
                    f4.DATE_REPEAT < "20180401"
                )
                t4.triggers |= f4.DATE_REPEAT + 2 == "20190101"
                t4.triggers |= f4.DATE_REPEAT - 5 == "20190819"

                assert (
                    str(t4.triggers.value) == "((((/s/f4:DATE_REPEAT ge 20180301) "
                    "and (/s/f4:DATE_REPEAT lt 20180401)) "
                    "or ((/s/f4:DATE_REPEAT + 2) eq 20190101)) "
                    "or ((/s/f4:DATE_REPEAT - 5) eq 20190819))"
                )

        s.check_definition()

    def test_combined_date_repeats(self):
        with pyflow.Suite("s") as s:
            with pyflow.Task("t1") as t1:
                pyflow.RepeatDate(
                    "DATE_REPEAT", datetime(2018, 1, 1), datetime(2019, 12, 31)
                )
            with pyflow.Task("t2") as t2:
                pyflow.RepeatDate(
                    "DATE_REPEAT",
                    datetime(2018, 1, 1),
                    datetime(2019, 12, 31),
                    2,
                )
        t2.triggers = t1.DATE_REPEAT == t2.DATE_REPEAT
        t2.triggers |= t1.DATE_REPEAT + 4 <= t2.DATE_REPEAT
        t2.triggers &= t1.DATE_REPEAT > t2.DATE_REPEAT - 10
        assert (
            str(t2.triggers.value) == "(((/s/t1:DATE_REPEAT eq /s/t2:DATE_REPEAT) "
            "or ((/s/t1:DATE_REPEAT + 4) le /s/t2:DATE_REPEAT)) "
            "and (/s/t1:DATE_REPEAT gt (/s/t2:DATE_REPEAT - 10)))"
        )

        s.check_definition()

    def test_combined_date_repeats_integers(self):
        with pyflow.Suite("s") as s:
            with pyflow.Task("t1") as t1:
                pyflow.RepeatDate("DATE_REPEAT", 20180101, 20191231)
            with pyflow.Task("t2") as t2:
                pyflow.RepeatDate("DATE_REPEAT", 20180101, 20191231, 2)
        t2.triggers = t1.DATE_REPEAT == t2.DATE_REPEAT
        t2.triggers |= t1.DATE_REPEAT + 4 <= t2.DATE_REPEAT
        t2.triggers &= t1.DATE_REPEAT > t2.DATE_REPEAT - 10
        assert (
            str(t2.triggers.value) == "(((/s/t1:DATE_REPEAT eq /s/t2:DATE_REPEAT) "
            "or ((/s/t1:DATE_REPEAT + 4) le /s/t2:DATE_REPEAT)) "
            "and (/s/t1:DATE_REPEAT gt (/s/t2:DATE_REPEAT - 10)))"
        )

        s.check_definition()

    def test_combined_date_repeats_date(self):
        with pyflow.Suite("s") as s:
            with pyflow.Task("t1") as t1:
                pyflow.RepeatDate("DATE_REPEAT", date(2018, 1, 1), date(2019, 12, 31))
            with pyflow.Task("t2") as t2:
                pyflow.RepeatDate(
                    "DATE_REPEAT", date(2018, 1, 1), date(2019, 12, 31), 2
                )
        t2.triggers = t1.DATE_REPEAT == t2.DATE_REPEAT
        t2.triggers |= t1.DATE_REPEAT + 4 <= t2.DATE_REPEAT
        t2.triggers &= t1.DATE_REPEAT > t2.DATE_REPEAT - 10
        assert (
            str(t2.triggers.value) == "(((/s/t1:DATE_REPEAT eq /s/t2:DATE_REPEAT) "
            "or ((/s/t1:DATE_REPEAT + 4) le /s/t2:DATE_REPEAT)) "
            "and (/s/t1:DATE_REPEAT gt (/s/t2:DATE_REPEAT - 10)))"
        )

        assert str(t1.DATE_REPEAT) == "$DATE_REPEAT"
        assert repr(t1.DATE_REPEAT) == "%DATE_REPEAT%"
        assert str(t2.DATE_REPEAT) == "$DATE_REPEAT"
        assert repr(t2.DATE_REPEAT) == "%DATE_REPEAT%"

        s.check_definition()

    def test_date_repeat_script_expansions(self):
        with pyflow.Suite("s"):
            with pyflow.Task("t1") as t1:
                pyflow.RepeatDate("DATE_REPEAT", date(2018, 1, 1), date(2019, 12, 31))
            with pyflow.Task("t2") as t2:
                pyflow.RepeatDate(
                    "DATE_REPEAT", date(2018, 1, 1), date(2019, 12, 31), 2
                )

        assert str(t1.DATE_REPEAT) == "$DATE_REPEAT"
        assert repr(t1.DATE_REPEAT) == "%DATE_REPEAT%"
        assert str(t2.DATE_REPEAT) == "$DATE_REPEAT"
        assert repr(t2.DATE_REPEAT) == "%DATE_REPEAT%"

    def test_repeat_datetime(self):
        start = datetime(year=2019, month=1, day=1, hour=12)
        end = datetime(year=2020, month=12, day=31, hour=12)
        increment = timedelta(days=1, hours=12, minutes=1, seconds=5)

        input_tests = (
            ("REPEAT_DATETIME", start, end),
            ("REPEAT_DATETIME", start, end, increment),
            (
                "REPEAT_DATETIME",
                "20200101T120000",
                "20201231T120000",
                "12:00:00",
            ),
            ("REPEAT_DATETIME", "20200101T13", "20201231T1400", "13:00"),
            ("REPEAT_DATETIME", "20200102", "20201231T080102", "12:00:00"),
            ("REPEAT_DATETIME", "20200102", end, "18:10:20"),
            ("REPEAT_DATETIME", "20200102", "20200103", "18:10"),
        )

        with pyflow.Suite("s") as s:
            for i, args in enumerate(input_tests):
                with pyflow.Task(str(i)):
                    pyflow.RepeatDateTime(*args)

        asserts = (
            "repeat datetime REPEAT_DATETIME 20190101T120000 20201231T120000 24:00:00",
            "repeat datetime REPEAT_DATETIME 20190101T120000 20201231T120000 36:01:05",
            "repeat datetime REPEAT_DATETIME 20200101T120000 20201231T120000 12:00:00",
            "repeat datetime REPEAT_DATETIME 20200101T130000 20201231T140000 13:00:00",
            "repeat datetime REPEAT_DATETIME 20200102T000000 20201231T080102 12:00:00",
            "repeat datetime REPEAT_DATETIME 20200102T000000 20201231T120000 18:10:20",
            "repeat datetime REPEAT_DATETIME 20200102T000000 20200103T000000 18:10:00",
        )

        for a in asserts:
            assert a in str(s.ecflow_definition())

        s.check_definition()

    def test_repeat_date_list(self):
        i = date(year=2019, month=12, day=31)
        j = date(year=2020, month=1, day=1)
        k = date(year=2020, month=1, day=3)

        x = "19991231"
        y = 20000101
        z = 20000102

        input_tests = (
            ("A", [i]),
            ("B", [i, j]),
            ("C", [i, j, k]),
            ("D", [x]),
            ("E", [x, y]),
            ("F", [x, y, z]),
            ("G", [i, x, j, y]),
        )

        with pyflow.Suite("s") as s:
            for idx, args in enumerate(input_tests):
                with pyflow.Task(f"t{str(idx)}"):
                    pyflow.RepeatDateList(*args)

        asserts = (
            f'repeat datelist A "{i.strftime("%Y%m%d")}"',
            f'repeat datelist B "{i.strftime("%Y%m%d")}" "{j.strftime("%Y%m%d")}"',
            f'repeat datelist C "{i.strftime("%Y%m%d")}" "{j.strftime("%Y%m%d")}" "{k.strftime("%Y%m%d")}"',
            f'repeat datelist D "{x}"',
            f'repeat datelist E "{x}" "{y}"',
            f'repeat datelist F "{x}" "{y}" "{z}"',
            f'repeat datelist G "{i.strftime("%Y%m%d")}" "{x}" "{j.strftime("%Y%m%d")}" "{y}"',
        )

        print(s.ecflow_definition())

        for a in asserts:
            print(a)
            assert a in str(s.ecflow_definition())

        s.check_definition()


class TestAviso:
    """A set of tests for Aviso attributes."""

    def test_create_aviso_from_strings(self):
        name = "AVISO_ATTRIBUTE"
        listener = "{}"
        url = "https://aviso.ecm:8888/v1"
        schema = "/path/to/schema.json"
        polling = "%ECFLOW_AVISO_POLLING%"
        auth = "/path/to/auth.json"

        attr = pyflow.Aviso(name, listener, url, schema, polling, auth)

        assert attr.name == name
        assert attr.listener == listener
        assert attr.url == url
        assert attr.schema == schema
        assert attr.polling == polling
        assert attr.auth == auth

    def test_create_aviso_from_objects(self):
        name = "AVISO_ATTRIBUTE"
        listener = json.loads(r'{ "event": "mars", "request": { "class": "od"} }')
        url = "https://aviso.ecm:8888/v1"
        schema = os.path.join(os.path.dirname(__file__), "schema.json")
        polling = 60
        auth = os.path.join(os.path.dirname(__file__), "auth.json")

        attr = pyflow.Aviso(name, listener, url, schema, polling, auth)

        assert attr.name == name
        assert attr.listener == str(listener)
        assert attr.url == url
        assert attr.schema == str(schema)
        assert attr.polling == str(polling)
        assert attr.auth == str(auth)

    def test_create_aviso_on_task(self):
        with pyflow.Suite("s") as s:
            assert "s" == s.name
            with pyflow.Family("f") as f:
                assert "f" == f.name
                with pyflow.Task("t") as t:
                    assert "t" == t.name
                    name = "AVISO_ATTRIBUTE"
                    listener = r'{ "event": "mars", "request": { "class": "od"} }'
                    url = "https://aviso.ecm:8888/v1"
                    schema = "/path/to/schema.json"
                    polling = "60"
                    auth = "/path/to/auth.json"

                    pyflow.Aviso(name, listener, url, schema, polling, auth)

        s.check_definition()

    def test_definitions_content_with_aviso_attribute(self):
        with pyflow.Suite("s") as s:
            assert "s" == s.name
            with pyflow.Family("f") as f:
                assert "f" == f.name
                with pyflow.Task("t") as t:
                    assert "t" == t.name
                    name = "AVISO_ATTRIBUTE"
                    listener = r'{ "event": "mars", "request": { "class": "od"} }'
                    url = "https://aviso.ecm:8888/v1"
                    schema = "/path/to/schema.json"
                    polling = "60"
                    auth = "/path/to/auth.json"

                    pyflow.Aviso(name, listener, url, schema, polling, auth)

        defs = s.ecflow_definition()

        assert "aviso --name AVISO_ATTRIBUTE" in str(defs)
        assert '--listener \'{ "event": "mars", "request": { "class": "od"} }\'' in str(
            defs
        )
        assert "--url https://aviso.ecm:8888/v1" in str(defs)
        assert "--schema /path/to/schema.json" in str(defs)
        assert "--auth /path/to/auth.json" in str(defs)


class TestMirror:
    """A set of tests for Mirror attributes."""

    def test_create_mirror_from_strings(self):
        name = "MIRROR_ATTRIBUTE"
        remote_path = "/s/f/t"
        remote_host = "remote-ecflow-server"
        remote_port = "3141"
        polling = "%ECFLOW_MIRROR_POLLING%"
        ssl = True
        auth = "/path/to/auth.json"

        attr = pyflow.Mirror(
            name, remote_path, remote_host, remote_port, polling, ssl, auth
        )

        assert attr.name == name
        assert attr.remote_path == remote_path
        assert attr.remote_host == remote_host
        assert attr.remote_port == remote_port
        assert attr.polling == polling
        assert attr.ssl == ssl
        assert attr.auth == auth

    def test_create_mirror_from_objects(self):
        name = "MIRROR_ATTRIBUTE"
        remote_path = "/s/f/t"
        remote_host = "remote-ecflow-server"
        remote_port = 3141
        polling = 60
        ssl = True
        auth = "/path/to/auth.json"

        attr = pyflow.Mirror(
            name, remote_path, remote_host, remote_port, polling, ssl, auth
        )

        assert attr.name == name
        assert attr.remote_path == remote_path
        assert attr.remote_host == remote_host
        assert attr.remote_port == str(remote_port)
        assert attr.polling == str(polling)
        assert attr.ssl == ssl
        assert attr.auth == auth

    def test_create_mirror_on_task(self):
        with pyflow.Suite("s") as s:
            assert "s" == s.name
            with pyflow.Family("f") as f:
                assert "f" == f.name
                with pyflow.Task("t") as t:
                    assert "t" == t.name

                    name = "MIRROR_ATTRIBUTE"
                    remote_path = "/s/f/t"
                    remote_host = "remote-ecflow-server"
                    remote_port = 3141
                    polling = 60
                    ssl = True
                    auth = "/path/to/auth.json"

                    pyflow.Mirror(
                        name, remote_path, remote_host, remote_port, polling, ssl, auth
                    )

        s.check_definition()

    def test_definitions_content_with_mirror_attribute(self):
        with pyflow.Suite("s") as s:
            assert "s" == s.name
            with pyflow.Family("f") as f:
                assert "f" == f.name
                with pyflow.Task("t") as t:
                    assert "t" == t.name

                    name = "MIRROR_ATTRIBUTE"
                    remote_path = "/s/f/t"
                    remote_host = "remote-ecflow-server"
                    remote_port = 3141
                    polling = 60
                    ssl = True
                    auth = "/path/to/auth.json"

                    pyflow.Mirror(
                        name, remote_path, remote_host, remote_port, polling, ssl, auth
                    )

        defs = s.ecflow_definition()

        assert "mirror --name MIRROR_ATTRIBUTE" in str(defs)
        assert "--remote_path /s/f/t" in str(defs)
        assert "--remote_host remote-ecflow-server" in str(defs)
        assert "--remote_port 3141" in str(defs)
        assert "--polling 60" in str(defs)
        assert "--ssl" in str(defs)
        assert "--remote_auth /path/to/auth.json" in str(defs)


def test_generated_variables():
    with pyflow.Suite("s") as s:
        with pyflow.Family("f", generated_variables=["MYVAR"]) as f:
            t = pyflow.Task("t")

    assert [var in s.all_exportables for var in s.suite_gen_vars]
    assert [var in f.all_exportables for var in f.family_gen_vars]
    assert "MYVAR" in f.all_exportables
    assert [var in t.all_exportables for var in t.task_gen_vars]


if __name__ == "__main__":
    from os import path

    pytest.main([path.abspath(__file__)])
