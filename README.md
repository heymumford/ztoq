# ZTOQ (Zephyr to qTest)

[![Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/yourusername/ztoq/main/docs/badges/test_results.json)](https://github.com/yourusername/ztoq/actions)
[![Unit Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/yourusername/ztoq/main/docs/badges/unit_tests.json)](https://github.com/yourusername/ztoq/actions)
[![Integration Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/yourusername/ztoq/main/docs/badges/integration_tests.json)](https://github.com/yourusername/ztoq/actions)
[![E2E Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/yourusername/ztoq/main/docs/badges/e2e_tests.json)](https://github.com/yourusername/ztoq/actions)

A Python CLI tool that extracts test data from Zephyr Scale and migrates it to qTest. This tool reads the Zephyr Scale OpenAPI specification and provides a complete migration pathway between these two test management systems.

## Test Pyramid

```
    ^^^^^^^^^^^^^^^^^^^^^    
    ^^^^ E2E Tests ^^^^^    
    ^^ 0/0 passed ^^^^^    
  /^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^/  
  ^^^^^^^ Integration Tests ^^^^^^^^^^^^^  
  ^^^^^^^^^ 0/3 passed ^^^^^^^^^^^^^^^^^  
///////////////////////////////////////////////////////////
/////////////// Unit Tests ////////////////////////////////
/////////////// 0/15 passed //////////////////////////////
============================================================
Total: 0/18 tests passed (18 failed, 0 skipped)
```

*Updated: 2025-04-13 21:30*

## Features

- Read and validate Zephyr Scale OpenAPI specification
- List available API endpoints
- Retrieve test cases, test cycles, and test plans
- Download test executions and results
- Export data to JSON or SQLite
- Support for projects, folders, statuses, priorities, and environments
- Handle pagination for large datasets
- Support for concurrent requests
- Export all test data across multiple projects
- Comprehensive request/response validation against OpenAPI schema
- Automatic test generation from OpenAPI specification
- Mock data generation for testing

## Project Structure

```
ztoq/
├── models.py         # Pydantic models for Zephyr data
├── openapi_parser.py # Parser for OpenAPI spec and API spec wrapper
├── zephyr_client.py  # Client for Zephyr Scale API
├── storage.py        # Storage adapters (JSON/SQLite)
├── exporter.py       # Data export orchestration
├── test_generator.py # Test case generator from OpenAPI spec
└── cli.py            # Typer CLI commands

tests/
├── unit/            # Unit tests
├── integration/     # Integration tests
└── generated/       # Auto-generated tests from OpenAPI spec

examples/
├── debug_example.py  # Example of using debug logging
└── generate_tests.py # Example of generating tests from OpenAPI spec

docs/
├── adr/             # Architecture Decision Records
├── c4-diagram.md    # C4 architecture diagrams
├── specs/           # API specifications
└── sphinx/          # Sphinx documentation source files
```

## Setup

```bash
# Install Poetry (if not already installed)
pip install poetry

# Install dependencies
poetry install
```

## Usage

### Validate OpenAPI Spec

```bash
# Validate the OpenAPI spec is for Zephyr Scale
poetry run ztoq validate z-openapi.yml
```

### List API Endpoints

```bash
# List all API endpoints in the spec
poetry run ztoq list-endpoints z-openapi.yml
```

### Get Projects

```bash
# Get all available projects
poetry run ztoq get-projects z-openapi.yml \
  --base-url https://api.atlassian.com/ex/jira/your-instance/rest/zephyr/1.0 \
  --api-token YOUR_TOKEN
```

### Get Test Cases

```bash
# Get test cases for a project
poetry run ztoq get-test-cases z-openapi.yml \
  --base-url https://api.atlassian.com/ex/jira/your-instance/rest/zephyr/1.0 \
  --api-token YOUR_TOKEN \
  --project-key PROJECT \
  --limit 100
```

### Get Test Cycles

```bash
# Get test cycles for a project
poetry run ztoq get-test-cycles z-openapi.yml \
  --base-url https://api.atlassian.com/ex/jira/your-instance/rest/zephyr/1.0 \
  --api-token YOUR_TOKEN \
  --project-key PROJECT
```

### Export All Test Data for a Project

```bash
# Export all test data for a single project
poetry run ztoq export-project z-openapi.yml \
  --base-url https://api.atlassian.com/ex/jira/your-instance/rest/zephyr/1.0 \
  --api-token YOUR_TOKEN \
  --project-key PROJECT \
  --output-dir ./zephyr-data \
  --format json
```

### Export All Test Data for Multiple Projects

```bash
# Export test data for all accessible projects
poetry run ztoq export-all z-openapi.yml \
  --base-url https://api.atlassian.com/ex/jira/your-instance/rest/zephyr/1.0 \
  --api-token YOUR_TOKEN \
  --output-dir ./zephyr-data \
  --format sqlite \
  --projects PROJECT1,PROJECT2
```

## Development

```bash
# Run all tests
poetry run pytest

# Run unit tests only
poetry run pytest -m unit

# Run integration tests only
poetry run pytest -m integration

# Run with coverage
poetry run pytest --cov=ztoq
```

### Debugging

The Zephyr client includes comprehensive logging for troubleshooting API interactions. You can enable DEBUG logging in three ways:

1. **Environment Variable**:
   ```bash
   # Set before running your script or application
   export ZTOQ_LOG_LEVEL=DEBUG
   ```

2. **Global Configuration**:
   ```python
   from ztoq.zephyr_client import configure_logging
   
   # Set to DEBUG, INFO, WARNING, ERROR, or CRITICAL
   configure_logging("DEBUG")
   ```

3. **Per-Client Configuration**:
   ```python
   from ztoq.zephyr_client import ZephyrClient
   from ztoq.models import ZephyrConfig
   
   config = ZephyrConfig(
       base_url="https://api.zephyrscale.smartbear.com/v2",
       api_token="your-api-token",
       project_key="PROJ"
   )
   
   # Create client with debug logging
   client = ZephyrClient(config, log_level="DEBUG")
   ```

See the `examples/debug_example.py` file for a complete example of debugging API interactions.

When DEBUG logging is enabled, you'll see detailed information about:
- API requests and responses
- API call timings
- Rate limiting information
- Full error details with context
- Pagination handling
- Schema validation results
- Request/response validation errors

The logs automatically redact sensitive information like API tokens.

### Using Makefile

```bash
# Setup project (install poetry and dependencies)
make setup

# Run tests
make test               # Run all tests
make test-unit          # Run unit tests only
make test-integration   # Run integration tests only
make test-cov           # Run tests with coverage

# Documentation
make docs               # Generate documentation
make docs-serve         # Generate and serve documentation
make test-with-docs     # Run tests and generate documentation

# Code quality
make format             # Format code with black
make lint               # Lint code with flake8

# Quick validation
make validate           # Validate OpenAPI spec
make list-endpoints     # List API endpoints in spec
```

### Using Build Scripts

```bash
# Run comprehensive build process
make build

# Run all build steps with original build script
python build.py all

# Run tests with documentation
python build.py test --with-docs

# Generate documentation only
python build.py docs

# Create a new commit with version update
make checkin message="Your commit message"
```

## Documentation

The project includes comprehensive documentation generated with Sphinx:

- **API Reference**: Automatically generated from docstrings
- **Architecture**: C4 diagrams and architectural overview
- **ADRs**: Architecture Decision Records for key design decisions
- **Usage Examples**: Command-line and Python API usage examples

To generate and view the documentation:

```bash
# Generate documentation
make docs

# Serve documentation locally
make docs-serve
```

Then visit http://localhost:8000 in your web browser.

For C4 diagrams, Lucidchart integration is available. See the "C4 Diagrams with Lucidchart" 
section in the documentation for instructions on creating and embedding C4 model diagrams.

## Additional Documentation

For more detailed information, see these documents in the `docs/` directory:

- [OpenAPI Integration](docs/openapi-integration.md)
- [Custom Fields and Attachments](docs/custom-fields-attachments.md)
- [qTest Migration Architecture](docs/qtest-migration-architecture.md)
- [Conversion Process](docs/conversion-process.md)
- [Entity Mapping](docs/entity-mapping.md)
- [Kanban Board](docs/kanban.md)
- [Maintenance Guide](docs/maintenance.md)
- [Documentation Contribution Guide](docs/docs-contribution-guide.md)
- [Test Strategy](docs/test-strategy.md)

All documentation follows the kebab-case naming convention for consistency and readability.

## Data Storage Options

### JSON Storage

By default, data is exported to JSON files organized by entity type:
- project.json
- test_cases.json
- test_cycles.json
- test_executions.json
- folders.json
- statuses.json
- priorities.json
- environments.json

### SQLite Storage

For relational storage, use the SQLite option with `--format sqlite`. This creates tables for each entity type with appropriate relationships.

## Object Hierarchy

The tool follows this object hierarchy based on the Zephyr Scale API:

```
PROJECT
│
├── Test Cases
│   ├── Test Case
│   │   ├── Test Script
│   │   ├── Test Steps
│   │   ├── Test Versions
│   │   └── Links (Issue/Web Links)
│   └── Custom Fields
│
├── Test Cycles
│   ├── Test Cycle
│   │   └── Links (Issue/Web Links)
│   └── Custom Fields
│
├── Test Plans
│   ├── Test Plan
│   │   └── Links (Issue/Web/Test Cycle Links)
│   └── Custom Fields
│
├── Test Executions
│   ├── Test Execution
│   │   ├── Test Steps
│   │   └── Links (Issue/Web Links)
│   └── Custom Fields
│
├── Folders
├── Statuses
├── Priorities
└── Environments
```