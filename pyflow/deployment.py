from __future__ import print_function

import hashlib
import os
import shutil

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
        Deploys the task script to target path. This method contains functionality needed for all deployments. Should be
        called in `super()` by all derived classes.

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

    def create_directories(self, path):
        raise NotImplementedError


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

    def create_directories(self, path):
        pass


class Dummy:
    def copy(*args):
        pass

    def save(*args):
        pass

    def create_directories(*args):
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
            except:
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

    def create_directories(self, path):
        pass
        # self.create_directory(self._home + path)
        # It isn't the job of pyflow to create these.
        # self.create_directory(self._out + path)


class DeployGitRepo(FileSystem):
    """
    A deployment target for Git repositories, clears target repository and dumps fresh **ecFlow** definitions.

    Parameters:
        suite(Suite_): The suite object to deploy.
        path(str): The path to Git repository.

    Example::

        s = pf.Suite('suite')
        pyflow.DeployGitRepo(s, path='/path/to/git')
    """

    def __init__(self, suite, path=None):
        super().__init__(suite)

        assert path is not None
        self.paths = {
            self._files: os.path.abspath(os.path.realpath(os.path.join(path, "files"))),
        }
        if self._include != self._files:
            self.paths[self._include] = os.path.abspath(
                os.path.realpath(os.path.join(path, "include"))
            )

        self._deploy_path = path

        print(self._deploy_path)
        assert os.path.exists(os.path.join(self._deploy_path, ".git"))

        # Cleaning existing deploy directory

        for root, dirs, files in os.walk(self._deploy_path):
            for f in files:
                os.unlink(os.path.join(root, f))
            for d in dirs:
                if d != ".git":
                    shutil.rmtree(os.path.join(root, d))

        # Deploy the definitions

        with open(os.path.join(self._deploy_path, "ecflow_defs"), "w") as f:
            f.write(str(suite.ecflow_definition()))

    def patch_path(self, path):
        """
        Patches the path so it includes the complete **ecFlow** path.

        Parameters:
            path(str): The path to patch.

        Returns:
            *str*: The patched path."""

        if path.startswith(self._deploy_path):
            return path

        fullpath = os.path.abspath(os.path.realpath(path))

        for ecf_path, deploy_path in self.paths.items():
            if fullpath.startswith(ecf_path):
                return os.path.join(deploy_path, os.path.relpath(fullpath, ecf_path))

        assert "Unexpected path: ", path
