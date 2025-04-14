# ZTOQ (Zephyr to qTest)

![Tests](https://img.shields.io/badge/tests-passing-brightgreen)
![Unit Tests](https://img.shields.io/badge/unit%20tests-passing-brightgreen)
![Integration Tests](https://img.shields.io/badge/integration%20tests-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-88%25-green)

> [!NOTE]
> This project follows a standard organization structure with:
> - `config/` - Configuration files (Dockerfiles, docker-compose, ini, config)
> - `docs/` - Documentation files
> - `utils/` - Utility scripts and tools
> - See [Project Structure](docs/project-structure.md) for details.

A Python CLI tool that extracts test data from Zephyr Scale and migrates it to qTest. This tool reads the Zephyr Scale OpenAPI specification and provides a complete migration pathway between these two test management systems.

## API Access Configuration

This tool requires authentication with both Zephyr Scale and qTest APIs. API tokens are securely managed through environment variables:

- **Zephyr Scale**: Set the `zephyr_access_token` environment variable with your Zephyr API token.
- **qTest**: Set the `qtest_bearer_token` environment variable with your qTest bearer token.

You can verify your API tokens using the provided example script:

```bash
# First, set your API tokens in your environment
export zephyr_access_token="your_zephyr_token"
export qtest_bearer_token="your_qtest_token"

# Then run the verification script
python examples/verify_api_tokens.py
```

For detailed instructions on obtaining and configuring API tokens, see the [API Tokens Configuration Guide](docs/api-tokens.md).

## Test Coverage

```
Test Type       | Count | Passing | Coverage
--------------- | ----- | ------- | --------
Unit Tests      | 40    | 40      | 92%
Integration     | 3     | 3       | 75%
E2E Tests       | 2     | 2       | 80%
--------------- | ----- | ------- | --------
Total           | 45    | 45      | 88%
```

*Updated: 2025-04-14*

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
- Complete ETL migration pipeline from Zephyr Scale to qTest
- Batch processing and parallel operations for large migrations
- Resumable migration with state tracking
- Attachment handling for complete data migration

## Project Structure

```
ztoq/
├── models.py         # Pydantic models for Zephyr data
├── qtest_models.py   # Pydantic models for qTest data
├── openapi_parser.py # Parser for OpenAPI spec and API spec wrapper
├── zephyr_client.py  # Client for Zephyr Scale API
├── qtest_client.py   # Client for qTest API
├── storage.py        # Storage adapters (JSON/SQLite/Canonical SQL)
├── exporter.py       # Data export orchestration
├── migration.py      # ETL migration from Zephyr to qTest
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

### Migrate from Zephyr Scale to qTest

```bash
# Run a complete migration from Zephyr Scale to qTest
poetry run ztoq migrate run \
  --zephyr-base-url https://api.atlassian.com/ex/jira/your-instance/rest/zephyr/1.0 \
  --zephyr-api-token YOUR_ZEPHYR_TOKEN \
  --zephyr-project-key PROJECT \
  --qtest-base-url https://yourcompany.qtestnet.com \
  --qtest-username YOUR_USERNAME \
  --qtest-password YOUR_PASSWORD \
  --qtest-project-id 12345 \
  --db-type sqlite \
  --db-path ./migration.db

# Check migration status
poetry run ztoq migrate status \
  --db-type sqlite \
  --db-path ./migration.db \
  --project-key PROJECT
```

For detailed migration instructions, see the [Migration Guide](docs/migration-guide.md).

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
make format             # Format code with ruff and isort
make lint               # Run linters (ruff, mypy, pylint)
make security           # Run security checks (bandit, safety)
make pre-commit         # Run pre-commit hooks on all files
make validate-all       # Run format, lint, test, and security checks

# Docker
make docker-build       # Build Docker container
make docker-run         # Run application in Docker

# Quick validation
make validate           # Validate OpenAPI spec
make list-endpoints     # List API endpoints in spec
```

## Quality Gates

ZTOQ implements comprehensive quality checks to ensure code quality, security, and reliability:

### Linters and Formatters

- **Ruff**: Fast Python linter combining multiple tools
- **Black**: Code formatter for consistent style
- **isort**: Import sorter to organize imports
- **mypy**: Static type checker for Python
- **pylint**: Python code analysis tool

### Security

- **Bandit**: Security linter for Python code
- **Safety**: Dependency vulnerability scanner
- **Trivy**: Container vulnerability scanner
- **SonarCloud**: Continuous code quality scanner

### Documentation

- **docformatter**: Formats Python docstrings
- **interrogate**: Measures docstring coverage
- **Sphinx**: Documentation generator

### Testing

- **pytest**: Testing framework
- **pytest-cov**: Test coverage measurement
- **pytest-benchmark**: Performance testing

### CI/CD Integration

- **GitHub Actions**: Automated quality gates and security scanning
  - Quality Gates workflow (linting, testing, security checks, SonarCloud analysis)
  - Container Security Scan workflow (Trivy vulnerability scanning)
  - Scheduled weekly security scans with automatic issue creation
- **pre-commit**: Git hooks for code quality
- **Dependabot**: Automated dependency updates for Python, GitHub Actions, and Docker

### Running Quality Checks

Run a comprehensive quality check with:

```bash
make validate-all
```

Or run individual checks:

```bash
# Code formatting
make format

# Static analysis
make lint

# Security checks
make security

# Run all pre-commit hooks
make pre-commit
```

### Docker Support

ZTOQ includes Docker support for containerized deployment:

#### General Docker Support

```bash
# Build the Docker image
make docker-build

# Run the application in Docker
make docker-run

# Run with Docker Compose (includes PostgreSQL)
docker-compose up
```

#### Docker Migration Support

For running migrations in a containerized environment, ZTOQ provides a specialized Docker Compose setup:

```bash
# Set up the migration environment (creates directories and initializes DB)
./run-migration.sh setup

# Run a migration with default settings
./run-migration.sh run

# Run a migration with custom batch size and workers
./run-migration.sh run --batch-size 100 --workers 8 --phase extract

# Check migration status
./run-migration.sh status

# Generate a migration report
./run-migration.sh report

# Start an interactive migration dashboard
./run-migration.sh dashboard

# Stop all containers
./run-migration.sh stop

# Clean up containers and networks (keeps data)
./run-migration.sh clean

# Clean up everything including data
./run-migration.sh purge
```

This approach simplifies the migration process by handling all dependencies and configurations automatically. See the [Migration Guide](docs/migration-guide.md#using-docker-for-migration) for detailed instructions.

#### CI/CD Migration Support

ZTOQ can be integrated into CI/CD pipelines for automated and scheduled migrations:

```yaml
# GitHub Actions workflow for scheduled migrations
name: Scheduled Migration

on:
  schedule:
    - cron: '0 2 * * *'  # Run daily at 2:00 AM UTC
  workflow_dispatch:     # Allow manual triggering
```

Features include:
- Scheduled migrations (daily, weekly, monthly)
- Multi-project migration sequencing
- Email and Slack notifications
- Detailed HTML reports with visualizations
- Resume capability for interrupted migrations

See [Scheduled Migrations](docs/scheduled-migrations.md) for comprehensive documentation on CI/CD integration.

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

- [Migration Guide](docs/migration-guide.md) - Complete migration workflow and instructions
- [Database Configuration](docs/database-configuration.md) - Database setup and optimization
- [Workflow Orchestration](docs/workflow-orchestration.md) - Advanced orchestration techniques
- [OpenAPI Integration](docs/openapi-integration.md) - Working with OpenAPI specifications
- [Custom Fields and Attachments](docs/custom-fields-attachments.md) - Handling custom data
- [Entity Mapping](docs/entity-mapping.md) - Zephyr to qTest entity mapping details
- [GitHub Actions](docs/github-actions.md) - CI/CD integration guide
- [Scheduled Migrations](docs/scheduled-migrations.md) - Automated migration guide
- [Maintenance Guide](docs/maintenance.md) - Project maintenance procedures

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

## Further Resources

- [Project Structure](docs/project-structure.md) - Learn about our standardized directory organization
- [Open Source Philosophy](docs/open-source-philosophy.md) - Explore our approach to open source and why it matters
- [Kanban History](docs/kanban-history.md) - Review our development journey and the reasoning behind key decisions

## Why Open Source Matters

We believe that test data migration tools should be built with care, not rushed as one-off scripts. By embracing open source principles, we've created a more robust, maintainable, and educational solution that serves both immediate needs and long-term value.

This repository demonstrates how thoughtful design and investment in quality can transform a utility task into a capability that benefits the entire testing community. Learn more in our [Open Source Philosophy](docs/open-source-philosophy.md) document.

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](LICENSE)*

#datamigration #testmanagement #zephyrscale #qtest #pythontool #etl #testautomation #dataextraction #apiclient #testtoolmigration #opensource #pythonapi #testdataintegration
