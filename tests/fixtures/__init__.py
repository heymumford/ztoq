"""
Fixtures package for the ZTOQ testing framework.

This package provides reusable fixtures and test data factories
to standardize the approach to testing throughout the project.
"""

# Export base fixtures
# Export API client fixtures
from tests.fixtures.api_clients import (
    mock_qtest_client,
    mock_response_factory,
    mock_zephyr_client,
    patch_qtest_client,
    patch_zephyr_client,
    qtest_client_with_mock_api,
    qtest_config,
    zephyr_client_with_mock_api,
    zephyr_config,
)
from tests.fixtures.base import (
    base_test_env,
    mock_env_vars,
    mock_requests_session,
    mock_response,
    temp_db_path,
    temp_dir,
    temp_file,
)

# Export database fixtures
from tests.fixtures.database import (
    concurrent_sessions,
    mock_sqlalchemy_engine,
    mock_sqlalchemy_session,
    populate_test_db,
    schema_tables,
    sqlalchemy_file_engine,
    sqlalchemy_file_session,
    sqlalchemy_memory_engine,
    sqlalchemy_memory_session,
    sqlite_test_db,
    transaction_fixture,
)

# Export factory base classes
from tests.fixtures.factories import BaseFactory, DictFactory, ModelFactory, SQLAlchemyModelFactory

# Export integration test fixtures
from tests.fixtures.integration import (
    mock_external_api,
    sqlite_file_engine,
    sqlite_memory_connection,
    sqlite_memory_engine,
    test_data_dir,
)

# Export API mocking fixtures
from tests.fixtures.mocks.conftest import (
    api_server,
    mock_both_apis,
    mock_both_clients,
    mock_qtest_api,
    mock_qtest_client,
    mock_zephyr_api,
    mock_zephyr_client,
)

# Export model factories
from tests.fixtures.model_factories import (
    AttachmentFactory,
    CaseStepFactory,
    CustomFieldFactory,
    EnvironmentFactory,
    FolderFactory,
    LinkFactory,
    # Domain models
    OpenAPISpecFactory,
    PriorityFactory,
    # Zephyr models
    ProjectFactory,
    # qTest models
    QTestConfigFactory,
    QTestProjectFactory,
    QTestTestCaseFactory,
    QTestTestCycleFactory,
    QTestTestRunFactory,
    StatusFactory,
    TestCaseFactory,
    TestCycleFactory,
    TestExecutionFactory,
    ZephyrConfigFactory,
)

# Export system test fixtures
from tests.fixtures.system import cli_runner, docker_compose_env, run_cli_command, skip_if_no_docker

# Export unit test fixtures
from tests.fixtures.unit import mock_db_connection, mock_db_cursor, mock_file_system
