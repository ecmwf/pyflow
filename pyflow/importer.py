import functools
import os
import sys
import types

from packaging.specifiers import SpecifierSet

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


def supported(specifier: str, current: str = ecflow.__version__):
    """
    A decorator that ensures the decorated class can only be used when
    the available ecFlow version satisfies ``specifier``.

    Every method and property of the class is wrapped so that invoking it
    (e.g. instantiating the class via ``__init__``, or accessing a property)
    raises :class:`NotImplementedError` when ``current`` does not satisfy
    ``specifier``.

    The version comparison is evaluated once, when the class is decorated
    (i.e. at import time, using ``current`` which defaults to the version of
    the imported ecFlow module).
    The ``current`` argument allows tests to instrument the behaviour for an arbitrary version.

    Parameters:
        specifier(str): A :class:`packaging.specifiers.SpecifierSet` string, e.g. ``">=5.12.0,<6.0.0"``.
        current(str): The current version, e.g. ``"5.12.0"``. Defaults to the version of the imported ecFlow module.
    """

    # Evaluate the comparison once, since both versions are fixed for the
    # lifetime of the decorated class.
    is_supported = SpecifierSet(specifier).contains(current)

    def decorator(cls):

        # Define a wrapper factory that checks the supported version before calling the original function
        def make_wrapper(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not is_supported:
                    raise NotImplementedError(
                        "{} functionality is only supported for ecFlow {}, but current version is {}".format(
                            cls.__name__, specifier, current
                        )
                    )

                return func(*args, **kwargs)

            return wrapper

        # Iterate over a copy as we mutate the class namespace while iterating.
        for attr_name, attr_value in list(cls.__dict__.items()):

            if isinstance(attr_value, types.FunctionType):
                # Wrapped plain methods directly.
                setattr(cls, attr_name, make_wrapper(attr_value))

            elif isinstance(attr_value, property):
                # Ensure properties must remain properties,
                # by wrapping accessors and rebuilding the property so attribute access keeps working.
                setattr(
                    cls,
                    attr_name,
                    property(
                        make_wrapper(attr_value.fget) if attr_value.fget else None,
                        make_wrapper(attr_value.fset) if attr_value.fset else None,
                        make_wrapper(attr_value.fdel) if attr_value.fdel else None,
                        attr_value.__doc__,
                    ),
                )

            elif isinstance(attr_value, staticmethod):
                # Unwrap the inner function, wrap it, and re-wrap as staticmethod.
                setattr(cls, attr_name, staticmethod(make_wrapper(attr_value.__func__)))

            elif isinstance(attr_value, classmethod):
                # Unwrap the inner function, wrap it, and re-wrap as classmethod.
                setattr(cls, attr_name, classmethod(make_wrapper(attr_value.__func__)))

        return cls

    return decorator
