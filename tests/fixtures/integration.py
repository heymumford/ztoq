"""
Integration test fixtures for the ZTOQ testing framework.

This module provides fixtures specifically designed for integration tests,
focusing on testing component interactions with real but isolated dependencies.
"""

import os
import pytest
import sqlite3
import tempfile
from pathlib import Path
from typing import Dict, Any, Generator, Optional
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Import the base fixtures
from tests.fixtures.base import (
    base_test_env,
    mock_env_vars,
    temp_dir,
    temp_file,
    temp_db_path
)


@pytest.fixture
def sqlite_memory_engine() -> Engine:
    """
    Create a SQLite in-memory database engine for testing.

    This fixture provides a real SQLAlchemy engine connected to an
    in-memory SQLite database for integration tests that require
    database access.

    Returns:
        Engine: SQLAlchemy engine connected to an in-memory SQLite database
    """
    engine = create_engine("sqlite:///:memory:", future=True)
    return engine


@pytest.fixture
def sqlite_memory_connection(sqlite_memory_engine: Engine) -> Generator[Session, None, None]:
    """
    Create a SQLite in-memory database connection for testing.

    This fixture provides a real SQLAlchemy session connected to an
    in-memory SQLite database for integration tests that require
    database access.

    Args:
        sqlite_memory_engine: The SQLite engine to connect to

    Yields:
        Session: SQLAlchemy session
    """
    connection = sqlite_memory_engine.connect()

    # Begin a non-ORM transaction
    transaction = connection.begin()

    # Create a session bound to the connection
    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    yield session

    # Rollback the transaction and close the session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def sqlite_file_engine(temp_db_path: str) -> Generator[Engine, None, None]:
    """
    Create a SQLite file-based database engine for testing.

    This fixture provides a real SQLAlchemy engine connected to a
    file-based SQLite database for integration tests that require
    persistent database access.

    Args:
        temp_db_path: Path to the temporary database file

    Yields:
        Engine: SQLAlchemy engine connected to a file-based SQLite database
    """
    engine = create_engine(f"sqlite:///{temp_db_path}", future=True)
    yield engine

    # Clean up the database file if it exists
    db_path = Path(temp_db_path)
    if db_path.exists():
        try:
            db_path.unlink()
        except (PermissionError, OSError):
            pass


@pytest.fixture
def mock_external_api() -> Generator[Dict[str, MagicMock], None, None]:
    """
    Mock external API interactions for controlled integration testing.

    This fixture provides mocks for external API clients while still allowing
    the actual application components to interact, which is useful for
    integration tests that need to isolate external dependencies.

    Yields:
        Dict[str, MagicMock]: Dictionary of mocked API clients
    """
    with patch("ztoq.zephyr_client.ZephyrClient") as mock_zephyr, \
         patch("ztoq.qtest_client.QTestClient") as mock_qtest:

        # Create instances for the mocks
        zephyr_instance = MagicMock()
        qtest_instance = MagicMock()

        # Configure the class mocks to return the instances
        mock_zephyr.return_value = zephyr_instance
        mock_qtest.return_value = qtest_instance

        # Return the instances in a dictionary
        mocks = {
            "zephyr": zephyr_instance,
            "qtest": qtest_instance
        }

        yield mocks


@pytest.fixture
def test_data_dir(temp_dir: Path) -> Generator[Path, None, None]:
    """
    Create a directory with test data files for integration testing.

    This fixture creates a directory with sample test data files
    that can be used for integration tests requiring file input.

    Args:
        temp_dir: The temporary directory to create the test data in

    Yields:
        Path: Path to the test data directory
    """
    # Create a subdirectory for test data
    data_dir = temp_dir / "test_data"
    data_dir.mkdir()

    # Create some sample test data files
    sample_files = {
        "test_cases.json": """[
            {"id": 1, "name": "Test Case 1", "description": "Test description 1"},
            {"id": 2, "name": "Test Case 2", "description": "Test description 2"}
        ]""",
        "test_cycles.json": """[
            {"id": 1, "name": "Cycle 1", "description": "Cycle description 1"},
            {"id": 2, "name": "Cycle 2", "description": "Cycle description 2"}
        ]""",
        "test_executions.json": """[
            {"id": 1, "test_case_id": 1, "status": "Passed"},
            {"id": 2, "test_case_id": 2, "status": "Failed"}
        ]"""
    }

    # Create each sample file
    for filename, content in sample_files.items():
        file_path = data_dir / filename
        file_path.write_text(content)

    yield data_dir

    # Clean up is handled by the temp_dir fixture
