# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quality Check Commands

When making changes to code, always run the following quality checks before finalizing:

```bash
# Run all linters and fixers
poetry run pre-commit run --all-files

# Check types with mypy
poetry run mypy ztoq/

# Run the test suite
poetry run pytest

# Check docstring coverage
poetry run interrogate -c pyproject.toml ztoq/

# Generate coverage report
poetry run pytest --cov=ztoq --cov-report=term-missing
```

## Common Commands

```bash
# Install dependencies
poetry install

# Run all tests
poetry run pytest

# Run unit tests only
poetry run pytest -m unit

# Run single test 
poetry run pytest tests/path/to/test_file.py::TestClass::test_function

# Run linting and auto-fix issues
poetry run ruff check --fix ztoq/

# Format code
poetry run ruff format ztoq/

# Sort imports
poetry run isort ztoq/

# Check type annotations
poetry run mypy ztoq

# Check for security issues
poetry run bandit -c pyproject.toml -r ztoq/

# Format docstrings
poetry run docformatter --in-place --config ./pyproject.toml ztoq/

# Using Makefile for convenience
make test
make format
make lint
```

## Code Style Guidelines

- Line length: 100 characters max
- Python version: 3.11+
- Use typing annotations for all functions and methods
- Strict type checking with mypy
- Imports: Use `isort` with first-party=["ztoq"] configuration
- Naming: Follow PEP8 conventions (`snake_case` for variables/functions, `CamelCase` for classes)
- Error handling: Use explicit exception handling, provide context with error messages
- Docstrings: Required for modules, classes, functions (except tests) with min 80% coverage
- Testing: Use TDD approach - write tests before/alongside implementation
- Use Pydantic models for data validation
- Use SQLAlchemy for database interactions
- Don't have print statements (use logging)
- Proper exception handling and error tracking using our contextual logging system

## Important Project Structure

- `ztoq/` - Main project code
- `tests/` - Test suite organized by test type (unit, integration, system, performance)
- `examples/` - Example usage and tools
- `docs/` - Documentation including ADRs and technical guides
- `config/` - Configuration files and build scripts
- `alembic/` - Database migration scripts
- `scripts/` - Utility scripts for development and maintenance

## Linting Configuration

The project uses:

1. **Ruff** - Fast Python linter that includes flake8, isort, pyupgrade and more
2. **mypy** - Static type checking
3. **docformatter** - Format docstrings consistently
4. **interrogate** - Check docstring coverage
5. **bandit** - Security linting
6. **pre-commit** - Run checks before commits

These are configured in `pyproject.toml` and `.pre-commit-config.yaml` files.