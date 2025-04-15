# Linting Issues and Code Quality Improvements

This document outlines the current linting issues and code quality improvements needed in the ZTOQ codebase.

## Recent Improvements

- Added `RecommendationHistory` model and corresponding database migration
- Enhanced API token diagnostics in `verify_api_tokens.py`
- Fixed unused imports in database optimization modules
- Updated flake8 configuration for better error handling
- Applied `black` formatting to the entire codebase for consistent style

## Remaining Linting Issues

The codebase still contains several types of linting issues that should be addressed:

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

## Recommended Next Steps

1. **Fix Unused Imports**:
   - Use the `scripts/fix_unused_imports.py` script to systematically remove unused imports
   - Update the script's `FILES_WITH_UNUSED_IMPORTS` dictionary with current findings

2. **Fix Undefined Names**:
   - Add missing imports in test files
   - Fix typos in variable names

3. **Fix Unused Variables**:
   - Remove unused variable assignments or use them where appropriate
   - Replace with `_` for intentionally ignored values

4. **Fix Line Length Issues**:
   - Break long lines into multiple lines
   - Consider factoring out complex expressions into separate variables
   - For strings, use multiple f-strings with line continuation

5. **Add to Pre-commit Hooks**:
   - Configure pre-commit hooks to automatically run black and flake8
   - Prevent commits with critical linting issues

## Running Linting Checks

To check for linting issues:

```bash
# Run critical linting checks only
./scripts/run_critical_lint.sh

# Run full linting checks
poetry run flake8 ztoq tests

# Format code with black
poetry run black ztoq tests
```

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](LICENSE)*
