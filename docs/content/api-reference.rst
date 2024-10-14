API
===

Nodes
-----

Suite
~~~~~

.. autoclass:: pyflow.Suite
   :special-members: __init__


.. _Task:

Task
~~~~

.. autoclass:: pyflow.Task
   :special-members: __init__


.. _Family:

Family
~~~~~~

.. autoclass:: pyflow.Family
   :special-members: __init__


AnchorFamily
~~~~~~~~~~~~

.. autoclass:: pyflow.AnchorFamily
   :special-members: __init__


Attributes
----------

Variable
~~~~~~~~

.. _Variable:

.. autoclass:: pyflow.Variable

.. autoclass:: pyflow.Edit


GeneratedVariable
~~~~~~~~~~~~~~~~~

.. _GeneratedVariable:

.. autoclass:: pyflow.GeneratedVariable


.. _Trigger:

Trigger
~~~~~~~

.. autoclass:: pyflow.Trigger


.. _Event:

Event
~~~~~

.. autoclass:: pyflow.Event


.. _Complete:

Complete
~~~~~~~~

.. autoclass:: pyflow.Complete


.. _Late:

Late
~~~~

.. autoclass:: pyflow.Late


.. _Label:

Label
~~~~~

.. autoclass:: pyflow.attributes.Label


.. _Meter:

Meter
~~~~~

.. autoclass:: pyflow.Meter


.. _Defstatus:

Defstatus
~~~~~~~~~

.. autoclass:: pyflow.Defstatus

Aviso
~~~~~~~~~

.. autoclass:: pyflow.Aviso

Mirror
~~~~~~~~~

.. autoclass:: pyflow.Mirror


Time Dependencies
~~~~~~~~~~~~~~~~~

.. _Time:

.. autoclass:: pyflow.Time

.. _Cron:

.. autoclass:: pyflow.Cron

.. autoclass:: pyflow.Crons

.. _Date:

.. autoclass:: pyflow.Date

.. _Day:

.. autoclass:: pyflow.attributes.Day

.. _Today:

.. autoclass:: pyflow.attributes.Today


Repeat
~~~~~~

.. _RepeatDate:

.. autoclass:: pyflow.RepeatDate

.. autoclass:: pyflow.RepeatInteger

.. autoclass:: pyflow.RepeatEnumerated

.. autoclass:: pyflow.attributes.RepeatString

.. _RepeatDay:

.. autoclass:: pyflow.attributes.RepeatDay


Limit
~~~~~

.. _Limit:

.. autoclass:: pyflow.Limit

.. _InLimit:

.. autoclass:: pyflow.InLimit

.. autoclass:: pyflow.Inlimit


Manual
~~~~~~

.. autoclass:: pyflow.attributes.Manual


.. _Autocancel:

Autocancel
~~~~~~~~~~

.. autoclass:: pyflow.attributes.Autocancel


.. _Follow:

Follow
~~~~~~

.. autoclass:: pyflow.attributes.Follow


.. _Zombies:

Zombies
~~~~~~~

.. autoclass:: pyflow.attributes.Zombies


External
--------

.. _Extern:

.. autoclass:: pyflow.Extern

.. autoclass:: pyflow.ExternNode

.. autoclass:: pyflow.ExternTask

.. autoclass:: pyflow.ExternFamily

.. autoclass:: pyflow.ExternEvent

.. autoclass:: pyflow.ExternMeter

.. autoclass:: pyflow.ExternYMD


Deployment
----------

.. autoclass:: pyflow.Notebook

.. autoclass:: pyflow.DeployGitRepo


Hosts
-----

.. _`Host`:

.. autoclass:: pyflow.Host

.. autoclass:: pyflow.NullHost

.. autoclass:: pyflow.LocalHost

.. autoclass:: pyflow.SSHHost

.. autoclass:: pyflow.SLURMHost

.. autoclass:: pyflow.PBSHost


Scripts
-------

.. _Script:

.. autoclass:: pyflow.Script

.. autoclass:: pyflow.PythonScript

.. autoclass:: pyflow.FileScript

.. autoclass:: pyflow.TemplateScript

.. autoclass:: pyflow.TemplateFileScript


Resources
---------

.. autoclass:: pyflow.DataResource

.. autoclass:: pyflow.FileResource

.. autoclass:: pyflow.WebResource

.. autoclass:: pyflow.Resources

Miscellaneous
-------------

.. _State:

State
~~~~~

.. automodule:: pyflow.state


Helper Functions
~~~~~~~~~~~~~~~~

.. autofunction:: pyflow.ecflow_name

.. autofunction:: pyflow.all_complete

.. autofunction:: pyflow.sequence


Deferred
~~~~~~~~

.. autoclass:: pyflow.Deferred
