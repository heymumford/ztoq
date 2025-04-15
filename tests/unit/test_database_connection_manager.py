"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Unit tests for the database connection manager.
"""

import os
import threading
from tempfile import NamedTemporaryFile

import pytest
from sqlalchemy import Column, Integer, String, text
from sqlalchemy.ext.declarative import declarative_base

from ztoq.database_connection_manager import (
    DatabaseConnectionManager,
    TransactionIsolationLevel,
    execute_query,
    get_connection_manager,
    get_session,
    transaction,
)

# Create a temporary model for testing
TestBase = declarative_base()


class TestModel(TestBase):
    """Test model for database testing."""

    __tablename__ = "test_models"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    value = Column(String(100))


@pytest.fixture
def temp_db_path():
    """Create a temporary SQLite database file."""
    with NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
        temp_path = temp_file.name

    # Yield the path
    yield f"sqlite:///{temp_path}"

    # Clean up the file after the test
    try:
        os.unlink(temp_path)
    except (OSError, PermissionError):
        pass


@pytest.fixture
def db_manager(temp_db_path):
    """Create a test database connection manager."""
    manager = DatabaseConnectionManager(
        db_url=temp_db_path,
        pool_size=2,
        max_overflow=3,
        echo=False,
        enable_metrics=False,
    )

    # Create the test table
    TestBase.metadata.create_all(manager.engine)

    yield manager

    # Clean up
    manager.close()


class TestDatabaseConnectionManager:
    """Test the database connection manager functionality."""

    def test_initialization(self, temp_db_path):
        """Test manager initialization with different configurations."""
        # Test with explicit URL
        manager1 = DatabaseConnectionManager(db_url=temp_db_path)
        assert manager1.db_url == temp_db_path
        assert manager1.is_sqlite == True
        assert manager1.is_postgresql == False

        # Test with default isolation level
        assert manager1.isolation_level == TransactionIsolationLevel.IMMEDIATE

        # Test with custom isolation level
        manager2 = DatabaseConnectionManager(
            db_url=temp_db_path,
            isolation_level=TransactionIsolationLevel.EXCLUSIVE,
        )
        assert manager2.isolation_level == TransactionIsolationLevel.EXCLUSIVE

        # Clean up
        manager1.close()
        manager2.close()

    def test_session_context_manager(self, db_manager):
        """Test the session context manager."""
        # Add data
        with db_manager.session() as session:
            session.add(TestModel(name="Test1", value="Value1"))
            session.add(TestModel(name="Test2", value="Value2"))

        # Verify data was committed
        with db_manager.session() as session:
            results = session.query(TestModel).all()
            assert len(results) == 2
            assert results[0].name == "Test1"
            assert results[1].name == "Test2"

    def test_transaction_context_manager(self, db_manager):
        """Test the transaction context manager."""
        # Add data with commit
        with db_manager.transaction() as session:
            session.add(TestModel(name="Test3", value="Value3"))

        # Verify data was committed
        with db_manager.session() as session:
            result = session.query(TestModel).filter_by(name="Test3").first()
            assert result is not None
            assert result.value == "Value3"

        # Test transaction rollback
        try:
            with db_manager.transaction() as session:
                session.add(TestModel(name="Test4", value="Value4"))
                # Raise an exception to trigger rollback
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Verify data was rolled back
        with db_manager.session() as session:
            result = session.query(TestModel).filter_by(name="Test4").first()
            assert result is None

    def test_read_only_transaction(self, db_manager):
        """Test read-only transaction."""
        # Add data first
        with db_manager.session() as session:
            session.add(TestModel(name="ReadOnly", value="ReadOnlyValue"))

        # Test read-only transaction
        with db_manager.read_only_transaction() as session:
            # Reading should work
            result = session.query(TestModel).filter_by(name="ReadOnly").first()
            assert result is not None
            assert result.value == "ReadOnlyValue"

            # For SQLite, writing will still work technically (can't enforce read-only)
            # but we're testing the functionality exists
            if not db_manager.is_sqlite:
                # Writing should fail for PostgreSQL
                with pytest.raises(Exception):
                    session.add(TestModel(name="ReadOnlyWrite", value="ShouldFail"))

    def test_thread_session(self, db_manager):
        """Test thread-local sessions."""
        # Add data in main thread
        session1 = db_manager.thread_session
        session1.add(TestModel(name="ThreadMain", value="MainValue"))
        session1.commit()

        # Track session objects
        sessions = []

        # Function to run in a separate thread
        def thread_function():
            # Get thread-local session
            session2 = db_manager.thread_session
            sessions.append(session2)

            # Add data in thread
            session2.add(TestModel(name="ThreadOther", value="OtherValue"))
            session2.commit()

        # Run in a separate thread
        thread = threading.Thread(target=thread_function)
        thread.start()
        thread.join()

        # The session objects should be different
        assert session1 != sessions[0]

        # Both operations should succeed
        with db_manager.session() as session:
            result1 = session.query(TestModel).filter_by(name="ThreadMain").first()
            result2 = session.query(TestModel).filter_by(name="ThreadOther").first()

            assert result1 is not None
            assert result2 is not None
            assert result1.value == "MainValue"
            assert result2.value == "OtherValue"

        # Clean up
        db_manager.close_thread_session()

    def test_execute_query(self, db_manager):
        """Test execute_query function."""
        # Add data
        with db_manager.session() as session:
            session.add(TestModel(name="Query1", value="QueryValue1"))
            session.add(TestModel(name="Query2", value="QueryValue2"))

        # Test simple query
        results = db_manager.execute_query("SELECT * FROM test_models WHERE name LIKE :pattern", {"pattern": "Query%"})
        assert len(results) == 2
        assert results[0]["name"] == "Query1"
        assert results[1]["name"] == "Query2"

        # Test SQLAlchemy selectable
        from sqlalchemy import select
        query = select(TestModel).where(TestModel.name == "Query1")
        results = db_manager.execute_query(query)
        assert len(results) == 1
        assert results[0]["name"] == "Query1"

    def test_execute_batch(self, db_manager):
        """Test execute_batch function."""
        # Prepare batch statements
        statements = [
            ("INSERT INTO test_models (name, value) VALUES (:name, :value)", {"name": "Batch1", "value": "BatchValue1"}),
            ("INSERT INTO test_models (name, value) VALUES (:name, :value)", {"name": "Batch2", "value": "BatchValue2"}),
            ("UPDATE test_models SET value = :value WHERE name = :name", {"name": "Batch1", "value": "BatchValueUpdated"}),
        ]

        # Execute batch
        success = db_manager.execute_batch(statements)
        assert success == True

        # Verify results
        with db_manager.session() as session:
            result1 = session.query(TestModel).filter_by(name="Batch1").first()
            result2 = session.query(TestModel).filter_by(name="Batch2").first()

            assert result1 is not None
            assert result2 is not None
            assert result1.value == "BatchValueUpdated"
            assert result2.value == "BatchValue2"

    def test_check_connectivity(self, db_manager):
        """Test connectivity check."""
        assert db_manager.check_connectivity() == True

    def test_get_table_names(self, db_manager):
        """Test getting table names."""
        tables = db_manager.get_table_names()
        assert "test_models" in tables

    def test_execute_in_batches(self, db_manager):
        """Test batched execution."""
        # Add a bunch of data
        with db_manager.session() as session:
            for i in range(25):
                session.add(TestModel(name=f"Batch_{i}", value=f"Value_{i}"))

        # Query function that gets data in batches
        def query_fn(session, offset, limit):
            return session.query(TestModel).order_by(TestModel.id).offset(offset).limit(limit).all()

        # Process function that extracts names
        def process_fn(batch):
            return [item.name for item in batch]

        # Execute in batches of 10
        results = db_manager.execute_in_batches(query_fn, process_fn, batch_size=10)

        # Should have 3 batches (10, 10, 5)
        assert len(results) == 3
        assert len(results[0]) == 10
        assert len(results[1]) == 10
        assert len(results[2]) == 5

        # Check first item in each batch
        assert results[0][0] == "Batch_0"
        assert results[1][0] == "Batch_10"
        assert results[2][0] == "Batch_20"

    def test_add_index(self, db_manager):
        """Test adding an index."""
        # Add an index
        success = db_manager.add_index("test_models", ["name", "value"])
        assert success == True

        # Check if index exists in SQLite (different for PostgreSQL)
        with db_manager.engine.connect() as conn:
            result = conn.execute(text("PRAGMA index_list('test_models')"))
            indexes = [row[1] for row in result]
            assert "idx_test_models_name_value" in indexes

    def test_get_database_stats(self, db_manager):
        """Test getting database stats."""
        # Add some data first
        with db_manager.session() as session:
            for i in range(5):
                session.add(TestModel(name=f"Stats_{i}", value=f"Value_{i}"))

        # Get stats
        stats = db_manager.get_database_stats()

        # Check basic stats
        assert stats["database_type"] == "sqlite"
        assert "test_models" in stats["tables"]
        assert stats["table_counts"]["test_models"] >= 5

    def test_global_functions(self, temp_db_path):
        """Test the global utility functions."""
        # Override the global manager for testing
        from ztoq.database_connection_manager import _default_manager
        old_manager = _default_manager

        try:
            # Create a test manager and set it as the global manager
            manager = DatabaseConnectionManager(
                db_url=temp_db_path,
                enable_metrics=False,
            )

            # Create the test table
            TestBase.metadata.create_all(manager.engine)

            from ztoq.database_connection_manager import _default_manager
            _default_manager = manager

            # Test get_connection_manager
            assert get_connection_manager() == manager

            # Test get_session
            with get_session() as session:
                session.add(TestModel(name="Global1", value="GlobalValue1"))

            # Test transaction
            with transaction() as session:
                session.add(TestModel(name="Global2", value="GlobalValue2"))

            # Test execute_query
            results = execute_query("SELECT * FROM test_models WHERE name LIKE :pattern", {"pattern": "Global%"})
            assert len(results) == 2
        finally:
            # Restore the original manager
            from ztoq.database_connection_manager import _default_manager
            _default_manager = old_manager
