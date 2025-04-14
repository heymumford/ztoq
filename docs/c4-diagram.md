# C4 Model Diagrams for ZTOQ

## Level 1: System Context Diagram

```
┌───────────────────────────────┐      ┌──────────────────────────┐
│                               │      │                          │
│                               │      │                          │
│       Tester / QA Team        │      │  Zephyr Scale API        │
│                               │      │  (in Jira)               │
│                               │      │                          │
└───────────────┬───────────────┘      └──────────┬───────────────┘
                │                                  │
                │                                  │
                │ uses                             │ extracts test data from
                │                                  │
                ▼                                  │
┌───────────────────────────────┐                 │
│                               │◄────────────────┘
│         ZTOQ                  │                 
│    (Zephyr to qTest)          │                 
│    CLI Application            │                 
│                               │                 
└───────────────┬───────────────┘                 
                │                                 
                │ migrates to                      
                │                                  
                ▼                                  
┌───────────────────────────────┐      ┌──────────────────────────┐
│                               │      │                          │
│   SQLite Database             │      │  qTest APIs              │
│   (Intermediate Storage       │      │  (Manager, Parameters,   │
│    & Migration State)         │      │   Pulse, Scenario)       │
│                               │      │                          │
└───────────────────────────────┘      └──────────────────────────┘
                                                   ▲
                                                   │
                                                   │ loads test data to
                                                   │
                                                   │
                                                   └───────────────
```

## Level 2: Container Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ ZTOQ Application                                                                     │
│                                                                                     │
│ ┌─────────────────────┐  ┌────────────────────┐  ┌────────────────────┐             │
│ │                     │  │                    │  │                    │             │
│ │ CLI Module          │  │ OpenAPI Parser     │  │ Zephyr Client      │             │
│ │ (Typer)             │◄─┼─►(Parses/validates │  │ (API interaction   │             │
│ │                     │  │  z-openapi.yml)    │  │  with pagination)  │             │
│ └──────────┬──────────┘  └────────────────────┘  └────────┬───────────┘             │
│            │                                              │                         │
│            ▼                                              ▼                         │
│ ┌─────────────────────┐                       ┌────────────────────────┐            │
│ │                     │                       │                        │            │
│ │ Exporter Module     │◄──────────────────────┤ Data Fetcher Module    │            │
│ │ (Orchestrates data  │                       │ (Handles parallel      │            │
│ │  extraction)        │                       │  data retrieval)       │            │
│ └──────────┬──────────┘                       └────────────────────────┘            │
│            │                                                                        │
│            ▼                                                                        │
│ ┌─────────────────────┐                       ┌────────────────────────┐            │
│ │                     │                       │                        │            │
│ │ Storage Module      │◄──────────────────────┤ Database Manager       │            │
│ │ (SQLite             │                       │ (Handles SQL operations │            │
│ │  implementation)    │                       │  and relationships)    │            │
│ └─────────┬───────────┘                       └────────────────────────┘            │
│           │                                                                         │
│           │                                                                         │
│           ▼                                                                         │
│ ┌─────────────────────┐                       ┌────────────────────────┐            │
│ │                     │                       │                        │            │
│ │ Transform Module    │◄──────────────────────┤ qTest Client Module    │            │
│ │ (Converts Zephyr to │                       │ (Unified client for    │            │
│ │  qTest format)      │                       │  all qTest APIs)       │            │
│ └─────────┬───────────┘                       └────────┬───────────────┘            │
│           │                                            │                            │
│           └────────────────────────────────────────────┘                            │
│                           │                                                         │
│                           ▼                                                         │
│ ┌─────────────────────┐  ┌────────────────────┐  ┌────────────────────┐             │
│ │                     │  │                    │  │                    │             │
│ │ ETL Orchestrator    │  │ Migration State    │  │ Reporting Module   │             │
│ │ (Coordinates the    │  │ (Tracks progress   │  │ (Generates migration│             │
│ │  migration workflow)│  │  and enables resume)  │  reports and logs)  │             │
│ └─────────────────────┘  └────────────────────┘  └────────────────────┘             │
│                                                                                     │
│ ┌───────────────────────┐  ┌─────────────────────┐  ┌────────────────────────┐     │
│ │                       │  │                     │  │                        │     │
│ │ Error Handling        │  │ Logging System      │  │ Testing & Mocking      │     │
│ │ (Domain exceptions &  │  │ (Structured logging │  │ (Mock servers for      │     │
│ │  Result objects)      │  │  with context)      │  │  API testing)          │     │
│ └───────────────────────┘  └─────────────────────┘  └────────────────────────┘     │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Level 3: Component Diagram

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ZTOQ Components                                                                                            │
│                                                                                                           │
│ ┌─────────────────────┐   ┌────────────────────┐   ┌────────────────────┐   ┌─────────────────────────┐   │
│ │                     │   │                    │   │                    │   │                         │   │
│ │ cli.py              │   │ openapi_parser.py  │   │ models.py          │   │ zephyr_client.py       │   │
│ │ - validate()        │   │ - load_spec()      │   │ - ZephyrConfig     │   │ - ZephyrClient         │   │
│ │ - list_endpoints()  │◄─►│ - validate_spec()  │◄─►│ - TestCase         │◄─►│ - PaginatedIterator    │   │
│ │ - get_test_cases()  │   │ - extract_endpoints│   │ - TestCycleInfo    │   │ - rate limiting        │   │
│ │ - export_project()  │   └────────────────────┘   │ - TestExecution    │   │ - handle pagination    │   │
│ │ - migrate_to_qtest()│                            └────────────────────┘   └─────────────┬───────────┘   │
│ └──────────┬──────────┘                                                                  │               │
│            │                                                                              │               │
│            └─────────────────────────┬─────────────────────────────────────┬─────────────┘               │
│                                      │                                     │                               │
│                                      ▼                                     ▼                               │
│                          ┌────────────────────────┐            ┌───────────────────────────┐              │
│                          │ exporter.py            │            │ data_fetcher.py           │              │
│                          │ - ZephyrExporter       │◄───────────┤ - FetchResult             │              │
│                          │ - ZephyrExportManager  │            │ - fetch_all_project_data  │              │
│                          │ - export data          │            │ - fetch_all_projects_data │              │
│                          │ - parallel processing  │            │ - parallel processing     │              │
│                          └───────────┬────────────┘            └───────────────────────────┘              │
│                                      │                                                                     │
│                                      ▼                                                                     │
│             ┌─────────────────────────────────────────────┐      ┌─────────────────────────────────┐      │
│             │                                             │      │                                 │      │
│             │ storage.py                                  │      │ database_manager.py             │      │
│             │ - SQLiteStorage                             │◄─────┤ - DatabaseManager              │      │
│             │ - save test data                            │      │ - get_connection               │      │
│             │ - context manager for resources             │      │ - initialize_database          │      │
│             └───────────────────┬─────────────────────────┘      │ - save_project_data            │      │
│                                 │                                 └─────────────────────────────────┘      │
│                                 ▼                                                                          │
│             ┌─────────────────────────────────────────────┐      ┌─────────────────────────────────┐      │
│             │                                             │      │                                 │      │
│             │ transform.py                                │      │ entity_mapping.py               │      │
│             │ - ZephyrToQTestTransformer                 │◄─────┤ - field_mappers                │      │
│             │ - transform_test_case()                     │      │ - relationship_resolvers       │      │
│             │ - transform_test_cycle()                    │      │ - custom_field_convertors      │      │
│             └───────────────────┬─────────────────────────┘      └─────────────────────────────────┘      │
│                                 │                                                                          │
│                                 ▼                                                                          │
│             ┌─────────────────────────────────────────────┐      ┌─────────────────────────────────┐      │
│             │                                             │      │                                 │      │
│             │ qtest_client.py                             │      │ qtest_models.py                │      │
│             │ - QTestClient                              │◄─────┤ - QTestConfig                  │      │
│             │ - QTestPaginatedIterator                   │      │ - QTestProject                 │      │
│             │ - API type detection                        │      │ - QTestTestCase                │      │
│             │ - Authentication handling                    │      │ - QTestCustomField             │      │
│             └───────────────────┬─────────────────────────┘      └─────────────────────────────────┘      │
│                                 │                                                                          │
│                                 ▼                                                                          │
│             ┌─────────────────────────────────────────────┐      ┌─────────────────────────────────┐      │
│             │                                             │      │                                 │      │
│             │ migration_orchestrator.py                   │      │ migration_state.py              │      │
│             │ - run_complete_migration()                  │◄─────┤ - MigrationState               │      │
│             │ - run_extraction_phase()                    │      │ - EntityBatchState             │      │
│             │ - run_transformation_phase()                │      │ - save_checkpoint()            │      │
│             │ - run_loading_phase()                       │      │ - resume_from_checkpoint()     │      │
│             └───────────────────┬─────────────────────────┘      └─────────────────────────────────┘      │
│                                 │                                                                          │
│                                 ▼                                                                          │
│             ┌─────────────────────────────────────────────┐      ┌─────────────────────────────────┐      │
│             │                                             │      │                                 │      │
│             │ qtest_mock_server.py                        │      │ reporter.py                     │      │
│             │ - QTestMockServer                          │      │ - MigrationReporter             │      │
│             │ - API simulation                            │      │ - generate_migration_report()   │      │
│             │ - Entity storage                            │      │ - generate_validation_report()  │      │
│             │ - Request handling                          │      │ - create_entity_mapping_report()│      │
│             └─────────────────────────────────────────────┘      └─────────────────────────────────┘      │
│                                                                                                           │
│ ┌─────────────────────────┐   ┌─────────────────────────────┐   ┌─────────────────────────────┐          │
│ │                         │   │                             │   │                             │          │
│ │ error_handling.py       │   │ logging.py                  │   │ documentation               │          │
│ │ - ZTOQError hierarchy   │   │ - StructuredLogger         │   │ - Sphinx configuration      │          │
│ │ - Result class          │   │ - JSONFormatter            │   │ - API autodocs              │          │
│ │ - retry decorator       │   │ - LogRedactor              │   │ - User guides               │          │
│ │ - handle_cli_error      │   │ - log_operation            │   │ - ADRs & C4 diagrams        │          │
│ └─────────────────────────┘   └─────────────────────────────┘   └─────────────────────────────┘          │
│                                                                                                           │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Level 4: Code Diagram (Key Classes)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Class Structure                                                                                         │
│                                                                                                        │
│  ┌────────────────┐    ┌───────────────────┐    ┌───────────────────────┐    ┌─────────────────────┐   │
│  │ZephyrConfig    │    │ZephyrTestCase     │    │ZephyrTestCycle        │    │ZephyrTestExecution  │   │
│  ├────────────────┤    ├───────────────────┤    ├───────────────────────┤    ├─────────────────────┤   │
│  │- base_url      │    │- id               │    │- id                    │    │- id                 │   │
│  │- api_token     │    │- key              │    │- key                   │    │- test_case_key      │   │
│  │- project_key   │    │- name             │    │- name                  │    │- cycle_id           │   │
│  └────────────────┘    │- steps            │    │- status                │    │- status             │   │
│                        │- custom_fields    │    │- custom_fields         │    │- steps              │   │
│                        └───────────────────┘    └───────────────────────┘    └─────────────────────┘   │
│                                                                                                        │
│  ┌────────────────┐    ┌───────────────────┐    ┌───────────────────────┐    ┌─────────────────────┐   │
│  │ZephyrClient    │    │QTestConfig        │    │QTestClient            │    │QTestPaginatedIterator│   │
│  ├────────────────┤    ├───────────────────┤    ├───────────────────────┤    ├─────────────────────┤   │
│  │- config        │    │- base_url         │    │- config               │    │- client             │   │
│  │- headers       │    │- username         │    │- api_type             │    │- endpoint           │   │
│  │- get_projects()│    │- password         │    │- get_projects()       │    │- model_class        │   │
│  │- get_test_cases│    │- project_id       │    │- get_test_cases()     │    │- params             │   │
│  │- get_test_cycle│    └───────────────────┘    │- _authenticate()      │    │- current_page       │   │
│  └────────────────┘                             └───────────────────────┘    └─────────────────────┘   │
│                                                                                                        │
│  ┌────────────────┐    ┌───────────────────┐    ┌───────────────────────┐    ┌─────────────────────┐   │
│  │QTestProject    │    │QTestTestCase      │    │QTestTestCycle         │    │QTestCustomField     │   │
│  ├────────────────┤    ├───────────────────┤    ├───────────────────────┤    ├─────────────────────┤   │
│  │- id            │    │- id               │    │- id                    │    │- field_id           │   │
│  │- name          │    │- name             │    │- name                  │    │- field_name         │   │
│  │- description   │    │- description      │    │- description           │    │- field_type         │   │
│  │- start_date    │    │- test_steps       │    │- parent_id             │    │- field_value        │   │
│  │- end_date      │    │- properties       │    │- release_id            │    └─────────────────────┘   │
│  └────────────────┘    └───────────────────┘    └───────────────────────┘                              │
│                                                                                                        │
│  ┌────────────────┐    ┌───────────────────┐    ┌───────────────────────┐    ┌─────────────────────┐   │
│  │SQLiteStorage   │    │DatabaseManager    │    │Transformer            │    │EntityMapper         │   │
│  ├────────────────┤    ├───────────────────┤    ├───────────────────────┤    ├─────────────────────┤   │
│  │- db_path       │    │- db_path          │    │- field_mapper         │    │- map_test_case      │   │
│  │- conn          │    │- initialize_db()  │    │- transform_test_case()│    │- map_custom_field   │   │
│  │- cursor        │    │- save_zephyr_data()   │- transform_cycle()    │    │- resolve_references │   │
│  │- save_test_case│    │- save_qtest_data()    │- transform_execution()│    │- convert_type       │   │
│  └────────────────┘    └───────────────────┘    └───────────────────────┘    └─────────────────────┘   │
│                                                                                                        │
│  ┌────────────────┐    ┌───────────────────┐    ┌───────────────────────┐    ┌─────────────────────┐   │
│  │QTestMockServer │    │MigrationState     │    │MigrationOrchestrator  │    │MigrationReporter    │   │
│  ├────────────────┤    ├───────────────────┤    ├───────────────────────┤    ├─────────────────────┤   │
│  │- data stores   │    │- status           │    │- zephyr_client        │    │- generate_report    │   │
│  │- handle_request│    │- phase            │    │- qtest_client         │    │- summarize_results  │   │
│  │- _handle_auth  │    │- total_entities   │    │- storage              │    │- create_charts      │   │
│  │- API simulation│    │- processed_entities   │- transformer           │    │- export_to_formats  │   │
│  └────────────────┘    └───────────────────┘    └───────────────────────┘    └─────────────────────┘   │
│                                                                                                        │
│  ┌────────────────┐    ┌───────────────────┐    ┌───────────────────────┐    ┌─────────────────────┐   │
│  │ZTOQError       │    │Result<T>          │    │StructuredLogger       │    │JSONFormatter        │   │
│  ├────────────────┤    ├───────────────────┤    ├───────────────────────┤    ├─────────────────────┤   │
│  │                │    │- success: bool    │    │- _log()               │    │- format()           │   │
│  │  APIError      │    │- value: T         │    │- context              │    │- serialize context  │   │
│  │  StorageError  │    │- error: Exception │    │- debug(), info()      │    │- handle exceptions  │   │
│  │  DataValidation│    │- error_message    │    │- warning(), error()   │    │- format timestamps  │   │
│  │  Error         │    │- warnings: List   │    └───────────────────────┘    └─────────────────────┘   │
│  └────────────────┘    └───────────────────┘                                                           │
│                                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Lucidchart Integration

These diagrams are available as interactive diagrams in Lucidchart. To edit or access the diagrams:

1. Visit [Lucidchart ZTOQ Diagrams](https://lucid.app/lucidchart/shared/123456)
2. Select the desired diagram level
3. Use the export options to save as PNG, SVG, or PDF

For creating new C4 diagrams, use the C4 Model shape library in Lucidchart and follow the style guide in our documentation.

## Build Integration

The C4 diagrams are automatically included in our Sphinx documentation build. After running:

```bash
make docs
```

The diagrams will be available in the Architecture section of the documentation.

## Modeling Architecture Evolution

The C4 diagrams are version-controlled alongside our code to track architectural evolution over time. Key changes are documented in corresponding ADRs:

1. Initial architecture (ADR-001 through ADR-005)
2. Storage extensions (ADR-002, ADR-007)
3. Documentation system (ADR-006)
4. Error handling framework (ADR-009)
5. Logging system (ADR-010)
6. qTest integration (ADR-011)
7. TDD approach (ADR-012)
8. ETL-based migration workflow (ADR-013)

## Architectural Decision Principles

Our architecture follows these key principles, which are reflected in the C4 diagrams:

1. **Separation of Concerns**: Clear boundaries between components
2. **Clean Code**: Following Uncle Bob's principles for code organization
3. **Test-Driven Development**: Testing before implementation
4. **Error Handling**: Consistent approach with Result objects and domain exceptions
5. **Logging**: Structured logging with context for observability
6. **Testability**: Components designed for easy testing
7. **Documentation**: Self-documenting architecture with Sphinx integration
8. **Extensibility**: Modular design that supports adding new features
9. **Data Integrity**: Validation at all stages of data processing
10. **Resumability**: Operations designed to be interruptible and resumable

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](../../LICENSE)*