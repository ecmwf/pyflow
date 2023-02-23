from __future__ import print_function

import hashlib
import os
import subprocess

from pyflow.html import FileListHTMLWrapper


class DeploymentError(RuntimeError):
    pass


class Deployment:
    def __init__(self, suite, headers=True, overwrite=False):
        """
        Base class for all deployments.

        Parameters:
            suite(Suite_): The suite object to deploy.
            headers(bool): Whether to deploy the headers.
            overwrite(bool): Whether to overwrite existing target.
        """

        self._overwrite = overwrite
        self._headers = headers
        self._includes = set()

        self._home = suite.lookup_variable_value("ECF_HOME", ".")
        try:
            self._files = suite.files_path
        except ValueError:
            self._files = self._home
        try:
            self._include = suite.include_path
        except ValueError:
            self._include = self._home
        self._out = suite.lookup_variable_value("ECF_OUT", self._home)

        # Track the unique scripts that are deployed. Ensures we can bail if multiple save()
        # calls are made to the same file, but with different contents

        self.scripts_map = {}

    def files_install_path(self):
        """*str*: Returns the files install path."""
        return self._files

    def deploy_uniqueness_check(self, source, target):
        m = hashlib.md5()
        assert isinstance(source, (str, bytes))
        m.update(source.encode("utf-8") if isinstance(source, str) else source)
        source_hash = m.digest()

        if target in self.scripts_map:
            if self.scripts_map[target] != source_hash:
                raise RuntimeError(
                    "Scripts deployed with the same name must be unique within one AnchorFamily or Suite: {}".format(
                        target
                    )
                )

        self.scripts_map[target] = source_hash

    def save(self, source, target):
        """
        Deploys the task script to target path.
        This method contains functionality needed for all deployments.
        Should be called in `super()` by all derived classes.

        Parameters:
            source(str,bytes,list): The task script to deploy.
            target(str): The deployment path.
        """

        if isinstance(source, list):
            source = "\n".join(source)

        self.deploy_uniqueness_check(source, target)

    def copy(self, source, target):
        """
        Deploys the task script to target path. This method contains functionality needed for all deployments. Should be
        called in `super()` by all derived classes.

        Parameters:
            source(str): The path to task script.
            target(str): The deployment path.
        """

        with open(source, "r") as f:
            self.deploy_uniqueness_check(f.read(), target)

    def deploy_task(self, deploy_path, full_script, required_includes):
        """
        Deploys the task to target path.

        Parameters:
            deploy_path(str): The deployment path.
            full_script(str,list): The full script of the task.
            required_includes(list): The list of required header files.
        """

        for h in required_includes:
            self._includes.add(h)

        # None is a valid deploy path for Notebooks
        if deploy_path is not None:
            assert deploy_path[0] == "/"
            if not deploy_path.startswith(self._files):
                print("Deploy path: {}".format(deploy_path))
                print("Suite base path: {}".format(self._files))
                raise RuntimeError("Paths must be subpaths of the suite ECF_FILES path")

        self.save(full_script, deploy_path)

    def deploy_headers(self):
        """Installs all required header files."""

        where = self if self._headers else Dummy()

        for inc in self._includes:
            inc.install(where)

    def finalise(self):
        """
        Allow derived types to perform an action at the end of the deployment
        """
        return


class Notebook(Deployment, FileListHTMLWrapper):
    """
    A dummy deployment target for Jupyter Notebooks, skips creation of directories and files and dumps fresh **ecFlow**
    definitions as cell output.

    Parameters:
        suite(Suite_): The suite object to deploy.
        path(str): The path to Git repository.

    Example::

        s = pyflow.Suite('suite')
        s.deploy_suite(target=pyflow.Notebook)
    """

    def __init__(self, suite, **options):
        super().__init__(suite, **options)
        self._content = []

    def copy(self, source, target):
        """
        Deploys the task script to target path.

        Parameters:
            source(str,bytes,list): The task script to deploy.
            target(str): The deployment path.
        """

        super().copy(source, target)
        with open(source, "r") as f:
            self.save(f.read(), target)

    def save(self, source, target):
        """
        Deploys the task script to target path.

        Parameters:
            source(str): The path to task script.
            target(str): The deployment path.
        """

        super().save(source, target)
        self._content.append((target, source))


class Dummy:
    def copy(*args):
        pass

    def save(*args):
        pass


class FileSystem(Deployment):
    def patch_path(self, path):
        """
        Allow derived types to simply modify the storage behaviour
        """
        return path

    def create_directory(self, path):
        path = self.patch_path(path)
        if not os.path.exists(path):
            try:
                os.makedirs(path)
                print("Create directory: {}".format(path))
            except Exception:
                print("WARNING: Couldn't create directory: {}".format(path))

    def check(self, target):
        if target is None:
            raise RuntimeError(
                "None is not a valid path for deployment. Most likely files/ECF_FILES unspecified"
            )
        if os.path.exists(target):
            if not self._overwrite:
                print("File %s exists, not overwriting" % (target,))
                return False
            else:
                print("Overwriting existing file: %s" % (target,))

        self.create_directory(os.path.dirname(target))
        return True

    def copy(self, source, target):
        target = self.patch_path(target)
        super().copy(source, target)

        if not self.check(target):
            return

        print("Copy %s to %s" % (source, target))

        with open(source, "r") as f:
            with open(target, "w") as g:
                g.write(f.read())

    def save(self, source, target):
        target = self.patch_path(target)
        super().save(source, target)

        if not self.check(target):
            return

        print("Save %s" % (target,))

        output = "\n".join(source) if isinstance(source, list) else source
        assert isinstance(output, (str, bytes))
        with open(target, "w" if isinstance(output, str) else "wb") as g:
            g.write(output)


class DeployGitRepo(FileSystem):
    """
    A deployment target for Git repositories


    Parameters:
        suite(Suite_): The suite object to deploy.
        host(str): The target host.
        user(str): The user account owning the git repository.
        message(str): commit message.
        build_dir(str): The path to the build directory (to stage the file).
        suite_def(str): The path to the suite definition file.

    Example::

        s = pf.Suite('suite')
        pyflow.DeployGitRepo(s, path='/path/to/git')
    """

    def __init__(
        self, suite, host=None, user=None, message=None, build_dir=None, suite_def=None
    ):
        super().__init__(suite)

        # get hostname and user to rsync the files later
        self.host = os.path.expandvars("$HOSTNAME") if host is None else host
        self.user = os.path.expandvars("$USER") if user is None else user

        # create the staging directory "build"
        self.build_dir = "build" if build_dir is None else build_dir
        self.build_dir = os.path.realpath(self.build_dir)
        self.source_dir = os.path.join(self.build_dir, "files")
        self.target_dir = self._files

        # write definition file in build directory
        def_file = "suite.def" if suite_def is None else suite_def
        source_def = os.path.join(self.build_dir, def_file)
        with open(source_def, "w") as f:
            f.write(str(suite.ecflow_definition()))

        # git commit message
        self.message = f"deployed by {user}\n"
        if message:
            self.message += message

    def patch_path(self, path):
        """
        Patches the path so it includes the complete **ecFlow** path.

        Parameters:
            path(str): The path to patch.

        Returns:
            *str*: The patched path.
        """
        rel_path = os.path.relpath(path, self._files)
        return os.path.join(self.files_dir, rel_path)

    def finalise(self):
        """
        Push the build folder with the git repository
        """
        # push the files (scripts and definition file) to remote
        self.sync(self.source_dir, self.target_dir)

    def sync(self, src, dest):
        """
        Rsync command on remote host
        """
        cmd = f"rsync -e 'ssh -o StrictHostKeyChecking=no' -avz --delete {src} {self.user}@{self.host}:{dest}"
        p = subprocess.Popen(cmd, shell=True)
        p.wait()
        yield f"{cmd} Rsync process completed."

    def git_commit(self):
        cmd = f'ssh {self.user}@{self.host} "'
        cmd += f"cd {self.target_dir};"
        cmd += "if [ ! -d .git ]; then git init; fi;"
        cmd += "git add .;"
        cmd += "git commit -am '{self.message}';"
        cmd += '"'


def deploy_suite(suite, target=FileSystem, **options):
    """
    Deploys suite and its components.

    Parameters:
        suite(Suite): suite to deploy
        target(Deployment): Deployment target for the suite.
        **options(dict): Accept extra keyword arguments as deployment options.

    Returns:
        *Deployment*: Deployment target object.
    """

    # N.B. Important safety check. Do not remove. Extern nodes must never be played or generated.
    assert not suite._extern, "Attempting to deploy extern node not permitted"

    target = target(suite, **options)
    for t in suite.all_tasks:
        script, includes = t.generate_script()
        target.deploy_task(t.deploy_path, script, includes)
    target.deploy_headers()
    target.finalise()
    return target
