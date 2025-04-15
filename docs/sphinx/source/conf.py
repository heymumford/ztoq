# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
from unittest.mock import MagicMock


class Mock(MagicMock):
    @classmethod
    def __getattr__(cls, name):
        return MagicMock()

# Mock modules that might not be available
MOCK_MODULES = ["psutil", "uvicorn"]
sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)

# Add the project root directory to the path
sys.path.insert(0, os.path.abspath("../../../"))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "ztoq"
copyright = "2025, Eric C. Mumford (@heymumford)"
author = "Eric C. Mumford (@heymumford)"
release = "0.4.1"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",  # Include documentation from docstrings
    "sphinx.ext.viewcode",  # Add links to highlighted source code
    "sphinx.ext.napoleon",  # Support for NumPy and Google style docstrings
    "sphinx.ext.coverage",  # Checks documentation coverage
    "sphinx.ext.todo",  # Support for todo items
    "sphinx.ext.intersphinx",  # Link to other projects' documentation
    "sphinx_rtd_theme",  # Read the Docs theme
    "myst_parser",  # MyST Markdown parser for Sphinx
    # Remove recommonmark as it conflicts with myst_parser
]

# Configure autodoc
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

# Configure MyST Parser
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "dollarmath",
    "fieldlist",
    "html_admonition",
    "html_image",
    "linkify",
    "replacements",
    "smartquotes",
    "strikethrough",
    "substitution",
    "tasklist",
]

# Configure markdown support
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

language = "en"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "navigation_depth": 4,
    "logo_only": False,
    "prev_next_buttons_location": "both",
    "style_external_links": True,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "titles_only": False,
}

# Set version display separately
html_show_sphinx = True
html_show_version = True

html_static_path = ["_static"]
html_css_files = ["custom.css"]

# -- Options for intersphinx extension ---------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
}

# -- Options for todo extension ----------------------------------------------
todo_include_todos = True

# -- Options for copyright information ------------------------------------------
copyright = "2025, Eric C. Mumford (@heymumford)"
html_show_copyright = True

# Link to license file
html_context = {
    "license_url": "https://github.com/heymumford/ztoq/blob/main/LICENSE",
}
