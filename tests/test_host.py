import pytest
import unittest

import pyflow


def test_host_task():
    host1 = pyflow.SSHHost(
        "a-host", user="a-user", scratch_directory="/tmp", ecflow_path="/usr/local/bin"
    )

    host2 = pyflow.LocalHost(scratch_directory="/tmp2", ecflow_path="/usr/local/bin")

    with pyflow.Suite("s") as s:
        with pyflow.Family("limits"):
            host1.build_limits()
            host2.build_limits()

        with pyflow.Family("f"):
            t1 = pyflow.Task("t1")

            t2 = pyflow.Task(
                "t2", host=host1, script='echo "boom"', workdir=host1.scratch_directory
            )

            t3 = pyflow.Task(
                "t3", host=host2, script='echo "boom"', workdir=host2.scratch_directory
            )

        with pyflow.Family("f2", host=host1) as f2:
            t4 = pyflow.Task(
                "t4", script='echo "boom"', workdir=host1.scratch_directory
            )

            t5 = pyflow.Task(
                "t5", host=host1, script='echo "boom"', workdir=host1.scratch_directory
            )

            t6 = pyflow.Task(
                "t6", host=host2, script='echo "boom"', workdir=host2.scratch_directory
            )

        with pyflow.Family("f3", host=host2) as f3:
            t7 = pyflow.Task(
                "t7", script='echo "boom"', workdir=host2.scratch_directory
            )

            t8 = pyflow.Task(
                "t8", host=host1, script='echo "boom"', workdir=host1.scratch_directory
            )

            t9 = pyflow.Task(
                "t9",
                host=host2,
                script='echo "boom"',
                workdir=host2.scratch_directory,
                clean_workdir=True,
            )

    s.check_definition()

    # Test job commands

    job_cmd1 = "bash -c 'export ECF_PORT=%ECF_PORT%; export ECF_HOST=%ECF_HOST%; export ECF_NAME=%ECF_NAME%; export ECF_PASS=%ECF_PASS%; export ECF_TRYNO=%ECF_TRYNO%; export PATH=/usr/local/bin:$PATH; ecflow_client --init=\"$$\" && ssh -v -o StrictHostKeyChecking=no a-user@a-host bash -s < %ECF_JOB%&& ecflow_client --complete || ecflow_client --abort ' 1> %ECF_JOBOUT% 2>&1 &"  # noqa: E501
    job_cmd2 = "bash -c 'export ECF_PORT=%ECF_PORT%; export ECF_HOST=%ECF_HOST%; export ECF_NAME=%ECF_NAME%; export ECF_PASS=%ECF_PASS%; export ECF_TRYNO=%ECF_TRYNO%; export PATH=/usr/local/bin:$PATH; ecflow_client --init=\"$$\" && %ECF_JOB% && ecflow_client --complete || ecflow_client --abort ' 1> %ECF_JOBOUT% 2>&1 &"  # noqa: E501

    assert not hasattr(t1, "ECF_JOB_CMD")

    assert t2.ECF_JOB_CMD.value == job_cmd1
    assert t3.ECF_JOB_CMD.value == job_cmd2

    assert f2.ECF_JOB_CMD.value == job_cmd1
    assert not hasattr(t4, "ECF_JOB_CMD")
    assert t5.ECF_JOB_CMD.value == job_cmd1
    assert t6.ECF_JOB_CMD.value == job_cmd2

    assert f3.ECF_JOB_CMD.value == job_cmd2
    assert not hasattr(t7, "ECF_JOB_CMD")
    assert t8.ECF_JOB_CMD.value == job_cmd1
    assert t9.ECF_JOB_CMD.value == job_cmd2

    # Test kill commands

    kill_cmd = "pkill -15 -P %ECF_RID%"

    assert not hasattr(t1, "ECF_KILL_CMD")

    assert t2.ECF_KILL_CMD.value == kill_cmd
    assert t3.ECF_KILL_CMD.value == kill_cmd

    assert f2.ECF_KILL_CMD.value == kill_cmd
    assert not hasattr(t4, "ECF_KILL_CMD")
    assert t5.ECF_KILL_CMD.value == kill_cmd
    assert t6.ECF_KILL_CMD.value == kill_cmd

    assert f3.ECF_KILL_CMD.value == kill_cmd
    assert not hasattr(t7, "ECF_KILL_CMD")
    assert t8.ECF_KILL_CMD.value == kill_cmd
    assert t9.ECF_KILL_CMD.value == kill_cmd

    # Has the working directory been correctly exported

    workdir1 = """[[ -d "/tmp" ]] || mkdir -p "/tmp"\ncd "/tmp"\n"""
    workdir2 = """[[ -d "/tmp2" ]] || mkdir -p "/tmp2"\ncd "/tmp2"\n"""

    s2 = "\n".join(t2.generate_script()[0])
    s3 = "\n".join(t3.generate_script()[0])
    s4 = "\n".join(t4.generate_script()[0])
    s5 = "\n".join(t5.generate_script()[0])
    s6 = "\n".join(t6.generate_script()[0])
    s7 = "\n".join(t7.generate_script()[0])
    s8 = "\n".join(t8.generate_script()[0])
    s9 = "\n".join(t9.generate_script()[0])

    assert workdir1 in s2 and workdir2 not in s2
    assert workdir2 in s3 and workdir1 not in s3
    assert workdir1 in s4 and workdir2 not in s4
    assert workdir1 in s5 and workdir2 not in s5
    assert workdir2 in s6 and workdir1 not in s6
    assert workdir2 in s7 and workdir1 not in s7
    assert workdir1 in s8 and workdir2 not in s8
    assert workdir2 in s9 and workdir1 not in s9


def test_nullhost():
    with pyflow.Suite("s") as s1:
        t1 = pyflow.Task("t1")

        with pyflow.Family("f", host=pyflow.NullHost()) as f:
            with pytest.raises(AttributeError):
                pyflow.Task("t2")

    with pyflow.Suite("s2", host=pyflow.NullHost()) as s2:
        with pytest.raises(AttributeError):
            pyflow.Task("t3")

    default_killcmd = "pkill -15 -P %ECF_RID%"

    assert s1.has_variable("ECF_JOB_CMD")
    assert not f.has_variable("ECF_JOB_CMD")
    assert not s2.has_variable("ECF_JOB_CMD")

    assert s1.has_variable("ECF_KILL_CMD")
    assert not f.has_variable("ECF_KILL_CMD")
    assert not s2.has_variable("ECF_KILL_CMD")

    assert s1.lookup_variable_value("ECF_KILL_CMD") == default_killcmd
    assert t1.lookup_variable_value("ECF_KILL_CMD") == default_killcmd
    assert f.lookup_variable_value("ECF_KILL_CMD") == default_killcmd


def test_explicit_hostname():
    h1 = pyflow.SSHHost("a-host", user="u")

    assert h1.name == "a-host"
    assert h1.hostname == "a-host"
    assert "u@a-host" in h1.job_cmd

    h2 = pyflow.SSHHost("b-host", hostname="other-host", user="u")

    assert h2.name == "b-host"
    assert h2.hostname == "other-host"
    assert "u@other-host" in h2.job_cmd


def test_default_host():
    with pyflow.Suite("s"):
        t = pyflow.Task("t")

    print(t.host)
    t.host.ecflow_path = "/usr/local/bin"
    assert t.host.name == "default"
    assert t.host.hostname == "default"
    assert (
        t.host.job_cmd
        == "bash -c 'export ECF_PORT=%ECF_PORT%; export ECF_HOST=%ECF_HOST%; export ECF_NAME=%ECF_NAME%; export ECF_PASS=%ECF_PASS%; export ECF_TRYNO=%ECF_TRYNO%; export PATH=/usr/local/bin:$PATH; ecflow_client --init=\"$$\" && %ECF_JOB% && ecflow_client --complete || ecflow_client --abort ' 1> %ECF_JOBOUT% 2>&1 &"  # noqa: E501
    )
    assert t.host.kill_cmd == "pkill -15 -P %ECF_RID%"


def test_label_host():
    with pyflow.Suite("s") as s:
        # No label on nodes where host is not set by default
        with pyflow.Family("f") as f:
            with pyflow.Family("f1", host=pyflow.LocalHost()) as f1:
                pass

            with pyflow.Family("f2", host=pyflow.LocalHost(label_host=False)) as f2:
                pass

            with pyflow.Family("f3", host=pyflow.NullHost()) as f3:
                pass

    assert "exec_host" in s._nodes
    assert isinstance(s.exec_host, pyflow.Label)
    assert s.exec_host.value == "default"
    assert "exec_host" not in f._nodes
    assert "exec_host" in f1._nodes
    assert isinstance(f1.exec_host, pyflow.Label)
    assert f1.exec_host.value == "localhost"
    assert "exec_host" not in f2._nodes
    assert "exec_host" not in f3._nodes


@pytest.mark.parametrize("class_name", ("LocalHost", "SLURMHost", "PBSHost"))
def test_host_kill_cmd(class_name):
    username = "{}user".format(class_name)
    hostname = class_name

    HostClass = getattr(pyflow, class_name)
    host = HostClass(
        hostname, user=username, scratch_directory="/tmp", log_directory="/var/log"
    )

    if class_name == "LocalHost" or class_name == "SSHHost":
        expected_kill_cmd = "pkill -15 -P %ECF_RID%"
    elif class_name == "SLURMHost":
        expected_kill_cmd = """export ECF_PORT=%ECF_PORT%; export ECF_HOST=%ECF_HOST%; export ECF_NAME=%ECF_NAME%; export ECF_PASS=%ECF_PASS%; export ECF_TRYNO=%ECF_TRYNO%; ssh -v -o StrictHostKeyChecking=no {}@{} "sh -l -c 'scancel "\\$(grep Submitted '%ECF_JOBOUT%.jobfile.sub' | cut -d' ' -f4)"'" && ecflow_client --abort""".format(  # noqa: E501
            username, hostname
        )
    elif class_name == "PBSHost":
        expected_kill_cmd = """export ECF_PORT=%ECF_PORT%; export ECF_HOST=%ECF_HOST%; export ECF_NAME=%ECF_NAME%; export ECF_PASS=%ECF_PASS%; export ECF_TRYNO=%ECF_TRYNO%; ssh -v -o StrictHostKeyChecking=no {}@{} qdel "\\$(cat '%ECF_JOBOUT%.jobfile.sub')" && ecflow_client --abort""".format(  # noqa: E501
            username, hostname
        )
    else:
        pytest.exit("Unrecognized host class: {}".format(class_name))

    assert host.kill_cmd == expected_kill_cmd


# class TestTroikaHost(unittest.TestCase):
#     def setUp(self):
#         self.troika_host = pyflow.TroikaHost(
#             name='test_host',
#             user='test_user',
#             hostname='test_hostname',
#             scratch_directory='/scratch',
#             log_directory='/log',
#             resources_directory='/resources',
#             limit=10,
#             extra_paths=['/usr/bin', '/bin'],
#             extra_variables={'VAR1': 'value1'},
#             environment_variables={'ENV1': 'env_value1'},
#             module_source='module.sh',
#             modules=['python', 'gcc'],
#             purge_models=True,
#             label_host=False,
#             ecflow_path='/ecflow',
#             server_ecfvars=False
#         )

#     def test_initialization(self):
#         self.assertEqual(self.troika_host.name, 'test_host')
#         self.assertEqual(self.troika_host.user, 'test_user')
#         self.assertEqual(self.troika_host.hostname, 'test_hostname')
#         self.assertEqual(self.troika_host.scratch_directory, '/scratch/test_user')
#         self.assertEqual(self.troika_host.log_directory, '/log/test_user')
#         self.assertEqual(self.troika_host.limit, 10)
#         self.assertListEqual(self.troika_host.extra_paths, ['/usr/bin', '/bin'])
#         self.assertDictEqual(self.troika_host.extra_variables, {'VAR1': 'value1'})
#         self.assertDictEqual(self.troika_host.environment_variables, {'ENV1': 'env_value1'})
#         self.assertEqual(self.troika_host.module_source, 'module.sh')
#         self.assertListEqual(self.troika_host.modules, ['python', 'gcc'])
#         self.assertTrue(self.troika_host.purge_models)
#         self.assertFalse(self.troika_host.label_host)
#         self.assertEqual(self.troika_host.ecflow_path, '/ecflow')
#         self.assertFalse(self.troika_host.server_ecfvars)

#     def test_troika_command(self):
#         command = self.troika_host.troika_command('test_command')
#         expected_command = '%TROIKA:troika% -vv -c %TROIKA_CONFIG:% -u test_user test_command -u test_user'
#         self.assertEqual(command, expected_command)

#     def test_job_command_property(self):
#         self.assertIn('submit', self.troika_host.job_cmd)
#         self.assertIn('test_hostname', self.troika_host.job_cmd)

#     def test_kill_command_property(self):
#         self.assertIn('kill', self.troika_host.kill_cmd)
#         self.assertIn('test_hostname', self.troika_host.kill_cmd)

#     def test_status_command_property(self):
#         self.assertIn('monitor', self.troika_host.status_cmd)
#         self.assertIn('test_hostname', self.troika_host.status_cmd)

#     def test_check_command_property(self):
#         self.assertIn('check', self.troika_host.check_cmd)
#         self.assertIn('test_hostname', self.troika_host.check_cmd)

#     def test_script_submit_arguments(self):
#         submit_args = {'tasks': 2, 'sthost': 'test', 'tmpdir': '500', 'hint': 'nomultithread'}
#         results = self.troika_host.script_submit_arguments(submit_args)
#         self.assertIn('export STHOST=test', results)
#         self.assertIn('--gres=ssdtmp:500', results)
#         self.assertIn('--hint=nomultithread', results)


if __name__ == "__main__":
    from os import path

    pytest.main(path.abspath(__file__))
