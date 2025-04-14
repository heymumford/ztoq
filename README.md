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
- Export data to JSON, SQLite or SQL database (PostgreSQL/SQLite with canonical schema)
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
├── storage.py        # Storage adapters (JSON/SQLite/Canonical SQL)
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
  --format sql \  # Options: json, sqlite, sql
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

### Design Philosophy

ZTOQ follows a set of strategic design preferences that guide our implementation decisions. Rather than viewing technical choices as strictly right or wrong, we acknowledge that software design often involves trade-offs and context-specific decisions.

Our key design preferences include:

- **Type Safety**: Prefer strong typing and validation over dynamic types
- **Explicitness**: Prefer explicit configuration over implicit defaults
- **Composition**: Prefer composition over inheritance
- **Test-Driven**: Prefer writing tests before or alongside implementation
- **Immutability**: Prefer immutable data structures where possible
- **Scalability**: Prefer batch processing over individual record handling
- **Reliability**: Prefer fine-grained error handling over generic exceptions
- **Antifragility**: Design systems that gain from disorder and uncertainty

For the complete list of strategic preferences, see [ADR-015: Strategic Design Preferences](docs/adr/015-strategic-design-preferences.md) and [ADR-016: Antifragile and Black Swan Design Principles](docs/adr/016-anti-fragile-and-black-swan-concepts.md).

### CLI Database Commands

The tool provides dedicated database commands for working with the canonical SQL schema:

```bash
# Initialize the database schema
poetry run ztoq db init --db-type sqlite

# Show database statistics for a project
poetry run ztoq db stats --project-key PROJECT

# Run pending database migrations
poetry run ztoq db migrate

# Use PostgreSQL database (recommended for production)
poetry run ztoq db init --db-type postgresql \
  --host localhost --port 5432 \
  --username ztoq_user --password password \
  --database ztoq_db
```

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

### SQL Database Storage

For robust relational storage, the tool offers two SQL approaches:

1. **Simple SQLite Storage**: Use the `--format sqlite` option for a basic relational database with all entity types.

2. **Canonical SQL Schema**: Use the `--format sql` option to use a standardized canonical schema that works with both PostgreSQL and SQLite:

```sql
-- Key tables in the canonical schema
CREATE TABLE Project (
    project_id VARCHAR PRIMARY KEY,
    project_key VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE TestCase (
    test_case_id BIGINT PRIMARY KEY,
    project_id VARCHAR REFERENCES Project(project_id),
    folder_id BIGINT REFERENCES Folder(folder_id),
    key VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    -- Additional fields...
);

CREATE TABLE CustomField (
    custom_field_id SERIAL PRIMARY KEY,
    object_type VARCHAR CHECK(object_type IN ('TestCase', 'TestCycle', 'TestExecution')),
    object_id BIGINT NOT NULL,
    field_name VARCHAR NOT NULL,
    field_value TEXT,
    UNIQUE(object_type, object_id, field_name)
);
```

The canonical schema provides:
- Compatibility with both Zephyr and qTest data models
- Optimized database design with proper indexes
- Connection pooling for high performance
- Future compatibility with Snowflake data warehouse

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

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](LICENSE)*