import os


class AnchorMixin:
    """
    A mixin to define Anchor behaviour --> part of Suite and of Family
    --> A helper to node.py, but needed in attribute.py
    """

    def __init__(self, *args, **kwargs):
        variables = {}
        variables.update(kwargs)

        if "out" in kwargs:
            print(
                "WARNING! out option is deprecated for nodes, use the log_directory option in the host instead"
            )

        for control_variable in ("files", "include", "home", "out", "extn"):
            if control_variable in kwargs:
                ecf_var = "ECF_{}".format(control_variable.upper())
                assert ecf_var not in kwargs
                variables[ecf_var] = kwargs[control_variable]
                del variables[control_variable]

        super().__init__(*args, **variables)

        if (
            "files" not in kwargs
            and "ECF_FILES" not in kwargs
            and self.suite is not self
        ):
            self.ECF_FILES = self._anchor_new_files_path

    @property
    def anchor(self):
        """*Anchor*: The anchor object."""
        return self

    @property
    def files_path(self):
        """*str*: The files path of the node."""
        return self.lookup_variable_value("ECF_FILES")

    @property
    def include_path(self):
        """*str*: The include path of the node."""
        return self.lookup_variable_value("ECF_INCLUDE", self.files_path)

    def _anchor_new_files_path(self, unused):
        """
        This is a function that is executed lazily, which allows any appropriate
        modifications to be made to the tree of objects, and still get the correct
        structure.

        n.b. This property is only assigned to the objects ECF_FILES variable if
             there is not a more fixed value.
        """
        return os.path.join(
            self.parent.anchor.files_path,
            os.path.relpath(self.fullname, self.parent.anchor.fullname),
        )
