# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

from datetime import datetime

from throttled import __version__

version = __version__
release = __version__
project = "throttled-py"
author = "ZhuoZhuoCrayon"
copyright = f"{datetime.now().year}, Crayon"
description = (
    "🔧 High-performance Python rate limiting library "
    "with multiple algorithms(Fixed Window, Sliding Window, Token Bucket, "
    "Leaky Bucket & GCRA) and storage backends (Redis, In-Memory)."
)

# html_title = (
#     f'<span class="project-title">{project}</span> '
#     f'<span class="project-version">v{version}</span>'
# )

html_title = f"{project} v{version}"

html_theme_options = {
    "repository_url": "https://github.com/ZhuoZhuoCrayon/throttled-py",
    "use_edit_page_button": False,
    "use_source_button": False,
    "use_issues_button": True,
    "use_repository_button": True,
    "use_download_button": False,
    "use_sidenotes": True,
    "show_toc_level": 2,
}

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["sphinx_thebe", "sphinx_inline_tabs", "sphinx_copybutton"]

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# Use the Sphinx Book Theme: https://github.com/executablebooks/sphinx-book-theme
html_theme = "sphinx_book_theme"
# Set the path to the static files directory
html_static_path = ["_static"]
# Add custom CSS files
html_css_files = [
    "custom.css",
]
