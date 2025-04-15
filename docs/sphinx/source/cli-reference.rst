CLI Command Reference
======================

This page provides detailed documentation for all ZTOQ command-line interface (CLI) commands and their options.

Core Commands
--------------

Global Options
--------------

These options can be used with any command:

.. code-block:: text

    --help            Show help message and exit
    --version         Show version information and exit
    --debug           Enable debug logging
    --log-level TEXT  Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    --log-file TEXT   Log file path (default: ztoq.log)
    --config FILE     Path to configuration file

Basic Commands
--------------

``validate``
^^^^^^^^^^^^

Validates an OpenAPI specification to ensure it's compatible with Zephyr Scale.

.. code-block:: text

    ztoq validate [OPTIONS] SPEC_PATH
    
    Options:
      --spec-format [json|yaml]  Format of the OpenAPI spec (default: auto-detect)
      --help                     Show this message and exit

``list-endpoints``
^^^^^^^^^^^^^^^^^^

Lists all available API endpoints from the OpenAPI specification.

.. code-block:: text

    ztoq list-endpoints [OPTIONS] SPEC_PATH
    
    Options:
      --format [text|json|yaml]  Output format (default: text)
      --help                     Show this message and exit

``get-projects``
^^^^^^^^^^^^^^^^

Retrieves all available projects from Zephyr Scale.

.. code-block:: text

    ztoq get-projects [OPTIONS] SPEC_PATH
    
    Options:
      --base-url TEXT        Zephyr Scale API base URL  [required]
      --api-token TEXT       Zephyr Scale API token  [required]
      --format [text|json]   Output format (default: text)
      --help                 Show this message and exit

``get-test-cases``
^^^^^^^^^^^^^^^^^^

Retrieves test cases for a specific project from Zephyr Scale.

.. code-block:: text

    ztoq get-test-cases [OPTIONS] SPEC_PATH
    
    Options:
      --base-url TEXT        Zephyr Scale API base URL  [required]
      --api-token TEXT       Zephyr Scale API token  [required]
      --project-key TEXT     Project key  [required]
      --format [text|json]   Output format (default: text)
      --limit INTEGER        Number of test cases to retrieve (default: 100)
      --offset INTEGER       Starting offset for pagination (default: 0)
      --folder-id INTEGER    Filter by folder ID
      --help                 Show this message and exit

Export Commands
---------------

``export-project``
^^^^^^^^^^^^^^^^^^

Exports all test data for a single project from Zephyr Scale.

.. code-block:: text

    ztoq export-project [OPTIONS] SPEC_PATH
    
    Options:
      --base-url TEXT                Zephyr Scale API base URL  [required]
      --api-token TEXT               Zephyr Scale API token  [required]
      --project-key TEXT             Project key  [required]
      --output-dir DIRECTORY         Output directory  [required]
      --format [json|sqlite|sql]     Output format (default: json)
      --include-attachments BOOLEAN  Include attachments (default: True)
      --help                         Show this message and exit

``export-all``
^^^^^^^^^^^^^^

Exports test data for all accessible projects from Zephyr Scale.

.. code-block:: text

    ztoq export-all [OPTIONS] SPEC_PATH
    
    Options:
      --base-url TEXT                Zephyr Scale API base URL  [required]
      --api-token TEXT               Zephyr Scale API token  [required]
      --output-dir DIRECTORY         Output directory  [required]
      --format [json|sqlite|sql]     Output format (default: json)
      --projects TEXT                Comma-separated list of project keys
      --include-attachments BOOLEAN  Include attachments (default: True)
      --max-workers INTEGER          Maximum number of worker threads (default: 4)
      --help                         Show this message and exit

Migration Commands
------------------

``migrate run``
^^^^^^^^^^^^^^^

Runs a complete migration from Zephyr Scale to qTest.

.. code-block:: text

    ztoq migrate run [OPTIONS]
    
    Options:
      --zephyr-base-url TEXT          Zephyr Scale API base URL  [required]
      --zephyr-api-token TEXT         Zephyr Scale API token  [required]
      --zephyr-project-key TEXT       Zephyr Scale project key  [required]
      --qtest-base-url TEXT           qTest API base URL  [required]
      --qtest-bearer-token TEXT       qTest bearer token
      --qtest-username TEXT           qTest username (if not using bearer token)
      --qtest-password TEXT           qTest password (if not using bearer token)
      --qtest-project-id INTEGER      qTest project ID  [required]
      --db-type [sqlite|postgresql]   Database type (default: sqlite)
      --db-path TEXT                  Database path (for SQLite)
      --db-host TEXT                  Database host (for PostgreSQL)
      --db-port INTEGER               Database port (for PostgreSQL)
      --db-username TEXT              Database username (for PostgreSQL)
      --db-password TEXT              Database password (for PostgreSQL)
      --db-name TEXT                  Database name (for PostgreSQL)
      --batch-size INTEGER            Batch size for operations (default: 50)
      --max-workers INTEGER           Maximum number of worker threads (default: 4)
      --phases TEXT                   Comma-separated list of phases to run
                                     (extract,transform,load,validate)
      --incremental BOOLEAN           Enable incremental migration (default: False)
      --no-rollback BOOLEAN           Disable rollback on failure (default: False)
      --use-batch-transformer BOOLEAN Use SQL-based batch transformer (default: True)
      --report-format [text|json|html] Report format (default: text)
      --output-dir DIRECTORY          Output directory for reports
      --help                          Show this message and exit

``migrate status``
^^^^^^^^^^^^^^^^^^

Checks the status of a migration.

.. code-block:: text

    ztoq migrate status [OPTIONS]
    
    Options:
      --db-type [sqlite|postgresql]  Database type (default: sqlite)
      --db-path TEXT                 Database path (for SQLite)
      --db-host TEXT                 Database host (for PostgreSQL)
      --db-port INTEGER              Database port (for PostgreSQL)
      --db-username TEXT             Database username (for PostgreSQL)
      --db-password TEXT             Database password (for PostgreSQL)
      --db-name TEXT                 Database name (for PostgreSQL)
      --project-key TEXT             Project key  [required]
      --format [text|json|html]      Output format (default: text)
      --output-file TEXT             Output file for report
      --help                         Show this message and exit

Workflow Commands
------------------

``workflow extract``
^^^^^^^^^^^^^^^^^^^^

Extracts data from Zephyr Scale.

.. code-block:: text

    ztoq workflow extract [OPTIONS]
    
    Options:
      --zephyr-base-url TEXT         Zephyr Scale API base URL  [required]
      --zephyr-api-token TEXT        Zephyr Scale API token  [required]
      --zephyr-project-key TEXT      Zephyr Scale project key  [required]
      --db-type [sqlite|postgresql]  Database type (default: sqlite)
      --db-path TEXT                 Database path (for SQLite)
      --db-host TEXT                 Database host (for PostgreSQL)
      --db-port INTEGER              Database port (for PostgreSQL)
      --db-username TEXT             Database username (for PostgreSQL)
      --db-password TEXT             Database password (for PostgreSQL)
      --db-name TEXT                 Database name (for PostgreSQL)
      --max-workers INTEGER          Maximum number of worker threads (default: 4)
      --include-attachments BOOLEAN  Include attachments (default: True)
      --checkpoint-interval INTEGER  Checkpoint interval in seconds (default: 300)
      --help                         Show this message and exit

``workflow transform``
^^^^^^^^^^^^^^^^^^^^^^

Transforms extracted data for qTest.

.. code-block:: text

    ztoq workflow transform [OPTIONS]
    
    Options:
      --db-type [sqlite|postgresql]   Database type (default: sqlite)
      --db-path TEXT                  Database path (for SQLite)
      --db-host TEXT                  Database host (for PostgreSQL)
      --db-port INTEGER               Database port (for PostgreSQL)
      --db-username TEXT              Database username (for PostgreSQL)
      --db-password TEXT              Database password (for PostgreSQL)
      --db-name TEXT                  Database name (for PostgreSQL)
      --project-key TEXT              Project key  [required]
      --batch-size INTEGER            Batch size for operations (default: 50)
      --use-batch-transformer BOOLEAN Use SQL-based batch transformer (default: True)
      --custom-field-map TEXT         Path to custom field mapping file
      --help                          Show this message and exit

``workflow load``
^^^^^^^^^^^^^^^^^

Loads transformed data into qTest.

.. code-block:: text

    ztoq workflow load [OPTIONS]
    
    Options:
      --qtest-base-url TEXT          qTest API base URL  [required]
      --qtest-bearer-token TEXT      qTest bearer token
      --qtest-username TEXT          qTest username (if not using bearer token)
      --qtest-password TEXT          qTest password (if not using bearer token)
      --qtest-project-id INTEGER     qTest project ID  [required]
      --db-type [sqlite|postgresql]  Database type (default: sqlite)
      --db-path TEXT                 Database path (for SQLite)
      --db-host TEXT                 Database host (for PostgreSQL)
      --db-port INTEGER              Database port (for PostgreSQL)
      --db-username TEXT             Database username (for PostgreSQL)
      --db-password TEXT             Database password (for PostgreSQL)
      --db-name TEXT                 Database name (for PostgreSQL)
      --project-key TEXT             Project key  [required]
      --batch-size INTEGER           Batch size for operations (default: 50)
      --max-workers INTEGER          Maximum number of worker threads (default: 4)
      --checkpoint-interval INTEGER  Checkpoint interval in seconds (default: 300)
      --skip-validation BOOLEAN      Skip validation checks (default: False)
      --help                         Show this message and exit

``workflow validate``
^^^^^^^^^^^^^^^^^^^^^

Runs validation on migrated data.

.. code-block:: text

    ztoq workflow validate [OPTIONS]
    
    Options:
      --qtest-base-url TEXT          qTest API base URL  [required]
      --qtest-bearer-token TEXT      qTest bearer token
      --qtest-username TEXT          qTest username (if not using bearer token)
      --qtest-password TEXT          qTest password (if not using bearer token)
      --qtest-project-id INTEGER     qTest project ID  [required]
      --db-type [sqlite|postgresql]  Database type (default: sqlite)
      --db-path TEXT                 Database path (for SQLite)
      --db-host TEXT                 Database host (for PostgreSQL)
      --db-port INTEGER              Database port (for PostgreSQL)
      --db-username TEXT             Database username (for PostgreSQL)
      --db-password TEXT             Database password (for PostgreSQL)
      --db-name TEXT                 Database name (for PostgreSQL)
      --project-key TEXT             Project key  [required]
      --output-format [text|json|html] Output format (default: text)
      --output-file TEXT             Output file for report
      --help                         Show this message and exit

``workflow rollback``
^^^^^^^^^^^^^^^^^^^^^

Runs rollback for failed migrations.

.. code-block:: text

    ztoq workflow rollback [OPTIONS]
    
    Options:
      --db-type [sqlite|postgresql]  Database type (default: sqlite)
      --db-path TEXT                 Database path (for SQLite)
      --db-host TEXT                 Database host (for PostgreSQL)
      --db-port INTEGER              Database port (for PostgreSQL)
      --db-username TEXT             Database username (for PostgreSQL)
      --db-password TEXT             Database password (for PostgreSQL)
      --db-name TEXT                 Database name (for PostgreSQL)
      --project-key TEXT             Project key  [required]
      --phases TEXT                  Comma-separated list of phases to rollback
                                    (load,transform,extract)
      --qtest-base-url TEXT          qTest API base URL (required for load phase)
      --qtest-bearer-token TEXT      qTest bearer token
      --qtest-username TEXT          qTest username (if not using bearer token)
      --qtest-password TEXT          qTest password (if not using bearer token)
      --qtest-project-id INTEGER     qTest project ID (required for load phase)
      --help                         Show this message and exit

Database Commands
------------------

``db init``
^^^^^^^^^^^

Initializes the database schema.

.. code-block:: text

    ztoq db init [OPTIONS]
    
    Options:
      --db-type [sqlite|postgresql]  Database type (default: sqlite)
      --db-path TEXT                 Database path (for SQLite)
      --db-host TEXT                 Database host (for PostgreSQL)
      --db-port INTEGER              Database port (for PostgreSQL)
      --db-username TEXT             Database username (for PostgreSQL)
      --db-password TEXT             Database password (for PostgreSQL)
      --db-name TEXT                 Database name (for PostgreSQL)
      --help                         Show this message and exit

``db migrate``
^^^^^^^^^^^^^^

Runs pending database migrations.

.. code-block:: text

    ztoq db migrate [OPTIONS]
    
    Options:
      --db-type [sqlite|postgresql]  Database type (default: sqlite)
      --db-path TEXT                 Database path (for SQLite)
      --db-host TEXT                 Database host (for PostgreSQL)
      --db-port INTEGER              Database port (for PostgreSQL)
      --db-username TEXT             Database username (for PostgreSQL)
      --db-password TEXT             Database password (for PostgreSQL)
      --db-name TEXT                 Database name (for PostgreSQL)
      --revision TEXT                Target revision (default: head)
      --help                         Show this message and exit

``db stats``
^^^^^^^^^^^^

Shows database statistics for a project.

.. code-block:: text

    ztoq db stats [OPTIONS]
    
    Options:
      --db-type [sqlite|postgresql]  Database type (default: sqlite)
      --db-path TEXT                 Database path (for SQLite)
      --db-host TEXT                 Database host (for PostgreSQL)
      --db-port INTEGER              Database port (for PostgreSQL)
      --db-username TEXT             Database username (for PostgreSQL)
      --db-password TEXT             Database password (for PostgreSQL)
      --db-name TEXT                 Database name (for PostgreSQL)
      --project-key TEXT             Project key  [required]
      --format [text|json|html]      Output format (default: text)
      --output-file TEXT             Output file for report
      --help                         Show this message and exit

``db index``
^^^^^^^^^^^^

Manages database indexes for performance optimization.

.. code-block:: text

    ztoq db index [OPTIONS] COMMAND [ARGS]...
    
    Commands:
      analyze     Analyze database query patterns
      recommend   Recommend indexes based on query patterns
      create      Create recommended indexes
      drop        Drop indexes
      list        List existing indexes
      stats       Show index usage statistics

Utility Commands
-----------------

``verify-tokens``
^^^^^^^^^^^^^^^^^

Verifies API tokens for Zephyr Scale and qTest.

.. code-block:: text

    ztoq verify-tokens [OPTIONS]
    
    Options:
      --zephyr-token TEXT   Zephyr Scale API token
      --qtest-token TEXT    qTest bearer token
      --qtest-username TEXT qTest username (if not using bearer token)
      --qtest-password TEXT qTest password (if not using bearer token)
      --verbose BOOLEAN     Show detailed information (default: False)
      --help                Show this message and exit

``generate-config``
^^^^^^^^^^^^^^^^^^^

Generates a sample configuration file.

.. code-block:: text

    ztoq generate-config [OPTIONS] OUTPUT_FILE
    
    Options:
      --format [yaml|json]  Configuration format (default: yaml)
      --help                Show this message and exit
      
Environment Variables
---------------------

ZTOQ reads many configuration values from environment variables:

.. code-block:: text

    # Zephyr Scale configuration
    zephyr_access_token       API token for Zephyr Scale
    zephyr_base_url           Base URL for Zephyr Scale API
    zephyr_project_key        Default project key for Zephyr Scale
    
    # qTest configuration
    qtest_bearer_token        Bearer token for qTest API
    qtest_base_url            Base URL for qTest API
    qtest_project_id          Default project ID for qTest
    qtest_username            Username for qTest (if not using bearer token)
    qtest_password            Password for qTest (if not using bearer token)
    
    # Database configuration
    ztoq_db_type              Database type (sqlite or postgresql)
    ztoq_db_path              Database path (for SQLite)
    ztoq_db_host              Database host (for PostgreSQL)
    ztoq_db_port              Database port (for PostgreSQL)
    ztoq_db_username          Database username (for PostgreSQL)
    ztoq_db_password          Database password (for PostgreSQL)
    ztoq_db_name              Database name (for PostgreSQL)
    
    # Performance tuning
    ztoq_batch_size           Batch size for operations
    ztoq_max_workers          Maximum number of worker threads
    ztoq_use_batch_transformer Enable/disable SQL-based batch transformer
    
    # Logging configuration
    ZTOQ_LOG_LEVEL            Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    ZTOQ_LOG_FILE             Log file path