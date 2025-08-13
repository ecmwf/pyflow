import datetime

from pyflow import Notebook, RepeatDate, Suite, Task

now = datetime.datetime.now()


def test_follow():
    with Suite("s") as s:
        with Task("t1") as t1:
            r1 = RepeatDate("YMD", now, now)
        with Task("t2") as t2:
            RepeatDate("YMD", now, now)
        t3 = Task("t3")
        with t3:
            RepeatDate("YMD", now, now)

        t2.triggers = t1.complete
        t2.follow = r1
        t3.follow = t2.repeat

    print(s)
    s.check_definition()
    s.generate_node()

    s.deploy_suite(target=Notebook)


if __name__ == "__main__":
    from os import path

    import pytest

    pytest.main(path.abspath(__file__))
