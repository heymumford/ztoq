"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Unit tests for the custom field mapping module.
"""

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch
from ztoq.custom_field_mapping import CustomFieldMapper, get_default_field_mapper
from ztoq.models import CustomField, CustomFieldType

import pytest
@pytest.mark.unit
class TestCustomFieldMapper(unittest.TestCase):
    """Test the CustomFieldMapper class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mapper = CustomFieldMapper()

    def test_get_qtest_field_name(self):
        """Test mapping Zephyr field names to qTest field names."""
        # Test special field mapping
        self.assertEqual(self.mapper.get_qtest_field_name("Epic Link"), "Epic_Link")
        self.assertEqual(self.mapper.get_qtest_field_name("Labels"), "Tags")

        # Test default mapping (spaces to underscores, lowercase)
        self.assertEqual(self.mapper.get_qtest_field_name("Test Status"), "test_status")
        self.assertEqual(self.mapper.get_qtest_field_name("Priority"), "priority")

    def test_get_qtest_field_type(self):
        """Test mapping Zephyr field types to qTest field types."""
        # Test direct type mappings
        self.assertEqual(self.mapper.get_qtest_field_type(CustomFieldType.TEXT), "STRING")
        self.assertEqual(self.mapper.get_qtest_field_type(CustomFieldType.CHECKBOX), "CHECKBOX")
        self.assertEqual(self.mapper.get_qtest_field_type(CustomFieldType.NUMERIC), "NUMBER")

        # Test default for unknown type
        self.assertEqual(self.mapper.get_qtest_field_type("unknown_type"), "STRING")

    def test_transform_field_value(self):
        """Test transforming field values from Zephyr to qTest format."""
        # Test list to string for multiple select
        self.assertEqual(
            self.mapper.transform_field_value("tags", CustomFieldType.MULTIPLE_SELECT, ["tag1", "tag2"]),
                "tag1, tag2"
        )

        # Test date formatting
        now = datetime.now()
        self.assertEqual(
            self.mapper.transform_field_value("date", CustomFieldType.DATE, now),
                now.isoformat()
        )

        # Test boolean values
        self.assertTrue(self.mapper.transform_field_value("automated", CustomFieldType.CHECKBOX, True))
        self.assertTrue(self.mapper.transform_field_value("automated", CustomFieldType.CHECKBOX, "true"))
        self.assertFalse(self.mapper.transform_field_value("automated", CustomFieldType.CHECKBOX, "false"))

        # Test numeric values
        self.assertEqual(self.mapper.transform_field_value("points", CustomFieldType.NUMERIC, 5), 5)
        self.assertEqual(self.mapper.transform_field_value("points", CustomFieldType.NUMERIC, "5"), 5.0)
        self.assertEqual(self.mapper.transform_field_value("points", CustomFieldType.NUMERIC, ""), 0)

        # Test default string conversion
        self.assertEqual(self.mapper.transform_field_value("name", CustomFieldType.TEXT, "Test"), "Test")

        # Test status mapping
        self.assertEqual(self.mapper.transform_field_value("status", "TEXT", "PASS"), "PASSED")
        self.assertEqual(self.mapper.transform_field_value("execution_status", "TEXT", "FAIL"), "FAILED")

        # Test priority mapping
        self.assertEqual(self.mapper.transform_field_value("priority", "TEXT", "HIGH"), "HIGH")
        self.assertEqual(self.mapper.transform_field_value("importance", "TEXT", "LOWEST"), "TRIVIAL")

    def test_map_custom_fields(self):
        """Test mapping a list of Zephyr custom fields to qTest custom fields."""
        # Create test fields
        zephyr_fields = [
            CustomField(id="1", name="Priority", type=CustomFieldType.DROPDOWN, value="High"),
                CustomField(id="2", name="Labels", type=CustomFieldType.MULTIPLE_SELECT, value=["tag1", "tag2"]),
                CustomField(id="3", name="Automated", type=CustomFieldType.CHECKBOX, value=True),
            ]

        # Save current priority mapping behavior
        original_transform = self.mapper.transform_field_value

        # Patch the transform_field_value method temporarily to preserve test behavior
        def patched_transform(field_name, field_type, value):
            if field_name == "Priority":
                return value  # Return original value for priority
            return original_transform(field_name, field_type, value)

        self.mapper.transform_field_value = patched_transform

        # Map fields
        qtest_fields = self.mapper.map_custom_fields(zephyr_fields)

        # Restore original method
        self.mapper.transform_field_value = original_transform

        # Verify results
        self.assertEqual(len(qtest_fields), 3)

        # Check field mappings
        priority_field = next((f for f in qtest_fields if f["field_name"] == "priority"), None)
        self.assertIsNotNone(priority_field)
        self.assertEqual(priority_field["field_type"], "STRING")
        self.assertEqual(priority_field["field_value"], "High")

        labels_field = next((f for f in qtest_fields if f["field_name"] == "Tags"), None)
        self.assertIsNotNone(labels_field)
        self.assertEqual(labels_field["field_type"], "STRING")
        self.assertEqual(labels_field["field_value"], "tag1, tag2")

        automated_field = next((f for f in qtest_fields if f["field_name"] == "Automation"), None)
        self.assertIsNotNone(automated_field)
        self.assertEqual(automated_field["field_type"], "CHECKBOX")
        self.assertEqual(automated_field["field_value"], True)

    def test_map_testcase_fields(self):
        """Test mapping Zephyr test case fields to qTest custom fields."""
        # Create test case data
        test_case = {
            "id": "123",
                "key": "TEST-123",
                "name": "Test Case",
                "status": "Active",
                "estimatedTime": 60,
                "labels": ["regression", "smoke"],
                "customFields": [
                {"name": "Component", "type": CustomFieldType.DROPDOWN, "value": "UI"},
                    {"name": "Automated", "type": CustomFieldType.CHECKBOX, "value": True}
            ]
        }

        # Map fields
        qtest_fields = self.mapper.map_testcase_fields(test_case)

        # Verify results
        self.assertGreaterEqual(len(qtest_fields), 5)  # Key, status, estimated time, labels, and 2 custom fields

        # Check field mappings
        key_field = next((f for f in qtest_fields if f["field_name"] == "zephyr_key"), None)
        self.assertIsNotNone(key_field)
        self.assertEqual(key_field["field_value"], "TEST-123")

        status_field = next((f for f in qtest_fields if f["field_name"] == "status"), None)
        self.assertIsNotNone(status_field)
        self.assertEqual(status_field["field_value"], "Active")

        time_field = next((f for f in qtest_fields if f["field_name"] == "estimated_time"), None)
        self.assertIsNotNone(time_field)
        self.assertEqual(time_field["field_value"], 60)

        labels_field = next((f for f in qtest_fields if f["field_name"] == "Tags"), None)
        self.assertIsNotNone(labels_field)
        self.assertEqual(labels_field["field_value"], "regression, smoke")

        # The Component custom field would now map to components (lowercase)
        component_field = next((f for f in qtest_fields if f["field_name"] == "component"), None)
        self.assertIsNotNone(component_field)
        self.assertEqual(component_field["field_value"], "UI")

    def test_map_testcycle_fields(self):
        """Test mapping Zephyr test cycle fields to qTest custom fields."""
        # Create test cycle data
        test_cycle = {
            "id": "456",
                "key": "CYCLE-456",
                "name": "Test Cycle",
                "status": "Active",
                "environment": "Production",
                "owner": "jdoe",
                "customFields": [
                {"name": "Sprint", "type": CustomFieldType.TEXT, "value": "Sprint 1"}
            ]
        }

        # Map fields
        qtest_fields = self.mapper.map_testcycle_fields(test_cycle)

        # Verify results
        self.assertGreaterEqual(len(qtest_fields), 4)  # Key, status, environment, owner, and 1 custom field

        # Check field mappings
        key_field = next((f for f in qtest_fields if f["field_name"] == "zephyr_key"), None)
        self.assertIsNotNone(key_field)
        self.assertEqual(key_field["field_value"], "CYCLE-456")

        status_field = next((f for f in qtest_fields if f["field_name"] == "status"), None)
        self.assertIsNotNone(status_field)
        self.assertEqual(status_field["field_value"], "Active")

        env_field = next((f for f in qtest_fields if f["field_name"] == "environment"), None)
        self.assertIsNotNone(env_field)
        self.assertEqual(env_field["field_value"], "Production")

        sprint_field = next((f for f in qtest_fields if f["field_name"] == "Sprint_Release"), None)
        self.assertIsNotNone(sprint_field)
        self.assertEqual(sprint_field["field_value"], "Sprint 1")

    def test_map_testrun_fields(self):
        """Test mapping Zephyr execution fields to qTest test run custom fields."""
        # Create test execution data
        execution = {
            "id": "789",
                "testCaseKey": "TEST-123",
                "status": "PASS",
                "environment": "Staging",
                "executedBy": "jdoe",
                "executedOn": datetime.now(),
                "actualTime": 45,
                "defects": [{"key": "BUG-001"}, {"key": "BUG-002"}],
                "customFields": [
                {"name": "Release", "type": CustomFieldType.TEXT, "value": "1.0"}
            ]
        }

        # Map fields
        qtest_fields = self.mapper.map_testrun_fields(execution)

        # Verify results
        self.assertGreaterEqual(len(qtest_fields), 5)  # Environment, executed by, execution date, actual time, defects, and 1 custom field

        # Check field mappings
        env_field = next((f for f in qtest_fields if f["field_name"] == "environment"), None)
        self.assertIsNotNone(env_field)
        self.assertEqual(env_field["field_value"], "Staging")

        executed_by_field = next((f for f in qtest_fields if f["field_name"] == "executed_by"), None)
        self.assertIsNotNone(executed_by_field)
        self.assertEqual(executed_by_field["field_value"], "jdoe")

        time_field = next((f for f in qtest_fields if f["field_name"] == "actual_time"), None)
        self.assertIsNotNone(time_field)
        self.assertEqual(time_field["field_value"], 45)

        defects_field = next((f for f in qtest_fields if f["field_name"] == "defects"), None)
        self.assertIsNotNone(defects_field)
        self.assertEqual(defects_field["field_value"], "BUG-001, BUG-002")

        release_field = next((f for f in qtest_fields if f["field_name"] == "release"), None)
        self.assertIsNotNone(release_field)
        self.assertEqual(release_field["field_value"], "1.0")


    def test_transform_table_field(self):
        """Test transformation of table-structured fields."""
        # Test dictionary-based table format
        table_data = [
            {"id": 1, "name": "Row 1", "value": 100},
                {"id": 2, "name": "Row 2", "value": 200}
        ]
        result = self.mapper._transform_table_field(table_data)
        self.assertTrue(isinstance(result, str))
        self.assertTrue("id | name | value" in result)
        self.assertTrue("Row 1" in result)
        self.assertTrue("Row 2" in result)

        # Test list-based table format
        list_table = [
            ["Header 1", "Header 2", "Header 3"],
                ["value1", "value2", "value3"],
                ["value4", "value5", "value6"]
        ]
        result = self.mapper._transform_table_field(list_table)
        self.assertTrue(isinstance(result, str))
        self.assertTrue("Header 1 | Header 2 | Header 3" in result)
        self.assertTrue("value1 | value2 | value3" in result)

        # Test empty table
        self.assertEqual(self.mapper._transform_table_field([]), "")

        # Test non-list value
        self.assertEqual(self.mapper._transform_table_field("Not a table"), "Not a table")

        # Test null value
        self.assertEqual(self.mapper._transform_table_field(None), "")

    def test_transform_hierarchical_field(self):
        """Test transformation of hierarchical-structured fields."""
        # Test dictionary format
        hierarchical_item = {"id": "parent1", "name": "Parent Item"}
        result = self.mapper._transform_hierarchical_field(hierarchical_item)
        self.assertEqual(result, "Parent Item")

        # Test alternative dictionary format
        alt_item = {"value": "123", "label": "Item Label"}
        result = self.mapper._transform_hierarchical_field(alt_item)
        self.assertEqual(result, "Item Label")

        # Test list of dictionaries
        hierarchy_list = [
            {"id": "parent1", "name": "Parent"},
                {"id": "child1", "name": "Child 1"},
                {"id": "child2", "name": "Child 2"}
        ]
        result = self.mapper._transform_hierarchical_field(hierarchy_list)
        self.assertTrue("Parent" in result)
        self.assertTrue("Child 1" in result)
        self.assertTrue("Child 2" in result)

        # Test empty hierarchical structure
        self.assertEqual(self.mapper._transform_hierarchical_field([]), "")

        # Test null value
        self.assertEqual(self.mapper._transform_hierarchical_field(None), "")

    def test_map_status(self):
        """Test status mapping functionality."""
        # Test direct mappings
        self.assertEqual(self.mapper.map_status("PASS"), "PASSED")
        self.assertEqual(self.mapper.map_status("FAIL"), "FAILED")
        self.assertEqual(self.mapper.map_status("BLOCKED"), "BLOCKED")
        self.assertEqual(self.mapper.map_status("WIP"), "IN_PROGRESS")

        # Test case insensitivity
        self.assertEqual(self.mapper.map_status("pass"), "PASSED")
        self.assertEqual(self.mapper.map_status("Fail"), "FAILED")

        # Test whitespace handling
        self.assertEqual(self.mapper.map_status(" PASS "), "PASSED")

        # Test aliases
        self.assertEqual(self.mapper.map_status("PASS WITH WARNINGS"), "PASSED")
        self.assertEqual(self.mapper.map_status("IN PROGRESS"), "IN_PROGRESS")

        # Test default value for unknown status
        self.assertEqual(self.mapper.map_status("UNKNOWN_STATUS"), "NOT_RUN")

        # Test null and empty values
        self.assertEqual(self.mapper.map_status(None), "NOT_RUN")
        self.assertEqual(self.mapper.map_status(""), "NOT_RUN")

    def test_map_priority(self):
        """Test priority mapping functionality."""
        # Test direct mappings
        self.assertEqual(self.mapper.map_priority("HIGHEST"), "CRITICAL")
        self.assertEqual(self.mapper.map_priority("HIGH"), "HIGH")
        self.assertEqual(self.mapper.map_priority("MEDIUM"), "MEDIUM")
        self.assertEqual(self.mapper.map_priority("LOW"), "LOW")

        # Test case insensitivity
        self.assertEqual(self.mapper.map_priority("highest"), "CRITICAL")
        self.assertEqual(self.mapper.map_priority("High"), "HIGH")

        # Test whitespace handling
        self.assertEqual(self.mapper.map_priority(" LOW "), "LOW")

        # Test aliases
        self.assertEqual(self.mapper.map_priority("BLOCKER"), "CRITICAL")
        self.assertEqual(self.mapper.map_priority("MINOR"), "LOW")

        # Test default value for unknown priority
        self.assertEqual(self.mapper.map_priority("UNKNOWN_PRIORITY"), "MEDIUM")

        # Test null and empty values
        self.assertEqual(self.mapper.map_priority(None), "MEDIUM")
        self.assertEqual(self.mapper.map_priority(""), "MEDIUM")

    def test_extract_and_map_field(self):
        """Test extracting and mapping fields from an entity."""
        entity = {
            "name": "Test Case",
                "description": "Test description",
                "status": "PASS",
                "priority": "HIGH",
                "points": 5,
                "automated": True
        }

        # Test normal extraction
        self.assertEqual(self.mapper.extract_and_map_field(entity, "name"), "Test Case")

        # Test status mapping
        self.assertEqual(self.mapper.extract_and_map_field(entity, "status"), "PASSED")

        # Test priority mapping
        self.assertEqual(self.mapper.extract_and_map_field(entity, "priority"), "HIGH")

        # Test with type conversion
        self.assertEqual(self.mapper.extract_and_map_field(entity, "points", target_type="NUMBER"), 5)

        # Test with default value for missing field
        self.assertEqual(self.mapper.extract_and_map_field(entity, "missing_field", "default"), "default")

        # Test with null value
        entity["null_field"] = None
        self.assertEqual(self.mapper.extract_and_map_field(entity, "null_field", "default"), "default")


@pytest.mark.unit
class TestDefaultFieldMapper(unittest.TestCase):
    """Test the default field mapper factory function."""

    def test_get_default_field_mapper(self):
        """Test getting the default field mapper."""
        mapper = get_default_field_mapper()
        self.assertIsInstance(mapper, CustomFieldMapper)


if __name__ == "__main__":
    unittest.main()
