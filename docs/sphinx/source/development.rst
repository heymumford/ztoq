Development
===========

Development Setup
----------------

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

Testing
-------

ZTOQ uses pytest for testing. To run the tests:

.. code-block:: bash

    pytest

To run tests with coverage:

.. code-block:: bash

    pytest --cov=ztoq tests/

Code Style
----------

This project follows PEP 8 style guidelines. We use ruff for linting and formatting:

.. code-block:: bash

    ruff check .
    ruff format .

Documentation
------------

To build the documentation:

.. code-block:: bash

    cd docs/sphinx
    make html

The built documentation will be available in the ``docs/sphinx/build/html`` directory.

Release Process
--------------

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