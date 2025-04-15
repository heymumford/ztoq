"""
Tests for the validation integration module.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from ztoq.database_manager import DatabaseManager
from ztoq.migration import create_migration
from ztoq.models import ZephyrConfig
from ztoq.qtest_models import QTestConfig
from ztoq.validation import ValidationScope
from ztoq.validation_integration import (
    EnhancedMigration,
    MigrationValidationDecorators,
    get_enhanced_migration,
)


class TestValidationIntegration(unittest.TestCase):
    """Test cases for validation integration."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        # Create database manager
        self.db_manager = DatabaseManager(self.temp_db.name)
        self.db_manager.initialize_database()

        # Create test configs
        self.zephyr_config = ZephyrConfig(
            api_url="https://zephyr-api.example.com",
            api_key="test-api-key",
            project_key="TEST",
        )

        self.qtest_config = QTestConfig(
            api_url="https://qtest-api.example.com",
            api_key="test-api-key",
            project_id="12345",
        )

    def tearDown(self):
        """Clean up after tests."""
        os.unlink(self.temp_db.name)

    def test_get_enhanced_migration(self):
        """Test that get_enhanced_migration returns an EnhancedMigration instance."""
        # Create a mock migration
        mock_migration = MagicMock()

        # Get enhanced migration
        enhanced = get_enhanced_migration(mock_migration, self.db_manager, "TEST")

        # Assert that it's the correct type
        self.assertIsInstance(enhanced, EnhancedMigration)
        self.assertEqual(enhanced.project_key, "TEST")
        self.assertEqual(enhanced.db, self.db_manager)
        self.assertEqual(enhanced.migration, mock_migration)

    @patch("ztoq.zephyr_client.ZephyrClient")
    @patch("ztoq.qtest_client.QTestClient")
    def test_create_migration_with_validation(self, mock_qtest_client, mock_zephyr_client):
        """Test that create_migration creates a migration with validation enabled."""
        # Use the factory function to create a migration
        migration = create_migration(
            zephyr_config=self.zephyr_config,
            qtest_config=self.qtest_config,
            database_manager=self.db_manager,
            enable_validation=True,
        )

        # Assert that it's an enhanced migration
        self.assertIsInstance(migration, EnhancedMigration)

        # Check that the validator is initialized
        self.assertIsNotNone(migration.validator)

    @patch("ztoq.zephyr_client.ZephyrClient")
    @patch("ztoq.qtest_client.QTestClient")
    def test_create_migration_without_validation(self, mock_qtest_client, mock_zephyr_client):
        """Test that create_migration creates a migration without validation when disabled."""
        # Use the factory function to create a migration with validation disabled
        migration = create_migration(
            zephyr_config=self.zephyr_config,
            qtest_config=self.qtest_config,
            database_manager=self.db_manager,
            enable_validation=False,
        )

        # Assert that it's not an enhanced migration
        self.assertNotIsInstance(migration, EnhancedMigration)

    def test_migration_validation_decorators(self):
        """Test that the MigrationValidationDecorators class works as expected."""
        # Create a mock validation manager
        mock_validation_manager = MagicMock()

        # Create the decorators
        decorators = MigrationValidationDecorators(mock_validation_manager)

        # Create a test function to decorate
        def test_func(entity_id=None):
            return f"processed {entity_id}"

        # Decorate the function
        decorated = decorators.validate_extraction(ValidationScope.TEST_CASE)(test_func)

        # Call the decorated function
        result = decorated(entity_id="123")

        # Assert that the result is correct
        self.assertEqual(result, "processed 123")

        # Assert that validation manager methods were called
        mock_validation_manager.run_validation.assert_called()


if __name__ == "__main__":
    unittest.main()
