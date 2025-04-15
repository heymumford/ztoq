# Acceptance Tests

This directory contains acceptance tests for the ZTOQ CLI commands and workflows. These tests verify that CLI commands function correctly with expected inputs and outputs.

## Structure

- `conftest.py` - Contains test fixtures used across all acceptance tests
- `test_cli_commands.py` - Tests for the main CLI commands defined in `ztoq/cli.py`
- `test_workflow_cli.py` - Tests for the workflow CLI commands defined in `ztoq/workflow_cli.py`

## Running the Tests

You can run these tests specifically with:

```bash
poetry run pytest tests/acceptance/ -v
```

Or you can use the acceptance test marker:

```bash
poetry run pytest -m acceptance -v
```

## Test Coverage

These tests cover:

1. Main CLI commands:
   - Version and help commands
   - Validation and listing OpenAPI endpoints
   - Project and entity retrieval commands
   - Export functionality
   - Database operations
   - Migration operations

2. Workflow CLI commands:
   - Running and resuming workflows
   - Status checking and reporting
   - Cleanup operations
   - Transform, validate, and load operations

These tests use mocking to simulate interactions with external systems like Zephyr and qTest APIs.

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](../../../LICENSE)*