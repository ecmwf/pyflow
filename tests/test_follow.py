import datetime

from pyflow import Family, Notebook, RepeatDate, Suite, Task

# Use a date object, not the datetime.date descriptor method
now = datetime.date(2025, 8, 14)


def test_follow():
    with Suite("s") as s:
        with Task("t1"):
            r1 = RepeatDate("YMD1", now, now)
        with Family("f1") as f1:
            f1.repeat = (RepeatDate, "YMD2", now, now)
            t2 = Task("t2")
        t3 = Task("t3", repeat=(RepeatDate, "YMD3", now, now))

        t2.follow = r1
        t3.follow = t2

    s.check_definition()
    s.generate_node()

    s.deploy_suite(target=Notebook)
    print(s)
    print(t3.repeat)
    print(str(t2.triggers))
    print(str(t3.triggers))
    print(t2.triggers)
    assert "trigger ../t1 eq complete or ../f1:YMD2 lt ../t1:YMD1" in str(t2.triggers)
    assert "trigger f1/t2 eq complete or t3:YMD3 lt f1:YMD2" in str(t3.triggers)
    assert "repeat date YMD3 20250814 20250814 1" in str(t3.triggers)


if __name__ == "__main__":
    from os import path

    import pytest

    pytest.main(path.abspath(__file__))
