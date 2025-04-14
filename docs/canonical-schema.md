# Canonical Schema for Zephyr to qTest Migration

This document describes the canonical schema that defines our standardized data model for the ZTOQ migration process. The canonical schema ensures compatibility between Zephyr Scale and qTest systems, while providing a clean future migration path to Snowflake.

## Canonical Data Schema

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
```

## Mapping Between Systems

| Canonical Entity | Zephyr Source                         | qTest Target                     |
|------------------|---------------------------------------|----------------------------------|
| Project          | Project Key & Name                    | Project                          |
| Folder           | Folder                                | Module/TestSuite                 |
| TestCase         | Test Case (Objective, Preconditions)  | Test Case                        |
| TestStep         | Test Steps                            | Test Steps                       |
| TestCycle        | Test Cycle                            | Test Cycle                       |
| TestExecution    | Test Execution                        | Test Run & Test Log              |
| CustomField      | Custom Fields (Generic structure)     | Custom Fields                    |
| Attachment       | Binary attachments (files, images)    | Attachments                      |

## Optimizations and Implementation

### Database Indexes

```sql
-- Project indexes
CREATE INDEX idx_project_key ON Project(project_key);

-- Folder indexes
CREATE INDEX idx_folder_project ON Folder(project_id);
CREATE INDEX idx_folder_parent ON Folder(parent_folder_id);

-- TestCase indexes
CREATE INDEX idx_testcase_project ON TestCase(project_id);
CREATE INDEX idx_testcase_folder ON TestCase(folder_id);
CREATE INDEX idx_testcase_key ON TestCase(key);
CREATE INDEX idx_testcase_status ON TestCase(status);

-- TestStep indexes
CREATE INDEX idx_step_testcase ON TestStep(test_case_id);
CREATE INDEX idx_step_order ON TestStep(step_order);

-- TestCycle indexes
CREATE INDEX idx_testcycle_project ON TestCycle(project_id);
CREATE INDEX idx_testcycle_folder ON TestCycle(folder_id);
CREATE INDEX idx_testcycle_key ON TestCycle(key);
CREATE INDEX idx_testcycle_status ON TestCycle(status);

-- TestExecution indexes
CREATE INDEX idx_execution_testcycle ON TestExecution(test_cycle_id);
CREATE INDEX idx_execution_testcase ON TestExecution(test_case_id);
CREATE INDEX idx_execution_status ON TestExecution(status);
CREATE INDEX idx_execution_project ON TestExecution(test_case_id, test_cycle_id);

-- CustomField indexes
CREATE INDEX idx_customfield_object ON CustomField(object_type, object_id);
CREATE INDEX idx_customfield_name ON CustomField(field_name);

-- Attachment indexes
CREATE INDEX idx_attachment_related ON Attachment(related_type, related_id);
```

### Implementation Strategy

We implement this canonical schema in our ETL process using:

1. **SQLAlchemy ORM**: For type-safe database operations with connection pooling
2. **Alembic**: For database migrations and schema evolution
3. **Parallel Processing**:
   - **Extraction**: Async/aiohttp for parallel API calls
   - **Transformation**: Pandas/numpy for efficient data processing
   - **Loading**: concurrent.futures for parallel qTest uploads

### Custom Field Approach

The schema uses a flexible key-value approach for custom fields rather than separate tables for different field types, providing:

- Support for Zephyr and qTest's diverse custom field types
- Simplified querying and mapping
- Elimination of schema changes when new custom field types are added
- Efficient migration to Snowflake's JSON/semi-structured features

### Batch Processing

For efficiency in high-volume operations:

- Extractions use pagination with adaptive rate limiting
- Transformations use pandas DataFrame batch operations
- Loading leverages qTest's bulk APIs like `/auto-test-logs`

## Snowflake Integration

This schema is designed for smooth future migration to Snowflake:

- All tables use Snowflake-compatible data types
- CustomField entity uses key-value pattern compatible with Snowflake's VARIANT type
- TIMESTAMP fields support Snowflake's timestamp functionality
- Joins and relationships all use standard SQL patterns

When migrating to Snowflake, we can optimize for:

- Warehouse-specific architecture (micro-partitioning)
- Clustering keys based on common query patterns (project_id, created_on)
- Snowflake's bulk-loading capabilities
- JSON storage for complex attributes

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](../LICENSE)*