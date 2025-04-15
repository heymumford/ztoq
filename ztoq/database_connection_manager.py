"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Database connection manager with support for connection pooling and transaction management.

This module provides a comprehensive solution for managing database connections,
implementing connection pooling, transaction management with proper isolation levels,
and performance monitoring for both SQLite and PostgreSQL databases.
"""

import logging
import os
import threading
import time
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any, TypeVar

import sqlalchemy as sa

# Database metrics collection
from prometheus_client import Counter, Gauge, Histogram, Summary
from sqlalchemy import create_engine, event, exc, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from ztoq.core.db_models import Base

# Type variables for generic functions
T = TypeVar("T")
R = TypeVar("R")

logger = logging.getLogger(__name__)


class TransactionIsolationLevel:
    """Transaction isolation levels for database operations."""

    # SQLite isolation levels
    DEFERRED = "DEFERRED"
    IMMEDIATE = "IMMEDIATE"
    EXCLUSIVE = "EXCLUSIVE"

    # PostgreSQL isolation levels
    READ_UNCOMMITTED = "READ UNCOMMITTED"
    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE_READ"
    SERIALIZABLE = "SERIALIZABLE"


class DatabaseMetrics:
    """Metrics for database connection and query performance monitoring."""

    # Connection metrics
    connection_count = Gauge("ztoq_db_connections", "Number of active database connections")
    connection_errors = Counter("ztoq_db_connection_errors", "Number of database connection errors")
    connection_timeouts = Counter("ztoq_db_connection_timeouts", "Number of database connection timeouts")

    # Transaction metrics
    transaction_count = Counter("ztoq_db_transactions", "Number of database transactions")
    transaction_errors = Counter("ztoq_db_transaction_errors", "Number of database transaction errors")
    transaction_time = Histogram("ztoq_db_transaction_time", "Transaction execution time in seconds")

    # Query metrics
    query_count = Counter("ztoq_db_queries", "Number of database queries", ["operation"])
    query_errors = Counter("ztoq_db_query_errors", "Number of database query errors", ["operation"])
    query_time = Histogram("ztoq_db_query_time", "Query execution time in seconds", ["operation"])
    rows_returned = Summary("ztoq_db_rows_returned", "Number of rows returned by queries")

    # Pool metrics
    pool_size = Gauge("ztoq_db_pool_size", "Number of connections in the pool")
    pool_overflow = Gauge("ztoq_db_pool_overflow", "Number of overflow connections in use")
    pool_checkedout = Gauge("ztoq_db_pool_checkedout", "Number of connections checked out from pool")
    pool_checkin_time = Histogram("ztoq_db_pool_checkin_time", "Time to check in connections to pool")
    pool_checkout_time = Histogram("ztoq_db_pool_checkout_time", "Time to check out connections from pool")


class DatabaseConnectionManager:
    """
    Comprehensive database connection manager with pooling and transaction support.
    
    This class provides:
    1. Connection pooling with configurable parameters
    2. Transaction management with isolation level control
    3. Performance monitoring and metrics collection
    4. Support for both SQLite and PostgreSQL databases
    5. Database-specific optimizations
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
        isolation_level: str | None = None,
        enable_metrics: bool = True,
    ):
        """
        Initialize the database connection manager.
        
        Args:
            db_url: Database connection URL. If None, will use environment variables
            pool_size: Size of the connection pool
            max_overflow: Maximum overflow connections
            pool_timeout: Timeout for acquiring connections (seconds)
            pool_recycle: Recycle connections after this many seconds
            echo: Echo SQL statements
            echo_pool: Echo connection pool activity
            create_tables: Create tables on initialization if True
            isolation_level: Transaction isolation level
            enable_metrics: Whether to collect and report metrics

        """
        self.db_url = db_url or self._get_db_url_from_env()
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo = echo
        self.echo_pool = echo_pool
        self.enable_metrics = enable_metrics

        # Generate a unique ID for this connection manager instance
        self.instance_id = str(uuid.uuid4())

        # Determine database type
        self.is_sqlite = self.db_url.startswith("sqlite:")
        self.is_postgresql = self.db_url.startswith("postgresql:")

        # Default isolation level if not specified
        if isolation_level is None:
            if self.is_sqlite:
                self.isolation_level = TransactionIsolationLevel.IMMEDIATE
            else:
                self.isolation_level = TransactionIsolationLevel.READ_COMMITTED
        else:
            self.isolation_level = isolation_level

        # Create engine and session factory
        self.engine = self._create_engine()
        self.session_factory = sessionmaker(bind=self.engine)

        # Thread-local session storage for per-thread sessions
        self._session_storage = threading.local()

        # Configure database-specific settings
        if self.is_sqlite:
            self._configure_sqlite()
        elif self.is_postgresql:
            self._configure_postgresql()

        # Initialize database if needed
        if create_tables:
            self.create_all_tables()

        logger.info(f"Database connection manager initialized with URL: {self._sanitize_url(self.db_url)}")

    def _sanitize_url(self, url: str) -> str:
        """
        Sanitize database URL for logging by removing sensitive information.
        
        Args:
            url: The database URL
            
        Returns:
            Sanitized URL

        """
        if self.is_postgresql:
            # Replace password with *** in PostgreSQL URL
            import re
            return re.sub(r"(postgresql://[^:]+:)[^@]+(@.+)", r"\1***\2", url)
        return url

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
            "isolation_level": self.isolation_level,
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
            kwargs["pool_pre_ping"] = True  # Check connection health before use

            # Performance settings for PostgreSQL
            kwargs["connect_args"] = {
                "options": "-c statement_timeout=30000",  # 30-second statement timeout
            }

        engine = create_engine(self.db_url, **kwargs)

        # Add event listeners for metrics collection
        if self.enable_metrics:
            self._add_engine_metrics(engine)

        return engine

    def _add_engine_metrics(self, engine: Engine) -> None:
        """
        Add event listeners to the engine for metrics collection.
        
        Args:
            engine: SQLAlchemy engine

        """
        # Connection metrics
        @event.listens_for(engine, "connect")
        def on_connect(dbapi_conn, conn_record):
            DatabaseMetrics.connection_count.inc()

        @event.listens_for(engine, "checkout")
        def on_checkout(dbapi_conn, conn_record, conn_proxy):
            start_time = time.time()
            conn_record._checkout_time = start_time

        @event.listens_for(engine, "checkin")
        def on_checkin(dbapi_conn, conn_record):
            if hasattr(conn_record, "_checkout_time"):
                checkout_time = time.time() - conn_record._checkout_time
                DatabaseMetrics.pool_checkout_time.observe(checkout_time)
                del conn_record._checkout_time
                DatabaseMetrics.connection_count.dec()

        # Pool metrics
        if hasattr(engine.pool, "_pool"):
            @event.listens_for(engine, "engine_connect")
            def on_engine_connect(conn):
                DatabaseMetrics.pool_size.set(engine.pool.size())
                DatabaseMetrics.pool_overflow.set(engine.pool.overflow())
                DatabaseMetrics.pool_checkedout.set(engine.pool.checkedout())

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
            cursor.execute("PRAGMA busy_timeout=5000")  # 5 second busy timeout
            cursor.close()

        logger.info("SQLite optimizations configured with WAL mode and performance settings")

    def _configure_postgresql(self) -> None:
        """Configure PostgreSQL-specific optimizations."""
        # Set session configuration for better PostgreSQL performance
        @event.listens_for(self.engine, "connect")
        def set_pg_config(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("SET application_name = 'ztoq'")
            cursor.execute("SET statement_timeout = 30000")  # 30 sec timeout
            cursor.close()

        logger.info("PostgreSQL optimizations configured with statement timeout and application name")

    @contextmanager
    def session(self) -> Session:
        """
        Get a database session in a context manager.
        
        This ensures that sessions are properly closed and transactions
        are committed or rolled back appropriately.
        
        Yields:
            Session: SQLAlchemy database session

        """
        session = None

        # Record metrics
        if self.enable_metrics:
            DatabaseMetrics.transaction_count.inc()
            start_time = time.time()

        try:
            # Create a new session
            session = self.session_factory()
            yield session

            # Only commit if the session is still active and hasn't been closed
            if session and not session.closed:
                session.commit()
        except Exception as e:
            # Only attempt rollback if we have a session and it's not closed
            if session and not session.closed:
                try:
                    session.rollback()
                except Exception as rollback_error:
                    logger.error(f"Error during session rollback: {rollback_error}")

            if self.enable_metrics:
                DatabaseMetrics.transaction_errors.inc()

            # Log the original error
            logger.error(f"Database transaction error: {e!s}")

            # Re-raise the original exception
            raise
        finally:
            # Always try to close the session in the finally block
            if session:
                try:
                    if not session.closed:
                        session.close()
                except Exception as close_error:
                    logger.error(f"Error closing database session: {close_error}")

            # Record metrics for transaction time
            if self.enable_metrics and "start_time" in locals():
                DatabaseMetrics.transaction_time.observe(time.time() - start_time)

    @property
    def thread_session(self) -> Session:
        """
        Get a thread-local session.
        
        This provides a single session per thread that can be reused
        within the same thread context. The session will be automatically
        cleaned up when the thread exits to prevent memory leaks.
        
        Returns:
            Session: Thread-local SQLAlchemy session

        """
        # Register a thread clean-up function if this is the first access
        if not hasattr(self._session_storage, "_cleanup_registered"):
            import atexit

            # Define cleanup function for current thread
            def cleanup_thread_local_session(local_storage=self._session_storage):
                if hasattr(local_storage, "session"):
                    try:
                        local_storage.session.close()
                    except Exception as e:
                        logger.warning(f"Error cleaning up thread session: {e}")

                    # Remove the reference to allow garbage collection
                    if hasattr(local_storage, "session"):
                        del local_storage.session

            # Register the cleanup function to run when the thread exits
            import threading
            thread = threading.current_thread()
            if hasattr(thread, "_exitfunc"):
                old_exitfunc = thread._exitfunc
                def new_exitfunc():
                    cleanup_thread_local_session()
                    if old_exitfunc:
                        old_exitfunc()
                thread._exitfunc = new_exitfunc
            else:
                thread._exitfunc = cleanup_thread_local_session

            # Also register with atexit for the main thread
            atexit.register(cleanup_thread_local_session)

            # Mark that we've registered cleanup for this thread
            self._session_storage._cleanup_registered = True

        # Create the session if it doesn't exist
        if not hasattr(self._session_storage, "session"):
            self._session_storage.session = self.session_factory()

        return self._session_storage.session

    def close_thread_session(self) -> None:
        """Close the thread-local session if it exists."""
        if hasattr(self._session_storage, "session"):
            try:
                self._session_storage.session.close()
            except Exception as e:
                logger.warning(f"Error closing thread session: {e}")

            # Remove the reference to allow garbage collection
            del self._session_storage.session

    @contextmanager
    def transaction(
        self,
        session: Session | None = None,
        isolation_level: str | None = None,
        read_only: bool = False,
    ) -> Session:
        """
        Execute operations in a transaction with explicit savepoints and isolation level.
        
        Args:
            session: Optional existing session to use
            isolation_level: Transaction isolation level
            read_only: Whether the transaction is read-only
        
        Yields:
            Session: SQLAlchemy session with transaction

        """
        # Use provided session or create a new one
        close_after = False
        if session is None:
            session = self.session_factory()
            close_after = True

        # Set isolation level if specified
        connection = session.connection()
        if isolation_level:
            # Store original isolation level to restore it later
            orig_isolation_level = connection.get_isolation_level()
            connection.execution_options(isolation_level=isolation_level)

        # For PostgreSQL, set read-only mode if requested
        if self.is_postgresql and read_only:
            session.execute(text("SET TRANSACTION READ ONLY"))

        # Record metrics
        if self.enable_metrics:
            DatabaseMetrics.transaction_count.inc()
            start_time = time.time()

        # Create a savepoint
        try:
            savepoint = session.begin_nested()
            yield session
            savepoint.commit()
            if not close_after:
                session.commit()
        except Exception as e:
            savepoint.rollback()
            if self.enable_metrics:
                DatabaseMetrics.transaction_errors.inc()
            logger.error(f"Transaction error: {e!s}")
            raise
        finally:
            # Restore original isolation level if changed
            if isolation_level:
                connection.execution_options(isolation_level=orig_isolation_level)

            # Close session if we created it
            if close_after:
                session.commit()
                session.close()

            # Record metrics
            if self.enable_metrics:
                DatabaseMetrics.transaction_time.observe(time.time() - start_time)

    @contextmanager
    def read_only_transaction(self, session: Session | None = None) -> Session:
        """
        Execute operations in a read-only transaction.
        
        This is an optimization for operations that don't modify data, and may
        use a different connection pool or be directed to a read replica.
        
        Args:
            session: Optional existing session to use
        
        Yields:
            Session: SQLAlchemy session with read-only transaction

        """
        with self.transaction(session=session, read_only=True) as session:
            yield session

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
        except exc.SQLAlchemyError as e:
            if self.enable_metrics:
                DatabaseMetrics.connection_errors.inc()
            logger.error(f"Database connection check failed: {e!s}")
            return False

    def execute_query(
        self,
        query: str | sa.sql.Selectable,
        params: dict[str, Any] | None = None,
        session: Session | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a query and return results as dictionaries.
        
        Args:
            query: SQL query or SQLAlchemy selectable
            params: Optional parameters for the query
            session: Optional existing session to use
        
        Returns:
            List[Dict[str, Any]]: Query results as list of dictionaries

        """
        close_session = session is None

        if session is None:
            session = self.session_factory()

        # Determine operation type for metrics
        operation = "select"
        if isinstance(query, str):
            if query.strip().lower().startswith("insert"):
                operation = "insert"
            elif query.strip().lower().startswith("update"):
                operation = "update"
            elif query.strip().lower().startswith("delete"):
                operation = "delete"

        # Record metrics
        if self.enable_metrics:
            DatabaseMetrics.query_count.labels(operation=operation).inc()
            start_time = time.time()

        try:
            if isinstance(query, str):
                result = session.execute(text(query), params or {})
            else:
                result = session.execute(query, params or {})

            rows = [dict(row._mapping) for row in result]

            # Record metrics
            if self.enable_metrics:
                DatabaseMetrics.rows_returned.observe(len(rows))

            return rows
        except Exception as e:
            if self.enable_metrics:
                DatabaseMetrics.query_errors.labels(operation=operation).inc()
            logger.error(f"Query execution error: {e!s}")
            raise
        finally:
            if self.enable_metrics:
                DatabaseMetrics.query_time.labels(operation=operation).observe(time.time() - start_time)

            if close_session:
                session.close()

    def execute_batch(
        self,
        statements: list[tuple[str | sa.sql.Executable, dict[str, Any] | None]],
        session: Session | None = None,
    ) -> bool:
        """
        Execute multiple statements in a batch.
        
        Args:
            statements: List of (statement, params) tuples
            session: Optional existing session to use
        
        Returns:
            bool: True if batch execution was successful

        """
        close_session = session is None

        if session is None:
            session = self.session_factory()

        # Record metrics
        if self.enable_metrics:
            DatabaseMetrics.transaction_count.inc()
            start_time = time.time()

        try:
            for stmt, params in statements:
                if isinstance(stmt, str):
                    session.execute(text(stmt), params or {})
                else:
                    session.execute(stmt, params or {})

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            if self.enable_metrics:
                DatabaseMetrics.transaction_errors.inc()
            logger.error(f"Batch execution error: {e!s}")
            return False
        finally:
            if self.enable_metrics:
                DatabaseMetrics.transaction_time.observe(time.time() - start_time)

            if close_session:
                session.close()

    def create_all_tables(self) -> None:
        """Create all tables defined in the Base metadata."""
        Base.metadata.create_all(self.engine)
        logger.info("Created all database tables")

    def drop_all_tables(self) -> None:
        """Drop all tables defined in the Base metadata."""
        Base.metadata.drop_all(self.engine)
        logger.info("Dropped all database tables")

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
            logger.info("Performed VACUUM on SQLite database")

    def analyze(self) -> None:
        """
        Perform database analyze operation.
        
        This updates statistics used by the query planner.
        """
        with self.engine.connect() as conn:
            conn.execute(text("ANALYZE"))
        logger.info("Performed ANALYZE on database")

    def execute_in_batches(
        self,
        query_fn: Callable[[Session, int, int], list[T]],
        process_fn: Callable[[list[T]], R],
        batch_size: int = 1000,
    ) -> list[R]:
        """
        Execute a query in batches and process each batch.
        
        This is useful for processing large result sets without loading
        everything into memory at once.
        
        Args:
            query_fn: Function that takes (session, offset, limit) and returns a batch
            process_fn: Function that processes a batch and returns a result
            batch_size: Number of records to process in each batch
        
        Returns:
            List[R]: List of batch processing results

        """
        results = []
        offset = 0
        total_records = 0

        with self.session() as session:
            while True:
                batch = query_fn(session, offset, batch_size)

                if not batch:
                    break

                result = process_fn(batch)
                results.append(result)

                total_records += len(batch)
                offset += batch_size

                if len(batch) < batch_size:
                    break

        logger.info(f"Processed {total_records} records in {len(results)} batches")
        return results

    def get_database_stats(self) -> dict[str, Any]:
        """
        Get statistics about the database.
        
        Returns:
            Dict[str, Any]: Database statistics

        """
        stats = {
            "database_type": "sqlite" if self.is_sqlite else "postgresql",
            "connection_url": self._sanitize_url(self.db_url),
            "tables": self.get_table_names(),
            "table_counts": {},
        }

        # Get table row counts
        with self.session() as session:
            for table in stats["tables"]:
                try:
                    result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    stats["table_counts"][table] = result.scalar() or 0
                except:
                    stats["table_counts"][table] = -1

        # Add PostgreSQL-specific stats
        if self.is_postgresql:
            with self.session() as session:
                # Database size
                try:
                    result = session.execute(text(
                        "SELECT pg_size_pretty(pg_database_size(current_database()))",
                    ))
                    stats["database_size"] = result.scalar() or "Unknown"
                except:
                    stats["database_size"] = "Unknown"

                # Connection stats
                try:
                    result = session.execute(text(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()",
                    ))
                    stats["active_connections"] = result.scalar() or 0
                except:
                    stats["active_connections"] = "Unknown"

        # Add SQLite-specific stats
        elif self.is_sqlite:
            with self.session() as session:
                # Database size
                try:
                    result = session.execute(text("PRAGMA page_count"))
                    page_count = result.scalar() or 0

                    result = session.execute(text("PRAGMA page_size"))
                    page_size = result.scalar() or 0

                    db_size_bytes = page_count * page_size
                    stats["database_size"] = f"{db_size_bytes / (1024 * 1024):.2f} MB"
                except:
                    stats["database_size"] = "Unknown"

                # WAL mode
                try:
                    result = session.execute(text("PRAGMA journal_mode"))
                    stats["journal_mode"] = result.scalar() or "Unknown"
                except:
                    stats["journal_mode"] = "Unknown"

        # Add connection pool stats if available
        if hasattr(self.engine, "pool") and hasattr(self.engine.pool, "size"):
            stats["pool_size"] = self.engine.pool.size()
            stats["pool_overflow"] = self.engine.pool.overflow()
            stats["pool_checkedout"] = self.engine.pool.checkedout()

        return stats

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
        if not index_name:
            index_name = f"idx_{table_name}_{'_'.join(column_names)}"

        # Use SQLAlchemy's schema components to avoid SQL injection
        from sqlalchemy import Index, MetaData

        try:
            # Get the table metadata
            metadata = MetaData()
            metadata.reflect(bind=self.engine, only=[table_name])

            if table_name in metadata.tables:
                table = metadata.tables[table_name]

                # Create the index object safely
                index = Index(
                    index_name,
                    *[table.c[column_name] for column_name in column_names],
                    unique=unique,
                )

                # Create the index in the database
                with self.engine.connect() as conn:
                    # Check if index already exists
                    if not index.exists(bind=conn):
                        index.create(bind=conn)

                    if not conn.in_transaction():
                        conn.commit()

            # Log the operation with columns joined for the message
            columns_str = ", ".join(column_names)
            logger.info(f"Created index {index_name} on {table_name}({columns_str})")
            return True
        except Exception as e:
            logger.error(f"Error adding index: {e!s}")
            return False

    def explain_query(self, query: str | sa.sql.Selectable, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Get the query execution plan.
        
        Args:
            query: SQL query or SQLAlchemy selectable
            params: Optional parameters for the query
        
        Returns:
            Dict[str, Any]: Query execution plan

        """
        with self.session() as session:
            if self.is_postgresql:
                if isinstance(query, str):
                    explain_query = f"EXPLAIN (FORMAT JSON) {query}"
                    result = session.execute(text(explain_query), params or {})
                else:
                    stmt = query.compile(
                        dialect=self.engine.dialect,
                        compile_kwargs={"literal_binds": True},
                    )
                    explain_query = f"EXPLAIN (FORMAT JSON) {stmt}"
                    result = session.execute(text(explain_query), params or {})

                plan = result.scalar()
                return {"plan": plan, "dialect": "postgresql"}
            if isinstance(query, str):
                explain_query = f"EXPLAIN QUERY PLAN {query}"
                result = session.execute(text(explain_query), params or {})
            else:
                stmt = query.compile(
                    dialect=self.engine.dialect,
                    compile_kwargs={"literal_binds": True},
                )
                explain_query = f"EXPLAIN QUERY PLAN {stmt}"
                result = session.execute(text(explain_query), params or {})

            plan = [dict(row._mapping) for row in result]
            return {"plan": plan, "dialect": "sqlite"}

    def close(self) -> None:
        """Close all connections and clean up resources."""
        # Close any thread-local sessions
        self.close_thread_session()

        # Dispose of the engine
        if hasattr(self, "engine"):
            self.engine.dispose()
            logger.info("Database engine disposed")


# Global database connection manager instance
_default_manager = None
_manager_lock = threading.RLock()


def get_connection_manager() -> DatabaseConnectionManager:
    """
    Get or create the default database connection manager instance.
    
    Thread-safe implementation using double-checked locking pattern.
    
    Returns:
        DatabaseConnectionManager: Default connection manager instance

    """
    global _default_manager
    # First check without acquiring lock
    if _default_manager is None:
        # Only acquire lock if we need to create the manager
        with _manager_lock:
            # Double-check after acquiring lock
            if _default_manager is None:
                _default_manager = DatabaseConnectionManager()
    return _default_manager


@contextmanager
def get_session() -> Session:
    """
    Get a database session from the default connection manager.
    
    Yields:
        Session: SQLAlchemy database session

    """
    with get_connection_manager().session() as session:
        yield session


@contextmanager
def transaction(
    session: Session | None = None,
    isolation_level: str | None = None,
    read_only: bool = False,
) -> Session:
    """
    Execute operations in a transaction using the default connection manager.
    
    Args:
        session: Optional existing session to use
        isolation_level: Transaction isolation level
        read_only: Whether the transaction is read-only
    
    Yields:
        Session: SQLAlchemy session with transaction

    """
    with get_connection_manager().transaction(
        session=session,
        isolation_level=isolation_level,
        read_only=read_only,
    ) as session:
        yield session


def execute_query(
    query: str | sa.sql.Selectable,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Execute a query using the default connection manager.
    
    Args:
        query: SQL query or SQLAlchemy selectable
        params: Optional parameters for the query
    
    Returns:
        List[Dict[str, Any]]: Query results as list of dictionaries

    """
    return get_connection_manager().execute_query(query, params)


def close_connections() -> None:
    """Close all connections from the default connection manager."""
    if _default_manager is not None:
        _default_manager.close()
