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
                │ uses                             │ exposes test data
                │                                  │
                ▼                                  │
┌───────────────────────────────┐                 │
│                               │                 │
│         ZTOQ                  │◄────────────────┘
│    (Zephyr Test Object Query) │  queries using 
│    CLI Application            │  OpenAPI spec
│                               │
└───────────────┬───────────────┘
                │
                │ exports to
                │
                ▼
┌───────────────────────────────┐
│                               │
│   JSON Files / SQLite DB      │
│   (Test Cases, Cycles,        │
│    Executions, etc.)          │
│                               │
└───────────────────────────────┘
```

## Level 2: Container Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ZTOQ Application                                                         │
│                                                                         │
│ ┌─────────────────────┐  ┌────────────────────┐ ┌────────────────────┐  │
│ │                     │  │                    │ │                    │  │
│ │ CLI Module          │  │ OpenAPI Parser     │ │ Zephyr Client      │  │
│ │ (Typer)             │◄─┼─►(Parses/validates │ │ (API interaction   │  │
│ │                     │  │  z-openapi.yml)    │ │  with pagination)  │  │
│ └──────────┬──────────┘  └────────────────────┘ └────────┬───────────┘  │
│            │                                             │              │
│            ▼                                             │              │
│ ┌─────────────────────┐                                  │              │
│ │                     │                                  │              │
│ │ Exporter Module     │◄─────────────────────────────────┘              │
│ │ (Orchestrates data  │                                                 │
│ │  extraction)        │                                                 │
│ └──────────┬──────────┘                                                 │
│            │                                                            │
│            ▼                                                            │
│ ┌─────────────────────┐                                                 │
│ │                     │                                                 │
│ │ Storage Module      │                                                 │
│ │ (JSON & SQLite      │                                                 │
│ │  implementations)   │                                                 │
│ └─────────────────────┘                                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
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
│ └──────────┬──────────┘                            └────────────────────┘   └─────────────┬───────────┘   │
│            │                                                                              │               │
│            └─────────────────────────┬─────────────────────────────────────┬─────────────┘               │
│                                      │                                     │                               │
│                                      ▼                                     ▼                               │
│                          ┌────────────────────────┐            ┌───────────────────────────┐              │
│                          │ exporter.py            │            │ storage.py                │              │
│                          │ - ZephyrExporter       │◄───────────┤ - SQLiteStorage           │              │
│                          │ - ZephyrExportManager  │            │ - JSONStorage             │              │
│                          │ - export data          │            │ - save test data          │              │
│                          │ - parallel processing  │            │ - load test data          │              │
│                          └────────────────────────┘            └───────────────────────────┘              │
│                                                                                                           │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Level 4: Code Diagram (Key Classes)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Class Structure                                                                                         │
│                                                                                                        │
│  ┌────────────────┐    ┌───────────────────┐    ┌───────────────────────┐    ┌─────────────────────┐   │
│  │ZephyrConfig    │    │TestCase           │    │TestCycleInfo          │    │TestExecution        │   │
│  ├────────────────┤    ├───────────────────┤    ├───────────────────────┤    ├─────────────────────┤   │
│  │- base_url      │    │- id               │    │- id                    │    │- id                 │   │
│  │- api_token     │    │- key              │    │- key                   │    │- test_case_key      │   │
│  │- project_key   │    │- name             │    │- name                  │    │- cycle_id           │   │
│  └────────────────┘    │- steps            │    │- status                │    │- status             │   │
│                        │- custom_fields    │    │- custom_fields         │    │- steps              │   │
│                        └───────────────────┘    └───────────────────────┘    └─────────────────────┘   │
│                                                                                                        │
│  ┌────────────────┐    ┌───────────────────┐                                                           │
│  │ZephyrClient    │    │PaginatedIterator<T>                                                           │
│  ├────────────────┤    ├───────────────────┤                                                           │
│  │- config        │    │- client           │                                                           │
│  │- headers       │    │- endpoint         │                                                           │
│  │- get_projects()│    │- model_class      │                                                           │
│  │- get_test_cases│    │- params           │                                                           │
│  │- get_test_cycle│    │- current_page     │                                                           │
│  └────────────────┘    └───────────────────┘                                                           │
│                                                                                                        │
│  ┌────────────────┐    ┌───────────────────┐    ┌───────────────────────┐    ┌─────────────────────┐   │
│  │SQLiteStorage   │    │JSONStorage        │    │ZephyrExporter         │    │ZephyrExportManager  │   │
│  ├────────────────┤    ├───────────────────┤    ├───────────────────────┤    ├─────────────────────┤   │
│  │- db_path       │    │- output_dir       │    │- client               │    │- config             │   │
│  │- conn          │    │- save_test_case() │    │- output_format        │    │- output_format      │   │
│  │- cursor        │    │- save_test_cycle()│    │- storage              │    │- output_dir         │   │
│  │- save_test_case│    │- serialize_object │    │- export_all()         │    │- export_project()   │   │
│  │- initialize_db │    └───────────────────┘    └───────────────────────┘    │- export_all_projects│   │
│  └────────────────┘                                                          └─────────────────────┘   │
│                                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```