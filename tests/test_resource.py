from os import path
from os.path import join

from pyflow import FileResource, Notebook, Suite
from pyflow.host import SSHHost


def test_file_resource():

    resouces_directory = "/resources_directory"

    sshhost_1 = SSHHost("example_ssh_host_1", resources_directory=resouces_directory)
    sshhost_2 = SSHHost("example_ssh_host_2", resources_directory=resouces_directory)
    host_set = [sshhost_1, sshhost_2]

    source_file = path.join(path.dirname(path.abspath(__file__)), "file_resource.txt")
    name = "file_resource"

    with Suite("s", host=sshhost_1) as s:
        s.resource_file = FileResource(name, hosts=host_set, source_file=source_file)

    # Check that variables are set correctly
    assert s.resource_file.host == sshhost_1
    assert s.resource_file.location() == join(
        str(sshhost_1.resources_directory), s.name, name
    )
    assert s.resource_file._hosts == host_set

    # Check that the deployment scripts have been generated
    s.check_definition()
    s.generate_node()

    s.deploy_suite(target=Notebook)

    generate_file_resource_script_lines, _ = s.resource_file.generate_script()
    assert any(sshhost_1.name in s for s in generate_file_resource_script_lines)
    assert any(sshhost_2.name in s for s in generate_file_resource_script_lines)


if __name__ == "__main__":

    import pytest

    pytest.main(path.abspath(__file__))
