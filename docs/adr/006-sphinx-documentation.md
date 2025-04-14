# ADR-006: Use Sphinx for Documentation Generation

## Status

Accepted

## Context

ZTOQ needs a comprehensive documentation system that can:

1. Generate API reference automatically from code
2. Include conceptual and usage documentation
3. Support both code syntax highlighting and diagrams
4. Be easily built and maintained alongside the codebase
5. Integrate with the build process
6. Present architecture decisions and diagrams clearly
7. Support multiple output formats (HTML, PDF)

We considered several options for documentation:

1. **Sphinx** - Python's de facto documentation generator
2. **MkDocs** - Markdown-based documentation generator
3. **Doxygen** - Comprehensive but more complex documentation system
4. **GitBook** - Modern documentation platform
5. **Plain Markdown** - Simple but limited

## Decision

We will use Sphinx with the Read the Docs theme for documentation generation, integrating it with our build process to automatically generate documentation after test completion.

## Consequences

### Positive

- Sphinx is the standard documentation tool in the Python ecosystem
- Automatic API documentation generation from docstrings
- Support for restructured text (rst) which is powerful for technical docs
- Extensible through a rich plugin ecosystem
- Read the Docs theme provides a professional, responsive design
- Integration with build process ensures documentation stays current
- Support for multiple output formats (HTML, PDF, ePub)
- Ability to include architecture diagrams and ADRs

### Negative

- Steeper learning curve compared to plain Markdown
- ReStructuredText syntax can be more verbose than Markdown
- Requires additional dependencies
- Configuration can be complex initially

## Implementation Details

1. **Project Structure**:
   ```
   docs/
   ├── sphinx/
   │   ├── source/
   │   │   ├── _static/          # Custom CSS and static assets
   │   │   ├── api/              # Auto-generated API documentation
   │   │   ├── adrs/             # Architecture Decision Records
   │   │   ├── conf.py           # Sphinx configuration
   │   │   └── index.rst         # Documentation root
   │   ├── Makefile              # Build commands
   │   └── make.bat              # Windows build script
   ```

2. **Build Integration**:
   - Added `docs` and `docs-serve` targets to Makefile
   - Enhanced build.py script with `--with-docs` flag to generate documentation after tests
   - Created test_docs.sh script for documentation verification

3. **Extensions Used**:
   - sphinx.ext.autodoc - Generate API documentation from docstrings
   - sphinx.ext.viewcode - Link documentation to highlighted source code
   - sphinx.ext.napoleon - Support for NumPy and Google style docstrings
   - sphinx_rtd_theme - Read the Docs theme
   - myst_parser - Markdown support

4. **Custom Styling**:
   - Custom CSS for C4 diagrams
   - Status badges for ADRs
   - Improved code blocks presentation

5. **C4 Diagram Integration**:
   - Guidelines for creating C4 diagrams with Lucidchart
   - Templates and example code

## Usage

Documentation can be generated using:

```bash
# Generate documentation
make docs

# Build and serve documentation locally
make docs-serve

# Run tests and generate documentation
make test-with-docs

# Build script with docs flag
python build.py test --with-docs
```

## References

- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [Read the Docs Theme](https://sphinx-rtd-theme.readthedocs.io/)
- [MyST Parser for Markdown](https://myst-parser.readthedocs.io/)

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](../../LICENSE)*