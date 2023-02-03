#!/usr/bin/env python3
"""
Example showing the use of the pyflow Configurator

The purpose of the configurator is to enable the creation of sophisticated, reproducible,
discrete configurations that can be selected on the command line.

Example usages:

  configuration.py --help
  configuration.py --foo first --bar second third
  configuration.py --foo=second --bar=third
"""

from __future__ import print_function

import os
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser

import pyflow


class BaseConfiguration(pyflow.FileConfiguration):
    # argument specifies the command line argument which will be used to select the
    # particular configuration.

    # config_dir specifies the location of the files containing the configurations

    argument = "foo"
    config_dir = os.path.join(os.path.dirname(__file__), "example_configurations")

    def __init__(self, args, value="default"):
        # This is the place to put in place checks that the relevant parameters have
        # been passed in, and are the correct type
        assert isinstance(value, str)
        self.value = value

        # Configurations can be fine tuned based on the contents of the command line arguments.
        self.extra = "{0} {0} splat".format(args.extra)

    def __str__(self):
        return "Config(value={}, created={}, extra={})".format(
            self.value, self.created, self.extra
        )

    def check(self):
        """
        Any post __init__ consistency checks can be added here. In this case we enforce that
        the configurations MUST create the attribute "created", and this must be a list.
        """
        assert hasattr(self, "created")
        assert isinstance(self.created, list)


class Configurator(pyflow.Configurator):
    """
    Configurator objects do the building of one or more Configurations according to
    a supplied command line.

    n.b. The attributes the configurations are placed into do not have to match the command
         line arguments
    """

    # An attribute is class derived from pyflow.FileConfiguration. This will be
    # instantiated with a specific configuration selected according to the
    # commandline arguments.

    foo_config = BaseConfiguration

    # pyflow.ConfigurationList allows the selection of a set of configurations, which
    # will populate a list.

    bar_configs = pyflow.ConfigurationList("bar", BaseConfiguration)

    # def __init__(self, args):
    #     super().__init__(args)
    #         ## Additional configuration can be added here, that is not dependent on
    #         ## discrete configuration files


if __name__ == "__main__":
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)

    # Command line arguments to control the configurator can be suggested by it.

    for configurable in Configurator.choices():
        parser.add_argument(
            "--{}".format(configurable.name),
            help=configurable.help,
            choices=configurable.choices,
            nargs=("*" if configurable.multichoice else None),
            default=configurable.default,
        )

    # Any additional commandline options can be added as desired.

    parser.add_argument("--extra", help="An extra parameter", default="squiggle")

    args = parser.parse_args()

    # The configuration object is constructed by the Configurator from the command line arguments

    # This configuration object should now be used in the construction of the Families.
    # If branching decisions are to be made dependent on the configuration, they should be
    # made in the configuration (e.g. config.build_worker_family()) rather than by having
    # if statements and branching logic in the main suite.

    config = Configurator(args)

    # Print the configuration

    print("Configuration:")

    print("Foo (single config):")
    print("  {}".format(config.foo_config))
    print()

    print("Bar (list of configs):")
    for i, config in enumerate(config.bar_configs):
        print("  {}: {}".format(i, config))
