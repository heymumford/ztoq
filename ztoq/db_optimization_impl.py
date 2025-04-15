"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Database access pattern optimizations implementation for ZTOQ.

This module implements the PERF-4 task to optimize database access patterns
for improved performance with large datasets.
"""

import functools
import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

from sqlalchemy import func, text
from sqlalchemy.orm import Query, Session

from ztoq.core.db_manager import DatabaseConfig
from ztoq.core.db_models import (
    EntityBatchState,
    Folder,
    Project,
    TestCase,
    TestCycle,
    TestExecution,
)
from ztoq.database_optimizations import (
    QueryCache,
    cached_query,
    chunked_fetch,
    db_stats,
    keyset_pagination,
    tracked_execution,
)
from ztoq.db_optimization_helpers import (
    get_database_performance_report,
    get_optimized_database_manager,
    migrate_to_optimized_manager,
    optimize_for_reads,
    optimize_for_writes,
    reset_performance_tracking,
)
from ztoq.models import (
    Case as CaseModel,
    CycleInfo as CycleInfoModel,
    Execution as ExecutionModel,
    Folder as FolderModel,
    Project as ProjectModel,
)
from ztoq.optimized_database_manager import OptimizedDatabaseManager

# Setup logging
logger = logging.getLogger(__name__)


class DatabasePerformanceMonitor:
    """
    Monitor database performance and provide recommendations.

    This class tracks database performance metrics and provides
    recommendations for optimizing database access patterns.
    """

    def __init__(self):
        """Initialize the database performance monitor."""
        self._last_report_time = time.time()
        self._report_interval = 3600  # 1 hour

    def monitor(self, db_manager: OptimizedDatabaseManager):
        """
        Monitor database performance and log recommendations.

        Args:
            db_manager: Optimized database manager to monitor
        """
        current_time = time.time()

        # Generate report only once per interval
        if current_time - self._last_report_time >= self._report_interval:
            self._last_report_time = current_time

            # Get performance statistics
            stats = db_manager.get_performance_statistics()

            # Log summary
            logger.info("Database Performance Report:")
            logger.info(f"Total operations: {stats['summary']['total_operations']}")
            logger.info(
                f"Average operation time: {stats['summary']['avg_operation_time']:.4f} seconds"
            )

            # Log slow operations
            slow_ops = [
                (op_name, op_stats)
                for op_name, op_stats in stats["operations"].items()
                if op_stats["avg_time"] > 0.1  # Slow operation threshold: 100ms
            ]

            if slow_ops:
                logger.warning("Slow database operations detected:")
                for op_name, op_stats in sorted(
                    slow_ops, key=lambda x: x[1]["avg_time"], reverse=True
                ):
                    logger.warning(
                        f"  - {op_name}: {op_stats['avg_time']:.4f}s avg, {op_stats['count']} calls"
                    )

    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get database optimization recommendations.

        Returns:
            List of optimization recommendations
        """
        # Get performance report
        report = get_database_performance_report()

        # Extract recommendations
        return report["recommendations"]

    def reset(self):
        """Reset performance monitoring."""
        reset_performance_tracking()
        self._last_report_time = time.time()


# Create global monitor instance
db_monitor = DatabasePerformanceMonitor()


def apply_database_optimizations():
    """
    Apply database access pattern optimizations.

    This function implements the optimizations for the PERF-4 task.
    """
    logger.info("Applying database access pattern optimizations")

    # Get optimized database manager
    db_manager = get_optimized_database_manager()

    # Initialize database
    db_manager.initialize_database()

    # Set up monitoring
    db_monitor.reset()

    logger.info("Database access pattern optimizations applied successfully")
    return db_manager


def optimize_database_queries(session: Session, query_type: str) -> None:
    """
    Apply query optimizations based on query type.

    Args:
        session: Database session
        query_type: Type of query to optimize
    """
    if query_type == "read":
        # Optimize for read operations
        optimize_for_reads()

        # Set transaction isolation level for read queries
        session.execute(text("PRAGMA read_uncommitted = 1"))

    elif query_type == "write":
        # Optimize for write operations
        optimize_for_writes()

        # Set transaction isolation level for write queries
        session.execute(text("PRAGMA synchronous = NORMAL"))


# Decorator for optimizing database access patterns
def optimize_database_access(query_type: str = "read"):
    """
    Decorator for optimizing database access.

    Args:
        query_type: Type of query to optimize

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Get database manager
            db_manager = None
            for arg in args:
                if isinstance(arg, OptimizedDatabaseManager):
                    db_manager = arg
                    break

            if db_manager is None:
                # No database manager found, just call the function
                return func(*args, **kwargs)

            # Apply query optimizations
            with db_manager.get_session() as session:
                optimize_database_queries(session, query_type)

                # Call the original function
                result = func(*args, **kwargs)

                # Monitor database performance
                db_monitor.monitor(db_manager)

                return result

        return wrapper

    return decorator


# Function for optimizing large result sets
def process_large_result_set(
    db_manager: OptimizedDatabaseManager,
    model_class: Any,
    filter_criteria: Any = None,
    batch_size: int = 1000,
    processor: Callable[[List[Any]], None] = None,
) -> int:
    """
    Process a large result set in batches.

    Args:
        db_manager: Optimized database manager
        model_class: Model class to query
        filter_criteria: Filter criteria for the query
        batch_size: Batch size for processing
        processor: Function to process each batch

    Returns:
        Count of processed records
    """
    processed_count = 0

    with db_manager.get_session() as session:
        # Create base query
        query = session.query(model_class)

        # Apply filter criteria
        if filter_criteria is not None:
            query = query.filter(filter_criteria)

        # Get ID column for keyset pagination
        id_column = getattr(model_class, "id")

        # Process records in batches
        last_id = None
        while True:
            # Use keyset pagination
            batch = keyset_pagination(
                session, model_class, id_column, batch_size, last_id, filter_criteria
            )

            if not batch:
                break

            # Process batch
            if processor:
                processor(batch)

            # Update counters
            processed_count += len(batch)

            # Get last ID for next batch
            last_id = batch[-1].id

            # Log progress
            logger.debug(f"Processed {processed_count} records")

    return processed_count
