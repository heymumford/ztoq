# API Mocking Harness

This directory contains the API mocking framework for ZTOQ, which provides tools for simulating API responses in tests without making real HTTP requests. This is particularly useful for testing the migration between Zephyr Scale and qTest.

## Overview

The API mocking harness provides:

- Simulated responses for Zephyr Scale and qTest APIs
- Tools for simulating network conditions, errors, and authentication
- Context managers for patching HTTP libraries
- FastAPI-based server for more realistic API simulation
- Fixtures for easy integration with pytest

## Files

- `api_harness.py` - The core mocking framework
- `conftest.py` - Pytest fixtures for easy test integration
- `test_api_harness_examples.py` - Examples demonstrating the harness
- `README.md` - This documentation file

## Getting Started

To use the API mocking harness in your tests, import the fixtures from the conftest.py file:

```python
from tests.fixtures.mocks.api_harness import (
    ZephyrAPIHarness,
    QTestAPIHarness,
    MockAPITestBase,
)

# For using fixtures
def test_with_mock_api(mock_zephyr_api):
    mock_zephyr_api.add_response(...)
    # Your test code here

# For using the base class
class TestWithMockAPI(MockAPITestBase):
    def test_zephyr_api(self, mock_zephyr_api):
        mock_zephyr_api.add_response(...)
        # Your test code here
```

## Key Components

### Base Classes

- `APIHarness` - Base harness with common mocking functionality
- `ZephyrAPIHarness` - Specialized for Zephyr Scale API
- `QTestAPIHarness` - Specialized for qTest API
- `MockAPITestBase` - Base test class with pre-configured harnesses
- `FastAPIHarness` - Server-based mocking with FastAPI

### Fixtures

- `mock_zephyr_api` - Mocked Zephyr API
- `mock_qtest_api` - Mocked qTest API
- `mock_both_apis` - Both APIs mocked together
- `api_server` - Running FastAPI server
- `mock_zephyr_client` - Client with mocked API
- `mock_qtest_client` - Client with mocked API
- `mock_both_clients` - Both clients with mocked APIs

## Documentation

For more detailed documentation on how to use the API mocking harness, please refer to:

- [API Mocking Guide](/docs/api-mocking-guide.md)
- [Example tests](/tests/fixtures/mocks/test_api_harness_examples.py)
- [Integration tests](/tests/integration/test_api_harness_integration.py)

## License

Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under MIT License
