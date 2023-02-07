from pyflow import Limits, Suite, Tasks


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


if __name__ == "__main__":
    from os import path

    import pytest

    pytest.main(path.abspath(__file__))
