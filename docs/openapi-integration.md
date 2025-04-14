# OpenAPI Specification Integration

This document summarizes the implementation of the OpenAPI specification integration in ZTOQ.

## Components Added

1. **ZephyrApiSpecWrapper** class in `openapi_parser.py`
   - Provides utilities for working with the OpenAPI spec
   - Handles endpoint discovery and validation
   - Performs request/response schema validation
   - Provides parameter validation
   - Generates mock data for testing
   - Creates Pydantic models from schemas
   - Generates method signatures for endpoints

2. **Enhanced ZephyrClient** in `zephyr_client.py`
   - Updated the `_make_request` method to validate requests and responses
   - Added a `validate` parameter to allow disabling validation when needed
   - Enhanced path parameter extraction and validation
   - Improved error handling for validation failures
   - Extended logging to include validation results

3. **ZephyrTestGenerator** class in `test_generator.py`
   - Generates test cases from the OpenAPI spec
   - Creates happy path tests for each endpoint
   - Generates parameter validation tests
   - Creates response validation tests
   - Provides schema validation tests
   - Exports test suites to JSON format
   - Generates pytest files with test functions

4. **Examples and Documentation**
   - Added `generate_tests.py` example
   - Updated README.md with OpenAPI integration documentation
   - Created unit tests for the new components

## Benefits

This integration provides several benefits:

1. **Improved Validation**: All API requests and responses are validated against the OpenAPI schema, catching errors early.

2. **Enhanced Testing**: Automated test generation creates comprehensive test suites covering happy paths, validation, and error cases.

3. **Mock Data Generation**: Generate realistic test data from OpenAPI schemas for testing without hitting real APIs.

4. **Better Documentation**: Schema information provides better understanding of the API structure.

5. **Improved Development Workflow**: Schema validation helps catch issues during development.

## Usage Example

```python
# Using validation in the client
from pathlib import Path
from ztoq.models import ZephyrConfig
from ztoq.zephyr_client import ZephyrClient

config = ZephyrConfig(
    base_url="https://api.zephyrscale.smartbear.com/v2",
    api_token="your-api-token",
    project_key="PROJ"
)

# Create client with OpenAPI spec
client = ZephyrClient.from_openapi_spec(
    Path("docs/specs/z-openapi.yml"),
    config,
    log_level="DEBUG"
)

# Request and response will be validated automatically
test_cases = client.get_test_cases()

# Generating tests
from ztoq.test_generator import ZephyrTestGenerator

# Create test generator
test_gen = ZephyrTestGenerator.from_spec_path(Path("docs/specs/z-openapi.yml"))

# Generate tests for all endpoints
test_gen.generate_pytest_file(Path("tests/generated/test_api.py"))
```

## Further Improvements

Potential future enhancements:

1. Add a CLI command for test generation
2. Enhance mock data generation with more realistic values
3. Add support for security scheme validation
4. Implement more advanced schema validation
5. Generate JSON Schema files from OpenAPI schemas for external tools
6. Enhance schema resolution to handle complex references