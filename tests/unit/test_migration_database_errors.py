"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

from unittest.mock import MagicMock, call, patch

import pytest

from ztoq.migration import MigrationState, ZephyrToQTestMigration
from ztoq.models import ZephyrConfig
from ztoq.qtest_models import QTestConfig


@pytest.mark.unit
class TestMigrationDatabaseErrors:
    """Test cases for database error handling in the ETL migration process."""

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
    def migration(self, zephyr_config, qtest_config):
        """Create a test migration manager with mocked clients and database."""
        with patch("ztoq.migration.ZephyrClient") as mock_zephyr, \
             patch("ztoq.migration.QTestClient") as mock_qtest:
            
            # Set up mock clients
            mock_zephyr_client = MagicMock()
            mock_qtest_client = MagicMock()

            mock_zephyr.return_value = mock_zephyr_client
            mock_qtest.return_value = mock_qtest_client
            
            # For each test, a new db_mock will be created
            db_mock = MagicMock()
            
            # Initialize with empty state
            db_mock.get_migration_state.return_value = None
            db_mock.get_entity_mappings.return_value = []

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
            migration.db_mock = db_mock

            yield migration

    def test_database_connection_error_during_state_load(self, zephyr_config, qtest_config):
        """Test handling of database connection errors during state loading."""
        # Create a database mock that raises an exception on get_migration_state
        db_mock = MagicMock()
        db_mock.get_migration_state.side_effect = Exception("Database connection error")
        
        # Create migration with failing database
        with patch("ztoq.migration.ZephyrClient"), patch("ztoq.migration.QTestClient"):
            # Should raise the database error when initializing
            with pytest.raises(Exception) as excinfo:
                migration = ZephyrToQTestMigration(
                    zephyr_config, qtest_config, db_mock
                )
            
            assert "Database connection error" in str(excinfo.value)

    def test_state_update_with_database_error(self, migration):
        """Test state update with database error."""
        # Make update_migration_state raise an error
        migration.db_mock.update_migration_state.side_effect = Exception("Database constraint violation")
        
        # Mock methods to avoid errors
        migration.state.extraction_status = "in_progress"
        
        # Test update method
        with pytest.raises(Exception) as excinfo:
            migration.state.update_extraction_status("completed")
            
        assert "Database constraint violation" in str(excinfo.value)

    def test_database_corruption_handling(self, migration):
        """Test handling of corrupted migration state in database."""
        # Set up a corrupted state
        migration.db_mock.get_migration_state.return_value = {
            "extraction_status": "completed",
            # Missing required fields
            "loading_status": "invalid_status",
            "error_message": "Database corruption detected",
        }
        
        # Create a new state to test loading corrupted data
        state = MigrationState("TEST", migration.db_mock)
        
        # Verify defaults are used for missing fields
        assert state.extraction_status == "completed"
        assert state.transformation_status == "not_started"  # Default
        assert state.loading_status == "invalid_status"
        assert state.error_message == "Database corruption detected"