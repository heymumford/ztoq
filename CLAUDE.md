# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Test Commands
- Setup: `poetry install`
- Run all tests: `poetry run pytest`
- Run unit tests: `poetry run pytest -m unit`
- Run integration tests: `poetry run pytest -m integration` 
- Run single test: `poetry run pytest tests/path/to/test_file.py::TestClass::test_method -v`
- Test with coverage: `poetry run pytest --cov=ztoq --cov-report=term --cov-report=html`
- Lint: `poetry run flake8 ztoq tests`
- Format: `poetry run black ztoq tests`
- Build docs: `cd docs/sphinx && make html`

## Code Style Guidelines
- **Line Length**: 100 characters max (black, flake8)
- **Format**: Use black with default settings
- **Typing**: Use static typing with mypy; all public functions should have type annotations
- **Exception Handling**: Use domain-specific exception hierarchy; handle and log appropriately
- **Imports**: Group standard library, third-party, and local imports (sorted alphabetically)
- **Naming**:
  - Classes: PascalCase
  - Functions/Variables: snake_case
  - Constants: UPPER_SNAKE_CASE
- **Documentation**: Docstrings for all public classes and methods
- **Testing**: Follow TDD approach (test-driven development) with pytest

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](LICENSE)*