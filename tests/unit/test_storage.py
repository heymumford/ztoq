"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import json
from datetime import datetime
import pytest
from ztoq.models import Case, TestCase  # Using compatibility alias
from ztoq.storage import JSONStorage, SQLiteStorage

@pytest.mark.unit()


class TestSQLiteStorage:
    @pytest.fixture()
    def db_path(self, tmp_path):
        """Create a temporary database path."""
        return tmp_path / "test.db"

    @pytest.fixture()
    def storage(self, db_path):
        """Create a test SQLite storage instance."""
        storage = SQLiteStorage(db_path)
        storage.connect()
        try:
            yield storage
        finally:
            storage.close()

    def test_context_manager(self, db_path):
        """Test using the storage as a context manager."""
        with SQLiteStorage(db_path) as storage:
            assert storage.conn is not None
            assert storage.cursor is not None
        assert storage.conn is None
        assert storage.cursor is None

    def test_initialize_database(self, storage):
        """Test initializing the database creates the expected tables."""
        storage.initialize_database()

        # Check if tables were created
        storage.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = storage.cursor.fetchall()
        table_names = [table[0] for table in tables]

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
            assert table in table_names

    def test_save_project(self, storage):
        """Test saving project information."""
        storage.initialize_database()
        storage.save_project("TEST", "Test Project", "123", "A test project")

        storage.cursor.execute("SELECT * FROM projects WHERE key=?", ("TEST",))
        project = storage.cursor.fetchone()

        assert project is not None
        assert project["id"] == "123"
        assert project["key"] == "TEST"
        assert project["name"] == "Test Project"
        assert project["description"] == "A test project"

    def test_save_test_case(self, storage):
        """Test saving a test case."""
        storage.initialize_database()

        # Create a test case
        test_case = Case(
            id="tc1",
                key="TEST-TC-1",
                name="Test Case 1",
                status="Draft",
                labels=["regression", "smoke"],
                created_on=datetime.now(),
            )

        # Save it
        storage.save_test_case(test_case, "TEST")

        # Verify it was saved
        storage.cursor.execute("SELECT * FROM test_cases WHERE key=?", ("TEST-TC-1",))
        saved_case = storage.cursor.fetchone()

        assert saved_case is not None
        assert saved_case["id"] == "tc1"
        assert saved_case["key"] == "TEST-TC-1"
        assert saved_case["name"] == "Test Case 1"
        assert saved_case["status"] == "Draft"

        # Check JSON fields are properly serialized
        labels = json.loads(saved_case["labels"])
        assert "regression" in labels
        assert "smoke" in labels

    def test_serialize_value(self, storage):
        """Test serializing different types of values."""
        # Dictionary
        assert storage._serialize_value({"key": "value"}) == '{"key": "value"}'

        # List
        assert storage._serialize_value([1, 2, 3]) == "[1, 2, 3]"

        # DateTime
        dt = datetime(2023, 1, 1, 12, 0, 0)
        assert storage._serialize_value(dt) == "2023-01-01T12:00:00"

        # Simple types pass through
        assert storage._serialize_value("string") == "string"
        assert storage._serialize_value(123) == 123
        assert storage._serialize_value(True) is True
        assert storage._serialize_value(None) is None


@pytest.mark.unit()


class TestJSONStorage:
    @pytest.fixture()
    def output_dir(self, tmp_path):
        """Create a temporary output directory."""
        return tmp_path / "output"

    @pytest.fixture()
    def storage(self, output_dir):
        """Create a test JSON storage instance."""
        return JSONStorage(output_dir)

    def test_directory_creation(self, tmp_path):
        """Test the directory is created if it doesn't exist."""
        output_dir = tmp_path / "new_dir"
        assert not output_dir.exists()

        JSONStorage(output_dir)
        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_save_project(self, storage, output_dir):
        """Test saving project information."""
        storage.save_project("TEST", "Test Project", "123", "A test project")

        # Check the file was created
        project_file = output_dir / "project.json"
        assert project_file.exists()

        # Check the content
        with open(project_file) as f:
            project_data = json.load(f)

        assert project_data["id"] == "123"
        assert project_data["key"] == "TEST"
        assert project_data["name"] == "Test Project"
        assert project_data["description"] == "A test project"

    def test_save_test_cases(self, storage, output_dir):
        """Test saving multiple test cases."""
        test_cases = [
            TestCase(
                id="tc1",
                    key="TEST-TC-1",
                    name="Test Case 1",
                    status="Draft",
                ),
                TestCase(
                id="tc2",
                    key="TEST-TC-2",
                    name="Test Case 2",
                    status="Ready",
                ),
            ]

        storage.save_test_cases(test_cases, "TEST")

        # Check the file was created
        test_cases_file = output_dir / "test_cases.json"
        assert test_cases_file.exists()

        # Check the content
        with open(test_cases_file) as f:
            saved_cases = json.load(f)

        assert len(saved_cases) == 2
        assert saved_cases[0]["key"] == "TEST-TC-1"
        assert saved_cases[1]["key"] == "TEST-TC-2"

    def test_save_test_case(self, storage, output_dir):
        """Test saving a single test case appends to existing file."""
        # Save initial test case
        test_case1 = TestCase(
            id="tc1",
                key="TEST-TC-1",
                name="Test Case 1",
                status="Draft",
            )
        storage.save_test_case(test_case1, "TEST")

        # Save another test case
        test_case2 = TestCase(
            id="tc2",
                key="TEST-TC-2",
                name="Test Case 2",
                status="Ready",
            )
        storage.save_test_case(test_case2, "TEST")

        # Check the file has both test cases
        test_cases_file = output_dir / "test_cases.json"
        assert test_cases_file.exists()

        with open(test_cases_file) as f:
            saved_cases = json.load(f)

        assert len(saved_cases) == 2
        assert saved_cases[0]["key"] == "TEST-TC-1"
        assert saved_cases[1]["key"] == "TEST-TC-2"

        # Test updating an existing test case
        updated_case = TestCase(
            id="tc1",
                key="TEST-TC-1",
                name="Updated Test Case",
                status="Ready",
            )
        storage.save_test_case(updated_case, "TEST")

        with open(test_cases_file) as f:
            saved_cases = json.load(f)

        assert len(saved_cases) == 2  # Still only 2 cases
        assert saved_cases[0]["key"] == "TEST-TC-1"
        assert saved_cases[0]["name"] == "Updated Test Case"  # Name was updated
        assert saved_cases[0]["status"] == "Ready"  # Status was updated

    def test_serialize_object(self, storage):
        """Test serializing different types of objects."""
        # Pydantic model
        test_case = TestCase(
            id="tc1",
                key="TEST-TC-1",
                name="Test Case 1",
                status="Draft",
            )
        serialized = storage._serialize_object(test_case)
        assert isinstance(serialized, dict)
        assert serialized["id"] == "tc1"
        assert serialized["key"] == "TEST-TC-1"

        # Datetime
        dt = datetime(2023, 1, 1, 12, 0, 0)
        assert storage._serialize_object(dt) == "2023-01-01T12:00:00"

        # List of models
        models = [test_case, test_case]
        serialized_list = storage._serialize_object(models)
        assert isinstance(serialized_list, list)
        assert len(serialized_list) == 2
        assert serialized_list[0]["id"] == "tc1"

        # Dictionary with models
        model_dict = {"test_case": test_case, "dt": dt}
        serialized_dict = storage._serialize_object(model_dict)
        assert isinstance(serialized_dict, dict)
        assert serialized_dict["test_case"]["id"] == "tc1"
        assert serialized_dict["dt"] == "2023-01-01T12:00:00"
