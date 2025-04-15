Development
===========

Development Setup
-----------------

1. Clone the repository:

   .. code-block:: bash

       git clone https://github.com/yourusername/ztoq.git
       cd ztoq

2. Create and activate a virtual environment:

   .. code-block:: bash

       python -m venv venv
       source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install development dependencies:

   .. code-block:: bash

       pip install -e ".[dev]"

Project Management
------------------

The project is managed using a Kanban board approach, with tasks organized into different phases.

.. include:: kanban.rst

Maintenance
-----------

.. include:: maintenance.rst

Testing
-------

ZTOQ uses pytest for testing. To run the tests:

.. code-block:: bash

    pytest

To run tests with coverage:

.. code-block:: bash

    pytest --cov=ztoq tests/

Test-Driven Development
~~~~~~~~~~~~~~~~~~~~~~~

The project follows a strict TDD approach. For each new feature:

1. Write tests first (Red phase)
2. Implement the feature to make tests pass (Green phase)
3. Refactor while maintaining test coverage

For details, see :doc:`adrs/012-test-driven-development-approach`.

Code Style
----------

This project follows PEP 8 style guidelines. We use Black for formatting and flake8 for linting:

.. code-block:: bash

    black .
    flake8

Documentation
-------------

To build the documentation:

.. code-block:: bash

    cd docs/sphinx
    make html

The built documentation will be available in the ``docs/sphinx/build/html`` directory.

Documentation Standards
~~~~~~~~~~~~~~~~~~~~~~~

All documentation follows these standards:

1. Files are stored in the ``docs/`` directory
2. Files use kebab-case naming (e.g., ``custom-fields-attachments.md``)
3. Markdown is used for content, with RST for Sphinx integration

You can check documentation naming conventions with:

.. code-block:: bash

    python build.py docs-check

For comprehensive documentation guidelines, see our `Documentation Contribution Guide <../../docs-contribution-guide.html>`_.

Release Process
---------------

1. Update version in ``pyproject.toml``
2. Update ``CHANGELOG.md``
3. Create a git tag:

   .. code-block:: bash

       git tag -a v0.1.0 -m "Release version 0.1.0"
       git push origin v0.1.0

4. Build and publish to PyPI:

   .. code-block:: bash

       python -m build
       python -m twine upload dist/*