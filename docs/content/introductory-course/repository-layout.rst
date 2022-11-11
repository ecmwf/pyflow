Repository Layout
=================

Object-oriented suites imply a certain breakdown of suites into components. These classes should be placed into different files within a repository.

Sub components of suites should be placed in their own Python submodule.

We encourage maintaining configurations independently to the suite structure.

As an example, we have (part of) the filesystem layout for the MARS testing suites.

.. code:: none

   repo/
    ├─ configuration/
    │   ├─ marsdev.yaml
    │   ├─ fdb-server-dev.yaml
    │   └─ ...
    │
    ├─ server/
    │   ├─ deployment/
    │   │   ├─ scripts/
    │   │   │   ├─ configure.sh
    │   │   │   ├─ build.sh
    │   │   │   └─ ...
    │   │   ├─ __init__.py
    │   │   ├─ deployment_family.py
    │   │   ├─ config.py
    │   │   └─ ...
    │   │
    │   ├─ tests/
    │   │   ├─ fdb-tools/
    │   │   │   ├─ scripts/
    │   │   │   │   ├─ write/
    │   │   │   │   │   ├─ simple.sh
    │   │   │   │   │   ├─ masking.sh
    │   │   │   │   │   └─ ...
    │   │   │   │   └─ ...
    │   │   │   │
    │   │   │   ├─ __init__.py
    │   │   │   ├─ tools_family.py
    │   │   │   ├─ fdb_write.py
    │   │   │   ├─ fdb_wipe.py
    │   │   │   └─ ...
    │   │   └─ ...
    │   │
    │   ├─ __init__.py
    │   ├─ server_family.py
    │   └─ ...
    │
    ├─ client/
    │   └─ ...
    │
    ├─ mars_flow.py
    └─ ...
