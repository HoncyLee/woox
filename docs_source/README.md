# WOOX Trading Bot Documentation

This directory contains the Sphinx documentation for the WOOX Trading Bot.

## Building Documentation

### Prerequisites

Install Sphinx and dependencies:

```bash
pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints
```

### Build HTML Documentation

```bash
cd docs
make html
```

The built documentation will be in `_build/html/`.

### View Documentation

```bash
# Open in browser
open _build/html/index.html

# Or on Linux
xdg-open _build/html/index.html
```

### Build Other Formats

```bash
# PDF (requires LaTeX)
make latexpdf

# EPUB
make epub

# Plain text
make text
```

### Clean Build

```bash
make clean
```

## Documentation Structure

```
docs/
├── conf.py                 # Sphinx configuration
├── index.rst              # Documentation home page
├── getting_started.rst    # Installation and setup
├── configuration.rst      # Configuration guide
├── strategies.rst         # Trading strategies guide
├── api_reference.rst      # API documentation
├── testing.rst            # Testing guide
├── deployment.rst         # Deployment guide
├── _static/              # Static files (CSS, images)
├── _templates/           # Custom templates
└── _build/               # Built documentation (generated)
```

## Writing Documentation

Documentation is written in reStructuredText (RST) format. See:

- [RST Primer](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html)
- [Sphinx Documentation](https://www.sphinx-doc.org/)

## Auto-Generated API Docs

API documentation is automatically generated from Python docstrings using:

- `sphinx.ext.autodoc` - Includes documentation from docstrings
- `sphinx.ext.napoleon` - Supports Google/NumPy style docstrings
- `sphinx_autodoc_typehints` - Includes type hints in docs

## Continuous Documentation

To rebuild documentation automatically on changes:

```bash
pip install sphinx-autobuild
sphinx-autobuild docs docs/_build/html
```

Then open http://127.0.0.1:8000 in your browser.

## Publishing Documentation

### GitHub Pages

```bash
# Build documentation
make html

# Copy to GitHub Pages directory
cp -r _build/html/* ../../docs/

# Commit and push
git add ../../docs/
git commit -m "Update documentation"
git push
```

### Read the Docs

1. Sign up at https://readthedocs.org/
2. Import your GitHub repository
3. Documentation will build automatically on each commit

## Contributing

When adding new features:

1. Add docstrings to all functions and classes
2. Update relevant RST files
3. Build documentation and check for warnings
4. Test all code examples
5. Submit pull request with documentation updates
