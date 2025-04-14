"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import pytest
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from ztoq.models import Project, Case, CycleInfo, Execution, Folder, Status, Priority, Environment, CustomField, Link, CaseStep
from ztoq.data_fetcher import FetchResult
from ztoq.database_manager import DatabaseManager




@pytest.mark.unit
class TestDatabaseManager:
    @pytest.fixture
    def db_path(self, tmp_path):
        """Create a temporary database path."""
        return tmp_path / "test.db"

    @pytest.fixture
    def db_manager(self, db_path):
        """Create a test database manager instance."""
        return DatabaseManager(db_path)

    def test_initialization(self, db_path):
        """Test initializing the database manager."""
        # Test with string path
        manager1 = DatabaseManager(str(db_path))
        assert manager1.db_path == db_path

        # Test with Path object
        manager2 = DatabaseManager(db_path)
        assert manager2.db_path == db_path

        # Test parent directory creation
        nested_path = db_path.parent / "nested" / "test.db"
        manager3 = DatabaseManager(nested_path)
        assert nested_path.parent.exists()

    def test_context_manager(self, db_manager):
        """Test using the context manager for database connections."""
        with db_manager.get_connection() as conn:
            assert isinstance(conn, sqlite3.Connection)
            cursor = conn.cursor()
            cursor.execute("SELECT sqlite_version();")
            version = cursor.fetchone()
            assert version is not None

        # Connection should be closed after context exit
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_initialize_database(self, db_manager):
        """Test database initialization creates all required tables."""
        db_manager.initialize_database()

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            # Check tables were created
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [table[0] for table in cursor.fetchall()]

            expected_tables = [
                "projects",
                "folders",
                "statuses",
                "priorities",
                "environments",
                "test_cases",
                "test_cycles",
                "test_plans",
                "test_executions",
            ]

            for table in expected_tables:
                assert table in tables

            # Check indexes were created
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [index[0] for index in cursor.fetchall()]

            expected_indexes = [
                "idx_test_cases_project",
                "idx_test_cycles_project",
                "idx_test_plans_project",
                "idx_test_executions_project",
                "idx_test_executions_cycle",
                "idx_test_executions_case",
                "idx_folders_project",
                "idx_folders_parent",
                "idx_statuses_project",
                "idx_priorities_project",
                "idx_environments_project",
            ]

            for index in expected_indexes:
                assert index in indexes

    def test_serialize_value(self, db_manager):
        """Test serialization of various data types."""
        # Test dict serialization
        assert db_manager._serialize_value({"key": "value"}) == '{"key": "value"}'

        # Test list serialization
        assert db_manager._serialize_value([1, 2, 3]) == "[1, 2, 3]"

        # Test datetime serialization
        dt = datetime(2023, 1, 1, 12, 0, 0)
        assert db_manager._serialize_value(dt) == "2023-01-01T12:00:00"

        # Test None value
        assert db_manager._serialize_value(None) is None

        # Test primitive values
        assert db_manager._serialize_value(123) == 123
        assert db_manager._serialize_value("test") == "test"
        assert db_manager._serialize_value(True) is True

    def test_serialize_object(self, db_manager):
        """Test object serialization for database storage."""
        # Create a sample model with model_dump method (Pydantic v2)
        mock_model_v2 = MagicMock()
        mock_model_v2.model_dump.return_value = {"id": "123", "name": "Test"}
        serialized_v2 = db_manager._serialize_object(mock_model_v2)
        assert serialized_v2 == {"id": "123", "name": "Test"}
        mock_model_v2.model_dump.assert_called_once()

        # Create a sample model with dict method (Pydantic v1)
        mock_model_v1 = MagicMock()
        # No model_dump method
        del mock_model_v1.model_dump
        mock_model_v1.dict.return_value = {"id": "456", "name": "Test"}
        serialized_v1 = db_manager._serialize_object(mock_model_v1)
        assert serialized_v1 == {"id": "456", "name": "Test"}
        mock_model_v1.dict.assert_called_once()

        # Test datetime serialization
        dt = datetime(2023, 1, 1, 12, 0, 0)
        assert db_manager._serialize_object(dt) == "2023-01-01T12:00:00"

        # Test list serialization
        test_list = [mock_model_v2, "string", 123]
        serialized_list = db_manager._serialize_object(test_list)
        assert serialized_list[0] == {"id": "123", "name": "Test"}
        assert serialized_list[1] == "string"
        assert serialized_list[2] == 123

        # Test dict serialization
        test_dict = {"model": mock_model_v1, "date": dt, "value": 123}
        serialized_dict = db_manager._serialize_object(test_dict)
        assert serialized_dict["model"] == {"id": "456", "name": "Test"}
        assert serialized_dict["date"] == "2023-01-01T12:00:00"
        assert serialized_dict["value"] == 123

    def test_save_project(self, db_manager):
        """Test saving a project to the database."""
        db_manager.initialize_database()

        project = Project(
            id="proj123", key="TEST", name="Test Project", description="This is a test project"
        )

        db_manager.save_project(project)

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project.id,))
            result = cursor.fetchone()

            assert result is not None
            assert result["id"] == "proj123"
            assert result["key"] == "TEST"
            assert result["name"] == "Test Project"
            assert result["description"] == "This is a test project"

    def test_save_folder(self, db_manager):
        """Test saving a folder to the database."""
        db_manager.initialize_database()

        # First create a project (for foreign key constraint)
        project = Project(id="proj123", key="TEST", name="Test Project")
        db_manager.save_project(project)

        # Create and save a folder
        folder = Folder(
            id="folder123", name="Test Folder", folderType="TEST_CASE", projectKey="TEST"
        )

        db_manager.save_folder(folder, "TEST")

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM folders WHERE id = ?", (folder.id,))
            result = cursor.fetchone()

            assert result is not None
            assert result["id"] == "folder123"
            assert result["name"] == "Test Folder"
            assert result["folder_type"] == "TEST_CASE"
            assert result["project_key"] == "TEST"
            assert result["parent_id"] is None

    def test_save_status(self, db_manager):
        """Test saving a status to the database."""
        db_manager.initialize_database()

        # First create a project (for foreign key constraint)
        project = Project(id="proj123", key="TEST", name="Test Project")
        db_manager.save_project(project)

        # Create and save a status
        status = Status(
            id="status123",
            name="Passed",
            description="Test passed successfully",
            color="#00FF00",
            type="TEST_EXECUTION",
        )

        db_manager.save_status(status, "TEST")

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM statuses WHERE id = ?", (status.id,))
            result = cursor.fetchone()

            assert result is not None
            assert result["id"] == "status123"
            assert result["name"] == "Passed"
            assert result["description"] == "Test passed successfully"
            assert result["color"] == "#00FF00"
            assert result["type"] == "TEST_EXECUTION"
            assert result["project_key"] == "TEST"

    def test_save_priority(self, db_manager):
        """Test saving a priority to the database."""
        db_manager.initialize_database()

        # First create a project (for foreign key constraint)
        project = Project(id="proj123", key="TEST", name="Test Project")
        db_manager.save_project(project)

        # Create and save a priority
        priority = Priority(
            id="priority123", name="High", description="High priority item", color="#FF0000", rank=1
        )

        db_manager.save_priority(priority, "TEST")

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM priorities WHERE id = ?", (priority.id,))
            result = cursor.fetchone()

            assert result is not None
            assert result["id"] == "priority123"
            assert result["name"] == "High"
            assert result["description"] == "High priority item"
            assert result["color"] == "#FF0000"
            assert result["rank"] == 1
            assert result["project_key"] == "TEST"

    def test_save_environment(self, db_manager):
        """Test saving an environment to the database."""
        db_manager.initialize_database()

        # First create a project (for foreign key constraint)
        project = Project(id="proj123", key="TEST", name="Test Project")
        db_manager.save_project(project)

        # Create and save an environment
        environment = Environment(
            id="env123", name="Production", description="Production environment"
        )

        db_manager.save_environment(environment, "TEST")

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM environments WHERE id = ?", (environment.id,))
            result = cursor.fetchone()

            assert result is not None
            assert result["id"] == "env123"
            assert result["name"] == "Production"
            assert result["description"] == "Production environment"
            assert result["project_key"] == "TEST"

    def test_save_test_case(self, db_manager):
        """Test saving a test case to the database."""
        db_manager.initialize_database()

        # First create a project (for foreign key constraint)
        project = Project(id="proj123", key="TEST", name="Test Project")
        db_manager.save_project(project)

        # Create priority and folder for foreign key constraints
        priority = Priority(id="priority123", name="High", rank=1)
        db_manager.save_priority(priority, "TEST")

        folder = Folder(
            id="folder123", name="Test Cases", folderType="TEST_CASE", projectKey="TEST"
        )
        db_manager.save_folder(folder, "TEST")

        # Create test case with steps, links, and other complex fields
        test_case = Case(
            id="tc123",
            key="TEST-1",
            name="Test Login",
            objective="Verify user login functionality",
            precondition="User exists in the system",
            description="Test the login functionality",
            status="Active",
            priority=priority,
            priority_name="High",
            folder="folder123",
            folder_name="Test Cases",
            created_on=datetime.now(),
            created_by="user1",
            labels=["regression", "smoke"],
            steps=[
                CaseStep(
                    index=0,
                    description="Navigate to login page",
                    expected_result="Login page is displayed",
                ),
                CaseStep(
                    index=1,
                    description="Enter credentials and click login",
                    expected_result="User is logged in successfully",
                ),
            ],
            custom_fields=[
                CustomField(id="cf1", name="Test Type", type="text", value="Integration")
            ],
            links=[Link(name="Requirements", url="https://example.com/req1", type="web")],
        )

        # Save the test case
        db_manager.save_test_case(test_case, "TEST")

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM test_cases WHERE id = ?", (test_case.id,))
            result = cursor.fetchone()

            assert result is not None
            assert result["id"] == "tc123"
            assert result["key"] == "TEST-1"
            assert result["name"] == "Test Login"
            assert result["objective"] == "Verify user login functionality"
            assert result["priority_id"] == "priority123"
            assert result["folder_id"] == "folder123"

            # Check complex fields were properly serialized
            labels = json.loads(result["labels"])
            assert "regression" in labels
            assert "smoke" in labels

            steps = json.loads(result["steps"])
            assert len(steps) == 2
            assert steps[0]["index"] == 0
            assert "Navigate to login page" in steps[0]["description"]

            custom_fields = json.loads(result["custom_fields"])
            assert len(custom_fields) == 1
            assert custom_fields[0]["name"] == "Test Type"
            assert custom_fields[0]["value"] == "Integration"

            links = json.loads(result["links"])
            assert len(links) == 1
            assert links[0]["name"] == "Requirements"
            assert links[0]["url"] == "https://example.com/req1"

    def test_save_test_case_with_dict_priority(self, db_manager):
        """Test saving a test case with a dictionary priority instead of an object."""
        db_manager.initialize_database()

        # First create a project (for foreign key constraint)
        project = Project(id="proj123", key="TEST", name="Test Project")
        db_manager.save_project(project)

        # Create priority (needed for foreign key constraint)
        priority = Priority(id="priority123", name="High", rank=1)
        db_manager.save_priority(priority, "TEST")

        # Since we can't directly modify the priority field validation,
        # let's modify the DatabaseManager._serialize_value method for this test
        original_serialize_value = db_manager._serialize_value

        try:
            # Create a test case
            test_case = Case(
                id="tc123",
                key="TEST-1",
                name="Test Login",
                status="Active",
                priority=priority,  # Use the actual priority object
                priority_name="High",
            )

            # Replace priority with dict just before processing
            # Use a mock to modify the behavior
            with patch.object(test_case, "priority", new={"id": "priority123", "name": "High"}):
                # Save the test case with our modified object
                db_manager.save_test_case(test_case, "TEST")

            # Verify it was saved correctly
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM test_cases WHERE id = ?", (test_case.id,))
                result = cursor.fetchone()

                assert result is not None
                assert result["priority_id"] == "priority123"
        finally:
            # Restore original method
            db_manager._serialize_value = original_serialize_value

    def test_save_test_cycle(self, db_manager):
        """Test saving a test cycle to the database."""
        db_manager.initialize_database()

        # First create a project (for foreign key constraint)
        project = Project(id="proj123", key="TEST", name="Test Project")
        db_manager.save_project(project)

        # Create and save a folder for the cycle
        folder = Folder(
            id="folder456", name="Test Cycles", folderType="TEST_CYCLE", projectKey="TEST"
        )
        db_manager.save_folder(folder, "TEST")

        # Create a test cycle
        test_cycle = CycleInfo(
            id="cycle123",
            key="TEST-C1",
            name="Sprint 1 Testing",
            description="Test cycle for Sprint 1",
            status="Active",
            status_name="Active",
            folder="folder456",
            folder_name="Test Cycles",
            project_key="TEST",
            owner="user1",
            owner_name="Test User",
            created_on=datetime.now(),
            created_by="user1",
            custom_fields=[CustomField(id="cf2", name="Sprint", type="text", value="Sprint 1")],
            links=[Link(name="Sprint Board", url="https://example.com/sprint1", type="web")],
        )

        # Save the test cycle
        db_manager.save_test_cycle(test_cycle, "TEST")

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM test_cycles WHERE id = ?", (test_cycle.id,))
            result = cursor.fetchone()

            assert result is not None
            assert result["id"] == "cycle123"
            assert result["key"] == "TEST-C1"
            assert result["name"] == "Sprint 1 Testing"
            assert result["description"] == "Test cycle for Sprint 1"
            assert result["folder_id"] == "folder456"
            assert result["project_key"] == "TEST"

            # Check complex fields were properly serialized
            custom_fields = json.loads(result["custom_fields"])
            assert len(custom_fields) == 1
            assert custom_fields[0]["name"] == "Sprint"
            assert custom_fields[0]["value"] == "Sprint 1"

            links = json.loads(result["links"])
            assert len(links) == 1
            assert links[0]["name"] == "Sprint Board"
            assert links[0]["url"] == "https://example.com/sprint1"

    def test_save_test_execution(self, db_manager):
        """Test saving a test execution to the database."""
        db_manager.initialize_database()

        # First create a project (for foreign key constraint)
        project = Project(id="proj123", key="TEST", name="Test Project")
        db_manager.save_project(project)

        # Create test case and cycle (for foreign key constraints)
        test_case = Case(id="tc123", key="TEST-1", name="Test Login")
        db_manager.save_test_case(test_case, "TEST")

        test_cycle = CycleInfo(
            id="cycle123", key="TEST-C1", name="Sprint 1 Testing", project_key="TEST"
        )
        db_manager.save_test_cycle(test_cycle, "TEST")

        # Create environment
        environment = Environment(id="env123", name="Production")
        db_manager.save_environment(environment, "TEST")

        # Create a step for the execution - use correct field names for the model
        # The model field is actual_result, not actualResult
        step = CaseStep(
            index=0,
            description="Navigate to login page",
            expected_result="Login page is displayed",  # Note the snake_case here
            actual_result="Login page was displayed",  # And here
            status="PASS",
        )

        # Create a test execution
        test_execution = Execution(
            id="exec123",
            testCaseKey="TEST-1",
            cycleId="cycle123",
            cycle_name="Sprint 1 Testing",
            status="PASS",
            status_name="Passed",
            environment="env123",
            environment_name="Production",
            executed_by="user1",
            executed_by_name="Test User",
            executed_on=datetime.now(),
            created_on=datetime.now(),
            created_by="user1",
            comment="Test passed without issues",
            steps=[step],
            custom_fields=[CustomField(id="cf3", name="Browser", type="text", value="Chrome")],
        )

        # Check that the step value is correct before serialization
        assert test_execution.steps[0].actual_result == "Login page was displayed"

        # Save the test execution
        db_manager.save_test_execution(test_execution, "TEST")

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM test_executions WHERE id = ?", (test_execution.id,))
            result = cursor.fetchone()

            assert result is not None
            assert result["id"] == "exec123"
            assert result["test_case_key"] == "TEST-1"
            assert result["cycle_id"] == "cycle123"
            assert result["status"] == "PASS"
            assert result["environment_id"] == "env123"
            assert result["comment"] == "Test passed without issues"
            assert result["project_key"] == "TEST"

            # Check complex fields were properly serialized
            steps = json.loads(result["steps"])
            assert len(steps) == 1
            assert steps[0]["index"] == 0
            assert steps[0]["status"] == "PASS"

            # Check using the correct snake_case field name
            assert "Login page was displayed" in steps[0]["actual_result"]

            custom_fields = json.loads(result["custom_fields"])
            assert len(custom_fields) == 1
            assert custom_fields[0]["name"] == "Browser"
            assert custom_fields[0]["value"] == "Chrome"

    def test_save_project_data(self, db_manager):
        """Test saving all project data from fetch results."""
        db_manager.initialize_database()

        # Create project
        project = Project(id="proj123", key="TEST", name="Test Project")

        # Create sample data
        folders = [
            Folder(id="folder1", name="Test Cases", folderType="TEST_CASE", projectKey="TEST"),
            Folder(
                id="folder2",
                name="Test Cycles",
                folderType="TEST_CYCLE",
                projectKey="TEST",
                parentId="folder1",
            ),
        ]

        statuses = [
            Status(id="status1", name="Passed", type="TEST_EXECUTION"),
            Status(id="status2", name="Failed", type="TEST_EXECUTION"),
        ]

        priorities = [
            Priority(id="priority1", name="High", rank=1),
            Priority(id="priority2", name="Medium", rank=2),
        ]

        environments = [
            Environment(id="env1", name="Production"),
            Environment(id="env2", name="Staging"),
        ]

        test_cases = [
            Case(id="tc1", key="TEST-1", name="Test Login", folder="folder1"),
            Case(id="tc2", key="TEST-2", name="Test Logout", folder="folder1"),
        ]

        test_cycles = [
            CycleInfo(
                id="cycle1",
                key="TEST-C1",
                name="Sprint 1 Testing",
                project_key="TEST",
                folder="folder2",
            )
        ]

        test_executions = [
            Execution(
                id="exec1",
                testCaseKey="TEST-1",
                cycleId="cycle1",
                status="PASS",
                environment="env1",
            )
        ]

        # Create fetch results
        fetch_results = {
            "project": FetchResult(
                entity_type="project", project_key="TEST", items=[project], count=1, success=True
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

        # Check counts are correct
        assert result["project"] == 1
        assert result["folders"] == 2
        assert result["statuses"] == 2
        assert result["priorities"] == 2
        assert result["environments"] == 2
        assert result["test_cases"] == 2
        assert result["test_cycles"] == 1
        assert result["test_executions"] == 1

        # Verify data was saved correctly
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Check project
            cursor.execute("SELECT COUNT(*) FROM projects")
            assert cursor.fetchone()[0] == 1

            # Check folders
            cursor.execute("SELECT COUNT(*) FROM folders")
            assert cursor.fetchone()[0] == 2

            # Check test cases
            cursor.execute("SELECT COUNT(*) FROM test_cases")
            assert cursor.fetchone()[0] == 2

            # Check parent-child relationship in folders
            cursor.execute("SELECT * FROM folders WHERE id = ?", ("folder2",))
            folder2 = cursor.fetchone()
            assert folder2["parent_id"] == "folder1"

    def test_save_project_data_with_placeholder(self, db_manager):
        """Test saving project data when no project is provided in fetch results."""
        db_manager.initialize_database()

        # Create test cases without project
        test_cases = [Case(id="tc1", key="TEST-1", name="Test Login")]

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

        # Check a placeholder project was created
        assert result["project"] == 1
        assert result["test_cases"] == 1

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE key = ?", ("TEST",))
            project = cursor.fetchone()

            assert project is not None
            assert project["key"] == "TEST"
            assert "Placeholder" in project["description"]

    def test_save_all_projects_data(self, db_manager):
        """Test saving data for multiple projects."""
        # Initialize database first (to fix the failure)
        db_manager.initialize_database()

        # Create projects
        project1 = Project(id="proj1", key="PROJ1", name="Project 1")

        project2 = Project(id="proj2", key="PROJ2", name="Project 2")

        # Create test cases for each project
        test_cases1 = [Case(id="tc1", key="PROJ1-1", name="Test 1 for Project 1")]

        test_cases2 = [
            Case(id="tc2", key="PROJ2-1", name="Test 1 for Project 2"),
            Case(id="tc3", key="PROJ2-2", name="Test 2 for Project 2"),
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

        # Mock initialize_database to verify it's called only once
        with patch.object(
            db_manager, "initialize_database", wraps=db_manager.initialize_database
        ) as mock_init_db:
            results = db_manager.save_all_projects_data(all_projects_data)

            # Check initialize_database was called exactly once
            mock_init_db.assert_called_once()

            # Check results contain correct counts
            assert results["PROJ1"]["project"] == 1
            assert results["PROJ1"]["test_cases"] == 1
            assert results["PROJ2"]["project"] == 1
            assert results["PROJ2"]["test_cases"] == 2
