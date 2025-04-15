Installation
============

Requirements
-----------

* Python 3.8 or higher
* pip
* Poetry (recommended for development)

Quick Start
----------

For users who want to get started quickly:

.. code-block:: bash

    # Install from PyPI
    pip install ztoq

    # Verify installation
    ztoq --version

    # Show help
    ztoq --help

Installation Methods
-------------------

You can install ZTOQ using pip:

.. code-block:: bash

    pip install ztoq

Alternatively, you can install from source:

.. code-block:: bash

    git clone https://github.com/yourusername/ztoq.git
    cd ztoq
    pip install -e .

Using Poetry (Recommended for Development)
-----------------------------------------

For development purposes, we recommend using Poetry for dependency management:

.. code-block:: bash

    # Install Poetry if you haven't already
    pip install poetry
    
    # Clone the repository
    git clone https://github.com/yourusername/ztoq.git
    cd ztoq
    
    # Install dependencies with Poetry
    poetry install
    
    # Install with development dependencies
    poetry install --with dev
    
    # Run commands with Poetry
    poetry run ztoq --help

Development Setup
----------------

For a complete development environment:

.. code-block:: bash

    # Clone repository
    git clone https://github.com/yourusername/ztoq.git
    cd ztoq
    
    # Install with Poetry (recommended)
    poetry install --with dev
    
    # Setup pre-commit hooks
    poetry run pre-commit install
    
    # Run tests to verify environment
    poetry run pytest
    
    # Build documentation
    poetry run make -C docs/sphinx html

Docker Installation
------------------

You can also run ZTOQ in Docker:

.. code-block:: bash

    # Build the Docker image
    docker build -t ztoq -f config/Dockerfile .
    
    # Run with Docker
    docker run -it --rm ztoq --help
    
    # Run with Docker Compose (includes PostgreSQL database)
    docker-compose -f config/docker-compose.yml up

Configuration
------------

After installation, you should configure your API access tokens:

.. code-block:: bash

    # Set environment variables for API access
    export zephyr_access_token="your_zephyr_token"
    export qtest_bearer_token="your_qtest_token"
    
    # Verify tokens
    ztoq verify-tokens

Accessing Documentation
--------------------

After installation, you can easily access the complete documentation:

.. code-block:: bash

    # Build and serve documentation in your web browser
    ztoq docs serve
    
    # Specify a custom port (default is 8000)
    ztoq docs serve --port 8080
    
    # Build documentation without opening a browser
    ztoq docs serve --no-browser
    
    # Choose a different format (html, dirhtml, singlehtml)
    ztoq docs serve --format dirhtml

The documentation server will start and automatically open your default web browser to display the documentation.

Next Steps
---------

Once installed, you can:

1. Read the :doc:`usage` guide to learn how to use the CLI
2. Check the :doc:`development` guide for contributing to the project
3. Learn about the :doc:`architecture` of ZTOQ
4. Use ``ztoq docs serve`` to view the complete documentation in your browser