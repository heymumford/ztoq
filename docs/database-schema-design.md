# Database Schema Design

This document outlines the database schema design for the Zephyr to qTest (ZTOQ) migration tool.

## Overview

The database schema is designed to efficiently store data from both Zephyr Scale and qTest, handling the migration process between these two test management systems. The schema supports:

1. **Cross-platform compatibility**: Works with both SQLite (for development/small datasets) and PostgreSQL (for production/large datasets)
2. **Flexible entity relationships**: Accommodates the complex relationships between test entities
3. **Custom field support**: Handles different custom field types and values
4. **Migration state tracking**: Maintains the state of ongoing migrations
5. **Performance optimization**: Includes appropriate indexes and constraints

## Entity Relationship Diagram

```
Project 1:N Folder
Project 1:N TestCase
Project 1:N TestCycle
Project 1:N TestPlan
Project 1:N Status
Project 1:N Priority
Project 1:N Environment
Folder 1:N Folder (recursive)
TestCase N:1 Folder
TestCase N:1 Priority
TestCase 1:N TestStep
TestCase 1:N ScriptFile
TestCase N:M Label
TestCase N:M CaseVersion
TestCase 1:N TestExecution
TestCycle N:1 Folder
TestCycle 1:N TestExecution
TestPlan N:1 Folder
TestExecution N:1 TestCase
TestExecution N:1 TestCycle
TestExecution N:1 Environment
TestExecution 1:N TestStep
```

## Core Tables

### Projects

The root entity for all test data.

```sql
CREATE TABLE projects (
    id VARCHAR(50) PRIMARY KEY,
    key VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT
);
```

### Folders

Hierarchical organization of test assets.

```sql
CREATE TABLE folders (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    folder_type VARCHAR(50) NOT NULL,
    parent_id VARCHAR(50) REFERENCES folders(id) ON DELETE SET NULL,
    project_key VARCHAR(50) NOT NULL REFERENCES projects(key) ON DELETE CASCADE
);
```

### Test Cases

Core test case entities.

```sql
CREATE TABLE test_cases (
    id VARCHAR(50) PRIMARY KEY,
    key VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    objective TEXT,
    precondition TEXT,
    description TEXT,
    status VARCHAR(50),
    priority_id VARCHAR(50) REFERENCES priorities(id) ON DELETE SET NULL,
    priority_name VARCHAR(100),
    folder_id VARCHAR(50) REFERENCES folders(id) ON DELETE SET NULL,
    folder_name VARCHAR(255),
    owner VARCHAR(100),
    owner_name VARCHAR(255),
    component VARCHAR(100),
    component_name VARCHAR(255),
    created_on TIMESTAMP,
    created_by VARCHAR(100),
    updated_on TIMESTAMP,
    updated_by VARCHAR(100),
    version VARCHAR(50),
    estimated_time INTEGER,
    project_key VARCHAR(50) NOT NULL REFERENCES projects(key) ON DELETE CASCADE
);
```

### Test Steps

Steps within test cases.

```sql
CREATE TABLE test_steps (
    id VARCHAR(50) PRIMARY KEY,
    index INTEGER NOT NULL,
    description TEXT NOT NULL,
    expected_result TEXT,
    data TEXT,
    actual_result TEXT,
    status VARCHAR(50),
    test_case_id VARCHAR(50) REFERENCES test_cases(id) ON DELETE CASCADE,
    test_execution_id VARCHAR(50) REFERENCES test_executions(id) ON DELETE CASCADE
);
```

### Test Cycles

Test execution cycles.

```sql
CREATE TABLE test_cycles (
    id VARCHAR(50) PRIMARY KEY,
    key VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50),
    status_name VARCHAR(100),
    folder_id VARCHAR(50) REFERENCES folders(id) ON DELETE SET NULL,
    folder_name VARCHAR(255),
    owner VARCHAR(100),
    owner_name VARCHAR(255),
    created_on TIMESTAMP,
    created_by VARCHAR(100),
    updated_on TIMESTAMP,
    updated_by VARCHAR(100),
    planned_start_date TIMESTAMP,
    planned_end_date TIMESTAMP,
    project_key VARCHAR(50) NOT NULL REFERENCES projects(key) ON DELETE CASCADE
);
```

### Test Executions

Individual test case executions.

```sql
CREATE TABLE test_executions (
    id VARCHAR(50) PRIMARY KEY,
    test_case_key VARCHAR(50) NOT NULL REFERENCES test_cases(key) ON DELETE CASCADE,
    cycle_id VARCHAR(50) NOT NULL REFERENCES test_cycles(id) ON DELETE CASCADE,
    cycle_name VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    status_name VARCHAR(100),
    environment_id VARCHAR(50) REFERENCES environments(id) ON DELETE SET NULL,
    environment_name VARCHAR(100),
    executed_by VARCHAR(100),
    executed_by_name VARCHAR(255),
    executed_on TIMESTAMP,
    created_on TIMESTAMP,
    created_by VARCHAR(100),
    updated_on TIMESTAMP,
    updated_by VARCHAR(100),
    actual_time INTEGER,
    comment TEXT,
    project_key VARCHAR(50) NOT NULL REFERENCES projects(key) ON DELETE CASCADE
);
```

## Supporting Tables

### Priorities

Test case priority values.

```sql
CREATE TABLE priorities (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    color VARCHAR(20),
    rank INTEGER NOT NULL,
    project_key VARCHAR(50) NOT NULL REFERENCES projects(key) ON DELETE CASCADE
);
```

### Statuses

Status values for various entities.

```sql
CREATE TABLE statuses (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    color VARCHAR(20),
    type VARCHAR(50) NOT NULL,
    project_key VARCHAR(50) NOT NULL REFERENCES projects(key) ON DELETE CASCADE
);
```

### Environments

Test execution environments.

```sql
CREATE TABLE environments (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    project_key VARCHAR(50) NOT NULL REFERENCES projects(key) ON DELETE CASCADE
);
```

### Labels

Labels/tags for test cases.

```sql
CREATE TABLE labels (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);
```

## Custom Field Handling

### Custom Field Definitions

Definitions for custom fields.

```sql
CREATE TABLE custom_field_definitions (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    project_key VARCHAR(50) NOT NULL REFERENCES projects(key) ON DELETE CASCADE
);
```

### Custom Field Values

Values for custom fields, with support for different data types.

```sql
CREATE TABLE custom_field_values (
    id VARCHAR(50) PRIMARY KEY,
    field_id VARCHAR(50) NOT NULL REFERENCES custom_field_definitions(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(50) NOT NULL,
    value_text TEXT,
    value_numeric FLOAT,
    value_boolean BOOLEAN,
    value_date TIMESTAMP,
    value_json TEXT
);
```

## Attachments and Links

### Attachments

Binary attachments for entities.

```sql
CREATE TABLE attachments (
    id VARCHAR(50) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    size INTEGER,
    created_on TIMESTAMP,
    created_by VARCHAR(100),
    content BYTEA,
    content_url VARCHAR(2000),
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(50) NOT NULL
);
```

### Links

External/internal links for entities.

```sql
CREATE TABLE links (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(2000) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(50) NOT NULL
);
```

## Migration Tracking Tables

### Migration State

Overall migration state tracking.

```sql
CREATE TABLE migration_state (
    id SERIAL PRIMARY KEY,
    project_key VARCHAR(50) UNIQUE,
    extraction_status VARCHAR(50),
    transformation_status VARCHAR(50),
    loading_status VARCHAR(50),
    last_updated TIMESTAMP,
    error_message TEXT,
    meta_data TEXT
);
```

### Entity Batch State

Tracking state of batch processing.

```sql
CREATE TABLE entity_batch_state (
    id SERIAL PRIMARY KEY,
    project_key VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    batch_number INTEGER NOT NULL,
    total_batches INTEGER,
    items_count INTEGER,
    processed_count INTEGER,
    status VARCHAR(50),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_updated TIMESTAMP,
    error_message TEXT,
    UNIQUE(project_key, entity_type, batch_number)
);
```

### Recommendation History

Track migration improvement recommendations.

```sql
CREATE TABLE recommendation_history (
    id SERIAL PRIMARY KEY,
    project_key VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    recommendation_id VARCHAR(50) NOT NULL,
    priority VARCHAR(10) NOT NULL,
    category VARCHAR(50) NOT NULL,
    issue TEXT NOT NULL,
    action TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    implemented_at TIMESTAMP,
    impact_score FLOAT,
    migration_phase VARCHAR(20),
    entity_type VARCHAR(50),
    meta_data JSONB
);
```

## Indexing Strategy

### Primary Indexes

- Primary keys on all tables
- Unique constraints on business keys

### Foreign Key Indexes

- All foreign key columns are indexed

### Performance Indexes

- Compound indexes for common query patterns:
  - project_key + entity_type (batch state)
  - entity_type + entity_id (custom fields, attachments)
  - project_key + timestamp (recommendation history)

## SQLite vs PostgreSQL Considerations

### Type Differences

- `BYTEA` in PostgreSQL vs `BLOB` in SQLite
- `JSONB` in PostgreSQL vs `TEXT` in SQLite

### Transaction Support

- PostgreSQL: Full ACID compliance with robust transaction isolation
- SQLite: Limited concurrent write operations

### Performance Optimization

- PostgreSQL: Advanced indexing, partitioning for large datasets
- SQLite: In-memory mode for performance testing

## Migration Strategy

### Initial Schema

The initial schema is created using Alembic migrations. The first migration creates all core tables with their relationships.

### Incremental Updates

Additional migrations add features such as:
- The recommendation history table
- Enhanced indexing
- New entity types

### Handling Custom Fields

Custom fields use a flexible key-value approach where:
1. Definitions are stored with their data types
2. Values are stored with type-specific columns
3. JSON is used for complex structured data

## Cross-Database Support

The schema is designed to work seamlessly with both SQLite and PostgreSQL:

1. SQLAlchemy ORM abstracts database differences
2. Alembic migrations handle database-specific SQL
3. Connection pooling is configured appropriately for each database
4. Transactions are managed with appropriate isolation levels

---

*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](../LICENSE)*