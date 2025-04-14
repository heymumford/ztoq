# ZTOQ Test Framework

This directory contains the standardized testing framework for the ZTOQ project, implementing a clear test pyramid approach with fixtures and factories for each test level.

## Test Pyramid Structure

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

### Layers of Testing

1. **Unit Tests**: Test individual components in isolation
   - Fast execution (milliseconds)
   - High volume
   - Focus on singular functionality
   - Use mocks extensively
   - In `tests/unit/` directory

2. **Integration Tests**: Test interactions between components
   - Medium speed (seconds)
   - Medium volume
   - Focus on boundaries and contracts
   - Some real dependencies, some mocked
   - In `tests/integration/` directory

3. **System/E2E Tests**: Test complete flows
   - Slower execution (seconds to minutes)
   - Lower volume
   - Focus on business scenarios
   - Minimal mocking, uses real systems when possible
   - In `tests/system/` directory

## Fixtures Organization

Our fixtures are organized by test level and purpose:

- `base.py`: Core fixtures usable at all test levels
- `unit.py`: Fixtures specifically for unit tests
- `integration.py`: Fixtures for integration tests
- `system.py`: Fixtures for system/E2E tests
- `factories.py`: Test data factories for generating consistent test data
- `model_factories.py`: Factories for domain-specific models
- `database.py`: Database fixtures for all test levels
- `api_clients.py`: API client fixtures for all test levels
- `mocks/`: API mocking framework and fixtures

## Usage

### Markers

Use the appropriate markers to categorize your tests:

```python
@pytest.mark.unit
def test_something_small():
    # Unit test implementation

@pytest.mark.integration
def test_component_interaction():
    # Integration test implementation

@pytest.mark.system
def test_complete_flow():
    # System test implementation
```

Additional markers are available for specific test characteristics:
- `@pytest.mark.docker`: Tests requiring Docker
- `@pytest.mark.api`: Tests of API functionality
- `@pytest.mark.db`: Tests requiring database access
- `@pytest.mark.cli`: Tests of CLI functionality
- `@pytest.mark.slow`: Tests that are particularly time-consuming

### Core Fixtures

Every test can access these basic fixtures:

```python
def test_with_fixtures(
    mock_env_vars,    # Mock environment variables
    temp_dir,         # Temporary directory
    temp_file,        # Temporary file
    temp_db_path      # Path for a temporary database
):
    # Test implementation
```

### Database Fixtures

Database fixtures are available for different testing scenarios:

```python
@pytest.mark.unit
def test_with_mock_database(mock_sqlalchemy_session):
    # Mock session for unit testing without actual database access
    mock_sqlalchemy_session.query.return_value.all.return_value = []
    # Test implementation

@pytest.mark.integration
def test_with_in_memory_database(sqlalchemy_memory_session, populate_test_db):
    # Real in-memory SQLite database for integration testing
    populate_test_db(sqlalchemy_memory_session)
    result = sqlalchemy_memory_session.execute("SELECT * FROM Project").fetchall()
    # Test implementation

@pytest.mark.integration
def test_with_file_database(sqlalchemy_file_session):
    # Real file-based SQLite database for persistent testing
    # Test implementation

@pytest.mark.integration
def test_with_transaction(transaction_fixture):
    # Testing database transactions with automatic rollback
    session, savepoint = transaction_fixture
    # Test implementation with transaction support

@pytest.mark.integration
def test_concurrent_operations(concurrent_sessions):
    # Testing concurrent database operations
    session1, session2, session3 = concurrent_sessions
    # Test implementation with multiple sessions
```

### API Client Fixtures

API client fixtures for testing with external APIs:

```python
@pytest.mark.unit
def test_with_mock_clients(mock_zephyr_client, mock_qtest_client):
    # Simple mock clients for unit testing
    mock_zephyr_client.get_test_cases.return_value = []
    # Test implementation

@pytest.mark.integration
def test_with_patched_clients(patch_zephyr_client, patch_qtest_client):
    # Patching the client classes for tests that create their own instances
    from ztoq.zephyr_client import ZephyrClient
    client = ZephyrClient(config)
    # Test implementation

@pytest.mark.integration
def test_with_mock_api(zephyr_client_with_mock_api, qtest_client_with_mock_api):
    # Real clients with mocked API responses for integration testing
    projects = zephyr_client_with_mock_api.get_projects()
    # Test implementation

@pytest.mark.integration
def test_with_api_harness(mock_zephyr_api, mock_qtest_api):
    # Direct access to the API mocking harness for custom responses
    mock_zephyr_api.add_response("GET", "/projects", {"values": []})
    # Test implementation
```

### API Mocking Harness

The API mocking harness provides sophisticated API simulation:

```python
@pytest.mark.integration
def test_with_api_harness(mock_zephyr_api):
    # Configure the harness
    mock_zephyr_api.add_response(
        "GET",
        "/projects",
        {"values": [{"id": "1", "key": "TEST"}]}
    )

    # Configure network conditions (optional)
    mock_zephyr_api.set_delay(100)  # 100ms delay
    mock_zephyr_api.set_error_rate(0.1)  # 10% error rate

    # Use a real client with the mock API
    client = ZephyrClient(config)
    projects = client.get_projects()

    # Inspect captured requests
    requests = mock_zephyr_api.get_requests()
    assert len(requests) == 1
    assert requests[0].method == "GET"
    assert requests[0].url.endswith("/projects")
```

### Factories

Use factories to create test data consistently:

```python
from tests.fixtures.factories import ModelFactory

# Creating a custom factory
class UserFactory(ModelFactory):
    MODEL_CLASS = User
    DEFAULTS = {
        "username": lambda: f"user_{BaseFactory.random_string(8)}",
        "email": lambda: f"{BaseFactory.random_string(8)}@example.com",
        "is_active": lambda: True
    }

# Using the factory in tests
def test_with_factory():
    # Create a single user
    user = UserFactory.create()

    # Create a user with specific attributes
    admin = UserFactory.create(is_admin=True)

    # Create a batch of users
    users = UserFactory.create_batch(5)
```

### Model-Specific Factories

Domain-specific model factories are available:

```python
def test_with_domain_factories():
    # Create Zephyr models
    project = ProjectFactory.create()
    test_case = TestCaseFactory.create(folder=project.id)
    test_case_with_steps = TestCaseFactory.create_with_steps(step_count=3)

    # Create qTest models
    qtest_project = QTestProjectFactory.create()
    qtest_test_case = QTestTestCaseFactory.create(project_id=qtest_project.id)
```

## Examples and Guides

Complete examples of fixture usage are available in:

- `tests/fixtures/test_fixtures_example.py`: General fixture examples
- `tests/unit/test_fixtures_example.py`: Unit testing examples
- `tests/integration/test_fixtures_example.py`: Integration testing examples
- `tests/system/test_fixtures_example.py`: System testing examples
- `tests/fixtures/mocks/test_api_harness_examples.py`: API mocking examples

## Best Practices

1. **Use the right test level**: Match your test to the appropriate level in the pyramid
2. **One assert per test**: Focus each test on a single behavior
3. **Descriptive naming**: Name tests clearly to describe the behavior being tested
4. **Use fixtures**: Leverage fixtures for setup and teardown
5. **Use factories**: Create consistent test data with factories
6. **Test isolation**: Ensure tests don't depend on each other
7. **Keep tests focused**: Test one thing per test
8. **Mind performance**: Minimize slow operations in unit tests
9. **Mock external systems**: Use the API mocking harness for external dependencies
10. **Use transactions**: Leverage transaction fixtures for database state isolation
