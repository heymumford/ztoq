# ADR-014: Database Platform Strategy

## Status

Accepted (2025-04-13)

## Context

The ZTOQ migration tool requires a robust and scalable database solution to store and process test data during the migration process. We need to decide on the database platform(s) to support, considering:

1. Ease of development and testing
2. Production performance requirements
3. Compatibility with our canonical schema
4. Future Snowflake integration
5. Enterprise deployment considerations
6. Concurrency and transaction management

Our current implementation uses SQLAlchemy ORM with support for both SQLite and PostgreSQL. We need to formalize our strategy regarding which database(s) to prioritize and support.

## Decision

We will adopt a **hybrid database approach** with the following characteristics:

1. **Support both SQLite and PostgreSQL** with abstraction through SQLAlchemy ORM
2. **Prioritize PostgreSQL for production use cases** due to its:
   - Superior concurrency handling
   - Better transaction isolation
   - Advanced indexing and optimization capabilities
   - Closer alignment with Snowflake for future migration
   - Better support for enterprise-scale data volumes
3. **Use SQLite for development and simple deployments** because of its:
   - Zero-configuration setup
   - File-based portability
   - Simpler testing environment

## Implementation Details

1. **Configuration**:
   - Keep the existing `DatabaseConfig` class with `db_type` selector
   - Maintain separate connection handling for each database type
   - Provide PostgreSQL-specific optimization options

2. **Testing Strategy**:
   - Use SQLite for unit tests (faster, simpler setup)
   - Use PostgreSQL for integration and performance tests
   - Include tests for both database backends to ensure compatibility

3. **Documentation and Deployment**:
   - Document PostgreSQL as the recommended production option
   - Provide deployment guides for both database options
   - Include performance recommendations for PostgreSQL
   - Clearly document SQLite limitations for production use

4. **Transaction Management**:
   - Implement proper transaction isolation levels for PostgreSQL
   - Add safeguards for SQLite's more limited transaction capabilities
   - Use optimistic concurrency control when appropriate

5. **Connection Pooling**:
   - Implement sophisticated connection pooling for PostgreSQL
   - Use simpler connection management for SQLite

## Consequences

### Positive

- **Flexibility** for different deployment scenarios
- **Developer-friendly** experience with SQLite for quick iterations
- **Production-ready** solution with PostgreSQL
- **Future-proof** architecture with path to Snowflake
- **Performance optimization** opportunities with PostgreSQL

### Negative

- **Increased testing burden** to verify both database platforms
- **More complex codebase** to handle differences between databases
- **Potential for database-specific bugs** if not properly tested

### Neutral

- Need to document limitations of each database option
- Some features may be PostgreSQL-only in the future

## Related ADRs

- [ADR-007: Database Manager Implementation](007-database-manager-implementation.md)
- [ADR-013: ETL Migration Workflow](013-etl-migration-workflow.md)