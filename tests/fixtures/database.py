"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Database fixtures for the ZTOQ testing framework.

This module provides fixtures for testing database interactions at different
levels of the testing pyramid, from unit tests with mocked database connections
to integration tests with real database access.
"""

import os
import pytest
import sqlite3
from pathlib import Path
from typing import Dict, Any, Generator, Optional, List, Tuple
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, Table, MetaData, text, Column, Integer, String
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Import the base fixtures
from tests.fixtures.base import temp_db_path


@pytest.fixture
def schema_tables() -> List[str]:
    """
    Get a list of table definitions for creating test schema.

    This fixture provides SQL statements to create the database schema
    tables for testing, without relying on the actual application models.

    Returns:
        List[str]: List of CREATE TABLE statements
    """
    return [
        """
        CREATE TABLE IF NOT EXISTS Project (
            project_id VARCHAR PRIMARY KEY,
            project_key VARCHAR UNIQUE NOT NULL,
            name VARCHAR NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS Folder (
            folder_id INTEGER PRIMARY KEY,
            project_id VARCHAR REFERENCES Project(project_id),
            parent_folder_id INTEGER REFERENCES Folder(folder_id),
            name VARCHAR NOT NULL,
            type VARCHAR CHECK(type IN ('TEST_CASE', 'TEST_PLAN', 'TEST_CYCLE')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS TestCase (
            test_case_id INTEGER PRIMARY KEY,
            project_id VARCHAR REFERENCES Project(project_id),
            folder_id INTEGER REFERENCES Folder(folder_id),
            key VARCHAR UNIQUE NOT NULL,
            name VARCHAR NOT NULL,
            objective TEXT,
            precondition TEXT,
            estimated_time_ms INTEGER,
            priority VARCHAR,
            status VARCHAR,
            owner_id VARCHAR,
            created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS TestStep (
            step_id INTEGER PRIMARY KEY,
            test_case_id INTEGER REFERENCES TestCase(test_case_id),
            step_order INTEGER NOT NULL,
            description TEXT NOT NULL,
            expected_result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS TestCycle (
            test_cycle_id INTEGER PRIMARY KEY,
            project_id VARCHAR REFERENCES Project(project_id),
            folder_id INTEGER REFERENCES Folder(folder_id),
            key VARCHAR UNIQUE NOT NULL,
            name VARCHAR NOT NULL,
            description TEXT,
            planned_start_date TIMESTAMP,
            planned_end_date TIMESTAMP,
            status VARCHAR,
            owner_id VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS TestExecution (
            execution_id INTEGER PRIMARY KEY,
            test_cycle_id INTEGER REFERENCES TestCycle(test_cycle_id),
            test_case_id INTEGER REFERENCES TestCase(test_case_id),
            status VARCHAR NOT NULL,
            executed_by_id VARCHAR,
            assigned_to_id VARCHAR,
            execution_time_ms INTEGER,
            actual_end_date TIMESTAMP,
            environment VARCHAR,
            comment TEXT,
            automated BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS CustomField (
            custom_field_id INTEGER PRIMARY KEY,
            object_type VARCHAR CHECK(object_type IN ('TestCase', 'TestCycle', 'TestExecution')),
            object_id INTEGER NOT NULL,
            field_name VARCHAR NOT NULL,
            field_value TEXT,
            UNIQUE(object_type, object_id, field_name)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS Attachment (
            attachment_id INTEGER PRIMARY KEY,
            related_type VARCHAR CHECK(related_type IN ('TestCase', 'TestExecution', 'TestStep')),
            related_id INTEGER NOT NULL,
            attachment_name VARCHAR NOT NULL,
            attachment_blob BLOB,
            attachment_url VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
    ]


@pytest.fixture
def sqlite_test_db(
    temp_db_path: str, schema_tables: List[str]
) -> Generator[sqlite3.Connection, None, None]:
    """
    Create a SQLite test database with schema.

    This fixture creates a SQLite database with the test schema tables
    and returns a connection to it, which is useful for database integration
    tests that don't require SQLAlchemy.

    Args:
        temp_db_path: Path to the temporary database file
        schema_tables: List of CREATE TABLE statements

    Yields:
        sqlite3.Connection: Connection to the SQLite database
    """
    # Create a SQLite database
    conn = sqlite3.connect(temp_db_path)
    conn.row_factory = sqlite3.Row

    # Create schema tables
    cursor = conn.cursor()
    for table_sql in schema_tables:
        cursor.execute(table_sql)
    conn.commit()

    yield conn

    # Close the connection
    conn.close()

    # Clean up by removing the temporary database file
    db_path = Path(temp_db_path)
    if db_path.exists():
        try:
            db_path.unlink()
        except (PermissionError, OSError):
            pass


@pytest.fixture
def sqlalchemy_memory_engine(schema_tables: List[str]) -> Generator[Engine, None, None]:
    """
    Create a SQLAlchemy in-memory database engine with schema.

    This fixture provides a SQLAlchemy engine connected to an in-memory
    SQLite database with the test schema tables, which is useful for
    integration tests that require database access.

    Args:
        schema_tables: List of CREATE TABLE statements

    Yields:
        Engine: SQLAlchemy engine
    """
    # Create an in-memory SQLite database engine
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    # Create schema tables
    with engine.begin() as conn:
        for table_sql in schema_tables:
            conn.execute(text(table_sql))

    yield engine


@pytest.fixture
def sqlalchemy_memory_session(sqlalchemy_memory_engine: Engine) -> Generator[Session, None, None]:
    """
    Create a SQLAlchemy session with in-memory database.

    This fixture provides a SQLAlchemy session connected to an in-memory
    SQLite database with the test schema tables, which is useful for
    integration tests that require database access.

    Args:
        sqlalchemy_memory_engine: SQLAlchemy engine

    Yields:
        Session: SQLAlchemy session
    """
    # Create a session
    connection = sqlalchemy_memory_engine.connect()
    transaction = connection.begin()

    # Create a session bound to the connection
    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    yield session

    # Clean up
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def sqlalchemy_file_engine(
    temp_db_path: str, schema_tables: List[str]
) -> Generator[Engine, None, None]:
    """
    Create a SQLAlchemy file database engine with schema.

    This fixture provides a SQLAlchemy engine connected to a file-based
    SQLite database with the test schema tables, which is useful for
    integration tests that require persistent database access.

    Args:
        temp_db_path: Path to the temporary database file
        schema_tables: List of CREATE TABLE statements

    Yields:
        Engine: SQLAlchemy engine
    """
    # Create a file-based SQLite database engine
    engine = create_engine(f"sqlite:///{temp_db_path}")

    # Create schema tables
    with engine.begin() as conn:
        for table_sql in schema_tables:
            conn.execute(text(table_sql))

    yield engine

    # Clean up by removing the temporary database file
    db_path = Path(temp_db_path)
    if db_path.exists():
        try:
            db_path.unlink()
        except (PermissionError, OSError):
            pass


@pytest.fixture
def sqlalchemy_file_session(sqlalchemy_file_engine: Engine) -> Generator[Session, None, None]:
    """
    Create a SQLAlchemy session with file database.

    This fixture provides a SQLAlchemy session connected to a file-based
    SQLite database with the test schema tables, which is useful for
    integration tests that require persistent database access.

    Args:
        sqlalchemy_file_engine: SQLAlchemy engine

    Yields:
        Session: SQLAlchemy session
    """
    # Create a session
    connection = sqlalchemy_file_engine.connect()
    transaction = connection.begin()

    # Create a session bound to the connection
    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    yield session

    # Clean up
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def populate_test_db() -> callable:
    """
    Provide a function to populate a test database with sample data.

    This fixture returns a function that can be used to populate
    a test database with sample data for testing.

    Returns:
        callable: Function to populate a test database
    """

    def _populate(
        session: Session, sample_data: Optional[Dict[str, List[Dict[str, Any]]]] = None
    ) -> None:
        """
        Populate a test database with sample data.

        Args:
            session: SQLAlchemy session
            sample_data: Dictionary of sample data keyed by table name
        """
        # Default sample data if not provided
        if sample_data is None:
            sample_data = {
                "Project": [
                    {"project_id": "PROJ-1", "project_key": "PROJ1", "name": "Project One"},
                    {"project_id": "PROJ-2", "project_key": "PROJ2", "name": "Project Two"},
                ],
                "Folder": [
                    {
                        "folder_id": 1,
                        "project_id": "PROJ-1",
                        "name": "Root Folder",
                        "type": "TEST_CASE",
                    },
                    {
                        "folder_id": 2,
                        "project_id": "PROJ-1",
                        "parent_folder_id": 1,
                        "name": "Child Folder",
                        "type": "TEST_CASE",
                    },
                ],
                "TestCase": [
                    {
                        "test_case_id": 1,
                        "project_id": "PROJ-1",
                        "folder_id": 2,
                        "key": "TC-1",
                        "name": "Test Case One",
                    },
                    {
                        "test_case_id": 2,
                        "project_id": "PROJ-1",
                        "folder_id": 2,
                        "key": "TC-2",
                        "name": "Test Case Two",
                    },
                ],
                "TestStep": [
                    {
                        "step_id": 1,
                        "test_case_id": 1,
                        "step_order": 1,
                        "description": "Step One",
                        "expected_result": "Expected One",
                    },
                    {
                        "step_id": 2,
                        "test_case_id": 1,
                        "step_order": 2,
                        "description": "Step Two",
                        "expected_result": "Expected Two",
                    },
                ],
                "TestCycle": [
                    {
                        "test_cycle_id": 1,
                        "project_id": "PROJ-1",
                        "folder_id": 1,
                        "key": "CY-1",
                        "name": "Cycle One",
                    },
                    {
                        "test_cycle_id": 2,
                        "project_id": "PROJ-1",
                        "folder_id": 1,
                        "key": "CY-2",
                        "name": "Cycle Two",
                    },
                ],
                "TestExecution": [
                    {"execution_id": 1, "test_cycle_id": 1, "test_case_id": 1, "status": "Passed"},
                    {"execution_id": 2, "test_cycle_id": 1, "test_case_id": 2, "status": "Failed"},
                ],
            }

        # Insert sample data
        for table_name, records in sample_data.items():
            # Create a metadata object
            metadata = MetaData()

            # Use SQLAlchemy Core to insert data
            # First, dynamically create a table object based on the first record
            if records:
                columns = {}
                for column_name, value in records[0].items():
                    if isinstance(value, int):
                        columns[column_name] = Column(column_name, Integer)
                    else:
                        columns[column_name] = Column(column_name, String)

                table = Table(table_name, metadata, *columns.values())

                # Insert data
                session.execute(table.insert().values(records))

        # Commit the changes
        session.commit()

    return _populate


@pytest.fixture
def mock_sqlalchemy_engine() -> MagicMock:
    """
    Mock a SQLAlchemy engine for unit testing.

    This fixture provides a mock SQLAlchemy engine that can be used
    for unit tests that interact with SQLAlchemy, without requiring
    an actual database connection.

    Returns:
        MagicMock: Mock SQLAlchemy engine
    """
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_sqlalchemy_session() -> MagicMock:
    """
    Mock a SQLAlchemy session for unit testing.

    This fixture provides a mock SQLAlchemy session that can be used
    for unit tests that interact with SQLAlchemy, without requiring
    an actual database connection.

    Returns:
        MagicMock: Mock SQLAlchemy session
    """
    mock = MagicMock()
    mock.execute.return_value = MagicMock()
    mock.query.return_value = MagicMock()
    mock.add.return_value = None
    mock.add_all.return_value = None
    mock.commit.return_value = None
    mock.rollback.return_value = None
    mock.close.return_value = None

    # Mock query builder methods
    mock.query.return_value.filter.return_value = mock.query.return_value
    mock.query.return_value.filter_by.return_value = mock.query.return_value
    mock.query.return_value.all.return_value = []
    mock.query.return_value.first.return_value = None
    mock.query.return_value.one.return_value = None
    mock.query.return_value.one_or_none.return_value = None
    mock.query.return_value.count.return_value = 0

    return mock


@pytest.fixture
def transaction_fixture(
    sqlalchemy_memory_session: Session,
) -> Generator[Tuple[Session, callable], None, None]:
    """
    Create a fixture for testing database transactions.

    This fixture provides a session and a savepoint function for testing
    database transactions with automatic rollback.

    Args:
        sqlalchemy_memory_session: SQLAlchemy session

    Yields:
        Tuple[Session, callable]: Session and savepoint function
    """
    # Start with a clean slate
    sqlalchemy_memory_session.begin_nested()

    # Function to create a savepoint
    def savepoint():
        sqlalchemy_memory_session.begin_nested()

    yield sqlalchemy_memory_session, savepoint

    # Roll back to the beginning
    sqlalchemy_memory_session.rollback()


@pytest.fixture
def concurrent_sessions(sqlalchemy_memory_engine: Engine) -> Generator[List[Session], None, None]:
    """
    Create multiple concurrent sessions for testing parallel operations.

    This fixture provides multiple SQLAlchemy sessions connected to the same
    database for testing concurrent database operations.

    Args:
        sqlalchemy_memory_engine: SQLAlchemy engine

    Yields:
        List[Session]: List of SQLAlchemy sessions
    """
    # Create session factory
    session_factory = sessionmaker(bind=sqlalchemy_memory_engine)

    # Create multiple sessions
    sessions = [session_factory() for _ in range(3)]

    yield sessions

    # Clean up
    for session in sessions:
        session.close()
