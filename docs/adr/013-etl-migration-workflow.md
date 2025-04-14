# ADR-013: SQL-Based ETL Migration Workflow

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
7. Setting up future compatibility with Snowflake

We need to establish a clear workflow that handles these challenges while being maintainable, testable, and efficient. The previous approach used SQLite only as an intermediate store, but we need a more robust SQL solution that supports future migration to Snowflake.

## Decision

We will implement a structured SQL-based ETL (Extract, Transform, Load) workflow for the migration process, with these key components:

1. **Extraction Phase**:
   - Fetch data from Zephyr using the existing client with parallel processing
   - Store raw data in a SQL database (PostgreSQL or SQLite)
   - Download all attachments to the database as binary blobs
   - Implement checkpoints for resumable extraction

2. **Transformation Phase**:
   - Use SQL queries and pandas for data transformation
   - Convert Zephyr entities to qTest model format
   - Resolve relationships between entities
   - Map custom fields with appropriate type conversions
   - Validate transformed data against qTest schemas
   - Store transformed data in SQL with mapping tables

3. **Loading Phase**:
   - Create entities in qTest in dependency order using parallel processing
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

1. **Robust Data Storage**: SQL provides transaction safety and data integrity
2. **Scalability**: Supports larger datasets with indexing and query optimization
3. **Concurrency**: Enables parallel operations with proper locking
4. **Resumability**: Process can be paused and resumed at checkpoints
5. **Visibility**: Clear status tracking throughout the migration
6. **Integrity**: Validation between phases ensures data quality
7. **Testability**: Each phase can be tested independently
8. **Performance**: Enables optimizations specific to each phase
9. **Future-Proofing**: SQL format provides clear path to Snowflake migration

### Negative

1. **Database Setup**: Requires SQL database configuration and maintenance
2. **Complexity**: More moving parts compared to a direct migration
3. **Development Effort**: Implementing a full SQL-based ETL pipeline requires significant work
4. **Learning Curve**: Team needs to understand SQL and related technologies

## Implementation Details

### Canonical Database Schema

We will use a canonical database schema that ensures compatibility between both Zephyr and qTest systems, while also supporting future migration to Snowflake:

```sql
CREATE TABLE Project (
    project_id VARCHAR PRIMARY KEY,
    project_key VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Folder (
    folder_id BIGINT PRIMARY KEY,
    project_id VARCHAR REFERENCES Project(project_id),
    parent_folder_id BIGINT REFERENCES Folder(folder_id),
    name VARCHAR NOT NULL,
    type VARCHAR CHECK(type IN ('TEST_CASE', 'TEST_PLAN', 'TEST_CYCLE')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE TestCase (
    test_case_id BIGINT PRIMARY KEY,
    project_id VARCHAR REFERENCES Project(project_id),
    folder_id BIGINT REFERENCES Folder(folder_id),
    key VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    objective TEXT,
    precondition TEXT,
    estimated_time_ms BIGINT,
    priority VARCHAR,
    status VARCHAR,
    owner_id VARCHAR,
    created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE TestStep (
    step_id BIGINT PRIMARY KEY,
    test_case_id BIGINT REFERENCES TestCase(test_case_id),
    step_order INT NOT NULL,
    description TEXT NOT NULL,
    expected_result TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE TestCycle (
    test_cycle_id BIGINT PRIMARY KEY,
    project_id VARCHAR REFERENCES Project(project_id),
    folder_id BIGINT REFERENCES Folder(folder_id),
    key VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    description TEXT,
    planned_start_date TIMESTAMP,
    planned_end_date TIMESTAMP,
    status VARCHAR,
    owner_id VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE TestExecution (
    execution_id BIGINT PRIMARY KEY,
    test_cycle_id BIGINT REFERENCES TestCycle(test_cycle_id),
    test_case_id BIGINT REFERENCES TestCase(test_case_id),
    status VARCHAR NOT NULL,
    executed_by_id VARCHAR,
    assigned_to_id VARCHAR,
    execution_time_ms BIGINT,
    actual_end_date TIMESTAMP,
    environment VARCHAR,
    comment TEXT,
    automated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE CustomField (
    custom_field_id SERIAL PRIMARY KEY,
    object_type VARCHAR CHECK(object_type IN ('TestCase', 'TestCycle', 'TestExecution')),
    object_id BIGINT NOT NULL,
    field_name VARCHAR NOT NULL,
    field_value TEXT,
    UNIQUE(object_type, object_id, field_name)
);

CREATE TABLE Attachment (
    attachment_id SERIAL PRIMARY KEY,
    related_type VARCHAR CHECK(related_type IN ('TestCase', 'TestExecution', 'TestStep')),
    related_id BIGINT NOT NULL,
    attachment_name VARCHAR NOT NULL,
    attachment_blob BYTEA,
    attachment_url VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- State tracking tables
CREATE TABLE migration_state (
    id SERIAL PRIMARY KEY,
    project_key VARCHAR UNIQUE NOT NULL,
    extraction_status VARCHAR,
    transformation_status VARCHAR,
    loading_status VARCHAR,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    meta_data TEXT
);

CREATE TABLE entity_batch_state (
    id SERIAL PRIMARY KEY,
    project_key VARCHAR NOT NULL,
    entity_type VARCHAR NOT NULL,
    batch_number INT NOT NULL,
    total_batches INT,
    items_count INT,
    processed_count INT DEFAULT 0,
    status VARCHAR,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    UNIQUE(project_key, entity_type, batch_number)
);
```

This schema design provides a clear mapping between Zephyr and qTest entities:

| Canonical Entity | Zephyr Source                         | qTest Target                     |
|------------------|---------------------------------------|----------------------------------|
| Project          | Project Key & Name                    | Project                          |
| Folder           | Folder                                | Module/TestSuite                 |
| TestCase         | Test Case (Objective, Preconditions)  | Test Case                        |
| TestStep         | Test Steps                            | Test Steps                       |
| TestCycle        | Test Cycle                            | Test Cycle                       |
| TestExecution    | Test Execution                        | Test Run & Test Log              |
| CustomField      | Custom Fields (Key-value approach)    | Custom Fields                    |
| Attachment       | Binary attachments (files, images)    | Attachments                      |

### Database Optimizations

1. **Indexing**:
   ```sql
   CREATE INDEX idx_project_key ON Project(project_key);
   CREATE INDEX idx_testcase_project ON TestCase(project_id);
   CREATE INDEX idx_execution_testcycle ON TestExecution(test_cycle_id);
   CREATE INDEX idx_attachments_related ON Attachment(related_type, related_id);
   ```

2. **Connection Pooling**:
   - Use SQLAlchemy's connection pool management
   - Configure pool size based on system resources
   - Implement connection recycling for long-running operations

3. **Transaction Management**:
   - Use explicit transactions for related operations
   - Implement savepoints for partial rollbacks
   - Configure appropriate isolation level for concurrent operations

4. **Performance Optimizations**:
   - Batch operations for bulk inserts
   - Use prepared statements for repeated queries
   - Implement query plan optimization

### Workflow Steps

1. **Initialize Migration**:
   - Create database schema and migrations
   - Initialize state tracking
   - Set up indexes and constraints

2. **Extract Data (Parallel)**:
   - Fetch all projects if not specified
   - For each project (in parallel with asyncio):
     - Fetch test cases with pagination
     - Fetch test cycles with pagination
     - Fetch test executions with pagination
     - Download attachments as binary blobs
   - Store everything in SQL database
   - Update extraction state

3. **Transform Data**:
   - Execute SQL queries to transform raw data
   - Use pandas for complex transformations
   - Apply mapping rules between systems
   - Validate against target schema
   - Store transformed data
   - Create mapping tables

4. **Load Data (Parallel)**:
   - For each entity type (in dependency order):
     - Read transformed data
     - Create multiple entities in parallel in qTest API
     - Store created entity IDs
     - Upload attachments
     - Update relationships
   - Update loading state

5. **Validate Migration**:
   - Count entities in source and target
   - Verify key entities exist
   - Check relationship integrity
   - Generate migration report

### Error Handling and Recovery

1. **Extraction Errors**: Retry with exponential backoff, store last successful batch
2. **Transformation Errors**: Log and continue with valid entities, mark failures
3. **Loading Errors**: Retry with exponential backoff, rollback if needed
4. **Database Errors**: Transaction rollback, connection retry
5. **Resume Logic**: Store checkpoints for each phase
6. **Monitoring**: Track progress metrics in dedicated tables

### Future Snowflake Migration

The SQL database schema is designed to be compatible with future migration to Snowflake:

1. **Schema Compatibility**: Tables and relationships follow Snowflake conventions
2. **ETL Readiness**: Data already stored in structured format for easy loading
3. **Transformation Pipeline**: SQL-based transformations can be reused

## Review

This approach will be reviewed after implementing the first full migration to assess its effectiveness and identify areas for optimization. Success metrics include:

1. Migration success rate
2. Performance (entities per minute)
3. Resource utilization
4. Error recovery effectiveness
5. Database scalability
6. Path to Snowflake readiness

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](../../LICENSE)*