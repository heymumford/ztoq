"""
Test configuration and fixtures for the ztoq project.

This file is the root pytest configuration file that sets up pytest
markers and imports fixtures from the fixtures modules to make them
available to all tests.
"""


# Import fixtures from the fixtures modules to make them available to all tests

# Import unit test fixtures

# Import integration test fixtures

# Import system test fixtures


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: mark a test as a unit test")
    config.addinivalue_line("markers", "integration: mark a test as an integration test")
    config.addinivalue_line("markers", "system: mark a test as a system test")
    config.addinivalue_line("markers", "docker: mark a test that requires Docker")
    config.addinivalue_line("markers", "api: mark a test that tests API functionality")
    config.addinivalue_line("markers", "db: mark a test that requires database access")
    config.addinivalue_line("markers", "cli: mark a test that tests CLI functionality")
    config.addinivalue_line("markers", "slow: mark a test that takes longer than average to run")
