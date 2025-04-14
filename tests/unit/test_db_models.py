"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import datetime
import json
import os
import tempfile
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from ztoq.core.db_models import (
    Attachment,
        Base,
        CaseVersion,
        CustomFieldDefinition,
        CustomFieldValue,
        EntityBatchState,
        EntityType,
        Environment,
        Folder,
        Label,
        Link,
        MigrationState,
        Priority,
        Project,
        ScriptFile,
        Status,
        TestCase,
        TestCycle,
        TestExecution,
        TestPlan,
        TestStep,
)

@pytest.mark.unit()


class TestDBModels:
    @pytest.fixture(scope="class")
    def db_path(self):
        """Create a temporary database file for testing."""
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        db_file = os.path.join(temp_dir, "test.db")

        # Create the database and tables
        engine = create_engine(f"sqlite:///{db_file}")
        Base.metadata.create_all(engine)

        yield db_file

        # Clean up
        os.unlink(db_file)
        os.rmdir(temp_dir)

    @pytest.fixture()
    def engine(self, db_path):
        """Create a SQLite engine for testing."""
        return create_engine(f"sqlite:///{db_path}")

    @pytest.fixture()
    def session(self, engine):
        """Create a new session for testing."""
        Session = sessionmaker(bind=engine)
        session = Session()

        yield session

        # Rollback and close
        session.rollback()
        session.close()

    def test_models_tablenames(self):
        """Test that all model classes have appropriate table names."""
        expected_tables = {
            Project: "projects",
                Folder: "folders",
                Status: "statuses",
                Priority: "priorities",
                Environment: "environments",
                Label: "labels",
                CustomFieldDefinition: "custom_field_definitions",
                CustomFieldValue: "custom_field_values",
                Link: "links",
                Attachment: "attachments",
                ScriptFile: "script_files",
                CaseVersion: "case_versions",
                TestStep: "test_steps",
                TestCase: "test_cases",
                TestCycle: "test_cycles",
                TestPlan: "test_plans",
                TestExecution: "test_executions",
                MigrationState: "migration_state",
                EntityBatchState: "entity_batch_state",
            }

        for model_class, expected_tablename in expected_tables.items():
            assert model_class.__tablename__ == expected_tablename

    def test_entity_type_enum(self):
        """Test that EntityType enum has all required values."""
        enum_values = [e.value for e in EntityType]
        expected_values = [
            "TEST_CASE",
                "TEST_EXECUTION",
                "TEST_STEP",
                "TEST_CYCLE",
                "TEST_PLAN",
                "FOLDER",
            ]

        for expected in expected_values:
            assert expected in enum_values

    def test_project_model(self, session):
        """Test Project model creation and relationships."""
        # Create a project
        project = Project(
            id="PRJ-123", key="TEST", name="Test Project", description="A test project"
        )
        session.add(project)
        session.commit()

        # Verify project was created
        saved_project = session.query(Project).filter_by(id="PRJ-123").first()
        assert saved_project is not None
        assert saved_project.key == "TEST"
        assert saved_project.name == "Test Project"
        assert saved_project.description == "A test project"

        # Test project relationships
        # Create related entities
        folder = Folder(
            id="FOLD-1",
                name="Test Folder",
                folder_type="TEST_CASE",
                project_key="TEST",
                project=project,
            )
        status = Status(
            id="STAT-1", name="Active", type="TEST_CASE", project_key="TEST", project=project
        )
        priority = Priority(id="PRI-1", name="High", rank=1, project_key="TEST", project=project)
        environment = Environment(
            id="ENV-1", name="Production", project_key="TEST", project=project
        )

        session.add_all([folder, status, priority, environment])
        session.commit()

        # Verify relationships
        assert len(project.folders) == 1
        assert project.folders[0].id == "FOLD-1"
        assert len(project.statuses) == 1
        assert project.statuses[0].id == "STAT-1"
        assert len(project.priorities) == 1
        assert project.priorities[0].id == "PRI-1"
        assert len(project.environments) == 1
        assert project.environments[0].id == "ENV-1"

    def test_folder_model(self, session):
        """Test Folder model creation and relationships."""
        # Create a project first
        project = Project(id="PRJ-FOLDER", key="TEST-FOLDER", name="Test Project for Folders")
        session.add(project)
        session.commit()

        # Create a parent folder
        parent_folder = Folder(
            id="FOLD-PARENT",
                name="Parent Folder",
                folder_type="TEST_CASE",
                project_key="TEST-FOLDER",
                project=project,
            )
        session.add(parent_folder)
        session.commit()

        # Create a child folder with parent relationship
        child_folder = Folder(
            id="FOLD-CHILD",
                name="Child Folder",
                folder_type="TEST_CASE",
                parent_id="FOLD-PARENT",
                project_key="TEST-FOLDER",
                project=project,
            )
        session.add(child_folder)
        session.commit()

        # Verify folder hierarchy
        saved_parent = session.query(Folder).filter_by(id="FOLD-PARENT").first()
        saved_child = session.query(Folder).filter_by(id="FOLD-CHILD").first()

        assert saved_parent is not None
        assert saved_child is not None
        assert saved_child.parent_id == "FOLD-PARENT"
        assert saved_child.parent.id == "FOLD-PARENT"
        assert len(saved_parent.children) == 1
        assert saved_parent.children[0].id == "FOLD-CHILD"

    def test_test_case_model(self, session):
        """Test TestCase model creation and relationships."""
        # Create a project first
        project = Project(id="PRJ-CASES", key="TEST-CASES", name="Test Project for Cases")
        session.add(project)

        # Create a folder
        folder = Folder(
            id="FOLD-CASES",
                name="Test Folder for Cases",
                folder_type="TEST_CASE",
                project_key="TEST-CASES",
                project=project,
            )
        session.add(folder)

        # Create a priority
        priority = Priority(
            id="PRI-CASES", name="High", rank=1, project_key="TEST-CASES", project=project
        )
        session.add(priority)
        session.commit()

        # Create a test case
        test_case = TestCase(
            id="TC-CASES",
                key="TESTCASE-1",
                name="Login Test",
                objective="Verify user login",
                precondition="User exists in system",
                description="Test the login functionality",
                status="Active",
                priority_id="PRI-CASES",
                priority_name="High",
                folder_id="FOLD-CASES",
                folder_name="Test Folder for Cases",
                owner="user1",
                owner_name="Test User",
                created_on=datetime.datetime.now(),
                created_by="user1",
                project_key="TEST-CASES",
                project=project,
                priority=priority,
                folder=folder,
            )
        session.add(test_case)

        # Create test steps
        step1 = TestStep(
            id="STEP-CASES-1",
                index=0,
                description="Navigate to login page",
                expected_result="Login page displayed",
                test_case_id="TC-CASES",
                test_case=test_case,
            )
        step2 = TestStep(
            id="STEP-CASES-2",
                index=1,
                description="Enter credentials and submit",
                expected_result="User logged in successfully",
                test_case_id="TC-CASES",
                test_case=test_case,
            )
        session.add_all([step1, step2])

        # Add label
        label = Label(id="LABEL-CASES", name="Regression")
        session.add(label)
        test_case.labels.append(label)

        # Create script file
        script = ScriptFile(
            id="SCRIPT-CASES",
                filename="login_test.py",
                type="python",
                content="import pytest\ndef test_login():\n    assert True",
                test_case_id="TC-CASES",
                test_case=test_case,
            )
        session.add(script)
        session.commit()

        # Verify test case
        saved_case = session.query(TestCase).filter_by(id="TC-CASES").first()
        assert saved_case is not None
        assert saved_case.name == "Login Test"
        assert saved_case.objective == "Verify user login"
        assert saved_case.priority_id == "PRI-CASES"
        assert saved_case.priority.name == "High"
        assert saved_case.folder_id == "FOLD-CASES"
        assert saved_case.folder.name == "Test Folder for Cases"

        # Verify relationships
        assert len(saved_case.steps) == 2
        assert saved_case.steps[0].description == "Navigate to login page"
        assert saved_case.steps[1].description == "Enter credentials and submit"

        assert len(saved_case.labels) == 1
        assert saved_case.labels[0].name == "Regression"

        assert len(saved_case.scripts) == 1
        assert saved_case.scripts[0].filename == "login_test.py"
        assert "import pytest" in saved_case.scripts[0].content

    def test_test_cycle_model(self, session):
        """Test TestCycle model creation and relationships."""
        # Create a project first
        project = Project(id="PRJ-CYCLES", key="TEST-CYCLES", name="Test Project for Cycles")
        session.add(project)

        # Create a folder
        folder = Folder(
            id="FOLD-CYCLES",
                name="Test Cycles",
                folder_type="TEST_CYCLE",
                project_key="TEST-CYCLES",
                project=project,
            )
        session.add(folder)
        session.commit()

        # Create a test cycle
        test_cycle = TestCycle(
            id="CYCLE-TEST",
                key="CYCLE-1",
                name="Sprint 1 Testing",
                description="Testing for Sprint 1",
                status="Active",
                status_name="Active",
                folder_id="FOLD-CYCLES",
                folder_name="Test Cycles",
                owner="user1",
                owner_name="Test User",
                created_on=datetime.datetime.now(),
                created_by="user1",
                planned_start_date=datetime.datetime.now(),
                planned_end_date=datetime.datetime.now() + datetime.timedelta(days=14),
                project_key="TEST-CYCLES",
                project=project,
                folder=folder,
            )
        session.add(test_cycle)
        session.commit()

        # Verify test cycle
        saved_cycle = session.query(TestCycle).filter_by(id="CYCLE-TEST").first()
        assert saved_cycle is not None
        assert saved_cycle.name == "Sprint 1 Testing"
        assert saved_cycle.description == "Testing for Sprint 1"
        assert saved_cycle.status == "Active"
        assert saved_cycle.folder_id == "FOLD-CYCLES"
        assert saved_cycle.folder.name == "Test Cycles"
        assert saved_cycle.planned_start_date is not None
        assert saved_cycle.planned_end_date is not None

    def test_test_execution_model(self, session):
        """Test TestExecution model creation and relationships."""
        # Create a project first
        project = Project(id="PRJ-EXEC", key="TEST-EXEC", name="Test Project for Executions")
        session.add(project)

        # Create a test case
        test_case = TestCase(
            id="TC-EXEC",
                key="EXEC-CASE-1",
                name="Login Test for Execution",
                project_key="TEST-EXEC",
                project=project,
            )
        session.add(test_case)

        # Create a test cycle
        test_cycle = TestCycle(
            id="CYCLE-EXEC",
                key="EXEC-CYCLE-1",
                name="Cycle for Execution Tests",
                project_key="TEST-EXEC",
                project=project,
            )
        session.add(test_cycle)

        # Create an environment
        environment = Environment(
            id="ENV-EXEC", name="Production Exec", project_key="TEST-EXEC", project=project
        )
        session.add(environment)
        session.commit()

        # Create a test execution
        execution = TestExecution(
            id="EXEC-TEST",
                test_case_key="EXEC-CASE-1",
                cycle_id="CYCLE-EXEC",
                cycle_name="Cycle for Execution Tests",
                status="PASS",
                status_name="Passed",
                environment_id="ENV-EXEC",
                environment_name="Production Exec",
                executed_by="user1",
                executed_by_name="Test User",
                executed_on=datetime.datetime.now(),
                created_on=datetime.datetime.now(),
                created_by="user1",
                comment="Test passed with no issues",
                project_key="TEST-EXEC",
                project=project,
                test_case=test_case,
                test_cycle=test_cycle,
                environment=environment,
            )
        session.add(execution)

        # Create execution steps
        exec_step = TestStep(
            id="EXEC-STEP-TEST",
                index=0,
                description="Navigate to login page",
                expected_result="Login page displayed",
                actual_result="Login page displayed correctly",
                status="PASS",
                test_execution_id="EXEC-TEST",
                test_execution=execution,
            )
        session.add(exec_step)
        session.commit()

        # Verify test execution
        saved_execution = session.query(TestExecution).filter_by(id="EXEC-TEST").first()
        assert saved_execution is not None
        assert saved_execution.test_case_key == "EXEC-CASE-1"
        assert saved_execution.cycle_id == "CYCLE-EXEC"
        assert saved_execution.status == "PASS"
        assert saved_execution.environment_id == "ENV-EXEC"
        assert saved_execution.comment == "Test passed with no issues"

        # Verify relationships
        assert saved_execution.test_case.key == "EXEC-CASE-1"
        assert saved_execution.test_cycle.name == "Cycle for Execution Tests"
        assert saved_execution.environment.name == "Production Exec"

        assert len(saved_execution.steps) == 1
        assert saved_execution.steps[0].description == "Navigate to login page"
        assert saved_execution.steps[0].actual_result == "Login page displayed correctly"
        assert saved_execution.steps[0].status == "PASS"

    def test_custom_field_models(self, session):
        """Test CustomFieldDefinition and CustomFieldValue models."""
        # Create a project first
        project = Project(id="PRJ-CF", key="TEST-CF", name="Test Project for Custom Fields")
        session.add(project)
        session.commit()

        # Create custom field definition
        field_def = CustomFieldDefinition(
            id="CF-TEST", name="Test Type", type="text", project_key="TEST-CF", project=project
        )
        session.add(field_def)
        session.commit()

        # Create custom field values for different entity types
        values = [
            CustomFieldValue(
                id="CFV-CASE",
                    field_id="CF-TEST",
                    entity_type=EntityType.TEST_CASE,
                    entity_id="TC-CF-TEST",
                    value_text="Integration test",
                    field_definition=field_def,
                ),
                CustomFieldValue(
                id="CFV-CYCLE",
                    field_id="CF-TEST",
                    entity_type=EntityType.TEST_CYCLE,
                    entity_id="CYCLE-CF-TEST",
                    value_text="Regression cycle",
                    field_definition=field_def,
                ),
            ]
        session.add_all(values)
        session.commit()

        # Verify custom field definitions
        saved_def = session.query(CustomFieldDefinition).filter_by(id="CF-TEST").first()
        assert saved_def is not None
        assert saved_def.name == "Test Type"
        assert saved_def.type == "text"
        assert saved_def.project_key == "TEST-CF"

        # Verify custom field values
        saved_values = session.query(CustomFieldValue).filter_by(field_id="CF-TEST").all()
        assert len(saved_values) == 2

        # Check relationship from definition to values
        assert len(field_def.values) == 2
        assert field_def.values[0].entity_type == EntityType.TEST_CASE
        assert field_def.values[1].entity_type == EntityType.TEST_CYCLE

    def test_attachment_model(self, session):
        """Test Attachment model."""
        # Create an attachment
        attachment = Attachment(
            id="ATT-1",
                filename="screenshot.png",
                content_type="image/png",
                size=1024,
                created_on=datetime.datetime.now(),
                created_by="user1",
                content=b"test binary data",
                entity_type=EntityType.TEST_EXECUTION,
                entity_id="EXEC-123",
            )
        session.add(attachment)
        session.commit()

        # Verify attachment
        saved_attachment = session.query(Attachment).filter_by(id="ATT-1").first()
        assert saved_attachment is not None
        assert saved_attachment.filename == "screenshot.png"
        assert saved_attachment.content_type == "image/png"
        assert saved_attachment.size == 1024
        assert saved_attachment.content == b"test binary data"
        assert saved_attachment.entity_type == EntityType.TEST_EXECUTION
        assert saved_attachment.entity_id == "EXEC-123"

    def test_migration_state_model(self, session):
        """Test MigrationState model."""
        # Create migration state
        migration_state = MigrationState(
            project_key="TEST",
                extraction_status="completed",
                transformation_status="in_progress",
                loading_status="not_started",
                error_message=None,
                meta_data=json.dumps(
                {
                    "extraction_complete_time": "2025-04-13T10:00:00",
                        "items_extracted": 150,
                        "items_transformed": 75,
                    }
            ),
            )
        session.add(migration_state)
        session.commit()

        # Verify migration state
        saved_state = session.query(MigrationState).filter_by(project_key="TEST").first()
        assert saved_state is not None
        assert saved_state.extraction_status == "completed"
        assert saved_state.transformation_status == "in_progress"
        assert saved_state.loading_status == "not_started"

        # Test metadata_dict property
        metadata = saved_state.metadata_dict
        assert isinstance(metadata, dict)
        assert metadata["extraction_complete_time"] == "2025-04-13T10:00:00"
        assert metadata["items_extracted"] == 150
        assert metadata["items_transformed"] == 75

    def test_entity_batch_state_model(self, session):
        """Test EntityBatchState model."""
        # Create entity batch state
        batch_state = EntityBatchState(
            project_key="TEST",
                entity_type="test_case",
                batch_number=1,
                total_batches=5,
                items_count=100,
                processed_count=50,
                status="in_progress",
                started_at=datetime.datetime.now() - datetime.timedelta(minutes=5),
                error_message=None,
            )
        session.add(batch_state)
        session.commit()

        # Verify entity batch state
        saved_batch = (
            session.query(EntityBatchState)
            .filter_by(project_key="TEST", entity_type="test_case", batch_number=1)
            .first()
        )

        assert saved_batch is not None
        assert saved_batch.total_batches == 5
        assert saved_batch.items_count == 100
        assert saved_batch.processed_count == 50
        assert saved_batch.status == "in_progress"
        assert saved_batch.started_at is not None
        assert saved_batch.completed_at is None

    def test_indexes_and_constraints(self, engine):
        """Test that all expected indexes and constraints exist."""
        inspector = inspect(engine)

        # Check test_cases table indexes
        test_case_indexes = inspector.get_indexes("test_cases")
        index_names = [idx["name"] for idx in test_case_indexes]

        assert "idx_test_case_project" in index_names
        assert "idx_test_case_folder" in index_names
        assert "idx_test_case_priority" in index_names
        assert "idx_test_case_status" in index_names

        # Check unique constraints on EntityBatchState
        entity_batch_unique = inspector.get_unique_constraints("entity_batch_state")
        assert len(entity_batch_unique) > 0
        unique_constraint = entity_batch_unique[0]
        assert "project_key" in unique_constraint["column_names"]
        assert "entity_type" in unique_constraint["column_names"]
        assert "batch_number" in unique_constraint["column_names"]

    def test_association_tables(self, session):
        """Test many-to-many association tables."""
        # Create a project
        project = Project(id="PRJ-ASSOC", key="TEST-ASSOC", name="Test Project for Associations")
        session.add(project)

        # Create a test case
        test_case = TestCase(
            id="TC-ASSOC",
                key="ASSOC-CASE-1",
                name="Association Test Case",
                project_key="TEST-ASSOC",
                project=project,
            )
        session.add(test_case)

        # Create labels
        labels = [
            Label(id="LABEL-A1", name="Regression-A"),
                Label(id="LABEL-A2", name="Smoke-A"),
                Label(id="LABEL-A3", name="API-A"),
            ]
        session.add_all(labels)

        # Create case versions
        versions = [
            CaseVersion(
                id="VER-A1",
                    name="v1.0-A",
                    created_at=datetime.datetime.now() - datetime.timedelta(days=30),
                    created_by="user1",
                ),
                CaseVersion(
                id="VER-A2", name="v2.0-A", created_at=datetime.datetime.now(), created_by="user1"
            ),
            ]
        session.add_all(versions)

        # Associate labels and versions with test case
        test_case.labels.extend(labels)
        test_case.versions.extend(versions)
        session.commit()

        # Verify associations
        saved_case = session.query(TestCase).filter_by(id="TC-ASSOC").first()
        assert len(saved_case.labels) == 3
        assert len(saved_case.versions) == 2

        # Check bidirectional relationship
        for label in labels:
            assert test_case in label.test_cases

        for version in versions:
            assert test_case in version.test_cases
