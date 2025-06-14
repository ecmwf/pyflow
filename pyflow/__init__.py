# flake8: noqa

from __future__ import absolute_import

from .attributes import (
    Aviso,
    Complete,
    Cron,
    Crons,
    Date,
    Defstatus,
    Edit,
    Event,
    GeneratedVariable,
    InLimit,
    Inlimit,
    Label,
    Late,
    Limit,
    Meter,
    Mirror,
    RepeatDate,
    RepeatDateList,
    RepeatDateTime,
    RepeatDay,
    RepeatEnumerated,
    RepeatInteger,
    RepeatString,
    Time,
    Trigger,
    Variable,
)
from .configurator import (
    Configuration,
    ConfigurationList,
    Configurator,
    FileConfiguration,
)
from .deployment import DeployGitRepo, Notebook
from .expressions import Deferred, all_complete, sequence
from .extern import (
    Extern,
    ExternEvent,
    ExternFamily,
    ExternMeter,
    ExternNode,
    ExternTask,
    ExternYMD,
)
from .header import FileHeader, FileTail, Header, InlineCodeHeader
from .host import Host, LocalHost, NullHost, PBSHost, SLURMHost, SSHHost, TroikaHost
from .multiple import Events, Families, InLimits, Limits, Tasks
from .nodes import AnchorFamily, Family, Suite, Task, ecflow_name
from .resource import DataResource, FileResource, Resources, WebResource
from .script import FileScript, PythonScript, Script, TemplateFileScript, TemplateScript

try:
    # NOTE: the `_version.py` file must not be present in the git repository
    #   as it is generated by setuptools at install time
    from ._version import __version__
except ImportError:  # pragma: no cover
    # Local copy or not installed with setuptools
    __version__ = ""
