# ADR-015: Strategic Design Preferences

## Status

Accepted (2025-04-13)

## Context

The ZTOQ project involves numerous design decisions where multiple valid approaches exist. While previous ADRs document specific implementation choices, we need a central document to articulate our overall design philosophy and preferences. This document will help ensure consistent decision-making across the project and provide guidance for future contributors.

Rather than focusing on "right vs. wrong" technical choices, we need to establish our "lean toward" preferences that reflect the project's priorities and values.

## Decision

We will establish a set of strategic design preferences that guide our decision-making process. These preferences will be expressed as "prefer X over Y" statements to clearly communicate our leanings while acknowledging that exceptions may exist based on specific requirements.

### Core Preferences

1. **Prefer explicit configuration over implicit defaults**
   - We favor making configuration options explicit, even if it requires more code
   - Default values should be clearly documented and sensible for most use cases
   - Configuration options should be centralized and validated early

2. **Prefer type safety over dynamic typing**
   - We lean toward strong type hints and validation with Pydantic
   - Runtime type validation is preferred for external inputs
   - Internal interfaces should leverage Python's type system

3. **Prefer SQLAlchemy ORM over raw SQL**
   - ORM provides better abstraction and database independence
   - Use raw SQL only for performance-critical operations
   - Maintain proper separation between data access and business logic

4. **Prefer PostgreSQL for production over SQLite**
   - As detailed in ADR-014, PostgreSQL is our preferred production database
   - SQLite is acceptable for development, testing, and simple deployments
   - Design should accommodate both but optimize for PostgreSQL capabilities

5. **Prefer asynchronous I/O for API operations over synchronous calls**
   - Use async/await for network I/O and database operations when possible
   - Enable concurrent operations for better throughput
   - Fall back to synchronous operations when simplicity is more important than performance

6. **Prefer batch processing over individual record processing**
   - Design for bulk operations when possible (both API and database)
   - Implement batch state tracking for resumability
   - Optimize data structures for efficient batch operations

7. **Prefer fine-grained error handling over generic exceptions**
   - Catch specific exceptions rather than broad exception types
   - Provide contextual information with exceptions
   - Implement proper error recovery mechanisms rather than just logging

8. **Prefer structured logging over print statements**
   - Use the logging module with proper context and levels
   - Include correlation IDs for tracking operations across components
   - Configure appropriate handlers based on deployment environment

9. **Prefer test-driven development over post-implementation testing**
   - Write tests before or alongside implementation code
   - Focus on behavior verification rather than implementation details
   - Maintain a comprehensive test pyramid (unit, integration, e2e)

10. **Prefer composition over inheritance**
    - Use dependency injection for flexibility and testability
    - Favor small, focused classes with single responsibilities
    - Use mixins sparingly and only for well-defined cross-cutting concerns

11. **Prefer immutability over mutable state**
    - Use immutable data structures where possible
    - Implement proper state transitions with validation
    - Minimize side effects in functions

12. **Prefer automation over manual processes**
    - Automate testing, documentation, and deployment
    - Implement continuous integration with comprehensive checks
    - Create reproducible environments with defined dependencies

### API Design Preferences

1. **Prefer REST API design over RPC-style endpoints**
   - Follow RESTful resource modeling when possible
   - Use appropriate HTTP methods (GET, POST, PUT, DELETE)
   - Implement proper status codes and error responses

2. **Prefer OpenAPI-first design over ad-hoc API development**
   - Start with specification before implementation
   - Generate client code from OpenAPI specs
   - Validate requests/responses against the schema

3. **Prefer pagination for collections over large responses**
   - Implement consistent pagination across all collection endpoints
   - Support both offset and cursor-based pagination
   - Provide metadata about total results and page information

### Data Design Preferences

1. **Prefer canonical data models over direct API models**
   - Transform external API formats to internal canonical models
   - Define clear boundaries between external and internal representations
   - Implement proper validation at system boundaries

2. **Prefer structured schema migrations over ad-hoc changes**
   - Use Alembic for database schema evolution
   - Version control all schema changes
   - Implement both upgrade and downgrade paths

3. **Prefer normalized data for storage over denormalized forms**
   - Follow database normalization principles for storage
   - Use denormalization selectively for read optimization
   - Implement proper entity relationships with foreign keys

4. **Prefer explicit entity mapping over automatic conversion**
   - Define explicit mapping between source and target systems
   - Document mapping decisions and transformations
   - Validate entity relationships during mapping

## Rationale

These preferences reflect the project's emphasis on:

1. **Reliability**: Focus on error handling, testing, and proper state management
2. **Maintainability**: Favor clear, explicit code over clever shortcuts
3. **Scalability**: Design for growth with batch processing and proper database design
4. **Performance**: Enable concurrent operations and optimized data access
5. **Flexibility**: Provide options for different deployment scenarios

By establishing these preferences, we create a consistent foundation for decision-making that balances competing concerns while acknowledging that exceptions may be appropriate in specific contexts.

## Consequences

### Positive

- **Consistent architecture** across the codebase
- **Clear guidance** for new contributors
- **Reduced decision fatigue** for common patterns
- **Better alignment** with project goals and priorities

### Negative

- May lead to **over-engineering** if preferences are applied dogmatically
- Requires **periodic review** to ensure preferences remain relevant
- Can **increase initial development time** for simpler features

### Neutral

- These preferences are guidelines, not rigid rules
- Exceptions should be documented and justified
- Preferences may evolve as the project matures

## Related ADRs

- [ADR-003: Use Pydantic Models](003-use-pydantic-models.md)
- [ADR-007: Database Manager Implementation](007-database-manager-implementation.md)
- [ADR-009: Error Handling Strategy](009-error-handling-strategy.md)
- [ADR-010: Logging Strategy](010-logging-strategy.md)
- [ADR-014: Database Platform Strategy](014-database-platform-strategy.md)