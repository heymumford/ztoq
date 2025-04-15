Getting Started
===============

Welcome to ZTOQ! This guide will help you get up and running quickly with our test migration tool.

What is ZTOQ?
-----------

ZTOQ (Zephyr to qTest) is a powerful Python CLI tool that helps you migrate test data from Zephyr Scale to qTest. It provides a complete solution for:

- Extracting test cases, cycles, and executions from Zephyr Scale
- Transforming the data to match qTest's data model
- Loading the transformed data into qTest
- Validating the migration to ensure data integrity

Quick Installation
----------------

The fastest way to get started is to install ZTOQ from PyPI:

.. code-block:: bash

    pip install ztoq

Verify that the installation worked:

.. code-block:: bash

    ztoq --version

This should display the current version of ZTOQ.

5-Minute Setup Guide
------------------

Follow these steps to perform a basic test migration:

1. **Set up API tokens**:

   .. code-block:: bash

       # Export your API tokens as environment variables
       export zephyr_access_token="your_zephyr_token"
       export qtest_bearer_token="your_qtest_token"

2. **Verify your tokens**:

   .. code-block:: bash

       ztoq verify-tokens

3. **Initialize the database**:

   .. code-block:: bash

       ztoq db init --db-type sqlite --db-path ./migration.db

4. **Run a test migration**:

   .. code-block:: bash

       ztoq migrate run \
         --zephyr-base-url https://api.atlassian.com/ex/jira/your-instance/rest/zephyr/1.0 \
         --zephyr-project-key PROJECT \
         --qtest-base-url https://yourcompany.qtestnet.com \
         --qtest-project-id 12345 \
         --db-path ./migration.db \
         --batch-size 50 \
         --max-workers 4

5. **Check migration status**:

   .. code-block:: bash

       ztoq migrate status --db-path ./migration.db --project-key PROJECT

Key Concepts
-----------

Understanding these key concepts will help you make the most of ZTOQ:

**ETL Pipeline**
  ZTOQ uses an ETL (Extract, Transform, Load) pipeline to migrate data. Each phase can be run separately or together.

**Entity Types**
  The main entity types are:
  
  - **Test Cases**: Core test definitions
  - **Test Cycles**: Groupings of test runs
  - **Test Executions**: Individual test run results
  - **Attachments**: Files attached to test entities
  - **Custom Fields**: User-defined metadata

**Storage Options**
  ZTOQ supports different storage backends:
  
  - **SQLite**: Simple file-based database (good for small migrations)
  - **PostgreSQL**: Powerful relational database (recommended for large migrations)

**Workflow Commands**
  For fine-grained control, ZTOQ provides workflow commands:
  
  - ``ztoq workflow extract``: Pull data from Zephyr Scale
  - ``ztoq workflow transform``: Convert data to qTest format
  - ``ztoq workflow load``: Push data to qTest
  - ``ztoq workflow validate``: Verify migration integrity

First Migration Walkthrough
-------------------------

Here's a step-by-step guide to running your first complete migration:

1. **Create a Configuration File**

   Create a file named `config.yaml` with the following content:

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
         type: sqlite
         path: ./migration.db
       
       performance:
         batch_size: 50
         max_workers: 4
       
       logging:
         level: INFO
         file: ztoq.log

2. **Initialize the Database**

   .. code-block:: bash

       ztoq db init --config config.yaml

3. **Extract Data from Zephyr Scale**

   .. code-block:: bash

       ztoq workflow extract --config config.yaml

   This command will:
   - Connect to Zephyr Scale API
   - Extract test cases, cycles, executions, etc.
   - Store the data in your database

4. **Transform the Data**

   .. code-block:: bash

       ztoq workflow transform --config config.yaml

   This command will:
   - Read the extracted data from the database
   - Convert it to qTest's data model
   - Handle custom fields and attachments
   - Store the transformed data in the database

5. **Load Data into qTest**

   .. code-block:: bash

       ztoq workflow load --config config.yaml

   This command will:
   - Connect to qTest API
   - Create test cases, cycles, executions, etc.
   - Upload attachments
   - Track created entities in the database

6. **Validate the Migration**

   .. code-block:: bash

       ztoq workflow validate --config config.yaml

   This command will:
   - Verify that all entities were correctly migrated
   - Check for data integrity
   - Generate a validation report

7. **Check Migration Status**

   .. code-block:: bash

       ztoq migrate status --config config.yaml

   This will show statistics about the migration:
   - Number of entities migrated
   - Success/failure counts
   - Duration and performance metrics

Common Use Cases
--------------

Here are some common scenarios and how to handle them with ZTOQ:

Running a Complete Migration
~~~~~~~~~~~~~~~~~~~~~~~~~~

For a one-time migration of all test data:

.. code-block:: bash

    ztoq migrate run --config config.yaml

Incremental Updates
~~~~~~~~~~~~~~~~~

For ongoing synchronization between systems:

.. code-block:: bash

    ztoq migrate run --config config.yaml --incremental true

Handling Custom Fields
~~~~~~~~~~~~~~~~~~~~

Map custom fields between systems:

1. Create a mapping file `custom_fields.yaml`:

   .. code-block:: yaml

       test_case:
         "Requirement ID": "Requirement"
         "Automation Status": "Automation"

2. Use it in your migration:

   .. code-block:: bash

       ztoq workflow transform --config config.yaml --custom-field-map custom_fields.yaml

Exporting Test Data Without Migration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To just extract and save test data:

.. code-block:: bash

    ztoq export-project z-openapi.yml \
      --base-url https://api.atlassian.com/ex/jira/your-instance/rest/zephyr/1.0 \
      --api-token YOUR_TOKEN \
      --project-key PROJECT \
      --output-dir ./zephyr-data \
      --format json

Next Steps
---------

Now that you understand the basics of ZTOQ, you can:

1. Learn more about the :doc:`usage` options
2. Explore the :doc:`cli-reference` for detailed command information
3. Read the :doc:`migration-workflow` guide for advanced migration scenarios
4. Check the :doc:`troubleshooting` guide if you encounter any issues

Need Help?
---------

If you run into problems:

1. Enable debug logging:

   .. code-block:: bash

       export ZTOQ_LOG_LEVEL=DEBUG
       ztoq --debug migrate run --config config.yaml

2. Check the log file for detailed information:

   .. code-block:: bash

       less ztoq.log

3. Refer to the :doc:`troubleshooting` guide for common issues and solutions

4. Open an issue on our GitHub repository if you need further assistance