import pytest

import pyflow

time_values = [
    {
        "time": "00:30",
        "definition": "00:30",
    },
    {
        "time": "30 0 * * *",
        "definition": "00:30",
    },
    {
        "time": "30 * * * *",
        "definition": "00:30 23:30 01:00",
    },
    {
        "time": "0 0-23 * * *",
        "definition": "00:00 23:00 01:00",
    },
    {
        "time": "0,30 * * * *",
        "definition": "00:00 23:30 00:30",
    },
    {
        "time": "00:30 23:30 00:30",
        "definition": "00:30 23:30 00:30",
    },
    {
        "time": "+00:02",
        "definition": "+00:02",
    },
    {
        "time": "+00:10 01:00 00:05",
        "definition": "+00:10 01:00 00:05",
    },
]

time_non_supported = [
    {
        "time": "0 12 15 * *",
    },
    {
        "time": "0 12 * 1 *",
    },
    {
        "time": "0 12 * * SUN",
    },
]


@pytest.mark.parametrize("time_value", time_values)
def test_time(time_value):
    with pyflow.Suite("s") as s:
        with pyflow.Task("t"):
            pyflow.Time(time_value["time"])

    assert f"time {time_value['definition']}" in str(s.t)


@pytest.mark.parametrize("time_value", time_non_supported)
def test_non_supported_time(time_value):
    with pyflow.Suite("s") as s:
        with pyflow.Task("t"):
            pyflow.Time(time_value["time"])

    with pytest.raises(ValueError):
        assert s.t


cron_values = [
    {
        "cron": "0 23 * * *",
        "definition": "23:00",
    },
    {
        "cron": "0 8-12 * * *",
        "definition": "08:00 12:00 01:00",
    },
    {
        "cron": "0 11 * * SUN,TUE",
        "definition": "-w 0,2 11:00",
    },
    {
        "cron": "0 2 1,15 * *",
        "definition": "-d 1,15 02:00",
    },
    {
        "cron": "0 14 1 1 *",
        "definition": "-d 1 -m 1 14:00",
    },
    {
        "cron": "30 22 * * SUN",
        "definition": "-w 0 22:30",
    },
    {
        "cron": "1-3/1 2 * JAN-DEC SUN-WED",
        "definition": "-w 0,1,2,3 -m 1,2,3,4,5,6,7,8,9,10,11,12 02:01 02:03 00:01",
    },
    {
        "cron": "3-5/2 3 * JAN-DEC SUN-WED",
        "definition": "-w 0,1,2,3 -m 1,2,3,4,5,6,7,8,9,10,11,12 03:03 03:05 00:02",
    },
    {
        "timeseries": "23:00",
        "definition": "23:00",
    },
    {
        "timeseries": "23:00",
        "last_week_days_of_the_month": [5],
        "definition": "-w 5L 23:00",
    },
    {
        "timeseries": "00:00",
        "days_of_week": [0, 6],
        "definition": "-w 0,6 00:00",
    },
    {
        "timeseries": "23:00",
        "days_of_month": [1],
        "last_day_of_the_month": True,
        "definition": "-d 1,L 23:00",
    },
    {
        "timeseries": "00:00",
        "months": [1, 12],
        "definition": "-m 1,12 00:00",
    },
    {
        "timeseries": "+01:00",
        "days_of_week": [1],
        "last_week_days_of_the_month": [5],
        "days_of_month": [1],
        "last_day_of_the_month": True,
        "months": [1, 12],
        "definition": "-w 1,5L -d 1,L -m 1,12 +01:00",
    },
]


@pytest.mark.parametrize("cron_value", cron_values)
def test_cron(cron_value):
    with pyflow.Suite("s") as s:
        with pyflow.Task("t"):
            pyflow.Cron(
                cron_value.get("cron") or cron_value.get("timeseries"),
                days_of_week=cron_value.get("days_of_week"),
                last_week_days_of_the_month=cron_value.get(
                    "last_week_days_of_the_month"
                ),
                days_of_month=cron_value.get("days_of_month"),
                last_day_of_the_month=cron_value.get("last_day_of_the_month"),
                months=cron_value.get("months"),
            )

    assert f"cron {cron_value['definition']}" in str(s.t)


date_values = [
    {
        "date": "31.12.2012",
        "definition": "31.12.2012",
    },
    {
        "date": "01.*.*",
        "definition": "1.*.*",
    },
    {
        "date": "*.10.*",
        "definition": "*.10.*",
    },
    {
        "date": "1.*.2008",
        "definition": "1.*.2008",
    },
]


@pytest.mark.parametrize("date_value", date_values)
def test_date(date_value):
    with pyflow.Suite("s") as s:
        with pyflow.Task("t"):
            pyflow.Date(date_value["date"])

    assert f"date {date_value['definition']}" in str(s.t)


day_values = [
    {
        "day": "sunday",
        "definition": "sunday",
    },
    {
        "day": "monday",
        "definition": "monday",
    },
    {
        "day": "tuesday",
        "definition": "tuesday",
    },
    {
        "day": "wednesday",
        "definition": "wednesday",
    },
    {
        "day": "thursday",
        "definition": "thursday",
    },
    {
        "day": "friday",
        "definition": "friday",
    },
    {
        "day": "saturday",
        "definition": "saturday",
    },
]


@pytest.mark.parametrize("day_value", day_values)
def test_day(day_value):
    with pyflow.Suite("s") as s:
        with pyflow.Task("t"):
            pyflow.attributes.Day(day_value["day"])

    assert f"day {day_value['definition']}" in str(s.t)


if __name__ == "__main__":
    from os import path

    pytest.main(path.abspath(__file__))
