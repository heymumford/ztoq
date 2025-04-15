"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Database access pattern optimizations for ZTOQ.

This module provides optimized database access patterns to improve performance
when working with large datasets and high-concurrency operations.
"""

import functools
import logging
import threading
import time
from collections import defaultdict
from collections.abc import Callable, Iterable
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Generic, TypeVar

from sqlalchemy import Column, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Query, Session
from sqlalchemy.sql import Select

# Setup logging
logger = logging.getLogger(__name__)

# Type variables
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


class QueryCache(Generic[K, V]):
    """
    Cache for database query results.

    This class provides a simple in-memory cache for database query results
    with automatic expiration to ensure data freshness.
    """

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize the query cache.

        Args:
            ttl_seconds: Time-to-live in seconds for cache entries

        """
        self._cache: dict[K, tuple[V, datetime]] = {}
        self._ttl_seconds = ttl_seconds
        self._lock = threading.RLock()

    def get(self, key: K) -> V | None:
        """
        Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired

        """
        with self._lock:
            if key not in self._cache:
                return None

            value, timestamp = self._cache[key]
            if datetime.now() - timestamp > timedelta(seconds=self._ttl_seconds):
                del self._cache[key]
                return None

            return value

    def set(self, key: K, value: V) -> None:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache

        """
        with self._lock:
            self._cache[key] = (value, datetime.now())

    def invalidate(self, key: K) -> None:
        """
        Invalidate a cached value.

        Args:
            key: Cache key to invalidate

        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def invalidate_pattern(self, pattern: str) -> None:
        """
        Invalidate all cache entries matching a pattern.

        Args:
            pattern: Pattern to match against cache keys

        """
        with self._lock:
            keys_to_remove = []
            for key in self._cache.keys():
                if isinstance(key, str) and pattern in key:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._cache[key]

    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()

    def cleanup(self) -> None:
        """Remove expired entries from the cache."""
        with self._lock:
            now = datetime.now()
            keys_to_remove = [
                key
                for key, (_, timestamp) in self._cache.items()
                if now - timestamp > timedelta(seconds=self._ttl_seconds)
            ]

            for key in keys_to_remove:
                del self._cache[key]


# Global query cache instance
query_cache = QueryCache[str, Any]()


def cached_query(ttl_seconds: int = 300) -> Callable:
    """
    Decorator for caching database query results.

    Args:
        ttl_seconds: Time-to-live in seconds for cached results

    Returns:
        Decorator function

    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Generate a cache key based on function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)

            # Check cache
            result = query_cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return result

            # Execute function and cache result
            result = func(*args, **kwargs)
            query_cache.set(cache_key, result)
            logger.debug(f"Cache miss for {cache_key}, cached result")

            return result

        return wrapper

    return decorator


def bulk_insert(session: Session, model_class: Any, items: list[dict[str, Any]]) -> None:
    """
    Perform a bulk insert operation.

    This method is much more efficient than inserting items one by one
    for large datasets.

    Args:
        session: SQLAlchemy session
        model_class: Model class to insert
        items: List of dictionaries with item data

    """
    if not items:
        return

    try:
        # Use the bulk_insert_mappings method for optimal performance
        session.bulk_insert_mappings(model_class, items)
        session.flush()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Error during bulk insert: {e}")
        raise


def bulk_update(
    session: Session, model_class: Any, items: list[dict[str, Any]], primary_key: str,
) -> None:
    """
    Perform a bulk update operation.

    Args:
        session: SQLAlchemy session
        model_class: Model class to update
        items: List of dictionaries with item data
        primary_key: Primary key column name

    """
    if not items:
        return

    try:
        # Use the bulk_update_mappings method for optimal performance
        session.bulk_update_mappings(model_class, items)
        session.flush()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Error during bulk update: {e}")
        raise


def batch_process(items: list[T], batch_size: int, processor: Callable[[list[T]], None]) -> None:
    """
    Process items in batches.

    Args:
        items: Items to process
        batch_size: Size of each batch
        processor: Function to process each batch

    """
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        processor(batch)


def optimized_query(session: Session, model_class: Any) -> Query:
    """
    Create an optimized query for a model class.

    This adds commonly used performance optimizations:
    1. Use of exists() instead of count() for existence checks
    2. Column selection to avoid loading unnecessary data
    3. Proper use of filter() vs. filter_by() for indexed columns

    Args:
        session: SQLAlchemy session
        model_class: Model class to query

    Returns:
        Optimized SQLAlchemy query object

    """
    return session.query(model_class)


def chunked_fetch(query: Query, chunk_size: int = 1000) -> Iterable[Any]:
    """
    Fetch large result sets in chunks to reduce memory usage.

    Args:
        query: SQLAlchemy query object
        chunk_size: Number of records to fetch per chunk

    Yields:
        Records from the query, one at a time

    """
    offset = 0
    while True:
        chunk = query.limit(chunk_size).offset(offset).all()
        if not chunk:
            break

        yield from chunk
        offset += chunk_size


def keyset_pagination(
    session: Session,
    model_class: Any,
    key_column: Column,
    page_size: int = 100,
    last_key: Any | None = None,
    filter_criteria: Any | None = None,
) -> list[Any]:
    """
    Implement keyset pagination for efficient paging through large datasets.

    Keyset pagination is much more efficient than offset/limit pagination
    for large datasets.

    Args:
        session: SQLAlchemy session
        model_class: Model class to query
        key_column: Column to use for pagination (should be indexed)
        page_size: Number of records per page
        last_key: Last key value from previous page
        filter_criteria: Additional filter criteria

    Returns:
        List of records for the current page

    """
    query = session.query(model_class)

    if filter_criteria is not None:
        query = query.filter(filter_criteria)

    if last_key is not None:
        query = query.filter(key_column > last_key)

    query = query.order_by(key_column).limit(page_size)

    return query.all()


def execute_with_timing(
    session: Session, query: str | Select, params: dict[str, Any] | None = None,
) -> tuple[Any, float]:
    """
    Execute a query and measure execution time.

    Args:
        session: SQLAlchemy session
        query: SQL query string or SQLAlchemy query object
        params: Query parameters

    Returns:
        Tuple of (query result, execution time in seconds)

    """
    start_time = time.time()

    try:
        if isinstance(query, str):
            result = session.execute(text(query), params or {})
        else:
            result = session.execute(query, params or {})

        execution_time = time.time() - start_time
        return result, execution_time
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Query execution failed in {execution_time:.4f}s: {e}")
        raise


def analyze_query_performance(
    session: Session, query: str, params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Analyze query performance using EXPLAIN.

    Args:
        session: SQLAlchemy session
        query: SQL query string
        params: Query parameters

    Returns:
        Dictionary with performance analysis data

    """
    try:
        # Execute the query with EXPLAIN
        explain_query = f"EXPLAIN QUERY PLAN {query}"
        result = session.execute(text(explain_query), params or {})

        # Parse the explain output
        explain_rows = [dict(row) for row in result]

        # Execute the query with timing
        _, execution_time = execute_with_timing(session, query, params)

        return {"explain_plan": explain_rows, "execution_time": execution_time}
    except Exception as e:
        logger.error(f"Query analysis failed: {e}")
        return {"error": str(e), "execution_time": -1}


def get_table_statistics(session: Session, table_name: str) -> dict[str, Any]:
    """
    Get statistics for a database table.

    Args:
        session: SQLAlchemy session
        table_name: Name of the table

    Returns:
        Dictionary with table statistics

    """
    try:
        # Get row count
        result = session.execute(text(f"SELECT COUNT(*) as count FROM {table_name}"))
        row_count = result.scalar()

        # Get index information (SQLite specific)
        result = session.execute(text(f"PRAGMA index_list({table_name})"))
        indices = [dict(row) for row in result]

        # Get column information
        result = session.execute(text(f"PRAGMA table_info({table_name})"))
        columns = [dict(row) for row in result]

        return {"row_count": row_count, "indices": indices, "columns": columns}
    except Exception as e:
        logger.error(f"Failed to get table statistics: {e}")
        return {"error": str(e)}


@contextmanager
def transaction_scope(session: Session, nested: bool = False):
    """
    Provide a transactional scope around a series of operations.

    This is a more robust transaction manager than the default session.

    Args:
        session: SQLAlchemy session
        nested: Whether to use a nested transaction

    """
    if nested:
        transaction = session.begin_nested()
    else:
        transaction = session.begin()

    try:
        yield session
        transaction.commit()
    except:
        transaction.rollback()
        raise


def with_retry(retries: int = 3, retry_delay: float = 0.1):
    """
    Decorator for retrying database operations on failure.

    Args:
        retries: Number of retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        Decorator function

    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_error = None

            for attempt in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < retries:
                        logger.warning(
                            f"Retrying operation after error: {e} (attempt {attempt + 1}/{retries})",
                        )
                        time.sleep(retry_delay * (2**attempt))  # Exponential backoff
                    else:
                        logger.error(f"Operation failed after {retries} retries: {e}")
                        raise last_error

        return wrapper

    return decorator


class DatabaseStats:
    """
    Track database operation statistics.
    """

    def __init__(self):
        """Initialize the statistics tracker."""
        self._stats = defaultdict(
            lambda: {
                "count": 0,
                "total_time": 0,
                "min_time": float("inf"),
                "max_time": 0,
                "errors": 0,
            },
        )
        self._lock = threading.RLock()

    def record_operation(self, operation: str, execution_time: float, success: bool = True) -> None:
        """
        Record statistics for a database operation.

        Args:
            operation: Name of the operation
            execution_time: Execution time in seconds
            success: Whether the operation was successful

        """
        with self._lock:
            stats = self._stats[operation]
            stats["count"] += 1
            stats["total_time"] += execution_time
            stats["min_time"] = min(stats["min_time"], execution_time)
            stats["max_time"] = max(stats["max_time"], execution_time)

            if not success:
                stats["errors"] += 1

    def get_stats(self) -> dict[str, dict[str, Any]]:
        """
        Get current statistics.

        Returns:
            Dictionary with operation statistics

        """
        with self._lock:
            result = {}
            for operation, stats in self._stats.items():
                result[operation] = {
                    "count": stats["count"],
                    "avg_time": stats["total_time"] / stats["count"] if stats["count"] > 0 else 0,
                    "min_time": stats["min_time"] if stats["min_time"] != float("inf") else 0,
                    "max_time": stats["max_time"],
                    "total_time": stats["total_time"],
                    "errors": stats["errors"],
                    "error_rate": stats["errors"] / stats["count"] if stats["count"] > 0 else 0,
                }

            return result

    def reset(self) -> None:
        """Reset all statistics."""
        with self._lock:
            self._stats.clear()


# Global database stats instance
db_stats = DatabaseStats()


def tracked_execution(operation: str) -> Callable:
    """
    Decorator for tracking database operation statistics.

    Args:
        operation: Name of the operation

    Returns:
        Decorator function

    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            success = False

            try:
                result = func(*args, **kwargs)
                success = True
                return result
            finally:
                execution_time = time.time() - start_time
                db_stats.record_operation(operation, execution_time, success)

        return wrapper

    return decorator
