# ZTOQ Testing Framework

This directory contains the testing framework for the ZTOQ project, organized according to the test pyramid approach.

## Directory Structure

```
tests/
├── fixtures/               # Test fixtures and factories
│   ├── base.py             # Base fixtures for all test levels
│   ├── factories.py        # Base factory classes
│   ├── integration.py      # Integration test fixtures
│   ├── model_factories.py  # Model-specific factories
│   ├── system.py           # System test fixtures
│   └── unit.py             # Unit test fixtures
│
├── unit/                   # Unit tests (fast, isolated)
│   ├── test_module_1.py
│   ├── test_module_2.py
│   └── ...
│
├── integration/            # Integration tests (component interactions)
│   ├── test_module_1.py
│   ├── test_module_2.py
│   └── ...
│
├── system/                 # System/E2E tests (full workflows)
│   ├── test_workflow_1.py
│   ├── test_workflow_2.py
│   └── ...
│
└── conftest.py             # Global pytest configuration
```

## Test Pyramid

Our testing follows the standard test pyramid approach:

```
    /\
   /  \
  /    \        Few E2E tests
 / E2E  \       (slow, complex, but test complete flows)
/--------\
/          \
/ Integration \  More integration tests
/--------------\ (test component interactions)
/                \
/      Unit       \ Many unit tests
/------------------\ (fast, focused, isolated)
```

## Running Tests

### Run All Tests

```bash
poetry run pytest
```

### Run Tests by Level

```bash
# Unit tests
poetry run pytest -m unit

# Integration tests
poetry run pytest -m integration

# System tests
poetry run pytest -m system
```

### Run Tests by Category

```bash
# Docker-related tests
poetry run pytest -m docker

# API tests
poetry run pytest -m api

# Database tests
poetry run pytest -m db

# CLI tests
poetry run pytest -m cli
```

### Skip Slow Tests

```bash
poetry run pytest -k "not slow"
```

## Writing Tests

For examples of how to use the test fixtures and factories, refer to the example test files:

- `tests/unit/test_fixtures_example.py`
- `tests/integration/test_fixtures_example.py`
- `tests/system/test_fixtures_example.py`

For more details on the available fixtures and factories, see the documentation in the `tests/fixtures/` directory.
