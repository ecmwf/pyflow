import io
import os

from setuptools import find_packages, setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return io.open(file_path, encoding="utf-8").read()


exec(open("pyflow/version.py").read())


setup(
    name="pyflow",
    version=__version__,
    author="European Centre for Medium-Range Weather Forecasts (ECMWF)",
    author_email="software.support@ecmwf.int",
    license="Apache 2.0",
    description="Create pythonic ecFlow suites",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "jinja2",
        "requests",
    ],
    extras_require={"diagrams": ["graphviz"]},
)
