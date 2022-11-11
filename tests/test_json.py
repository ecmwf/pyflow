import json
from os import path

from pyflow import Suite


def test_json():
    with open(path.join(path.dirname(path.abspath(__file__)), "test8.json")) as f:
        x = json.loads(f.read())

    s = Suite("s", json=x)

    s.check_definition()
    s.generate_node()


if __name__ == "__main__":
    import pytest

    pytest.main(path.abspath(__file__))
