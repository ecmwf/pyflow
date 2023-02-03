import os
import sys

try:
    import ecflow
except ImportError:
    found = False

    for env_var in ("ECFLOW_DIR", "ecflow_DIR"):
        try:
            lib_dir = os.path.join(os.environ[env_var], "lib")
        except KeyError:
            continue

        for minor_version in reversed(range(6, sys.version_info.minor + 1)):
            python_dir = os.path.join(
                lib_dir, "python3.{}".format(minor_version), "site-packages"
            )
            if os.path.exists(python_dir):
                sys.path.insert(0, python_dir)
                import ecflow  # noqa: F401

                found = True
                break

        if found:
            break

    if not found:
        raise ImportError(
            "Could not find ecflow Python library, try to set ECFLOW_DIR environment variable to correct path"
        )
