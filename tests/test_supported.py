import ecflow
import pytest
from packaging import version

import pyflow
from pyflow.importer import supported


def make_widget(specifier, current):
    """Build a class decorated with an explicitly instrumented specifier/current version."""

    @supported(specifier, current=current)
    class Widget:
        def __init__(self, value=0):
            self.value = value

        def a_method(self):
            "A Widget method."
            return self.value

        @property
        def a_property(self):
            "A Widget property."
            return self.value * 2

    return Widget


def test_widget_use_is_disallowed_on_older_version():
    Widget = make_widget(specifier=">=5.12.0", current="5.0.0")
    with pytest.raises(NotImplementedError):
        Widget()


def test_widget_use_is_allowed_on_newer_version():
    Widget = make_widget(specifier=">=5.12.0", current="5.13.0")
    assert Widget(3).value == 3


def test_widget_use_is_allowed_on_boundary_version():
    """The exact lower-bound version must be accepted (>= semantics)."""
    Widget = make_widget(specifier=">=5.12.0", current="5.12.0")
    assert Widget(7).value == 7


def test_widget_use_is_disallowed_on_just_below_boundary():
    Widget = make_widget(specifier=">=5.12.0", current="5.11.9")
    with pytest.raises(NotImplementedError):
        Widget()


def test_error_message_contains_specifier_and_name():
    Widget = make_widget(specifier=">=5.20.1", current="5.6.7")
    with pytest.raises(NotImplementedError) as exc:
        Widget()
    message = str(exc.value)
    assert "Widget" in message
    assert ">=5.20.1" in message
    assert "5.6.7" in message


def test_methods_are_guarded_when_unsupported():
    """Ensure non-__init__ methods also raise when unsupported."""

    Widget = make_widget(specifier=">=5.12.0", current="5.0.0")
    # __init__ is guarded too, so build with an unguarded instance via __new__.
    w = Widget.__new__(Widget)
    with pytest.raises(NotImplementedError):
        w.a_method()


def test_methods_work_when_supported():
    Widget = make_widget(specifier=">=5.12.0", current="5.20.0")
    w = Widget(5)
    assert w.a_method() == 5


def test_properties_remain_properties():
    """
    Ensure properties behave as properties (return a computed value) after decoration.
    """
    Widget = make_widget(specifier=">=5.12.0", current="5.20.0")
    w = Widget(4)
    assert w.a_property == 8
    assert isinstance(type(w).__dict__["a_property"], property)


def test_properties_are_disallowed_on_older_version():
    Widget = make_widget(specifier=">=5.12.0", current="5.0.0")
    w = Widget.__new__(Widget)
    with pytest.raises(NotImplementedError):
        _ = w.a_property


def test_properties_are_allowed_on_newer_version():
    Widget = make_widget(specifier=">=5.12.0", current="5.20.0")
    w = Widget(4)
    assert w.a_property == 8


def test_wraps_preserves_metadata():
    Widget = make_widget(specifier=">=5.12.0", current="5.20.0")
    assert Widget.a_method.__name__ == "a_method"
    assert Widget.a_method.__doc__ == "A Widget method."
    assert Widget.__dict__["a_property"].__doc__ == "A Widget property."


def test_current_defaults_to_installed_ecflow_version():
    """Without an explicit ``current``, the installed ecFlow version is used."""

    @supported(">=9999.0.0")
    class Future:
        def __init__(self):
            pass

    with pytest.raises(NotImplementedError):
        Future()

    @supported(">=0.0.1")
    class Ancient:
        def __init__(self):
            self.ok = True

    assert Ancient().ok is True


def test_compound_specifier_excludes_upper_bound():
    """A compound specifier like >=5.12.0,<5.13.0 rejects versions outside the range."""
    Widget = make_widget(specifier=">=5.12.0,<5.13.0", current="5.13.0")
    with pytest.raises(NotImplementedError):
        Widget()


def test_compound_specifier_allows_version_in_range():
    Widget = make_widget(specifier=">=5.12.0,<5.13.0", current="5.12.5")
    assert Widget(1).value == 1


# -----------------------------------------------------------------------------


def _installed_below(min_version):
    return version.parse(ecflow.__version__) < version.parse(min_version)


def test_repeat_datetime_builds_on_installed_ecflow():
    if _installed_below("5.12.0"):
        pytest.skip("RepeatDateTime requires ecFlow >= 5.12.0")

    with pyflow.Suite("s"):
        with pyflow.Task("t"):
            repeat = pyflow.RepeatDateTime(
                "REPEAT_DATETIME",
                "20190101T120000",
                "20191231T120000",
                "12:00:00",
            )

    assert repeat.name == "REPEAT_DATETIME"
    assert not callable(repeat.second)
    assert isinstance(type(repeat).__dict__["second"], property)


def test_repeat_datetimelist_builds_on_installed_ecflow():
    if _installed_below("5.17.0"):
        pytest.skip("RepeatDateTimeList requires ecFlow >= 5.17.0")

    with pyflow.Suite("s"):
        with pyflow.Task("t"):
            repeat = pyflow.RepeatDateTimeList(
                "REPEAT_DATETIME", ["20190101T120000", "20190103"]
            )

    assert repeat.name == "REPEAT_DATETIME"
    assert not callable(repeat.values)
    assert isinstance(type(repeat).__dict__["values"], property)
