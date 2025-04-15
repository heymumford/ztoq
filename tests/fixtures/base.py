"""
Base fixtures for the ZTOQ testing framework.

This module provides foundational fixtures that can be used across all test types
(unit, integration, system) to ensure consistent test setup and teardown.
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any, Generator, Optional
from unittest.mock import MagicMock, patch

# Add the project root to the path if not already there
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def base_test_env() -> Dict[str, str]:
    """
    Provide a standardized set of environment variables for testing.

    This fixture sets up a basic set of environment variables that can be used
    across different test types to ensure consistent behavior.

    Returns:
        Dict[str, str]: Dictionary of environment variables
    """
    return {
        "ZTOQ_LOG_LEVEL": "DEBUG",
        "ZTOQ_DB_TYPE": "sqlite",
        "ZTOQ_DB_PATH": ":memory:",
        "ZEPHYR_BASE_URL": "https://api.example.com/v2",
        "ZEPHYR_API_TOKEN": "test_token",
        "ZEPHYR_PROJECT_KEY": "TEST",
        "QTEST_BASE_URL": "https://qtest.example.com",
        "QTEST_USERNAME": "test_user",
        "QTEST_PASSWORD": "test_password",
        "QTEST_PROJECT_ID": "12345",
    }


@pytest.fixture
def mock_env_vars(base_test_env: Dict[str, str]) -> Generator[Dict[str, str], None, None]:
    """
    Set and restore environment variables for tests.

    This fixture applies the environment variables from base_test_env,
    yields control back to the test, and then restores the original
    environment after the test completes.

    Args:
        base_test_env: The base testing environment variables

    Yields:
        Dict[str, str]: The applied environment variables
    """
    original_environ = os.environ.copy()

    # Apply the test environment
    os.environ.update(base_test_env)

    yield base_test_env

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_environ)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory for test files.

    This fixture creates a temporary directory that can be used to store
    test files and artifacts. The directory is automatically cleaned up
    after the test completes.

    Yields:
        Path: Path to the temporary directory
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def temp_file(temp_dir: Path) -> Generator[Path, None, None]:
    """
    Create a temporary file for testing.

    This fixture creates a temporary file within the temporary directory
    that can be used for testing file operations.

    Args:
        temp_dir: The temporary directory to create the file in

    Yields:
        Path: Path to the temporary file
    """
    temp_file_path = temp_dir / "temp_test_file.txt"
    temp_file_path.touch()
    yield temp_file_path


@pytest.fixture
def temp_db_path(temp_dir: Path) -> str:
    """
    Create a path for a temporary database file.

    Args:
        temp_dir: The temporary directory to create the database in

    Returns:
        str: Path to the temporary database file
    """
    return str(temp_dir / "test_ztoq.db")


@pytest.fixture
def mock_response() -> MagicMock:
    """
    Create a mock HTTP response object for testing.

    This fixture provides a standardized mock response that can be customized
    for different test scenarios involving HTTP requests.

    Returns:
        MagicMock: A mock response object
    """
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"status": "success", "data": []}
    mock.text = '{"status": "success", "data": []}'
    mock.headers = {"Content-Type": "application/json"}
    return mock


@pytest.fixture
def mock_requests_session(mock_response: MagicMock) -> Generator[MagicMock, None, None]:
    """
    Mock the requests.Session for HTTP request testing.

    This fixture patches the requests.Session class to return a mock session
    that can be used to simulate HTTP requests without making actual network calls.

    Args:
        mock_response: The mock response to return from requests

    Yields:
        MagicMock: The mock session object
    """
    with patch("requests.Session") as mock_session:
        session_instance = MagicMock()
        session_instance.get.return_value = mock_response
        session_instance.post.return_value = mock_response
        session_instance.put.return_value = mock_response
        session_instance.delete.return_value = mock_response
        session_instance.request.return_value = mock_response
        mock_session.return_value = session_instance
        yield session_instance
