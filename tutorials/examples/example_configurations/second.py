from __future__ import absolute_import

from configuration import BaseConfiguration


class Configuration(BaseConfiguration):
    def __str__(self):
        """This override is optional. Just to print '(second)'"""
        return "(second) {}".format(super().__str__())

    def __init__(self, args):
        # Any imports that are required in the __init__ function should be here, not globally
        # to circumvent globals() confusion with execfile()

        # n.b. self.__class__ as running in a different namespace
        super().__init__(args, value="second-value")

        self.created = [2, 2]
