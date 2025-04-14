# ADR-002: Support Both JSON and SQLite Storage Formats

## Status

Accepted

## Context

ZTOQ needs to store data extracted from the Zephyr Scale API in a persistent format. Different users may have different requirements for how this data is stored:

- Some users may need simple file-based storage for portability
- Others may need relational capabilities for complex queries
- Some may want to import the data into other tools or systems

We considered these options:
1. JSON files only
2. SQLite database only
3. Support for both formats with a configurable option
4. Support for additional formats like CSV, XML, or PostgreSQL

## Decision

We will implement support for both JSON and SQLite storage formats, with a user-selectable option in the CLI.

## Consequences

### Positive

- Flexibility to meet different user needs
- JSON provides human-readable format and easy integration with web technologies
- SQLite offers relational queries and better performance for large datasets
- Both formats are portable (files) and don't require external services
- The abstraction will make it easier to add more storage formats later if needed

### Negative

- Need to maintain two storage implementations
- More code complexity due to the storage abstraction layer
- Need to handle different database schemas and migration strategies
- Extra testing burden to ensure both implementations work correctly

## Implementation Details

We'll implement a storage layer with these components:

1. Abstract base class or interface for storage operations:
   - save_project()
   - save_test_case()
   - save_test_cases()
   - etc.

2. Two concrete implementations:
   - JSONStorage: Stores data in JSON files (one per entity type)
   - SQLiteStorage: Stores data in a SQLite database with appropriate tables

3. CLI option to select the format:
   ```
   --format [json|sqlite]
   ```

4. Example storage methods for each implementation:

   **SQLiteStorage**:
   ```python
   def save_test_case(self, test_case: TestCase, project_key: str):
       # Insert into test_cases table with appropriate fields
   ```

   **JSONStorage**:
   ```python
   def save_test_case(self, test_case: TestCase, project_key: str):
       # Update test_cases.json file with new test case
   ```

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](../../LICENSE)*