import pytest

from pyflow import InLimit, Limit, Limits, Suite, Tasks


def test_inlimits():
    """
    Generate limits and inlimits. Test also the generation of multiple nodes
    of the same structure.
    """
    with Suite("s") as s:
        Limits("tlimit", "t2limit", value=3)
        Tasks("t", "t2", inlimits=lambda lim: "{}limit".format(lim.parent.name))

    s.check_definition()
    s.generate_node()


@pytest.mark.parametrize(
    "options",
    [
        {},
        {"path": "/s"},
        {"value": "tlimit"},
        {"value": "tlimit", "path": "/s"},
        {"value": "tlimit", "tokens": 1},
        {"value": "tlimit", "limit_this_node_only": True},
        {"value": "tlimit", "limit_submission": True},
    ],
)
def test_options(options):
    with Suite("s") as s:
        limit = Limit("tlimit", value=3)
        if "value" not in options:
            options["value"] = limit
        Tasks("t", "t2", inlimits=InLimit(**options))

    s.check_definition()
    s.generate_node()


if __name__ == "__main__":
    from os import path

    import pytest

    pytest.main(path.abspath(__file__))
