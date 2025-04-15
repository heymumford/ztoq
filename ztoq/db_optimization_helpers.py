"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Helper functions for using the optimized database manager.

This module provides utilities to easily use and configure
the optimized database manager for improved performance.
"""

import logging
import os
from typing import Any, Dict, Optional

from ztoq.core.db_manager import SQLDatabaseManager
from ztoq.database_factory import DatabaseFactory, DatabaseType
from ztoq.database_optimizations import db_stats, query_cache
from ztoq.optimized_database_manager import OptimizedDatabaseManager


# Setup logging
logger = logging.getLogger(__name__)


def get_optimized_database_manager(
    db_type: str = os.environ.get("ZTOQ_DB_TYPE", DatabaseType.SQLITE),
    db_path: Optional[str] = os.environ.get("ZTOQ_DB_PATH"),
    host: Optional[str] = os.environ.get("ZTOQ_PG_HOST"),
    port: Optional[int] = int(os.environ.get("ZTOQ_PG_PORT", "5432"))
    if os.environ.get("ZTOQ_PG_PORT")
    else None,
    username: Optional[str] = os.environ.get("ZTOQ_PG_USER"),
    password: Optional[str] = os.environ.get("ZTOQ_PG_PASSWORD"),
    database: Optional[str] = os.environ.get("ZTOQ_PG_DATABASE"),
    cache_ttl: int = 300,
    pool_size: int = 10,
    max_overflow: int = 20,
) -> OptimizedDatabaseManager:
    """
    Get an optimized database manager with environment variable fallbacks.

    Args:
        db_type: Database type
        db_path: Path to SQLite database file
        host: PostgreSQL host
        port: PostgreSQL port
        username: PostgreSQL username
        password: PostgreSQL password
        database: PostgreSQL database name
        cache_ttl: Time-to-live for query cache in seconds
        pool_size: Connection pool size
        max_overflow: Maximum number of connections to overflow

    Returns:
        Optimized database manager instance
    """
    # Configure cache TTL
    query_cache._ttl_seconds = cache_ttl

    # Create database manager using factory
    manager = DatabaseFactory.create_database_manager(
        db_type=db_type,
        db_path=db_path,
        host=host,
        port=port,
        username=username,
        password=password,
        database=database,
        pool_size=pool_size,
        max_overflow=max_overflow,
        optimize=True,
    )

    logger.info(f"Created optimized database manager for {db_type} database")

    return manager


def migrate_to_optimized_manager(standard_manager: SQLDatabaseManager) -> OptimizedDatabaseManager:
    """
    Migrate from a standard database manager to an optimized one.

    Args:
        standard_manager: Standard database manager

    Returns:
        Optimized database manager
    """
    # Create optimized manager wrapping the base manager
    optimized_manager = OptimizedDatabaseManager(base_manager=standard_manager)

    logger.info("Migrated to optimized database manager")
    return optimized_manager


def get_database_performance_report() -> Dict[str, Any]:
    """
    Get a comprehensive database performance report.

    Returns:
        Dictionary with performance statistics and recommendations
    """
    # Get basic statistics
    stats = db_stats.get_stats()

    # Analyze slow operations
    slow_operations = []
    for op_name, op_stats in stats.items():
        if op_stats["avg_time"] > 0.1:  # Consider operations taking > 100ms as slow
            slow_operations.append(
                {
                    "operation": op_name,
                    "avg_time": op_stats["avg_time"],
                    "count": op_stats["count"],
                    "max_time": op_stats["max_time"],
                }
            )

    # Sort slow operations by average time (descending)
    slow_operations.sort(key=lambda op: op["avg_time"], reverse=True)

    # Generate recommendations
    recommendations = []

    if slow_operations:
        recommendations.append(
            {
                "title": "Optimize slow database operations",
                "description": "Consider optimizing the following slow operations",
                "operations": slow_operations[:5],  # Top 5 slowest operations
            }
        )

    if any(op_stats["error_rate"] > 0.01 for op_name, op_stats in stats.items()):
        error_prone_ops = [
            {
                "operation": op_name,
                "error_rate": op_stats["error_rate"],
                "errors": op_stats["errors"],
                "count": op_stats["count"],
            }
            for op_name, op_stats in stats.items()
            if op_stats["error_rate"] > 0.01  # Error rate > 1%
        ]

        if error_prone_ops:
            recommendations.append(
                {
                    "title": "Fix error-prone database operations",
                    "description": "The following operations have high error rates",
                    "operations": error_prone_ops,
                }
            )

    # Check cache efficiency
    cache_hits = sum(
        op_stats["count"] for op_name, op_stats in stats.items() if "cached" in op_name
    )
    cache_misses = sum(
        op_stats["count"]
        for op_name, op_stats in stats.items()
        if "cached" in op_name and op_stats["avg_time"] > 0.01
    )

    if cache_hits > 0:
        cache_hit_rate = (cache_hits - cache_misses) / cache_hits

        if cache_hit_rate < 0.5:  # Cache hit rate < 50%
            recommendations.append(
                {
                    "title": "Improve cache efficiency",
                    "description": f"Current cache hit rate is only {cache_hit_rate:.1%}",
                    "suggestion": "Consider increasing cache TTL or optimizing cache keys",
                }
            )

    # Build the final report
    report = {
        "statistics": {
            "operations": stats,
            "summary": {
                "total_operations": sum(op_stats["count"] for op_stats in stats.values()),
                "total_errors": sum(op_stats["errors"] for op_stats in stats.values()),
                "avg_operation_time": sum(op_stats["total_time"] for op_stats in stats.values())
                / sum(op_stats["count"] for op_stats in stats.values())
                if sum(op_stats["count"] for op_stats in stats.values()) > 0
                else 0,
                "error_rate": sum(op_stats["errors"] for op_stats in stats.values())
                / sum(op_stats["count"] for op_stats in stats.values())
                if sum(op_stats["count"] for op_stats in stats.values()) > 0
                else 0,
            },
        },
        "slow_operations": slow_operations,
        "recommendations": recommendations,
        "cache": {
            "size": len(query_cache._cache),
            "ttl": query_cache._ttl_seconds,
        },
    }

    return report


def reset_performance_tracking():
    """Reset all performance tracking data."""
    db_stats.reset()
    query_cache.clear()
    logger.info("Reset database performance tracking")


def optimize_for_reads():
    """Configure the database for read-heavy workloads."""
    # Increase cache TTL for read-heavy workloads
    query_cache._ttl_seconds = 600  # 10 minutes
    logger.info("Optimized database for read-heavy workloads")


def optimize_for_writes():
    """Configure the database for write-heavy workloads."""
    # Decrease cache TTL for write-heavy workloads to prevent stale data
    query_cache._ttl_seconds = 60  # 1 minute
    logger.info("Optimized database for write-heavy workloads")
