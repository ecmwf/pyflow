"""
A base class for providing configurations to which elements of pyflow suites can be delegated

**********************************************************************************************

n.b. The Configuration / Configurator classes make use of a substantial amount of black magic.

If you are wishing to understand how to use these classes, please see the example
found at:

examples/configuration.py

This is likely to be more illuminating than an examination of the source code.

**********************************************************************************************
"""

import inspect
import os
from collections import namedtuple
from importlib import util


class Configuration:
    def __init__(self, *args, **kwargs):
        """Ensure we can safely be an arbitrary base class"""
        pass

    def check(self):
        pass

    @staticmethod
    def available_choices():
        return None

    @classmethod
    def build_configuration_object(cls, args, **kwargs):
        return cls(args, **kwargs)

    def __repr__(self):
        return "{}()".format(self.__class__.__name__)


class FileConfiguration(Configuration):
    """
    A base class for all configuration objects
    """

    # These three class-level attributes must be overridden in the derived class.

    argument = None  # The command line argument to use
    help = None  # The help text for the command line
    config_dir = None  # The directory to search for configuration files
    config_dirs = None  # The directories to search for configuration files

    # The name of the class which is being configured in the configs. By default 'Configuration'
    configured_class = "Configuration"

    # The configuration name is set automatically by the Configurator according to the command line
    # arguments (and therefore from the name of the configuration file selected).
    # It can alternatively be explicitly overridden in the derived Configuration class.

    configuration_name = None

    # What is the default choice? No default by default...
    default = None

    def __repr__(self):
        try:
            class_name = self.__class__.__bases__[0].__name__
        except (AttributeError, KeyError):
            class_name = "Configuration"
        return "{}({})".format(class_name, self.configuration_name or "unknown")

    @classmethod
    def available_choices(cls):
        """
        Return a list of strings corresponding to the available configuration files in the specified
        directory
        """
        files = [
            (os.path.splitext(f), os.path.join(config_dir, f))
            for config_dir in cls.config_dirs or [cls.config_dir]
            for f in os.listdir(config_dir)
        ]
        return [
            f[0][0]
            for f in files
            if (
                os.path.exists(f[1])
                and os.path.isfile(f[1])
                and f[0][1] == ".py"
                and f[0][0][0] != "_"
            )
        ]

    @classmethod
    def build_configuration_object(cls, args, choice=None, **kwargs):
        # We can manually supply the argument, or get it from the commandline arguments.
        # This is mostly useful if we are iterating through the available choices...
        if choice is None:
            keyword = cls.argument
            choice = getattr(args, keyword)
            if choice is None:
                return None

        for config_dir in cls.config_dirs or [cls.config_dir]:
            filename = os.path.join(config_dir, "{}.py".format(choice))
            if os.path.exists(filename):
                break

        name = filename[1:].replace("/", "_")
        spec = util.spec_from_file_location(name, filename)
        imported = util.module_from_spec(spec)
        spec.loader.exec_module(imported)

        configured_class = getattr(imported, cls.configured_class)

        if issubclass(configured_class, Configuration):
            cfg = configured_class(args, **kwargs)
        else:
            cfg = configured_class(**kwargs)

        # If the configuration name is unspecified, use the supplied one
        if not hasattr(cfg, "configuration_name") or cfg.configuration_name is None:
            cfg.configuration_name = choice

        return cfg


class ConfigurationList(Configuration):
    """
    A configuration that allows selecting multiple configurations from above with the given
    option, rather than just one of them.
    """

    def __init__(self, argument, configuration_class):
        assert issubclass(configuration_class, FileConfiguration)

        self._configuration_class = configuration_class

        self.argument = argument
        self.help = self._configuration_class.help
        self.config_dir = self._configuration_class.config_dir
        self.default = self._configuration_class.default

    def available_choices(self):
        """
        A configuration list has the option to return all configurations
        """
        return ["all"] + self._configuration_class.available_choices()

    def build_configuration_object(self, args, **kwargs):
        keyword = self.argument
        choices = getattr(args, keyword)

        if choices is None:
            choices = []
        elif choices == "all" or choices == ["all"]:
            choices = self._configuration_class.available_choices()

        return [
            self._configuration_class.build_configuration_object(args, choice, **kwargs)
            for choice in choices
        ]


class Configurator:
    """
    A configurator object is initialised with pyflow.Configuration classes (or objects that behave like classes),
    which specify what needs to be built.

    At initialisation time, these attributes are replaced on the object with initialised objects according to
    the arguments passed in.
    """

    def __init__(self, args, **kwargs):
        for attr_name, configuration_class in self.configurations():
            setattr(
                self,
                attr_name,
                configuration_class.build_configuration_object(args, **kwargs),
            )

            cfgs = getattr(self, attr_name)
            if not isinstance(cfgs, list):
                cfgs = [cfgs]
            for cfg in cfgs:
                cfg.check()

    def __repr__(self):
        elems = {
            attr: getattr(self, attr)
            for attr in dir(self)
            if not attr[0] == "_" and not inspect.ismethod(getattr(self, attr))
        }
        return "{}".format(elems)

    @classmethod
    def choices(cls):
        """
        Return an iterable of (named) tuples of the name, help string and options
        """
        Configurable = namedtuple(
            "Configurable",
            ["name", "help", "choices", "multichoice", "default"],
        )
        for attr_name, configuration_class in cls.configurations():
            choices = configuration_class.available_choices()
            if choices is not None:
                yield Configurable(
                    configuration_class.argument,
                    configuration_class.help,
                    configuration_class.available_choices(),
                    isinstance(configuration_class, ConfigurationList),
                    configuration_class.default,
                )

    @classmethod
    def configurations(cls):
        """
        Return the available configurations
        :return: a list of tuples of (attribute_name, configuration_class)
        """
        return [
            (attr, getattr(cls, attr))
            for attr in dir(cls)
            if (
                inspect.isclass(getattr(cls, attr))
                and issubclass(getattr(cls, attr), Configuration)
                or isinstance(getattr(cls, attr), Configuration)
            )
        ]
