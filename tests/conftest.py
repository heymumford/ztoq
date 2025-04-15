"""
Test configuration and fixtures for the ztoq project.

This file is the root pytest configuration file that sets up pytest
markers and imports fixtures from the fixtures modules to make them
available to all tests.
"""

import pytest

# Import fixtures from the fixtures modules to make them available to all tests
from tests.fixtures.base import (
    base_test_env,
    mock_env_vars,
    temp_dir,
    temp_file,
    temp_db_path,
    mock_response,
    mock_requests_session,
)

# Import unit test fixtures
from tests.fixtures.unit import mock_db_connection, mock_db_cursor, mock_file_system

# Import integration test fixtures
from tests.fixtures.integration import (
    sqlite_memory_engine,
    sqlite_memory_connection,
    sqlite_file_engine,
    mock_external_api,
    test_data_dir,
)

# Import system test fixtures
from tests.fixtures.system import skip_if_no_docker, docker_compose_env, cli_runner, run_cli_command


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: mark a test as a unit test")
    config.addinivalue_line("markers", "integration: mark a test as an integration test")
    config.addinivalue_line("markers", "system: mark a test as a system test")
    config.addinivalue_line("markers", "docker: mark a test that requires Docker")
    config.addinivalue_line("markers", "api: mark a test that tests API functionality")
    config.addinivalue_line("markers", "db: mark a test that requires database access")
    config.addinivalue_line("markers", "cli: mark a test that tests CLI functionality")
    config.addinivalue_line("markers", "slow: mark a test that takes longer than average to run")
