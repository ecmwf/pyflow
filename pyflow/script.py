from __future__ import absolute_import

import jinja2

from .attributes import Exportable


class Script:
    """
    A group of commands that define the main work that is to be carried out for a task.

    Parameters:
        value(str,list): The script command or the list of script commands.

    Example::

        with pyflow.Task('t', script=pyflow.Script('echo "Hello, world!"')):
            pass
    """

    def __init__(self, value=None):
        self._values = (
            (value if isinstance(value, list) else [value]) if value is not None else []
        )
        self._environment_variables = {}
        self._extra_required_exportables = set()

    def __str__(self):
        return "\n".join(self.generate_stub())

    @property
    def value(self):
        """*str*: The string value with all script commands."""
        return str(self)

    # @deprecated (TODO)
    def environment_variable(self, k, v):
        """
        Defines an environment variable for the script.

        Parameters:
            k(str): The name of the environment variable.
            v(str): The value of the environment variable.
        """

        self.define_environment_variable(k, v)

    def define_environment_variable(self, k, v, export=True):
        """
        Defines an environment variable for the script.

        Parameters:
            k(str): The name of the environment variable.
            v(str): The value of the environment variable.
            export(bool): Whether to export the environment variable, must be `True`.
        """

        assert export
        self._environment_variables[k] = v

    def generate(self):
        """
        This is the routine that should be overridden by derived Script classes

        --> The actual content associated with this script

        :meta private:
        """
        return []

    # @deprecated (TODO)
    def add_required_exportables(self, *args):
        """
        Defines a set of required exportable variables.

        Parameters:
            *args(tuple): Accept positional arguments as names of exportable variables.
        """

        self._extra_required_exportables |= set(args)

    def force_exported(self, exportable):
        """
        Defines a required exportable attribute.

        Parameters:
            exportable(str): The name of the exportable variables.
        """

        self.add_required_exportables(exportable)

    def required_exportables(self):
        """
        Returns the set of required exportable variables.

        Returns:
            *set*: The set of required exportable variables.
        """

        """
        Which exportables are explicitly known (n.b. this does not include those
        inferred by using regexes on the script - that is done in class Task in nodes.py
        as it has a broader view of the scripts.
        """

        required = set()
        for val in self._values:
            try:
                required |= val.required_exportables()
            except AttributeError:
                pass
        required |= self._extra_required_exportables
        return required

    def generate_stub(self):
        """
        Returns complete script by combining the fragments.

        Returns:
            *list*: The list of script commands.
        """

        """
        You probably DON'T want to override this one. Consider generate() instead
        """
        lines = []

        for variable, value in self._environment_variables.items():
            if not variable.isupper():
                raise RuntimeError(
                    "Environment variables should be uppercased ({})".format(variable)
                )
            lines.append('export {}="{}"'.format(variable, str(value)))

        # Customised generate functions

        lines += self.generate()

        # Sub-scripts and component values
        # n.b. any added via __iadd__ will be here, so should be after the generate function

        lines += self.generate_list_scripts(self._values)

        return lines

    @staticmethod
    def generate_list_scripts(values):
        """
        Generates a script of all passed scripts.

        Parameters:
            values(list): The list of Script_ objects.

        Returns:
            *list*: The list of script commands.
        """

        lines = []
        for val in values:
            try:
                lines += val.generate_stub()
            except AttributeError:
                if isinstance(val, list):
                    lines += Script.generate_list_scripts(val)
                else:
                    lines += [line.rstrip() for line in str(val).split("\n")]
        return lines

    def __iadd__(self, other):
        if isinstance(other, list):
            self._values += other
        else:
            self._values.append(other)
        return self

    def __add__(self, other):
        """
        We can combine scripts to produce more complex scripts
        """
        aggregated = Script(self)
        aggregated += other
        return aggregated


class PythonScript(Script):
    """
    A script written in Python language.

    Parameters:
        value(str,list): The Python command or the list of Python commands.
        python(int): The Python major version.

    Example::

        pyflow.PythonScript('w1 = "Hello"\\nw2 = "world"\\nprint(f"{w1}, {w2}!")', 3)
    """

    def __init__(self, value=None, python=3):
        super().__init__(value)
        self.python_version = python

    def generate_stub(self):
        script_body = super().generate_stub()
        if script_body[0] == "":
            script_body = script_body[1:]
        if script_body[-1] == "":
            script_body = script_body[:-1]
        return (
            ["python{} -u - <<EOS".format(self.python_version)] + script_body + ["EOS"]
        )


class DelegatingScript(Script):
    """
    A helper script that delegates construction of its contents to another object (most likely the
    Task) which has additional functionality available at build time.
    """

    def __init__(self, delegee):
        super().__init__()
        self._delegee = delegee

    def generate(self):
        return self._delegee.build_script()


class FileScript(Script):
    """
    A script with a provided filename, which is read at the time of suite generation.

    Parameters:
        filename(str): The filename of the script to read from.

    Example::

        pyflow.FileScript('/path/to/script')
    """

    def __init__(self, filename):
        super().__init__()
        self._filename = filename

    def generate(self):
        """
        Returns the script commands from the provided file.

        Returns:
            *list*: The list of script commands.
        """
        with open(self._filename, "r") as f:
            return f.read().split("\n")


class JinjaMixin:
    """
    Use Jinja2 templating
    """

    def __init__(self, *args, **kwargs):
        self.template_values = kwargs
        super().__init__(*args)

    def generate_stub(self):
        """
        Returns complete script by combining the fragments.

        Returns:
            *list*: The list of script commands.
        """

        # Split encodable values from filter functions
        filter_functions = {
            k: v for k, v in self.template_values.items() if callable(v)
        }
        template_values = {
            k: v for k, v in self.template_values.items() if not callable(v)
        }
        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        env.filters.update(filter_functions)
        template = env.from_string("\n".join(super().generate_stub()))
        return template.render(**template_values).split("\n")

    def required_exportables(self):
        """
        Returns the set of required exportable variables.

        Returns:
            *set*: The set of required exportable variables.
        """

        required = super().required_exportables()
        for var in self.template_values.values():
            if isinstance(var, Exportable):
                required.add(var)
        return required

    def add_parameters(self, **kwargs):
        """
        Defines extra parameters for template variables.

        Parameters:
            **kwargs(dict): Accept keyword arguments as values for template variables.
        """

        self.template_values.update(kwargs)


class TemplateScript(JinjaMixin, Script):
    """
    A script template with Jinja syntax support.

    Parameters:
        value(str,list): The script command or the list of script commands.
        **kwargs(dict): Accept keyword arguments as values for template variables.

    Example::

        pyflow.TemplateScript('echo "{{ w1 }}, {{ w2 }}!"', w1='Hello', w2='world')
    """

    pass


class TemplateFileScript(JinjaMixin, FileScript):
    """
    A script template with a provided filename, which is read at the time of suite generation.

    Parameters:
        filename(str): The filename of the script to read from.
        **kwargs(dict): Accept keyword arguments as values for template variables.

    Example::

        pyflow.TemplateFileScript('/path/to/script', foo='bar')
    """

    pass
