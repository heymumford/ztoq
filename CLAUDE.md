# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Test Commands
- Setup: `poetry install`
- Run all tests: `poetry run pytest`
- Run unit tests: `poetry run pytest -m unit`
- Run integration tests: `poetry run pytest -m integration` 
- Run single test: `poetry run pytest tests/path/to/test_file.py::TestClass::test_method -v`
- Test with coverage: `poetry run pytest --cov=ztoq --cov-report=term --cov-report=html`
- Lint: 
  - Standard: `poetry run flake8 ztoq tests`
  - Helper scripts:
    - `./scripts/run_lint.sh` - Run flake8 ignoring common style issues
    - `./scripts/run_critical_lint.sh` - Run flake8 focusing only on critical issues
- Format: `poetry run black ztoq tests`
- Build docs: `cd docs/sphinx && make html`

## Code Style Guidelines
- **Line Length**: 100 characters max (black, flake8)
- **Format**: Use black with default settings
- **Typing**: Use static typing with mypy; all public functions should have type annotations
- **Exception Handling**: Use domain-specific exception hierarchy; handle and log appropriately
- **Imports**: 
  - Keep imports after license header and docstrings but before any other code
  - Order: standard library, third-party, local imports (sorted alphabetically)
  - Standard format: 
    ```python
    import std_lib1
    import std_lib2
    from std_lib3 import something
    
    from third_party import package
    
    from ztoq.some_module import SomeClass
    ```
  - Fix imports with the scripts/fix_imports.py tool when adding license headers
  - Note: setup.cfg contains configured exceptions for various linting rules:
    - E402 errors for imports after license headers and docstrings are ignored
    - E501 line length exceptions for specific complex files
    - E131/E125/E122 continuation line formatting in specific files
- **Naming**:
  - Classes: PascalCase
  - Functions/Variables: snake_case
  - Constants: UPPER_SNAKE_CASE
- **Documentation**: Docstrings for all public classes and methods
- **Testing**: Follow TDD approach (test-driven development) with pytest
- **License Headers**: Make sure to use scripts/add_license_headers.py to add license information to new files
- **Helper Scripts**:
  - scripts/add_license_headers.py - Adds license headers to Python files and footers to Markdown files
  - scripts/fix_imports.py - Fixes import ordering in Python files
  - scripts/fix_spacing.py - Fixes class and function spacing issues according to flake8 rules
  - scripts/fix_fstring.py - Fixes f-strings missing placeholders (F541 errors)

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](LICENSE)*