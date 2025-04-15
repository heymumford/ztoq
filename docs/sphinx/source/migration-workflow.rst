Migration Workflow Guide
=====================

This guide explains the complete process of migrating test data from Zephyr Scale to qTest using ZTOQ, including best practices and troubleshooting tips.

Overview
--------

ZTOQ uses a four-phase ETL (Extract, Transform, Load, Validate) pipeline for migration:

1. **Extract**: Data is pulled from Zephyr Scale using their API
2. **Transform**: Data is restructured to match qTest's data model
3. **Load**: Transformed data is pushed to qTest using their API
4. **Validate**: Data in qTest is verified against the source data

The migration process is designed to be:

- **Resumable**: You can stop and restart at any point
- **Incremental**: Only migrate what has changed since last run
- **Reliable**: Comprehensive validation and error handling
- **Efficient**: Parallel processing and batch operations
- **Traceable**: Detailed logging and reporting

Prerequisites
------------

Before starting a migration, ensure you have:

1. **API Access**:
   - Zephyr Scale API token with read access
   - qTest API token or username/password with write access

2. **Project Information**:
   - Zephyr Scale project key
   - qTest project ID

3. **Database Setup**:
   - SQLite for small migrations (default)
   - PostgreSQL for large migrations (recommended for production)

4. **System Requirements**:
   - Python 3.8 or higher
   - Sufficient disk space for the database and attachments
   - Adequate network bandwidth for API communication

Planning Your Migration
----------------------

Migration Scope
~~~~~~~~~~~~~~

Determine what you want to migrate:

- **Test Cases**: Core test definitions
- **Test Cycles**: Test execution groupings
- **Test Executions**: Test run history
- **Attachments**: Binary files attached to test entities
- **Custom Fields**: User-defined fields and metadata

Migration Strategy
~~~~~~~~~~~~~~~~

Choose a migration approach based on your needs:

1. **Complete Migration**:
   - Migrate everything at once
   - Best for one-time migrations

2. **Incremental Migration**:
   - Migrate changes since last run
   - Best for ongoing synchronization

3. **Phased Migration**:
   - Migrate one entity type at a time
   - Best for complex migrations with validation between phases

Database Selection
~~~~~~~~~~~~~~~~

Choose the appropriate database:

- **SQLite**: Simple setup, good for small migrations (< 10,000 test cases)
- **PostgreSQL**: Better performance, required for large migrations

Step-by-Step Migration Process
-----------------------------

Step 1: Initialize the Database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # For SQLite
    ztoq db init --db-type sqlite --db-path ./migration.db
    
    # For PostgreSQL
    ztoq db init --db-type postgresql \
      --db-host localhost --db-port 5432 \
      --db-username ztoq_user --db-password password \
      --db-name ztoq_db

Step 2: Create a Configuration File
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a `config.yaml` file with your migration settings:

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
    
    migration:
      incremental: false
      include_attachments: true
      phases: extract,transform,load,validate
      no_rollback: false
    
    logging:
      level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
      file: ztoq-migration.log

Step 3: Run the Migration
~~~~~~~~~~~~~~~~~~~~~~~

Run the full migration in a single command:

.. code-block:: bash

    ztoq migrate run --config config.yaml

Alternatively, run each phase separately for more control:

.. code-block:: bash

    # Extract phase
    ztoq workflow extract --config config.yaml
    
    # Transform phase
    ztoq workflow transform --config config.yaml
    
    # Load phase
    ztoq workflow load --config config.yaml
    
    # Validate phase
    ztoq workflow validate --config config.yaml

Step 4: Monitor Progress
~~~~~~~~~~~~~~~~~~~~~

Check migration status periodically:

.. code-block:: bash

    ztoq migrate status --config config.yaml

You can also view detailed database statistics:

.. code-block:: bash

    ztoq db stats --config config.yaml --project-key PROJECT

Step 5: Validate Results
~~~~~~~~~~~~~~~~~~~~~

Run a comprehensive validation:

.. code-block:: bash

    ztoq workflow validate --config config.yaml \
      --output-format html --output-file validation-report.html

Review the validation report to identify any issues.

Advanced Migration Scenarios
--------------------------

Handling Custom Fields
~~~~~~~~~~~~~~~~~~~~

Custom fields require mapping between Zephyr Scale and qTest:

1. **Create a mapping file** (`custom_fields_map.yaml`):

   .. code-block:: yaml

       test_case:
         # Zephyr field name: qTest field name
         "Requirement ID": "Requirement"
         "Automation Status": "Automation"
       
       test_cycle:
         "Sprint": "Sprint Number"
         "Release": "Release Version"
       
       test_execution:
         "Environment": "Test Environment"
         "Browser": "Browser Version"

2. **Use the mapping in your migration**:

   .. code-block:: bash

       ztoq workflow transform --config config.yaml \
         --custom-field-map custom_fields_map.yaml

For more details, see the :doc:`custom-fields` documentation.

Incremental Migration
~~~~~~~~~~~~~~~~~~~

For ongoing synchronization, use incremental migration:

.. code-block:: bash

    # Enable incremental migration
    ztoq migrate run --config config.yaml --incremental true

This will:
- Only extract test entities that have changed since the last run
- Update existing entities in qTest rather than creating duplicates
- Track migration state between runs

Large-Scale Migrations
~~~~~~~~~~~~~~~~~~~~

For large migrations (> 10,000 test cases):

1. **Use PostgreSQL** for better performance:

   .. code-block:: bash

       ztoq db init --db-type postgresql \
         --db-host localhost --db-port 5432 \
         --db-username ztoq_user --db-password password \
         --db-name ztoq_db

2. **Optimize performance settings**:

   .. code-block:: yaml

       performance:
         batch_size: 200
         max_workers: 16
         use_batch_transformer: true

3. **Run in multiple phases**:

   .. code-block:: bash

       # Extract and transform first
       ztoq migrate run --config config.yaml --phases extract,transform
       
       # Then load and validate
       ztoq migrate run --config config.yaml --phases load,validate

Handling Errors and Recovery
--------------------------

When Errors Occur
~~~~~~~~~~~~~~~

If the migration encounters errors:

1. Check the log file for error details:

   .. code-block:: bash

       less ztoq-migration.log

2. Fix any issues with data or configuration

3. Resume the migration:

   .. code-block:: bash

       ztoq migrate run --config config.yaml

   The migration will automatically continue from where it left off.

Manual Rollback
~~~~~~~~~~~~~

If you need to roll back a migration:

.. code-block:: bash

    ztoq workflow rollback --config config.yaml \
      --project-key PROJECT --phases load,transform,extract

This will:
- Remove migrated entities from qTest
- Clear transformed data from the database
- Optionally remove extracted data

Automated Migration with Docker
-----------------------------

For containerized migration:

.. code-block:: bash

    # Set up the migration environment
    ./config/run-migration.sh setup
    
    # Run a migration with default settings
    ./config/run-migration.sh run
    
    # Run a migration with custom batch size and workers
    ./config/run-migration.sh run --batch-size 100 --workers 8 --phase extract
    
    # Check migration status
    ./config/run-migration.sh status
    
    # Generate a migration report
    ./config/run-migration.sh report
    
    # Start an interactive migration dashboard
    ./config/run-migration.sh dashboard

Scheduled Migrations with CI/CD
-----------------------------

For automated and scheduled migrations:

1. **Create a GitHub Actions workflow** (`.github/workflows/scheduled-migration.yml`):

   .. code-block:: yaml

       name: Scheduled Migration
       
       on:
         schedule:
           - cron: '0 2 * * *'  # Run daily at 2:00 AM UTC
         workflow_dispatch:     # Allow manual triggering
       
       jobs:
         migrate:
           runs-on: ubuntu-latest
           steps:
             - uses: actions/checkout@v2
             - name: Set up Python
               uses: actions/setup-python@v2
               with:
                 python-version: '3.8'
             - name: Install dependencies
               run: |
                 python -m pip install --upgrade pip
                 pip install -e .
             - name: Run migration
               run: |
                 ztoq migrate run --config config.yaml
               env:
                 zephyr_access_token: ${{ secrets.ZEPHYR_API_TOKEN }}
                 qtest_bearer_token: ${{ secrets.QTEST_API_TOKEN }}

2. **Set up secrets in your CI/CD environment**

3. **Configure notifications for migration results**

For more information, see the :doc:`scheduled-migrations` documentation.

Performance Tuning
----------------

Optimize migration performance:

1. **Adjust batch size** based on entity type:

   .. code-block:: yaml

       performance:
         batch_size: 200  # Higher for test cases, lower for executions
         
2. **Tune worker count** based on available CPU and network resources:

   .. code-block:: yaml

       performance:
         max_workers: 8  # Increase for faster networks and more CPU cores

3. **Enable batch transformer** for faster SQL operations:

   .. code-block:: yaml

       performance:
         use_batch_transformer: true

4. **Optimize database indexes**:

   .. code-block:: bash

       # Analyze query patterns
       ztoq db index analyze --config config.yaml
       
       # Create recommended indexes
       ztoq db index create --config config.yaml

Troubleshooting
--------------

Common Issues
~~~~~~~~~~~

1. **API Rate Limiting**:
   
   *Symptom*: Extraction fails with HTTP 429 errors
   
   *Solution*: 
   - Reduce worker count
   - Enable automatic retry
   - Add rate limit options:
     
     .. code-block:: yaml
     
         zephyr:
           rate_limit_delay: 5  # seconds between requests
           auto_retry: true
           retry_count: 3

2. **Memory Issues**:
   
   *Symptom*: Process crashes with out-of-memory errors
   
   *Solution*:
   - Reduce batch size
   - Use PostgreSQL instead of SQLite
   - Run extraction and transformation separately

3. **Network Errors**:
   
   *Symptom*: Connection timeout or reset errors
   
   *Solution*:
   - Enable retry:
     
     .. code-block:: yaml
     
         network:
           timeout: 60  # seconds
           retry_count: 3
           retry_delay: 5  # seconds

4. **Authentication Errors**:
   
   *Symptom*: HTTP 401 or 403 errors
   
   *Solution*:
   - Verify API tokens
   - Check permissions
   - Ensure URLs are correct:
     
     .. code-block:: bash
     
         ztoq verify-tokens --zephyr-token YOUR_TOKEN --qtest-token YOUR_TOKEN

Logging and Debugging
~~~~~~~~~~~~~~~~~~~

Enable debug logging for troubleshooting:

.. code-block:: yaml

    logging:
      level: DEBUG
      file: ztoq-debug.log

View real-time logs during migration:

.. code-block:: bash

    # In a separate terminal
    tail -f ztoq-debug.log

Next Steps
---------

After completing the migration:

1. **Verify data integrity** in qTest
2. **Generate a final report**:
   
   .. code-block:: bash
   
       ztoq migrate status --config config.yaml \
         --format html --output-file migration-report.html

3. **Document your migration** for future reference

For more information on specific aspects of the migration process, refer to:

- :doc:`conversion-process` - Technical details of the ETL pipeline
- :doc:`entity-mapping` - How Zephyr entities map to qTest entities
- :doc:`custom-fields` - Handling custom fields and attachments
- :doc:`database-configuration` - Database setup and optimization