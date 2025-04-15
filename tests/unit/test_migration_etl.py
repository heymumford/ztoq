"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch
import pytest
from ztoq.migration import ZephyrToQTestMigration
from ztoq.models import ZephyrConfig
from ztoq.qtest_models import QTestConfig, QTestModule, QTestTestCase, QTestTestCycle, QTestTestRun


@pytest.mark.unit()
class TestMigrationETLProcess:
    @pytest.fixture()
    def zephyr_config(self):
        """Create a test Zephyr configuration."""
        return ZephyrConfig(
            base_url="https://api.zephyrscale.example.com/v2",
            api_token="zephyr-token",
            project_key="DEMO",
        )

    @pytest.fixture()
    def qtest_config(self):
        """Create a test qTest configuration."""
        return QTestConfig(
            base_url="https://example.qtest.com",
            username="test-user",
            password="test-password",
            project_id=12345,
        )

    @pytest.fixture()
    def db_mock(self):
        """Create a mock database manager with test data."""
        db = MagicMock()

        # Set up basic mock returns
        db.get_migration_state.return_value = None
        db.get_entity_mappings.return_value = []

        # Mock project data
        db.get_project.return_value = {
            "id": "10001",
            "key": "DEMO",
            "name": "Demo Project",
            "description": "Project for testing migrations",
        }

        # Mock folder data
        db.get_folders.return_value = [
            {"id": "folder-1", "name": "Folder 1", "parentId": None, "description": "Root folder"},
            {
                "id": "folder-2",
                "name": "Folder 2",
                "parentId": "folder-1",
                "description": "Subfolder",
            },
            {
                "id": "folder-3",
                "name": "Folder 3",
                "parentId": "folder-1",
                "description": "Another subfolder",
            },
        ]

        # Mock test case data
        db.get_test_cases_with_steps.return_value = [
            {
                "id": "tc-001",
                "name": "Test Case 1",
                "description": "First test case",
                "precondition": "System is running",
                "folderId": "folder-2",
                "priority": "high",
                "steps": [
                    {"id": "step-1", "description": "Step 1", "expectedResult": "Result 1"},
                    {"id": "step-2", "description": "Step 2", "expectedResult": "Result 2"},
                ],
                "customFields": {"field1": "value1", "field2": True},
            },
            {
                "id": "tc-002",
                "name": "Test Case 2",
                "description": "Second test case",
                "precondition": "User is logged in",
                "folderId": "folder-3",
                "priority": "medium",
                "steps": [{"id": "step-3", "description": "Step 3", "expectedResult": "Result 3"}],
                "customFields": {"field1": "value2", "field3": 42},
            },
        ]

        # Mock test cycle data
        db.get_test_cycles.return_value = [
            {
                "id": "cycle-1",
                "name": "Sprint 1",
                "description": "First sprint cycle",
                "folderId": "folder-1",
                "startDate": "2025-01-01",
                "endDate": "2025-01-15",
            },
            {
                "id": "cycle-2",
                "name": "Sprint 2",
                "description": "Second sprint cycle",
                "folderId": "folder-2",
                "startDate": "2025-01-16",
                "endDate": "2025-01-31",
            },
        ]

        # Mock test execution data
        db.get_test_executions.return_value = [
            {
                "id": "exec-1",
                "testCaseId": "tc-001",
                "testCycleId": "cycle-1",
                "status": "pass",
                "executionTime": "2025-01-02",
                "comment": "All tests passed",
            },
            {
                "id": "exec-2",
                "testCaseId": "tc-002",
                "testCycleId": "cycle-1",
                "status": "fail",
                "executionTime": "2025-01-03",
                "comment": "Failed at step 3",
            },
        ]

        # Mock attachments
        db.get_attachments.side_effect = lambda entity_type, entity_id: (
            [{"name": "attachment1.png", "content": b"mock-image-data"}]
            if entity_id == "tc-001" and entity_type == "TestCase"
            else []
        )

        # Set up mock entity mapping
        def mock_get_entity_mapping(project_key, mapping_type, source_id):
            if mapping_type == "folder_to_module":
                if source_id == "folder-1":
                    return {"source_id": source_id, "target_id": "module-1"}
                elif source_id == "folder-2":
                    return {"source_id": source_id, "target_id": "module-2"}
                elif source_id == "folder-3":
                    return {"source_id": source_id, "target_id": "module-3"}
            elif mapping_type == "testcase_to_testcase":
                if source_id == "tc-001":
                    return {"source_id": source_id, "target_id": "qtc-001"}
                elif source_id == "tc-002":
                    return {"source_id": source_id, "target_id": "qtc-002"}
            elif mapping_type == "cycle_to_cycle":
                if source_id == "cycle-1":
                    return {"source_id": source_id, "target_id": "qcycle-001"}
                elif source_id == "cycle-2":
                    return {"source_id": source_id, "target_id": "qcycle-002"}
            return None

        db.get_entity_mapping.side_effect = mock_get_entity_mapping

        # Mock transformed data
        db.get_transformed_modules_by_level.return_value = [
            # Level 0 (root modules)
            [
                {
                    "source_id": "folder-1",
                    "module": {"name": "Folder 1", "description": "Root folder", "parent_id": None},
                }
            ],
            # Level 1 (child modules)
            [
                {
                    "source_id": "folder-2",
                    "module": {
                        "name": "Folder 2",
                        "description": "Subfolder",
                        "parent_id": "module-1",
                    },
                },
                {
                    "source_id": "folder-3",
                    "module": {
                        "name": "Folder 3",
                        "description": "Another subfolder",
                        "parent_id": "module-1",
                    },
                },
            ],
        ]

        db.get_transformed_test_cases.return_value = [
            {
                "source_id": "tc-001",
                "test_case": {
                    "name": "Test Case 1",
                    "description": "First test case",
                    "precondition": "System is running",
                    "module_id": "module-2",
                    "priority_id": 2,
                    "test_steps": [
                        {"description": "Step 1", "expected_result": "Result 1", "order": 1},
                        {"description": "Step 2", "expected_result": "Result 2", "order": 2},
                    ],
                    "properties": [
                        {"field_name": "field1", "field_type": "STRING", "field_value": "value1"},
                        {"field_name": "field2", "field_type": "BOOLEAN", "field_value": "true"},
                    ],
                },
            },
            {
                "source_id": "tc-002",
                "test_case": {
                    "name": "Test Case 2",
                    "description": "Second test case",
                    "precondition": "User is logged in",
                    "module_id": "module-3",
                    "priority_id": 3,
                    "test_steps": [
                        {"description": "Step 3", "expected_result": "Result 3", "order": 1}
                    ],
                    "properties": [
                        {"field_name": "field1", "field_type": "STRING", "field_value": "value2"},
                        {"field_name": "field3", "field_type": "NUMBER", "field_value": "42"},
                    ],
                },
            },
        ]

        db.get_transformed_test_cycles.return_value = [
            {
                "source_id": "cycle-1",
                "test_cycle": {
                    "name": "Sprint 1",
                    "description": "First sprint cycle",
                    "parent_id": "module-1",
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-15",
                },
            },
            {
                "source_id": "cycle-2",
                "test_cycle": {
                    "name": "Sprint 2",
                    "description": "Second sprint cycle",
                    "parent_id": "module-2",
                    "start_date": "2025-01-16",
                    "end_date": "2025-01-31",
                },
            },
        ]

        db.get_transformed_executions.return_value = [
            {
                "source_id": "exec-1",
                "test_run": {
                    "name": "Run for tc-001 in cycle cycle-1",
                    "test_case_id": "qtc-001",
                    "test_cycle_id": "qcycle-001",
                },
                "test_log": {
                    "status": "PASSED",
                    "execution_date": "2025-01-02",
                    "note": "All tests passed",
                },
            },
            {
                "source_id": "exec-2",
                "test_run": {
                    "name": "Run for tc-002 in cycle cycle-1",
                    "test_case_id": "qtc-002",
                    "test_cycle_id": "qcycle-001",
                },
                "test_log": {
                    "status": "FAILED",
                    "execution_date": "2025-01-03",
                    "note": "Failed at step 3",
                },
            },
        ]

        return db

    @pytest.fixture()
    def migration(self, zephyr_config, qtest_config, db_mock):
        """Create a test migration manager with mocked clients."""
        with patch("ztoq.migration.ZephyrClient") as mock_zephyr, patch(
            "ztoq.migration.QTestClient"
        ) as mock_qtest:
            # Configure mocks
            mock_zephyr_client = MagicMock()
            mock_qtest_client = MagicMock()

            # Set up mock Zephyr client responses
            mock_zephyr_client.get_project.return_value = {
                "id": "10001",
                "key": "DEMO",
                "name": "Demo Project",
                "description": "Project for testing migrations",
            }

            mock_zephyr_client.get_folders.return_value = [
                {
                    "id": "folder-1",
                    "name": "Folder 1",
                    "parentId": None,
                    "description": "Root folder",
                },
                {
                    "id": "folder-2",
                    "name": "Folder 2",
                    "parentId": "folder-1",
                    "description": "Subfolder",
                },
                {
                    "id": "folder-3",
                    "name": "Folder 3",
                    "parentId": "folder-1",
                    "description": "Another subfolder",
                },
            ]

            mock_zephyr_client.get_test_cases.return_value = [
                {
                    "id": "tc-001",
                    "name": "Test Case 1",
                    "description": "First test case",
                    "precondition": "System is running",
                    "folderId": "folder-2",
                    "priority": "high",
                },
                {
                    "id": "tc-002",
                    "name": "Test Case 2",
                    "description": "Second test case",
                    "precondition": "User is logged in",
                    "folderId": "folder-3",
                    "priority": "medium",
                },
            ]

            mock_zephyr_client.get_test_steps.side_effect = lambda tc_id: (
                [
                    {"id": "step-1", "description": "Step 1", "expectedResult": "Result 1"},
                    {"id": "step-2", "description": "Step 2", "expectedResult": "Result 2"},
                ]
                if tc_id == "tc-001"
                else [{"id": "step-3", "description": "Step 3", "expectedResult": "Result 3"}]
            )

            mock_zephyr_client.get_test_cycles.return_value = [
                {
                    "id": "cycle-1",
                    "name": "Sprint 1",
                    "description": "First sprint cycle",
                    "folderId": "folder-1",
                    "startDate": "2025-01-01",
                    "endDate": "2025-01-15",
                },
                {
                    "id": "cycle-2",
                    "name": "Sprint 2",
                    "description": "Second sprint cycle",
                    "folderId": "folder-2",
                    "startDate": "2025-01-16",
                    "endDate": "2025-01-31",
                },
            ]

            mock_zephyr_client.get_test_executions.return_value = [
                {
                    "id": "exec-1",
                    "testCaseId": "tc-001",
                    "testCycleId": "cycle-1",
                    "status": "pass",
                    "executionTime": "2025-01-02",
                    "comment": "All tests passed",
                },
                {
                    "id": "exec-2",
                    "testCaseId": "tc-002",
                    "testCycleId": "cycle-1",
                    "status": "fail",
                    "executionTime": "2025-01-03",
                    "comment": "Failed at step 3",
                },
            ]

            mock_zephyr_client.download_attachment.return_value = b"mock-image-data"

            # Set up mock qTest client responses
            def create_module_side_effect(module):
                result = QTestModule(
                    id=f"qmodule-{module.name.lower().replace(' ', '-')}",
                    name=module.name,
                    description=module.description,
                    parent_id=module.parent_id,
                )
                return result

            mock_qtest_client.create_module.side_effect = create_module_side_effect

            def create_test_case_side_effect(test_case):
                result = QTestTestCase(
                    id=f"qtc-{test_case.name.lower().replace(' ', '-')}",
                    name=test_case.name,
                    description=test_case.description,
                    precondition=test_case.precondition,
                    module_id=test_case.module_id,
                    priority_id=test_case.priority_id,
                    test_steps=test_case.test_steps,
                    properties=test_case.properties,
                )
                return result

            mock_qtest_client.create_test_case.side_effect = create_test_case_side_effect

            def create_test_cycle_side_effect(test_cycle):
                result = QTestTestCycle(
                    id=f"qcycle-{test_cycle.name.lower().replace(' ', '-')}",
                    name=test_cycle.name,
                    description=test_cycle.description,
                    parent_id=test_cycle.parent_id,
                    start_date=test_cycle.start_date,
                    end_date=test_cycle.end_date,
                )
                return result

            mock_qtest_client.create_test_cycle.side_effect = create_test_cycle_side_effect

            def create_test_run_side_effect(test_run):
                result = QTestTestRun(
                    id=f"qrun-{test_run.test_case_id}-{test_run.test_cycle_id}",
                    name=test_run.name,
                    test_case_id=test_run.test_case_id,
                    test_cycle_id=test_run.test_cycle_id,
                )
                return result

            mock_qtest_client.create_test_run.side_effect = create_test_run_side_effect

            mock_zephyr.return_value = mock_zephyr_client
            mock_qtest.return_value = mock_qtest_client

            # Create temp directory for attachments
            temp_dir = tempfile.TemporaryDirectory()
            attachments_dir = Path(temp_dir.name)

            migration = ZephyrToQTestMigration(
                zephyr_config,
                qtest_config,
                db_mock,
                batch_size=10,
                max_workers=2,
                attachments_dir=attachments_dir,
            )

            # Store test objects for cleanup
            migration.zephyr_client_mock = mock_zephyr_client
            migration.qtest_client_mock = mock_qtest_client
            migration.temp_dir = temp_dir

            yield migration

            # Cleanup temp directory
            temp_dir.cleanup()

    def test_extract_data(self, migration, db_mock):
        """Test the extract_data phase of the migration."""
        migration.extract_data()

        # Verify state updates
        assert migration.state.extraction_status == "completed"

        # Verify Zephyr client calls
        migration.zephyr_client_mock.get_project.assert_called_once_with("DEMO")
        migration.zephyr_client_mock.get_folders.assert_called_once()
        migration.zephyr_client_mock.get_test_cases.assert_called_once()
        migration.zephyr_client_mock.get_test_cycles.assert_called_once()
        migration.zephyr_client_mock.get_test_executions.assert_called_once()

        # Verify database calls
        db_mock.save_project.assert_called_once()
        db_mock.save_folders.assert_called_once()
        db_mock.save_test_cases.assert_called_once()
        db_mock.save_test_cycles.assert_called_once()
        db_mock.save_test_executions.assert_called_once()

    def test_transform_data(self, migration, db_mock):
        """Test the transform_data phase of the migration."""
        # First ensure extraction status is completed
        migration.state.extraction_status = "completed"

        # Run transformation
        migration.transform_data()

        # Verify state updates
        assert migration.state.transformation_status == "completed"

        # Verify database calls
        db_mock.save_transformed_project.assert_called_once()
        db_mock.save_transformed_module.assert_has_calls(
            [
                call("DEMO", "folder-1", ANY),
                # The next calls depend on the recursive function implementation
            ],
            any_order=True,
        )
        db_mock.save_transformed_test_case.assert_has_calls(
            [call("DEMO", "tc-001", ANY), call("DEMO", "tc-002", ANY)], any_order=True
        )
        db_mock.save_transformed_test_cycle.assert_has_calls(
            [call("DEMO", "cycle-1", ANY), call("DEMO", "cycle-2", ANY)], any_order=True
        )
        db_mock.save_transformed_execution.assert_has_calls(
            [call("DEMO", "exec-1", ANY, ANY), call("DEMO", "exec-2", ANY, ANY)], any_order=True
        )

    def test_load_data(self, migration, db_mock):
        """Test the load_data phase of the migration."""
        # First ensure extraction and transformation are completed
        migration.state.extraction_status = "completed"
        migration.state.transformation_status = "completed"

        # Run loading
        migration.load_data()

        # Verify state updates
        assert migration.state.loading_status == "completed"

        # Verify qTest client calls for creating entities
        assert migration.qtest_client_mock.create_module.call_count > 0
        assert migration.qtest_client_mock.create_test_case.call_count > 0
        assert migration.qtest_client_mock.create_test_cycle.call_count > 0
        assert migration.qtest_client_mock.create_test_run.call_count > 0

        # Verify entity mappings were saved
        assert db_mock.save_entity_mapping.call_count > 0

    def test_extract_with_attachments(self, migration, db_mock):
        """Test extracting test cases with attachments."""
        # Add attachments to a test case
        test_case = {
            "id": "tc-001",
            "name": "Test Case with Attachments",
            "attachments": [
                {"id": "att-1", "filename": "screenshot.png", "url": "http://example.com/att-1"}
            ],
        }

        # Run the attachment extraction method
        migration._extract_test_case_attachments(test_case)

        # Verify attachment was downloaded and saved
        migration.zephyr_client_mock.download_attachment.assert_called_once_with("att-1")
        db_mock.save_attachment.assert_called_once_with(
            related_type="TestCase",
            related_id="tc-001",
            name="screenshot.png",
            content=b"mock-image-data",
            url="http://example.com/att-1",
        )

        # Verify attachment was saved to filesystem
        attachment_path = migration.attachments_dir / f"tc_tc-001_screenshot.png"
        assert os.path.exists(attachment_path)

    def test_handle_extraction_errors(self, migration, db_mock):
        """Test error handling during extraction phase."""
        # Make API calls raise exceptions
        migration.zephyr_client_mock.get_project.side_effect = Exception("API error")

        # Run extraction and verify error is caught
        with pytest.raises(Exception) as excinfo:
            migration.extract_data()

        assert "API error" in str(excinfo.value)
        assert migration.state.extraction_status == "failed"
        assert migration.state.error_message is not None

    def test_status_transitions(self, migration):
        """Test the state transitions during a complete migration."""
        # Set up mocks to avoid actual processing
        migration.extract_data = MagicMock()
        migration.transform_data = MagicMock()
        migration.load_data = MagicMock()

        # Initial state
        assert migration.state.extraction_status == "not_started"
        assert migration.state.transformation_status == "not_started"
        assert migration.state.loading_status == "not_started"

        # Simulate extract phase
        migration.state.update_extraction_status("in_progress")
        assert migration.state.can_extract() is True
        assert migration.state.can_transform() is False
        assert migration.state.can_load() is False

        migration.state.update_extraction_status("completed")
        assert migration.state.can_extract() is False
        assert migration.state.can_transform() is True
        assert migration.state.can_load() is False

        # Simulate transform phase
        migration.state.update_transformation_status("in_progress")
        assert migration.state.can_transform() is True

        migration.state.update_transformation_status("completed")
        assert migration.state.can_transform() is False
        assert migration.state.can_load() is True

        # Simulate load phase
        migration.state.update_loading_status("in_progress")
        assert migration.state.can_load() is True

        migration.state.update_loading_status("completed")
        assert migration.state.can_load() is False

    def test_map_priority(self, migration):
        """Test mapping of Zephyr priorities to qTest priority IDs."""
        assert migration._map_priority("highest") == 1
        assert migration._map_priority("high") == 2
        assert migration._map_priority("medium") == 3
        assert migration._map_priority("low") == 4
        assert migration._map_priority("lowest") == 5
        assert migration._map_priority("unknown") == 3  # Default to medium

    def test_map_status(self, migration):
        """Test mapping of Zephyr execution status to qTest status."""
        assert migration._map_status("pass") == "PASSED"
        assert migration._map_status("fail") == "FAILED"
        assert migration._map_status("wip") == "IN_PROGRESS"
        assert migration._map_status("blocked") == "BLOCKED"
        assert migration._map_status("unexecuted") == "NOT_RUN"
        assert migration._map_status("unknown") == "NOT_RUN"  # Default


@pytest.mark.unit()
class TestMigrationRestartability:
    """Test the ability to restart a migration from a specific point."""

    @pytest.fixture()
    def migration_with_progress(self):
        """Create a migration instance with some progress already made."""
        zephyr_config = ZephyrConfig(
            base_url="https://api.zephyrscale.example.com/v2",
            api_token="zephyr-token",
            project_key="DEMO",
        )

        qtest_config = QTestConfig(
            base_url="https://example.qtest.com",
            username="test-user",
            password="test-password",
            project_id=12345,
        )

        db_mock = MagicMock()

        # Mock migration that completed extraction but failed during transformation
        db_mock.get_migration_state.return_value = {
            "extraction_status": "completed",
            "transformation_status": "failed",
            "loading_status": "not_started",
            "error_message": "Transform error: API timeout",
        }

        # Empty mappings
        db_mock.get_entity_mappings.return_value = []

        with patch("ztoq.migration.ZephyrClient"), patch("ztoq.migration.QTestClient"):
            migration = ZephyrToQTestMigration(
                zephyr_config, qtest_config, db_mock, batch_size=50, max_workers=5
            )

            # Add mocks for the ETL methods
            migration.extract_data = MagicMock()
            migration.transform_data = MagicMock()
            migration.load_data = MagicMock()

            return migration

    def test_restart_after_extraction_failure(self, migration_with_progress):
        """Test restarting a migration after extraction failure."""
        # Set state to failed extraction
        migration_with_progress.state.extraction_status = "failed"
        migration_with_progress.state.transformation_status = "not_started"
        migration_with_progress.state.loading_status = "not_started"

        # Run the migration
        migration_with_progress.run_migration()

        # Should call extract but not transform or load
        migration_with_progress.extract_data.assert_called_once()
        migration_with_progress.transform_data.assert_not_called()
        migration_with_progress.load_data.assert_not_called()

    def test_restart_from_transformation(self, migration_with_progress):
        """Test restarting a migration from the transformation phase."""
        # State is already set to completed extraction, failed transformation

        # Run the migration
        migration_with_progress.run_migration()

        # Should not call extract, but should call transform
        migration_with_progress.extract_data.assert_not_called()
        migration_with_progress.transform_data.assert_called_once()
        migration_with_progress.load_data.assert_not_called()

    def test_run_specific_phase(self, migration_with_progress):
        """Test running only a specific phase of migration."""
        # Run only the load phase
        migration_with_progress.run_migration(phases=["load"])

        # Should only call load if it's allowed
        migration_with_progress.extract_data.assert_not_called()
        migration_with_progress.transform_data.assert_not_called()
        migration_with_progress.load_data.assert_not_called()  # Can't load yet

        # Now update state to allow loading
        migration_with_progress.state.transformation_status = "completed"

        # Try again
        migration_with_progress.run_migration(phases=["load"])

        # Now load should be called
        migration_with_progress.extract_data.assert_not_called()
        migration_with_progress.transform_data.assert_not_called()
        migration_with_progress.load_data.assert_called_once()
