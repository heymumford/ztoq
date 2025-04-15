# ZTOQ Development Scripts

This directory contains utility scripts to help with development and maintenance of the ZTOQ project.

## Available Scripts

### Setup and Environment Management

- **setup.py**: Sets up the development environment by installing dependencies, configuring pre-commit hooks, and verifying critical dependencies are available.

  ```bash
  python scripts/setup.py
  ```

- **update_environment.py**: Updates all dependencies and tools to the latest versions, ensuring everything is in sync.

  ```bash
  python scripts/update_environment.py
  ```

- **ensure_dependencies.py**: Verifies that all required dependencies are properly installed.

  ```bash
  python scripts/ensure_dependencies.py
  ```

### Documentation and Code Quality

- **build_and_host_docs.py**: Builds the Sphinx documentation and hosts it locally.

- **check_personal_refs.py**: Checks for personal references in the codebase.

- **fix_logging.py**: Fixes logging configuration across the project.

- **remove_unused_imports.py**: Removes unused imports from Python files.

- **verify_project_structure.py**: Verifies that the project structure adheres to best practices.

### Database Management

- **init_db.py**: Initializes the database schema.

## Using the Makefile

For convenience, many of these scripts can be run through the Makefile:

```bash
# Setup development environment
make setup

# Update dependencies and tools
make update

# Clean build artifacts
make clean

# Run linting with auto-fix
make lint-fix

# Run type checking
make type

# Check documentation coverage
make doc

# Run tests
make test

# Run all checks
make all-checks
```

## Notes

- Most of the scripts in this directory are exempt from certain linting rules to allow for necessary system interactions.
- The scripts are designed to work with either Poetry or direct pip installation.
- These scripts automate many common tasks and ensure consistency across development environments.
