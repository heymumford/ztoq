# ZTOQ (Zephyr Test Object Query)

A Python CLI tool that reads the Zephyr Scale OpenAPI specification (z-openapi.yml) and extracts test data from Zephyr Scale via its API. This tool allows you to download all testing data for a JIRA project that has Zephyr Scale connected to it.

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

## Project Structure

```
ztoq/
├── models.py         # Pydantic models for Zephyr data
├── openapi_parser.py # Parser for OpenAPI spec
├── zephyr_client.py  # Client for Zephyr Scale API
├── storage.py        # Storage adapters (JSON/SQLite)
├── exporter.py       # Data export orchestration
└── cli.py            # Typer CLI commands

tests/
├── unit/            # Unit tests
└── integration/     # Integration tests

docs/
├── adr/             # Architecture Decision Records
├── c4_diagram.md    # C4 architecture diagrams
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

### Using Build Script

```bash
# Run all build steps
python build.py all

# Run tests with documentation
python build.py test --with-docs

# Generate documentation only
python build.py docs
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