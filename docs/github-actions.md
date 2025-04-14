# GitHub Actions Configuration

This document describes the GitHub Actions workflows configured for the ZTOQ project.

## Overview

ZTOQ uses GitHub Actions for continuous integration and security scanning. The following workflows are configured:

1. **Quality Gates** - Runs linting, testing, security checks, and SonarCloud analysis
2. **Container Security Scan** - Scans Docker container images for vulnerabilities
3. **Migration Tests** - Tests the Zephyr Scale to qTest migration functionality
4. **ETL Integration** - Runs extensive tests for the ETL migration pipeline
5. **Migration PR Validation** - Validates pull requests that modify migration code
6. **Release** - Handles versioning, packaging, and documentation for releases
7. **Dependabot** - Automatically updates dependencies

## Quality Gates Workflow

The Quality Gates workflow (`quality-gates.yml`) runs on:
- Push to the main branch (excluding documentation changes)
- Pull requests to the main branch (excluding documentation changes)
- Weekly schedule (Sunday at midnight UTC)
- Manual trigger

### Jobs

#### Linting

- Runs pre-commit hooks on all files
- Executes ruff linter
- Runs mypy type checking

#### Testing

- Runs unit tests with coverage reporting
- Runs integration tests
- Uploads coverage reports as artifacts

#### Security Checks

- Runs bandit security scans
- Executes safety dependency vulnerability checks
- Uploads security reports as artifacts
- Creates GitHub issues for critical vulnerabilities (only on scheduled runs)

#### SonarCloud Analysis

- Uploads code for SonarCloud analysis
- Provides quality metrics and code smells
- Only runs on push and pull request events

### Example Output

The workflow produces several artifacts:
- Coverage reports (HTML and XML)
- Security scan results (JSON, HTML, and text)
- SonarCloud analysis results

## Container Security Scan Workflow

The Container Security Scan workflow (`container-scan.yml`) runs on:
- Push to the main branch when Dockerfile, docker-compose.yml, or dependency files change
- Pull requests to the main branch when relevant files change
- Weekly schedule (Wednesday at midnight UTC)
- Manual trigger

### Jobs

#### Build and Scan Container

- Builds the Docker image using Buildx
- Scans the image using Trivy in multiple formats:
  - JSON for parsing
  - Table for human readability
  - HTML for detailed reports
  - SARIF for GitHub code scanning integration
- Uploads scan results as artifacts
- Creates GitHub issues for critical vulnerabilities (only on scheduled runs)

### Example Output

The workflow produces several artifacts:
- Trivy scan results (JSON, text, HTML, and SARIF)
- GitHub issues for critical vulnerabilities with detailed summaries

## Dependabot Configuration

Dependabot is configured to automatically update:
- Python dependencies (weekly)
- GitHub Actions (monthly)
- Docker dependencies (monthly)

### Configuration Details

- Python updates include scope in commit messages
- Limits open pull requests to avoid overwhelming maintainers
- Ignores certain dev dependencies that shouldn't block releases
- Adds appropriate labels to pull requests by type

## Workflow Optimization

These workflows are optimized to:
1. Only run when necessary (path filtering)
2. Run in parallel when possible (job dependencies)
3. Cache dependencies for faster execution
4. Provide actionable outputs (artifacts, issues)
5. Balance frequency with resource usage (scheduled runs)

## Manual Triggers

All workflows support manual triggering via the GitHub Actions UI under the "Actions" tab. This is useful for:
- Testing workflow changes
- Running scans after significant dependency updates
- Verifying that issues have been resolved

## Required Secrets

The workflows require the following GitHub secrets:
- `GITHUB_TOKEN` (automatically provided)
- `SONAR_TOKEN` (for SonarCloud integration)
- `PYPI_API_TOKEN` (for publishing to PyPI)

For real API tests, the following secrets are required in the `integration-testing` environment:
- `ZEPHYR_BASE_URL` - Base URL of the Zephyr Scale API
- `ZEPHYR_API_TOKEN` - API token for Zephyr Scale
- `ZEPHYR_PROJECT_KEY` - Project key in Zephyr Scale
- `QTEST_BASE_URL` - Base URL of the qTest API
- `QTEST_USERNAME` - Username for qTest authentication
- `QTEST_PASSWORD` - Password for qTest authentication
- `QTEST_PROJECT_ID` - Project ID in qTest

## Migration Workflow Suite

The migration functionality in ZTOQ is tested by multiple specialized workflows:

### Migration Tests Workflow

The Migration Tests workflow (`migration-tests.yml`) runs on:
- Push to the main branch when migration-related files change
- Pull requests to the main branch when migration-related files change
- Manual trigger

#### Jobs

##### Migration Tests
- Runs unit tests specifically for the migration module
- Generates coverage reports for migration code
- Continues on errors to collect maximum test data

##### Migration Batch Tests
- Sets up a PostgreSQL database for real database testing
- Tests the batch processing functionality with various batch sizes
- Simulates large dataset migrations to verify performance

##### Update Badge
- Extracts coverage data from test reports
- Generates and updates the migration test coverage badge
- Only runs on pushes to the main branch

### ETL Integration Workflow

The ETL Integration workflow (`etl-integration.yml`) runs on:
- Push to the main branch when ETL-related files change
- Pull requests to the main branch when ETL-related files change
- Weekly schedule (Monday at midnight UTC)
- Manual trigger with customizable batch size

#### Jobs

##### ETL SQLite Tests
- Tests ETL functionality with SQLite database backend
- Runs example files to verify real-world usage patterns
- Generates coverage reports

##### ETL PostgreSQL Tests
- Tests ETL functionality with PostgreSQL database backend
- Runs custom migration examples with real database connections
- Generates coverage reports

##### Parallel Execution Tests
- Tests concurrent execution of migration tasks
- Verifies thread safety and resource management
- Ensures optimal performance for large migrations

##### Resume Capability Tests
- Tests the ability to resume migrations after interruptions
- Runs a multi-phase migration to verify state persistence
- Ensures data integrity across migration phases

##### Real API Tests
- Only runs on schedule or manual trigger with explicit approval
- Tests against actual Zephyr Scale and qTest APIs using project secrets
- Generates detailed migration reports for analysis

##### Performance Tests
- Benchmarks migration performance with different batch sizes
- Generates performance reports comparing configuration options
- Helps optimize settings for different migration scenarios

### Migration PR Validation Workflow

The Migration PR Validation workflow (`migration-pr-validation.yml`) runs on:
- Pull requests to the main branch when migration-related files change

#### Jobs

##### Validate Migration Code
- Runs mypy for type checking
- Runs ruff for code quality checks
- Runs migration unit tests with coverage
- Warns when coverage drops below 80%

##### Validate ETL Workflow
- Runs a mock ETL workflow to verify overall process
- Tests with dry-run mode to prevent actual API calls
- Verifies integration points between components

##### Check SQL Injection
- Scans for potential SQL injection vulnerabilities
- Looks for unparameterized SQL queries
- Flags potentially unsafe database operations

##### Check API Security
- Scans for hardcoded secrets or credentials
- Checks token and password handling for security
- Ensures sensitive data is properly protected

## Release Workflow

The Release workflow (`release.yml`) runs on:
- Tags matching the pattern 'v*'
- Manual trigger with version input

#### Jobs

##### Build
- Runs tests to ensure code quality
- Builds Python package artifacts
- Uploads artifacts for later jobs

##### Release
- Creates a GitHub release with changelog
- Attaches built artifacts to the release
- Tags the release with appropriate version

##### Publish
- Publishes package to PyPI
- Only runs for tagged releases
- Uses PyPI API token for authentication

##### Update Docs
- Updates documentation with latest changes
- Publishes updated docs to GitHub Pages
- Ensures documentation stays in sync with releases

## Best Practices

When modifying workflows:
1. Test changes with workflow_dispatch before merging
2. Keep the balance between thoroughness and execution time
3. Ensure actionable outputs are maintained
4. Preserve the path filtering to avoid unnecessary runs
5. Maintain the scheduled runs for security scanning
6. Update badges to reflect current project status
7. Consider database requirements for integration tests
8. Use mock objects for API tests unless explicitly testing API integration