"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
SQLAlchemy-based database manager with support for PostgreSQL and SQLite.

This module implements a database manager using SQLAlchemy ORM for handling
both PostgreSQL and SQLite databases with appropriate connection pooling,
transaction management, and database-specific optimizations.
"""

import logging
import os
import threading
import time
from contextlib import contextmanager
from typing import Any, TypeVar

from sqlalchemy import create_engine, event, exc, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Query, Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from ztoq.core.db_models import Base

# Type variable for entity models
T = TypeVar("T", bound=DeclarativeMeta)

logger = logging.getLogger(__name__)


class SQLDatabaseManager:
    """
    SQLAlchemy-based database manager with support for PostgreSQL and SQLite.
    
    This class implements connection pooling, transaction management, 
    ORM operations, and database-specific optimizations.
    """

    def __init__(
        self,
        db_url: str | None = None,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        echo: bool = False,
        echo_pool: bool = False,
        create_tables: bool = False,
    ):
        """
        Initialize the database manager.
        
        Args:
            db_url: Database connection URL. If None, will use environment variables
            pool_size: Size of the connection pool
            max_overflow: Maximum overflow connections
            pool_timeout: Timeout for acquiring connections
            pool_recycle: Recycle connections after this many seconds
            echo: Echo SQL statements
            echo_pool: Echo connection pool activity
            create_tables: Create tables on initialization if True

        """
        self.db_url = db_url or self._get_db_url_from_env()
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo = echo
        self.echo_pool = echo_pool

        # Determine database type
        self.is_sqlite = self.db_url.startswith("sqlite:")
        self.is_postgresql = self.db_url.startswith("postgresql:")

        # Create engine and session factory
        self.engine = self._create_engine()
        self.session_factory = sessionmaker(bind=self.engine)

        # Configure database-specific settings
        if self.is_sqlite:
            self._configure_sqlite()
        elif self.is_postgresql:
            self._configure_postgresql()

        # Create tables if requested
        if create_tables:
            Base.metadata.create_all(self.engine)

        # Thread-local session storage
        self._session_storage = threading.local()

    def _get_db_url_from_env(self) -> str:
        """
        Get database URL from environment variables.
        
        Returns:
            str: Database connection URL

        """
        # Check for PostgreSQL environment variables
        pg_host = os.environ.get("ZTOQ_PG_HOST")
        pg_port = os.environ.get("ZTOQ_PG_PORT", "5432")
        pg_user = os.environ.get("ZTOQ_PG_USER")
        pg_pass = os.environ.get("ZTOQ_PG_PASSWORD", "")
        pg_db = os.environ.get("ZTOQ_PG_DATABASE")

        # If PostgreSQL environment variables are set, use PostgreSQL
        if all([pg_host, pg_user, pg_db]):
            return f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"

        # Otherwise, fall back to SQLite
        sqlite_path = os.environ.get("ZTOQ_SQLITE_PATH", "ztoq_data.db")
        return f"sqlite:///{sqlite_path}"

    def _create_engine(self) -> Engine:
        """
        Create SQLAlchemy engine with appropriate connection pooling.
        
        Returns:
            Engine: SQLAlchemy engine instance

        """
        kwargs = {
            "echo": self.echo,
            "echo_pool": self.echo_pool,
        }

        # SQLite-specific engine configuration
        if self.is_sqlite:
            # Use NullPool for SQLite to avoid threading issues
            kwargs["poolclass"] = NullPool

        # PostgreSQL-specific engine configuration
        elif self.is_postgresql:
            kwargs["poolclass"] = QueuePool
            kwargs["pool_size"] = self.pool_size
            kwargs["max_overflow"] = self.max_overflow
            kwargs["pool_timeout"] = self.pool_timeout
            kwargs["pool_recycle"] = self.pool_recycle

            # Optional: Enable server-side prepared statements for repeated queries
            kwargs["connect_args"] = {"options": "-c statement_timeout=30000"}

        return create_engine(self.db_url, **kwargs)

    def _configure_sqlite(self) -> None:
        """Configure SQLite-specific optimizations."""
        # Set pragma options for better SQLite performance
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            cursor.execute("PRAGMA synchronous=NORMAL")  # fsync only in critical moments
            cursor.execute("PRAGMA cache_size=-10000")  # 10MB page cache
            cursor.execute("PRAGMA foreign_keys=ON")  # Enable foreign key constraints
            cursor.execute("PRAGMA temp_store=MEMORY")  # Store temporary tables in memory
            cursor.close()

    def _configure_postgresql(self) -> None:
        """Configure PostgreSQL-specific optimizations."""
        # No specific configurations needed at engine level
        # Most PostgreSQL-specific options are set in the connection parameters

    @contextmanager
    def session(self) -> Session:
        """
        Get a database session in a context manager.
        
        Yields:
            Session: SQLAlchemy database session

        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e!s}")
            raise
        finally:
            session.close()

    @property
    def thread_session(self) -> Session:
        """
        Get a thread-local session.
        
        This provides a single session per thread that can be reused
        within the same thread context.
        
        Returns:
            Session: Thread-local SQLAlchemy session

        """
        if not hasattr(self._session_storage, "session"):
            self._session_storage.session = self.session_factory()
        return self._session_storage.session

    def close_thread_session(self) -> None:
        """Close the thread-local session if it exists."""
        if hasattr(self._session_storage, "session"):
            self._session_storage.session.close()
            del self._session_storage.session

    @contextmanager
    def transaction(self, session: Session | None = None) -> Session:
        """
        Execute operations in a transaction with explicit savepoints.
        
        Args:
            session: Optional existing session to use
        
        Yields:
            Session: SQLAlchemy session with transaction

        """
        # Use provided session or create a new one
        close_after = False
        if session is None:
            session = self.session_factory()
            close_after = True

        # Create a savepoint
        savepoint = session.begin_nested()

        try:
            yield session
            savepoint.commit()
        except Exception:
            savepoint.rollback()
            raise
        finally:
            if close_after:
                session.close()

    def check_connectivity(self) -> bool:
        """
        Check database connectivity.
        
        Returns:
            bool: True if connection successful, False otherwise

        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except exc.SQLAlchemyError:
            logger.exception("Database connection check failed")
            return False

    def execute_raw_sql(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Execute raw SQL and return results as dictionaries.
        
        Args:
            sql: SQL statement to execute
            params: Optional parameters for SQL statement
        
        Returns:
            List[Dict[str, Any]]: Query results as list of dictionaries

        """
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            return [dict(row._mapping) for row in result]

    def create_all_tables(self) -> None:
        """Create all tables defined in the Base metadata."""
        Base.metadata.create_all(self.engine)

    def drop_all_tables(self) -> None:
        """Drop all tables defined in the Base metadata."""
        Base.metadata.drop_all(self.engine)

    def get_table_names(self) -> list[str]:
        """
        Get all table names in the database.
        
        Returns:
            List[str]: List of table names

        """
        inspector = inspect(self.engine)
        return inspector.get_table_names()

    def vacuum(self) -> None:
        """
        Perform database vacuum operation for SQLite.
        
        This reclaims space and defragments the database file.
        """
        if self.is_sqlite:
            with self.engine.connect() as conn:
                conn.execute(text("VACUUM"))

    def analyze(self) -> None:
        """
        Perform database analyze operation.
        
        This updates statistics used by the query planner.
        """
        with self.engine.connect() as conn:
            conn.execute(text("ANALYZE"))

    # Generic CRUD operations

    def create(self, model: T, commit: bool = True) -> T:
        """
        Create a new record in the database.
        
        Args:
            model: The model instance to create
            commit: Whether to commit the transaction immediately
        
        Returns:
            The created model instance

        """
        with self.session() as session:
            session.add(model)
            if commit:
                session.commit()
                session.refresh(model)
            return model

    def get_by_id(self, model_class: type[T], id_value: Any) -> T | None:
        """
        Get a record by its primary key.
        
        Args:
            model_class: The model class
            id_value: The primary key value
        
        Returns:
            The model instance or None if not found

        """
        with self.session() as session:
            return session.get(model_class, id_value)

    def get_by_field(self, model_class: type[T], field_name: str, value: Any) -> T | None:
        """
        Get the first record matching a field value.
        
        Args:
            model_class: The model class
            field_name: The field name
            value: The field value
        
        Returns:
            The model instance or None if not found

        """
        with self.session() as session:
            return session.query(model_class).filter(getattr(model_class, field_name) == value).first()

    def get_all(self, model_class: type[T]) -> list[T]:
        """
        Get all records of a model class.
        
        Args:
            model_class: The model class
        
        Returns:
            List of model instances

        """
        with self.session() as session:
            return session.query(model_class).all()

    def update(self, model: T, commit: bool = True) -> T:
        """
        Update a record in the database.
        
        Args:
            model: The model instance to update
            commit: Whether to commit the transaction immediately
        
        Returns:
            The updated model instance

        """
        with self.session() as session:
            session.add(model)
            if commit:
                session.commit()
                session.refresh(model)
            return model

    def delete(self, model: T, commit: bool = True) -> None:
        """
        Delete a record from the database.
        
        Args:
            model: The model instance to delete
            commit: Whether to commit the transaction immediately

        """
        with self.session() as session:
            session.delete(model)
            if commit:
                session.commit()

    def bulk_create(self, models: list[T], batch_size: int = 1000, commit: bool = True) -> list[T]:
        """
        Bulk create records in the database.
        
        Args:
            models: List of model instances to create
            batch_size: Number of records to insert in each batch
            commit: Whether to commit the transaction immediately
        
        Returns:
            List of created model instances

        """
        if not models:
            return []

        with self.session() as session:
            for i in range(0, len(models), batch_size):
                batch = models[i:i+batch_size]
                session.add_all(batch)
                if commit:
                    session.commit()
                    for model in batch:
                        session.refresh(model)

            return models

    def bulk_update(self, models: list[T], batch_size: int = 1000, commit: bool = True) -> list[T]:
        """
        Bulk update records in the database.
        
        Args:
            models: List of model instances to update
            batch_size: Number of records to update in each batch
            commit: Whether to commit the transaction immediately
        
        Returns:
            List of updated model instances

        """
        if not models:
            return []

        with self.session() as session:
            for i in range(0, len(models), batch_size):
                batch = models[i:i+batch_size]
                for model in batch:
                    session.add(model)
                if commit:
                    session.commit()
                    for model in batch:
                        session.refresh(model)

            return models

    def bulk_delete(self, models: list[T], batch_size: int = 1000, commit: bool = True) -> None:
        """
        Bulk delete records from the database.
        
        Args:
            models: List of model instances to delete
            batch_size: Number of records to delete in each batch
            commit: Whether to commit the transaction immediately

        """
        if not models:
            return

        with self.session() as session:
            for i in range(0, len(models), batch_size):
                batch = models[i:i+batch_size]
                for model in batch:
                    session.delete(model)
                if commit:
                    session.commit()

    # Performance optimization methods

    def add_index(self, table_name: str, column_names: list[str], index_name: str | None = None) -> bool:
        """
        Add an index to a table.
        
        Args:
            table_name: Name of the table
            column_names: List of column names to include in the index
            index_name: Optional name for the index
        
        Returns:
            bool: True if index was created, False otherwise

        """
        try:
            if not index_name:
                index_name = f"idx_{table_name}_{'_'.join(column_names)}"

            columns_str = ", ".join(column_names)
            sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns_str})"

            with self.engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()

            return True
        except Exception as e:
            logger.error(f"Error adding index: {e!s}")
            return False

    def explain_query(self, query: Query) -> list[dict[str, Any]]:
        """
        Get the query execution plan.
        
        Args:
            query: SQLAlchemy query object
        
        Returns:
            List[Dict[str, Any]]: Query execution plan

        """
        try:
            with self.session() as session:
                if self.is_postgresql:
                    sql = "EXPLAIN (FORMAT JSON) " + str(query.statement.compile(
                        compile_kwargs={"literal_binds": True},
                    ))
                    result = session.execute(text(sql))
                    return result.scalar()
                sql = "EXPLAIN QUERY PLAN " + str(query.statement.compile(
                    compile_kwargs={"literal_binds": True},
                ))
                result = session.execute(text(sql))
                return [dict(row._mapping) for row in result]
        except Exception as e:
            logger.error(f"Error explaining query: {e!s}")
            return []

    def measure_query(self, query: Query) -> dict[str, Any]:
        """
        Measure the execution time of a query.
        
        Args:
            query: SQLAlchemy query object
        
        Returns:
            Dict[str, Any]: Query execution metrics

        """
        try:
            with self.session() as session:
                start_time = time.time()
                result = session.execute(query.statement)
                rows = result.all()
                end_time = time.time()

                execution_time = end_time - start_time
                row_count = len(rows)

                return {
                    "execution_time_ms": execution_time * 1000,
                    "row_count": row_count,
                    "rows_per_second": row_count / execution_time if execution_time > 0 else 0,
                }
        except Exception as e:
            logger.error(f"Error measuring query: {e!s}")
            return {
                "execution_time_ms": 0,
                "row_count": 0,
                "rows_per_second": 0,
                "error": str(e),
            }


# Global database manager instance
_default_sql_db_manager = None


def get_sql_db_manager() -> SQLDatabaseManager:
    """
    Get the default SQL database manager instance.
    
    This creates a singleton instance if it doesn't exist yet.
    
    Returns:
        SQLDatabaseManager: The default SQL database manager instance

    """
    global _default_sql_db_manager
    if _default_sql_db_manager is None:
        _default_sql_db_manager = SQLDatabaseManager()
    return _default_sql_db_manager


@contextmanager
def get_db_session() -> Session:
    """
    Get a database session from the default SQL manager.
    
    This is a convenience function for getting a session from
    the default SQL database manager.
    
    Yields:
        Session: SQLAlchemy database session

    """
    with get_sql_db_manager().session() as session:
        yield session


@contextmanager
def sql_transaction(session: Session | None = None) -> Session:
    """
    Execute operations in a transaction using default SQL manager.
    
    This is a convenience function for creating a transaction
    using the default SQL database manager.
    
    Args:
        session: Optional existing session to use
    
    Yields:
        Session: SQLAlchemy session with transaction

    """
    with get_sql_db_manager().transaction(session=session) as session:
        yield session
