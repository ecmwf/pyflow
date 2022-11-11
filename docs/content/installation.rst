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

For Conda environment, a definition file is provided in the repository root. It will create a suitable environment with all dependencies installed.

.. code-block:: shell

   git clone ssh://git@git.ecmwf.int/ecflow/pyflow.git
   cd pyflow
   conda env create -f environment.yml
   conda activate pyflow


ECMWF Environment Modules
~~~~~~~~~~~~~~~~~~~~~~~~~

On ECMWF systems, Environment Modules can be used to switch on relevant packages and make them available for use.

.. code-block:: shell

   module load python3 ecflow/5 pyflow


.. warning::

   Please make sure to also set the following environment variable, so **pyflow** library can be found:

   .. code-block:: shell

      export PYTHONPATH="$PYFLOW_DIR/lib/python3.6/site-packages:$PYTHONPATH"


.. todo::

   The need for ``PYTHONPATH`` variable should be handled in the next release of the module.


Install from Source
~~~~~~~~~~~~~~~~~~~

Follow `ecFlow installation instructions`_ and after all steps make sure to set following environment variable to correct paths.

.. code-block:: shell

   export ECFLOW_DIR=/path/to/ecflow
   git clone ssh://git@git.ecmwf.int/ecflow/pyflow.git
   cd pyflow
   pip3 install .


.. _`ecFlow`: https://github.com/ecmwf/ecflow
.. _`Jupyter Notebook`: https://jupyter.org
.. _`ecFlow installation instructions`: https://github.com/ecmwf/ecflow#install-from-source
