# ADR-013: ETL-Based Migration Workflow

## Status

Accepted

## Context

Migrating test data from Zephyr Scale to qTest is a complex process that involves:

1. Extracting large volumes of data from Zephyr API
2. Transforming between different data models and structures
3. Loading data into qTest with the correct relationships
4. Handling errors, retries, and resuming partial migrations
5. Providing visibility into the migration process
6. Ensuring data integrity throughout the process

We need to establish a clear workflow that handles these challenges while being maintainable, testable, and efficient.

## Decision

We will implement a structured ETL (Extract, Transform, Load) workflow for the migration process, with these key components:

1. **Extraction Phase**:
   - Fetch data from Zephyr using the existing client
   - Store raw data in an intermediate SQLite database
   - Download all attachments to a local cache
   - Implement checkpoints for resumable extraction

2. **Transformation Phase**:
   - Convert Zephyr entities to qTest model format
   - Resolve relationships between entities
   - Map custom fields with appropriate type conversions
   - Validate transformed data against qTest schemas
   - Store transformed data in SQLite with mapping tables

3. **Loading Phase**:
   - Create entities in qTest in dependency order
   - Track created entities and their IDs
   - Upload attachments linked to correct entities
   - Implement error handling and retry logic
   - Update progress in the database for resumability

4. **Workflow Orchestration**:
   - CLI commands for full ETL or individual phases
   - Migration state tracking for resumability
   - Progress reporting and logging
   - Validation checks between phases

## Consequences

### Positive

1. **Separation of Concerns**: Each phase has a distinct responsibility
2. **Resumability**: Process can be paused and resumed at checkpoints
3. **Visibility**: Clear status tracking throughout the migration
4. **Integrity**: Validation between phases ensures data quality
5. **Testability**: Each phase can be tested independently
6. **Performance**: Enables optimizations specific to each phase

### Negative

1. **Storage Overhead**: Requires intermediate storage for extracted and transformed data
2. **Processing Time**: Multiple phases add processing overhead
3. **Complexity**: More moving parts compared to a direct migration
4. **Development Effort**: Implementing a full ETL pipeline requires significant work

## Implementation Details

### Database Schema

The SQLite database will include:

1. **Zephyr Tables**: Raw entities from Zephyr
   - projects, test_cases, test_cycles, test_executions, attachments

2. **qTest Tables**: Transformed entities ready for qTest
   - projects, modules, test_cases, test_cycles, test_runs, executions

3. **Mapping Tables**: Track relationships between systems
   - zephyr_to_qtest_id_map

4. **State Tables**: Track migration progress
   - migration_state, entity_batch_state

### Workflow Steps

1. **Initialize Migration**:
   - Create database schema
   - Set up attachment storage
   - Initialize state tracking

2. **Extract Data**:
   - Fetch all projects if not specified
   - For each project:
     - Fetch test cases with pagination
     - Fetch test cycles with pagination
     - Fetch test executions with pagination
     - Download attachments
   - Update extraction state in database

3. **Transform Data**:
   - For each entity type (in order):
     - Read extracted data from database
     - Apply transformations
     - Validate against target schema
     - Store transformed data
   - Create mapping tables
   - Update transformation state

4. **Load Data**:
   - For each entity type (in dependency order):
     - Read transformed data
     - Create in qTest API
     - Store created entity IDs
     - Upload attachments
     - Update relationships
   - Update loading state

5. **Validate Migration**:
   - Count entities in source and target
   - Verify key entities exist
   - Check relationship integrity
   - Generate migration report

### Error Handling

1. **Extraction Errors**: Retry with exponential backoff
2. **Transformation Errors**: Log and continue with valid entities
3. **Loading Errors**: Retry with exponential backoff, rollback if needed
4. **Resumption Logic**: Store last successful checkpoint

## Review

This approach will be reviewed after implementing the first full migration to assess its effectiveness and identify areas for optimization. Success metrics include:

1. Migration success rate
2. Performance (entities per minute)
3. Resource utilization
4. Error recovery effectiveness

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](../../LICENSE)*