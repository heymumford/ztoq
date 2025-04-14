# API Mocking Harness Guide

## Overview

The ZTOQ API Mocking Harness provides a flexible framework for simulating API responses in tests. It supports both the Zephyr Scale and qTest APIs, allowing for comprehensive testing of migration code without hitting real APIs.

This guide explains how to use the API mocking harness effectively in your tests.

## Key Components

The API mocking harness consists of several key components:

1. **Base Harness Classes**:
   - `APIHarness`: Base class with core mocking functionality
   - `ZephyrAPIHarness`: Specialized for Zephyr Scale API
   - `QTestAPIHarness`: Specialized for qTest API

2. **Context Managers**:
   - `mock_requests`: For patching the requests library
   - `mock_httpx`: For patching the httpx library (async)

3. **Test Base Classes**:
   - `MockAPITestBase`: Base class for test cases using the harnesses

4. **Server-based Mocking**:
   - `FastAPIHarness`: Runs an actual FastAPI server for more realistic tests

5. **Fixtures**:
   - Pytest fixtures for easily integrating with test suites

## Getting Started

### Basic Usage

The simplest way to use the harness is with the provided pytest fixtures:

```python
def test_zephyr_api(mock_zephyr_api):
    # Configure response
    mock_zephyr_api.add_response(
        "GET",
        "/projects",
        {
            "values": [
                {"id": "1001", "key": "DEMO", "name": "Demo Project"}
            ]
        }
    )

    # Create client
    config = ZephyrConfig(
        base_url="https://api.zephyrscale.example.com/v2",
        api_token="mock-token",
        project_key="DEMO"
    )
    client = ZephyrClient(config)

    # Call API
    projects = client.get_projects()

    # Verify results
    assert len(projects) == 1
    assert projects[0].key == "DEMO"
```

### Using the Test Base Class

For more control, extend the `MockAPITestBase` class:

```python
class TestAPIIntegration(MockAPITestBase):
    def test_multiple_apis(self, mock_both_apis):
        zephyr_harness, qtest_harness = mock_both_apis

        # Configure harnesses
        # ...

        # Create clients and make API calls
        # ...
```

### Using Context Managers

For more fine-grained control over the patching lifecycle:

```python
def test_with_context():
    harness = ZephyrAPIHarness()

    # Configure harness
    harness.add_response("GET", "/projects", {"values": [...]})

    with harness.mock_requests():
        # Make API calls within the context
        # ...
```

### Using the FastAPI Harness

For tests that need an actual running server:

```python
def test_with_server():
    harness = FastAPIHarness(port=8123)

    with harness.server_context():
        # Make real HTTP requests to the server
        response = requests.get(f"{harness.zephyr_url}/projects")
        # ...
```

## Key Features

### Configuring Responses

```python
# Add a successful response
harness.add_response(
    "GET",
    "/projects",
    {"values": [{"id": "1001", "key": "DEMO", "name": "Demo Project"}]},
    status_code=200  # Optional, defaults to 200
)

# Add an error response
harness.add_error_response(
    "GET",
    "/testcases",
    "Invalid project key",
    status_code=400
)
```

### Simulating Network Conditions

```python
# Set random error rate
harness.set_error_rate(0.2)  # 20% of requests will fail randomly

# Set network latency
harness.set_delay_range(0.1, 0.5)  # 100-500ms delays
```

### Authentication Simulation

```python
# Generate a token
token = harness.generate_token(ttl=3600)  # 1 hour TTL

# Validate a token
is_valid = harness.validate_token(token)
```

### Request Tracking

```python
# Get all requests
all_requests = harness.get_requests()

# Filter requests
get_requests = harness.get_requests(method="GET")
project_requests = harness.get_requests(path="/projects")
specific_requests = harness.get_requests(method="POST", path="/test-cases")
```

### Dynamic Response Handlers

For complex scenarios, you can replace the request handler:

```python
def custom_handler(method, path, params, data, headers, files):
    if method == "POST" and path == "/api/v3/projects/1/test-cases":
        return {"id": 1001, "name": "Custom Response"}, 201

    # Return None to fall back to configured responses
    return None, None

harness._handle_request = custom_handler
```

## Best Practices

1. **Reset Between Tests**:
   - Call `harness.reset()` between tests to clear configured responses and request history

2. **Use Descriptive Test Names**:
   - Name your tests clearly to indicate what API behavior they're testing

3. **Test Error Handling**:
   - Test both successful responses and error cases
   - Use `add_error_response()` and `set_error_rate()` to simulate failures

4. **Verify Request Details**:
   - Check that your code is making the expected requests with `get_requests()`

5. **Use Request History**:
   - Examine `harness.request_history` to debug test failures

6. **Test Edge Cases**:
   - Simulate rate limiting, timeouts, and auth failures
   - Test pagination and handling of large datasets

## Example Patterns

### Testing Migration Functions

```python
def test_migrate_test_case():
    # Set up both harnesses
    zephyr_harness = ZephyrAPIHarness()
    qtest_harness = QTestAPIHarness()

    with zephyr_harness.mock_requests(), qtest_harness.mock_requests():
        # Configure responses
        # ...

        # Call migration function
        migrate_test_case(zephyr_client, qtest_client, "DEMO-T1")

        # Verify correct API calls were made
        # ...
```

### Testing Error Recovery

```python
def test_retry_logic():
    harness = ZephyrAPIHarness()

    # Configure initial error, then success
    request_count = 0

    def conditional_response(method, path, params, data, headers, files):
        nonlocal request_count
        request_count += 1

        if request_count == 1:
            return {"error": "Rate limit exceeded"}, 429
        else:
            return {"values": [{"id": "1001", "name": "Project"}]}, 200

    harness._handle_request = conditional_response

    with harness.mock_requests():
        # Test code with retry logic
        # ...
```

### Performance Testing

```python
def test_api_performance():
    harness = ZephyrAPIHarness()

    # Configure various delay scenarios
    harness.set_delay_range(0.5, 1.0)  # Slow responses

    with harness.mock_requests():
        # Test performance handling code
        # ...
```

## Advanced Usage

### Custom Response Generation

```python
import random

def generate_test_cases(count):
    return [
        {
            "id": f"tc{i}",
            "key": f"DEMO-T{i}",
            "name": f"Test Case {i}",
            "status": random.choice(["Draft", "Ready", "Approved"])
        }
        for i in range(1, count + 1)
    ]

# Use in test
harness.add_response(
    "GET",
    "/testcases",
    {"values": generate_test_cases(50), "total": 50}
)
```

### Testing Pagination Handling

```python
# First page
harness.add_response(
    "GET",
    "/testcases",
    {
        "values": generate_test_cases(25),
        "total": 50,
        "startAt": 0,
        "maxResults": 25,
        "isLast": False
    }
)

# Custom handler for subsequent pages
def paginated_handler(method, path, params, data, headers, files):
    if method == "GET" and path == "/testcases" and params.get("startAt") == 25:
        return {
            "values": generate_test_cases(25, start=26),
            "total": 50,
            "startAt": 25,
            "maxResults": 25,
            "isLast": True
        }, 200
    return None, None

harness._handle_request = paginated_handler
```

## Troubleshooting

### Common Issues and Solutions

1. **Tests Hitting Real APIs**:
   - Ensure the mock is active: check that the context manager is properly set up
   - Verify URLs: the harness only mocks URLs that match the configured base URL

2. **Unexpected Response Data**:
   - Double-check response format: ensure it matches what the client expects
   - Verify endpoint paths: paths are case-sensitive

3. **Mocks Not Working with Authentication**:
   - Ensure the auth token response is properly configured
   - Check that your code is using the configured base URL

4. **Multiple Test Interference**:
   - Reset the harness between tests with `harness.reset()`
   - Use separate harness instances for independent tests

## Reference

### APIHarness Methods

- `add_response(method, path, response, status_code=200)`
- `add_error_response(method, path, error, status_code=400)`
- `set_error_rate(rate)` - 0.0 to 1.0
- `set_delay_range(min_delay, max_delay)` - in seconds
- `generate_token(ttl=3600)` - returns a mock token
- `validate_token(token)` - checks if token is valid
- `get_requests(method=None, path=None)` - filters request history
- `reset()` - clears all configuration
- `mock_requests()` - context manager for patching

### ZephyrAPIHarness Extras

- `configure_project(project_key, test_cases=10)` - sets up mock project

### QTestAPIHarness Extras

- `configure_project(project_id, test_cases=10)` - sets up mock project
- `create_test_run(project_id, test_case_id, test_cycle_id)` - creates a test run
- `submit_test_log(project_id, test_run_id, status)` - submits a test log

### FastAPIHarness Methods

- `start_server()` - starts the HTTP server
- `stop_server()` - stops the server
- `server_context()` - context manager for server lifecycle
- `base_url` - property with the server's URL
- `zephyr_url` - property with the Zephyr API URL
- `qtest_url` - property with the qTest API URL

## API-First Development and QA Empowerment

### The Importance of API Design Before Development

One of the most significant advantages of a robust API mocking framework is enabling an API-first development approach. By designing APIs and providing thorough documentation (such as OpenAPI/Swagger specs) to QA teams *before* implementation begins, organizations can dramatically improve their development process:

1. **Unblocking QA from Day One**: When QA has the ability to mock APIs based on Swagger documentation, they become unblocked from the development timeline. They can apply their test pyramid philosophy to code that doesn't even exist yet.

2. **Comprehensive Test Planning**: QA can perform pairwise modeling of parameters and values, identify critical path transactions with business or product owners, and strategically plan positive and negative test cases—all before a single line of production code is written.

3. **Value-Based Test Prioritization**: QA professionals can focus on determining which test cases are high-value (likely to catch bugs) versus which will likely never raise a bug, optimizing test effort allocation.

4. **Breaking Down Organizational Silos**: These conversations are often blocked in traditional development processes because QA may lack the technical capabilities to code such mocks, and development teams rarely have time to help.

### Crafting a More Technical QA Organization

Empowering QA teams with tools like this API mocking harness is essential for several reasons:

1. **Future of Open Source**: Technical QA teams that can fully utilize mocking frameworks contribute significantly to open source quality and adoption.

2. **Learning Efficient and Effective Coding/Testing**: A more technical QA approach bridges the gap between coding and testing, fostering a culture of quality from the earliest stages of development.

3. **Addressing Agentic AI in Software Engineering**: As AI tools become more prevalent in software development, QA teams with technical capabilities to create and maintain mocks will be better positioned to test AI-augmented or AI-generated code.

4. **Breaking Down the Developer-QA Divide**: When QA can create sophisticated mocks based on API documentation, they become true partners in the development process rather than gatekeepers at the end.

This API mocking harness isn't just a testing tool—it's an enabler for a fundamental shift in how development and QA teams collaborate. By providing QA with the capability to create sophisticated mocks, organizations can foster earlier collaboration, more comprehensive testing, and ultimately higher quality software.

## Conclusion

The API mocking harness is a powerful tool for testing API integrations without making real HTTP requests. It allows you to simulate various API responses, error conditions, and network behaviors, making your tests more reliable and comprehensive.

For more examples, see the test files in `tests/fixtures/mocks/test_api_harness_examples.py` and `tests/integration/test_api_harness_integration.py`.

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](LICENSE)*
