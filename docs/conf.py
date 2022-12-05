# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Imports -----------------------------------------------------------------

import datetime
import os
import re
import sys

import pyflow

# -- Path manipulation--------------------------------------------------------

# Add a specific path to the Python system path.
include_path = os.path.realpath("..")
sys.path.insert(0, include_path)

# Add custom extension directory to the Python system path.
sys.path.append(os.path.abspath("./_ext"))


# -- Project information -----------------------------------------------------

project = "pyflow"
author = "ECMWF"

year = datetime.datetime.now().year
if year == 2021:
    years = "2021"
else:
    years = "2021-%s" % (year,)

copyright = "%s, %s" % (years, author)

release = pyflow.__version__


def parse_version(ver_str):
    return re.sub("^((([0-9]+)\\.)+([0-9]+)).*", "\\1", ver_str)


version = parse_version(release)  # feature version


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx_rtd_theme",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "nbsphinx",
    "IPython.sphinxext.ipython_directive",
    "IPython.sphinxext.ipython_console_highlighting",
    "sphinx_copybutton",
    "sphinx_tabs.tabs",
    "sphinx.ext.todo",
    "ecflow_lexers",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "__pycache__",
    "'**.ipynb_checkpoints'",
]

source_suffix = ".rst"
master_doc = "index"
pygments_style = "sphinx"


# -- Options for nbsphinx ----------------------------------------------------

# https://www.notion.so/Deepnote-Launch-Buttons-63c642a5e875463495ed2341e83a4b2a

# nbsphinx_prolog = """
# {% set gh_repo = "ecmwf/project" %}
# {% set docname = env.doc2path(env.docname, base=None) %}

# |Binder| |Colab| |Deepnote| |Kaggle|

# .. |Binder| image:: https://mybinder.org/badge.svg
#    :target: https://mybinder.org/v2/gh/{{ gh_repo|e }}/{{ env.config.release|e }}?urlpath=lab/tree/docs/{{ docname|e }} # noqa: E501
#    :alt: Binder
#    :class: badge

# .. |Colab| image:: https://colab.research.google.com/assets/colab-badge.svg
#    :target: https://colab.research.google.com/github/{{ gh_repo|e }}/blob/{{ env.config.release|e }}/docs/{{ docname|e }} # noqa: E501
#    :alt: Colab
#    :class: badge

# .. |Deepnote| image:: https://img.shields.io/badge/launch%20in-deepnote-blue.svg
#    :target: https://beta.deepnote.org/launch?template=deepnote&url=https://github.com/{{ gh_repo|e }}/blob/{{ env.config.release|e }}/docs/{{ docname|e }} # noqa: E501
#    :alt: Deepnote
#    :class: badge

# .. |Kaggle| image:: https://kaggle.com/static/images/open-in-kaggle.svg
#    :target: https://kaggle.com/kernels/welcome?src=https://github.com/{{ gh_repo|e }}/blob/{{ env.config.release|e }}/docs/{{ docname|e }} # noqa: E501
#    :alt: Kaggle
#    :class: badge

# """  # noqa

ipython_warning_is_error = True


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_context = {"css_files": ["_static/style.css"]}

# Remove links to the reST sources from the page headers.
html_show_sourcelink = False

# Remove "Created using Sphinx" from the HTML footer.
html_show_sphinx = False

# html_theme_options = {'logo_only': True}
# html_logo = '_static/logo.png'


# -- Options for the todo extension ------------------------------------------

# To disable output of `todo` blocks, just set the `NO_INCLUDE_TODOS` environment variable to any value, i.e:
#
#   NO_INCLUDE_TODOS=1
#
#   Unfortunately, this cannot be done via the configuration file for the Read the Docs service, you must use their web
#   interface instead. More information here: https://github.com/readthedocs/readthedocs.org/issues/6311
todo_include_todos = False if os.environ.get("NO_INCLUDE_TODOS") else True


# -- Options for the autodoc extension ---------------------------------------

autodoc_member_order = "groupwise"
autodoc_default_options = {
    "members": True,
    "inherited-members": True,
    "noindex": True,
}


# -- Sphinx copy button configuration ----------------------------------------

copybutton_selector = ".copybutton div.highlight pre"


# -- Sphinx Tabs configuration -----------------------------------------------

sphinx_tabs_disable_tab_closing = True


# -- Set a "fake" user name for API reference purposes -----------------------

os.environ["LOGNAME"] = "pyflow"
