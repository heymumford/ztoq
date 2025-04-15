"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Integration tests for custom field mapping during migration process.
"""

import unittest
from unittest.mock import MagicMock, patch
from ztoq.custom_field_mapping import CustomFieldMapper, get_default_field_mapper
from ztoq.migration import ZephyrToQTestMigration
from ztoq.models import CustomFieldType, ZephyrConfig
from ztoq.qtest_models import QTestConfig, QTestCustomField


class TestMigrationCustomFields(unittest.TestCase):
    """Integration tests for custom field mapping in the migration process."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock configuration
        self.zephyr_config = ZephyrConfig(
            base_url="https://zephyr.example.com", api_token="zephyr-token", project_key="TEST"
        )

        self.qtest_config = QTestConfig(
            base_url="https://qtest.example.com",
            username="qtest-user",
            password="qtest-password",
            project_id=123,
        )

        # Mock database manager
        self.db_manager = MagicMock()

        # Test data
        self.test_case = {
            "id": "tc-001",
            "key": "TEST-001",
            "name": "Test Case 1",
            "status": "Active",
            "priority": "High",
            "labels": ["regression", "api"],
            "customFields": [
                {"name": "Story Points", "type": CustomFieldType.NUMERIC, "value": 5},
                {"name": "Automated", "type": CustomFieldType.CHECKBOX, "value": True},
                {
                    "name": "Components",
                    "type": CustomFieldType.COMPONENT,
                    "value": [{"id": "comp1", "name": "API"}, {"id": "comp2", "name": "Backend"}],
                },
                {
                    "name": "Test Data",
                    "type": CustomFieldType.TABLE,
                    "value": [
                        {"id": 1, "input": "test input 1", "expected": "test output 1"},
                        {"id": 2, "input": "test input 2", "expected": "test output 2"},
                    ],
                },
            ],
        }

        self.test_execution = {
            "id": "exec-001",
            "testCaseId": "tc-001",
            "status": "PASS",
            "environment": "Production",
            "executedBy": "tester",
            "executedOn": "2023-01-01T10:00:00",
            "comment": "Test passed successfully",
            "steps": [
                {"id": "step-1", "status": "PASS", "actualResult": "As expected"},
                {"id": "step-2", "status": "PASS", "actualResult": "As expected"},
            ],
            "customFields": [
                {"name": "Browser", "type": CustomFieldType.TEXT, "value": "Chrome"},
                {
                    "name": "Version",
                    "type": CustomFieldType.VERSION,
                    "value": {"id": "ver-1", "name": "v1.0"},
                },
            ],
        }

        # We need to patch the client initialization in ZephyrToQTestMigration
        self.client_patcher = patch("ztoq.migration.ZephyrClient")
        self.qtest_client_patcher = patch("ztoq.migration.QTestClient")

        self.mock_zephyr_client = self.client_patcher.start()
        self.mock_qtest_client = self.qtest_client_patcher.start()

        # Make the mocks return themselves when instantiated
        mock_zephyr_instance = MagicMock()
        mock_qtest_instance = MagicMock()
        self.mock_zephyr_client.return_value = mock_zephyr_instance
        self.mock_qtest_client.return_value = mock_qtest_instance

        # Create migration instance
        self.migration = ZephyrToQTestMigration(
            zephyr_config=self.zephyr_config,
            qtest_config=self.qtest_config,
            database_manager=self.db_manager,
            enable_validation=False,
        )

        # Set up the field mapper
        self.field_mapper = get_default_field_mapper()
        self.migration.field_mapper = self.field_mapper

    def tearDown(self):
        """Tear down test fixtures."""
        self.client_patcher.stop()
        self.qtest_client_patcher.stop()

    def test_test_case_custom_field_mapping(self):
        """Test mapping of test case custom fields using the mapper directly."""
        # Test the field mapper directly, not through the migration process
        mapped_fields = self.field_mapper.map_testcase_fields(self.test_case)

        # Verify the mapping
        self.assertIsInstance(mapped_fields, list)

        # Check Zephyr key field
        zephyr_key_field = next((f for f in mapped_fields if f.field_name == "zephyr_key"), None)
        self.assertIsNotNone(zephyr_key_field)
        self.assertEqual(zephyr_key_field.field_value, "TEST-001")

        # Check numeric field (Story Points)
        points_field = next((f for f in mapped_fields if f.field_name == "story_points"), None)
        self.assertIsNotNone(points_field)
        self.assertEqual(points_field.field_value, 5)

        # Check boolean field (Automated) - this maps to "Automation" in the field mappings
        automated_field = next((f for f in mapped_fields if f.field_name == "Automation"), None)
        self.assertIsNotNone(automated_field)
        self.assertTrue(automated_field.field_value)

        # Check components field (hierarchical)
        components_field = next(
            (f for f in mapped_fields if f.field_name.lower() == "components"), None
        )
        self.assertIsNotNone(components_field)
        components_value = str(components_field.field_value)
        self.assertIn("API", components_value)
        self.assertIn("Backend", components_value)

        # Check table field (Test Data)
        test_data_field = next((f for f in mapped_fields if f.field_name == "test_data"), None)
        self.assertIsNotNone(test_data_field)
        test_data_value = str(test_data_field.field_value)
        self.assertIn("input", test_data_value)
        self.assertIn("expected", test_data_value)
        self.assertIn("test input 1", test_data_value)
        self.assertIn("test output 2", test_data_value)

    def test_test_execution_custom_field_mapping(self):
        """Test mapping of test execution custom fields using the mapper directly."""
        # Test the field mapper directly, not through the migration process
        mapped_fields = self.field_mapper.map_testrun_fields(self.test_execution)

        # Verify the mapping
        self.assertIsInstance(mapped_fields, list)

        # Check environment field
        env_field = next((f for f in mapped_fields if f.field_name == "environment"), None)
        self.assertIsNotNone(env_field)
        self.assertEqual(env_field.field_value, "Production")

        # Check browser field
        browser_field = next((f for f in mapped_fields if f.field_name == "browser"), None)
        self.assertIsNotNone(browser_field)
        self.assertEqual(browser_field.field_value, "Chrome")

        # Check version field (hierarchical)
        version_field = next((f for f in mapped_fields if f.field_name.lower() == "version"), None)
        self.assertIsNotNone(version_field)
        version_value = str(version_field.field_value)
        self.assertEqual(version_value, "v1.0")

        # Test direct status mapping
        status = self.field_mapper.map_status("PASS")
        self.assertEqual(status, "PASSED")

        # Check additional status mappings
        self.assertEqual(self.field_mapper.map_status("FAIL"), "FAILED")
        self.assertEqual(self.field_mapper.map_status("BLOCKED"), "BLOCKED")
        self.assertEqual(self.field_mapper.map_status("NOT EXECUTED"), "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
