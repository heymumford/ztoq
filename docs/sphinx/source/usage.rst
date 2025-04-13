Usage
=====

Basic Usage
----------

ZTOQ can be used both as a command-line tool and as a Python library.

Command Line Interface
---------------------

To use ZTOQ from the command line:

.. code-block:: bash

    # Initialize a new configuration
    ztoq init --api-token YOUR_TOKEN --base-url https://api.example.com

    # Import data from Zephyr Scale
    ztoq import --project-key PROJECT_KEY --output-dir ./data

    # Show available options
    ztoq --help

Python API
---------

You can also use ZTOQ as a library in your Python code:

.. code-block:: python

    from ztoq.zephyr_client import ZephyrClient
    from ztoq.models import ZephyrConfig
    from ztoq.database_manager import DatabaseManager
    from pathlib import Path

    # Create a configuration
    config = ZephyrConfig(
        base_url="https://api.example.com",
        api_token="YOUR_TOKEN",
        project_key="PROJECT_KEY"
    )

    # Create a client
    client = ZephyrClient(config)

    # Initialize database
    db_manager = DatabaseManager(Path("./data/zephyr.db"))
    db_manager.initialize_database()

    # Fetch and save project data
    projects = client.get_projects()
    for project in projects:
        db_manager.save_project(project)

Configuration
------------

ZTOQ can be configured through:

1. Command-line arguments
2. Environment variables
3. Configuration file

Example configuration file (`config.yaml`):

.. code-block:: yaml

    zephyr:
      base_url: https://api.example.com
      api_token: YOUR_TOKEN
      project_key: PROJECT_KEY
    
    storage:
      type: sqlite  # or json
      path: ./data/zephyr.db