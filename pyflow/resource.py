from __future__ import absolute_import

import collections
import hashlib
import os

import requests

from .nodes import Family, Task
from .script import DelegatingScript


class Resources(Family):
    """
    Provides both visual and logical grouping of related resources.

    Note:
        Just a wrapper (for now) on Family_, used for consistency and elegance.

    Parameters:
        name(str): The name of the resource group to create.
        host(Host_): The host to execute the resource group on.

    Example::

        with pyflow.Resources(host=pf.LocalHost()):
            pass
    """

    def __init__(self, name=None, host=None):
        # n.b. The Resources tasks run on the ecflow server (LocalHost)
        super().__init__(name or "resources", host=host)


class Resource(Task):
    """
    Provides a single resource to be deployed at suite generation time.

    Parameters:
        name(str): The name of the resource.
        hosts(list,Host_): The list of hosts to deploy the resource to.
    """

    def __init__(self, name, hosts):
        super().__init__(name, script=DelegatingScript(self))

        self._server_filename = None

        self._hosts = hosts if isinstance(hosts, collections.abc.Iterable) else [hosts]
        self._resource_directory = os.path.join(
            self._hosts[0].resources_directory,
            os.path.dirname(self.fullname[1:]),
        )

        for h in self._hosts:
            if not h.resources_directory:
                raise RuntimeError(
                    "Resource {} can only be deployed to hosts with the same resources directory".format(
                        name
                    )
                )

    def md5(self):
        raise NotImplementedError

    def save_data(self, target, filename):
        """
        Resources don't all need to save data at generation time.

        :meta private:
        """

        pass

    def get_resource(self, filename):
        """
        (Running on the ecflow server) a script get the resource to deploy at runtime

        :meta private:
        """

        return []

    def install_file_stub(self, target):
        """
        Installs any data associated with the resource object that is going to be deployed from the **ecFlow** server.

        Parameters:
            target(Deployment): The target deployment where the resource data should be installed.
        """

        """
        n.b. If a resource does not need to save data at deployment time, it should not do so (e.g. WebResource)
        """
        # Install path is for the suite, so we don't need to include the suite name
        assert self.fullname.count("/") > 1
        subpath = self.fullname[self.fullname.find("/", 1) + 1 :]

        self._server_filename = os.path.join(
            target.files_install_path(), subpath, self.name
        )

        super().install_file_stub(target)

        self.save_data(target, self._server_filename)

    def build_script(self):
        """
        Returns the installer script for the data resource.

        Returns:
            *list*: The list of installer commands.
        """

        assert self._server_filename

        lines = ['echo "Resource installer for: {}"'.format(self.name)]

        lines += self.get_resource(self._server_filename)

        lines += [
            "(cd {}; echo {} {} | md5sum -c)".format(
                os.path.dirname(self._server_filename),
                self.md5(),
                os.path.basename(self._server_filename),
            )
        ]

        for h in self._hosts:
            lines += h.copy_file_to(self._server_filename, self.location()).split("\n")

        return lines

    def location(self):
        """
        Returns the path of the resource.

        Returns:
            *str*: The path of the resource.
        """

        return os.path.join(self._resource_directory, self.name)


class DataResource(Resource):
    """
    Provides a data resource to be deployed at suite generation time.

    Parameters:
        name(str): The name of the resource.
        hosts(Host_,list): The host or list of hosts to deploy the resource to.
        source_data: The resource data.

    Example::

        pyflow.DataResource('data1',
                            [pyflow.LocalHost(resources_directory='/path/to/data')],
                            "this is some data".encode('utf-8'))
    """

    def __init__(self, name, hosts, source_data):
        self._data = source_data

        super().__init__(name, hosts)

    def md5(self):
        """
        Returns MD5 checksum of the resource data.

        Returns:
            *str*: The MD5 checksum of the resource data.
        """

        m = hashlib.md5()
        m.update(self._data)
        return m.hexdigest()

    def save_data(self, target, filename):
        """
        Deploys the data for the resource at suite generation time.

        Parameters:
            target(Deployment): The deployment target.
            filename(str): The filename for the resource data.
        """

        """
        Resources don't all need to save data at generation time
        """
        target.save(self._data, filename)


class FileResource(Resource):
    """
    Provides a file resource to be deployed at suite generation time.

    Parameters:
        name(str): The name of the resource.
        hosts(list,Host_): The list of hosts to deploy the resource to.
        source_file(str): The filename of the resource.

    Example::

        pyflow.FileResource('data2',
                            [pyflow.LocalHost(resources_directory='/path/to/data')],
                            'path/to/data.dat')
    """

    def __init__(self, name, hosts, source_file):
        self._source = source_file

        super().__init__(name, hosts)

    def md5(self):
        """
        Returns MD5 checksum of the resource data.

        Returns:
            *str*: The MD5 checksum of the resource data.
        """

        m = hashlib.md5()
        m.update(self.data())
        return m.hexdigest()

    def data(self):
        """
        Returns the resource data from the provided file.

        Returns:
            The resource data.
        """

        with open(self._source, "rb") as f:
            return f.read()

    def save_data(self, target, filename):
        """
        Deploys the data for the resource at suite generation time.

        Parameters:
            target(Deployment): The deployment target.
            filename(str): The filename for the resource data.
        """

        target.save(self.data(), filename)


class WebResource(Resource):
    """
    Provides a web resource to be deployed at suite generation time.

    Parameters:
        name(str): The name of the resource.
        hosts(list,Host_): The list of hosts to deploy the resource to.
        url(str): The URL of the resource.
        md5(str): The MD5 checksum of the resource.

    Example::

        pyflow.WebResource('data3',
                           [pyflow.LocalHost(resources_directory='/path/to/data')],
                           'https://example.com/data',
                           md5='0123456789abcdef')
    """

    def __init__(self, name, hosts, url, md5=None):
        self._url = url
        self._md5 = md5
        super().__init__(name, hosts)

    def md5(self):
        """
        Returns MD5 checksum of the resource data. If not provided at construction time, resource will be downloaded
        and hashed.

        Returns:
            *str*: The MD5 checksum of the resource data.
        """

        if not self._md5:
            md5_url = "{}.md5".format(self._url)
            print("Getting MD5 from: {}".format(md5_url))

            r = requests.get(md5_url)
            if r.status_code != 200:
                raise RuntimeError(
                    "Error ({}) getting {}".format(r.status_code, md5_url)
                )

            self._md5 = r.content.split(" ")[0]

        return self._md5

    # TODO: do we want to clean up once we have deployed the data?
    def get_resource(self, filename):
        """
        Returns script commands to retrieve the resource to deploy at runtime.

        Parameters:
            filename(str): The filename for the resource data.
        """

        return [
            'mkdir -p $(dirname "{}")'.format(filename),
            'wget -O "{}" "{}"'.format(filename, self._url),
        ]
