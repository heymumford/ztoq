# ZTOQ Test Pyramid Guidelines

This document provides guidelines for organizing and writing tests according to the test pyramid approach in the ZTOQ project.

## Test Pyramid Structure

```
    /\
   /  \
  /    \        System Tests (E2E)
 /      \       (Few, complex, slow)
/--------\
/          \
/ Integration \  Integration Tests
/--------------\ (More, component interactions)
/                \
/      Unit       \ Unit Tests
/------------------\ (Many, fast, isolated)
```

## Test Levels

### 1. Unit Tests (`tests/unit/`)

Unit tests focus on testing individual components in isolation. These are fast, focused tests that should make up the majority of your test suite.

**Characteristics:**
- Tests a single component or function in isolation
- Mocks or stubs all dependencies
- Fast execution (should run in milliseconds)
- No external dependencies (database, API, filesystem, etc.)
- One clear assertion or set of related assertions

**Examples:**
- Testing an individual function's logic
- Testing a class method in isolation
- Testing validation rules
- Testing utility functions

**Guidelines:**
- Always mark with `@pytest.mark.unit`
- Use dependency injection to make mocking easier
- Use fixtures from `tests/fixtures/unit.py`
- Don't access real external services
- Keep tests small and focused

**Sample Unit Test:**
```python
@pytest.mark.unit
def test_validate_project_key():
    """Test that project key validation works correctly."""
    # Valid key
    assert validate_project_key("PROJ-123") is True

    # Invalid keys
    assert validate_project_key("proj-123") is False  # Lowercase
    assert validate_project_key("PROJ 123") is False  # Space
    assert validate_project_key("") is False  # Empty
```

### 2. Integration Tests (`tests/integration/`)

Integration tests focus on testing how components interact with each other. They verify that the interfaces between components work correctly.

**Characteristics:**
- Tests interaction between two or more components
- May use real dependencies or controlled test doubles
- Medium execution speed (milliseconds to seconds)
- Limited external dependencies (may use test databases)
- Verifies behavior at component boundaries

**Examples:**
- Testing API client with mock server
- Testing database operations with test database
- Testing service class that coordinates multiple components
- Testing CLI commands that coordinate multiple services

**Guidelines:**
- Always mark with `@pytest.mark.integration`
- Use fixtures from `tests/fixtures/integration.py`
- Use mocks for external services where appropriate
- Use in-memory databases for database tests
- Additional markers may apply (`@pytest.mark.db`, `@pytest.mark.api`)

**Sample Integration Test:**
```python
@pytest.mark.integration
@pytest.mark.db
def test_store_and_retrieve_project(sqlalchemy_memory_session):
    """Test storing and retrieving a project from the database."""
    # Create and save a project
    project = Project(id="PROJ-1", key="PROJ1", name="Test Project")
    sqlalchemy_memory_session.add(project)
    sqlalchemy_memory_session.commit()

    # Retrieve the project and verify
    retrieved = sqlalchemy_memory_session.query(Project).filter_by(id="PROJ-1").first()
    assert retrieved is not None
    assert retrieved.key == "PROJ1"
    assert retrieved.name == "Test Project"
```

### 3. System Tests (`tests/system/`)

System tests (also called E2E tests) focus on testing complete workflows from end to end. They verify that the entire system works correctly from a user's perspective.

**Characteristics:**
- Tests complete workflows across the entire system
- Uses real components where possible
- Slow execution (seconds to minutes)
- May interact with external services
- Focuses on user-facing functionality

**Examples:**
- Testing a complete migration process
- Testing CLI commands that perform multi-step operations
- Testing application startup and configuration
- Testing Docker container deployment

**Guidelines:**
- Always mark with `@pytest.mark.system`
- Use fixtures from `tests/fixtures/system.py`
- Mock external services only when necessary
- Additional markers likely apply (`@pytest.mark.slow`, `@pytest.mark.docker`)
- Focus on real-world user scenarios

**Sample System Test:**
```python
@pytest.mark.system
@pytest.mark.slow
@pytest.mark.docker
def test_full_migration_process(docker_compose_env, cli_runner):
    """Test a full migration process from start to finish."""
    # Set up environment
    config_path = docker_compose_env["dir"] / "migration.yaml"
    create_test_config(config_path)

    # Run the migration command
    result = run_cli_command(["ztoq", "migrate", "--config", str(config_path)])

    # Verify results
    assert result["successful"] is True
    assert "Migration completed successfully" in result["stdout"]

    # Verify data was migrated correctly
    # ... additional verification logic
```

## Test Categories (Markers)

In addition to the pyramid levels, we use these markers to categorize tests by functionality:

1. `@pytest.mark.db`: Tests that interact with databases
2. `@pytest.mark.api`: Tests that interact with APIs
3. `@pytest.mark.cli`: Tests that interact with the command-line interface
4. `@pytest.mark.docker`: Tests that require Docker to run
5. `@pytest.mark.slow`: Tests that take significantly longer than average to run

## File Organization

```
tests/
├── fixtures/               # Test fixtures and factories
│   ├── base.py             # Base fixtures for all test levels
│   ├── unit.py             # Unit test fixtures
│   ├── integration.py      # Integration test fixtures
│   ├── system.py           # System test fixtures
│   ├── factories.py        # Base factory classes
│   ├── model_factories.py  # Model-specific factories
│   ├── database.py         # Database fixtures
│   ├── api_clients.py      # API client fixtures
│   └── mocks/              # Mock services and API harness
│
├── unit/                   # Unit tests
│   ├── test_module_a.py    # Unit tests for module A
│   ├── test_module_b.py    # Unit tests for module B
│   └── ...
│
├── integration/            # Integration tests
│   ├── test_feature_x.py   # Integration tests for feature X
│   ├── test_feature_y.py   # Integration tests for feature Y
│   └── ...
│
├── system/                 # System/E2E tests
│   ├── test_workflow_1.py  # System test for workflow 1
│   ├── test_workflow_2.py  # System test for workflow 2
│   └── ...
│
└── conftest.py             # Global pytest configuration
```

## Best Practices

1. **File Organization**: Name test files according to what they test (e.g., `test_user_service.py` for `user_service.py`)

2. **Function Names**: Use descriptive names that clearly communicate what's being tested (e.g., `test_user_creation_with_valid_data`)

3. **Arrange-Act-Assert**: Structure your tests with clear sections:
   - Arrange: Set up the test data and context
   - Act: Perform the operation being tested
   - Assert: Verify the results

4. **Test Independence**: Each test should be able to run independently without relying on other tests

5. **Use Fixtures**: Leverage pytest fixtures for clean setup and teardown

6. **Mock External Services**: Don't rely on external services in unit and most integration tests

7. **Descriptive Assertions**: Use descriptive assertion messages to explain failures

8. **Use Factories**: Use the provided factories to generate consistent test data

9. **Test Edge Cases**: Include tests for error conditions and edge cases

10. **Follow TDD**: Write tests before implementing features when possible

## Running Tests

### By Level
```bash
# Unit tests only
poetry run pytest -m unit

# Integration tests only
poetry run pytest -m integration

# System tests only
poetry run pytest -m system
```

### By Category
```bash
# Database tests
poetry run pytest -m db

# API tests
poetry run pytest -m api

# Tests requiring Docker
poetry run pytest -m docker
```

### Excluding Slow Tests
```bash
# Run all tests except slow ones
poetry run pytest -k "not slow"
```

### Combining Markers
```bash
# Run all unit tests related to the database
poetry run pytest -m "unit and db"

# Run all API tests that aren't slow
poetry run pytest -m "api and not slow"
```

## Example Tests

For examples of how to use the test fixtures and factories, refer to:
- `tests/unit/test_fixtures_example.py`
- `tests/integration/test_fixtures_example.py`
- `tests/system/test_fixtures_example.py`

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](../LICENSE)*
