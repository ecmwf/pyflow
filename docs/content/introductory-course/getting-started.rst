.. role:: magenta

Getting Started
===============

You can quickly get started with **pyflow** with a trivial example outlined below. Before you run it, make sure to setup your environment by following instructions in :doc:`/content/installation` chapter.

.. seealso::

   For more details about **ecFlow**, please check `ecFlow documentation`_.


Write Suite
-----------

Copy the following code into a new file called ``hello_pyflow.py``:

.. code-block:: python
   :class: copybutton

   import os
   from pwd import getpwuid

   import pyflow as pf


   scratchdir = os.path.join(os.path.abspath(''), 'scratch')
   filesdir = os.path.join(scratchdir, 'files')
   outdir = os.path.join(scratchdir, 'out')

   if not os.path.exists(filesdir):
       os.makedirs(filesdir, exist_ok=True)

   if not os.path.exists(outdir):
       os.makedirs(outdir, exist_ok=True)

   passwd = getpwuid(os.getuid())

   server_host = 'localhost'
   server_port = 1500+passwd.pw_uid

   with pf.Suite('hello_pyflow',
                 host=pf.LocalHost('localhost'),
                 files=filesdir,
                 home=outdir,
                 defstatus=pf.state.suspended) as s:
       pf.Label('greeting', '')
       t1 = pf.Task('t1', script='echo "I am on $(hostname) : $ECF_HOST"')
       t2 = pf.Task('t2', script='ecflow_client --alter=change label greeting "Hello, pyflow!" /hello_pyflow')
       t1 >> t2

   s.check_definition()
   print(s)

   s.deploy_suite()
   s.replace_on_server(server_host, server_port)


.. _`start-server`:

Start Server
------------

Before you can deploy suite, make sure to start a local **ecFlow** server, via command line:

.. code-block:: shell

   ecflow_start.sh


Make a note of your **ecFlow** server :magenta:`Port Number`, which will be shown by the command above. By default, this value is dynamic and will be set to ``1500 + UID``, where ``UID`` is your current user ID.


Deploy Suite
------------

To deploy the suite, simply run the Python script from the command line:

.. code-block:: shell

   python3 hello_pyflow.py


Run Suite
---------

You can run the suite from the **ecFlowUI** application. Either start it via system menu icon or via command line:

.. code-block:: shell

   ecflow_ui


If running for the first time, turn on the Administrator menu mode in **Tools > Preferences**:

.. figure:: /_static/images/ecflow-ui-administrator-menu-mode.png
   :alt: ecFlowUI Administrator Menu Mode

   ecFlowUI Administrator Menu Mode


Then, add the local server to the view via **Servers > Manage servers > Add server dialog**, taking care to substitute the :magenta:`Port Number` value, which was shown when you :ref:`started <start-server>` the **ecFlow** server:

.. figure:: /_static/images/ecflow-ui-add-server-dialog.png
   :alt: ecFlowUI Add Server Dialog

   ecFlowUI Add Server Dialog


To queue the deployed suite, right click on it in the tree and choose **Begin** from the context menu:

.. figure:: /_static/images/ecflow-ui-begin-suite.png
   :alt: ecFlowUI Begin Suite

   ecFlowUI Begin Suite


Finally, to resume the suite, right click on it and choose **Resume** from the context menu:

.. figure:: /_static/images/ecflow-ui-resume-suite.png
   :alt: ecFlowUI Resume Suite

   ecFlowUI Resume Suite


The suite should now run and you should see the nodes change colour depending on their state and label get updated. Note that you can refresh the server view at any time by clicking on appropriate toolbar button or via F5 keyboard shortcut.

.. figure:: /_static/images/ecflow-ui-complete-suite.png
   :alt: ecFlowUI Complete Suite

   ecFlowUI Complete Suite


Stop Server
-----------

After you finish, make sure to stop the local **ecFlow** server:

.. code-block:: shell

   ecflow_stop.sh


.. _`ecFlow documentation`: https://ecflow.readthedocs.io/
