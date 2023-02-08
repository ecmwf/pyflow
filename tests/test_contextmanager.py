from pyflow import (
    Complete,
    Event,
    Events,
    Families,
    Family,
    InLimit,
    InLimits,
    Label,
    Limit,
    Meter,
    Suite,
    Task,
    Tasks,
    Trigger,
    Variable,
)


def test_suite():
    with Suite("s", FOO=12, BAR=23, YMD=99999) as s:
        Limit("foo", 1)
        Limit("bar", 2)

        with Family("f", BAR=[1, 2, 3]):
            Task("t1")
            Task("t2")
            Task("t3").triggers = (s.f.t1 == "complete") | "2 < 8"

        with Family("g") as g:
            InLimit("foo")

            g.QUUX = [1, 2]
            Task("t4").triggers = s.f.t1 == "aborted"

            with Task("t5"):
                Label("info", "Hello, world!")
                Trigger(s.f.t1 == "complete")
                Meter("step", 0, 100)
                Event("a")

            with Task("t6"):
                Variable("AAA", 56)
                Trigger(s.f.t2.complete | s.f.t1.aborted & (s.g.t5.step > 7))
                Complete(s.g.t5.a)

            with Tasks("ta", "tb", "tc"):
                Variable("ABCD", 56)
                Events("a", "b", "c")

            with Families("oper", "test"):
                InLimits("foo", "bar")
                t1 = Task("t1")
                t2 = Task("t2")
                Task("t3").triggers = t1.complete & t2.complete

        s.check_definition()


if __name__ == "__main__":
    from os import path

    import pytest

    pytest.main(path.abspath(__file__))
