# ADR-007: Database Manager Implementation for Zephyr Data

## Status

Accepted

## Context

The ZTOQ application needs a robust way to handle database operations for storing Zephyr Scale test data. While the storage module provides basic abstractions for JSON and SQLite storage, we needed a more sophisticated component to handle relational database operations with proper foreign key relationships, serialization of complex objects, and transaction management.

The specific challenges that needed to be addressed include:

1. Handling complex object hierarchies in test data
2. Managing foreign key relationships and proper insertion order
3. Serialization of nested objects and datetime values
4. Transaction management for data consistency
5. Connection pooling and resource management
6. Abstraction of SQL operations from the rest of the application

## Decision

We will implement a dedicated `DatabaseManager` class that provides a higher-level abstraction over SQLite operations, with a focus on proper handling of Zephyr Scale data structures, foreign key relationships, and transaction management.

## Consequences

### Positive

- Clear separation of concerns with a dedicated component for database operations
- Proper handling of foreign key relationships and constraints
- Consistent transaction management with context managers
- Effective serialization of complex objects and special types
- Improved data integrity and reliability
- Better error handling and reporting
- Simplified interface for other components to use

### Negative

- Introduces another layer in the architecture
- Potential duplication with some functionality in the SQLiteStorage class
- Requires careful management of database connections
- Additional testing burden to ensure all operations work correctly

## Implementation Details

### Class Structure

```python
class DatabaseManager:
    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path) if isinstance(db_path, str) else db_path
        self._ensure_parent_dir_exists()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("PRAGMA foreign_keys = ON")
            conn.row_factory = sqlite3.Row
            yield conn
        finally:
            if conn:
                conn.close()
    
    def initialize_database(self) -> None:
        """Creates all necessary database tables."""
        # Implementation to create all tables with proper foreign keys
    
    def save_project(self, project: Project) -> None:
        """Save a project to the database."""
        # Implementation with proper transaction handling
    
    # Methods for saving various entity types...
    
    def save_project_data(self, project_key: str, fetch_results: Dict[str, FetchResult]) -> Dict[str, int]:
        """Save all fetched data for a project with proper ordering."""
        # Implementation that respects foreign key relationships
    
    def save_all_projects_data(self, all_projects_data: Dict[str, Dict[str, FetchResult]]) -> Dict[str, Dict[str, int]]:
        """Save data for multiple projects."""
        # Implementation with initialization and per-project saving
```

### Key Features

1. **Context Manager for Connections**: Uses Python's context management to ensure connections are properly closed.

2. **Object Serialization**: Handles complex serialization needs:
   ```python
   def _serialize_object(self, obj: Any) -> Any:
       """Serialize an object for database storage."""
       # Implementation to handle Pydantic models, datetime objects, lists, etc.
   
   def _serialize_value(self, value: Any) -> Any:
       """Serialize a value for database storage."""
       # Implementation specific to database field values
   ```

3. **Foreign Key Management**: Ensures tables are created with proper foreign key relationships and data is inserted in the correct order to satisfy constraints.

4. **Transaction Management**: Uses SQLite transactions to ensure data consistency.

5. **Entity-Specific Methods**: Dedicated methods for each entity type (projects, test cases, cycles, etc.) with proper error handling.

## Testing Approach

The DatabaseManager implementation follows Test-Driven Development principles with:

1. Unit tests achieving 100% code coverage
2. Testing of all edge cases and error conditions
3. Mocking of dependencies where appropriate
4. Verification of foreign key constraints
5. Testing of serialization mechanisms
6. Tests for parallel operations
7. Performance tests for large datasets

## References

- [SQLite Foreign Key Documentation](https://www.sqlite.org/foreignkeys.html)
- [Python contextlib Documentation](https://docs.python.org/3/library/contextlib.html)
- [SQLite Transaction Documentation](https://www.sqlite.org/lang_transaction.html)