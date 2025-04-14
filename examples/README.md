# ZTOQ Examples

This directory contains example scripts that demonstrate the usage of the ZTOQ library. These examples are designed to help you get started and show you how to use the various features of the library.

## qTest API Authentication Examples

### qtest_auth_tool.py

A comprehensive tool for working with qTest authentication including getting tokens, verifying tokens, checking token status, and revoking tokens.

```bash
# Get a token using username and password
python qtest_auth_tool.py get-token --base-url https://example.qtest.com --username user@example.com --password P@ssw0rd

# Verify an existing token
python qtest_auth_tool.py verify-token --base-url https://example.qtest.com --token YOUR_TOKEN

# Get token status (expiration info)
python qtest_auth_tool.py token-status --base-url https://example.qtest.com --token YOUR_TOKEN

# Revoke a token
python qtest_auth_tool.py revoke-token --base-url https://example.qtest.com --token YOUR_TOKEN

# Export as environment variables
eval $(python qtest_auth_tool.py get-token --base-url https://example.qtest.com --username user@example.com --password P@ssw0rd --format env)
```

### qtest_get_token.py

A simple script to acquire a qTest API token using username/password authentication.

```bash
python qtest_get_token.py --base-url https://example.qtest.com --username user@example.com --password P@ssw0rd
```

### qtest_auth_test.py

Test script for verifying qTest authentication using environment variables.

```bash
# Set environment variables
export qtest_base_url=https://example.qtest.com
export qtest_bearer_token=YOUR_TOKEN

# Run authentication test
python qtest_auth_test.py --project-id 12345
```

### qtest_auth_debug.py

Debug script for troubleshooting qTest authentication issues with detailed logging.

```bash
python qtest_auth_debug.py --base-url https://example.qtest.com --username user@example.com --password P@ssw0rd --api-type manager --debug
```

### qtest_project_list.py

Example script to list qTest projects with various authentication methods.

```bash
# Use environment variables
python qtest_project_list.py

# Use token from command line
python qtest_project_list.py --base-url https://example.qtest.com --token YOUR_TOKEN

# Use username/password
python qtest_project_list.py --base-url https://example.qtest.com --username user@example.com --password P@ssw0rd
```

### qtest_client_example.py

Comprehensive example demonstrating various qTest API operations.

```bash
# List projects
python qtest_client_example.py --base-url https://example.qtest.com --token YOUR_TOKEN --list-projects

# List test cases
python qtest_client_example.py --base-url https://example.qtest.com --token YOUR_TOKEN --project-id 12345 --list-test-cases

# Get user permissions
python qtest_client_example.py --base-url https://example.qtest.com --token YOUR_TOKEN --project-id 12345 --get-permissions
```

## Zephyr API Examples

### verify_api_tokens.py

Script to verify both qTest and Zephyr API tokens.

```bash
# Set environment variables
export qtest_base_url=https://example.qtest.com
export qtest_bearer_token=YOUR_QTEST_TOKEN
export zephyr_access_token=YOUR_ZEPHYR_TOKEN

# Run verification
python verify_api_tokens.py
```

## Other Examples

### custom_fields_test.py

Example script showing how to work with custom fields in both qTest and Zephyr.

### custom_migration.py

Example script demonstrating a custom migration workflow.

### debug_example.py

Example script showing how to set up logging and debugging.

### generate_tests.py

Example script showing how to generate test cases.

### migration_example.py

Example script demonstrating basic migration functionality.

### migration_report.py

Example script showing how to generate migration reports.

### validation_example.py

Example script showing data validation functionality.

## Environment Variables

Some common environment variables used by these examples:

- `qtest_base_url`: Base URL for qTest API (e.g., https://example.qtest.com)
- `qtest_bearer_token`: Bearer token for qTest authentication
- `qtest_username`: Username for qTest authentication
- `qtest_password`: Password for qTest authentication
- `zephyr_access_token`: Access token for Zephyr Scale API

## Running Examples with Debug Logging

Most examples support debug logging with the `--debug` flag:

```bash
python qtest_auth_test.py --debug
```

or by setting the logging level environment variable:

```bash
export ZTOQ_LOG_LEVEL=DEBUG
python qtest_auth_test.py
```
