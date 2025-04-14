"""
Fixtures package for the ZTOQ testing framework.

This package provides reusable fixtures and test data factories
to standardize the approach to testing throughout the project.
"""

# Export base fixtures
from tests.fixtures.base import (
    base_test_env,
    mock_env_vars,
    temp_dir,
    temp_file,
    temp_db_path,
    mock_response,
    mock_requests_session
)

# Export unit test fixtures
from tests.fixtures.unit import (
    mock_db_connection,
    mock_db_cursor,
    mock_file_system
)

# Export integration test fixtures
from tests.fixtures.integration import (
    sqlite_memory_engine,
    sqlite_memory_connection,
    sqlite_file_engine,
    mock_external_api,
    test_data_dir
)

# Export system test fixtures
from tests.fixtures.system import (
    skip_if_no_docker,
    docker_compose_env,
    cli_runner,
    run_cli_command
)

# Export factory base classes
from tests.fixtures.factories import (
    BaseFactory,
    DictFactory,
    ModelFactory,
    SQLAlchemyModelFactory
)

# Export model factories
from tests.fixtures.model_factories import (
    # Domain models
    OpenAPISpecFactory,

    # Zephyr models
    ProjectFactory,
    TestCaseFactory,
    TestCycleFactory,
    TestExecutionFactory,
    PriorityFactory,
    StatusFactory,
    CaseStepFactory,
    CustomFieldFactory,
    LinkFactory,
    AttachmentFactory,
    FolderFactory,
    EnvironmentFactory,
    ZephyrConfigFactory,

    # qTest models
    QTestConfigFactory,
    QTestProjectFactory,
    QTestTestCaseFactory,
    QTestTestCycleFactory,
    QTestTestRunFactory
)
