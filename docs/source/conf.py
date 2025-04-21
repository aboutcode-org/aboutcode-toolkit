# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

project = 'aboutcode-toolkit'
copyright = "nexB Inc. and others."
author = "AboutCode.org authors and contributors"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.intersphinx",
    "sphinx_reredirects",
    "sphinx_rtd_theme",
    "sphinx_rtd_dark_mode",
    "sphinx.ext.extlinks",
    "sphinx_copybutton",
]


# Redirects for olds pages
# See https://documatt.gitlab.io/sphinx-reredirects/usage.html
redirects = {}

# This points to aboutcode.readthedocs.io
# In case of "undefined label" ERRORS check docs on intersphinx to troubleshoot
# Link was created at commit - https://github.com/aboutcode-org/aboutcode/commit/faea9fcf3248f8f198844fe34d43833224ac4a83

intersphinx_mapping = {
    "aboutcode": ("https://aboutcode.readthedocs.io/en/latest/", None),
    "scancode-workbench": (
        "https://scancode-workbench.readthedocs.io/en/develop/",
        None,
    ),
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]
# templates_path = ['../_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# This adds to the levels displayed in the sidebar but the indent is wrong and expand/collapse doesn't work for the additional nodes.
# It's a known issue: see https://stackoverflow.com/questions/14477396/how-to-expand-all-the-subsections-on-the-sidebar-toctree-in-sphinx and https://github.com/readthedocs/sphinx_rtd_theme/issues/455
# html_theme_options = {
#     'navigation_depth': 6,
# }

html_theme_options = {
    "canonical_url": "",
    "analytics_id": "UA-XXXXXXX-1",
    "logo_only": False,
    # "display_version": True,
    # 'prev_next_buttons_location': 'bottom',
    # 'prev_next_buttons_location': 'top',
    "prev_next_buttons_location": "both",
    # 'style_external_links': False,
    # 'style_external_links': True,
    # 'style_nav_header_background': 'white',
    # Toc options
    # 'collapse_navigation': True,
    "collapse_navigation": False,
    # 'sticky_navigation': True,
    "sticky_navigation": False,
    # 'navigation_depth': 4,
    "navigation_depth": -1,
    "includehidden": True,
    "titles_only": False,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
# html_static_path = ['../_static']

html_context = {
    "display_github": True,
    "github_user": "nexB",
    "github_repo": "spats",
    "github_version": "develop",  # branch
    "conf_py_path": "/docs/source/",  # path in the checkout to the docs root
}

html_css_files = [
    "theme_overrides.css",
]

html_js_files = [
    "js/custom.js",
]

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = True

# Define CSS and HTML abbreviations used in .rst files.  These are examples.
# .. role:: is used to refer to styles defined in _static/theme_overrides.css
# and is used like this: :red:`text`
rst_prolog = """
.. # define a hard line break for HTML
.. |br| raw:: html

   <br />

.. role:: red

.. role:: img-title

.. role:: img-title-para

"""

# -- Options for LaTeX output -------------------------------------------------

latex_elements = {
    'classoptions': ',openany,oneside'
}
