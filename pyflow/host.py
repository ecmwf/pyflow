from __future__ import absolute_import

import getpass

# Code needed for all types of script to set the ecflow variables used later
import os
import pwd
import shutil
import textwrap

from .attributes import Label, Limit
from .base import STACK
from .nodes import DuplicateNodeError, Family, ecflow_name

SET_ECF_VARIABLES = """
export ECF_PORT=%ECF_PORT%    # The server port number
export ECF_HOST=%ECF_HOST%    # The host name where the server is running
export ECF_NAME=%ECF_NAME%    # The name of this current task
export ECF_PASS=%ECF_PASS%    # A unique password
export ECF_TRYNO=%ECF_TRYNO%  # Current try number of the task
"""

POSTAMBLE_SUBMITTED_JOBS = """
# -------------------------- ECFLOW STATUS FOR SUBMITTED JOBS ------------------------,

wait                      # wait for background process to stop
exit_hook                 # calling custom exit/cleaning code
trap 0                    # Remove all traps
ecflow_client --complete  # Notify ecFlow of a normal end
exit 0
"""


SSH_COMMAND = "ssh -v -o StrictHostKeyChecking=no"


class Host:
    """
    An abstract base class for host-related functionality.

    Parameters:
        name(str): The name of the host.
        hostname(str): The hostname of the host, otherwise `name` will be used.
        scratch_directory(str): The path in which tasks will be run, unless otherwise specified.
        log_directory(str): The directory to use for script output. Normally `ECF_HOME`, but may need to be changed on
            systems with scheduling systems to make the output visible to the **ecFlow** server.
        resources_directory(str): The directory to use for suite resources. By default, `scratch_directory` is used.
        limit(int): The number of tasks that can run on this node simultaneously. By default, there is no limit.
        extra_paths(list): The list of paths that are added to `PATH` on the host.
        extra_variables(dict): The dictionary of additional **ecFlow** variables that are set on the host.
        environment_variables(dict): The dictionary of additional environment variables that are included in scripts.
        module_source(str): The shell script to source to initialise the module system.
        modules(list): The list of environment modules to load via `module load` command.
        purge_models(bool): Whether to run the `module purge` command, before loading any environment modules.
        label_host(bool): Whether to create an `exec_host` label on nodes where this host is freshly set.
        user(str): The user running the script. May be used to determine paths, or for login details. Defaults to
            current user.
        ecflow_path(str): The directory containing the `ecflow_client` executable.
        server_ecfvars(bool): If true, don't define ECF_JOB_CMD, ECF_KILL_CMD, ECF_STATUS_CMD and ECF_OUT variables
            and use defaults from server
        submit_arguments(dict): A dictionary of arguments to pass to the scheduler when submitting jobs, which each key
            is a label that can be referenced when creating tasks with the `Host` instance.
        workdir(str): Work directory for every task executed within the `Host` instance, if not
            overriden for a Node.

    Example::

        class MyHost(Host):
            pass
    """

    def __init__(
        self,
        name,
        hostname=None,
        scratch_directory=None,
        log_directory=None,
        resources_directory=None,
        limit=None,
        extra_paths=None,
        extra_variables=None,
        environment_variables=None,
        module_source=None,
        modules=None,
        purge_modules=False,
        label_host=True,
        user=getpass.getuser(),
        ecflow_path=None,
        server_ecfvars=False,
        submit_arguments=None,
        workdir=None,
    ):
        self.name = name
        self.hostname = hostname or name
        self.user = user

        # We can extend the extra preamble if required later.
        self.extra_preamble = []
        self.extra_paths = extra_paths or []

        # A host can be configured to require additional ecflow variables
        self.extra_variables = extra_variables or {}
        self.environment_variables = environment_variables or {}

        # Directories
        self.scratch_directory = scratch_directory
        self.resources_directory = resources_directory
        self.log_directory = log_directory or "%ECF_HOME%"

        # Control for modules in preamble
        self.module_source = module_source
        self.modules = modules or []
        self.purge_modules = purge_modules
        self.workdir = workdir

        # Limit cannot be build before tree starts being constructed

        self._limit_count = limit
        self._limit = None

        self._label_host = label_host
        if ecflow_path is None:
            ecflow_path = os.path.dirname(shutil.which("ecflow_client"))
        self.ecflow_path = ecflow_path

        self.server_ecfvars = server_ecfvars

        self.submit_arguments = submit_arguments or {}

    def __str__(self):
        return "{}({})".format(self.__class__.__name__, self.hostname)

    def __repr__(self):
        return str(self)

    @property
    def ecflow_variables(self):
        """*dict*: The variables that must be set on relevant nodes to run on this host."""
        if self.server_ecfvars:
            vars = {}
        else:
            vars = {
                "ECF_JOB_CMD": self.job_cmd,
                "ECF_KILL_CMD": self.kill_cmd,
                "ECF_STATUS_CMD": self.status_cmd,
                "ECF_CHECK_CMD": self.check_cmd,
                "ECF_OUT": self.log_directory,
            }
        vars.update(self.extra_variables)
        return vars

    @property
    def job_cmd(self):
        """
        ecflow submission command. Sets ECF_JOB_CMD

        :meta private:
        """

        raise NotImplementedError

    @property
    def kill_cmd(self):
        """
        ecflow kill command. Sets ECF_KILL_CMD

        :meta private:
        """

        raise NotImplementedError

    @property
    def status_cmd(self):
        """*str*: The **ecflow** status command."""
        return "true"

    @property
    def check_cmd(self):
        """*str*: The **ecflow** check command."""
        return "true"

    def run_simple_command(self, cmd):
        raise NotImplementedError

    def preamble(self, exit_hook=None):
        """*list*: The host-specific preamble script for jobs."""
        preamble = SET_ECF_VARIABLES.split("\n")
        if self.extra_paths:
            preamble.append("export PATH=%s:${PATH}" % (":".join(self.extra_paths),))
        for var, val in self.environment_variables.items():
            preamble.append('export {}="{}"'.format(var, val))

        specific_preamble = self.host_preamble(exit_hook)
        if specific_preamble:
            preamble += specific_preamble
        if self.extra_preamble:
            preamble.append("")
            preamble += self.extra_preamble
        return preamble

    def host_preamble(self, exit_hook=None):
        """*list*: The host-specific implementation of preamble script, always empty."""
        return []

    @property
    def host_postamble(self):
        """*list*: The host-specific cleanup script, always empty."""
        return []

    @property
    def limit(self):
        """*int*: The number of tasks that can run on this host simultaneously."""
        return self._limit_count

    def copy_file_to(self, source_file, target_file):
        raise NotImplementedError

    def add_to_limits(self, task):
        """
        Adds a task to be contained within a hosts assigned limit.

        Parameters:
            task(Task_): The task to contain within the assigned limit.
        """
        if self._limit_count is not None and self._limit is not None:
            assert isinstance(self._limit, Limit)
            task.inlimits += self._limit

    def build_limits(self, replace=False):
        """
        Sets the number of tasks that can run on this host simultaneously, if configured.

        Parameters:
            replace(bool): Whether to replace the currently computed limit.

        Raises:
            DuplicateNodeError
        """
        if not replace:
            assert self._limit is None
        try:
            if self._limit_count is not None:
                self._limit = Limit(ecflow_name(self.name), self._limit_count)
        except DuplicateNodeError:
            family = STACK[-1]
            assert isinstance(family, Family)
            self._limit = getattr(family, ecflow_name(self.name))
            assert isinstance(family, Family)

    def build_label(self):
        """
        Sets an `exec_host` label on nodes where this host is freshly set, if configured.
        """
        if self._label_host:
            return Label("exec_host", self.hostname)

    def script_submit_arguments(self, submit_arguments):
        if len(submit_arguments) > 0:
            print(
                f"Host {self.__class__.__name__} does not support scheduler submission arguments. \
                    Submission arguments will be ignored in the script generation",
            )
        return []

    def get_host_submit_arguments(self, label: str):
        """
        Returns the submit arguments for the given label.

        Parameters:
            label(str): The label to get the submit arguments for.

        Returns:
            *dict*: The submit arguments for the given label.
        """
        try:
            return self.submit_arguments[label]
        except KeyError:
            raise KeyError(
                f"Label {label} not found in submit arguments for host {self.name}"
            )

    def preamble_init(self, ecflowpath):
        """
        Returns the host-specific preamble initialisation section for jobs.

        Parameters:
            ecflowpath(str): The path to **ecFlow**.

        Returns:
            *str*: The preamble initialisation script.
        """

        script = (
            textwrap.dedent(
                """
        # ----------------------------- ECFLOW INIT ----------------------------

        export PATH=%(ecf_path)s:$PATH

        export ECF_RID=$$  # record the process id. Also used for zombie detection

        # Tell ecFlow we have started
        ecflow_client --init=$$
        """
            )
            % {"ecf_path": ecflowpath}
        )

        return script

    def preamble_error_function(self, ecflowpath, exit_hook=None):
        """
        Returns the host-specific error function for jobs.

        Parameters:
            ecflowpath(str): The path to **ecFlow**.
            additional_commands(tuple): The list of additional commands to include in the function.

        Returns:
            *str*: The error function script.
        """
        script = ""

        script += textwrap.dedent(
            """
            # custom exit/cleanup code
            exit_hook () {
                echo "cleaning up ...."
            """
        )
        if exit_hook:
            for line in exit_hook:
                script += f"    {line}\n"
        script += "}\n\n"

        script += textwrap.dedent(
            (
                """
            # ----------------------------- TRAPS FOR SUBMITTED JOBS ----------------------------
            set +x
            # Define a error handler
            ERROR() {
                export PATH=%(ecf_path)s:$PATH
                set +eu  # Clear -eu flag, so we don't fail
                wait  # wait for background process to stop
                exit_hook  # calling custom exit/cleaning code
                ecflow_client --abort=trap  # Notify ecFlow that something went wrong, using 'trap' as the reason
                trap - 0 $SIGNAL_LIST  # Remove the traps
                echo "The environment was:"
                printenv | sort
                # End the script
                exit 1
            }

            # Trap any signal that may cause the script to fail
            # Note: don't trap SIGTERM/SIGCONT for Slurm to properly reach shell children on cancel/timeout
            export SIGNAL_LIST='1 2 3 4 5 6 7 8 10 11 13 24 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64'

            for signal in $SIGNAL_LIST; do
                trap "ERROR $signal \\"Signal $(kill -l $signal) ($signal) received \\"" $signal
            done

            # Trap any calls to exit and errors caught by the -e flag
            trap ERROR 0
            set -x
            """  # noqa: E501
            )
            % {"ecf_path": ecflowpath}
        )
        return script

    def job_preamble(self, exit_hook=None):
        """*list*: The host-specific preamble for jobs."""
        return self.preamble_init(self.ecflow_path).split(
            "\n"
        ) + self.preamble_error_function(self.ecflow_path, exit_hook).split("\n")


class NullHost(Host):
    """
    A dummy host object invisible to **ecFlow**, but still throws exceptions if **pyflow** attempts to create tasks
    inside it.

    Parameters:
        hostname(str): The hostname of the host, otherwise `null` will be used.
        scratch_directory(str): The path in which tasks will be run, unless otherwise specified.
        log_directory(str): The directory to use for script output. Normally `ECF_HOME`, but may need to be changed on
            systems with scheduling systems to make the output visible to the **ecFlow** server.
        resources_directory(str): The directory to use for suite resources. By default, `scratch_directory` is used.
        limit(int): The number of tasks that can run on this node simultaneously. By default, there is no limit.
        extra_paths(list): The list of paths that are added to `PATH` on the host.
        extra_variables(dict): The dictionary of additional **ecFlow** variables that are set on the host.
        environment_variables(dict): The dictionary of additional environment variables that are included in scripts.
        module_source(str): The shell script to source to initialise the module system.
        modules(list): The list of environment modules to load via `module load` command.
        purge_models(bool): Whether to run the `module purge` command, before loading any environment modules.
        label_host(bool): Whether to create an `exec_host` label on nodes where this host is freshly set.
        user(str): The user running the script. May be used to determine paths. Defaults to current user.
        ecflow_path(str): The directory containing the `ecflow_client` executable.
        server_ecfvars(bool): If true, don't define ECF_JOB_CMD, ECF_KILL_CMD, ECF_STATUS_CMD and ECF_OUT variables
            and use defaults from server

    Example::

        with pyflow.Suite('s', host=pf.NullHost()):
            pass
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("limit", None)
        super().__init__("null", **kwargs)

    @property
    def ecflow_variables(self):
        """*dict*: The variables that must be set on relevant nodes to run on this host, always empty."""
        return {}

    def host_preamble(self, exit_hook=None):
        """
        The host-specific implementation of preamble script, always raises an error.

        Raises:
            AttributeError: Constructing tasks under `NullHost` is invalid.
        """

        raise AttributeError("Constructing Tasks under NullHost is invalid")

    @property
    def host_postamble(self):
        """
        The host-specific implementation of cleanup script, always raises an error.

        Raises:
            AttributeError: Constructing tasks under `NullHost` is invalid.
        """

        raise AttributeError("Constructing Tasks under NullHost is invalid")

    def build_label(self):
        """Skips setting an `exec_host` label on nodes where this host is freshly set."""
        return None


class LocalHost(Host):
    """
    A host object that executes scripts directly on the **ecFlow** server.

    Parameters:
        name(str): The name of the host, `localhost` by default.
        hostname(str): The hostname of the host, otherwise `name` will be used.
        scratch_directory(str): The path in which tasks will be run, unless otherwise specified.
        log_directory(str): The directory to use for script output. Normally `ECF_HOME`, but may need to be changed on
            systems with scheduling systems to make the output visible to the **ecFlow** server.
        resources_directory(str): The directory to use for suite resources. By default, `scratch_directory` is used.
        limit(int): The number of tasks that can run on this node simultaneously. By default, the limit is 20 tasks.
        extra_paths(list): The list of paths that are added to `PATH` on the host.
        extra_variables(dict): The dictionary of additional **ecFlow** variables that are set on the host.
        environment_variables(dict): The dictionary of additional environment variables that are included in scripts.
        module_source(str): The shell script to source to initialise the module system.
        modules(list): The list of environment modules to load via `module load` command.
        purge_models(bool): Whether to run the `module purge` command, before loading any environment modules.
        label_host(bool): Whether to create an `exec_host` label on nodes where this host is freshly set.
        user(str): The user running the script. May be used to determine paths. Defaults to current user.
        ecflow_path(str): The directory containing the `ecflow_client` executable.
        server_ecfvars(bool): If true, don't define ECF_JOB_CMD, ECF_KILL_CMD, ECF_STATUS_CMD and ECF_OUT variables
            and use defaults from server

    Example::

        pyflow.LocalHost(purge_modules=True, modules=['mod1/123', '-mod2/321', 'mod3/33'])
    """

    def __init__(self, name="localhost", **kwargs):
        """Very much the same as the EcflowDefaultHost, but has **pyflow** rather than **ecFlow** behaviour."""
        kwargs.setdefault("limit", 20)
        super().__init__(name, **kwargs)

    @property
    def job_cmd(self):
        """*str*: The **ecFlow** submission command, sets the `ECF_JOB_CMD` variable."""

        # 1. Use bash -c to ensure that we get a
        return (
            "bash -c '"
            + "export ECF_PORT=%ECF_PORT%; "
            + "export ECF_HOST=%ECF_HOST%; "
            + "export ECF_NAME=%ECF_NAME%; "
            + "export ECF_PASS=%ECF_PASS%; "
            + "export ECF_TRYNO=%ECF_TRYNO%; "
            + "export PATH={}:$PATH; ".format(self.ecflow_path)
            + 'ecflow_client --init="$$" && '
            + "%ECF_JOB% "
            + "&& ecflow_client --complete "
            + "|| ecflow_client --abort "
            + "' 1> %ECF_JOBOUT% 2>&1 &"
        )
        # return ("export ECF_PORT=%ECF_PORT%; " +
        #        "export ECF_HOST=%ECF_HOST%; " +
        #        "export ECF_NAME=%ECF_NAME%; " +
        #        "export ECF_PASS=%ECF_PASS%; " +
        #        "export ECF_TRYNO=%ECF_TRYNO%; " +
        #        "(" +
        #        "%ECF_JOB% 1> %ECF_JOBOUT% 2>&1" +
        #        "&& ecflow_client --complete" +
        #        "|| ecflow_client --abort" +
        #        ") & ecflow_client --init=$!")

    @property
    def kill_cmd(self):
        """*str*: The **ecflow** kill command, sets the `ECF_KILL_CMD` variable."""
        return "pkill -15 -P %ECF_RID%"

    @property
    def host_postamble(self):
        """*list*: The host-specific cleanup script, always empty."""
        return []

    def run_simple_command(self, cmd):
        """
        Returns the command to run a simple command on this host.

        Parameters:
            cmd(str): A simple command to run.

        Returns:
            *str*: The command to run a simple command.
        """
        return cmd

    def copy_file_to(self, source_file, target_file):
        """
        Returns the script for copying a file to host.

        Parameters:
            source_file(str): The source file to copy from.
            target_file(str): The target file to copy to.

        Returns:
            *str*: The script for copying a file to host.
        """

        return textwrap.dedent(
            """
            mkdir -p "{}"
            cp "{}" "{}"
        """.format(
                os.path.dirname(os.path.abspath(target_file)),
                source_file,
                target_file,
            )
        )


class EcflowDefaultHost(LocalHost):
    """
    By default we just use LocalHost... Slightly modified from ecflow default of

        return "%ECF_JOB% 1> %ECF_JOBOUT% 2>&1"
        return "kill -15 %ECF_RID%"
    """

    def __init__(self, **kwargs):
        super().__init__("default", **kwargs)


class SSHHost(Host):
    """
    A host object that executes scripts on the **ecFlow** server via SSH protocol.

    Parameters:
        name(str): The name of the host.
        user(str): The user to use for SSH commands to the host. Defaults to current user.
        indirect_host(str): The name of the host to use indirectly. May be in `user@server` format.
        indirect_user(str): The user to use for SSH commands on the indirect host.
        hostname(str): The hostname of the host, otherwise `name` will be used.
        scratch_directory(str): The path in which tasks will be run, unless otherwise specified.
        log_directory(str): The directory to use for script output. Normally `ECF_HOME`, but may need to be changed on
            systems with scheduling systems to make the output visible to the **ecFlow** server.
        resources_directory(str): The directory to use for suite resources. By default, `scratch_directory` is used.
        limit(int): The number of tasks that can run on this node simultaneously. By default, the limit is 20 tasks.
        extra_paths(list): The list of paths that are added to `PATH` on the host.
        extra_variables(dict): The dictionary of additional **ecFlow** variables that are set on the host.
        environment_variables(dict): The dictionary of additional environment variables that are included in scripts.
        module_source(str): The shell script to source to initialise the module system.
        modules(list): The list of environment modules to load via `module load` command.
        purge_models(bool): Whether to run the `module purge` command, before loading any environment modules.
        label_host(bool): Whether to create an `exec_host` label on nodes where this host is freshly set.
        ecflow_path(str): The directory containing the `ecflow_client` executable.
        server_ecfvars(bool): If true, don't define ECF_JOB_CMD, ECF_KILL_CMD, ECF_STATUS_CMD and ECF_OUT variables
            and use defaults from server

    Example::

        pyflow.SSHHost('dhs9999', user='max', scratch_directory='/data/a_mounted_filesystem/tmp')
    """

    def __init__(
        self, name, user=None, indirect_host=None, indirect_user=None, **kwargs
    ):
        if user is None:
            try:
                user, name = name.split("@")
            except ValueError:
                user = getpass.getuser()

        if indirect_host is not None and indirect_user is None:
            try:
                indirect_user, indirect_host = indirect_host.split("@")
            except ValueError:
                indirect_user = user

        super().__init__(name, user=user, **kwargs)

        self.indirect_host = indirect_host
        self.indirect_user = indirect_user

    @property
    def job_cmd(self):
        """*str*: The **ecFlow** submission command, sets the `ECF_JOB_CMD` variable."""
        """
        Run the command remotely. Additional choices to consider:
           > bash -l  --- runs bash as a login shell (sources things)
           > bash --noprofile
        ... exactly which version of bash is used could be configurable.
        """
        # return "ssh {}@{} bash -l -s < %ECF_JOB% > %ECF_JOBOUT% 2>&1".format(self.user, self.hostname)
        #     repr(self.user) if isinstance(self),
        #     repr(self.hostname))
        # return ("export ECF_PORT=%ECF_PORT%; " +
        #        "export ECF_HOST=%ECF_HOST%; " +
        #        "export ECF_NAME=%ECF_NAME%; " +
        #        "export ECF_PASS=%ECF_PASS%; " +
        #        "export ECF_TRYNO=%ECF_TRYNO%; " +
        #        "(" +
        #        "{} {}@{} bash -s < %ECF_JOB% > %ECF_JOBOUT% 2>&1".format(
        #            SSH_COMMAND, self.user, self.hostname) +
        #        "&& ecflow_client --complete" +
        #        "|| ecflow_client --abort" +
        #        ") & ecflow_client --init=$!")

        if self.indirect_host is not None:
            assert self.indirect_user is not None
            return (
                "bash -c '"
                + "export ECF_PORT=%ECF_PORT%; "
                + "export ECF_HOST=%ECF_HOST%; "
                + "export ECF_NAME=%ECF_NAME%; "
                + "export ECF_PASS=%ECF_PASS%; "
                + "export ECF_TRYNO=%ECF_TRYNO%; "
                + "export PATH={}:$PATH; ".format(self.ecflow_path)
                + 'ecflow_client --init="$$" && '
                + "{} {}@{} {} {}@{} bash -s < %ECF_JOB%".format(
                    SSH_COMMAND,
                    self.indirect_user,
                    self.indirect_host,
                    SSH_COMMAND,
                    self.user,
                    self.hostname,
                )
                + "&& ecflow_client --complete "
                + "|| ecflow_client --abort "
                + "' 1> %ECF_JOBOUT% 2>&1 &"
            )
        else:
            return (
                "bash -c '"
                + "export ECF_PORT=%ECF_PORT%; "
                + "export ECF_HOST=%ECF_HOST%; "
                + "export ECF_NAME=%ECF_NAME%; "
                + "export ECF_PASS=%ECF_PASS%; "
                + "export ECF_TRYNO=%ECF_TRYNO%; "
                + "export PATH={}:$PATH; ".format(self.ecflow_path)
                + 'ecflow_client --init="$$" && '
                + "{} {}@{} bash -s < %ECF_JOB%".format(
                    SSH_COMMAND, self.user, self.hostname
                )
                + "&& ecflow_client --complete "
                + "|| ecflow_client --abort "
                + "' 1> %ECF_JOBOUT% 2>&1 &"
            )

    def run_simple_command(self, cmd):
        """
        Returns the command to run a simple command on this host.

        Parameters:
            cmd(str): A simple command to run.

        Returns:
            *str*: The command to run a simple command.
        """

        if self.indirect_host is not None:
            return "ssh -o StrictHostKeyChecking=no {}@{} ssh -o StrictHostKeyChecking=no {}@{} {}".format(
                self.indirect_user,
                self.indirect_host,
                self.user,
                self.hostname,
                cmd,
            )
        else:
            return "ssh -o StrictHostKeyChecking=no {}@{} {}".format(
                self.user, self.hostname, cmd
            )

    @property
    def kill_cmd(self):
        """*str*: The **ecflow** kill command, sets the `ECF_KILL_CMD` variable."""
        return "pkill -15 -P %ECF_RID%"

    def copy_file_to(self, source_file, target_file):
        """
        Returns the script for copying a file to host.

        Parameters:
            source_file(str): The source file to copy from.
            target_file(str): The target file to copy to.

        Returns:
            *str*: The script for copying a file to host.
        """

        # n.b. --rsync-path specifies the rsync command to run on the remote machine.
        #      By inserting mkdir -p there, we can ensure that the target directory exists
        return 'rsync -e "{}" --archive --verbose --rsync-path="mkdir -p {} && rsync" "{}" {}@{}:{}'.format(
            SSH_COMMAND,
            os.path.dirname(os.path.abspath(target_file)),
            source_file,
            self.user,
            self.hostname,
            target_file,
        )

    @property
    def host_postamble(self):
        """*list*: The host-specific cleanup script, always empty."""
        return []


class SimpleSSHHost(Host):
    def __init__(self, host):
        super().__init__(host)
        self.host = host

    @property
    def job_cmd(self):
        return (
            SSH_COMMAND
            + " "
            + self.host
            + " /bin/bash -s < %ECF_JOB% > %ECF_JOBOUT% 2>&1&"
        )

    @property
    def kill_cmd(self):
        return (
            SSH_COMMAND
            + " "
            + self.host
            + " kill %ECF_RID% >> %ECF_JOBOUT% 2>&1 < /dev/null&"
        )

    def run_simple_command(self, cmd):
        return "ssh {} {}".format(self.host, cmd)

    def host_preamble(self, exit_hook=None):
        return self.job_preamble(exit_hook)

    @property
    def host_postamble(self):
        return POSTAMBLE_SUBMITTED_JOBS.split("\n")


class SLURMHost(SSHHost):
    """
    A host object that executes scripts on the **ecFlow** server via Slurm job scheduling system.

    Parameters:
        name(str): The name of the host.
        user(str): The user to use for SSH commands to the host. Defaults to current user.
        indirect_host(str): The name of the host to use indirectly. May be in `user@server` format.
        indirect_user(str): The user to use for SSH commands on the indirect host.
        hostname(str): The hostname of the host, otherwise `name` will be used.
        scratch_directory(str): The path in which tasks will be run, unless otherwise specified.
        log_directory(str): The directory to use for script output. Normally `ECF_HOME`, but may need to be changed on
            systems with scheduling systems to make the output visible to the **ecFlow** server.
        resources_directory(str): The directory to use for suite resources. By default, `scratch_directory` is used.
        limit(int): The number of tasks that can run on this node simultaneously. By default, there is no limit.
        extra_paths(list): The list of paths that are added to `PATH` on the host.
        extra_variables(dict): The dictionary of additional **ecFlow** variables that are set on the host.
        environment_variables(dict): The dictionary of additional environment variables that are included in scripts.
        module_source(str): The shell script to source to initialise the module system.
        modules(list): The list of environment modules to load via `module load` command.
        purge_models(bool): Whether to run the `module purge` command, before loading any environment modules.
        label_host(bool): Whether to create an `exec_host` label on nodes where this host is freshly set.
        ecflow_path(str): The directory containing the `ecflow_client` executable.
        server_ecfvars(bool): If true, don't define ECF_JOB_CMD, ECF_KILL_CMD, ECF_STATUS_CMD and ECF_OUT variables
            and use defaults from server

    Example::

        with pyflow.Suite('s', host=pyflow.SLURMHost('slurm_a')):
            pass
    """

    def __init__(self, name, **kwargs):
        passwd = pwd.getpwuid(os.getuid())
        username = passwd.pw_name

        kwargs.setdefault("user", username)

        super().__init__(name, **kwargs)

    def script_submit_arguments(self, submit_arguments):
        """
        Returns list of script submit arguments.

        Parameters:
            submit_arguments(dict): A dictionary of script submit arguments.

        Returns:
            *list*: The list of script submit arguments.
        """
        if isinstance(submit_arguments, str):
            submit_arguments = self.get_host_submit_arguments(submit_arguments)
        args = []
        for key, value in submit_arguments.items():
            args.append("#SBATCH --{}={}".format(key, value))
        return args

    @property
    def job_cmd(self):
        """*str*: The **ecFlow** submission command, sets the `ECF_JOB_CMD` variable."""
        return (
            "mkdir -p $(dirname %ECF_JOBOUT%); "
            + 'cp %ECF_JOB% "%ECF_JOBOUT%.jobfile"; '
            + '{} {}@{} "sh -l -c \'sbatch -o "%ECF_JOBOUT%" "%ECF_JOBOUT%.jobfile" /> "%ECF_JOBOUT%.jobfile.sub"\'"'.format(  # noqa: E501
                SSH_COMMAND, self.user, self.hostname
            )
        )

    @property
    def kill_cmd(self):
        """*str*: The **ecflow** kill command, sets the `ECF_KILL_CMD` variable."""
        return (
            "export ECF_PORT=%ECF_PORT%; "
            + "export ECF_HOST=%ECF_HOST%; "
            + "export ECF_NAME=%ECF_NAME%; "
            + "export ECF_PASS=%ECF_PASS%; "
            + "export ECF_TRYNO=%ECF_TRYNO%; "
            + (
                "{} {}@{} \"sh -l -c 'scancel \"\\$(grep Submitted '%ECF_JOBOUT%.jobfile.sub'"
                " | cut -d' ' -f4)\"'\""
            ).format(SSH_COMMAND, self.user, self.hostname)
            + " && ecflow_client --abort"
        )

    def host_preamble(self, exit_hook=None):
        """*list*: The host-specific implementation of preamble script."""
        return self.job_preamble(exit_hook)

    @property
    def host_postamble(self):
        """*list*: The host-specific cleanup script."""
        return POSTAMBLE_SUBMITTED_JOBS.split("\n")


class PBSHost(SSHHost):
    """
    A host object that executes scripts on the **ecFlow** server via batch server.

    Parameters:
        name(str): The name of the host.
        user(str): The user to use for SSH commands to the host. Defaults to current user.
        indirect_host(str): The name of the host to use indirectly. May be in `user@server` format.
        indirect_user(str): The user to use for SSH commands on the indirect host.
        hostname(str): The hostname of the host, otherwise `name` will be used.
        scratch_directory(str): The path in which tasks will be run, unless otherwise specified.
        log_directory(str): The directory to use for script output. Normally `ECF_HOME`, but may need to be changed on
            systems with scheduling systems to make the output visible to the **ecFlow** server.
        resources_directory(str): The directory to use for suite resources. By default, `scratch_directory` is used.
        limit(int): The number of tasks that can run on this node simultaneously. By default, there is no limit.
        extra_paths(list): The list of paths that are added to `PATH` on the host.
        extra_variables(dict): The dictionary of additional **ecFlow** variables that are set on the host.
        environment_variables(dict): The dictionary of additional environment variables that are included in scripts.
        module_source(str): The shell script to source to initialise the module system.
        modules(list): The list of environment modules to load via `module load` command.
        purge_models(bool): Whether to run the `module purge` command, before loading any environment modules.
        label_host(bool): Whether to create an `exec_host` label on nodes where this host is freshly set.
        ecflow_path(str): The directory containing the `ecflow_client` executable.
        server_ecfvars(bool): If true, don't define ECF_JOB_CMD, ECF_KILL_CMD, ECF_STATUS_CMD and ECF_OUT variables
            and use defaults from server

    Example::

        with pyflow.Suite('s', host=pyflow.PBSHost('host_a')):
            pass
    """

    def __init__(self, name, **kwargs):
        passwd = pwd.getpwuid(os.getuid())
        username = passwd.pw_name

        kwargs.setdefault("user", kwargs.get("user", username))

        super().__init__(name, **kwargs)

    @property
    def job_cmd(self):
        """*str*: The **ecFlow** submission command, sets the `ECF_JOB_CMD` variable."""
        return (
            "{} {}@{} '".format(SSH_COMMAND, self.user, self.hostname)
            + "mkdir -p $(dirname %ECF_JOBOUT%) ; "
            + "cat - > %ECF_JOBOUT%.jobfile ; "
            + 'qsub "%ECF_JOBOUT%.jobfile" 2>&1 | tee "%ECF_JOBOUT%.jobfile.sub"\' < %ECF_JOB% '
        )

    @property
    def kill_cmd(self):
        """*str*: The **ecflow** kill command, sets the `ECF_KILL_CMD` variable."""
        return (
            "export ECF_PORT=%ECF_PORT%; "
            + "export ECF_HOST=%ECF_HOST%; "
            + "export ECF_NAME=%ECF_NAME%; "
            + "export ECF_PASS=%ECF_PASS%; "
            + "export ECF_TRYNO=%ECF_TRYNO%; "
            + "{} {}@{} qdel \"\\$(cat '%ECF_JOBOUT%.jobfile.sub')\"".format(
                SSH_COMMAND, self.user, self.hostname
            )
            + " && ecflow_client --abort"
        )

    def script_submit_arguments(self, submit_arguments):
        """
        Returns list of script submit arguments.

        Parameters:
            submit_arguments(dict): A dictionary of script submit arguments.

        Returns:
            *list*: The list of script submit arguments.
        """

        if isinstance(submit_arguments, str):
            submit_arguments = self.get_host_submit_arguments(submit_arguments)
        args = []
        for key, value in submit_arguments.items():
            args.append("#PBS -l {}={}".format(key, value))

        return args

    def host_preamble(self, exit_hook=None):
        """*list*: The host-specific implementation of preamble script."""
        return self.job_preamble(exit_hook)

    @property
    def host_postamble(self):
        """*list*: The host-specific cleanup script."""
        return POSTAMBLE_SUBMITTED_JOBS.split("\n")


class TroikaHost(Host):
    """
    A host object that executes scripts on the **ecFlow** server via the troika job submitter.

    Parameters:
        name(str): The name of the host.
        user(str): The user to use for troika commands to the host.
        hostname(str): The hostname of the host, otherwise `name` will be used.
        scratch_directory(str): The path in which tasks will be run, unless otherwise specified.
        log_directory(str): The directory to use for script output. Normally `ECF_HOME`, but may need to be changed on
            systems with scheduling systems to make the output visible to the **ecFlow** server.
        resources_directory(str): The directory to use for suite resources. By default, `scratch_directory` is used.
        limit(int): The number of tasks that can run on this node simultaneously. By default, there is no limit.
        extra_paths(list): The list of paths that are added to `PATH` on the host.
        extra_variables(dict): The dictionary of additional **ecFlow** variables that are set on the host.
        environment_variables(dict): The dictionary of additional environment variables that are included in scripts.
        module_source(str): The shell script to source to initialise the module system.
        modules(list): The list of environment modules to load via `module load` command.
        purge_models(bool): Whether to run the `module purge` command, before loading any environment modules.
        label_host(bool): Whether to create an `exec_host` label on nodes where this host is freshly set.
        ecflow_path(str): The directory containing the `ecflow_client` executable.
        server_ecfvars(bool): If true, don't define ECF_JOB_CMD, ECF_KILL_CMD, ECF_STATUS_CMD and ECF_OUT variables
            and use defaults from server

    Example::

        with pyflow.Suite('s', host=pyflow.TroikaHost('host_a', user='emos')):
            pass
    """

    def __init__(self, name, user, **kwargs):
        self.troika_exec = kwargs.pop("troika_exec", "troika")
        self.troika_config = kwargs.pop("troika_config", "")
        self.troika_version = tuple(
            map(int, kwargs.pop("troika_version", "0.2.1").split("."))
        )
        super().__init__(name, user=user, **kwargs)

    def troika_command(self, command):
        cmd = " ".join(
            [
                f"%TROIKA:{self.troika_exec}%",
                "-vv",
                (
                    f"-c %TROIKA_CONFIG:{self.troika_config}%"
                    if self.troika_config
                    else ""
                ),
                f"{command}",
                f"-u {self.user}",
            ]
        )
        return cmd

    @property
    def job_cmd(self):
        """*str*: The **ecFlow** submission command, sets the `ECF_JOB_CMD` variable."""
        return self.troika_command("submit") + " -o %ECF_JOBOUT% {} %ECF_JOB%".format(
            self.hostname
        )

    @property
    def kill_cmd(self):
        """*str*: The **ecflow** kill command, sets the `ECF_KILL_CMD` variable."""
        return self.troika_command("kill") + " {} %ECF_JOB%".format(self.hostname)

    @property
    def status_cmd(self):
        """*str*: The **ecflow** status command."""
        return self.troika_command("monitor") + " {} %ECF_JOB%".format(self.hostname)

    @property
    def check_cmd(self):
        """*str*: The **ecflow** check command."""
        return self.troika_command("check") + " {} %ECF_JOB%".format(self.hostname)

    def host_preamble(self, exit_hook=None):
        return self.job_preamble(exit_hook)

    @property
    def host_postamble(self):
        return POSTAMBLE_SUBMITTED_JOBS.split("\n")

    def script_submit_arguments(self, submit_arguments):
        """
        Returns list of script submit arguments.

        Parameters:
            submit_arguments(dict): A dictionary of script submit arguments.

        Returns:
            *list*: The list of script submit arguments.
        """

        """
        Accepted submit arguments:
        """

        deprecated = {
            "tasks": "total_tasks",
            "nodes": "total_nodes",
            "threads_per_task": "cpus_per_task",
            "hyperthreads": "threads_per_core",
            "memory_per_task": "memory_per_cpu",
            "accounting": "billing_account",
            "working_dir": "working_dir",
            "tmpdir": "tmpdir_size",
            "export": "export_vars",
        }

        slurm_resources = {
            "hint": " --hint=",
        }

        if self.troika_version < (0, 2, 2):
            slurm_resources.update(
                {
                    "distribution": "--distribution=",
                    "reservation": "--reservation=",
                }
            )

        def _translate_hint(val):
            if val == "multithread":
                return "enable_hyperthreading", "yes"
            elif val == "nomultithread":
                return "enable_hyperthreading", "no"
            else:
                return "hint", val

        def _translate_sthost(val):
            return "export_vars", f"STHOST={val}"

        special = {
            "hint": _translate_hint,
            "sthost": _translate_sthost,
        }

        if isinstance(submit_arguments, str):
            submit_arguments = self.get_host_submit_arguments(submit_arguments)
        args = []
        for arg, val in submit_arguments.items():
            if arg in special:
                arg, val = special[arg](val)

            if arg in slurm_resources:
                resource = slurm_resources[arg]
                if resource is not None:
                    args.append("#SBATCH {}{}".format(resource, val))
            elif arg == "RAW_PRAGMA":
                for pragma in val:
                    args.append(pragma)
            else:
                if arg in deprecated:
                    print(
                        f"WARNING! '{arg}' is deprecated, use '{deprecated[arg]}' instead"
                    )
                    arg = deprecated[arg]
                if arg is not None:
                    args.append("#TROIKA {}={}".format(arg, val))

        return args
