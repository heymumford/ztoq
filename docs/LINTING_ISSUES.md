# ZTOQ Linting Guide

This document outlines the linting configuration and common issues that need to be addressed in the codebase.

## Linting Setup

The project uses several linting and code quality tools:

1. **Ruff** - Fast Python linter that includes flake8, isort, pyupgrade and more
2. **mypy** - Static type checking 
3. **docformatter** - Format docstrings consistently
4. **interrogate** - Check docstring coverage 
5. **bandit** - Security linting
6. **pre-commit** - Run checks before commits

Configuration is primarily in:
- `pyproject.toml` - Main configuration file
- `.pre-commit-config.yaml` - Pre-commit hooks configuration
- `config/setup.cfg` - Supplementary flake8 configuration

## Running Linters

```bash
# Run all linters via pre-commit
poetry run pre-commit run --all-files

# Run just Ruff (fixes issues automatically with --fix)
poetry run ruff check --fix ztoq/

# Run type checking
poetry run mypy ztoq/

# Check docstring coverage
poetry run interrogate -c pyproject.toml ztoq/

# Format docstrings
poetry run docformatter --in-place --config ./pyproject.toml ztoq/

# Check for security issues
poetry run bandit -c pyproject.toml -r ztoq/
```

## Common Issues

### 1. Type Annotations

We're using mypy for type checking. Common issues are:

- Missing function return types (`ANN201` for public functions, `ANN202` for private)
- Missing parameter types (`ANN001` for regular params, `ANN002` for `*args`, `ANN003` for `**kwargs`)
- No need to annotate `self` or `cls` (we ignore `ANN101` and `ANN102`)

Example fix:
```python
# Before
def process_data(data, extra=None):
    return data

# After
from typing import Any, Dict, Optional

def process_data(data: Dict[str, Any], extra: Optional[str] = None) -> Dict[str, Any]:
    return data
```

### 2. Docstrings

We use Google-style docstrings. Common issues:

- Missing docstrings for classes, methods, functions (`D101`, `D102`, `D103`)
- Missing docstrings for `__init__` methods (`D107`) 
- First line should be imperative mood (`D401`)
- Need blank line between summary and description (`D205`)

Example fix:
```python
# Before
def transform_data(data):
    """This function transforms the data.
    It applies several processing steps."""
    return data

# After
def transform_data(data: dict) -> dict:
    """Transform the data.
    
    It applies several processing steps.
    
    Args:
        data: The data to transform
        
    Returns:
        The transformed data
    """
    return data
```

### 3. Code Complexity

- Functions with too many branches or too complex control flow (`C901`)
- Functions with too many parameters
- Too many nested blocks

### 4. Naming

- Function/method names shadowing built-ins (`A003`)
- Using variable names that are too short or not descriptive

### 5. Import Order

We use isort with a Black-compatible profile for import sorting. Imports should be in this order:
1. Standard library  
2. Third-party libraries
3. ZTOQ modules

## Ignored Rules

We've ignored some rules where appropriate:

- `E501` - Line length (handled by Black/Ruff formatter)
- `S101` - Use of assert (acceptable in test files)
- `E402` - Module level import not at top of file (for imports after license headers)
- Various docstring rules that docformatter handles

## Previous Linting Issues

The following issues have been previously identified:

### Unused Imports (F401)

Many files have unused imports that should be removed, including:

- `ztoq/batch_strategies.py`
- `ztoq/cli.py`
- `ztoq/custom_field_mapping.py`
- `ztoq/data_comparison.py`
- `ztoq/entity_mapping.py`
- `ztoq/zephyr_mock_server.py`

### Undefined Names (F821)

There are undefined names in several test files:

- `tests/integration/test_db_error_handling.py` - undefined name 'sessionmaker', 'scoped_session'
- `tests/unit/test_db_storage_operations.py` - undefined name 'CustomFieldDefinition'
- `tests/unit/test_migration_etl.py` - undefined name 'ANY'
- `tests/unit/test_work_queue.py` - undefined name 'os'

### Unused Local Variables (F841)

Several files have variables that are assigned but never used:

- `ztoq/cli.py` - 'db_config' assigned but never used
- `tests/fixtures/mocks/test_api_harness_examples.py` - unused variables ('config', 'zephyr_client', 'qtest_client')
- `tests/integration/test_migration_system_workflow.py` - multiple instances of 'test_env' and 'result' variables

### Line Too Long (E501)

Many files have lines exceeding the 100-character limit, including:

- `ztoq/batch_strategies.py`
- `ztoq/core/db_models.py`
- `ztoq/custom_field_mapping.py`
- `ztoq/data_comparison.py`
- `ztoq/database_factory.py`
- `ztoq/database_manager.py`
- `ztoq/entity_mapping.py`
- `ztoq/migration.py`
- `ztoq/zephyr_mock_server.py`

## Per-file Exceptions

We have special exceptions for certain files:

- Test files ignore many docstring and annotation rules
- Example files allow prints and missing annotations
- CLI files allow print statements
- Script files have relaxed linting

## Migration Strategy

When fixing linting issues:

1. Start with files that are actively being modified
2. Focus on new code to ensure it meets standards
3. Fix existing code incrementally when touching those files
4. Prioritize type annotations and docstrings for public interfaces

## Running All Quality Checks

To run all quality checks before a PR:

```bash
# In project root
cd path/to/ztoq
make validate-all
```

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](LICENSE)*