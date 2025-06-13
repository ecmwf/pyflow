Installation
============


.. index:: Dependencies

Dependencies
------------


.. index:: Dependencies; Required

Required
~~~~~~~~

* Python 3.x
* `ecFlow`_


.. index:: Dependencies; Optional

Optional
~~~~~~~~

* `Jupyter Notebook`_


Setup
-----

Conda Environment (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An environment definition file to setup Conda is provided at the root of the **pyflow** repository. 
The following commands create a suitable environment with all necessary dependencies, including `ecFlow`_:

.. code-block:: shell

   # clone using HTTPS
   git clone https://github.com/ecmwf/pyflow.git
   # or, clone using an SSH key
   git clone git@github.com:ecmwf/pyflow.git

   cd pyflow
   conda env create -f environment.yml
   conda activate pyflow

To install **pyflow** in the Conda environment, simply use :code:`pip`

.. code-block:: shell

   pip install pyflow-workflow-generator


Install from Source
~~~~~~~~~~~~~~~~~~~

Follow the `ecFlow installation instructions`_ ensuring that the ecFlow Python interface is enabled (see :code:`ENABLE_PYTHON`).
After a successful build, perform the ecFlow installation step to place all binary artifacts into an instalation directory.
Considering :code:`$ECFLOW_DIR` is the installation directory, the ecFlow Python interface is available at
:code:`$ECFLOW_DIR/lib/python3.XX/site-packages/ecflow/`. 

Ensure the following environment variables are set, and install **pyflow**:

.. code-block:: shell

   export ECFLOW_DIR=/path/to/installation/directory/of/ecflow

   # clone using HTTPS
   git clone https://github.com/ecmwf/pyflow.git
   # or, clone using an SSH key
   git clone git@github.com:ecmwf/pyflow.git

   cd pyflow
   pip install .

.. _`ecFlow`: https://github.com/ecmwf/ecflow
.. _`Jupyter Notebook`: https://jupyter.org
.. _`ecFlow installation instructions`: https://ecflow.readthedocs.io/en/latest/install/build_from_source.html
