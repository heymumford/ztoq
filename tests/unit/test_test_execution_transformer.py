"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Unit tests for the Test Execution Transformer.

These tests verify the transformation of Zephyr test executions to qTest test runs and logs,
including field mappings, validation rules, error handling, and special case processing.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from ztoq.entity_mapping import EntityType, ValidationAction
from ztoq.test_execution_transformer import (
    TestExecutionTransformer,
    TestExecutionTransformError,
    TransformationResult,
)
from ztoq.models import (
    Execution as TestExecution,
    CaseStep as TestStep,
    Attachment,
    CustomField,
    CustomFieldType,
)


class TestTestExecutionTransformer:
    """Test suite for the TestExecutionTransformer class."""

    @pytest.fixture
    def transformer(self):
        """Fixture for creating a test execution transformer with defaults."""
        return TestExecutionTransformer()

    @pytest.fixture
    def custom_transformer(self):
        """Fixture for creating a test execution transformer with custom settings."""
        db_mock = MagicMock()
        field_mapper_mock = MagicMock()
        return TestExecutionTransformer(
            db_manager=db_mock,
            field_mapper=field_mapper_mock,
            strict_mode=True,
            with_attachments=True,
        )

    @pytest.fixture
    def sample_test_execution(self):
        """Fixture for creating a sample test execution for transformation."""
        # Create a test execution as a dictionary for testing
        return {
            "id": "3001",
            "testCaseKey": "DEMO-TC-1001",
            "cycleId": "2001",
            "cycleName": "Sample Test Cycle",
            "status": "PASS",
            "statusName": "Passed",
            "environment": "Production",
            "environmentName": "Production Environment",
            "executedBy": "testuser",
            "executedByName": "Test User",
            "executedOn": datetime.now(),
            "created_on": datetime.now(),
            "created_by": "testuser",
            "updated_on": datetime.now(),
            "updated_by": "testuser",
            "actualTime": 3600000,  # 1 hour in milliseconds
            "comment": "Test ran successfully",
            "steps": [
                {
                    "id": "step_1",
                    "index": 1,
                    "description": "Login to the system",
                    "expected_result": "Login successful",
                    "actual_result": "Login was successful",
                    "status": "PASS",
                },
                {
                    "id": "step_2",
                    "index": 2,
                    "description": "Navigate to user profile",
                    "expected_result": "Profile page displayed",
                    "actual_result": "Profile page was displayed correctly",
                    "status": "PASS",
                },
            ],
            "customFields": [
                {
                    "id": "cf_001",
                    "name": "Build",
                    "type": CustomFieldType.TEXT,
                    "value": "v1.2.3",
                },
                {
                    "id": "cf_002",
                    "name": "Browser",
                    "type": CustomFieldType.DROPDOWN,
                    "value": "Chrome",
                },
            ],
        }

    def test_basic_transformation(self, transformer, sample_test_execution):
        """Test basic transformation of a test execution with no errors."""
        # Act
        result = transformer.transform(sample_test_execution)

        # Assert
        assert result.success is True
        assert result.errors == []

        # Check test run data
        test_run = result.transformed_entity.get("test_run")
        assert test_run is not None
        assert test_run["status"] == "PASSED"  # Mapped from PASS
        assert test_run["test_case_id"] is not None

        # Check test log data
        test_log = result.transformed_entity.get("test_log")
        assert test_log is not None
        assert test_log["status"] == "PASSED"
        assert test_log["note"] == "Test ran successfully"
        assert "test_step_logs" in test_log

        # Verify step logs were created
        step_logs = test_log["test_step_logs"]
        assert len(step_logs) == 2
        assert step_logs[0]["status"] == "PASSED"
        assert step_logs[0]["actual_result"] == "Login was successful"

    def test_custom_field_transformation(self, transformer, sample_test_execution):
        """Test transformation of custom fields."""
        # Prepare mock data to simulate the field mapper's behavior
        browser_field = {
            "field_id": 1,
            "field_name": "browser",
            "field_type": "STRING",
            "field_value": "Chrome",
        }
        build_field = {
            "field_id": 2,
            "field_name": "build",
            "field_type": "STRING",
            "field_value": "v1.2.3",
        }

        # Save original mapper
        original_mapper = transformer.field_mapper

        # Create mock mapper
        mock_mapper = MagicMock()
        mock_mapper.map_testrun_fields.return_value = [browser_field, build_field]
        transformer.field_mapper = mock_mapper

        try:
            # Act
            result = transformer.transform(sample_test_execution)

            # Assert
            assert result.success is True
            assert mock_mapper.map_testrun_fields.called

            # Check test run properties
            test_run = result.transformed_entity.get("test_run")
            assert test_run is not None
            # There should be at least 2 fields from the mock mapper
            assert len(test_run["properties"]) >= 2

            # Remove environment field that gets added automatically
            properties_without_env = [
                p for p in test_run["properties"] if p["field_name"] != "environment"
            ]

            # Check if custom fields were added
            custom_fields = {field["field_name"]: field for field in test_run["properties"]}
            assert "browser" in custom_fields
            assert custom_fields["browser"]["field_value"] == "Chrome"
            assert "build" in custom_fields
            assert custom_fields["build"]["field_value"] == "v1.2.3"
        finally:
            # Restore original mapper
            transformer.field_mapper = original_mapper

    def test_custom_mapper_integration(self, transformer):
        """Test integration with custom field mapper."""
        # Use non-strict regular transformer instead of custom transformer
        # Setup - need to prepare a test execution without any keys that could cause conflicts
        test_execution = {
            "id": "3002",
            "testCaseKey": "DEMO-TC-1002",  # Include required keys but with non-strict mode
            "status": "PASS",
            "executedBy": "testuser",
            "executedOn": datetime.now(),
            "comment": "Test with custom fields",
        }

        custom_fields = [
            {
                "field_id": 0,
                "field_name": "custom1",
                "field_type": "STRING",
                "field_value": "value1",
            },
            {"field_id": 0, "field_name": "custom2", "field_type": "CHECKBOX", "field_value": True},
        ]

        # Save original mapper
        original_mapper = transformer.field_mapper

        # Create mock mapper
        mock_mapper = MagicMock()
        mock_mapper.map_testrun_fields.return_value = custom_fields
        transformer.field_mapper = mock_mapper

        try:
            # Act
            result = transformer.transform(test_execution)

            # Assert - non-strict mode should work with warnings
            assert result.success is True
            assert mock_mapper.map_testrun_fields.called

            test_run = result.transformed_entity.get("test_run")
            assert test_run is not None

            # Extract only the custom fields we added
            custom_fields_in_result = [
                f for f in test_run["properties"] if f["field_name"] in ("custom1", "custom2")
            ]
            assert len(custom_fields_in_result) == 2
        finally:
            # Restore original mapper
            transformer.field_mapper = original_mapper

    def test_handle_missing_steps(self, transformer):
        """Test transformation of test execution without steps."""
        # Setup
        test_execution = {
            "id": "3003",
            "testCaseKey": "DEMO-TC-1003",
            "cycleId": "2003",
            "status": "PASS",
            "comment": "Test without steps",
        }

        # Act
        result = transformer.transform(test_execution)

        # Assert
        assert result.success is True
        test_log = result.transformed_entity.get("test_log")
        assert test_log is not None
        assert "test_step_logs" in test_log
        assert len(test_log["test_step_logs"]) == 0

    def test_handle_different_status_values(self, transformer):
        """Test handling of different status values."""
        test_cases = [
            ("PASS", "PASSED"),
            ("FAIL", "FAILED"),
            ("BLOCKED", "BLOCKED"),
            ("WIP", "IN_PROGRESS"),
            ("UNEXECUTED", "NOT_RUN"),
            ("not_executed", "NOT_RUN"),
            ("passed", "PASSED"),
            ("failed", "FAILED"),
            ("EXECUTING", "IN_PROGRESS"),
            ("ABORTED", "BLOCKED"),
            ("CANCELED", "NOT_RUN"),
            ("PENDING", "NOT_RUN"),
            (None, "NOT_RUN"),  # Test None value
            (123, "NOT_RUN"),  # Test numeric value
            ("unknown_status", "NOT_RUN"),  # Default to NOT_RUN for unknown
        ]

        for zephyr_status, expected_qtest_status in test_cases:
            # Setup
            test_execution = {
                "id": "3004",
                "testCaseKey": "DEMO-TC-1004",
                "cycleId": "2004",
                "status": zephyr_status,
                "comment": f"Test with status {zephyr_status}",
            }

            # Act
            result = transformer.transform(test_execution)

            # Assert
            assert result.success is True
            test_run = result.transformed_entity.get("test_run")
            test_log = result.transformed_entity.get("test_log")
            assert test_run["status"] == expected_qtest_status
            assert test_log["status"] == expected_qtest_status

    def test_transform_attachments(self, transformer, sample_test_execution):
        """Test transformation with attachments."""
        # Setup - use regular transformer with attachments enabled
        transformer.with_attachments = True
        sample_test_execution["attachments"] = [
            {
                "id": "att_1",
                "filename": "test_results.log",
                "contentType": "text/plain",
                "size": 1024,
                "content": b"fake-binary-content",
            }
        ]

        # Act
        result = transformer.transform(sample_test_execution)

        # Assert
        assert result.success is True
        test_log = result.transformed_entity.get("test_log")
        assert "attachments" in test_log
        assert len(test_log["attachments"]) == 1
        attachment = test_log["attachments"][0]
        assert attachment["name"] == "test_results.log"
        assert attachment["content_type"] == "text/plain"
        assert attachment["size"] == 1024

    def test_strict_mode_failures(self, custom_transformer):
        """Test that strict mode causes validation failures."""
        # Setup - missing required fields
        test_execution = {
            "id": "3005",
            "status": "PASS",
            # Missing testCaseKey - will cause strict validation error
        }

        # Act
        result = custom_transformer.transform(test_execution)

        # Assert
        assert result.success is False
        assert len(result.errors) > 0
        assert any("required" in str(err).lower() for err in result.errors)
        assert any("testcasekey" in str(err).lower() for err in result.errors) or any(
            "test case key" in str(err).lower() for err in result.errors
        )

    def test_non_strict_mode_handles_missing_fields(self, transformer):
        """Test that non-strict mode handles missing fields with warnings."""
        # Setup
        test_execution = {
            "id": "3006",
            "status": "PASS",
            # Missing testCaseKey - will be handled with warnings in non-strict mode
        }
        transformer.strict_mode = False

        # Act
        result = transformer.transform(test_execution)

        # Assert
        assert result.success is True  # Still succeeds in non-strict mode
        assert len(result.warnings) > 0
        test_run = result.transformed_entity.get("test_run")
        assert test_run is not None

    def test_db_integration_for_id_mapping(self, custom_transformer, sample_test_execution):
        """Test integration with database for test case and cycle ID mapping."""
        # Setup
        custom_transformer.db_manager.get_entity_mapping.side_effect = (
            lambda project_key, mapping_type, source_id: {
                "source_id": source_id,
                "target_id": 1000,  # Fixed ID for testing
                "mapping_type": mapping_type,
            }
        )

        # Act
        result = custom_transformer.transform(sample_test_execution)

        # Assert
        assert result.success is True
        assert (
            custom_transformer.db_manager.get_entity_mapping.call_count >= 2
        )  # Should be called for test case and cycle
        test_run = result.transformed_entity.get("test_run")
        assert test_run["test_case_id"] is not None
        assert test_run["test_cycle_id"] is not None

    def test_error_boundaries_with_exception(self, transformer, sample_test_execution):
        """Test error boundaries when unexpected exceptions occur."""
        # Setup - mock the field mapper to raise an exception
        original_mapper = transformer.field_mapper

        # Create a mock mapper that raises an exception
        mock_mapper = MagicMock()
        mock_mapper.map_testrun_fields.side_effect = Exception("Unexpected mapper error")
        transformer.field_mapper = mock_mapper

        try:
            # Act
            result = transformer.transform(sample_test_execution)

            # Assert
            assert result.success is False
            assert len(result.errors) > 0
            assert "Unexpected mapper error" in str(result.errors[0])
            assert result.transformed_entity is not None  # Should still return partial entity
        finally:
            # Restore original mapper
            transformer.field_mapper = original_mapper

    def test_date_field_mapping(self, transformer, sample_test_execution):
        """Test mapping of date fields to test run and log."""
        # Setup - use specific dates
        execution_date = datetime(2023, 1, 15, 12, 0, 0)
        sample_test_execution["executedOn"] = execution_date

        # Act
        result = transformer.transform(sample_test_execution)

        # Assert
        assert result.success is True
        test_run = result.transformed_entity.get("test_run")
        test_log = result.transformed_entity.get("test_log")

        # Check execution date in both entities
        assert test_run["actual_execution_date"] == execution_date
        assert test_log["execution_date"] == execution_date

    def test_step_status_mapping(self, transformer, sample_test_execution):
        """Test mapping of test step statuses."""
        # Setup - different statuses for steps
        sample_test_execution["steps"] = [
            {
                "id": "step_1",
                "index": 1,
                "description": "Step 1",
                "expected_result": "Expected 1",
                "actual_result": "Actual 1",
                "status": "PASS",
            },
            {
                "id": "step_2",
                "index": 2,
                "description": "Step 2",
                "expected_result": "Expected 2",
                "actual_result": "Actual 2",
                "status": "FAIL",
            },
            {
                "id": "step_3",
                "index": 3,
                "description": "Step 3",
                "expected_result": "Expected 3",
                "actual_result": "Skipped",
                "status": "NOT_EXECUTED",
            },
        ]

        # Act
        result = transformer.transform(sample_test_execution)

        # Assert
        assert result.success is True
        test_log = result.transformed_entity.get("test_log")
        step_logs = test_log["test_step_logs"]

        assert len(step_logs) == 3
        assert step_logs[0]["status"] == "PASSED"  # PASS -> PASSED
        assert step_logs[1]["status"] == "FAILED"  # FAIL -> FAILED
        assert step_logs[2]["status"] == "NOT_RUN"  # NOT_EXECUTED -> NOT_RUN

    def test_with_null_steps(self, transformer, sample_test_execution):
        """Test handling of null steps in the execution."""
        # Setup - include a null step
        sample_test_execution["steps"] = [
            {
                "id": "step_1",
                "index": 1,
                "description": "Step 1",
                "expected_result": "Expected 1",
                "actual_result": "Actual 1",
                "status": "PASS",
            },
            None,  # Null step
            {
                "id": "step_3",
                "index": 3,
                "description": "Step 3",
                "expected_result": "Expected 3",
                "actual_result": "Actual 3",
                "status": "PASS",
            },
        ]

        # Act
        result = transformer.transform(sample_test_execution)

        # Assert
        assert result.success is True
        test_log = result.transformed_entity.get("test_log")
        step_logs = test_log["test_step_logs"]

        # Should only have 2 valid steps
        assert len(step_logs) == 2
        assert step_logs[0]["order"] == 1
        assert step_logs[1]["order"] == 3

    def test_general_error_catching(self, transformer, sample_test_execution):
        """Test the general error catching mechanism in transform method."""
        # Override the _map_basic_fields method to throw an exception
        original_method = transformer._map_basic_fields

        def failing_method(*args, **kwargs):
            raise ValueError("Test exception")

        transformer._map_basic_fields = failing_method

        try:
            # Act
            result = transformer.transform(sample_test_execution)

            # Assert - the error should be caught and added to errors list
            assert len(result.errors) > 0
            assert "Test exception" in str(result.errors[0])
            assert result.success is False
        finally:
            # Restore original method
            transformer._map_basic_fields = original_method

    def test_db_error_during_id_mapping(self, custom_transformer, sample_test_execution):
        """Test handling of database errors during ID mapping."""
        # Setup - make the DB manager raise an exception
        custom_transformer.db_manager.get_entity_mapping.side_effect = Exception(
            "Database connection error"
        )

        # Act
        result = custom_transformer.transform(sample_test_execution)

        # Assert - in strict mode, we should get an error but still have a valid entity
        assert len(result.errors) > 0
        assert any("database" in str(err).lower() for err in result.errors)
        assert result.transformed_entity is not None
        assert "test_run" in result.transformed_entity
        assert "test_log" in result.transformed_entity

    def test_default_transformer_factory(self):
        """Test the get_default_transformer factory function."""
        # Act
        from ztoq.test_execution_transformer import get_default_transformer

        transformer = get_default_transformer()

        # Assert
        assert transformer is not None
        assert isinstance(transformer, TestExecutionTransformer)
        assert transformer.strict_mode is False  # Should default to non-strict
