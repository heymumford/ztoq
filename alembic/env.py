"""
Alembic environment module for database migrations.

This module is used by alembic to interact with the SQLAlchemy models
and manage database migrations.
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Add the project root directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the models that should be included in the migration
from ztoq.core.db_models import Base

# This is the Alembic Config object.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the SQLAlchemy URL from environment variables if available
pg_host = os.environ.get("ZTOQ_PG_HOST")
pg_port = os.environ.get("ZTOQ_PG_PORT", "5432")
pg_user = os.environ.get("ZTOQ_PG_USER")
pg_pass = os.environ.get("ZTOQ_PG_PASSWORD")
pg_db = os.environ.get("ZTOQ_PG_DATABASE")

# Override the SQLAlchemy URL if PostgreSQL environment variables are set
if all([pg_host, pg_user, pg_db]):
    pg_url = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_db}"
    config.set_main_option("sqlalchemy.url", pg_url)

# Add your model's MetaData object here
target_metadata = Base.metadata

# Other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
