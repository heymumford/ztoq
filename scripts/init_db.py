#!/usr/bin/env python3
"""
Initialize the database using SQLAlchemy models and Alembic migrations.

This script creates a new SQLite or PostgreSQL database and applies
all migrations to set up the schema.

Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import argparse
import logging
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from ztoq.core.db_manager import DatabaseConfig, SQLDatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_alembic_config(db_config: DatabaseConfig) -> Config:
    """Get Alembic configuration with the correct connection string."""
    # Create Alembic config pointing to our project's alembic.ini
    project_root = Path(__file__).parent.parent
    alembic_cfg = Config(project_root / "alembic.ini")

    # Set the connection string based on database configuration
    alembic_cfg.set_main_option("sqlalchemy.url", db_config.get_connection_string())

    return alembic_cfg


def init_db(
    db_type: str = "sqlite",
    db_path: str = None,
    host: str = None,
    port: int = None,
    username: str = None,
    password: str = None,
    database: str = None,
    drop_existing: bool = False,
) -> None:
    """
    Initialize the database with the schema.

    Args:
        db_type: Database type (sqlite, postgresql)
        db_path: Path to SQLite database file
        host: PostgreSQL host
        port: PostgreSQL port
        username: PostgreSQL username
        password: PostgreSQL password
        database: PostgreSQL database name
        drop_existing: Whether to drop existing tables
    """
    # Configure the database
    db_config = DatabaseConfig(
        db_type=db_type,
        db_path=db_path,
        host=host,
        port=port,
        username=username,
        password=password,
        database=database,
    )

    # Create the database manager
    db_manager = SQLDatabaseManager(config=db_config)

    if drop_existing:
        logger.warning("Dropping existing database tables...")
        db_manager.drop_all_tables()
        logger.warning("Database tables dropped")

    # Get Alembic config
    alembic_cfg = get_alembic_config(db_config)

    # Initialize database schema through Alembic migrations
    logger.info("Applying database migrations...")
    command.upgrade(alembic_cfg, "head")
    logger.info("Database migrations applied successfully")


def main():
    """Script entry point."""
    parser = argparse.ArgumentParser(description="Initialize the ZTOQ database")

    # Database type
    parser.add_argument(
        "--db-type",
        choices=["sqlite", "postgresql"],
        default="sqlite",
        help="Database type (sqlite, postgresql)",
    )

    # SQLite options
    parser.add_argument(
        "--db-path",
        default=None,
        help="Path to SQLite database file (for SQLite only)",
    )

    # PostgreSQL options
    parser.add_argument(
        "--host",
        default=None,
        help="PostgreSQL host (for PostgreSQL only)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="PostgreSQL port (for PostgreSQL only)",
    )
    parser.add_argument(
        "--username",
        default=None,
        help="PostgreSQL username (for PostgreSQL only)",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="PostgreSQL password (for PostgreSQL only)",
    )
    parser.add_argument(
        "--database",
        default=None,
        help="PostgreSQL database name (for PostgreSQL only)",
    )

    # Other options
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Drop existing tables before initializing",
    )

    args = parser.parse_args()

    # If no arguments are provided, check for environment variables
    if args.db_type == "postgresql" and not all([args.host, args.username, args.database]):
        args.host = os.environ.get("ZTOQ_PG_HOST", args.host)
        args.port = int(os.environ.get("ZTOQ_PG_PORT", args.port or 5432))
        args.username = os.environ.get("ZTOQ_PG_USER", args.username)
        args.password = os.environ.get("ZTOQ_PG_PASSWORD", args.password)
        args.database = os.environ.get("ZTOQ_PG_DATABASE", args.database)

    # Initialize the database
    init_db(
        db_type=args.db_type,
        db_path=args.db_path,
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
        database=args.database,
        drop_existing=args.drop_existing,
    )

    logger.info("Database initialization complete")


if __name__ == "__main__":
    main()
