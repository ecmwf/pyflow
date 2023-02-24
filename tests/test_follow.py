import datetime

from pyflow import Notebook, Suite, Task, deploy_suite

now = datetime.datetime.now()


def test_follow():
    with Suite("s") as s:
        t1 = Task("t1", YMD=(now, now))
        t2 = Task("t2")
        Task("t3")

        t2.triggers = t1.complete
        t2.follow = t1.YMD

    s.check_definition()
    s.generate_node()

    deploy_suite(s, target=Notebook)


if __name__ == "__main__":
    from os import path

    import pytest

    pytest.main(path.abspath(__file__))
