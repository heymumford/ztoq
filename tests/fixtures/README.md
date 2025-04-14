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

## Best Practices

1. **Use the right test level**: Match your test to the appropriate level in the pyramid
2. **One assert per test**: Focus each test on a single behavior
3. **Descriptive naming**: Name tests clearly to describe the behavior being tested
4. **Use fixtures**: Leverage fixtures for setup and teardown
5. **Use factories**: Create consistent test data with factories
6. **Test isolation**: Ensure tests don't depend on each other
7. **Keep tests focused**: Test one thing per test
8. **Mind performance**: Minimize slow operations in unit tests
