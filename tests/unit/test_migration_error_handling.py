"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

from unittest.mock import MagicMock, patch

import pytest

from ztoq.migration import MigrationState, ZephyrToQTestMigration
from ztoq.models import ZephyrConfig
from ztoq.qtest_models import QTestConfig


@pytest.mark.unit
class TestMigrationErrorHandling:
    """Test cases for error handling in the ETL migration process."""

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
        db.get_migration_state.return_value = None
        db.get_entity_mappings.return_value = []
        return db

    @pytest.fixture
    def migration(self, zephyr_config, qtest_config, db_mock):
        """Create a test migration manager with mocked clients."""
        with patch("ztoq.migration.ZephyrClient") as mock_zephyr, patch(
            "ztoq.migration.QTestClient",
        ) as mock_qtest:
            # Set up mock clients
            mock_zephyr_client = MagicMock()
            mock_qtest_client = MagicMock()

            mock_zephyr.return_value = mock_zephyr_client
            mock_qtest.return_value = mock_qtest_client

            migration = ZephyrToQTestMigration(
                zephyr_config,
                qtest_config,
                db_mock,
                batch_size=10,
                max_workers=2,
            )

            # Store mocks for assertions
            migration.zephyr_client_mock = mock_zephyr_client
            migration.qtest_client_mock = mock_qtest_client

            yield migration

    def test_extraction_api_errors(self, migration, db_mock):
        """Test handling of API errors during extraction phase."""
        # Simulate API connection failure during project fetch
        migration.zephyr_client_mock.get_project.side_effect = Exception("Connection refused")

        # Run extraction and verify it fails properly
        with pytest.raises(Exception) as excinfo:
            migration.extract_data()

        assert "Connection refused" in str(excinfo.value)
        assert migration.state.extraction_status == "failed"
        assert migration.state.error_message is not None

    def test_extraction_database_errors(self, migration, db_mock):
        """Test handling of database errors during extraction phase."""
        # Set up successful API responses
        migration.zephyr_client_mock.get_project.return_value = {"id": "1", "key": "DEMO", "name": "Demo Project"}
        
        # Simulate database failure
        db_mock.save_project.side_effect = Exception("Database connection error")

        # Run extraction and verify it fails properly
        with pytest.raises(Exception) as excinfo:
            migration.extract_data()

        assert "Database connection error" in str(excinfo.value)
        assert migration.state.extraction_status == "failed"
        assert migration.state.error_message is not None

    def test_transformation_missing_data(self, migration, db_mock):
        """Test handling of missing data during transformation phase."""
        # Set extraction status to completed
        migration.state.extraction_status = "completed"
        
        # Make database return empty data
        db_mock.get_project.return_value = None

        # Run transformation and verify it fails with appropriate error
        with pytest.raises(Exception):
            migration.transform_data()

        assert migration.state.transformation_status == "failed"
        assert migration.state.error_message is not None

    def test_json_decode_error_handling(self, migration, db_mock):
        """Test handling of JSON decode errors in metadata."""
        # Create a mock state with invalid JSON
        db_mock.get_migration_state.return_value = {
            "meta_data": "{invalid json"  # Invalid JSON that will cause a parse error
        }
        
        # Create a new state instance that will parse the invalid JSON
        state = MigrationState("TEST", db_mock)
        
        # Accessing metadata_dict should handle the error gracefully
        metadata = state.metadata_dict
        
        # Should return empty dict on parse error
        assert metadata == {}


@pytest.mark.unit
class TestMigrationStateHandling:
    """Test cases for the MigrationState class."""
    
    @pytest.fixture
    def db_mock(self):
        """Create a mock database manager."""
        db = MagicMock()
        db.get_migration_state.return_value = None
        return db
    
    def test_state_initialization(self, db_mock):
        """Test initialization of migration state."""
        state = MigrationState("TEST", db_mock)
        
        # Check default values
        assert state.project_key == "TEST"
        assert state.extraction_status == "not_started"
        assert state.transformation_status == "not_started"
        assert state.loading_status == "not_started"
        assert state.rollback_status == "not_started"
        assert state.error_message is None
        assert state.is_incremental is False
        
        # Verify database was queried
        db_mock.get_migration_state.assert_called_once_with("TEST")
    
    def test_state_load_from_db(self, db_mock):
        """Test loading state from database."""
        db_mock.get_migration_state.return_value = {
            "extraction_status": "completed",
            "transformation_status": "in_progress",
            "loading_status": "not_started", 
            "rollback_status": "not_started",
            "error_message": "Test error",
            "is_incremental": True,
            "meta_data": '{"key": "value"}'
        }
        
        state = MigrationState("TEST", db_mock)
        
        # Verify values from database
        assert state.extraction_status == "completed"
        assert state.transformation_status == "in_progress"
        assert state.loading_status == "not_started"
        assert state.rollback_status == "not_started"
        assert state.error_message == "Test error"
        assert state.is_incremental is True