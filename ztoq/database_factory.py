"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Database factory module that provides a unified interface for creating and managing
database connections based on configuration settings.

This module allows the application to choose between SQLite and PostgreSQL database
implementations based on configuration, following the Factory pattern.
"""

import logging
import os
from typing import Any, Optional, TypeVar, Union
from ztoq.core.db_manager import DatabaseConfig, SQLDatabaseManager
from ztoq.database_manager import DatabaseManager
from ztoq.pg_database_manager import PostgreSQLDatabaseManager

logger = logging.getLogger(__name__)

# Type variable for database managers
T = TypeVar("T", bound=Union[DatabaseManager, SQLDatabaseManager, PostgreSQLDatabaseManager])


class DatabaseType:
    """Database type constants."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    SQLALCHEMY = "sqlalchemy"  # For the SQLAlchemy-based implementation


class DatabaseFactory:
    """
    Factory class for creating database manager instances based on configuration.

    This class provides methods for creating and retrieving database managers, abstracting
    away the details of which database implementation is being used.
    """

    @staticmethod
    def create_database_manager(
        db_type: str,
            db_path: Optional[str] = None,
            host: Optional[str] = None,
            port: Optional[int] = None,
            username: Optional[str] = None,
            password: Optional[str] = None,
            database: Optional[str] = None,
            min_connections: int = 5,
            max_connections: int = 20,
            pool_size: int = 5,
            max_overflow: int = 10,
            echo: bool = False,
        ) -> Union[DatabaseManager, SQLDatabaseManager, PostgreSQLDatabaseManager]:
        """
        Create a database manager based on configuration.

        Args:
            db_type: Database type (sqlite, postgresql, sqlalchemy)
            db_path: Path to SQLite database file (for SQLite)
            host: Database host (for PostgreSQL)
            port: Database port (for PostgreSQL)
            username: Database username (for PostgreSQL)
            password: Database password (for PostgreSQL)
            database: Database name (for PostgreSQL)
            min_connections: Minimum number of connections in the pool (for PostgreSQL)
            max_connections: Maximum number of connections in the pool (for PostgreSQL)
            pool_size: Connection pool size (for SQLAlchemy)
            max_overflow: Maximum number of connections to overflow (for SQLAlchemy)
            echo: Whether to echo SQL statements (for SQLAlchemy)

        Returns:
            Database manager instance
        """
        # Check for environment variables if not provided directly (PostgreSQL)
        if db_type == DatabaseType.POSTGRESQL and not all([host, username, database]):
            env_host = os.environ.get("ZTOQ_PG_HOST")
            env_port = os.environ.get("ZTOQ_PG_PORT")
            env_user = os.environ.get("ZTOQ_PG_USER")
            env_pass = os.environ.get("ZTOQ_PG_PASSWORD")
            env_db = os.environ.get("ZTOQ_PG_DATABASE")

            if env_host and env_user and env_db:
                host = env_host
                port = int(env_port) if env_port else 5432
                username = env_user
                password = env_pass
                database = env_db
                logger.info("Using PostgreSQL settings from environment variables")

        # Create the appropriate database manager based on type
        if db_type == DatabaseType.SQLITE:
            logger.info(f"Creating SQLite database manager with path: {db_path}")
            return DatabaseManager(db_path=db_path)

        elif db_type == DatabaseType.POSTGRESQL:
            if not all([host, username, database]):
                raise ValueError("Host, username, and database name are required for PostgreSQL")

            logger.info(f"Creating PostgreSQL database manager for {database} on {host}:{port}")
            return PostgreSQLDatabaseManager(
                host=host,
                    database=database,
                    user=username,
                    password=password,
                    port=port or 5432,
                    min_connections=min_connections,
                    max_connections=max_connections
            )

        elif db_type == DatabaseType.SQLALCHEMY:
            logger.info(f"Creating SQLAlchemy database manager")
            # Create database configuration
            db_config = DatabaseConfig(
                db_type=DatabaseType.SQLITE if not host else DatabaseType.POSTGRESQL,
                    db_path=db_path,
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    database=database,
                    pool_size=pool_size,
                    max_overflow=max_overflow,
                    echo=echo,
                )
            return SQLDatabaseManager(config=db_config)

        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    @staticmethod
    def from_config(config: dict[str, Any]) -> Union[DatabaseManager, SQLDatabaseManager, PostgreSQLDatabaseManager]:
        """
        Create a database manager from a configuration dictionary.

        Args:
            config: Configuration dictionary with database settings

        Returns:
            Database manager instance
        """
        db_type = config.get("db_type", DatabaseType.SQLITE)

        return DatabaseFactory.create_database_manager(
            db_type=db_type,
                db_path=config.get("db_path"),
                host=config.get("host"),
                port=config.get("port"),
                username=config.get("username"),
                password=config.get("password"),
                database=config.get("database"),
                min_connections=config.get("min_connections", 5),
                max_connections=config.get("max_connections", 20),
                pool_size=config.get("pool_size", 5),
                max_overflow=config.get("max_overflow", 10),
                echo=config.get("echo", False),
            )


def get_database_manager(
    db_type: str = os.environ.get("ZTOQ_DB_TYPE", DatabaseType.SQLITE),
        db_path: Optional[str] = os.environ.get("ZTOQ_DB_PATH"),
        host: Optional[str] = os.environ.get("ZTOQ_PG_HOST"),
        port: Optional[int] = int(os.environ.get("ZTOQ_PG_PORT", "5432")) if os.environ.get("ZTOQ_PG_PORT") else None,
        username: Optional[str] = os.environ.get("ZTOQ_PG_USER"),
        password: Optional[str] = os.environ.get("ZTOQ_PG_PASSWORD"),
        database: Optional[str] = os.environ.get("ZTOQ_PG_DATABASE"),
) -> Union[DatabaseManager, SQLDatabaseManager, PostgreSQLDatabaseManager]:
    """
    Helper function to get a database manager using environment variables or defaults.

    This function provides a convenient way to get a database manager with environment
    variable fallbacks, making it easy to configure the database through environment.

    Args:
        db_type: Database type
        db_path: Path to SQLite database file
        host: PostgreSQL host
        port: PostgreSQL port
        username: PostgreSQL username
        password: PostgreSQL password
        database: PostgreSQL database name

    Returns:
        Database manager instance
    """
    return DatabaseFactory.create_database_manager(
        db_type=db_type,
            db_path=db_path,
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
        )
