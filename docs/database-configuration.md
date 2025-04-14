# Database Configuration

ZTOQ supports multiple database backends for storing migration data, including SQLite and PostgreSQL. This document describes how to configure the database connection.

## Database Factory

The database factory pattern is implemented to allow the application to switch between different database backends without changing the code. This is particularly useful for the following scenarios:

- Development using SQLite for simplicity
- Production using PostgreSQL for scalability and performance
- Testing using in-memory SQLite for speed

## Supported Database Types

- **SQLite**: Simple file-based database, good for small to medium migrations
- **PostgreSQL**: Robust server-based database, good for large migrations and concurrent operations

## Configuration Options

### Environment Variables

These environment variables can be used to configure the database connection:

```bash
# Database type
export ZTOQ_DB_TYPE=sqlite  # or postgresql

# SQLite configuration
export ZTOQ_DB_PATH=/path/to/database.db

# PostgreSQL configuration
export ZTOQ_PG_HOST=localhost
export ZTOQ_PG_PORT=5432
export ZTOQ_PG_USER=postgres
export ZTOQ_PG_PASSWORD=password
export ZTOQ_PG_DATABASE=ztoq
```

### Command-Line Options

All ZTOQ commands that interact with the database support the following options:

```bash
# Database type
--db-type sqlite  # or postgresql

# SQLite configuration
--db-path /path/to/database.db

# PostgreSQL configuration
--host localhost
--port 5432
--username postgres
--password password
--database ztoq
```

## Database Manager Classes

ZTOQ provides three database manager implementations:

1. **DatabaseManager**: The original SQLite-based implementation
2. **PostgreSQLDatabaseManager**: PostgreSQL-specific implementation with connection pooling
3. **SQLDatabaseManager**: SQLAlchemy-based implementation that supports both SQLite and PostgreSQL

## Using the Database Factory

The database factory provides a simple interface for creating database managers:

```python
from ztoq.database_factory import DatabaseFactory, DatabaseType, get_database_manager

# Creating a database manager from explicit parameters
db_manager = DatabaseFactory.create_database_manager(
    db_type=DatabaseType.POSTGRESQL,
    host="localhost",
    port=5432,
    username="postgres",
    password="password",
    database="ztoq",
)

# Creating a database manager from environment variables
db_manager = get_database_manager()

# Creating a database manager from a configuration dictionary
config = {
    "db_type": DatabaseType.SQLITE,
    "db_path": "/path/to/database.db",
}
db_manager = DatabaseFactory.from_config(config)
```

## PostgreSQL Connection Pooling

When using PostgreSQL, the database manager uses connection pooling to improve performance. This is particularly important for concurrent operations.

Connection pooling parameters can be configured:

```python
db_manager = DatabaseFactory.create_database_manager(
    db_type=DatabaseType.POSTGRESQL,
    host="localhost",
    port=5432,
    username="postgres",
    password="password",
    database="ztoq",
    min_connections=5,  # Minimum number of connections in the pool
    max_connections=20,  # Maximum number of connections in the pool
)
```

## Transaction Management

All database operations are wrapped in transactions to ensure data consistency. This is particularly important for migrations, where multiple operations need to succeed or fail together.

```python
# Example of transaction use in the code
with db_manager.get_session() as session:
    # All operations within this block are part of a transaction
    # If an exception occurs, the transaction is automatically rolled back
    # If no exception occurs, the transaction is automatically committed
    pass
```

## Schema Migrations

Database schema migrations are managed using Alembic. This allows for changes to the database schema over time without losing data.

```bash
# Initialize the database schema
ztoq db init

# Upgrade to the latest schema version
ztoq db migrate
```

## Performance Considerations

- **SQLite**: Good for small to medium migrations, but may have performance issues with large datasets or concurrent operations
- **PostgreSQL**: Better performance for large datasets and concurrent operations, but requires more setup