from __future__ import print_function

import difflib
import hashlib
import os
import shutil

from pyflow.html import FileListHTMLWrapper


class DeploymentError(RuntimeError):
    pass


class Deployment:
    def __init__(self, suite, headers=True):
        """
        Base class for all deployments.

        Parameters:
            suite(Suite_): The suite object to deploy.
            headers(bool): Whether to deploy the headers.
        """

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
                with open(target, "r") as f:
                    old_content = f.read()
                    diff = difflib.unified_diff(
                        old_content.splitlines(),
                        source.splitlines(),
                        lineterm="",
                    )
                    diff_str = "\n".join(diff)
                    print(
                        f"\nERROR! Differences between already-deployed script and current one:\n{diff_str}"
                    )
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
            if not deploy_path.startswith(self._files):
                print("Deploy path: {}".format(deploy_path))
                print("Suite base path: {}".format(self._files))
                raise RuntimeError("Paths must be subpaths of the suite ECF_FILES path")

        self.save(full_script, deploy_path)

    def deploy_manual(self, deploy_path, full_script):
        """
        Deploys the manual to target path.

        Parameters:
            deploy_path(str): The deployment path.
            full_script(str,list): The full script of the manual.
        """

        # None is a valid deploy path for Notebooks
        if deploy_path is not None:
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
    """
    A filesystem target for suite deployment
    Parameters:
        suite(Suite_): The suite object to deploy.
        path(str): The target directory (by default ECF_FILES).
    Example:
        s = pf.Suite('suite')
        pyflow.FileSystem(s, path='/path/to/suite/files')
    """

    def __init__(self, suite, path=None, **kwargs):
        super().__init__(suite, **kwargs)
        self.path = path
        self._processed = set()

    def patch_path(self, path):
        """
        Allows to deploy the suite to a different place than ECF_FILES
        """
        if self.path:
            rel_path = os.path.relpath(path, self._files)
            path = os.path.join(self.path, rel_path)
        return path

    def create_directory(self, path):
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except Exception:
                print("WARNING: Couldn't create directory: {}".format(path))

    def check(self, target):
        """
        Check if the target should be deployed.
        Returns False if target has already been deployed, True otherwise.

        Parameters
        ----------
        target : str
            The target path for deployment.

        Returns
        -------
        bool
            True if the target path is valid for deployment, False otherwise.
        """
        if target is None:
            raise RuntimeError(
                "None is not a valid path for deployment. Most likely files/ECF_FILES unspecified"
            )

        # if script with same content already deployed, skip
        if os.path.exists(target):
            if self.duplicate_write_check(target):
                return False
        else:
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

        output = "\n".join(source) if isinstance(source, list) else source
        assert isinstance(output, (str, bytes))
        with open(target, "w" if isinstance(output, str) else "wb") as g:
            g.write(output)

    def duplicate_write_check(self, target):
        if target in self._processed:
            return True
        self._processed.add(target)
        return False


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
