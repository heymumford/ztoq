# ADR-011: qTest Integration Architecture

## Status

Accepted

## Context

The ZTOQ tool was initially designed to extract test data from Zephyr Scale. Now, we need to extend it to support migration of test data to qTest. This requires implementing an architecture that supports:

1. Connecting to qTest APIs (Manager, Parameters, Pulse, and Scenario)
2. Converting Zephyr test entities to qTest entity formats
3. Supporting all qTest entity types and their relationships
4. Handling file attachments and binary content transfers
5. Supporting large dataset migration with proper error handling and recovery

The qTest API is split into four separate APIs with different authentication mechanisms, pagination approaches, and data formats. We need to create a unified client that abstracts these differences.

## Decision

We will implement a comprehensive qTest integration using a modular architecture with these components:

1. **QTestClient**: A unified client that handles all four qTest APIs:
   - Automatic API type detection and switching
   - Authentication for each API type
   - Shared request handling with appropriate error handling
   - Rate limiting and retry mechanisms
   - Pagination support across different API types

2. **QTest Models**: Pydantic models for all qTest entities:
   - Manager API: Projects, Modules, Test Cases, Test Cycles, Test Runs, Executions
   - Parameters API: Parameters, Parameter Values, Datasets, Dataset Rows
   - Pulse API: Rules, Actions, Triggers
   - Scenario API: Features, Scenarios, Steps

3. **QTest Mock Server**: A mock server for testing:
   - Comprehensive entity simulation for all API types
   - Realistic responses matching API behavior
   - Support for all CRUD operations
   - Authentication simulation
   - Error simulation for testing edge cases

4. **Entity Mapping Layer**:
   - Transformation logic from Zephyr to qTest entities
   - Type conversion for custom fields
   - Relationship preservation
   - Validation of transformed data

5. **Migration Workflow**:
   - Extraction from Zephyr
   - Transformation to qTest format
   - Validation before loading
   - Loading to qTest with dependency ordering
   - Tracking and resume capability

## Consequences

### Positive

1. **Unified Interface**: All qTest API interactions happen through a single client interface, simplifying code
2. **Comprehensive Testing**: Mock server enables thorough testing without real API access
3. **Type Safety**: Pydantic models ensure data integrity and validation
4. **Scalability**: Pagination handling enables processing large datasets
5. **Robustness**: Error handling, retries, and validation at each step prevents data corruption
6. **Extensibility**: The modular architecture allows for adding new entity types or API versions

### Negative

1. **Complexity**: Supporting four different APIs increases the implementation complexity
2. **Maintenance Burden**: Changes to any qTest API may require updates to multiple components
3. **Performance Overhead**: Additional validation and transformation steps may impact performance
4. **Development Time**: Building a comprehensive client and mock server requires significant effort

## Implementation Approach

1. Use Test-Driven Development (TDD) approach:
   - Write acceptance tests for each component
   - Implement to pass tests
   - Refactor while maintaining test coverage

2. Implement in phases:
   - Phase 1: Core models and API client
   - Phase 2: Mock server for testing
   - Phase 3: Entity mapping and transformation
   - Phase 4: Migration workflow
   - Phase 5: Performance optimization and error handling

## Technical Details

### Authentication

qTest uses OAuth2 for authentication, but with slightly different endpoints and parameters for each API type. Our client will handle these differences transparently.

### Pagination

The Manager API and other APIs use different pagination mechanisms:
- Manager: Uses page-based pagination
- Parameters, Pulse, Scenario: Use offset-based pagination

We will implement a unified `QTestPaginatedIterator` that handles both pagination styles transparently.

### API Versioning

Our client will be designed to work with:
- Manager API v3
- Parameters API v1
- Pulse API (no specific version)
- Scenario API (no specific version)

### Performance Considerations

- Implement connection pooling
- Use batched operations where possible
- Support parallel processing for independent entities
- Implement intelligent retry mechanisms with exponential backoff