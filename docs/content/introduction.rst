Introduction
============

**pyflow** is a high-level language used to describe `ecFlow`_ suites. The aim is to build object-oriented suites that are designed and maintained as software.

**pyflow** acts both as a compiler and a library for **ecFlow** definition files that generate suites. Internally it wraps the **ecFlow** Python library, but does not require knowledge of its API.

.. seealso::

   For more details about **ecFlow**, please check `ecFlow documentation`_.


Benefits
--------

* Provides a higher level API
* Introduces common idioms, and provides helper functionality
* Encourages the use of certain work practices
* **pyflow** classes wrap **ecFlow** classes (e.g. ``pyflow.Family`` wraps ``ecflow.Family``)


Idiomatic Suites
----------------

The aim of **pyflow** is to build object-oriented suites, which compile to **ecFlow** output.

**ecFlow** suites involve the construction of three tree-structures:

   A graphical tree, visible to the user of the suite
      * Various properties are inherited through this tree

   A *Directed Graph* for execution
      * Not necessarily a *DAG*, as it may contain cycles
      * Partly coupled to the graphical tree

   An on-disk layout of scripts
      * Driven by **ecFlow** search rules

      .. note::

         The on-disk layout for scripts is constrained by **ecFlow** and is discussed in the section on :doc:`/content/introductory-course/script-handling`.

**pyflow** provides tools and practices to help manage the complexity of building these three trees simultaneously.


.. _`ecFlow`: https://github.com/ecmwf/ecflow
.. _`ecFlow documentation`: https://ecflow.readthedocs.io/
