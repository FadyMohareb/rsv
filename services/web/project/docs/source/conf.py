import os
import sys
sys.path.insert(0, os.path.abspath('../../..'))
print("Current sys.path:", sys.path)  # Debugging
import project  # Now it should work!

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'rsv-neqas'
copyright = '2025, Kevin'
author = 'Kevin'
release = '0.0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc','sphinx.ext.napoleon', 'sphinx.ext.viewcode','sphinx_js']

js_source_path = os.path.join('../../..', 'frontend_mount', 'src')  # Path to your frontend code

napoleon_google_docstring = True
napoleon_numpy_docstring = False

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
