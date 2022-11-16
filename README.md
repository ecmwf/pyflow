# Pyflow

**Pyflow** is a high level Python interface to ecFlow allowing the creation of ecFlow suites in a modular and "pythonic" way.

The documentation can be found at <https://ecmwf-pyflow.readthedocs.io>.

## Installation
To install pyflow using conda:

    conda env create -n pyflow -f environment.yml

To install pyflow using pip (requires python, ecflow and pip):

    python -m pip install .

Link the pyflow directory in the user site packages
(recommended for pyflow developers):

    python -m pip install -e .

## Tutorial
Pyflow tutorials are available in the form of a Jupyter notebook:

    jupyter-notebook tutorials/pyflow.ipynb
    jupyter-notebook tutorials/course/course.ipynb

Other learning materials can be found in the tutorials folder.

## License
[Apache License 2.0](LICENSE) In applying this licence, ECMWF does not waive the privileges and immunities 
granted to it by virtue of its status as an intergovernmental organisation nor does it submit to any jurisdiction.
