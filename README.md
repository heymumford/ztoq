# ZTOQ (Zephyr to qTest)

![Tests](https://img.shields.io/badge/tests-passing-brightgreen)
![Unit Tests](https://img.shields.io/badge/unit%20tests-passing-brightgreen)
![Integration Tests](https://img.shields.io/badge/integration%20tests-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-88%25-green)

A Python CLI tool that extracts test data from Zephyr Scale and migrates it to qTest. This tool reads the Zephyr Scale OpenAPI specification and provides a complete migration pathway between these two test management systems.

## Quick Start

```bash
# Install with pip
pip install ztoq

# Or with Poetry
pip install poetry
poetry install

# Verify installation
ztoq --version

# View documentation
ztoq docs serve
```

## Features

- Complete ETL migration pipeline from Zephyr Scale to qTest
- Batch processing with parallel operations for large migrations
- Efficient resource management with automatic cleanup
- Connection pooling for optimal API performance
- Memory-efficient processing for large datasets
- Resumable migration with state tracking
- Support for custom fields and attachments
- Connection pooling with automatic resource management
- Robust resource cleanup for parallel and async processing
- Comprehensive logging and error handling
- Dockerized deployment option

## Basic Usage

```bash
# Set your API tokens
export zephyr_access_token="your_zephyr_token"
export qtest_bearer_token="your_qtest_token"

# Run a migration
ztoq migrate run \
  --zephyr-base-url https://api.atlassian.com/ex/jira/your-instance/rest/zephyr/1.0 \
  --zephyr-api-token YOUR_ZEPHYR_TOKEN \
  --zephyr-project-key PROJECT \
  --qtest-base-url https://yourcompany.qtestnet.com \
  --qtest-username YOUR_USERNAME \
  --qtest-password YOUR_PASSWORD \
  --qtest-project-id 12345 \
  --db-type sqlite \
  --db-path ./migration.db
```

## Documentation

After installation, view the full documentation with:

```bash
ztoq docs serve
```

The documentation includes:
- Detailed command examples
- Migration guide
- API documentation
- Advanced configuration options
- Docker deployment instructions
- Troubleshooting tips

## Development

```bash
# Install development dependencies
poetry install --with dev

# Run linters and tests
make lint
make test

# Generate documentation
make docs
```

## Resource Management

ZTOQ is designed for efficient resource usage with automatic cleanup mechanisms:

- **Connection Pooling**: HTTP connections are pooled and automatically cleaned up
- **Async Task Management**: All async tasks include timeouts and proper cancellation
- **Database Sessions**: Thread-local sessions are tracked and cleaned up when threads exit
- **Memory Management**: Work queues and caches automatically clean up completed items
- **Circuit Breakers**: Idle circuit breakers are periodically removed to prevent memory leaks

Client classes provide explicit cleanup methods to ensure resources are properly released:

```python
# Create a client
client = ZephyrClient(config)

try:
    # Use the client
    projects = client.get_projects()
finally:
    # Clean up resources when done
    client.cleanup()
```

## Further Resources

- [Migration Guide](docs/migration-guide.md)
- [Resource Management Best Practices](docs/resource-management.md) 
- [API Tokens Configuration](docs/api-tokens.md)
- [Database Configuration](docs/database-configuration.md)
- [Docker Deployment](docs/docker-deployment.md)

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](LICENSE)*
*Last updated: April 17, 2025*