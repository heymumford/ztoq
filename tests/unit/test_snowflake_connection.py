"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Unit tests for Snowflake database connection functionality.

These tests verify the Snowflake database connection and operations,
ensuring proper integration with the application's database abstraction layer.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.engine import Engine

# Import only the database config to avoid circular imports
from ztoq.core.db_manager import DatabaseConfig, SQLDatabaseManager


@pytest.mark.unit
class TestSnowflakeConnection:
    """Test cases for Snowflake database connection."""

    def test_snowflake_connection_string(self):
        """Test generating the correct Snowflake connection string."""
        # Create a configuration for Snowflake
        config = DatabaseConfig(
            db_type="snowflake",
            account="testaccount",
            username="testuser",
            password="testpass",
            database="testdb",
            warehouse="testwh",
            schema="testschema",
            role="testrole",
        )

        # Use a patched create_engine to avoid actual connection attempts
        with patch("sqlalchemy.create_engine") as mock_create_engine:
            mock_engine = MagicMock(spec=Engine)
            mock_create_engine.return_value = mock_engine

            # Create the database manager with our config
            db_manager = SQLDatabaseManager(config)

            # Verify the connection string was correctly formed
            mock_create_engine.assert_called_once()
            conn_str = mock_create_engine.call_args[0][0]

            # Check the connection string contains the expected Snowflake parameters
            assert "snowflake://" in conn_str
            assert "testuser" in conn_str
            assert "testaccount" in conn_str
            assert "testdb" in conn_str
            assert "warehouse=testwh" in conn_str
            assert "schema=testschema" in conn_str
            assert "role=testrole" in conn_str

    def test_snowflake_database_type(self):
        """Test creating a database manager with Snowflake database type."""
        # Mock the create_engine function to avoid actual connection attempts
        with patch("sqlalchemy.create_engine") as mock_create_engine:
            mock_engine = MagicMock(spec=Engine)
            mock_create_engine.return_value = mock_engine

            # Create database config for Snowflake
            config = DatabaseConfig(
                db_type="snowflake",
                account="testaccount",
                username="testuser",
                password="testpass",
                database="testdb",
                warehouse="testwh",
                schema="testschema",
                role="testrole",
            )

            # Create the database manager directly
            manager = SQLDatabaseManager(config)

            # Verify the manager is created and properly configured
            assert isinstance(manager, SQLDatabaseManager)
            assert manager.config.db_type == "snowflake"
            assert manager.config.account == "testaccount"
            assert manager.config.username == "testuser"
            assert manager.config.database == "testdb"
            assert manager.config.warehouse == "testwh"
            assert manager.config.schema == "testschema"
            assert manager.config.role == "testrole"

    def test_snowflake_environment_variables(self):
        """Test creating a Snowflake manager from environment variables."""
        # This test will mock the environment variable parsing
        # Mock a DatabaseConfig object with attributes from environment variables
        mock_config = MagicMock(spec=DatabaseConfig)
        mock_config.db_type = "snowflake"
        mock_config.account = "envaccount"
        mock_config.username = "envuser"
        mock_config.password = "envpass"
        mock_config.database = "envdb"
        mock_config.warehouse = "envwh"
        mock_config.schema = "envschema"
        mock_config.role = "envrole"

        # Mock create_engine to avoid actual connection
        with patch("sqlalchemy.create_engine") as mock_create_engine:
            mock_engine = MagicMock(spec=Engine)
            mock_create_engine.return_value = mock_engine

            # Mock the DatabaseConfig constructor
            with patch("ztoq.core.db_manager.DatabaseConfig", return_value=mock_config):
                # Create a database manager directly with mocked config
                manager = SQLDatabaseManager()

                # Verify the manager is configured with our mock config
                assert manager.config.db_type == "snowflake"
                assert manager.config.account == "envaccount"
                assert manager.config.username == "envuser"
                assert manager.config.password == "envpass"
                assert manager.config.database == "envdb"
                assert manager.config.warehouse == "envwh"
                assert manager.config.schema == "envschema"
                assert manager.config.role == "envrole"

    def test_snowflake_transaction_management(self):
        """Test transaction management with Snowflake database."""
        # Create a configuration for Snowflake
        config = DatabaseConfig(
            db_type="snowflake",
            account="testaccount",
            username="testuser",
            password="testpass",
            database="testdb",
            warehouse="testwh",
        )

        # Mock the engine and session
        with patch("sqlalchemy.create_engine") as mock_create_engine:
            mock_engine = MagicMock(spec=Engine)
            mock_create_engine.return_value = mock_engine

            # Mock the session factory and session
            mock_session_factory = MagicMock()
            mock_session = MagicMock()
            mock_scoped_session = MagicMock()
            mock_scoped_session.return_value = mock_session

            # Create the database manager
            with patch("sqlalchemy.orm.sessionmaker", return_value=mock_session_factory):
                with patch("sqlalchemy.orm.scoped_session", return_value=mock_scoped_session):
                    db_manager = SQLDatabaseManager(config)

                    # Test the session context manager
                    with db_manager.get_session() as session:
                        # Do some operations
                        session.execute("SELECT 1")

                    # Verify commit was called
                    mock_session.commit.assert_called_once()
                    mock_session.close.assert_called_once()

    def test_snowflake_error_handling(self):
        """Test handling errors with Snowflake database."""
        # Create a configuration for Snowflake
        config = DatabaseConfig(
            db_type="snowflake",
            account="testaccount",
            username="testuser",
            password="testpass",
            database="testdb",
        )

        # Mock the engine and session
        with patch("sqlalchemy.create_engine") as mock_create_engine:
            mock_engine = MagicMock(spec=Engine)
            mock_create_engine.return_value = mock_engine

            # Mock the session factory and session with an error
            mock_session_factory = MagicMock()
            mock_session = MagicMock()
            mock_session.commit.side_effect = Exception("Test error")
            mock_scoped_session = MagicMock(return_value=mock_session)

            # Create the database manager
            with patch("sqlalchemy.orm.sessionmaker", return_value=mock_session_factory):
                with patch("sqlalchemy.orm.scoped_session", return_value=mock_scoped_session):
                    db_manager = SQLDatabaseManager(config)

                    # Test the session context manager with an error
                    with pytest.raises(Exception) as excinfo:
                        with db_manager.get_session() as session:
                            # Do some operations
                            session.execute("SELECT 1")

                    # Verify rollback was called
                    assert "Test error" in str(excinfo.value)
                    mock_session.rollback.assert_called_once()
                    mock_session.close.assert_called_once()

    def test_snowflake_connection_pooling(self):
        """Test connection pooling settings with Snowflake."""
        # Create a configuration for Snowflake with pooling settings
        config = DatabaseConfig(
            db_type="snowflake",
            account="testaccount",
            username="testuser",
            password="testpass",
            database="testdb",
            pool_size=10,
            max_overflow=20,
            pool_timeout=60,
            pool_recycle=1800,
        )

        # Mock create_engine to capture connection args
        with patch("sqlalchemy.create_engine") as mock_create_engine:
            mock_engine = MagicMock(spec=Engine)
            mock_create_engine.return_value = mock_engine

            # Create the database manager
            db_manager = SQLDatabaseManager(config)

            # Verify create_engine was called with correct pool settings
            mock_create_engine.assert_called_once()
            kwargs = mock_create_engine.call_args[1]

            # Check pool settings
            assert kwargs["pool_size"] == 10
            assert kwargs["max_overflow"] == 20

            # Check pre_ping is enabled
            assert kwargs.get("pool_pre_ping", False) is True

    def test_snowflake_schema_creation(self):
        """Test creating database schema in Snowflake."""
        # Create a configuration for Snowflake
        config = DatabaseConfig(
            db_type="snowflake",
            account="testaccount",
            username="testuser",
            password="testpass",
            database="testdb",
        )

        # Mock the engine and metadata
        with patch("sqlalchemy.create_engine") as mock_create_engine:
            mock_engine = MagicMock(spec=Engine)
            mock_create_engine.return_value = mock_engine

            # Create the database manager
            db_manager = SQLDatabaseManager(config)

            # Mock Base.metadata.create_all to avoid actual schema creation
            with patch("ztoq.core.db_models.Base.metadata.create_all") as mock_create_all:
                # Initialize the database
                db_manager.initialize_database()

                # Verify create_all was called with our engine
                mock_create_all.assert_called_once_with(mock_engine)

if __name__ == "__main__":
    unittest.main()
