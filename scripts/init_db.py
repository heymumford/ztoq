#!/usr/bin/env python
"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Database initialization script.

This script initializes the database schema for the ZTOQ application.
It creates all necessary tables, indexes, and relationships.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add the project root directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ztoq.core.db_models import Base
from ztoq.sql_database_manager import SQLDatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("init_db")


def init_database(
    db_url: str,
    drop_existing: bool = False,
    create_indexes: bool = True,
    analyze: bool = True,
) -> None:
    """
    Initialize the database schema.

    Args:
        db_url: Database connection URL
        drop_existing: Whether to drop existing tables
        create_indexes: Whether to create additional performance indexes
        analyze: Whether to run ANALYZE on the database

    """
    logger.info(f"Initializing database with URL: {db_url}")

    # Create database manager
    db_manager = SQLDatabaseManager(db_url=db_url)

    # Check connectivity
    if not db_manager.check_connectivity():
        logger.error("Failed to connect to the database")
        sys.exit(1)

    # Drop existing tables if requested
    if drop_existing:
        logger.info("Dropping existing tables")
        Base.metadata.drop_all(db_manager.engine)

    # Create tables
    logger.info("Creating tables")
    Base.metadata.create_all(db_manager.engine)

    # Create additional indexes if requested
    if create_indexes:
        logger.info("Creating additional performance indexes")

        # User-defined indexes (in addition to SQLAlchemy's default ones)
        indexes = [
            ("test_cases", ["created_on"]),
            ("test_cases", ["updated_on"]),
            ("test_executions", ["executed_on"]),
            ("migration_state", ["last_updated"]),
            ("recommendation_history", ["project_key", "timestamp"]),
            ("recommendation_history", ["priority"]),
            ("migration_performance_stats", ["project_key", "phase"]),
            ("migration_checkpoints", ["project_key", "phase"]),
        ]

        for table_name, column_names in indexes:
            index_name = f"idx_{table_name}_{'_'.join(column_names)}"
            logger.info(f"Creating index {index_name}")
            success = db_manager.add_index(table_name, column_names, index_name)
            if not success:
                logger.warning(f"Failed to create index {index_name}")

    # Analyze the database if requested
    if analyze:
        logger.info("Analyzing the database for query optimization")
        db_manager.analyze()

    logger.info("Database initialization completed successfully")


def main():
    parser = argparse.ArgumentParser(description="Initialize the ZTOQ database")

    parser.add_argument(
        "--db-url",
        help="Database connection URL (e.g., sqlite:///ztoq_data.db, postgresql://user:pass@host/db)",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing tables before creating new ones",
    )
    parser.add_argument(
        "--no-indexes",
        action="store_true",
        help="Skip creating additional performance indexes",
    )
    parser.add_argument(
        "--no-analyze",
        action="store_true",
        help="Skip running ANALYZE on the database",
    )

    args = parser.parse_args()

    # Get database URL from arguments or environment variables
    db_url = args.db_url
    if not db_url:
        # Check for PostgreSQL environment variables
        pg_host = os.environ.get("ZTOQ_PG_HOST")
        pg_port = os.environ.get("ZTOQ_PG_PORT", "5432")
        pg_user = os.environ.get("ZTOQ_PG_USER")
        pg_pass = os.environ.get("ZTOQ_PG_PASSWORD", "")
        pg_db = os.environ.get("ZTOQ_PG_DATABASE")

        if all([pg_host, pg_user, pg_db]):
            db_url = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
        else:
            # Use SQLite as fallback
            sqlite_path = os.environ.get("ZTOQ_SQLITE_PATH", "ztoq_data.db")
            db_url = f"sqlite:///{sqlite_path}"

    init_database(
        db_url=db_url,
        drop_existing=args.drop,
        create_indexes=not args.no_indexes,
        analyze=not args.no_analyze,
    )


if __name__ == "__main__":
    main()
