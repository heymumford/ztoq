"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import json
import os
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from ztoq.core.db_manager import DatabaseConfig, SQLDatabaseManager
from ztoq.core.db_models import (
    Attachment,
    CustomFieldDefinition,
    CustomFieldValue,
    EntityType,
    Environment,
    Folder,
    Link,
    Priority,
    Project,
    Status,
    TestCase,
    TestCycle,
    TestExecution,
)
from ztoq.data_fetcher import FetchResult
from ztoq.models import (
    Attachment as AttachmentModel,
)
from ztoq.models import (
    Case as CaseModel,
)
from ztoq.models import (
    CaseStep as CaseStepModel,
)
from ztoq.models import (
    CustomField as CustomFieldModel,
)
from ztoq.models import (
    CycleInfo as CycleInfoModel,
)
from ztoq.models import (
    Environment as EnvironmentModel,
)
from ztoq.models import (
    Execution as ExecutionModel,
)
from ztoq.models import (
    Folder as FolderModel,
)
from ztoq.models import (
    Link as LinkModel,
)
from ztoq.models import (
    Priority as PriorityModel,
)
from ztoq.models import (
    Project as ProjectModel,
)
from ztoq.models import (
    Status as StatusModel,
)


@pytest.mark.unit()
class TestSQLDatabaseManager:
    @pytest.fixture()
    def db_config(self):
        """Create a database configuration for testing with SQLite."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_db.sqlite")
            config = DatabaseConfig(db_type="sqlite", db_path=db_path, echo=False)
            yield config

    @pytest.fixture()
    def db_manager(self, db_config):
        """Create a SQLDatabaseManager instance for testing."""
        manager = SQLDatabaseManager(config=db_config)
        manager.initialize_database()
        return manager

    @pytest.fixture()
    def test_project(self):
        """Create a test project model."""
        return ProjectModel(
            id="PRJ-123", key="TEST", name="Test Project", description="This is a test project"
        )

    @pytest.fixture()
    def test_folder(self):
        """Create a test folder model."""
        return FolderModel(
            id="FOLD-123", name="Test Folder", folderType="TEST_CASE", projectKey="TEST"
        )

    @pytest.fixture()
    def test_status(self):
        """Create a test status model."""
        return StatusModel(
            id="STAT-123",
            name="Active",
            description="Active status",
            color="#00FF00",
            type="TEST_CASE",
        )

    @pytest.fixture()
    def test_priority(self):
        """Create a test priority model."""
        return PriorityModel(
            id="PRI-123", name="High", description="High priority", color="#FF0000", rank=1
        )

    @pytest.fixture()
    def test_environment(self):
        """Create a test environment model."""
        return EnvironmentModel(
            id="ENV-123", name="Production", description="Production environment"
        )

    def test_initialization(self, db_config):
        """Test database manager initialization."""
        manager = SQLDatabaseManager(config=db_config)

        # Check engine is created
        assert manager._engine is not None

        # Check session factory is created
        assert manager._session_factory is not None

        # Check scoped session is created
        assert manager._scoped_session is not None

        # Check config is set correctly
        assert manager.config == db_config

    def test_create_engine(self, db_config):
        """Test engine creation with different database types."""
        # Test SQLite engine creation
        sqlite_manager = SQLDatabaseManager(config=db_config)
        assert sqlite_manager._engine is not None
        assert sqlite_manager._engine.name == "sqlite"

        # Test PostgreSQL engine creation with mocked connection string
        pg_config = DatabaseConfig(
            db_type="postgresql",
            host="localhost",
            port=5432,
            username="test_user",
            password="test_password",
            database="test_db",
            pool_size=10,
            max_overflow=20,
        )

        # Mock create_engine to avoid actual connection
        with patch("ztoq.core.db_manager.create_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine

            SQLDatabaseManager(config=pg_config)

            # Verify engine was created with the right parameters
            mock_create_engine.assert_called_once()
            args, kwargs = mock_create_engine.call_args

            # Check PostgreSQL connection string format
            assert "postgresql://" in args[0]
            assert "test_user:test_password@localhost:5432/test_db" in args[0]

            # Check pool settings
            assert kwargs["poolclass"] is not None
            assert kwargs["pool_size"] == 10
            assert kwargs["max_overflow"] == 20
            assert kwargs["pool_pre_ping"] is True

    def test_get_session_context_manager(self, db_manager):
        """Test the session context manager."""
        # Test normal operation
        with db_manager.get_session() as session:
            # Perform a simple query
            session.query(Project).all()

            # Session should be usable
            assert session.is_active

        # Test exception handling and rollback
        with patch("sqlalchemy.orm.Session.commit") as mock_commit:
            mock_commit.side_effect = SQLAlchemyError("Test error")

            with pytest.raises(SQLAlchemyError), db_manager.get_session() as session:
                # Add a project
                project = Project(id="test", key="TEST", name="Test")
                session.add(project)
                # The commit will fail, triggering rollback

            # Verify commit was called (and failed)
            mock_commit.assert_called_once()

    def test_initialize_database(self, db_config):
        """Test database initialization creates the schema."""
        manager = SQLDatabaseManager(config=db_config)

        # Initialize the database
        manager.initialize_database()

        # Verify tables were created by querying metadata
        inspector = manager._engine.inspect()
        table_names = inspector.get_table_names()

        # Check essential tables exist
        essential_tables = [
            "projects",
            "folders",
            "test_cases",
            "test_cycles",
            "test_steps",
            "test_executions",
            "custom_field_definitions",
            "custom_field_values",
            "attachments",
            "migration_state",
            "entity_batch_state",
        ]

        for table in essential_tables:
            assert table in table_names

    def test_drop_all_tables(self, db_manager):
        """Test dropping all tables."""
        # First verify tables exist
        inspector = db_manager._engine.inspect()
        initial_tables = inspector.get_table_names()
        assert len(initial_tables) > 0

        # Drop tables
        db_manager.drop_all_tables()

        # Verify tables were dropped
        inspector = db_manager._engine.inspect()
        remaining_tables = inspector.get_table_names()
        assert len(remaining_tables) == 0

    def test_get_or_create(self, db_manager):
        """Test get_or_create method with new and existing objects."""
        with db_manager.get_session() as session:
            # Test creating a new object
            project, created = db_manager.get_or_create(
                session,
                Project,
                create_kwargs={"id": "PRJ-123", "key": "TEST", "name": "Test Project"},
                key="TEST",
            )

            assert created is True
            assert project.id == "PRJ-123"
            assert project.key == "TEST"

            # Test retrieving an existing object
            same_project, created = db_manager.get_or_create(
                session,
                Project,
                create_kwargs={"id": "DIFFERENT", "key": "TEST", "name": "Different Name"},
                key="TEST",
            )

            assert created is False
            assert same_project.id == "PRJ-123"  # Original ID, not the new one
            assert same_project.name == "Test Project"  # Original name

            # Test race condition handling (simulate an integrity error)
            with patch.object(session, "flush") as mock_flush:
                mock_flush.side_effect = IntegrityError("Test error", None, None)

                # Also patch the query to return a result on second attempt
                original_query = session.query
                mock_query_result = MagicMock()
                mock_query_result.filter_by.return_value.first.return_value = project

                def mock_query_func(*args):
                    # Return a mocked result on second call
                    session.query = mock_query_result
                    return original_query(*args)

                with patch.object(session, "query", side_effect=mock_query_func):
                    with patch.object(session, "rollback"):
                        race_project, created = db_manager.get_or_create(
                            session,
                            Project,
                            create_kwargs={"id": "PRJ-456", "key": "RACE", "name": "Race Project"},
                            key="RACE",
                        )

                        assert created is False
                        assert race_project == project

    def test_save_project(self, db_manager, test_project):
        """Test saving a project."""
        # Save the project
        db_manager.save_project(test_project)

        # Verify the project was saved
        with db_manager.get_session() as session:
            saved_project = session.query(Project).filter_by(id=test_project.id).first()

            assert saved_project is not None
            assert saved_project.id == test_project.id
            assert saved_project.key == test_project.key
            assert saved_project.name == test_project.name
            assert saved_project.description == test_project.description

            # Test updating an existing project
            test_project.name = "Updated Project"
            db_manager.save_project(test_project)

            session.refresh(saved_project)
            assert saved_project.name == "Updated Project"

    def test_save_folder(self, db_manager, test_project, test_folder):
        """Test saving a folder."""
        # First save the project for foreign key constraint
        db_manager.save_project(test_project)

        # Save the folder
        db_manager.save_folder(test_folder, test_project.key)

        # Verify the folder was saved
        with db_manager.get_session() as session:
            saved_folder = session.query(Folder).filter_by(id=test_folder.id).first()

            assert saved_folder is not None
            assert saved_folder.id == test_folder.id
            assert saved_folder.name == test_folder.name
            assert saved_folder.folder_type == test_folder.folderType
            assert saved_folder.project_key == test_project.key

            # Test updating an existing folder
            test_folder.name = "Updated Folder"
            db_manager.save_folder(test_folder, test_project.key)

            session.refresh(saved_folder)
            assert saved_folder.name == "Updated Folder"

    def test_save_status(self, db_manager, test_project, test_status):
        """Test saving a status."""
        # First save the project for foreign key constraint
        db_manager.save_project(test_project)

        # Save the status
        db_manager.save_status(test_status, test_project.key)

        # Verify the status was saved
        with db_manager.get_session() as session:
            saved_status = session.query(Status).filter_by(id=test_status.id).first()

            assert saved_status is not None
            assert saved_status.id == test_status.id
            assert saved_status.name == test_status.name
            assert saved_status.description == test_status.description
            assert saved_status.color == test_status.color
            assert saved_status.type == test_status.type
            assert saved_status.project_key == test_project.key

    def test_save_priority(self, db_manager, test_project, test_priority):
        """Test saving a priority."""
        # First save the project for foreign key constraint
        db_manager.save_project(test_project)

        # Save the priority
        db_manager.save_priority(test_priority, test_project.key)

        # Verify the priority was saved
        with db_manager.get_session() as session:
            saved_priority = session.query(Priority).filter_by(id=test_priority.id).first()

            assert saved_priority is not None
            assert saved_priority.id == test_priority.id
            assert saved_priority.name == test_priority.name
            assert saved_priority.description == test_priority.description
            assert saved_priority.color == test_priority.color
            assert saved_priority.rank == test_priority.rank
            assert saved_priority.project_key == test_project.key

    def test_save_environment(self, db_manager, test_project, test_environment):
        """Test saving an environment."""
        # First save the project for foreign key constraint
        db_manager.save_project(test_project)

        # Save the environment
        db_manager.save_environment(test_environment, test_project.key)

        # Verify the environment was saved
        with db_manager.get_session() as session:
            saved_environment = session.query(Environment).filter_by(id=test_environment.id).first()

            assert saved_environment is not None
            assert saved_environment.id == test_environment.id
            assert saved_environment.name == test_environment.name
            assert saved_environment.description == test_environment.description
            assert saved_environment.project_key == test_project.key

    def test_save_custom_fields(self, db_manager, test_project):
        """Test saving custom fields."""
        # First save the project for foreign key constraint
        db_manager.save_project(test_project)

        with db_manager.get_session() as session:
            # Test saving custom fields
            custom_fields = [
                CustomFieldModel(id="CF-1", name="Test Type", type="text", value="Integration"),
                CustomFieldModel(id="CF-2", name="Component", type="dropdown", value="Login"),
                CustomFieldModel(id="CF-3", name="Is Automated", type="checkbox", value=True),
                CustomFieldModel(id="CF-4", name="Due Date", type="date", value="2025-05-01"),
                CustomFieldModel(
                    id="CF-5", name="Tags", type="multipleSelect", value=["api", "regression"]
                ),
            ]

            db_manager._save_custom_fields(
                session=session,
                custom_fields=custom_fields,
                entity_type=EntityType.TEST_CASE,
                entity_id="TC-123",
                project_key=test_project.key,
            )

            # Verify custom field definitions were created
            field_defs = session.query(CustomFieldDefinition).all()
            assert len(field_defs) == 5

            # Verify custom field values were created
            values = session.query(CustomFieldValue).all()
            assert len(values) == 5

            # Check specific value types
            text_value = session.query(CustomFieldValue).filter_by(field_id="CF-1").first()
            assert text_value.value_text == "Integration"

            bool_value = session.query(CustomFieldValue).filter_by(field_id="CF-3").first()
            assert bool_value.value_boolean is True

            # Test JSON value for array
            json_value = session.query(CustomFieldValue).filter_by(field_id="CF-5").first()
            assert json_value.value_json is not None
            assert json.loads(json_value.value_json) == ["api", "regression"]

    def test_save_links(self, db_manager):
        """Test saving links."""
        links = [
            LinkModel(
                id="LINK-1",
                name="Requirements",
                url="https://example.com/req",
                description="Requirements document",
                type="web",
            ),
            LinkModel(
                id="LINK-2",
                name="Issue",
                url="https://example.com/issue/123",
                description="Related issue",
                type="issue",
            ),
        ]

        with db_manager.get_session() as session:
            # Save links
            db_manager._save_links(
                session=session, links=links, entity_type=EntityType.TEST_CASE, entity_id="TC-123"
            )

            # Verify links were saved
            saved_links = (
                session.query(Link)
                .filter_by(entity_type=EntityType.TEST_CASE, entity_id="TC-123")
                .all()
            )

            assert len(saved_links) == 2
            assert saved_links[0].name == "Requirements"
            assert saved_links[1].name == "Issue"

            # Test links are replaced when saving again
            new_links = [
                LinkModel(id="LINK-3", name="New Link", url="https://example.com/new", type="web")
            ]

            db_manager._save_links(
                session=session,
                links=new_links,
                entity_type=EntityType.TEST_CASE,
                entity_id="TC-123",
            )

            updated_links = (
                session.query(Link)
                .filter_by(entity_type=EntityType.TEST_CASE, entity_id="TC-123")
                .all()
            )

            assert len(updated_links) == 1
            assert updated_links[0].name == "New Link"

    def test_save_attachments(self, db_manager):
        """Test saving attachments."""
        # Create test attachments
        attachments = [
            AttachmentModel(
                id="ATT-1",
                filename="screenshot.png",
                content_type="image/png",
                size=1024,
                created_on=datetime.now(),
                created_by="user1",
                content="c2ltdWxhdGVkIGJpbmFyeSBkYXRh",  # base64 encoded "simulated binary data"
            )
        ]

        with db_manager.get_session() as session:
            # Save attachments
            db_manager._save_attachments(
                session=session,
                attachments=attachments,
                entity_type=EntityType.TEST_EXECUTION,
                entity_id="EXEC-123",
            )

            # Verify attachments were saved
            saved_attachments = (
                session.query(Attachment)
                .filter_by(entity_type=EntityType.TEST_EXECUTION, entity_id="EXEC-123")
                .all()
            )

            assert len(saved_attachments) == 1
            assert saved_attachments[0].filename == "screenshot.png"
            assert saved_attachments[0].content_type == "image/png"
            assert saved_attachments[0].size == 1024
            assert saved_attachments[0].content is not None  # Binary content should be decoded

            # Test updating existing attachment
            updated_attachments = [
                AttachmentModel(
                    id="ATT-1",  # Same ID as before
                    filename="updated_screenshot.png",
                    content_type="image/png",
                    size=2048,
                    created_on=datetime.now(),
                    created_by="user1",
                    content="dXBkYXRlZCBiaW5hcnkgZGF0YQ==",  # "updated binary data"
                )
            ]

            db_manager._save_attachments(
                session=session,
                attachments=updated_attachments,
                entity_type=EntityType.TEST_EXECUTION,
                entity_id="EXEC-123",
            )

            # Verify attachment was updated
            updated_attachment = session.query(Attachment).filter_by(id="ATT-1").first()
            assert updated_attachment.filename == "updated_screenshot.png"
            assert updated_attachment.size == 2048

    def test_get_or_create_labels(self, db_manager):
        """Test getting or creating labels."""
        with db_manager.get_session() as session:
            # Test creating new labels
            labels = db_manager._get_or_create_labels(
                session=session, labels=["Regression", "Smoke", "API"]
            )

            assert len(labels) == 3
            label_names = [label.name for label in labels]
            assert "Regression" in label_names
            assert "Smoke" in label_names
            assert "API" in label_names

            # Test getting existing labels
            same_labels = db_manager._get_or_create_labels(
                session=session, labels=["Regression", "Smoke", "Performance"]
            )

            assert len(same_labels) == 3
            # The first two should be the same objects
            assert same_labels[0].id == labels[0].id or same_labels[0].id == labels[1].id
            assert same_labels[1].id == labels[0].id or same_labels[1].id == labels[1].id
            # The third should be new
            assert same_labels[2].name == "Performance"

    def test_save_test_case(self, db_manager, test_project, test_folder, test_priority):
        """Test saving a test case."""
        # First save the project, folder, and priority for foreign key constraints
        db_manager.save_project(test_project)
        db_manager.save_folder(test_folder, test_project.key)
        db_manager.save_priority(test_priority, test_project.key)

        # Create test case model
        test_case = CaseModel(
            id="TC-123",
            key="TEST-1",
            name="Login Test",
            objective="Verify user login functionality",
            precondition="User exists in system",
            description="Test the login functionality",
            status="Active",
            priority=test_priority,
            priority_name="High",
            folder=test_folder.id,
            folder_name=test_folder.name,
            owner="user1",
            owner_name="Test User",
            created_on=datetime.now(),
            created_by="user1",
            labels=["Regression", "Smoke"],
            steps=[
                CaseStepModel(
                    index=0,
                    description="Navigate to login page",
                    expected_result="Login page displayed",
                ),
                CaseStepModel(
                    index=1,
                    description="Enter credentials and submit",
                    expected_result="User logged in successfully",
                ),
            ],
            custom_fields=[
                CustomFieldModel(id="CF-1", name="Test Type", type="text", value="Integration")
            ],
            links=[LinkModel(name="Requirements", url="https://example.com/req", type="web")],
            attachments=[],
            scripts=[],
        )

        # Save test case
        db_manager.save_test_case(test_case, test_project.key)

        # Verify test case was saved
        with db_manager.get_session() as session:
            saved_case = session.query(TestCase).filter_by(id=test_case.id).first()

            assert saved_case is not None
            assert saved_case.key == "TEST-1"
            assert saved_case.name == "Login Test"
            assert saved_case.objective == "Verify user login functionality"
            assert saved_case.precondition == "User exists in system"
            assert saved_case.priority_id == test_priority.id
            assert saved_case.folder_id == test_folder.id

            # Verify steps
            assert len(saved_case.steps) == 2
            assert saved_case.steps[0].description == "Navigate to login page"
            assert saved_case.steps[1].description == "Enter credentials and submit"

            # Verify labels
            assert len(saved_case.labels) == 2
            label_names = [label.name for label in saved_case.labels]
            assert "Regression" in label_names
            assert "Smoke" in label_names

            # Verify custom fields
            custom_fields = (
                session.query(CustomFieldValue)
                .filter_by(entity_type=EntityType.TEST_CASE, entity_id=test_case.id)
                .all()
            )
            assert len(custom_fields) == 1
            assert custom_fields[0].value_text == "Integration"

            # Verify links
            links = (
                session.query(Link)
                .filter_by(entity_type=EntityType.TEST_CASE, entity_id=test_case.id)
                .all()
            )
            assert len(links) == 1
            assert links[0].name == "Requirements"

            # Test updating existing test case
            test_case.name = "Updated Login Test"
            test_case.status = "Ready"
            test_case.steps = [
                CaseStepModel(index=0, description="Updated step", expected_result="Updated result")
            ]

            db_manager.save_test_case(test_case, test_project.key)

            session.refresh(saved_case)
            assert saved_case.name == "Updated Login Test"
            assert saved_case.status == "Ready"
            assert len(saved_case.steps) == 1
            assert saved_case.steps[0].description == "Updated step"

    def test_save_test_cycle(self, db_manager, test_project, test_folder):
        """Test saving a test cycle."""
        # First save the project and folder for foreign key constraints
        db_manager.save_project(test_project)
        test_folder.folderType = "TEST_CYCLE"  # Update folder type
        db_manager.save_folder(test_folder, test_project.key)

        # Create test cycle model
        test_cycle = CycleInfoModel(
            id="CYCLE-123",
            key="TEST-C1",
            name="Sprint 1 Testing",
            description="Test cycle for Sprint 1",
            status="Active",
            status_name="Active",
            folder=test_folder.id,
            folder_name=test_folder.name,
            owner="user1",
            owner_name="Test User",
            created_on=datetime.now(),
            created_by="user1",
            project_key=test_project.key,
            custom_fields=[
                CustomFieldModel(id="CF-1", name="Sprint", type="text", value="Sprint 1")
            ],
            links=[LinkModel(name="Sprint Board", url="https://example.com/sprint1", type="web")],
            attachments=[],
        )

        # Save test cycle
        db_manager.save_test_cycle(test_cycle, test_project.key)

        # Verify test cycle was saved
        with db_manager.get_session() as session:
            saved_cycle = session.query(TestCycle).filter_by(id=test_cycle.id).first()

            assert saved_cycle is not None
            assert saved_cycle.key == "TEST-C1"
            assert saved_cycle.name == "Sprint 1 Testing"
            assert saved_cycle.description == "Test cycle for Sprint 1"
            assert saved_cycle.status == "Active"
            assert saved_cycle.folder_id == test_folder.id

            # Verify custom fields
            custom_fields = (
                session.query(CustomFieldValue)
                .filter_by(entity_type=EntityType.TEST_CYCLE, entity_id=test_cycle.id)
                .all()
            )
            assert len(custom_fields) == 1
            assert custom_fields[0].value_text == "Sprint 1"

            # Verify links
            links = (
                session.query(Link)
                .filter_by(entity_type=EntityType.TEST_CYCLE, entity_id=test_cycle.id)
                .all()
            )
            assert len(links) == 1
            assert links[0].name == "Sprint Board"

    def test_save_test_execution(self, db_manager, test_project):
        """Test saving a test execution."""
        # First save the project for foreign key constraints
        db_manager.save_project(test_project)

        # Create test case, cycle, and environment
        test_case = CaseModel(
            id="TC-123", key="TEST-1", name="Login Test", project_key=test_project.key
        )
        db_manager.save_test_case(test_case, test_project.key)

        test_cycle = CycleInfoModel(
            id="CYCLE-123", key="TEST-C1", name="Sprint 1 Testing", project_key=test_project.key
        )
        db_manager.save_test_cycle(test_cycle, test_project.key)

        test_environment = EnvironmentModel(id="ENV-123", name="Production")
        db_manager.save_environment(test_environment, test_project.key)

        # Create test execution model
        test_execution = ExecutionModel(
            id="EXEC-123",
            testCaseKey="TEST-1",
            cycleId="CYCLE-123",
            cycle_name="Sprint 1 Testing",
            status="PASS",
            status_name="Passed",
            environment="ENV-123",
            environment_name="Production",
            executed_by="user1",
            executed_by_name="Test User",
            executed_on=datetime.now(),
            created_on=datetime.now(),
            created_by="user1",
            comment="Test passed with no issues",
            steps=[
                CaseStepModel(
                    index=0,
                    description="Navigate to login page",
                    expected_result="Login page displayed",
                    actual_result="Login page displayed correctly",
                    status="PASS",
                )
            ],
            custom_fields=[
                CustomFieldModel(id="CF-1", name="Browser", type="text", value="Chrome")
            ],
            attachments=[],
            links=[],
        )

        # Save test execution
        db_manager.save_test_execution(test_execution, test_project.key)

        # Verify test execution was saved
        with db_manager.get_session() as session:
            saved_execution = session.query(TestExecution).filter_by(id=test_execution.id).first()

            assert saved_execution is not None
            assert saved_execution.test_case_key == "TEST-1"
            assert saved_execution.cycle_id == "CYCLE-123"
            assert saved_execution.status == "PASS"
            assert saved_execution.environment_id == "ENV-123"
            assert saved_execution.comment == "Test passed with no issues"

            # Verify steps
            assert len(saved_execution.steps) == 1
            assert saved_execution.steps[0].description == "Navigate to login page"
            assert saved_execution.steps[0].actual_result == "Login page displayed correctly"
            assert saved_execution.steps[0].status == "PASS"

            # Verify custom fields
            custom_fields = (
                session.query(CustomFieldValue)
                .filter_by(entity_type=EntityType.TEST_EXECUTION, entity_id=test_execution.id)
                .all()
            )
            assert len(custom_fields) == 1
            assert custom_fields[0].value_text == "Chrome"

    def test_save_project_data(self, db_manager, test_project):
        """Test saving all project data from fetch results."""
        # Create sample data
        folders = [
            FolderModel(id="FOLD-1", name="Test Cases", folderType="TEST_CASE", projectKey="TEST"),
            FolderModel(
                id="FOLD-2", name="Test Cycles", folderType="TEST_CYCLE", projectKey="TEST"
            ),
        ]

        statuses = [
            StatusModel(id="STAT-1", name="Passed", type="TEST_EXECUTION"),
            StatusModel(id="STAT-2", name="Failed", type="TEST_EXECUTION"),
        ]

        priorities = [
            PriorityModel(id="PRI-1", name="High", rank=1),
            PriorityModel(id="PRI-2", name="Medium", rank=2),
        ]

        environments = [
            EnvironmentModel(id="ENV-1", name="Production"),
            EnvironmentModel(id="ENV-2", name="Staging"),
        ]

        test_cases = [
            CaseModel(id="TC-1", key="TEST-1", name="Test Login", folder="FOLD-1"),
            CaseModel(id="TC-2", key="TEST-2", name="Test Logout", folder="FOLD-1"),
        ]

        test_cycles = [
            CycleInfoModel(
                id="CYCLE-1",
                key="TEST-C1",
                name="Sprint 1 Testing",
                project_key="TEST",
                folder="FOLD-2",
            )
        ]

        test_executions = [
            ExecutionModel(
                id="EXEC-1",
                testCaseKey="TEST-1",
                cycleId="CYCLE-1",
                status="PASS",
                environment="ENV-1",
            )
        ]

        # Create fetch results
        fetch_results = {
            "project": FetchResult(
                entity_type="project",
                project_key="TEST",
                items=[test_project],
                count=1,
                success=True,
            ),
            "folders": FetchResult(
                entity_type="folders",
                project_key="TEST",
                items=folders,
                count=len(folders),
                success=True,
            ),
            "statuses": FetchResult(
                entity_type="statuses",
                project_key="TEST",
                items=statuses,
                count=len(statuses),
                success=True,
            ),
            "priorities": FetchResult(
                entity_type="priorities",
                project_key="TEST",
                items=priorities,
                count=len(priorities),
                success=True,
            ),
            "environments": FetchResult(
                entity_type="environments",
                project_key="TEST",
                items=environments,
                count=len(environments),
                success=True,
            ),
            "test_cases": FetchResult(
                entity_type="test_cases",
                project_key="TEST",
                items=test_cases,
                count=len(test_cases),
                success=True,
            ),
            "test_cycles": FetchResult(
                entity_type="test_cycles",
                project_key="TEST",
                items=test_cycles,
                count=len(test_cycles),
                success=True,
            ),
            "test_executions": FetchResult(
                entity_type="test_executions",
                project_key="TEST",
                items=test_executions,
                count=len(test_executions),
                success=True,
            ),
        }

        # Save all project data
        result = db_manager.save_project_data("TEST", fetch_results)

        # Verify counts
        assert result["project"] == 1
        assert result["folders"] == 2
        assert result["statuses"] == 2
        assert result["priorities"] == 2
        assert result["environments"] == 2
        assert result["test_cases"] == 2
        assert result["test_cycles"] == 1
        assert result["test_executions"] == 1

        # Verify data was saved correctly
        with db_manager.get_session() as session:
            assert session.query(Project).count() == 1
            assert session.query(Folder).count() == 2
            assert session.query(TestCase).count() == 2
            assert session.query(TestCycle).count() == 1
            assert session.query(TestExecution).count() == 1

    def test_save_project_data_with_placeholder(self, db_manager):
        """Test saving project data when no project is provided."""
        # Create sample data without project
        test_cases = [CaseModel(id="TC-1", key="TEST-1", name="Test Login")]

        # Create fetch results without project
        fetch_results = {
            "test_cases": FetchResult(
                entity_type="test_cases",
                project_key="TEST",
                items=test_cases,
                count=len(test_cases),
                success=True,
            )
        }

        # Save project data
        result = db_manager.save_project_data("TEST", fetch_results)

        # Verify placeholder project was created
        assert result["project"] == 1
        assert result["test_cases"] == 1

        with db_manager.get_session() as session:
            project = session.query(Project).filter_by(key="TEST").first()
            assert project is not None
            assert "Placeholder" in project.description

    def test_save_all_projects_data(self, db_manager):
        """Test saving data for multiple projects."""
        # Create projects
        project1 = ProjectModel(id="PRJ-1", key="PROJ1", name="Project 1")
        project2 = ProjectModel(id="PRJ-2", key="PROJ2", name="Project 2")

        # Create test cases for each project
        test_cases1 = [CaseModel(id="TC-1", key="PROJ1-1", name="Test 1 for Project 1")]

        test_cases2 = [
            CaseModel(id="TC-2", key="PROJ2-1", name="Test 1 for Project 2"),
            CaseModel(id="TC-3", key="PROJ2-2", name="Test 2 for Project 2"),
        ]

        # Create fetch results for each project
        project1_results = {
            "project": FetchResult(
                entity_type="project", project_key="PROJ1", items=[project1], count=1, success=True
            ),
            "test_cases": FetchResult(
                entity_type="test_cases",
                project_key="PROJ1",
                items=test_cases1,
                count=len(test_cases1),
                success=True,
            ),
        }

        project2_results = {
            "project": FetchResult(
                entity_type="project", project_key="PROJ2", items=[project2], count=1, success=True
            ),
            "test_cases": FetchResult(
                entity_type="test_cases",
                project_key="PROJ2",
                items=test_cases2,
                count=len(test_cases2),
                success=True,
            ),
        }

        all_projects_data = {"PROJ1": project1_results, "PROJ2": project2_results}

        # Mock initialize_database to verify it's called once
        with patch.object(db_manager, "initialize_database") as mock_init_db:
            results = db_manager.save_all_projects_data(all_projects_data)

            # Check initialize_database was called once
            mock_init_db.assert_called_once()

            # Check results contain correct counts
            assert results["PROJ1"]["project"] == 1
            assert results["PROJ1"]["test_cases"] == 1
            assert results["PROJ2"]["project"] == 1
            assert results["PROJ2"]["test_cases"] == 2

        # Verify data was saved
        with db_manager.get_session() as session:
            assert session.query(Project).count() == 2
            assert session.query(TestCase).count() == 3

    def test_migration_state_methods(self, db_manager):
        """Test migration state methods."""
        # Create initial migration state
        state = db_manager.update_migration_state(
            project_key="TEST", extraction_status="in_progress"
        )

        assert state is not None
        assert state.project_key == "TEST"
        assert state.extraction_status == "in_progress"
        assert state.transformation_status == "not_started"
        assert state.loading_status == "not_started"

        # Update migration state
        updated_state = db_manager.update_migration_state(
            project_key="TEST",
            extraction_status="completed",
            transformation_status="in_progress",
            metadata={"extracted_items": 100},
        )

        assert updated_state.extraction_status == "completed"
        assert updated_state.transformation_status == "in_progress"
        assert "extracted_items" in updated_state.metadata_dict

        # Get migration state
        retrieved_state = db_manager.get_migration_state("TEST")
        assert retrieved_state is not None
        assert retrieved_state.extraction_status == "completed"
        assert retrieved_state.transformation_status == "in_progress"

        # Test non-existent state
        non_existent = db_manager.get_migration_state("NONEXISTENT")
        assert non_existent is None

    def test_entity_batch_state_methods(self, db_manager):
        """Test entity batch state methods."""
        # Create entity batch state
        batch = db_manager.create_entity_batch_state(
            project_key="TEST",
            entity_type="test_case",
            batch_number=1,
            total_batches=5,
            items_count=100,
            status="not_started",
        )

        assert batch is not None
        assert batch.project_key == "TEST"
        assert batch.entity_type == "test_case"
        assert batch.batch_number == 1
        assert batch.total_batches == 5
        assert batch.items_count == 100
        assert batch.status == "not_started"

        # Update batch state
        updated_batch = db_manager.update_entity_batch_state(
            project_key="TEST",
            entity_type="test_case",
            batch_number=1,
            status="in_progress",
            processed_count=50,
        )

        assert updated_batch is not None
        assert updated_batch.status == "in_progress"
        assert updated_batch.processed_count == 50

        # Complete batch
        completed_batch = db_manager.update_entity_batch_state(
            project_key="TEST",
            entity_type="test_case",
            batch_number=1,
            status="completed",
            processed_count=100,
        )

        assert completed_batch is not None
        assert completed_batch.status == "completed"
        assert completed_batch.processed_count == 100
        assert completed_batch.completed_at is not None

        # Get incomplete batches (should be empty now)
        incomplete = db_manager.get_incomplete_batches("TEST")
        assert len(incomplete) == 0

        # Create another batch that's not complete
        db_manager.create_entity_batch_state(
            project_key="TEST",
            entity_type="test_cycle",
            batch_number=1,
            total_batches=3,
            items_count=50,
            status="in_progress",
        )

        # Get incomplete batches (should have one now)
        incomplete = db_manager.get_incomplete_batches("TEST")
        assert len(incomplete) == 1
        assert incomplete[0].entity_type == "test_cycle"

        # Test filtering by entity type
        test_case_incomplete = db_manager.get_incomplete_batches("TEST", "test_case")
        assert len(test_case_incomplete) == 0

        test_cycle_incomplete = db_manager.get_incomplete_batches("TEST", "test_cycle")
        assert len(test_cycle_incomplete) == 1

    def test_get_statistics(self, db_manager, test_project):
        """Test getting statistics for a project."""
        # First populate database
        db_manager.save_project(test_project)

        # Create and save entities
        folder = FolderModel(
            id="FOLD-1", name="Test Cases", folderType="TEST_CASE", projectKey="TEST"
        )
        db_manager.save_folder(folder, "TEST")

        status = StatusModel(id="STAT-1", name="Active", type="TEST_CASE")
        db_manager.save_status(status, "TEST")

        priority = PriorityModel(id="PRI-1", name="High", rank=1)
        db_manager.save_priority(priority, "TEST")

        environment = EnvironmentModel(id="ENV-1", name="Production")
        db_manager.save_environment(environment, "TEST")

        test_case = CaseModel(
            id="TC-1",
            key="TEST-1",
            name="Test Login",
            folder="FOLD-1",
            steps=[
                CaseStepModel(index=0, description="Step 1", expected_result="Result 1"),
                CaseStepModel(index=1, description="Step 2", expected_result="Result 2"),
            ],
            custom_fields=[
                CustomFieldModel(id="CF-1", name="Test Type", type="text", value="Integration")
            ],
        )
        db_manager.save_test_case(test_case, "TEST")

        test_cycle = CycleInfoModel(
            id="CYCLE-1", key="TEST-C1", name="Sprint 1 Testing", project_key="TEST"
        )
        db_manager.save_test_cycle(test_cycle, "TEST")

        test_execution = ExecutionModel(
            id="EXEC-1", testCaseKey="TEST-1", cycleId="CYCLE-1", status="PASS", environment="ENV-1"
        )
        db_manager.save_test_execution(test_execution, "TEST")

        # Get statistics
        stats = db_manager.get_statistics("TEST")

        # Verify counts
        assert stats["projects"] == 1
        assert stats["folders"] == 1
        assert stats["statuses"] == 1
        assert stats["priorities"] == 1
        assert stats["environments"] == 1
        assert stats["test_cases"] == 1
        assert stats["test_cycles"] == 1
        assert stats["test_executions"] == 1
        assert stats["test_steps"] == 2  # From test case
        assert stats["custom_fields"] == 1

    def test_execute_query(self, db_manager, test_project):
        """Test executing raw SQL queries."""
        # First populate database
        db_manager.save_project(test_project)

        # Execute a simple query
        result = db_manager.execute_query(
            "SELECT * FROM projects WHERE key = :key", {"key": "TEST"}
        )

        # Verify result
        assert len(result) == 1
        assert result[0]["key"] == "TEST"
        assert result[0]["name"] == "Test Project"

        # Execute a more complex query with joins
        folder = FolderModel(
            id="FOLD-1", name="Test Cases", folderType="TEST_CASE", projectKey="TEST"
        )
        db_manager.save_folder(folder, "TEST")

        query = """
        SELECT p.name as project_name, f.name as folder_name
        FROM projects p JOIN folders f ON p.key = f.project_key
        WHERE p.key = :key
        """

        result = db_manager.execute_query(query, {"key": "TEST"})

        assert len(result) == 1
        assert result[0]["project_name"] == "Test Project"
        assert result[0]["folder_name"] == "Test Cases"

    def test_query_to_dataframe(self, db_manager, test_project):
        """Test executing queries and returning pandas DataFrames."""
        # First populate database
        db_manager.save_project(test_project)

        # Save additional projects for testing
        project2 = ProjectModel(id="PRJ-2", key="PROJ2", name="Project 2")
        db_manager.save_project(project2)

        project3 = ProjectModel(id="PRJ-3", key="PROJ3", name="Project 3")
        db_manager.save_project(project3)

        # Execute query to DataFrame
        df = db_manager.query_to_dataframe("SELECT * FROM projects ORDER BY key")

        # Verify DataFrame
        assert len(df) == 3
        assert list(df.columns) == ["id", "key", "name", "description"]
        assert df["key"].tolist() == ["PROJ2", "PROJ3", "TEST"]

        # Test DataFrame operations
        filtered_df = df[df["key"] != "TEST"]
        assert len(filtered_df) == 2
        assert filtered_df["key"].tolist() == ["PROJ2", "PROJ3"]
