Architecture
============

C4 Diagram
----------

.. include:: ../../../docs/c4-diagram.md
   :parser: myst_parser.sphinx_

Components
----------

ZTOQ is organized into several main components:

1. **Zephyr Client**: Handles API communication with Zephyr Scale.
2. **Data Models**: Defines the structure of the data using Pydantic.
3. **Storage Layer**: Manages data storage in SQLite or JSON formats.
4. **Database Manager**: Handles database operations for storing fetched data.
5. **CLI**: Provides command-line interface for user interaction.
6. **Error Handling**: Provides domain-specific exceptions and Result objects for operations.
7. **Logging System**: Implements structured logging with context and redaction capabilities.
8. **Documentation**: Comprehensive documentation with Sphinx, ADRs, and C4 diagrams.

Sequence Flow
-------------

.. code-block:: text

    ┌────────┐          ┌───────────┐          ┌───────────┐          ┌────────────┐
    │  User  │          │   CLI     │          │  Zephyr   │          │  Database  │
    │        │          │           │          │  Client   │          │  Manager   │
    └────┬───┘          └─────┬─────┘          └─────┬─────┘          └──────┬─────┘
         │                    │                      │                        │
         │ Execute command    │                      │                        │
         │───────────────────>│                      │                        │
         │                    │                      │                        │
         │                    │ Create client        │                        │
         │                    │─────────────────────>│                        │
         │                    │                      │                        │
         │                    │ Initialize DB        │                        │
         │                    │──────────────────────┼───────────────────────>│
         │                    │                      │                        │
         │                    │ Fetch data           │                        │
         │                    │─────────────────────>│                        │
         │                    │                      │   Fetch from API       │
         │                    │                      │◀────────────────────┐  │
         │                    │                      │                     │  │
         │                    │                      │───────────────────┐ │  │
         │                    │                      │ Process response  │ │  │
         │                    │                      │◀──────────────────┘ │  │
         │                    │ Return data          │                     │  │
         │                    │<─────────────────────│                     │  │
         │                    │                      │                     │  │
         │                    │ Save data            │                     │  │
         │                    │──────────────────────┼───────────────────────>│
         │                    │                      │                     │  │
         │                    │                      │                     │  │
         │ Report completion  │                      │                     │  │
         │<───────────────────│                      │                     │  │
    ┌────┴───┐          ┌─────┴─────┐          ┌─────┴─────┐          ┌──────┴─────┐
    │  User  │          │   CLI     │          │  Zephyr   │          │  Database  │
    │        │          │           │          │  Client   │          │  Manager   │
    └────────┘          └───────────┘          └───────────┘          └────────────┘

Design Decisions
----------------

For detailed information about design decisions, please refer to the Architecture Decision Records (ADRs):

.. toctree::
   :maxdepth: 1
   
   adrs/index

Additional Architecture Documents
---------------------------------

.. toctree::
   :maxdepth: 1
   
   openapi-integration
   qtest-integration
   conversion-process
   entity-mapping