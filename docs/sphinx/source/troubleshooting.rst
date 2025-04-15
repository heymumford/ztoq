Troubleshooting
===============

This guide helps you diagnose and solve common issues with ZTOQ.

General Troubleshooting
---------------------

Enable Debug Logging
~~~~~~~~~~~~~~~~~~

When troubleshooting, the first step is to enable debug logging:

.. code-block:: bash

    # Set environment variable
    export ZTOQ_LOG_LEVEL=DEBUG
    
    # Run command with debug flag
    ztoq --debug migrate run --config config.yaml
    
    # Specify a log file
    ztoq --debug --log-file ztoq-debug.log migrate run --config config.yaml

Debug logs provide detailed information about:
- API requests and responses
- Error details with stack traces
- Database operations
- Data transformation steps
- Validation results

Check Versions
~~~~~~~~~~~~

Ensure you're using the latest version of ZTOQ:

.. code-block:: bash

    # Check installed version
    ztoq --version
    
    # Update to latest version
    pip install --upgrade ztoq

Common Issues
-----------

API Authentication Problems
~~~~~~~~~~~~~~~~~~~~~~~~~

**Issue**: HTTP 401 (Unauthorized) or 403 (Forbidden) errors when connecting to APIs.

**Solution**:

1. Verify your API tokens:

   .. code-block:: bash

       ztoq verify-tokens --zephyr-token YOUR_TOKEN --qtest-token YOUR_TOKEN

2. Check that tokens have the correct permissions:
   - Zephyr Scale token needs read access
   - qTest token needs write access

3. Ensure URLs are correct:
   - Zephyr Scale URL should end with `/rest/zephyr/1.0`
   - qTest URL should be the base URL (e.g., `https://yourcompany.qtestnet.com`)

4. For qTest, try using username/password instead of bearer token:

   .. code-block:: bash

       ztoq migrate run --config config.yaml \
         --qtest-username YOUR_USERNAME --qtest-password YOUR_PASSWORD

API Rate Limiting
~~~~~~~~~~~~~~~

**Issue**: HTTP 429 (Too Many Requests) errors during data extraction or loading.

**Solution**:

1. Reduce the number of worker threads:

   .. code-block:: bash

       ztoq migrate run --config config.yaml --max-workers 2

2. Add rate limiting configuration to your `config.yaml`:

   .. code-block:: yaml

       zephyr:
         rate_limit_delay: 2  # seconds between requests
       
       qtest:
         rate_limit_delay: 1  # seconds between requests

3. Enable automatic retry with exponential backoff:

   .. code-block:: yaml

       api:
         auto_retry: true
         retry_count: 5
         retry_backoff: true

Database Issues
~~~~~~~~~~~~~

**Issue**: Database errors or corruption.

**Solution**:

1. For SQLite issues:
   
   - Check file permissions:
     
     .. code-block:: bash
     
         ls -la migration.db
         chmod 644 migration.db
   
   - Create a new database:
     
     .. code-block:: bash
     
         rm migration.db
         ztoq db init --db-type sqlite --db-path migration.db

2. For PostgreSQL issues:
   
   - Verify connection parameters:
     
     .. code-block:: bash
     
         psql -h localhost -U username -d database -c "SELECT 1"
   
   - Check that the schema exists:
     
     .. code-block:: bash
     
         psql -h localhost -U username -d database -c "\dt"
   
   - Reinitialize the database:
     
     .. code-block:: bash
     
         ztoq db init --db-type postgresql \
           --db-host localhost --db-port 5432 \
           --db-username username --db-password password \
           --db-name database

Memory Issues
~~~~~~~~~~~

**Issue**: Process crashes with out-of-memory errors.

**Solution**:

1. Reduce batch size:

   .. code-block:: bash

       ztoq migrate run --config config.yaml --batch-size 20

2. Process phases separately:

   .. code-block:: bash

       # Extract data first
       ztoq workflow extract --config config.yaml
       
       # Then transform
       ztoq workflow transform --config config.yaml
       
       # Finally, load
       ztoq workflow load --config config.yaml

3. For large migrations, use PostgreSQL instead of SQLite:

   .. code-block:: bash

       ztoq db init --db-type postgresql \
         --db-host localhost --db-port 5432 \
         --db-username username --db-password password \
         --db-name database

Network Errors
~~~~~~~~~~~~

**Issue**: Connection timeouts or resets during API operations.

**Solution**:

1. Configure longer timeouts:

   .. code-block:: yaml

       network:
         timeout: 60  # seconds
         connect_timeout: 30  # seconds

2. Enable retry with longer delays:

   .. code-block:: yaml

       network:
         retry_count: 5
         retry_delay: 10  # seconds
         retry_backoff: true

3. Check your network connection and proxy settings

Entity-Specific Issues
--------------------

Test Case Migration Issues
~~~~~~~~~~~~~~~~~~~~~~~~

**Issue**: Test cases fail to migrate correctly.

**Solutions**:

1. Check for custom fields that might be missing a mapping:

   .. code-block:: bash

       # Extract test cases with custom fields
       ztoq get-test-cases z-openapi.yml \
         --base-url YOUR_URL --api-token YOUR_TOKEN \
         --project-key PROJECT \
         --format json > test_cases.json
       
       # Look for custom fields in the output
       grep -i "customField" test_cases.json

2. Create a custom field mapping file:

   .. code-block:: yaml

       test_case:
         "Requirement ID": "Requirement"
         "Automation Status": "Automation"

3. Use the mapping in your migration:

   .. code-block:: bash

       ztoq workflow transform --config config.yaml \
         --custom-field-map custom_fields.yaml

Test Cycle Migration Issues
~~~~~~~~~~~~~~~~~~~~~~~~~

**Issue**: Test cycles fail to migrate or have incorrect hierarchy.

**Solutions**:

1. Check cycle hierarchy in Zephyr Scale:

   .. code-block:: bash

       ztoq get-test-cycles z-openapi.yml \
         --base-url YOUR_URL --api-token YOUR_TOKEN \
         --project-key PROJECT \
         --format json > test_cycles.json

2. Ensure qTest has appropriate test cycle structure:
   - qTest requires at least one cycle at the root level
   - Nested cycles must have a parent cycle

3. Add cycle mapping to your configuration:

   .. code-block:: yaml

       entity_mapping:
         test_cycle:
           folder_mapping: true
           create_missing_parents: true

Attachment Migration Issues
~~~~~~~~~~~~~~~~~~~~~~~~~

**Issue**: Attachments fail to upload or download.

**Solutions**:

1. Check attachment sizes:
   - Zephyr Scale may limit attachment sizes
   - qTest typically limits attachments to 50MB

2. Configure attachment handling:

   .. code-block:: yaml

       attachments:
         include: true
         max_size_mb: 50
         skip_on_error: true
         concurrent_uploads: 2

3. Disable attachments if they're causing problems:

   .. code-block:: bash

       ztoq migrate run --config config.yaml --include-attachments false

Migration Process Issues
---------------------

Interrupted Migration
~~~~~~~~~~~~~~~~~~~

**Issue**: Migration was interrupted and needs to be resumed.

**Solution**:

ZTOQ automatically saves migration state, so you can usually just run the same command again:

.. code-block:: bash

    ztoq migrate run --config config.yaml

The migration will continue from where it left off.

Failed Validation
~~~~~~~~~~~~~~~

**Issue**: Validation phase reports data integrity issues.

**Solutions**:

1. Generate a detailed validation report:

   .. code-block:: bash

       ztoq workflow validate --config config.yaml \
         --output-format html --output-file validation-report.html

2. Fix any identified issues:
   - Incorrect mappings
   - Missing custom fields
   - qTest configuration issues

3. Run a specific phase again:

   .. code-block:: bash

       # Re-run transformation and loading
       ztoq migrate run --config config.yaml --phases transform,load

Migration Takes Too Long
~~~~~~~~~~~~~~~~~~~~~

**Issue**: Migration is very slow or seems to hang.

**Solutions**:

1. Optimize performance settings:

   .. code-block:: yaml

       performance:
         batch_size: 200
         max_workers: 8
         use_batch_transformer: true

2. Use a more efficient database:

   .. code-block:: bash

       ztoq db init --db-type postgresql \
         --db-host localhost --db-port 5432 \
         --db-username username --db-password password \
         --db-name database

3. Run phases separately and monitor each one:

   .. code-block:: bash

       # Extract with progress monitoring
       ztoq workflow extract --config config.yaml
       
       # Then transform
       ztoq workflow transform --config config.yaml
       
       # Finally, load
       ztoq workflow load --config config.yaml

4. Optimize database indexes:

   .. code-block:: bash

       # Analyze query patterns
       ztoq db index analyze --config config.yaml
       
       # Create recommended indexes
       ztoq db index create --config config.yaml

Diagnosing Issues
---------------

Check Database Status
~~~~~~~~~~~~~~~~~~~

View database statistics to understand the current migration state:

.. code-block:: bash

    ztoq db stats --config config.yaml --project-key PROJECT

This shows:
- Entity counts by type
- Migration progress percentages
- Data storage usage
- Error counts

Analyze Logs
~~~~~~~~~~~

Find specific error patterns in logs:

.. code-block:: bash

    # Find all HTTP errors
    grep "HTTP Error" ztoq-debug.log
    
    # Find rate limiting issues
    grep -i "rate limit" ztoq-debug.log
    
    # Find database errors
    grep -i "database error" ztoq-debug.log
    
    # Find transformation errors
    grep -i "transformation error" ztoq-debug.log

Test API Connectivity
~~~~~~~~~~~~~~~~~~~

Verify API connections independently:

.. code-block:: bash

    # Test Zephyr Scale API
    ztoq get-projects z-openapi.yml \
      --base-url YOUR_URL --api-token YOUR_TOKEN
    
    # Test qTest API connectivity
    ztoq verify-tokens --qtest-token YOUR_TOKEN

Rollback a Failed Migration
~~~~~~~~~~~~~~~~~~~~~~~~~

If you need to start over:

.. code-block:: bash

    # Rollback everything
    ztoq workflow rollback --config config.yaml \
      --project-key PROJECT --phases load,transform,extract
    
    # Rollback just the load phase
    ztoq workflow rollback --config config.yaml \
      --project-key PROJECT --phases load

Advanced Troubleshooting
----------------------

Use Mock Servers
~~~~~~~~~~~~~~

For testing without real APIs:

.. code-block:: bash

    # Start mock servers
    ztoq mock start --zephyr-port 8080 --qtest-port 8081
    
    # Use mock servers in your migration
    ztoq migrate run --config config.yaml \
      --zephyr-base-url http://localhost:8080 \
      --qtest-base-url http://localhost:8081

Export API Responses
~~~~~~~~~~~~~~~~~~

Save API responses for analysis:

.. code-block:: bash

    # Enable API response saving
    export ZTOQ_SAVE_RESPONSES=true
    export ZTOQ_RESPONSE_DIR=./api_responses
    
    # Run your command
    ztoq workflow extract --config config.yaml
    
    # Examine saved responses
    ls -la ./api_responses

Create a Diagnostic Report
~~~~~~~~~~~~~~~~~~~~~~~~

Generate a comprehensive diagnostic report:

.. code-block:: bash

    ztoq diagnostic --config config.yaml \
      --output-file diagnostic-report.html

This provides:
- System information
- Configuration details
- Database status
- API connectivity tests
- Recommended actions

Getting Additional Help
---------------------

If you can't resolve the issue:

1. Generate a diagnostic report (see above)

2. Create a GitHub issue with:
   - Your diagnostic report
   - Steps to reproduce the problem
   - Error messages
   - ZTOQ version information

3. For urgent issues, consider:
   - Using Docker for a clean environment
   - Running a minimal test migration
   - Providing sanitized examples of problematic data