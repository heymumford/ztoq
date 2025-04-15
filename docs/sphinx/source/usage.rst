Usage Guide
===========

ZTOQ is a powerful tool for migrating test data from Zephyr Scale to qTest. This guide covers all common use cases, from basic operations to advanced migration workflows.

Basic Concepts
-------------

ZTOQ operates as an ETL (Extract, Transform, Load) pipeline:

1. **Extract**: Data is pulled from Zephyr Scale using their API
2. **Transform**: Data is restructured to match qTest's data model
3. **Load**: Transformed data is pushed to qTest using their API

The tool provides both a command-line interface (CLI) and a Python API for these operations.

Command Line Interface
---------------------

The CLI provides commands for different aspects of the migration process:

.. code-block:: bash

    # Get help with available commands
    ztoq --help
    
    # Get help with a specific command
    ztoq migrate --help

Using Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~

For security reasons, API tokens should be provided as environment variables:

.. code-block:: bash

    # Set environment variables for API access
    export zephyr_access_token="your_zephyr_token"
    export qtest_bearer_token="your_qtest_token"

Common Commands
--------------

Here are the most commonly used commands:

Validate OpenAPI Specification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Validate the OpenAPI spec is for Zephyr Scale
    ztoq validate z-openapi.yml

List API Endpoints
~~~~~~~~~~~~~~~~

.. code-block:: bash

    # List all API endpoints in the spec
    ztoq list-endpoints z-openapi.yml

Get Projects
~~~~~~~~~~

.. code-block:: bash

    # Get all available projects
    ztoq get-projects z-openapi.yml \
      --base-url https://api.atlassian.com/ex/jira/your-instance/rest/zephyr/1.0 \
      --api-token YOUR_TOKEN

Get Test Cases
~~~~~~~~~~~~

.. code-block:: bash

    # Get test cases for a project
    ztoq get-test-cases z-openapi.yml \
      --base-url https://api.atlassian.com/ex/jira/your-instance/rest/zephyr/1.0 \
      --api-token YOUR_TOKEN \
      --project-key PROJECT \
      --limit 100

Export All Test Data
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Export all test data for a single project
    ztoq export-project z-openapi.yml \
      --base-url https://api.atlassian.com/ex/jira/your-instance/rest/zephyr/1.0 \
      --api-token YOUR_TOKEN \
      --project-key PROJECT \
      --output-dir ./zephyr-data \
      --format json

Migration Workflow
-----------------

The complete migration process is managed with the ``migrate`` command:

.. code-block:: bash

    # Run a complete migration from Zephyr Scale to qTest
    ztoq migrate run \
      --zephyr-base-url https://api.atlassian.com/ex/jira/your-instance/rest/zephyr/1.0 \
      --zephyr-api-token YOUR_ZEPHYR_TOKEN \
      --zephyr-project-key PROJECT \
      --qtest-base-url https://yourcompany.qtestnet.com \
      --qtest-bearer-token YOUR_QTEST_TOKEN \
      --qtest-project-id 12345 \
      --db-type sqlite \
      --db-path ./migration.db \
      --batch-size 100 \
      --max-workers 8

Check Migration Status
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Check migration status
    ztoq migrate status \
      --db-type sqlite \
      --db-path ./migration.db \
      --project-key PROJECT

Fine-Grained Workflow Commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For more control over the migration process, use the ``workflow`` commands:

.. code-block:: bash

    # Extract data from Zephyr Scale
    ztoq workflow extract \
      --zephyr-base-url https://api.atlassian.com/ex/jira/your-instance/rest/zephyr/1.0 \
      --zephyr-api-token YOUR_ZEPHYR_TOKEN \
      --zephyr-project-key PROJECT \
      --db-type sqlite \
      --db-path ./migration.db
    
    # Transform extracted data for qTest
    ztoq workflow transform \
      --db-type sqlite \
      --db-path ./migration.db \
      --project-key PROJECT \
      --batch-size 100 \
      --use-batch-transformer true
    
    # Load transformed data into qTest
    ztoq workflow load \
      --qtest-base-url https://yourcompany.qtestnet.com \
      --qtest-bearer-token YOUR_QTEST_TOKEN \
      --qtest-project-id 12345 \
      --db-type sqlite \
      --db-path ./migration.db \
      --project-key PROJECT \
      --max-workers 5
    
    # Run validation on migrated data
    ztoq workflow validate \
      --qtest-base-url https://yourcompany.qtestnet.com \
      --qtest-bearer-token YOUR_QTEST_TOKEN \
      --qtest-project-id 12345 \
      --db-type sqlite \
      --db-path ./migration.db \
      --project-key PROJECT \
      --output-format json
    
    # Run rollback for failed migrations
    ztoq workflow rollback \
      --db-type sqlite \
      --db-path ./migration.db \
      --project-key PROJECT \
      --phases load,transform,extract

Database Management
------------------

ZTOQ provides commands for managing the migration database:

.. code-block:: bash

    # Initialize the database schema
    ztoq db init --db-type sqlite
    
    # Show database statistics for a project
    ztoq db stats --project-key PROJECT
    
    # Run pending database migrations
    ztoq db migrate
    
    # Use PostgreSQL database (recommended for production)
    ztoq db init --db-type postgresql \
      --host localhost --port 5432 \
      --username ztoq_user --password password \
      --database ztoq_db

Python API
---------

ZTOQ can also be used as a Python library in your scripts:

.. code-block:: python

    from ztoq.zephyr_client import ZephyrClient
    from ztoq.models import ZephyrConfig
    from ztoq.database_manager import DatabaseManager
    from ztoq.qtest_client import QTestClient
    from ztoq.qtest_models import QTestConfig
    from ztoq.migration import MigrationManager
    from pathlib import Path
    
    # Create Zephyr configuration
    zephyr_config = ZephyrConfig(
        base_url="https://api.example.com",
        api_token="YOUR_ZEPHYR_TOKEN",
        project_key="PROJECT_KEY"
    )
    
    # Create qTest configuration
    qtest_config = QTestConfig(
        base_url="https://yourcompany.qtestnet.com",
        bearer_token="YOUR_QTEST_TOKEN",
        project_id=12345
    )
    
    # Initialize clients
    zephyr_client = ZephyrClient(zephyr_config)
    qtest_client = QTestClient(qtest_config)
    
    # Initialize database
    db_manager = DatabaseManager(Path("./data/migration.db"))
    db_manager.initialize_database()
    
    # Initialize migration manager
    migration_manager = MigrationManager(
        zephyr_client=zephyr_client,
        qtest_client=qtest_client,
        db_manager=db_manager,
        project_key="PROJECT_KEY",
        batch_size=100,
        max_workers=8
    )
    
    # Run migration
    result = migration_manager.run_migration()
    
    # Check migration status
    status = migration_manager.get_status()
    print(f"Migrated {status.test_cases_migrated} test cases")
    print(f"Migrated {status.test_cycles_migrated} test cycles")
    print(f"Migrated {status.test_executions_migrated} test executions")

Configuration
------------

ZTOQ can be configured through:

1. Command-line arguments
2. Environment variables
3. Configuration file

Environment Variables
~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Zephyr Scale configuration
    export zephyr_access_token="YOUR_ZEPHYR_TOKEN"
    export zephyr_base_url="https://api.atlassian.com/ex/jira/your-instance/rest/zephyr/1.0"
    export zephyr_project_key="PROJECT"
    
    # qTest configuration
    export qtest_bearer_token="YOUR_QTEST_TOKEN"
    export qtest_base_url="https://yourcompany.qtestnet.com"
    export qtest_project_id="12345"
    
    # Database configuration
    export ztoq_db_type="sqlite"  # or "postgresql"
    export ztoq_db_path="./migration.db"
    
    # Performance tuning
    export ztoq_batch_size="100"
    export ztoq_max_workers="8"
    export ztoq_use_batch_transformer="true"
    
    # Logging configuration
    export ZTOQ_LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

Configuration File
~~~~~~~~~~~~~~~~

Example configuration file (`config.yaml`):

.. code-block:: yaml

    zephyr:
      base_url: https://api.atlassian.com/ex/jira/your-instance/rest/zephyr/1.0
      api_token: YOUR_ZEPHYR_TOKEN
      project_key: PROJECT
    
    qtest:
      base_url: https://yourcompany.qtestnet.com
      bearer_token: YOUR_QTEST_TOKEN
      project_id: 12345
    
    database:
      type: sqlite  # or postgresql
      path: ./migration.db
      # PostgreSQL specific options
      # host: localhost
      # port: 5432
      # username: ztoq_user
      # password: password
      # database: ztoq_db
    
    performance:
      batch_size: 100
      max_workers: 8
      use_batch_transformer: true
    
    logging:
      level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL

Using the configuration file:

.. code-block:: bash

    ztoq migrate run --config config.yaml

Debugging
---------

For troubleshooting, you can enable DEBUG logging:

.. code-block:: bash

    # Enable debug logging with environment variable
    export ZTOQ_LOG_LEVEL=DEBUG
    
    # Run command with debug flag
    ztoq --debug migrate run [options]
    
    # Check detailed logs
    cat ztoq-debug.log

When DEBUG logging is enabled, you'll see detailed information about:

- API requests and responses
- API call timings
- Rate limiting information
- Full error details with context
- Pagination handling
- Schema validation results
- Request/response validation errors

The logs automatically redact sensitive information like API tokens.

Next Steps
---------

Now that you understand how to use ZTOQ, you might want to explore:

- :doc:`conversion-process` - Learn about the ETL pipeline details
- :doc:`custom-fields` - Work with custom fields and attachments
- :doc:`entity-mapping` - Understand how Zephyr data maps to qTest
- :doc:`database-configuration` - Configure database for optimal performance