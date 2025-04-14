"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ztoq.core.db_models import Base, MigrationStateModel
from ztoq.database_manager import DatabaseManager
from ztoq.migration import ZephyrToQTestMigration
from ztoq.models import ZephyrConfig
from ztoq.qtest_models import QTestConfig

@pytest.mark.integration()


class TestMigrationETLIntegration:
    """Integration tests for the full ETL migration workflow with a real SQLite database."""

    @pytest.fixture()
    def db_path(self):
        """Create a temporary SQLite database file for testing."""
        temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db_file.close()

        # Create database URL
        db_url = f"sqlite:///{temp_db_file.name}"

        yield db_url

        # Clean up the database file after tests
        os.unlink(temp_db_file.name)

    @pytest.fixture()
    def db_manager(self, db_path):
        """Create a real database manager with a SQLite database."""
        # Create engine and initialize database
        engine = create_engine(db_path)
        Base.metadata.create_all(engine)

        # Create session factory
        Session = sessionmaker(bind=engine)

        # Create database manager using real implementation
        db_manager = DatabaseManager(engine, Session())

        return db_manager

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
    def migration(self, zephyr_config, qtest_config, db_manager):
        """Create a migration manager with mocked API clients but real database."""
        with patch("ztoq.migration.ZephyrClient") as mock_zephyr, patch(
            "ztoq.migration.QTestClient"
        ) as mock_qtest:
            # Configure mocks
            mock_zephyr_client = MagicMock()
            mock_qtest_client = MagicMock()

            # Configure Zephyr client mock responses
            mock_zephyr_client.get_project.return_value = {
                "id": "10001",
                    "key": "DEMO",
                    "name": "Demo Project",
                    "description": "Project for testing migrations"
            }

            mock_zephyr_client.get_folders.return_value = [
                {"id": "folder-1", "name": "Folder 1", "parentId": None, "description": "Root folder"},
                    {"id": "folder-2", "name": "Folder 2", "parentId": "folder-1", "description": "Subfolder"}
            ]

            mock_zephyr_client.get_test_cases.return_value = [
                {
                    "id": "tc-001",
                        "name": "Test Case 1",
                        "description": "First test case",
                        "precondition": "System is running",
                        "folderId": "folder-2",
                        "priority": "high",
                        "attachments": []
                }
            ]

            mock_zephyr_client.get_test_steps.return_value = [
                {"id": "step-1", "description": "Step 1", "expectedResult": "Result 1"}
            ]

            mock_zephyr_client.get_test_cycles.return_value = [
                {
                    "id": "cycle-1",
                        "name": "Sprint 1",
                        "description": "First sprint cycle",
                        "folderId": "folder-1",
                        "startDate": "2025-01-01",
                        "endDate": "2025-01-15"
                }
            ]

            mock_zephyr_client.get_test_executions.return_value = [
                {
                    "id": "exec-1",
                        "testCaseId": "tc-001",
                        "testCycleId": "cycle-1",
                        "status": "pass",
                        "executionTime": "2025-01-02",
                        "comment": "All tests passed",
                        "attachments": []
                }
            ]

            # Configure qTest client mock responses for entity creation
            # These should return objects with ID values
            mock_qtest_client.create_module.return_value = MagicMock(id="qmodule-1")
            mock_qtest_client.create_test_case.return_value = MagicMock(id="qtc-1")
            mock_qtest_client.create_test_cycle.return_value = MagicMock(id="qcycle-1")
            mock_qtest_client.create_test_run.return_value = MagicMock(id="qrun-1")

            mock_zephyr.return_value = mock_zephyr_client
            mock_qtest.return_value = mock_qtest_client

            # Create temp directory for attachments
            temp_dir = tempfile.TemporaryDirectory()
            attachments_dir = Path(temp_dir.name)

            migration = ZephyrToQTestMigration(
                zephyr_config,
                    qtest_config,
                    db_manager,
                    batch_size=10,
                    max_workers=2,
                    attachments_dir=attachments_dir
            )

            # Store mocks in migration for test access
            migration.zephyr_client_mock = mock_zephyr_client
            migration.qtest_client_mock = mock_qtest_client
            migration.temp_dir = temp_dir

            yield migration

            # Clean up temp directory
            temp_dir.cleanup()

    def test_full_etl_workflow(self, migration, db_manager):
        """Test the complete ETL workflow with a real SQLite database."""
        # Run the full migration
        migration.run_migration()

        # Check final migration state in database
        session = db_manager.session
        migration_state = session.query(MigrationStateModel).filter_by(
            project_key=migration.zephyr_config.project_key
        ).first()

        assert migration_state is not None
        assert migration_state.extraction_status == "completed"
        assert migration_state.transformation_status == "completed"
        assert migration_state.loading_status == "completed"

        # Check entity counts in database
        # These queries would vary based on your actual schema
        folder_count = db_manager.get_folders_count(migration.zephyr_config.project_key)
        assert folder_count == 2

        test_case_count = db_manager.get_test_cases_count(migration.zephyr_config.project_key)
        assert test_case_count == 1

        test_cycle_count = db_manager.get_test_cycles_count(migration.zephyr_config.project_key)
        assert test_cycle_count == 1

        execution_count = db_manager.get_test_executions_count(migration.zephyr_config.project_key)
        assert execution_count == 1

        # Check that entity mappings were created
        folder_mappings = db_manager.get_entity_mappings(
            migration.zephyr_config.project_key, "folder_to_module"
        )
        assert len(folder_mappings) == 2

        testcase_mappings = db_manager.get_entity_mappings(
            migration.zephyr_config.project_key, "testcase_to_testcase"
        )
        assert len(testcase_mappings) == 1

        cycle_mappings = db_manager.get_entity_mappings(
            migration.zephyr_config.project_key, "cycle_to_cycle"
        )
        assert len(cycle_mappings) == 1

        execution_mappings = db_manager.get_entity_mappings(
            migration.zephyr_config.project_key, "execution_to_run"
        )
        assert len(execution_mappings) == 1

    def test_migration_failure_recovery(self, migration, db_manager):
        """Test that a migration can recover from failures."""
        # Make transform_data fail
        original_transform = migration.transform_data

        def failing_transform():
            # Update state to in_progress first
            migration.state.update_transformation_status("in_progress")
            raise Exception("Simulated API failure during transformation")

        migration.transform_data = failing_transform

        # Run migration - should fail during transform
        with pytest.raises(Exception) as excinfo:
            migration.run_migration()

        assert "Simulated API failure" in str(excinfo.value)

        # Check migration state in database
        session = db_manager.session
        migration_state = session.query(MigrationStateModel).filter_by(
            project_key=migration.zephyr_config.project_key
        ).first()

        assert migration_state is not None
        assert migration_state.extraction_status == "completed"
        assert migration_state.transformation_status == "failed"
        assert migration_state.loading_status == "not_started"
        assert "Simulated API failure" in migration_state.error_message

        # Restore original transform method
        migration.transform_data = original_transform

        # Run migration again - should resume from transformation
        migration.run_migration()

        # Check updated migration state
        session.refresh(migration_state)
        assert migration_state.extraction_status == "completed"
        assert migration_state.transformation_status == "completed"
        assert migration_state.loading_status == "completed"
        assert migration_state.error_message is None

    def test_batch_tracking(self, migration, db_manager):
        """Test that batch tracking properly records progress in the database."""
        # Run the migration
        migration.run_migration()

        # Check batch records in database
        folder_batches = db_manager.get_entity_batches(
            migration.zephyr_config.project_key, "folders"
        )
        assert len(folder_batches) == 1  # 2 folders / 10 batch size = 1 batch
        assert folder_batches[0]["status"] == "completed"

        test_case_batches = db_manager.get_entity_batches(
            migration.zephyr_config.project_key, "test_cases"
        )
        assert len(test_case_batches) == 1  # 1 test case / 10 batch size = 1 batch
        assert test_case_batches[0]["status"] == "completed"

        # Check transformed entity batches
        transformed_test_case_batches = db_manager.get_entity_batches(
            migration.zephyr_config.project_key, "transformed_test_cases"
        )
        assert len(transformed_test_case_batches) == 1
        assert transformed_test_case_batches[0]["status"] == "completed"

        # Check loaded entity batches
        loaded_test_case_batches = db_manager.get_entity_batches(
            migration.zephyr_config.project_key, "loaded_test_cases"
        )
        assert len(loaded_test_case_batches) == 1
        assert loaded_test_case_batches[0]["status"] == "completed"
