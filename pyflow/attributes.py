from __future__ import absolute_import

import datetime
import re

from .anchor import AnchorMixin
from .base import Base, GenerateError
from .cron import Crontab
from .expressions import (
    Add,
    Constant,
    Div,
    Eq,
    Expression,
    Function,
    Ge,
    Gt,
    Le,
    Lt,
    Mod,
    Ne,
    Sub,
    expression_from_json,
    make_expression,
)
from .importer import ecflow
from .state import aborted, active, complete, queued, submitted, suspended, unknown

NO_TRIGGER = False
NO_INLIMIT = False
NO_LATE = False


class Attribute(Base):
    def __init__(self, name, value=None):
        super().__init__(name, value)

    @property
    def children(self):
        return []

    def relative_path(self, other):
        """
        Returns relative path of the attribute.

        Parameters:
            other(str): Relative path of the parent node.

        Returns:
            *str*: Relative path of the attribute.
        """

        # TODO: This might belong as a special case in Node._relative_path(), if both paths are equal
        rel_path = self.parent.relative_path(other)

        # Check if the relative path is invalid. Valid paths end in a node name.
        if rel_path.endswith("."):
            if rel_path.endswith(".."):
                # If the relative path ended in ".." we need to go up 2 levels
                # to reference the node correctly:
                extra_rel_path = "../../{}".format(self.parent.name)
            else:
                # Otherwise we only need to go up one level:
                extra_rel_path = "../{}".format(self.parent.name)

            # Split the relative path on "/", and discard the right-most
            # element of the result to be replaced by extra_rel_path.
            split_rel_path = rel_path.rsplit("/", 1)
            split_rel_path.pop(-1)
            split_rel_path.append(extra_rel_path)
            rel_path = "/".join(split_rel_path)

        return "%s:%s" % (rel_path, self.name)

    @property
    def fullname(self):
        """*str*: The relative path of the attribute."""
        return ":".join([self.parent.fullname, self.name])

    def __hash__(self):
        return hash(self.fullname)

    def _graph(self, dot):
        pass

    def tree(self, dot):
        pass

    def generate_stub(self):
        return []

    shape = "box"


class RepeatDay(Attribute):
    """
    An attribute that allows a node to be repeated infinitely.

    Parameters:
        value(int): The repeat step.

    Example::

        pyflow.attributes.RepeatDay(1)
    """

    def __init__(self, value):
        super().__init__("_repeat")
        self._value = value

    def _build(self, ecflow_parent):
        ecflow_parent.add_repeat(ecflow.RepeatDay(int(self.value)))


class Time(Attribute):
    """
    An attribute for setting a time dependency of the node.

    Parameters:
        value(str): Either a cron-like expression (`m h d M D`), cron-like time series expression (`start(hh:mm) end
            (hh:mm) increment(hh:mm)`) or an absolute or relative time stamp (`hh:mm`).

    Example::

        pyflow.Time("23:00")          # at next 23:00
        pyflow.Time("0 10-20 * * *")  # every hour between 10 am and 8 pm
    """

    def __init__(self, value):
        super().__init__("_time", value)

    def _build(self, ecflow_parent):
        if len(self.value) >= 5 and ":" in self.value:
            ecflow_parent.add_time(self.value)
            return

        try:
            time = Crontab(self.value, time_only=True)
        except AssertionError as exc:
            raise ValueError(f"Invalid cron-like time format: {self.value}") from exc
        ecflow_parent.add_time(time.generate_time())


class Today(Attribute):
    """
    An attribute for setting a cron dependency of the node for the current day.

    Parameters:
        value(str): A cron-like expression (`m h d M D`) for the node dependency, limited to current day.

    Example::

        pyflow.attributes.Today("0 12 * * *")  # today at 12 pm
    """

    def __init__(self, value):
        super().__init__("_today", value)

    def _build(self, ecflow_parent):
        today = Crontab(self.value)
        ecflow_parent.add_today(today.generate_today())


class Cron(Attribute):
    """
    An attribute for setting a cron dependency of the node.

    Parameters:
        value(str): Either a cron-like expression (`m h d M D`), cron-like time series expression (`start(hh:mm) end
            (hh:mm) increment(hh:mm)`) or an absolute or relative time stamp (`hh:mm`).
        days_of_week(list): The list of the days of the week when the task should run, with `0` being Sunday and `6`
            Saturday.
        last_week_days_of_the_month(list): The list of the last days of the week of the month when the task should run,
            with `0` being Sunday and `6` Saturday.
        days_of_month(list): The list of the days of the month when the task should run.
        last_day_of_the_month(bool): Whether the task should run at the last day of the month.
        months(list): The list of the months when the task should run.

    Example::

        pyflow.Cron("0 23 * * *")                                            # every day at 11 pm
        pyflow.Cron("0 8-12 * * *")                                          # every hour between 8 and 12 am
        pyflow.Cron("0 11 * * SUN,TUE")                                      # every Sunday and Tuesday at 11 am
        pyflow.Cron("0 2 1,15 * *")                                          # every 1st and 15th of each month at 2 am
        pyflow.Cron("0 14 1 1 *")                                            # every first of January at 2 pm
        pyflow.Cron("23:00", last_week_days_of_the_month=[5])                # every *last* Friday of month at 11 pm
        pyflow.Cron("23:00", days_of_month=[1], last_day_of_the_month=True)  # every first and last of month at 11 pm
    """

    def __init__(
        self,
        value,
        days_of_week=None,
        last_week_days_of_the_month=None,
        days_of_month=None,
        last_day_of_the_month=None,
        months=None,
    ):
        self._days_of_week = days_of_week
        self._last_week_days_of_the_month = last_week_days_of_the_month
        self._days_of_month = days_of_month
        self._last_day_of_the_month = last_day_of_the_month
        self._months = months
        super().__init__("_cron", value)

    def _build(self, ecflow_parent):
        if (
            ":" in self.value
            or self._days_of_week
            or self._last_week_days_of_the_month
            or self._days_of_month
            or self._last_day_of_the_month
            or self._months
        ):
            cron = ecflow.Cron()

            if self._days_of_week:
                cron.set_week_days(self._days_of_week)

            if self._last_week_days_of_the_month:
                cron.set_last_week_days_of_the_month(self._last_week_days_of_the_month)

            if self._days_of_month:
                cron.set_days_of_month(self._days_of_month)

            if self._last_day_of_the_month:
                cron.set_last_day_of_the_month()

            if self._months:
                cron.set_months(self._months)

            cron.set_time_series(self.value)
            ecflow_parent.add_cron(cron)
            return

        cron = Crontab(self.value)
        ecflow_parent.add_cron(cron.generate_cron())


class Crons(Attribute):
    """
    An attribute for setting a cron time series dependency of the node.

    Parameters:
        value(str): A cron-like time series expression (`start(hh:mm) end(hh:mm) increment(hh:mm)`) for the node
            dependency.

    Example::

        pyflow.Crons("00:00 23:59 00:05")  # every 5 minutes during the day
    """

    def __init__(self, value):
        super().__init__("_cron", value)

    def _build(self, ecflow_parent):
        cron = ecflow.Cron()
        cron.set_time_series(self.value)
        ecflow_parent.add_cron(cron)


class Exportable(Attribute):
    """
    All types that will generate an export `FOO=%FOO%` statement.
    """

    def __init__(self, name, value=None):
        super().__init__(name, value)
        # By default, we don't export to script
        self.export = False

    def __str__(self):
        return "${}".format(self.name)

    def __repr__(self):
        return "%{}%".format(self.name)


class Variable(Exportable):
    """
    An attribute for setting an **ecFlow** variable.

    Parameters:
        name(str): The name of the variable.
        value(str): The value of the variable.

    Example::

        Variable('FOO', 'foo_value')
    """

    def __init__(self, name, value):
        if not is_variable(name):
            raise ValueError("'{}' is not a valid variable name".format(name))
        super().__init__(name, value)

    def _build(self, ecflow_parent):
        ecflow_parent.add_variable(str(self.name), str(self.value))


class GeneratedVariable(Exportable):
    """
    An attribute for referencing an **ecFlow** generated variable.
    The variable value will be generated automatically by ecFlow.

    Parameters:
        name(str): The name of the variable.

    Example::

        GeneratedVariable('FOO')
    """

    def __init__(self, name):
        if not is_variable(name):
            raise ValueError("'{}' is not a valid variable name".format(name))
        super().__init__(name)

    def _build(self, *args, **kwargs):
        return


class Edit:
    """
    An attribute for setting multiple **ecFlow** variables.

    Parameters:
        **kwargs(dict): Accept keyword arguments as variables to be set.

    Example::

        pyflow.Edit(FOO='foo_value', BAR='bar_value')
    """

    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            Variable(key, val)


class RepeatString(Exportable):
    """
    An attribute that allows a node to be repeated by a string value.

    Parameters:
        name(str): The name of the repeat attribute.
        list(tuple): The list of string values for the repeat attribute.

    Example::

        pyflow.RepeatString("COLOR", ["red", "green", "blue"])
    """

    def __init__(self, name, value):
        super().__init__(name, value)

    def _build(self, ecflow_parent):
        repeat = ecflow.RepeatString(self.name, self.values)
        ecflow_parent.add_repeat(repeat)

    @property
    def values(self):
        """*list*: The list of repeat string values."""
        return [str(x) for x in self.value]

    def _other_value(self, other):
        """
        In triggers and other expressions, ecflow will _always_ return the index rather than the
        value from a RepeatString.

        As a result, if in _pyflow_ a string is supplied for the other value we should look this
        up in the values and return the index. But otherwise (especially if it is an _expression_
        that will evaluate to an index at runtime, then this value should just be used directly.
        """
        if isinstance(other, str):
            for i, n in enumerate(self.values):
                if n == other:
                    return i

        if not isinstance(other, (int, RepeatString, Expression)):
            raise ValueError(
                "RepeatString: Cannot find {} in {}".format(other, self.values)
            )

        return other

    def __eq__(self, other):
        return Eq(self, self._other_value(other))

    def __ne__(self, other):
        return Ne(self, self._other_value(other))

    def __lt__(self, other):
        return Lt(self, self._other_value(other))

    def __le__(self, other):
        return Le(self, self._other_value(other))

    def __gt__(self, other):
        return Gt(self, self._other_value(other))

    def __ge__(self, other):
        return Ge(self, self._other_value(other))

    def __add__(self, other):
        return Add(self, other)

    def __sub__(self, other):
        return Sub(self, other)


class RepeatEnumerated(Exportable):
    """
    An attribute that allows a node to be repeated by an enumerated list.

    Parameters:
        name(str): The name of the repeat attribute.
        list(tuple): The list of enumerations for the repeat attribute.

    Example::

        pyflow.RepeatEnumerated("REPEAT_STRING", ["a", "b", "c", "d", "e"])
    """

    def __init__(self, name, value):
        super().__init__(name, value)

    def _build(self, ecflow_parent):
        repeat = ecflow.RepeatEnumerated(self.name, self.values)
        ecflow_parent.add_repeat(repeat)

    @property
    def values(self):
        """*list*: The list of enumerated values."""
        return [str(x) for x in self.value]

    def settings(self):
        return self.value

    def __add__(self, other):
        return Add(self, other)

    def __sub__(self, other):
        return Sub(self, other)


class RepeatDateList(Exportable):
    """
    An attribute that allows a node to be repeated over a list of dates.

    Parameters:
        name(str): The name of the repeat attribute.
        list(tuple): The list of dates for the repeat attribute.

    Example::

        pyflow.RepeatDateList("REPEAT_DATELIST", ["20000101", "20000102", "20000103", "d", "e"])
    """

    def __init__(self, name, value):
        super().__init__(name, value)

    def _build(self, ecflow_parent):
        repeat = ecflow.RepeatDateList(self.name, self.values)
        ecflow_parent.add_repeat(repeat)

    @property
    def values(self):
        """*list*: The list of date values (as integers)."""
        # Convert dates to numerical values
        v = [
            x.strftime("%Y%m%d") if isinstance(x, datetime.date) else x
            for x in self.value
        ]
        # Convert all values to integers
        v = [int(x) for x in v]
        return v

    def settings(self):
        return self.value

    def __add__(self, other):
        return Add(self, other)

    def __sub__(self, other):
        return Sub(self, other)


class RepeatInteger(Exportable):
    """
    An attribute that allows a node to be repeated by an integer range.

    Parameters:
        name(str): The name of the repeat attribute.
        start(int): The start integer value of the repeat attribute.
        end(datetime): The end integer value of the repeat attribute.
        increment(int): The step amount used to update the integer.

    Example::

        pyflow.RepeatInteger("REPEAT_INTEGER", 1, 5, 1)
    """

    def __init__(self, name, start, end, increment=1):
        super().__init__(name)
        self._start = start
        self._end = end
        self._increment = increment

    def _build(self, ecflow_parent):
        start = self._start(self) if callable(self._start) else self._start
        end = self._end(self) if callable(self._end) else self._end
        increment = (
            self._increment(self) if callable(self._increment) else self._increment
        )

        repeat = ecflow.RepeatInteger(self.name, start, end, increment)
        ecflow_parent.add_repeat(repeat)

    def __add__(self, other):
        return Add(self, other)

    def __sub__(self, other):
        return Sub(self, other)


class RepeatDate(Exportable):
    """
    An attribute that allows a node to be repeated by a date value.

    Parameters:
        name(str): The name of the repeat attribute.
        start(datetime): The start date of the repeat attribute.
        end(datetime): The end date of the repeat attribute.
        increment(int): The increment used to update the date.

    Example::

        pyflow.RepeatDate('REPEAT_DATE',
                          datetime.date(year=2019, month=1, day=1),
                          datetime.date(year=2019, month=12, day=31))
    """

    def __init__(self, name, start, end, increment=1):
        super().__init__(name)
        self._start = start
        self._end = end
        self._increment = increment

    def _build(self, ecflow_parent):
        start = self._start(self) if callable(self._start) else self._start
        end = self._end(self) if callable(self._end) else self._end
        increment = (
            self._increment(self) if callable(self._increment) else self._increment
        )

        repeat = ecflow.RepeatDate(
            str(self.name),
            int(as_date(start).strftime("%Y%m%d")),
            int(as_date(end).strftime("%Y%m%d")),
            increment,
        )

        ecflow_parent.add_repeat(repeat)

    def __add__(self, other):
        if isinstance(other, int):
            result = Add(self, other)
        else:
            result = Add(self.julian, other.julian)
        return result

    def __sub__(self, other):
        if isinstance(other, int):
            result = Sub(self, other)
        else:
            result = Sub(self.julian, other.julian)
        return result

    def settings(self):
        return self._start, self._end, self._increment

    @property
    def julian(self):
        """*int*: The Julian date of the repeat date."""
        return Function("cal::date_to_julian", self)

    @property
    def day(self):
        """*int*: The day of the repeat date."""
        return Mod(self, 100)

    @property
    def month(self):
        """*int*: The month of the repeat date."""
        return Mod(Div(self, 100), 100)

    @property
    def year(self):
        """*int*: The year of the repeat date."""
        return Mod(self, 10000)

    @property
    def day_of_week(self):
        """*int*: The day of the week of the repeat date."""
        return Mod(self.julian, 7)


for dow, day in enumerate(
    (
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    )
):
    setattr(RepeatDate, day, property(lambda self: Eq(self.day_of_week, dow)))


class RepeatDateTime(Exportable):
    """
    An attribute that allows a node to be repeated by a date+time value.

    Parameters:
        name(str): The name of the repeat attribute.
        start(datetime): The start date of the repeat attribute.
        end(datetime): The end date of the repeat attribute.
        increment(timedelta): The increment used to update the datetime.

    Example::

        pyflow.RepeatDateTime('REPEAT_DATETIME',
                              datetime.datetime(year=2019, month=1, day=1, hour=12, minute=0, second=0),
                              datetime.datetime(year=2019, month=12, day=31, hour=12, minute=0, second=0),
                              datetime.timedelta(hours=12, minutes=0, seconds=0))

    Date and increment can also be strings::

        pyflow.RepeatDateTime('REPEAT_DATETIME',
                              '20190101T120000', '20191231T120000', '12:00:00')

    """

    def __init__(
        self,
        name,
        start,
        end,
        increment=datetime.timedelta(hours=24, minutes=0, seconds=0),
    ):
        super().__init__(name)
        self._start = start
        self._end = end
        self._increment = increment

    def _build(self, ecflow_parent):
        start = self._start(self) if callable(self._start) else self._start
        end = self._end(self) if callable(self._end) else self._end
        increment = (
            self._increment(self) if callable(self._increment) else self._increment
        )

        repeat = ecflow.RepeatDateTime(
            str(self.name),
            as_date(start).strftime("%Y%m%dT%H%M%S"),
            as_date(end).strftime("%Y%m%dT%H%M%S"),
            self._delta_to_string(as_delta(increment)),
        )

        ecflow_parent.add_repeat(repeat)

    def __add__(self, other):
        return Add(self, other)

    def __sub__(self, other):
        return Sub(self, other)

    def settings(self):
        return self._start, self._end, self._increment

    def _delta_to_string(self, delta):
        # there is no strftime for timedelta so we make our own
        total_seconds = int(delta.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)

    @property
    def second(self):
        """*int*: The second of the repeat datetime."""
        return Mod(self, 60)

    @property
    def minute(self):
        """*int*: The minute of the repeat datetime."""
        return Mod(Div(self, 60), 60)

    @property
    def hour(self):
        """*int*: The hour of the repeat datetime."""
        return Mod(Div(self, 3600), 24)

    @property
    def day_of_week(self):
        """*int*: The day of the week of the repeat datetime."""
        return Mod(Add(Div(self, 86400), 4), 7)


def string_or_enumerated(name, value):
    if all(isinstance(v, int) for v in value):
        return RepeatEnumerated(name, value)
    return RepeatString(name, value)


def is_date(value):
    return (
        isinstance(value, (datetime.date, datetime.datetime))
        or (isinstance(value, str) and re.match(r"^\d\d\d+-\d\d-\d\d$", value))
        or (isinstance(value, int) and value > 19000100 and value < 21990101)
        or (isinstance(value, int) and value > 1900010000 and value < 2199010100)
    )


def as_date(value):
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value

    if isinstance(value, int) and value < 21990101:
        y = value // 10000
        m = (value // 100) % 100
        d = value % 100

    elif isinstance(value, str):
        if "T" in value:
            for format in ("%Y%m%dT%H", "%Y%m%dT%H%M", "%Y%m%dT%H%M%S"):
                try:
                    return datetime.datetime.strptime(value, format)
                except ValueError:
                    pass
            raise ValueError(
                'Argument "{}" should be in format '
                "yyyymmddTHHMMSS, yyyymmddTHHMM or yyyymmddTHH".format(value)
            )
        elif "-" in value:
            y, m, d = [int(x, 10) for x in value.split("-")]
        else:
            y = int(value[:4])
            m = int(value[4:6])
            d = int(value[6:8])
    else:
        raise ValueError('Argument "{}" cannot be converted to date'.format(value))

    return datetime.datetime(y, m, d)


def as_delta(value):
    if isinstance(value, datetime.timedelta):
        return value

    if isinstance(value, str):
        if ":" in value:
            try:
                split = [int(x) for x in value.split(":")]
                if len(split) == 2:
                    split.append(0)
                return datetime.timedelta(
                    hours=split[0], minutes=split[1], seconds=split[2]
                )
            except ValueError:
                raise ValueError(
                    'Argument "{}" should be in format '
                    '"HH:MM:SS" or "HH:MM"'.format(value)
                )

    raise ValueError('Argument "{}" cannot be converted to timedelta'.format(value))


def is_variable(name):
    return name.upper() == name and name[0].isalpha()


def make_variable(node, name, value):
    # Certain ecFlow variables may only be set on the Suite
    if (
        (name in {"ECF_HOME", "ECF_FILES", "ECF_INCLUDE"} and node.suite is not node)
        and (node.suite.has_variable(name) or node.parent is not node.suite)
        and (not isinstance(node, AnchorMixin))
    ):
        raise RuntimeError("{} can only be set at the suite level".format(name))

    with node:
        if isinstance(value, (tuple, list)):
            if len(value) in [2, 3]:
                if is_date(value[0]) and is_date(value[1]):
                    if len(value) == 3:
                        if isinstance(value[2], int):
                            return RepeatDate(
                                name,
                                as_date(value[0]),
                                as_date(value[1]),
                                value[2],
                            )
                    else:
                        return RepeatDate(name, as_date(value[0]), as_date(value[1]), 1)

                if isinstance(value[0], int) and isinstance(value[1], int):
                    if len(value) == 3:
                        if isinstance(value[2], int):
                            return RepeatInteger(name, value[0], value[1], value[2])
                    else:
                        return RepeatInteger(name, value[0], value[1], 1)

            return string_or_enumerated(name, value)

        if isinstance(value, (str, int, float)):
            return Variable(name, value)

        if callable(value):
            return Variable(name, value)

    raise ValueError("Cannot convert", value, type(value), "into variable or repeat")


class _Trigger(Attribute):
    def _build(self, ecflow_parent):
        simplified = make_expression(self.value).simplify()
        if isinstance(simplified, Constant):
            raise GenerateError(
                'Trigger expression "{}" simplifies to constant "{}" for node {}'.format(
                    self.value, simplified, self.parent.fullname
                )
            )
        e = simplified.generate_expression(self.parent)
        if e == NO_TRIGGER:
            return
        if ecflow_parent.get_trigger() is None:
            ecflow_parent.add_trigger(str(e))
        else:
            ecflow_parent.add_part_trigger(str(e), True)

    def _graph(self, dot):
        make_expression(self.value).simplify()._graph(dot, self.parent)


class Trigger(_Trigger):
    """
    An attribute for setting a condition for running the node depending on other tasks or families.

    Parameters:
        value(expression): Expression to evaluate for running the node.
        *args(tuple): Accept extra positional arguments for expressions provided as a JSON value.

    Example::

        pyflow.Trigger(t1 & t2)
    """

    def __init__(self, value, *args):
        if len(args) > 0 and isinstance(value, str):
            # JSON expression
            value = expression_from_json({value: args})

        super().__init__("_trigger", value)

    def __repr__(self):
        return "Trigger(%r)" % self.value


class Complete(Attribute):
    """
    An attribute for setting a condition for setting the node as complete depending on other tasks or families.

    Note:
        Complete expression evaluation takes precedence over the trigger.

    Parameters:
        value(expression): Expression to evaluate for setting the node as complete.

    Example::

        pyflow.Complete(t1 & t2)
    """

    def __init__(self, value):
        super().__init__("_complete", make_expression(value))

    def _build(self, ecflow_parent):
        ecflow_parent.add_complete(
            self.value.simplify().generate_expression(self.parent)
        )

    def __repr__(self):
        return "Complete(%r)" % self.value

    def _graph(self, dot):
        self.value._graph(dot, self.parent)


class Limit(Attribute):
    """
    An attribute for a simple load management by limiting the number of tasks submitted by a specific **ecFlow** server.

    Parameters:
        name(str): The name of the limit.
        value(int): The maximum number of tasks.

    Example::

        pyflow.Limit('l', 3)
    """

    def __init__(self, name, value):
        super().__init__(name, value)

    def _build(self, ecflow_parent):
        ecflow_parent.add_limit(ecflow.Limit(str(self.name), self.value))


class Label(Attribute):
    """
    An attribute for a string value that can be set from a script.

    Parameters:
        name(str): The name of the label.
        value(str): The initial value of the label.

    Example::

        pyflow.attributes.Label('foo', 'bar')
    """

    def __init__(self, name, value):
        super().__init__(name, value)

    def _build(self, ecflow_parent):
        ecflow_parent.add_label(ecflow.Label(str(self.name), str(self.value)))


class InLimit(Attribute):
    """
    An attribute for grouping of nodes to which a limit should be applied.

    Parameters:
        value(str,Limit_): The name of the limit or a limit object.

    Example::

        l = pyflow.Limit('l', 3)
        pyflow.InLimit(l)
    """

    def __init__(self, value):
        super().__init__("_" + str(value), value)

    def _build(self, ecflow_parent):
        value = self.value
        if NO_INLIMIT:
            return
        if isinstance(value, Limit):
            value = value.fullname.split(":")
            ecflow_parent.add_inlimit(ecflow.InLimit(value[1], value[0]))
        else:
            ecflow_parent.add_inlimit(ecflow.InLimit(str(value)))


class Inlimit(InLimit):
    """
    An attribute for grouping of tasks to which a limit should be applied.

    Parameters:
        value(str,Limit_): The name of the limit or a limit object.

    Example::

        l = pyflow.Limit('l', 3)
        pyflow.Inlimit(l)
    """

    pass


class Meter(Attribute):
    """
    An attribute for a range of integer values that can be set from a script.

    Parameters:
        name(str): The name of the meter.
        min(int,tuple,list): Minimum value of the meter. Alternatively, a tuple or list containing minimum, maximum and
            threshold value of the meter.
        max(int): Maximum value of the meter.
        threshold(int): Threshold value of the meter.

    Example::

        pyflow.Meter('progress', 1, 100, 90)
    """

    def __init__(self, name, min, max=None, threshold=None):
        super().__init__(name)

        if isinstance(min, (tuple, list)):
            if len(min) == 2:
                min, max = min
            else:
                min, max, threshold = min

        self._min = min
        self._max = max
        if threshold is None:
            self._threshold = max
        else:
            self._threshold = threshold

    def _build(self, ecflow_parent):
        min = self._min(self) if callable(self._min) else self._min
        max = self._max(self) if callable(self._max) else self._max
        threshold = (
            self._threshold(self) if callable(self._threshold) else self._threshold
        )

        ecflow_parent.add_meter(ecflow.Meter(str(self.name), min, max, threshold))


class Event(Attribute):
    """
    An attribute for declaring an action that a node can trigger while it is running.

    Parameters:
        name(str): The name of the event.

    Example::

        pyflow.Event('a')
    """

    def __init__(self, name):
        super().__init__(str(name))

    def _build(self, ecflow_parent):
        ecflow_parent.add_event(ecflow.Event(self.name))


class Defstatus(Attribute):
    """
    An attribute for declaring the default status of the node.

    Parameters:
        value(State_): Default state to set for the node.

    Example::

        pyflow.Defstatus(pyflow.state.suspended)
    """

    def __init__(self, value):
        if value not in (
            complete,
            unknown,
            aborted,
            submitted,
            suspended,
            active,
            queued,
        ):
            raise ValueError('invalid defstatus "{}"'.format(value))
        super().__init__("_defstatus", value)

    def _build(self, ecflow_parent):
        ecflow_parent.add_defstatus(self.value)


class DefCompleteIf(Defstatus):
    def __init__(self, expression):
        self.expression = expression
        if expression:
            super().__init__("_defstatus", complete)

    def _build(self, ecflow_parent):
        if self.expression:
            ecflow_parent.add_defstatus(self.value)


###################################################################


class Autocancel(Attribute):
    """
    An attribute for automatic removal of the node which has completed.

    Parameters:
        value(bool,int,str,list,tuple): The time slot arguments for autocancel attribute. If `True` the node will be
            removed as soon as it has completed. If a list or tuple, items will be used for hour and minute when the
            node will be removed.
        value2(str): The optional minute argument in case first argument contained only hour.

    Example::

         pyflow.attributes.Autocancel(True)      # delete node immediately after completion
         pyflow.attributes.Autocancel('+01:30')  # delete node 1 hour and 30 minutes after completion
         pyflow.attributes.Autocancel((1, 30))   # delete node at 1:30 am after completion
         pyflow.attributes.Autocancel(1, 30)     # delete node at 1:30 am after completion
         pyflow.attributes.Autocancel(3)         # delete node 3 days after completion
    """

    def __init__(self, value, value2=None):
        super().__init__("_autocancel")

        if value2 is not None:
            value = (value, value2)

        if isinstance(value, (list, tuple)) and len(value) == 2:
            value = "%02d:%02d" % (value[0], value[1])

        if value is True:
            value = "+00:00"

        if isinstance(value, int):
            value = str(value)

        self._value = value

    def _build(self, ecflow_parent):
        value = self.value

        if value[0] == "+":
            relative = True
            v = [int(x, 10) for x in value[1:].split(":")]
        else:
            relative = False
            v = [int(x, 10) for x in value.split(":")]

        if len(v) == 1:
            ecflow_parent.add_autocancel(ecflow.Autocancel(v[0]))
        else:
            ecflow_parent.add_autocancel(
                ecflow.Autocancel(ecflow.TimeSlot(*v), relative)
            )


###################################################################


class Day(Attribute):
    """
    An attribute for setting a day of the week dependency of the node.

    Parameters:
        value(str): Day of the week of the dependency.

    Example::

        pyflow.attributes.Day('monday')  # every monday
    """

    def __init__(self, value):
        super().__init__("_day_%s" % (value,), value)

    def _build(self, ecflow_parent):
        ecflow_parent.add_day(str(self.value))


class Date(Attribute):
    """
    An attribute for setting a date dependency of the node.

    Note:
        All string values support wildcards (`*`).

    Parameters:
        value(str,datetime): Either the day of the month (`d`), the complete date (`d.M.Y`) or the `datetime` object of
            the date dependency.
        value2(str): Month of the date dependency (`M`).
        value3(str): Year of the date dependency (`Y`).

    Example::

        pyflow.Date("31.12.2012")  # the 31st of December 2012
        pyflow.Date("01.*.*")      # every first of the month
        pyflow.Date("*.10.*")      # every day in October
        pyflow.Date("1.*.2008")    # every first of the month, but only in 2008
    """

    def __init__(self, value, value2=None, value3=None):
        super().__init__("_date_%s_%s_%s" % (value, value2, value3))

        if isinstance(value, (datetime.date, datetime.datetime)):
            value = (value.day, value.month, value.year)

        elif isinstance(value, str):
            value = [None if x == "*" else int(x) for x in value.split(".")]

        else:
            value = (value, value2, value3)

        self._value = [0 if x is None else int(x) for x in value]

    def _build(self, ecflow_parent):
        ecflow_parent.add_date(ecflow.Date(*self._value))


###################################################################


class Manual(Attribute):
    """
    An attribute for setting help text of the node.

    Parameters:
        value(str): The help text or list of help texts to include in the node.

    Example::

        pyflow.attributes.Manual('This is a multi-line manual\\nwhich can contain instructions')
    """

    def __init__(self, value):
        super().__init__("_manual", value)

    def _build(self, ecflow_parent):
        pass

    def generate_stub(self):
        if not self.value.strip():
            return []

        return (
            ["%manual"] + [line.rstrip() for line in self.value.split("\n")] + ["%end"]
        )


###################################################################


class Follow(_Trigger):
    """
    An attribute for setting a condition for running the node behind another repeated node which has completed.

    Parameters:
        value(RepeatDate_): The repeat date attribute of the followed node.

    Example::

        pyflow.attributes.Follow(pyflow.RepeatDate('REPEAT_DATE',
                                                   datetime.date(year=2019, month=1, day=1),
                                                   datetime.date(year=2019, month=12, day=31)))
    """

    def __init__(self, value):
        super().__init__("_follow_%s" % (value,), value)
        if not hasattr(value, "settings"):
            raise Exception(
                "Cannot follow a node of type %s (%r)" % (type(value), value)
            )
        self.parent[value.name] = value.settings()
        self._value = value.parent.complete | (self.parent[value.name] < value)


###################################################################


class Zombies(Attribute):
    """
    An attribute that defines how a zombie should be handled in an automated fashion.

    Parameters:
        value(str): A custom way a zombie should be handled when encountered.

    Example::

        pyflow.attributes.Zombies(None)
    """

    def __init__(self, value):
        super().__init__("_zombies", value)

    def _build(self, ecflow_parent):
        if not self.value:
            sources = [
                ecflow.ZombieType.ecf,
                ecflow.ZombieType.path,
                ecflow.ZombieType.user,
            ]
            nodes = []
            action = ecflow.ZombieUserActionType.fob

            for s in sources:
                z = ecflow.ZombieAttr(s, nodes, action, 300)
                ecflow_parent.add_zombie(z)


class Late(Attribute):
    """
    An attribute for a flag for notifying if task does not run as expected.

    Parameters:
        value(str): Expression to evaluate for setting the late flag.

    Example::

        pyflow.Late('-c +00:01')  # set late flag if task takes longer than a minute
    """

    def __init__(self, value):
        super().__init__("_late", value)
        import argparse

        parser = argparse.ArgumentParser("Late")
        parser.add_argument("-s", help="submitted")
        parser.add_argument("-c", help="complete")
        parser.add_argument("-a", help="active")
        opt = parser.parse_args(value.split())
        self.late = ecflow.Late()
        if opt.s:
            self._add(opt.s, self.late.submitted, 0)
        if opt.c:
            self._add(opt.c, self.late.complete)
        if opt.a:
            self._add(opt.a, self.late.active)

    def _build(self, ecflow_parent):
        if NO_LATE:
            return
        ecflow_parent.add_late(self.late)

    def _add(self, time, adder, rel=1):
        rel = rel & (time[0] == "+")
        if rel:
            time = time[1:]
        hour, mins = [int(x) for x in time.split(":")]
        if rel:
            adder(ecflow.TimeSlot(hour, mins), rel)
        else:
            adder(ecflow.TimeSlot(hour, mins))


###################################################################


class Aviso(Attribute):
    """
    An attribute that allows a node to be triggered by an external Aviso notification.

    Parameters:
        name(str): The name of the attribute.
        listener(str): The listener configuration.
        url(str): The URL to the Aviso server.
        schema(str): The schema used to process Aviso notifications.
        polling(str, int): The time interval used to poll the Aviso server.
        auth(str): The path to the Aviso authentication credentials file.

    Example::

        pyflow.Aviso("AVISO_NOTIFICATION",
                     r'{ "event": "mars", "request": { "class": "od"} }',
                    "https://aviso.ecm:8888/v1",
                    "/path/to/schema.json"
                    60,
                    "/path/to/auth.json")

    """

    def __init__(self, name, listener, url, schema, polling, auth):
        super().__init__(name)
        self.listener = str(listener)
        self.url = str(url)
        self.schema = str(schema)
        self.polling = str(polling)
        self.auth = str(auth)

    def _build(self, ecflow_parent):
        # The listener configuration must be provided as a single-quoted JSON string
        quoted_listener_cfg = "'{}'".format(self.listener)

        aviso = ecflow.AvisoAttr(
            self.name,
            quoted_listener_cfg,
            self.url,
            self.schema,
            self.polling,
            self.auth,
        )

        ecflow_parent.add_aviso(aviso)


###################################################################


class Mirror(Attribute):
    """
    An attribute that allows a node status to be synchronized with a node from another ecFlow server.

    Parameters:
        name(str): The name of the attribute.
        remote_path(str): The path to the mirrored node on the remote ecFlow server.
        remote_host(str): The host used to connect to the remote ecFlow server.
        remote_port(str, int): The port used to connect to the remote ecFlow server.
        polling(str, int): The time interval used to poll the remote ecFlow server.
        ssl(bool): The flag indicating if SSL communication is enabled.
        auth(str): The path to the ecFlow authentication credentials file.


    Example::

        pyflow.Mirror("NODE_MIRROR"
                     "/suite/family/task",
                     "remote-ecflow-server",
                     "3141",
                     60,
                     False
                     "/path/to/auth.json")

    """

    def __init__(self, name, remote_path, remote_host, remote_port, polling, ssl, auth):
        super().__init__(name)
        self.remote_path = str(remote_path)
        self.remote_host = str(remote_host)
        self.remote_port = str(remote_port)
        self.polling = str(polling)
        self.ssl = bool(ssl)
        self.auth = str(auth)

    def _build(self, ecflow_parent):
        mirror = ecflow.MirrorAttr(
            self.name,
            self.remote_path,
            self.remote_host,
            self.remote_port,
            self.polling,
            self.ssl,
            self.auth,
        )

        ecflow_parent.add_mirror(mirror)
