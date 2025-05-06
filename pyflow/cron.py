from __future__ import absolute_import, print_function

import itertools

from .importer import ecflow

# https://crontab.guru/
MAP = {
    "SUN": 0,
    "MON": 1,
    "TUE": 2,
    "WED": 3,
    "THU": 4,
    "FRI": 5,
    "SAT": 6,
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


def _num(a, first, last):
    a = MAP.get(a.upper()[:3], a)
    return (int(a) - first) % (last - first + 1) + first


def _parse(m, first, last):
    if m == "*":
        return None

    result = []
    for p in m.split(","):
        a = p.split("/")
        assert len(a) in [1, 2]
        if len(a) == 1:
            a.append("1")
        b = a[0].split("-")
        assert len(b) in [1, 2]
        if len(b) == 1:
            b.append(b[0])

        value = (
            _num(b[0], first, last),
            _num(b[1], first, last),
            _num(a[1], first, last),
        )
        assert value[0] <= value[1]
        result.append(value)

    return result


def _expand(y):
    if y is None:
        return None

    result = set()
    for x in y:
        for i in range(x[0], x[1] + x[2], x[2]):
            result.add(i)
    return sorted(result)


def minutes(m):
    return _parse(m, 0, 59)


def hours(m):
    return _parse(m, 0, 23)


def days_of_month(m):
    return _parse(m, 1, 31)


def months(m):
    return _parse(m, 1, 12)


def days_of_week(m):
    return _parse(m, 0, 6)


def parse_cron(c):
    minute, hour, day_of_month, month, day_of_week = c.split(" ")

    minute = minutes(minute)
    hour = hours(hour)
    day_of_month = days_of_month(day_of_month)
    month = months(month)
    day_of_week = days_of_week(day_of_week)

    return minute, hour, day_of_month, month, day_of_week


def increment(a, b):
    m1 = a[0] * 60 + a[1]
    m2 = b[0] * 60 + b[1]
    m3 = m1 - m2
    return m3 // 60, m3 % 60


class Crontab:
    def __init__(self, cron, time_only=False):
        minute, hour, day_of_month, month, day_of_week = parse_cron(cron)
        self._day_of_week = _expand(day_of_week)
        self._day_of_month = _expand(day_of_month)
        self._month = _expand(month)

        if time_only:
            assert self._day_of_week is None, "Day of week not supported"
            assert self._day_of_month is None, "Day of month not supported"
            assert self._month is None, "Month not supported"

        if minute is None and hour is None:
            ts = ecflow.TimeSeries(
                ecflow.TimeSlot(0, 0),
                ecflow.TimeSlot(23, 59),
                ecflow.TimeSlot(0, 1),
            )
        else:
            if minute is None:
                minute = range(0, 60)
            else:
                minute = _expand(minute)

            if hour is None:
                hour = range(0, 24)
            else:
                hour = _expand(hour)

            ts = set()
            for h, m in itertools.product(hour, minute):
                ts.add((h, m))

            assert len(ts) > 0
            ts = sorted(ts)
            if len(ts) == 1:
                ts = ecflow.TimeSeries(ecflow.TimeSlot(ts[0][0], ts[0][1]))
            else:
                inc = increment(ts[1], ts[0])
                for i, t in enumerate(ts[1:]):
                    inc2 = increment(t, ts[i])
                    if inc != inc2:
                        raise Exception("Cron: Cannot represent %s" % cron)

                ts = ecflow.TimeSeries(
                    ecflow.TimeSlot(*ts[0]),
                    ecflow.TimeSlot(*ts[-1]),
                    ecflow.TimeSlot(*inc),
                )

        self._timeseries = ts

    def generate_today(self):
        assert self._day_of_week is None
        assert self._day_of_month is None
        assert self._month is None
        return ecflow.Today(self._timeseries)

    def generate_time(self):
        assert self._day_of_week is None
        assert self._day_of_month is None
        assert self._month is None
        return ecflow.Time(self._timeseries)

    def generate_cron(self):
        cron = ecflow.Cron()

        if self._day_of_week is not None:
            cron.set_week_days(self._day_of_week)

        if self._day_of_month is not None:
            cron.set_days_of_month(self._day_of_month)

        if self._month is not None:
            cron.set_months(self._month)

        cron.set_time_series(self._timeseries)

        return cron


if __name__ == "__main__":
    print(Crontab("1-3/1,3-5/2 2,3,5 * JAN-DEC SUN-WED"))
    print(Crontab("10:30"))
    print(Crontab("10:30 23:59 01:00"))
