#!/usr/bin/env python3

import getpass
import os
import subprocess
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser

from pyflow.importer import ecflow

if __name__ == "__main__":
    # Argument parsing

    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        "--host",
        help="ecflow server hostname",
        default=os.environ.get("ECF_HOST", "localhost"),
    )
    parser.add_argument(
        "--port",
        help="ecflow server port",
        default=os.environ.get("ECF_PORT", 5459),
    )
    parser.add_argument(
        "--family", help="the subset of the tree to deploy", default="/"
    )
    parser.add_argument(
        "--deploy-user",
        help="the subset of the tree to deploy",
        default=getpass.getuser(),
    )
    parser.add_argument(
        "--deploy-host",
        help="the subset of the tree to deploy",
        default="localhost",
    )
    parser.add_argument(
        "--deploy-files",
        help="sync the files with the remote",
        action="store_true",
    )
    parser.add_argument(
        "--play-suite", help="play the suite to ecflow", action="store_true"
    )
    parser.add_argument("repo", type=str, nargs=1)

    args = parser.parse_args()

    repo_path = args.repo[0]

    assert args.family[0] == "/"
    family_path = args.family

    # Extract definitions from the relevant definitions file

    defs = ecflow.Defs(os.path.join(repo_path, "ecflow_defs"))
    defs.check()

    # We are only deploying one suite

    suites = list(defs.suites)
    assert len(suites) == 1
    s = suites[0]

    base_vars = {v.name(): v.value() for v in s.variables}
    assert "ECF_FILES" in base_vars
    assert "ECF_INCLUDE" in base_vars

    # Have we found the base node?

    node = defs.find_abs_node(family_path)
    if node is None:
        raise RuntimeError("Node {} not found".format(family_path))

    # In the filesystem, ECF_FILES relates to the suite directory, so remove that from the path

    if family_path.count("/") == 1:
        filesystem_family_path = ""
    else:
        assert family_path.count("/") > 1
        filesystem_family_path = family_path[family_path.find("/", 1) + 1 :]

    for local, remote in (
        ("files", base_vars["ECF_FILES"]),
        ("include", base_vars["ECF_INCLUDE"]),
    ):
        local_path = os.path.join(repo_path, local, filesystem_family_path)
        remote_path = os.path.join(remote, filesystem_family_path)

        if os.path.exists(local_path):
            cmd = [
                "rsync",
                "--recursive",
                "--delete",
                "--verbose",
                # '--dry-run',
                "{}/".format(local_path),
                "{}@{}:{}/".format(args.deploy_user, args.deploy_host, remote_path),
            ]

            if args.deploy_files:
                print("Command: {}".format(cmd))
                subprocess.check_call(cmd)

    # Get the ecflow Client and play the suite

    if args.play_suite:
        print(
            "Replacing family '{}' on {}:{}".format(family_path, args.host, args.port)
        )
        ci = ecflow.Client(args.host, args.port)
        ci.replace(family_path, defs, True, True)
        print("done")
