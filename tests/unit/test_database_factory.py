"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import unittest
from unittest.mock import patch, MagicMock
from ztoq.database_factory import DatabaseFactory, DatabaseType, get_database_manager
from ztoq.database_manager import DatabaseManager
from ztoq.pg_database_manager import PostgreSQLDatabaseManager
from ztoq.core.db_manager import SQLDatabaseManager

class TestDatabaseFactory(unittest.TestCase):
    """Test cases for the DatabaseFactory class."""

    def test_create_sqlite_manager(self):
        """Test creating a SQLite database manager."""
        db_path = "/tmp/test.db"
        manager = DatabaseFactory.create_database_manager(db_type=DatabaseType.SQLITE, db_path=db_path)

        self.assertIsInstance(manager, DatabaseManager)
        self.assertEqual(manager.db_path, db_path)

    @patch('ztoq.pg_database_manager.pool.ThreadedConnectionPool')
    @patch('ztoq.pg_database_manager.create_engine')
    def test_create_postgresql_manager(self, mock_create_engine, mock_connection_pool):
        """Test creating a PostgreSQL database manager."""
        # Mock the connection pool
        mock_pool = MagicMock()
        mock_connection_pool.return_value = mock_pool

        # Mock the SQLAlchemy engine
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        manager = DatabaseFactory.create_database_manager(
            db_type=DatabaseType.POSTGRESQL,
                host="localhost",
                port=5432,
                username="testuser",
                password="testpass",
                database="testdb"
        )

        self.assertIsInstance(manager, PostgreSQLDatabaseManager)
        self.assertEqual(manager.connection_params["host"], "localhost")
        self.assertEqual(manager.connection_params["port"], 5432)
        self.assertEqual(manager.connection_params["user"], "testuser")
        self.assertEqual(manager.connection_params["password"], "testpass")
        self.assertEqual(manager.connection_params["database"], "testdb")

    def test_create_sqlalchemy_manager(self):
        """Test creating a SQLAlchemy database manager."""
        # Test with SQLite configuration
        manager = DatabaseFactory.create_database_manager(
            db_type=DatabaseType.SQLALCHEMY,
                db_path="/tmp/test.db"
        )

        self.assertIsInstance(manager, SQLDatabaseManager)
        self.assertEqual(manager.config.db_type, DatabaseType.SQLITE)
        self.assertEqual(manager.config.db_path, "/tmp/test.db")

        # Test with PostgreSQL configuration
        with patch('ztoq.core.db_manager.create_engine') as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine

            manager = DatabaseFactory.create_database_manager(
                db_type=DatabaseType.SQLALCHEMY,
                    host="localhost",
                    port=5432,
                    username="testuser",
                    password="testpass",
                    database="testdb"
            )

            self.assertIsInstance(manager, SQLDatabaseManager)
            self.assertEqual(manager.config.db_type, DatabaseType.POSTGRESQL)
            self.assertEqual(manager.config.host, "localhost")
            self.assertEqual(manager.config.port, 5432)
            self.assertEqual(manager.config.username, "testuser")
            self.assertEqual(manager.config.password, "testpass")
            self.assertEqual(manager.config.database, "testdb")

    def test_from_config(self):
        """Test creating a database manager from a configuration dictionary."""
        # Test with SQLite configuration
        config = {
            "db_type": DatabaseType.SQLITE,
                "db_path": "/tmp/test.db"
        }

        manager = DatabaseFactory.from_config(config)
        self.assertIsInstance(manager, DatabaseManager)
        self.assertEqual(manager.db_path, "/tmp/test.db")

        # Test with PostgreSQL configuration
        with patch('ztoq.pg_database_manager.pool.ThreadedConnectionPool') as mock_connection_pool:
            with patch('ztoq.pg_database_manager.create_engine') as mock_create_engine:
                mock_pool = MagicMock()
                mock_connection_pool.return_value = mock_pool

                mock_engine = MagicMock()
                mock_create_engine.return_value = mock_engine

                config = {
                    "db_type": DatabaseType.POSTGRESQL,
                        "host": "localhost",
                        "port": 5432,
                        "username": "testuser",
                        "password": "testpass",
                        "database": "testdb",
                        "min_connections": 10,
                        "max_connections": 30
                }

                manager = DatabaseFactory.from_config(config)
                self.assertIsInstance(manager, PostgreSQLDatabaseManager)
                self.assertEqual(manager.connection_params["host"], "localhost")
                self.assertEqual(manager.connection_params["port"], 5432)
                self.assertEqual(manager.connection_params["user"], "testuser")
                self.assertEqual(manager.connection_params["password"], "testpass")
                self.assertEqual(manager.connection_params["database"], "testdb")

    @patch('os.environ.get')
    def test_get_database_manager(self, mock_environ_get):
        """Test the get_database_manager helper function."""
        # Mock environment variables
        def mock_env(var, default=None):
            env_vars = {
                "ZTOQ_DB_TYPE": DatabaseType.SQLITE,
                    "ZTOQ_DB_PATH": "/tmp/env_test.db"
            }
            return env_vars.get(var, default)

        mock_environ_get.side_effect = mock_env

        # Test with environment variables
        manager = get_database_manager()
        self.assertIsInstance(manager, DatabaseManager)
        self.assertEqual(manager.db_path, "/tmp/env_test.db")

        # Test with direct parameters (overriding environment)
        manager = get_database_manager(db_type=DatabaseType.SQLITE, db_path="/tmp/direct_test.db")
        self.assertIsInstance(manager, DatabaseManager)
        self.assertEqual(manager.db_path, "/tmp/direct_test.db")

        # Test PostgreSQL with environment variables
        def mock_pg_env(var, default=None):
            env_vars = {
                "ZTOQ_DB_TYPE": DatabaseType.POSTGRESQL,
                    "ZTOQ_PG_HOST": "pg-host",
                    "ZTOQ_PG_PORT": "5433",
                    "ZTOQ_PG_USER": "pg-user",
                    "ZTOQ_PG_PASSWORD": "pg-pass",
                    "ZTOQ_PG_DATABASE": "pg-db"
            }
            return env_vars.get(var, default)

        mock_environ_get.side_effect = mock_pg_env

        with patch('ztoq.pg_database_manager.pool.ThreadedConnectionPool') as mock_connection_pool:
            with patch('ztoq.pg_database_manager.create_engine') as mock_create_engine:
                mock_pool = MagicMock()
                mock_connection_pool.return_value = mock_pool

                mock_engine = MagicMock()
                mock_create_engine.return_value = mock_engine

                manager = get_database_manager()
                self.assertIsInstance(manager, PostgreSQLDatabaseManager)
                self.assertEqual(manager.connection_params["host"], "pg-host")
                self.assertEqual(manager.connection_params["port"], 5433)
                self.assertEqual(manager.connection_params["user"], "pg-user")
                self.assertEqual(manager.connection_params["password"], "pg-pass")
                self.assertEqual(manager.connection_params["database"], "pg-db")


if __name__ == '__main__':
    unittest.main()
