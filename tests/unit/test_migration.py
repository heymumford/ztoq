"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

from unittest.mock import MagicMock, call, patch

import pytest

from ztoq.migration import EntityBatchTracker, MigrationState, ZephyrToQTestMigration
from ztoq.models import ZephyrConfig
from ztoq.qtest_models import QTestConfig


@pytest.mark.unit
class TestMigrationState:
    @pytest.fixture
    def db_mock(self):
        """Create a mock database manager."""
        db = MagicMock()
        db.get_migration_state.return_value = None
        return db

    @pytest.fixture
    def state(self, db_mock):
        """Create a test migration state."""
        return MigrationState("DEMO", db_mock)

    def test_initialization(self, state, db_mock):
        """Test migration state initialization."""
        assert state.project_key == "DEMO"
        assert state.db == db_mock
        assert state.extraction_status == "not_started"
        assert state.transformation_status == "not_started"
        assert state.loading_status == "not_started"
        assert state.error_message is None

        # Test loading existing state
        db_mock.get_migration_state.return_value = {
            "extraction_status": "completed",
            "transformation_status": "in_progress",
            "loading_status": "not_started",
            "error_message": None,
        }

        state = MigrationState("DEMO", db_mock)
        assert state.extraction_status == "completed"
        assert state.transformation_status == "in_progress"
        assert state.loading_status == "not_started"

    def test_update_extraction_status(self, state, db_mock):
        """Test updating extraction status."""
        state.update_extraction_status("in_progress")
        assert state.extraction_status == "in_progress"
        db_mock.update_migration_state.assert_called_once_with(
            "DEMO", extraction_status="in_progress", error_message=None,
        )

        # With error
        state.update_extraction_status("failed", "API error")
        assert state.extraction_status == "failed"
        assert state.error_message == "API error"

    def test_can_extract(self, state):
        """Test can_extract method."""
        # Initial state
        assert state.can_extract() is True

        # In progress
        state.extraction_status = "in_progress"
        assert state.can_extract() is True

        # Failed
        state.extraction_status = "failed"
        assert state.can_extract() is True

        # Completed
        state.extraction_status = "completed"
        assert state.can_extract() is False


@pytest.mark.unit
class TestEntityBatchTracker:
    @pytest.fixture
    def db_mock(self):
        """Create a mock database manager."""
        return MagicMock()

    @pytest.fixture
    def tracker(self, db_mock):
        """Create a test entity batch tracker."""
        return EntityBatchTracker("DEMO", "test_cases", db_mock)

    def test_initialization(self, tracker, db_mock):
        """Test entity batch tracker initialization."""
        assert tracker.project_key == "DEMO"
        assert tracker.entity_type == "test_cases"
        assert tracker.db == db_mock

    def test_initialize_batches(self, tracker, db_mock):
        """Test initializing batches."""
        tracker.initialize_batches(120, 50)

        # Should create 3 batches (120 items with batch size 50)
        assert db_mock.create_entity_batch.call_count == 3

        # Check calls
        calls = [
            call("DEMO", "test_cases", 0, 3, 50),  # First batch: 50 items
            call("DEMO", "test_cases", 1, 3, 50),  # Second batch: 50 items
            call("DEMO", "test_cases", 2, 3, 20),  # Third batch: 20 items
        ]
        db_mock.create_entity_batch.assert_has_calls(calls)


@pytest.mark.unit
class TestZephyrToQTestMigration:
    @pytest.fixture
    def zephyr_config(self):
        """Create a test Zephyr configuration."""
        return ZephyrConfig(
            base_url="https://api.zephyrscale.example.com/v2",
            api_token="zephyr-token",
            project_key="DEMO",
        )

    @pytest.fixture
    def qtest_config(self):
        """Create a test qTest configuration."""
        return QTestConfig(
            base_url="https://example.qtest.com",
            username="test-user",
            password="test-password",
            project_id=12345,
        )

    @pytest.fixture
    def db_mock(self):
        """Create a mock database manager."""
        db = MagicMock()
        # Mock initial migration state
        db.get_migration_state.return_value = None
        # Mock empty mappings
        db.get_entity_mappings.return_value = []
        return db

    @pytest.fixture
    def migration(self, zephyr_config, qtest_config, db_mock):
        """Create a test migration manager with mocked clients."""
        with patch("ztoq.migration.ZephyrClient") as mock_zephyr, patch(
            "ztoq.migration.QTestClient",
        ) as mock_qtest:
            # Configure mocks
            mock_zephyr_client = MagicMock()
            mock_qtest_client = MagicMock()

            mock_zephyr.return_value = mock_zephyr_client
            mock_qtest.return_value = mock_qtest_client

            migration = ZephyrToQTestMigration(
                zephyr_config, qtest_config, db_mock, batch_size=50, max_workers=5,
            )

            # Store mocks in migration for test access
            migration.zephyr_client_mock = mock_zephyr_client
            migration.qtest_client_mock = mock_qtest_client

            return migration

    def test_initialization(self, migration, zephyr_config, qtest_config, db_mock):
        """Test migration manager initialization."""
        assert migration.zephyr_config == zephyr_config
        assert migration.qtest_config == qtest_config
        assert migration.db == db_mock
        assert migration.batch_size == 50
        assert migration.max_workers == 5
        assert migration.attachments_dir is None
        assert migration.state.project_key == "DEMO"

        # Entity mappings should be initialized as empty
        assert migration.entity_mappings == {
            "folders": {},
            "test_cases": {},
            "test_cycles": {},
            "test_executions": {},
        }

    def test_run_migration_all_phases(self, migration):
        """Test running a full migration (all phases)."""
        # Mock methods
        migration.extract_data = MagicMock()
        migration.transform_data = MagicMock()
        migration.load_data = MagicMock()

        # Allow all phases
        migration.state.extraction_status = "not_started"
        migration.state.transformation_status = "not_started"
        migration.state.loading_status = "not_started"

        # Run migration
        migration.run_migration()

        # Verify all phases were called
        migration.extract_data.assert_called_once()
        migration.transform_data.assert_called_once()
        migration.load_data.assert_called_once()

    def test_run_migration_specific_phases(self, migration):
        """Test running specific migration phases."""
        # Mock methods
        migration.extract_data = MagicMock()
        migration.transform_data = MagicMock()
        migration.load_data = MagicMock()

        # Allow all phases
        migration.state.extraction_status = "not_started"
        migration.state.transformation_status = "not_started"
        migration.state.loading_status = "not_started"

        # Run only extract and transform
        migration.run_migration(phases=["extract", "transform"])

        # Verify only specified phases were called
        migration.extract_data.assert_called_once()
        migration.transform_data.assert_called_once()
        migration.load_data.assert_not_called()
