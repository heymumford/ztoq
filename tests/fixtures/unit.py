"""
Unit test fixtures for the ZTOQ testing framework.

This module provides fixtures specifically designed for unit tests,
focusing on isolation and mocking of dependencies.
"""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

# Import the base fixtures


@pytest.fixture
def mock_db_connection() -> MagicMock:
    """
    Mock a database connection for unit testing.

    This fixture provides a mock database connection that can be used
    for unit tests that interact with the database, without requiring
    an actual database connection.

    Returns:
        MagicMock: A mock database connection
    """
    mock = MagicMock()
    mock.execute.return_value = MagicMock()
    mock.commit.return_value = None
    mock.rollback.return_value = None
    mock.close.return_value = None
    return mock


@pytest.fixture
def mock_db_cursor(mock_db_connection: MagicMock) -> MagicMock:
    """
    Mock a database cursor for unit testing.

    This fixture provides a mock database cursor that can be used
    for unit tests that interact with the database, without requiring
    an actual database connection.

    Args:
        mock_db_connection: The mock database connection

    Returns:
        MagicMock: A mock database cursor
    """
    mock = MagicMock()
    mock.execute.return_value = mock
    mock.fetchall.return_value = []
    mock.fetchone.return_value = None
    mock.close.return_value = None
    mock_db_connection.cursor.return_value = mock
    return mock


@pytest.fixture
def mock_file_system() -> Generator[dict[str, MagicMock], None, None]:
    """
    Mock file system operations for unit testing.

    This fixture patches common file system operations to avoid actual
    file system interactions during unit tests.

    Yields:
        Dict[str, MagicMock]: Dictionary of mocked file system functions
    """
    with patch("pathlib.Path.exists") as mock_exists, patch(
        "pathlib.Path.is_file",
    ) as mock_is_file, patch("pathlib.Path.is_dir") as mock_is_dir, patch(
        "pathlib.Path.open",
    ) as mock_open, patch(
        "builtins.open",
    ) as mock_builtin_open:
        # Set default returns
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_is_dir.return_value = False

        # Return all mocks in a dictionary for easy access
        mocks = {
            "exists": mock_exists,
            "is_file": mock_is_file,
            "is_dir": mock_is_dir,
            "path_open": mock_open,
            "builtin_open": mock_builtin_open,
        }

        yield mocks
