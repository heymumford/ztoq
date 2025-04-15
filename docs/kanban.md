# Zephyr to qTest Migration - Kanban Board

> For a historical record of completed work with reasoning and lessons learned, see [Kanban History](https://github.com/heymumford/ztoq/blob/main/docs/kanban-history.md)

## Backlog

### Phase 16: Code Quality and Linting

#### Linting Improvements
- [x] **[LINT-1]** Consolidate linting tools in ruff configuration *(Removed redundant linters like black, flake8, isort, and standardized on ruff as the primary linting tool)*
- [x] **[LINT-2]** Create utility scripts for common linting fixes *(Created scripts for removing unused imports and fixing logging statements)*
- [x] **[LINT-3]** Fix import-related linting issues *(Fixed hundreds of unused import issues across the codebase)*
- [x] **[LINT-4]** Fix formatting and style issues *(Addressed trailing commas, whitespace, quotes consistency, and other style issues)*
- [ ] **[LINT-5]** Fix logging format issues (G004) *(Convert f-string logging to correct string interpolation)*
- [ ] **[LINT-6]** Add missing type annotations for public APIs
- [ ] **[LINT-7]** Update pytest assertions to follow pytest style
- [ ] **[LINT-8]** Add missing __init__.py files to namespace packages
- [ ] **[LINT-9]** Refactor complex functions to improve maintainability

#### Test Coverage Improvements
- [x] **[TEST-COV-1]** Implement negative tests for ETL error handling *(Created comprehensive test suite focused on error handling in extraction, transformation, and loading phases)*
- [x] **[TEST-COV-2]** Implement tests for database error handling *(Added robust tests for database connection errors, constraint violations, transaction failures, and recovery mechanisms)*
- [x] **[TEST-COV-3]** Implement tests for concurrent operation error handling *(Created test suite focusing on thread pool errors, partial batch failures, and parallel processing edge cases)*

### Phase 1: Core Infrastructure

#### Test Foundations
- [x] **[TEST-INFRA-2]** Create base test fixtures and factories
- [x] **[TEST-INFRA-3]** Implement test harness for API mocking

#### Unit Tests First
- [x] **[TEST-UNIT-1]** Write unit tests for project structure and configuration *(Implemented comprehensive tests for project structure, configuration validation, environment variable handling, and CLI command structure)*
- [x] **[SETUP-1]** Set up project structure and dependencies *(Implemented a comprehensive utilities module with package information, dependency management, version management, and project structure verification)*
- [x] **[TEST-UNIT-2]** Write unit tests for CLI framework and command parsing *(Implemented tests for CLI version flags, command parsing, debug mode, and environment variable handling)*
- [x] **[SETUP-2]** Create configuration management module with environment variable support *(Implemented a complete configuration management module with support for environment variables, validation, and nested configurations for different components)*
- [x] **[SETUP-3]** Implement CLI framework with debug mode flag *(Enhanced CLI framework with debug mode flag, version information, and proper logging configuration)*

#### Integration Tests
- [x] **[TEST-INT-1]** Write integration tests for SQL database schema and migrations
- [x] **[SETUP-4]** Design PostgreSQL/SQLite database schema with migration scripts *(Implemented comprehensive database schema with SQLAlchemy ORM models, migration scripts for both PostgreSQL and SQLite, and performance optimizations)*
- [x] **[SETUP-5]** Create database connection manager with pooling and transaction support *(Implemented a robust database connection manager with support for both PostgreSQL and SQLite, connection pooling, transaction management with isolation levels, and performance monitoring)*

#### Acceptance Tests
- [x] **[TEST-E2E-1]** Write acceptance tests for CLI commands *(Implemented comprehensive acceptance tests for both the main CLI commands and workflow CLI commands, including thorough test fixtures and mock configurations)*
- [x] **[SETUP-6]** Set up logging infrastructure with contextual error tracking
- [ ] **[SETUP-7]** Implement test fixtures for acceptance testing

### Phase 14: Resource Management and Performance Optimization

#### Connection Pooling Improvements
- [x] **[PERF-10]** Enhance connection pooling for thread safety and resource cleanup *(Implemented improved connection pooling with daemon threads, deadlock prevention, and proper async cleanup mechanisms)*
- [x] **[PERF-11]** Add timeout management for asynchronous tasks *(Added configurable timeouts for all async worker tasks to prevent resource leaks and ensure bounded execution time)*

#### Memory Management
- [x] **[PERF-12]** Implement automatic cleanup for completed work items *(Added a configurable cleanup mechanism for work queues to prevent unbounded memory growth with completed items)*
- [x] **[PERF-13]** Add circuit breaker cleanup to prevent unbounded growth *(Implemented periodic cleanup of idle circuit breakers to prevent memory leaks in long-running applications)*

#### Session Management
- [x] **[PERF-14]** Enhance thread-local session management *(Improved thread-local session handling with automatic cleanup on thread exit and proper exception handling)*
- [x] **[PERF-15]** Improve transaction isolation and error handling *(Enhanced transaction management with better error handling, proper session state checking, and improved resource cleanup)*

#### Documentation
- [x] **[DOC-9]** Create comprehensive resource management guide *(Developed resource-management.md with detailed best practices for connection pooling, session management, thread safety, and memory optimization with practical code examples)*
- [x] **[DOC-10]** Update client documentation with cleanup methods *(Enhanced client documentation with explicit cleanup methods, resource management patterns, and comprehensive examples for proper resource handling)*

### Phase 15: Data Vacuum and Export

#### Unit Tests
- [ ] **[TEST-UNIT-40]** Write unit tests for Zephyr data vacuum functionality
- [ ] **[VACUUM-1]** Implement Zephyr data vacuum functionality using URL and token
- [ ] **[TEST-UNIT-41]** Write unit tests for data review CLI commands
- [ ] **[VACUUM-2]** Create CLI commands for reviewing vacuumed data
- [ ] **[TEST-UNIT-42]** Write unit tests for qTest export functionality
- [ ] **[EXPORT-1]** Implement qTest export functionality with project selection

#### Integration Tests
- [ ] **[TEST-INT-26]** Write integration tests for data pipeline with retries
- [ ] **[EXPORT-2]** Implement data pipeline with individual record retries
- [ ] **[TEST-INT-27]** Write integration tests for destination validation
- [ ] **[EXPORT-3]** Add validation to ensure destination qTest has valid data copies

### Phase 2: Extraction Service

#### Unit Tests
- [ ] **[TEST-UNIT-3]** Write unit tests for Zephyr API client
- [ ] **[EXTRACT-1]** Create Zephyr API client with retry logic
- [ ] **[TEST-UNIT-4]** Write unit tests for test case extraction
- [ ] **[EXTRACT-2]** Implement test case extraction with pagination support
- [ ] **[TEST-UNIT-5]** Write unit tests for test cycle extraction
- [ ] **[EXTRACT-3]** Implement test cycle extraction with validation
- [ ] **[TEST-UNIT-6]** Write unit tests for test execution extraction
- [ ] **[EXTRACT-4]** Implement test execution extraction with integrity checks
- [ ] **[TEST-UNIT-7]** Write unit tests for attachment downloading
- [ ] **[EXTRACT-5]** Implement attachment download module with checksums

#### Integration Tests
- [ ] **[TEST-INT-2]** Write integration tests for extraction flow
- [ ] **[EXTRACT-6]** Add pagination and adaptive rate limiting
- [ ] **[TEST-INT-3]** Write integration tests for error handling across extraction flow
- [ ] **[EXTRACT-7]** Implement detailed logging with contextual information
- [ ] **[TEST-INT-4]** Write integration tests for concurrent extraction
- [ ] **[EXTRACT-8]** Implement concurrent extraction with asyncio and aiohttp

#### Acceptance Tests
- [ ] **[TEST-E2E-2]** Write acceptance tests for the extraction CLI command
- [ ] **[EXTRACT-9]** Integrate extraction into CLI with progress reporting

### Phase 3: SQL Database Implementation

#### Unit Tests
- [x] **[TEST-UNIT-8]** Write unit tests for database models and schemas
- [x] **[DB-1]** Define SQL models and schemas with SQLAlchemy
- [x] **[TEST-UNIT-9]** Write unit tests for database connection management
- [x] **[DB-2]** Implement connection pooling and management
- [x] **[TEST-UNIT-10]** Write unit tests for transaction handling
- [x] **[DB-3]** Implement transaction management with proper error handling
- [x] **[TEST-UNIT-11]** Write unit tests for entity storage operations
- [x] **[DB-4]** Implement entity CRUD operations with validation

#### Integration Tests
- [x] **[TEST-INT-5]** Write integration tests for database migrations
- [x] **[DB-5]** Implement database migration system with Alembic
- [x] **[TEST-INT-6]** Write integration tests for parallel database operations
- [x] **[DB-6]** Implement concurrent database operations with proper locking
- [x] **[TEST-INT-7]** Write integration tests for error handling and recovery
- [x] **[DB-7]** Implement database error handling and recovery procedures

#### Performance Tests
- [ ] **[TEST-PERF-1]** Create database performance test suite
- [x] **[DB-8]** Optimize database queries and indexes
- [ ] **[TEST-PERF-2]** Measure and benchmark database operations
- [ ] **[DB-9]** Implement database query caching and optimization

### Phase 4: Mock Infrastructure

#### Unit Tests
- [x] **[TEST-UNIT-12]** Define unit tests for Zephyr mock factories
- [x] **[MOCK-1]** Create mock factory for Zephyr API responses
- [x] **[TEST-UNIT-13]** Write unit tests for Zephyr mock server endpoints
- [x] **[MOCK-2]** Build mock server for Zephyr API endpoints
- [x] **[TEST-UNIT-14]** Define unit tests for qTest mock factories
- [x] **[MOCK-3]** Create mock factory for qTest API responses
- [x] **[TEST-UNIT-15]** Write unit tests for qTest mock server endpoints
- [x] **[MOCK-4]** Build mock server for qTest API endpoints

#### Integration Tests
- [x] **[TEST-INT-8]** Write integration tests for mock server performance
- [x] **[TEST-INT-9]** Verify mock server API compatibility with real endpoints

### Phase 5: Transformation Service

#### Unit Tests
- [x] **[TEST-UNIT-16]** Write unit tests for entity mapping definitions
- [x] **[TRANSFORM-1]** Create entity mapping definitions with validation rules
- [x] **[TEST-UNIT-17]** Write unit tests for test case transformer
- [x] **[TRANSFORM-2]** Implement test case transformer with error boundaries
- [x] **[TEST-UNIT-18]** Write unit tests for test cycle transformer
- [x] **[TRANSFORM-3]** Implement test cycle transformer with validation
- [x] **[TEST-UNIT-19]** Write unit tests for test execution transformer
- [x] **[TRANSFORM-4]** Implement test execution transformer with data normalization
- [x] **[TEST-UNIT-20]** Write unit tests for custom field mapper
- [x] **[TRANSFORM-5]** Implement custom field mapper with type checking

#### Integration Tests
- [x] **[TEST-INT-10]** Write integration tests for relationship resolution
- [x] **[TRANSFORM-6]** Create data quality validation layer
- [x] **[TEST-INT-11]** Write integration tests for transformation flow *(Implemented comprehensive tests for transformation flow with error handling and recovery)*
- [x] **[TRANSFORM-7]** Implement SQL-based transformation with pandas *(Created high-performance batch transformation using pandas and SQLite/SQLAlchemy)*
- [x] **[TEST-INT-12]** Write integration tests for batch transformations *(Implemented tests for batch processing, error handling, and performance)*
- [x] **[TRANSFORM-8]** Implement batch transformation process *(Integrated SQL-based batch transformer with workflow orchestrator for efficient processing of large datasets)*

#### Acceptance Tests
- [ ] **[TEST-E2E-3]** Write acceptance tests for the transformation CLI command
- [ ] **[TRANSFORM-9]** Integrate transformation into CLI with validation reporting

### Phase 6: qTest Integration

#### Unit Tests
- [ ] **[TEST-UNIT-21]** Write unit tests for qTest entity models
- [ ] **[QTEST-1]** Finalize Pydantic models for qTest entities (Manager, Parameters, Pulse, Scenario)
- [x] **[TEST-UNIT-22]** Write unit tests for qTest authentication
- [x] **[QTEST-2]** Implement qTest authentication and token management *(Added comprehensive token management, authentication flow, and debugging tools)*
- [x] **[TEST-UNIT-23]** Write unit tests for test case API operations *(Implemented comprehensive tests for CRUD operations, batch operations, attachments, and link management for test cases)*
- [x] **[QTEST-3]** Implement qTest test case operations with custom field support *(Implemented full support for test case CRUD operations, custom fields, and relationship management)*
- [x] **[TEST-UNIT-24]** Write unit tests for test cycle API operations *(Implemented comprehensive tests for test cycle CRUD operations, nested cycles, and test run management)*
- [x] **[QTEST-4]** Implement qTest test cycle operations with hierarchical structure *(Implemented CRUD operations with support for hierarchical structure and test case assignment)*
- [x] **[TEST-UNIT-25]** Write unit tests for attachment uploads *(Implemented comprehensive tests for uploading and downloading attachments, including custom MIME type handling, error cases, and checksum verification)*
- [x] **[QTEST-5]** Add support for qTest attachment uploads and binary content handling *(Implemented comprehensive attachment handling with MIME type detection, checksums, progress tracking, parallel uploads, and binary data support)*
- [x] **[TEST-UNIT-26]** Write unit tests for pagination *(Created comprehensive tests for pagination functionality including iterators, processors, parallel handling, and convenience functions)*
- [x] **[QTEST-6]** Create qTest pagination utilities for large dataset handling *(Implemented comprehensive pagination utilities with batch processing, parallel execution, and progress tracking)*

#### Integration Tests
- [x] **[TEST-INT-13]** Write integration tests for retry mechanisms
- [x] **[QTEST-7]** Implement automatic retry mechanisms for qTest API failures
- [x] **[TEST-INT-14]** Write integration tests for qTest client error handling
- [x] **[QTEST-8]** Add comprehensive logging for qTest operations with correlation IDs

### Phase 7: Loading Service

#### Unit Tests
- [x] **[TEST-UNIT-27]** Write unit tests for qTest API client
- [x] **[LOAD-1]** Create qTest API client with comprehensive error handling
- [x] **[TEST-UNIT-28]** Write unit tests for test case import *(Implemented comprehensive test suite for QTestCaseImporter with conflict resolution strategies, validation, and attachment handling)*
- [x] **[LOAD-2]** Implement test case import with conflict resolution *(Created QTestCaseImporter with multiple conflict resolution strategies, parallel processing, validation, and detailed statistics tracking)*
- [x] **[TEST-UNIT-29]** Write unit tests for test cycle import *(Implemented test suite for QTestCycleImporter with nested cycles, test case association, and conflict resolution)*
- [x] **[LOAD-3]** Implement test cycle import with dependency checks *(Created QTestCycleImporter with hierarchical structure support, test case association, and conflict resolution)*
- [x] **[TEST-UNIT-30]** Write unit tests for test execution import *(Implemented comprehensive tests for QTestExecutionImporter with test run creation, test log creation, and attachment handling)*
- [x] **[LOAD-4]** Implement test execution import with relationship validation *(Created QTestExecutionImporter with support for test run and test log creation, validation, and parallel processing)*
- [x] **[TEST-UNIT-31]** Write unit tests for attachment upload *(Implemented comprehensive tests for uploading and downloading attachments with MIME type detection, checksums, and parallel processing)*
- [x] **[LOAD-5]** Implement attachment upload module with integrity verification *(Implemented robust attachment upload module with checksum verification, parallel uploads, and retry mechanisms)*

#### Integration Tests
- [x] **[TEST-INT-15]** Write integration tests for error handling *(Implemented comprehensive tests for QTestExecutionImporter with entity mapping errors, test run creation errors, test log creation errors, attachment upload errors, validation errors, and parallel processing errors)*
- [x] **[LOAD-6]** Add validation and detailed error reporting *(Enhanced QTestExecutionImporter with comprehensive validation, detailed error categorization, warning collection, and metrics tracking)*
- [x] **[TEST-INT-16]** Write integration tests for recovery mechanisms *(Created tests for checkpoint creation, resumption from checkpoints, partial batch failures, and network recovery)*
- [x] **[LOAD-7]** Implement recovery mechanisms for failed operations *(Implemented checkpointing, resume-from-checkpoint, and batch recovery capabilities for robust error recovery)*
- [x] **[TEST-INT-17]** Write integration tests for concurrent loading *(Implemented comprehensive tests for parallel processing, batch size optimization, and error resilience during concurrent operations)*
- [x] **[LOAD-8]** Implement parallel loading with ThreadPoolExecutor/ProcessPoolExecutor *(Enhanced QTestExecutionImporter with optimized parallel processing, batching, rate limiting, and comprehensive performance metrics)*

#### Acceptance Tests
- [x] **[TEST-E2E-4]** Write acceptance tests for the loading CLI command *(Implemented comprehensive tests for test execution loading CLI with full test coverage of configuration options and error handling)*
- [x] **[LOAD-9]** Integrate loading into CLI with progress tracking *(Added loading command to workflow_cli with rich progress bars, performance metrics, checkpoint/recovery capabilities, and detailed reporting)*

### Phase 8: Migration Workflow

#### Unit Tests
- [x] **[TEST-UNIT-32]** Write unit tests for validation checkpoints
- [x] **[FLOW-1]** Design migration workflow with validation checkpoints
- [x] **[TEST-UNIT-33]** Write unit tests for incremental migration
- [x] **[FLOW-2]** Implement incremental migration support with resume capability
- [x] **[TEST-UNIT-34]** Write unit tests for migration state tracking
- [x] **[FLOW-3]** Create migration state tracking with database persistence

#### Integration Tests
- [x] **[TEST-INT-18]** Write integration tests for migration reports
- [x] **[TEST-INT-19]** Write integration tests for validation checks
- [x] **[FLOW-5]** Implement post-migration validation checks
- [x] **[TEST-INT-20]** Write integration tests for rollback capability
- [x] **[FLOW-6]** Add rollback capability for failed migrations

#### Acceptance Tests
- [x] **[TEST-E2E-5]** Write acceptance tests for the migrate CLI command *(Implemented comprehensive tests for migrate CLI command with test coverage for various phases, configurations, and error scenarios)*
- [x] **[FLOW-7]** Implement the full ETL pipeline in the migrate command *(Implemented complete ETL pipeline with all phases integrated, including validation, rollback, incremental migration, and detailed reporting)*

### Phase 9: Performance Optimization

#### Unit Tests
- [x] **[TEST-UNIT-35]** Create unit tests for parallel processing *(Implemented comprehensive tests for WorkQueue including priority scheduling, dependency resolution, error handling, and retry mechanisms)*
- [x] **[PERF-1]** Optimize parallel processing with asyncio and work queues *(Created a robust WorkQueue implementation with priority scheduling, dependency management, and support for thread/process/asyncio workers)*
- [x] **[TEST-UNIT-36]** Create unit tests for batching strategies *(Implemented comprehensive tests for various batching strategies including size-based, time-based, adaptive, entity-type, and similarity-based batching)*
- [x] **[PERF-2]** Implement intelligent batching strategies *(Created a modular batching strategy system with size-based, time-based, adaptive, entity-type, and similarity-based batching, integrated with ETL pipeline for optimal performance)*

#### Integration Tests
- [x] **[TEST-INT-21]** Create integration tests for resume capability *(Implemented comprehensive tests for checkpoint and resume capability, including file and database storage backends)*
- [x] **[PERF-3]** Add resume capability with checkpointing *(Implemented a modular checkpoint system with file and database storage, automated checkpointing, and seamless workflow resumption)*
- [x] **[TEST-INT-22]** Create integration tests for database access patterns *(Implemented comprehensive tests for various database access patterns including indexed queries, batch loading, bulk operations, pandas integration, and prepared statements for optimized database performance)*
- [x] **[PERF-4]** Optimize database access patterns *(Implemented comprehensive database optimization system with query caching, keyset pagination, batch operations, performance monitoring, and optimized transaction management; integrated with database factory for easy adoption; see [Database Optimization](https://github.com/heymumford/ztoq/blob/main/docs/database-optimization.md) for detailed documentation)*
- [x] **[TEST-INT-23]** Create integration tests for connection pooling *(Implemented comprehensive tests for connection reuse, pool size limits, concurrent requests, cleanup mechanisms, error handling, and metrics tracking)*
- [x] **[PERF-5]** Implement connection pooling for API clients *(Created a robust connection pooling system with dedicated pool management per host, automatic retry handling, connection reuse, and proper cleanup; integrated with both Zephyr and qTest clients for optimal performance with high-volume API requests)*

#### Performance Tests
- [x] **[TEST-PERF-3]** Create performance test suite *(Implemented comprehensive performance testing framework with base test infrastructure, database tests, and API client tests, including metrics collection, visualization, and statistical analysis)*
- [x] **[TEST-PERF-4]** Benchmark migration throughput *(Implemented comprehensive migration throughput benchmarking with multiple test configurations, phase-specific performance analysis, optimal configuration reporting, and advanced profiling capabilities with cProfile integration)*
- [x] **[TEST-PERF-5]** Profile and optimize critical paths *(Created a CriticalPathOptimizer that analyzes profiling data to identify bottlenecks, generates specific optimization recommendations, and visualizes hotspots with comprehensive reporting)*
- [x] **[PERF-6]** Implement SQL database indexing for performance
- [x] **[PERF-7]** Optimize data transformation with numpy/pandas
- [ ] **[TEST-PERF-6]** Implement large-scale load testing framework for 500,000 records
- [ ] **[PERF-16]** Develop configurable API rate limiting for Zephyr and qTest endpoints
- [ ] **[TEST-PERF-7]** Benchmark performance metrics for large-scale migrations (records/min)

### Phase 13: Snowflake Integration (Future)

#### Unit Tests
- [x] **[TEST-UNIT-37]** Write unit tests for Snowflake connection
- [ ] **[SNOW-1]** Implement Snowflake connection management
- [ ] **[TEST-UNIT-38]** Write unit tests for SQL to Snowflake schema mapping
- [ ] **[SNOW-2]** Create SQL to Snowflake schema mapping
- [ ] **[SNOW-5]** Analyze canonical schema for Snowflake compatibility and refactoring opportunities

#### Integration Tests
- [ ] **[TEST-INT-24]** Write integration tests for data export
- [ ] **[SNOW-3]** Implement data export to Snowflake
- [ ] **[TEST-INT-25]** Write integration tests for incremental sync
- [ ] **[SNOW-4]** Implement incremental sync to Snowflake

### Phase 11: Documentation and Deployment

- [ ] **[DOC-12]** Create database configuration documentation
- [ ] **[DOC-13]** Create scheduled migrations documentation
- [ ] **[DEPLOY-1]** Create Docker setup for containerized deployment
- [ ] **[DEPLOY-2]** Add CI/CD pipelines for automated testing
- [ ] **[DEPLOY-3]** Create production deployment procedures

### Phase 12: Antifragile and Chaos Engineering

#### Chaos Testing
- [ ] **[ANTIFRAGILE-1]** Set up Chaos Toolkit for testing infrastructure
- [ ] **[ANTIFRAGILE-2]** Implement network failure simulation tests
- [ ] **[ANTIFRAGILE-3]** Implement API rate limiting and error simulation
- [ ] **[ANTIFRAGILE-4]** Create database failure and corruption tests

#### Silent Evidence Gathering
- [ ] **[ANTIFRAGILE-5]** Enhance structured logging for silent evidence capture
- [ ] **[ANTIFRAGILE-6]** Implement log aggregation and analysis framework
- [ ] **[ANTIFRAGILE-7]** Create silent evidence dashboard for regular reviews

#### Optionality Implementation
- [ ] **[ANTIFRAGILE-8]** Implement storage format switching utilities
- [ ] **[ANTIFRAGILE-9]** Create fallback mechanisms for critical operations
- [ ] **[ANTIFRAGILE-10]** Design multi-path execution strategies for high-value operations

#### Via Negativa (Simplification)
- [ ] **[ANTIFRAGILE-11]** Implement code complexity metrics tracking
- [ ] **[ANTIFRAGILE-12]** Create regular codebase simplification workflow
- [ ] **[ANTIFRAGILE-13]** Document barbell strategy for feature development

## In Progress

## Review

## Completed
- [x] **[DOC-1]** Create comprehensive README with setup instructions *(Enhanced README with detailed installation steps, feature overview, test coverage information, and usage examples)*
- [x] **[DOC-2]** Document error handling strategies and debug procedures *(Created comprehensive troubleshooting guide with detailed error handling and debugging procedures)*
- [x] **[DOC-3]** Generate API documentation for maintenance *(Generated comprehensive API documentation with Sphinx autodoc)*
- [x] **[DOC-4]** Create database schema documentation (canonical-schema.md)
- [x] **[DOC-5]** Document SQL schema to Snowflake mapping
- [x] **[DOC-6]** Document troubleshooting procedures for production issues *(Created detailed troubleshooting guide with common issues and their solutions)*
- [x] **[DOC-7]** Add CLI command reference with examples *(Created comprehensive CLI command reference with all commands, options, and examples)*
- [x] **[DOC-8]** Create getting started guide for new users *(Created beginner-friendly guide with quick installation and first migration walkthrough)*
- [x] **[DOC-9]** Create detailed usage guide *(Enhanced usage documentation with comprehensive information on all features)*
- [x] **[DOC-10]** Create migration workflow guide *(Created detailed guide covering the complete migration process)*
- [x] **[DOC-11]** Improve Sphinx documentation structure *(Reorganized Sphinx documentation with a more intuitive structure and better navigation)*
- [x] **[TEST-E2E-1]** Write acceptance tests for CLI commands *(Implemented comprehensive acceptance tests for both the main CLI commands and workflow CLI commands, including thorough test fixtures and mock configurations)*
- [x] **[TEST-UNIT-37]** Write unit tests for Snowflake connection *(Created comprehensive test suite for Snowflake database connection functionality following test-driven development principles to guide future implementation)*
- [x] **[PERF-7]** Optimize data transformation with numpy/pandas *(Implemented comprehensive data transformation optimizations using pandas and numpy to significantly improve throughput and memory efficiency across the ETL pipeline)*
- [x] **[PERF-6]** Implement SQL database indexing for performance *(Implemented a comprehensive database indexing system with index recommendation, creation, validation, and performance analysis capabilities for both SQLite and PostgreSQL databases)*
- [x] **[TEST-PERF-5]** Profile and optimize critical paths *(Created a CriticalPathOptimizer that analyzes profiling data to identify bottlenecks, generates specific optimization recommendations, and visualizes hotspots with comprehensive reporting)*
- [x] **[TEST-PERF-4]** Benchmark migration throughput *(Implemented comprehensive migration throughput benchmarking with multiple test configurations, phase-specific performance analysis, optimal configuration reporting, and advanced profiling capabilities with cProfile integration)*
- [x] **[TEST-PERF-3]** Create performance test suite *(Implemented comprehensive performance testing framework with base test infrastructure, database tests, and API client tests, including metrics collection, visualization, and statistical analysis)*
- [x] **[TEST-INT-22]** Create integration tests for database access patterns *(Implemented comprehensive tests for various database access patterns including indexed queries, batch loading, bulk operations, pandas integration, and prepared statements for optimized database performance)*
- [x] **[TEST-INT-21]** Create integration tests for resume capability *(Implemented comprehensive tests for checkpoint and resume capability, including file and database storage backends)*
- [x] **[PERF-3]** Add resume capability with checkpointing *(Implemented a modular checkpoint system with file and database storage, automated checkpointing, and seamless workflow resumption)*
- [x] **[TEST-UNIT-36]** Create unit tests for batching strategies *(Implemented comprehensive tests for various batching strategies including size-based, time-based, adaptive, entity-type, and similarity-based batching)*
- [x] **[PERF-2]** Implement intelligent batching strategies *(Created a modular batching strategy system with size-based, time-based, adaptive, entity-type, and similarity-based batching, integrated with ETL pipeline for optimal performance)*
- [x] **[TEST-UNIT-35]** Create unit tests for parallel processing *(Implemented comprehensive tests for WorkQueue including priority scheduling, dependency resolution, error handling, and retry mechanisms)*
- [x] **[PERF-1]** Optimize parallel processing with asyncio and work queues *(Created a robust WorkQueue implementation with priority scheduling, dependency management, and support for thread/process/asyncio workers)*
- [x] **[TEST-E2E-5]** Write acceptance tests for the migrate CLI command *(Implemented comprehensive tests for migrate CLI command with test coverage for various phases, configurations, and error scenarios)*
- [x] **[FLOW-7]** Implement the full ETL pipeline in the migrate command *(Implemented complete ETL pipeline with all phases integrated, including validation, rollback, incremental migration, and detailed reporting)*
- [x] **[TEST-INT-19]** Write integration tests for validation checks *(Implemented comprehensive tests for validation reporting, different severity levels, and database functionality)*
- [x] **[FLOW-5]** Implement post-migration validation checks *(Created robust validation system with content validation, performance metrics, and actionable recommendations)*
- [x] **[TEST-INT-20]** Write integration tests for rollback capability *(Implemented tests for various rollback scenarios, error cases, and verification of cleanup)*
- [x] **[FLOW-6]** Add rollback capability for failed migrations *(Added complete rollback functionality with qTest entity cleanup, database cleanup, and configurable behavior)*
- [x] **[TEST-UNIT-3]** Write unit tests for Zephyr API client *(Enhanced existing tests with comprehensive coverage of retry logic, circuit breaker pattern, and error handling)*
- [x] **[EXTRACT-1]** Create Zephyr API client with robust error handling and retry logic *(Improved existing client with circuit breaker pattern, enhanced logging, and metrics tracking)*
- [x] **[TEST-INT-14]** Write integration tests for qTest client error handling *(Implemented comprehensive tests for various error scenarios, edge cases, and retry behaviors)*
- [x] **[QTEST-8]** Add comprehensive logging for qTest operations with correlation IDs *(Implemented complete correlation ID tracking system with context propagation, metrics collection, and enhanced logging)*
- [x] **[TEST-INT-18]** Write integration tests for migration reports
- [x] **[TEST-INT-16]** Write integration tests for recovery mechanisms *(Created tests for checkpoint creation, resumption from checkpoints, partial batch failures, and network recovery)*
- [x] **[LOAD-7]** Implement recovery mechanisms for failed operations *(Implemented checkpointing, resume-from-checkpoint, and batch recovery capabilities for robust error recovery)*
- [x] **[TEST-INT-15]** Write integration tests for error handling *(Implemented comprehensive tests for QTestExecutionImporter with entity mapping errors, test run creation errors, test log creation errors, attachment upload errors, validation errors, and parallel processing errors)*
- [x] **[LOAD-6]** Add validation and detailed error reporting *(Enhanced QTestExecutionImporter with comprehensive validation, detailed error categorization, warning collection, and metrics tracking)*
- [x] **[QTEST-7]** Implement automatic retry mechanisms for qTest API failures *(Implemented comprehensive retry mechanism with QTestRetryPolicy, with_retry decorator, and QTestCircuitBreaker for enhanced API reliability)*
- [x] **[TEST-INT-13]** Write integration tests for retry mechanisms *(Implemented tests for both client-specific retry mechanisms and circuit breaker patterns)*
- [x] **[QTEST-6]** Create qTest pagination utilities for large dataset handling *(Implemented comprehensive pagination utilities with batch processing, parallel execution, and progress tracking)*
- [x] **[TEST-UNIT-25]** Write unit tests for attachment uploads *(Implemented comprehensive tests for uploading and downloading attachments, including custom MIME type handling, error cases, and checksum verification)*
- [x] **[TEST-UNIT-24]** Write unit tests for test cycle API operations *(Implemented comprehensive tests for test cycle CRUD operations, nested cycles, and test run management)*
- [x] **[QTEST-4]** Implement qTest test cycle operations with hierarchical structure *(Implemented CRUD operations with support for hierarchical structure and test case assignment)*
- [x] **[TEST-UNIT-23]** Write unit tests for test case API operations *(Implemented comprehensive tests for CRUD operations, batch operations, attachments, and link management for test cases)*
- [x] **[QTEST-3]** Implement qTest test case operations with custom field support *(Implemented full support for test case CRUD operations, attachments, and link management)*
- [x] **[TRANSFORM-9]** Integrate transformation into CLI with validation reporting *(Implemented dedicated transform command with validation reporting in workflow_cli.py, including detailed statistics and color-coded validation issue reporting by severity level)*
- [x] **[TEST-E2E-3]** Write acceptance tests for the transformation CLI command *(Implemented comprehensive tests for batch transformation CLI commands, including options to enable/disable the batch transformer and configure batch size)*
- [x] **[TRANSFORM-8]** Implement batch transformation process *(Integrated SQL-based batch transformer with workflow orchestrator for efficient processing of large datasets)*
- [x] **[TEST-INT-10]** Write integration tests for relationship resolution
- [x] **[TRANSFORM-6]** Create data quality validation layer
- [x] **[TEST-INT-11]** Write integration tests for transformation flow
- [x] **[TRANSFORM-7]** Implement SQL-based transformation with pandas
- [x] **[TEST-INT-12]** Write integration tests for batch transformations
- [x] **[TEST-INFRA-1]** Setup test pyramid structure (unit, integration, acceptance)
- [x] **[TEST-INFRA-2]** Create base test fixtures and factories
- [x] **[TEST-INFRA-3]** Implement test harness for API mocking
- [x] **[TEST-UNIT-17]** Write unit tests for test case transformer
- [x] **[TRANSFORM-2]** Implement test case transformer with error boundaries
- [x] **[TEST-UNIT-18]** Write unit tests for test cycle transformer
- [x] **[TRANSFORM-3]** Implement test cycle transformer with validation
- [x] **[TEST-UNIT-19]** Write unit tests for test execution transformer
- [x] **[TRANSFORM-4]** Implement test execution transformer with data normalization
- [x] **[TEST-UNIT-22]** Write unit tests for qTest authentication
- [x] **[QTEST-2]** Implement qTest authentication and token management *(Added comprehensive token management with bearer token and username/password authentication, automatic token refresh, rate limit handling, and debugging tools)*
- [x] **[TEST-UNIT-3]** Write unit tests for Zephyr API client *(Added comprehensive tests for retry logic, circuit breaker, and error handling)*
- [x] **[EXTRACT-1]** Create Zephyr API client with robust error handling and retry logic *(Implemented retry decorator with exponential backoff, circuit breaker pattern, and comprehensive error handling)*
- [x] **[TEST-UNIT-12]** Define unit tests for Zephyr mock factories *(Implemented comprehensive tests for all factory classes)*
- [x] **[MOCK-1]** Create mock factory for Zephyr API responses *(Implemented factory classes for all Zephyr entities with specialized creation methods)*
- [x] **[TEST-UNIT-13]** Write unit tests for Zephyr mock server endpoints *(Added tests for all server functionality including authentication and API endpoints)*
- [x] **[MOCK-2]** Build mock server for Zephyr API endpoints *(Implemented a complete mock server with endpoint routing, validation, and error handling)*
- [x] **[TEST-INT-8]** Write integration tests for mock server performance *(Created performance tests for response times, concurrent requests, and configurable delays)*
- [x] **[TEST-INT-9]** Verify mock server API compatibility with real endpoints *(Implemented tests to verify API structure, response formats, pagination, filtering, and error handling match real APIs)*
- [x] **[TEST-UNIT-15]** Write unit tests for qTest mock server endpoints
- [x] **[MOCK-4]** Build mock server for qTest API endpoints *(All endpoints implemented with proper routing and validation)*
- [x] **[QTEST-1]** Finalize Pydantic models for qTest entities *(Added Scenario models and enhanced validation for all existing models)*
- [x] **[TEST-UNIT-27]** Write unit tests for qTest API client *(Added comprehensive test scenarios for error handling)*
- [x] **[LOAD-1]** Create qTest API client with comprehensive error handling *(Implemented with robust error handling for all API operations)*
- [x] **[TEST-UNIT-21]** Write unit tests for qTest entity models
- [x] **[TEST-UNIT-14]** Define unit tests for qTest mock factories
- [x] **[MOCK-3]** Create mock factory for qTest API responses
- [x] **[TEST-UNIT-4]** Write unit tests for test case extraction
- [x] **[EXTRACT-2]** Implement test case extraction with comprehensive error handling
- [x] **[TEST-UNIT-5]** Write unit tests for test cycle extraction
- [x] **[EXTRACT-3]** Implement test cycle extraction with validation
- [x] **[TEST-UNIT-6]** Write unit tests for test execution extraction
- [x] **[EXTRACT-4]** Implement test execution extraction with data integrity checks
- [x] **[TEST-UNIT-7]** Write unit tests for attachment downloading
- [x] **[EXTRACT-5]** Implement attachment download module with checksums
- [x] **[TEST-INT-2]** Write integration tests for extraction flow
- [x] **[EXTRACT-6]** Add pagination and adaptive rate limiting
- [x] **[TEST-INT-3]** Write integration tests for error handling across extraction flow
- [x] **[EXTRACT-7]** Implement detailed logging with contextual information
- [x] **[DB-1]** Define SQL models and schemas with SQLAlchemy
- [x] **[DB-2]** Implement connection pooling and management
- [x] **[DB-3]** Implement transaction management with proper error handling
- [x] **[DB-4]** Implement entity CRUD operations with validation
- [x] **[DB-5]** Implement database migration system with Alembic
- [x] **[DB-6]** Implement concurrent database operations with proper locking
- [x] **[DB-7]** Implement database error handling and recovery procedures
- [x] **[DB-8]** Optimize database queries and indexes
- [x] **[FLOW-1]** Design migration workflow with validation checkpoints
- [x] **[FLOW-3]** Create migration state tracking with database persistence
- [x] **[DOC-4]** Create database schema documentation (canonical-schema.md)

## Test Pyramid Strategy

Our testing approach follows the Test Pyramid model, ensuring appropriate test coverage at all levels:

```
    /\
   /  \
  /    \
 / E2E  \       Fewer acceptance tests (End-to-end)
/--------\
/          \
/ Integration \   More integration tests
/--------------\
/                \
/     Unit        \  Many unit tests
/------------------\
```

### 1. Unit Tests (Base Layer)
- Focus on testing individual components in isolation
- Mock all dependencies
- Aim for high coverage (80%+)
- Fast execution
- Test both success and failure paths
- Follow TDD approach - tests written before implementation

### 2. Integration Tests (Middle Layer)
- Test interactions between components
- Use mock APIs for external services
- Focus on communication boundaries
- Verify error handling across components
- Test data flows and transformations
- SQL database interactions and validation

### 3. Acceptance Tests (Top Layer)
- Test complete workflows
- CLI command execution
- Focus on user-facing functionality
- Verify business requirements
- Use realistic but controlled test data
- End-to-end ETL process validation

### 4. Performance Tests (Specialized)
- Benchmark key operations
- Measure throughput and scalability
- Test with large datasets
- Identify bottlenecks
- SQL database performance optimization
- Parallel processing evaluation

## TDD Implementation Process

For each task in the above Kanban board, we will follow this TDD (Test-Driven Development) process:

1. **Write Tests First**:
   - Define expected behavior and outcomes
   - Create test fixtures with sample data
   - Implement test cases covering both positive and negative scenarios
   - Ensure tests initially fail (Red)

2. **Implement Functionality**:
   - Create minimal implementation to pass tests
   - Focus on correctness over optimization initially
   - Ensure all tests pass (Green)

3. **Refactor Code**:
   - Improve implementation while maintaining test coverage
   - Optimize for performance and readability
   - Extract common functionality into reusable components

4. **Extend Test Coverage**:
   - Add edge cases and error conditions
   - Implement integration tests with other components
   - Verify interfaces and contracts between components

5. **Document and Review**:
   - Add documentation for usage and maintenance
   - Review code with peers
   - Finalize implementation

## Canonical SQL Database Schema

Our SQL database strategy follows a canonical schema approach to ensure compatibility with both Zephyr and qTest systems, as well as future migration to Snowflake:

### Database Schema
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

### Optimization Techniques
- **Indexing**: Implement specific indexes for all foreign keys and commonly queried fields
- **Connection Pooling**: Configure SQLAlchemy connection pools with optimal size and timeout settings
- **Transaction Management**: Use explicit transactions with proper isolation levels
- **Batch Processing**: Implement qTest bulk APIs (like `/auto-test-logs`) for high-throughput uploads
- **Parallel Processing**: Use asyncio/aiohttp for extraction and concurrent.futures for transformation/loading
- **Type-Safe ORM**: SQLAlchemy models with proper relationships and constraints
- **Custom Field Strategy**: Use simplified key-value approach for flexible custom field handling
- **Attachment Handling**: Efficient binary blob handling with parallel uploads
- **Snowflake Compatibility**: Schema designed for future Snowflake warehouse migration

## Migration Plan Timeline

### Weeks 1-2: Infrastructure and Extraction
- Set up project structure, CLI framework, and database
- Implement and test Zephyr API client
- Complete test case, cycle, and execution extraction

### Weeks 3-4: SQL Database and Mock Services
- Implement SQL database schema and migrations
- Build and test mock servers for both APIs
- Implement concurrent data extraction with async

### Weeks 5-6: Transformation Service
- Complete entity mapping definitions
- Implement SQL-based transformation with pandas
- Implement and test validation services

### Weeks 7-8: qTest Integration and Loading
- Finalize qTest models and API client
- Implement entity creation and relationship handling
- Complete attachment upload functionality
- Implement parallel loading

### Weeks 9-10: Workflow and Optimization
- Implement complete migration workflow
- Add state tracking and resume capability
- Optimize performance for large datasets
- Implement transaction management and rollback

### Weeks 11-12: Finalization and Documentation
- Complete validation and reporting
- Add comprehensive documentation
- Prepare deployment procedures
- Set up Snowflake migration path

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| API rate limits | Migration slowdown | Implement adaptive rate limiting and batching |
| Data inconsistencies | Failed mappings | Add validation layers with clear error reporting |
| Large attachment volumes | Storage and bandwidth issues | Implement chunked uploads with checksums |
| Custom field mismatches | Data loss or corruption | Create custom field mapping with type conversion |
| Migration interruptions | Incomplete transfers | Implement checkpointing and resume capability |
| Performance bottlenecks | Extended migration time | Add parallel processing and optimize database access |
| Database locking | Concurrent operation failures | Implement proper transaction isolation levels with PostgreSQL |
| SQLite concurrency limits | Data corruption | Prioritize PostgreSQL for production, use SQLite only for development |
| Database scaling challenges | Migration failures | Configure PostgreSQL connection pooling and optimize for large datasets |

## Notes
- All components must include comprehensive test coverage at appropriate pyramid levels
- Follow the TDD process (Red-Green-Refactor) for all implementations
- Debug mode should provide verbose output for troubleshooting
- Each API client must have corresponding mock implementations
- Database should support transaction rollback for test isolation
- Implement proper connection pooling for database and API connections
- Include validation at all stages of the ETL process
- Logging should capture sufficient context for production troubleshooting
- All errors should be gracefully handled with clear user feedback
- SQL database provides future path to Snowflake migration

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](https://github.com/heymumford/ztoq/blob/main/LICENSE)*
