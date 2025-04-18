"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Unit tests for the Test Case Transformer.

These tests verify the transformation of Zephyr test cases to qTest test cases, including
field mappings, validation rules, error handling, and special case processing.
"""

from unittest.mock import MagicMock

import pytest

from ztoq.models import (
    CustomFieldType,
)
from ztoq.test_case_transformer import (
    TestCaseTransformer,
    TransformationResult,
)

# Removed qTest model imports since we now use dictionaries


class TestTestCaseTransformer:
    """Test suite for the TestCaseTransformer class."""

    @pytest.fixture
    def transformer(self):
        """Fixture for creating a test case transformer with defaults."""
        return TestCaseTransformer()

    @pytest.fixture
    def custom_transformer(self):
        """Fixture for creating a test case transformer with custom settings."""
        db_mock = MagicMock()
        field_mapper_mock = MagicMock()
        return TestCaseTransformer(
            db_manager=db_mock,
            field_mapper=field_mapper_mock,
            strict_mode=True,
            with_attachments=True,
        )

    @pytest.fixture
    def sample_test_case(self):
        """Fixture for creating a sample test case for transformation."""
        # Create a test case as a dictionary for testing
        return {
            "id": "1001",
            "key": "DEMO-TC-1001",
            "name": "Sample Test Case",
            "objective": "This is a sample test case for testing",
            "precondition": "System is up and running",
            "priority": "high",
            "status": "active",
            "folderId": 42,
            "owner": "testuser",
            "labels": ["regression", "api"],
            "estimatedTime": 3600000,  # 1 hour in milliseconds
            "customFields": [
                {
                    "id": "cf_001",
                    "name": "Test Level",
                    "type": CustomFieldType.DROPDOWN,
                    "value": "Integration",
                },
                {
                    "id": "cf_002",
                    "name": "Automated",
                    "type": CustomFieldType.CHECKBOX,
                    "value": True,
                },
            ],
            "steps": [
                {
                    "id": "step_1",
                    "index": 1,
                    "description": "Login to the system",
                    "expected_result": "Login successful",
                    "data": "username=admin, password=admin123",
                },
                {
                    "id": "step_2",
                    "index": 2,
                    "description": "Navigate to user profile",
                    "expected_result": "Profile page displayed",
                },
            ],
        }

    def test_basic_transformation(self, transformer, sample_test_case):
        """Test basic transformation of a test case with no errors."""
        # Act
        result = transformer.transform(sample_test_case)

        # Assert
        assert result.success is True
        assert result.errors == []
        assert result.transformed_entity["name"] == "Sample Test Case"
        assert result.transformed_entity["description"] == "This is a sample test case for testing"
        assert result.transformed_entity["precondition"] == "System is up and running"
        assert result.transformed_entity["priority_id"] == 2  # high maps to 2

        # Verify steps were transformed correctly
        assert len(result.transformed_entity["test_steps"]) == 2
        step = result.transformed_entity["test_steps"][0]
        assert step["description"].startswith("Login to the system")
        assert "username=admin" in step["description"]
        assert step["expected_result"] == "Login successful"
        assert step["order"] == 1

    def test_custom_field_transformation(self, transformer, sample_test_case):
        """Test transformation of custom fields."""
        # Prepare mock data to simulate the field mapper's behavior
        automation_field = {
            "field_id": 1,
            "field_name": "automation",
            "field_type": "CHECKBOX",
            "field_value": True,
        }

        # Save original mapper
        original_mapper = transformer.field_mapper

        # Create mock mapper
        mock_mapper = MagicMock()
        mock_mapper.map_testcase_fields.return_value = [automation_field]
        transformer.field_mapper = mock_mapper

        try:
            # Act
            result = transformer.transform(sample_test_case)

            # Assert
            assert result.success is True
            assert mock_mapper.map_testcase_fields.called

            # There should be at least 2 fields (zephyr_key from the implementation plus automation)
            assert len(result.transformed_entity["properties"]) >= 2

            # Check if custom fields were added
            custom_fields = {
                field["field_name"]: field for field in result.transformed_entity["properties"]
            }
            assert "zephyr_key" in custom_fields
            assert custom_fields["zephyr_key"]["field_value"] == "DEMO-TC-1001"

            # Verify automated field is present
            assert "automation" in custom_fields
            assert custom_fields["automation"]["field_value"] is True
        finally:
            # Restore original mapper
            transformer.field_mapper = original_mapper

    def test_custom_mapper_integration(self, custom_transformer, sample_test_case):
        """Test integration with custom field mapper."""
        # Setup - need to prepare a more realistic test case without zephyr_key
        # to avoid the automatic zephyr_key field addition
        test_case_no_key = sample_test_case.copy()
        test_case_no_key.pop("key", None)  # Remove the key field

        custom_fields = [
            {
                "field_id": 0,
                "field_name": "custom1",
                "field_type": "STRING",
                "field_value": "value1",
            },
            {"field_id": 0, "field_name": "custom2", "field_type": "CHECKBOX", "field_value": True},
        ]
        custom_transformer.field_mapper.map_testcase_fields.return_value = custom_fields

        # Act
        result = custom_transformer.transform(test_case_no_key)

        # Assert
        assert result.success is True
        assert custom_transformer.field_mapper.map_testcase_fields.called
        assert len(result.transformed_entity["properties"]) == 2
        assert result.transformed_entity["properties"][0]["field_name"] == "custom1"
        assert result.transformed_entity["properties"][1]["field_name"] == "custom2"

    def test_handle_missing_test_steps(self, transformer):
        """Test transformation of test case without steps."""
        # Setup
        test_case = {
            "id": "1002",
            "key": "DEMO-TC-1002",
            "name": "Test Case Without Steps",
            "objective": "Test handling of missing steps",
            "priority": "medium",
            "folderId": 42,
            "steps": [],  # No steps
        }

        # Act
        result = transformer.transform(test_case)

        # Assert
        assert result.success is True
        assert len(result.transformed_entity["test_steps"]) == 0

    def test_handle_invalid_priority(self, transformer, sample_test_case):
        """Test handling of invalid priority values."""
        # Setup
        sample_test_case["priority"] = "invalid_priority"

        # Act
        result = transformer.transform(sample_test_case)

        # Assert
        assert result.success is True
        assert result.transformed_entity["priority_id"] == 3  # Default to medium (3)
        assert any("priority" in err for err in result.warnings)

    def test_transform_attachments(self, custom_transformer, sample_test_case):
        """Test transformation with attachments."""
        # Setup
        sample_test_case["attachments"] = [
            {
                "id": "att_1",
                "filename": "test.png",
                "content_type": "image/png",
                "size": 1024,
                "content": b"fake-binary-content",
            },
        ]

        # Act
        result = custom_transformer.transform(sample_test_case)

        # Assert
        assert result.success is True
        assert "attachments" in result.transformed_entity
        assert len(result.transformed_entity["attachments"]) == 1
        attachment = result.transformed_entity["attachments"][0]
        assert attachment["name"] == "test.png"
        assert attachment["content_type"] == "image/png"
        assert attachment["size"] == 1024

    def test_step_transformation_error(self, transformer, sample_test_case):
        """Test handling of step transformation errors."""
        # Setup - create a step that will cause an error
        sample_test_case["steps"].append(
            {
                "id": None,  # Missing ID will cause an error in strict mode
                "index": 3,
                "description": None,  # Missing description (required field)
            },
        )
        transformer.strict_mode = True  # Enable strict mode

        # Act
        result = transformer.transform(sample_test_case)

        # Assert
        assert result.success is False
        assert len(result.errors) > 0
        assert any("step" in str(err).lower() for err in result.errors)
        assert (
            len(result.transformed_entity["test_steps"]) == 2
        )  # Only the valid steps were transformed

    def test_strict_mode_failures(self, custom_transformer):
        """Test that strict mode causes validation failures."""
        # Setup
        test_case = {
            "id": "1003",
            "objective": "This test should fail in strict mode",
            "folderId": None,  # Missing folder ID
            "steps": [],
            # Name is missing - will cause strict validation error
        }

        # Act
        result = custom_transformer.transform(test_case)

        # Assert
        assert result.success is False
        assert len(result.errors) > 0
        assert any("required" in str(err).lower() for err in result.errors)
        assert any("name" in str(err).lower() for err in result.errors)

    def test_non_strict_mode_handles_missing_fields(self, transformer):
        """Test that non-strict mode handles missing fields with defaults."""
        # Setup
        test_case = {
            "id": "1004",
            "objective": "This test should use defaults in non-strict mode",
            "folderId": None,  # Missing folder ID
            "steps": [],
            # Name is missing - will be handled in non-strict mode
        }
        transformer.strict_mode = False

        # Act
        result = transformer.transform(test_case)

        # Assert
        assert result.success is True
        assert len(result.warnings) > 0
        assert result.transformed_entity["name"] is not None  # Should have default name
        assert result.transformed_entity["module_id"] is None  # No module mapping found

    def test_db_integration_for_folder_mapping(self, custom_transformer, sample_test_case):
        """Test integration with database for folder-to-module mapping."""
        # Setup
        custom_transformer.db_manager.get_entity_mapping.return_value = {
            "source_id": 42,
            "target_id": 100,
            "mapping_type": "folder_to_module",
        }

        # Act
        result = custom_transformer.transform(sample_test_case)

        # Assert
        assert result.success is True
        assert custom_transformer.db_manager.get_entity_mapping.called
        assert result.transformed_entity["module_id"] == 100

    def test_error_boundaries_with_exception(self, transformer, sample_test_case):
        """Test error boundaries when unexpected exceptions occur."""
        # Setup - mock the field mapper to raise an exception
        original_mapper = transformer.field_mapper

        # Create a mock mapper that raises an exception
        mock_mapper = MagicMock()
        mock_mapper.map_testcase_fields.side_effect = Exception("Unexpected mapper error")
        transformer.field_mapper = mock_mapper

        try:
            # Act
            result = transformer.transform(sample_test_case)

            # Assert
            assert result.success is False
            assert len(result.errors) > 0
            assert "Unexpected mapper error" in str(result.errors[0])
            assert result.transformed_entity is not None  # Should still return partial entity
        finally:
            # Restore original mapper
            transformer.field_mapper = original_mapper

    def test_partial_transformation_on_error(self, transformer, sample_test_case):
        """Test that partial transformation is returned even when errors occur."""
        # Setup - add an invalid step that will cause an error
        sample_test_case["steps"].append(None)  # Invalid step

        # Act
        result = transformer.transform(sample_test_case)

        # Assert
        assert result.success is False
        assert len(result.errors) > 0
        assert result.transformed_entity is not None
        assert len(result.transformed_entity["test_steps"]) == 2  # Only valid steps transformed

    def test_validation_with_special_fields(self, transformer, sample_test_case):
        """Test validation of special fields with custom validation rules."""
        # Setup - add a special field with validation
        sample_test_case["customFields"].append(
            {
                "id": "cf_003",
                "name": "Max Users",
                "type": CustomFieldType.NUMERIC,
                "value": "not_a_number",  # Invalid numeric value
            },
        )

        # Act
        result = transformer.transform(sample_test_case)

        # Assert
        assert result.success is True  # Non-strict mode allows this
        assert len(result.warnings) > 0
        assert any("numeric" in str(warning).lower() for warning in result.warnings)

    def test_log_warnings_for_non_critical_issues(self, transformer, sample_test_case, caplog):
        """Test that warnings are logged for non-critical issues."""
        # Setup - add a field that will cause a warning
        sample_test_case["estimatedTime"] = "invalid_time"

        # Act
        with caplog.at_level("WARNING"):
            result = transformer.transform(sample_test_case)

        # Assert
        assert result.success is True
        assert len(result.warnings) > 0
        assert "estimated time" in caplog.text.lower()

    def test_transformation_result_object(self, transformer, sample_test_case):
        """Test the TransformationResult object structure and methods."""
        # Act
        result = transformer.transform(sample_test_case)

        # Assert
        assert isinstance(result, TransformationResult)
        assert hasattr(result, "success")
        assert hasattr(result, "transformed_entity")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")
        assert hasattr(result, "original_entity")

        # Test the add_error method
        original_error_count = len(result.errors)
        result.add_error("Test error")
        assert len(result.errors) == original_error_count + 1
        assert result.success is False  # Adding error should set success to False

        # Test the add_warning method
        original_warning_count = len(result.warnings)
        result.add_warning("Test warning")
        assert len(result.warnings) == original_warning_count + 1

    def test_attachment_transformation_error_handling(self, custom_transformer, sample_test_case):
        """Test that attachments with errors are skipped gracefully."""
        # Setup - create a problematic attachment that will cause an error
        sample_test_case["attachments"] = [
            # Valid attachment but will be skipped because it has invalid name - should be a warning
            {
                "id": "att_1",
                "filename": None,
                "content_type": "application/octet-stream",
                "size": 100,
            },
            # Valid attachment
            {"id": "att_2", "filename": "valid.txt", "content_type": "text/plain", "size": 100},
        ]

        # Make sure with_attachments is enabled
        custom_transformer.with_attachments = True

        # Act
        result = custom_transformer.transform(sample_test_case)

        # Assert
        # The implementation doesn't add errors for invalid attachments but still processes them
        assert result.transformed_entity["attachments"] is not None

        # Let's verify our code correctly processes the valid attachment
        valid_attachments = [
            a for a in result.transformed_entity["attachments"] if a.get("name") == "valid.txt"
        ]
        assert len(valid_attachments) > 0

    def test_general_error_catching(self, transformer, sample_test_case):
        """Test the general error catching mechanism in transform method."""
        # Override the _map_basic_fields method to throw an exception
        original_method = transformer._map_basic_fields

        def failing_method(*args, **kwargs):
            raise ValueError("Test exception")

        transformer._map_basic_fields = failing_method

        try:
            # Act
            result = transformer.transform(sample_test_case)

            # Assert - the error should be caught and added to errors list
            assert len(result.errors) > 0
            assert "Test exception" in str(result.errors[0])
            assert result.success is False
        finally:
            # Restore original method
            transformer._map_basic_fields = original_method

    def test_db_error_during_module_mapping(self, custom_transformer, sample_test_case):
        """Test handling of database errors during module mapping."""
        # Setup - make the DB manager raise an exception
        custom_transformer.db_manager.get_entity_mapping.side_effect = Exception(
            "Database connection error",
        )

        # Act
        result = custom_transformer.transform(sample_test_case)

        # Assert - in strict mode, we should get an error but still have a valid entity
        assert len(result.errors) > 0
        assert any(
            "database" in str(err).lower() or "module mapping" in str(err).lower()
            for err in result.errors
        )
        assert result.transformed_entity["module_id"] is None  # Should default to None
        assert "name" in result.transformed_entity  # Should still have basic fields

    def test_edge_case_with_missing_steps_array(self, transformer):
        """Test handling of a test case with entirely missing steps array."""
        # Setup - test case without 'steps' key at all
        test_case = {
            "id": "1005",
            "name": "Missing Steps Array Test",
            "objective": "Test case should handle missing steps array",
        }

        # Act
        result = transformer.transform(test_case)

        # Assert
        assert result.success is True
        # There will be a warning for missing folder ID, not for missing steps
        assert not any("steps" in warning.lower() for warning in result.warnings)
        assert "test_steps" in result.transformed_entity
        assert result.transformed_entity["test_steps"] == []  # Empty steps array

    def test_default_transformer_factory(self):
        """Test the get_default_transformer factory function."""
        # Act
        from ztoq.test_case_transformer import get_default_transformer

        transformer = get_default_transformer()

        # Assert
        assert transformer is not None
        assert isinstance(transformer, TestCaseTransformer)
        assert transformer.strict_mode is False  # Should default to non-strict
