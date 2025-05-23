import pytest

import pyflow


def test_host_task():
    host1 = pyflow.SSHHost(
        "a-host",
        user="a-user",
        scratch_directory="/tmp",
        ecflow_path="/usr/local/bin",
    )

    host2 = pyflow.LocalHost(scratch_directory="/tmp2", ecflow_path="/usr/local/bin")

    with pyflow.Suite("s") as s:
        with pyflow.Family("limits"):
            host1.build_limits()
            host2.build_limits()

        with pyflow.Family("f"):
            t1 = pyflow.Task("t1")

            t2 = pyflow.Task(
                "t2",
                host=host1,
                script='echo "boom"',
                workdir=host1.scratch_directory,
            )

            t3 = pyflow.Task(
                "t3",
                host=host2,
                script='echo "boom"',
                workdir=host2.scratch_directory,
            )

        with pyflow.Family("f2", host=host1) as f2:
            t4 = pyflow.Task(
                "t4", script='echo "boom"', workdir=host1.scratch_directory
            )

            t5 = pyflow.Task(
                "t5",
                host=host1,
                script='echo "boom"',
                workdir=host1.scratch_directory,
            )

            t6 = pyflow.Task(
                "t6",
                host=host2,
                script='echo "boom"',
                workdir=host2.scratch_directory,
            )

        with pyflow.Family("f3", host=host2) as f3:
            t7 = pyflow.Task(
                "t7", script='echo "boom"', workdir=host2.scratch_directory
            )

            t8 = pyflow.Task(
                "t8",
                host=host1,
                script='echo "boom"',
                workdir=host1.scratch_directory,
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
        hostname,
        user=username,
        scratch_directory="/tmp",
        log_directory="/var/log",
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


def check_pragma(script, pragmas):
    for prag in pragmas:
        assert prag in script[0]


def test_troika_host():
    host1 = pyflow.TroikaHost(
        name="test_host",
        user="test_user",
    )
    host2 = pyflow.TroikaHost(
        name="test_host", user="test_user", troika_version="2.2.2"
    )

    submit_args = {
        "tasks": 2,  # deprecated option, will be translated to total_tasks
        "gpus": 1,
        "sthost": "/foo/bar",
        "distribution": "test",  # generates TROIKA pragma for recent version of troika, SBATCH for older versions
    }

    with pyflow.Suite("s", host=host1) as s:
        with pyflow.Family("f"):
            t1 = pyflow.Task("t1", script='echo "boom"', submit_arguments=submit_args)
            t2 = pyflow.Task(
                "t2",
                host=host2,
                script='echo "boom"',
                submit_arguments=submit_args,
            )

    s.check_definition()

    assert (
        s.ECF_JOB_CMD.value
        == "%TROIKA:troika% -vv  submit -u test_user -o %ECF_JOBOUT% test_host %ECF_JOB%"
    )
    assert (
        s.ECF_KILL_CMD.value
        == "%TROIKA:troika% -vv  kill -u test_user test_host %ECF_JOB%"
    )

    t1_script = t1.generate_script()
    t2_script = t2.generate_script()
    print(t1_script)
    print(t2_script)

    in_script = [
        "#TROIKA total_tasks=2",
        "#TROIKA gpus=1",
        "#TROIKA export_vars=STHOST=/foo/bar",
        "#SBATCH --distribution=test",
    ]
    check_pragma(t1_script, in_script)

    # check for new versions of troika
    in_script = [
        "#TROIKA total_tasks=2",
        "#TROIKA gpus=1",
        "#TROIKA export_vars=STHOST=/foo/bar",
        "#TROIKA distribution=test",
    ]
    check_pragma(t2_script, in_script)


def test_host_submit_args():

    submit_args = {
        "troika": {
            "tasks": 2,  # deprecated option, will be translated to total_tasks
            "gpus": 1,
            "sthost": "/foo/bar",
            "distribution": "test",  # generates TROIKA pragma for recent version of troika, SBATCH for older versions
        },
    }
    host1 = pyflow.TroikaHost(
        name="test_host",
        user="test_user",
        submit_arguments=submit_args,
        troika_version="2.2.2",
    )

    with pyflow.Suite("s", host=host1) as s:
        with pyflow.Family("f"):
            t1 = pyflow.Task("t1", script='echo "boom"', submit_arguments="troika")
            t2 = pyflow.Task(
                "t2",
                host=host1,
                script='echo "boom"',
                submit_arguments={
                    **submit_args["troika"],
                    **{"job_name": "task2_jobname", "gpus": 2},
                },
            )
            t3 = pyflow.Task("t3", script='echo "boom"')

    s.check_definition()

    t1_script = t1.generate_script()
    t2_script = t2.generate_script()
    t3_script = t3.generate_script()

    in_script = [
        "#TROIKA total_tasks=2",
        "#TROIKA gpus=1",
        "#TROIKA export_vars=STHOST=/foo/bar",
        "#TROIKA distribution=test",
    ]
    check_pragma(t1_script, in_script)

    # check for new versions of troika
    in_script = [
        "#TROIKA total_tasks=2",
        "#TROIKA gpus=2",
        "#TROIKA export_vars=STHOST=/foo/bar",
        "#TROIKA distribution=test",
        "#TROIKA job_name=task2_jobname",
    ]
    check_pragma(t2_script, in_script)

    assert "#TROIKA" not in t3_script[0]
    assert "#SBATCH" not in t3_script[0]


def test_troika_host_options():
    host = pyflow.TroikaHost(
        name="test_host",
        user="test_user",
        troika_exec="/path/to/troika",
        troika_config="/path/to/troika.cfg",
        troika_version="2.1.3",
    )

    s = pyflow.Suite("s", host=host)

    assert (
        s.ECF_JOB_CMD.value
        == "%TROIKA:/path/to/troika% -vv -c %TROIKA_CONFIG:/path/to/troika.cfg% submit -u test_user -o %ECF_JOBOUT% test_host %ECF_JOB%"  # noqa: E501
    )
    assert (
        s.ECF_KILL_CMD.value
        == "%TROIKA:/path/to/troika% -vv -c %TROIKA_CONFIG:/path/to/troika.cfg% kill -u test_user test_host %ECF_JOB%"  # noqa: E501
    )
    assert s.host.troika_version == (2, 1, 3)


if __name__ == "__main__":
    from os import path

    pytest.main(path.abspath(__file__))
