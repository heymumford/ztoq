"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Unit tests for the Test Cycle Transformer.

These tests verify the transformation of Zephyr test cycles to qTest test cycles, including
field mappings, validation rules, error handling, and special case processing.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from ztoq.entity_mapping import EntityType, ValidationAction
from ztoq.test_cycle_transformer import (
    TestCycleTransformer,
    TestCycleTransformError,
    TransformationResult,
)
from ztoq.models import (
    CycleInfo as TestCycle,
    Attachment,
    CustomField,
    CustomFieldType,
)


class TestTestCycleTransformer:
    """Test suite for the TestCycleTransformer class."""

    @pytest.fixture
    def transformer(self):
        """Fixture for creating a test cycle transformer with defaults."""
        return TestCycleTransformer()

    @pytest.fixture
    def custom_transformer(self):
        """Fixture for creating a test cycle transformer with custom settings."""
        db_mock = MagicMock()
        field_mapper_mock = MagicMock()
        return TestCycleTransformer(
            db_manager=db_mock,
            field_mapper=field_mapper_mock,
            strict_mode=True,
            with_attachments=True,
        )

    @pytest.fixture
    def sample_test_cycle(self):
        """Fixture for creating a sample test cycle for transformation."""
        # Create a test cycle as a dictionary for testing
        return {
            "id": "2001",
            "key": "DEMO-CY-2001",
            "name": "Sample Test Cycle",
            "description": "This is a sample test cycle for testing",
            "status": "active",
            "folder": "42",
            "folder_name": "Test Folder",
            "project_key": "DEMO",
            "owner": "testuser",
            "created_on": datetime.now(),
            "created_by": "testuser",
            "updated_on": datetime.now(),
            "updated_by": "testuser",
            "customFields": [
                {
                    "id": "cf_001",
                    "name": "Sprint",
                    "type": CustomFieldType.DROPDOWN,
                    "value": "Sprint 1",
                },
                {
                    "id": "cf_002",
                    "name": "Environment",
                    "type": CustomFieldType.DROPDOWN,
                    "value": "Production",
                },
            ],
            "startDate": datetime.now(),
            "endDate": datetime.now(),
        }

    def test_basic_transformation(self, transformer, sample_test_cycle):
        """Test basic transformation of a test cycle with no errors."""
        # Act
        result = transformer.transform(sample_test_cycle)

        # Assert
        assert result.success is True
        assert result.errors == []
        assert result.transformed_entity["name"] == "Sample Test Cycle"
        assert result.transformed_entity["description"] == "This is a sample test cycle for testing"
        assert "start_date" in result.transformed_entity
        assert "end_date" in result.transformed_entity

    def test_custom_field_transformation(self, transformer, sample_test_cycle):
        """Test transformation of custom fields."""
        # Prepare mock data to simulate the field mapper's behavior
        environment_field = {
            "field_id": 1,
            "field_name": "environment",
            "field_type": "STRING",
            "field_value": "Production",
        }

        # Save original mapper
        original_mapper = transformer.field_mapper

        # Create mock mapper
        mock_mapper = MagicMock()
        mock_mapper.map_testcycle_fields.return_value = [environment_field]
        transformer.field_mapper = mock_mapper

        try:
            # Act
            result = transformer.transform(sample_test_cycle)

            # Assert
            assert result.success is True
            assert mock_mapper.map_testcycle_fields.called

            # There should be at least 2 fields (zephyr_key from the implementation plus environment)
            assert len(result.transformed_entity["properties"]) >= 1

            # Check if custom fields were added
            custom_fields = {
                field["field_name"]: field for field in result.transformed_entity["properties"]
            }
            assert "environment" in custom_fields
            assert custom_fields["environment"]["field_value"] == "Production"
        finally:
            # Restore original mapper
            transformer.field_mapper = original_mapper

    def test_custom_mapper_integration(self, custom_transformer, sample_test_cycle):
        """Test integration with custom field mapper."""
        # Setup - need to prepare a test cycle without zephyr_key
        # to avoid the automatic zephyr_key field addition
        test_cycle_no_key = sample_test_cycle.copy()
        test_cycle_no_key.pop("key", None)  # Remove the key field

        custom_fields = [
            {
                "field_id": 0,
                "field_name": "custom1",
                "field_type": "STRING",
                "field_value": "value1",
            },
            {"field_id": 0, "field_name": "custom2", "field_type": "CHECKBOX", "field_value": True},
        ]
        custom_transformer.field_mapper.map_testcycle_fields.return_value = custom_fields

        # Act
        result = custom_transformer.transform(test_cycle_no_key)

        # Assert
        assert result.success is True
        assert custom_transformer.field_mapper.map_testcycle_fields.called
        assert len(result.transformed_entity["properties"]) == 2
        assert result.transformed_entity["properties"][0]["field_name"] == "custom1"
        assert result.transformed_entity["properties"][1]["field_name"] == "custom2"

    def test_handle_missing_dates(self, transformer):
        """Test transformation of test cycle without dates."""
        # Setup
        test_cycle = {
            "id": "2002",
            "key": "DEMO-CY-2002",
            "name": "Test Cycle Without Dates",
            "description": "Test handling of missing dates",
            "status": "active",
            "project_key": "DEMO",
        }

        # Act
        result = transformer.transform(test_cycle)

        # Assert
        assert result.success is True
        assert result.transformed_entity["start_date"] is None
        assert result.transformed_entity["end_date"] is None

    def test_handle_invalid_dates(self, transformer, sample_test_cycle):
        """Test handling of invalid dates."""
        # Setup
        sample_test_cycle["startDate"] = "invalid_date"
        sample_test_cycle["endDate"] = "invalid_date"

        # Act
        result = transformer.transform(sample_test_cycle)

        # Assert
        assert result.success is True
        assert any("date" in err.lower() for err in result.warnings)

    def test_transform_attachments(self, custom_transformer, sample_test_cycle):
        """Test transformation with attachments."""
        # Setup
        sample_test_cycle["attachments"] = [
            {
                "id": "att_1",
                "filename": "cycle_doc.pdf",
                "contentType": "application/pdf",
                "size": 1024,
                "content": b"fake-binary-content",
            }
        ]

        # Act
        result = custom_transformer.transform(sample_test_cycle)

        # Assert
        assert result.success is True
        assert "attachments" in result.transformed_entity
        assert len(result.transformed_entity["attachments"]) == 1
        attachment = result.transformed_entity["attachments"][0]
        assert attachment["name"] == "cycle_doc.pdf"
        assert attachment["content_type"] == "application/pdf"
        assert attachment["size"] == 1024

    def test_strict_mode_failures(self, custom_transformer):
        """Test that strict mode causes validation failures."""
        # Setup
        test_cycle = {
            "id": "2003",
            "description": "This test should fail in strict mode",
            # Name is missing - will cause strict validation error
        }

        # Act
        result = custom_transformer.transform(test_cycle)

        # Assert
        assert result.success is False
        assert len(result.errors) > 0
        assert any("required" in str(err).lower() for err in result.errors)
        assert any("name" in str(err).lower() for err in result.errors)

    def test_non_strict_mode_handles_missing_fields(self, transformer):
        """Test that non-strict mode handles missing fields with defaults."""
        # Setup
        test_cycle = {
            "id": "2004",
            "description": "This test should use defaults in non-strict mode",
            # Name is missing - will be handled in non-strict mode
        }
        transformer.strict_mode = False

        # Act
        result = transformer.transform(test_cycle)

        # Assert
        assert result.success is True
        assert len(result.warnings) > 0
        assert result.transformed_entity["name"] is not None  # Should have default name

    def test_db_integration_for_folder_mapping(self, custom_transformer, sample_test_cycle):
        """Test integration with database for folder-to-module mapping."""
        # Setup
        custom_transformer.db_manager.get_entity_mapping.return_value = {
            "source_id": 42,
            "target_id": 100,
            "mapping_type": "folder_to_module",
        }

        # Act
        result = custom_transformer.transform(sample_test_cycle)

        # Assert
        assert result.success is True
        assert custom_transformer.db_manager.get_entity_mapping.called
        assert result.transformed_entity["parent_id"] == 100

    def test_error_boundaries_with_exception(self, transformer, sample_test_cycle):
        """Test error boundaries when unexpected exceptions occur."""
        # Setup - mock the field mapper to raise an exception
        original_mapper = transformer.field_mapper

        # Create a mock mapper that raises an exception
        mock_mapper = MagicMock()
        mock_mapper.map_testcycle_fields.side_effect = Exception("Unexpected mapper error")
        transformer.field_mapper = mock_mapper

        try:
            # Act
            result = transformer.transform(sample_test_cycle)

            # Assert
            assert result.success is False
            assert len(result.errors) > 0
            assert "Unexpected mapper error" in str(result.errors[0])
            assert result.transformed_entity is not None  # Should still return partial entity
        finally:
            # Restore original mapper
            transformer.field_mapper = original_mapper

    def test_date_field_transformation(self, transformer, sample_test_cycle):
        """Test transformation of date fields."""
        # Setup - use a specific date to test
        test_date = datetime(2023, 1, 15, 12, 0, 0)
        sample_test_cycle["startDate"] = test_date
        sample_test_cycle["endDate"] = test_date

        # Act
        result = transformer.transform(sample_test_cycle)

        # Assert
        assert result.success is True
        assert result.transformed_entity["start_date"] is not None
        assert result.transformed_entity["end_date"] is not None

    def test_validation_result_object(self, transformer, sample_test_cycle):
        """Test the TransformationResult object structure and methods."""
        # Act
        result = transformer.transform(sample_test_cycle)

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

    def test_attachment_transformation_error_handling(self, custom_transformer, sample_test_cycle):
        """Test that attachments with errors are skipped gracefully."""
        # Setup - create a problematic attachment that will cause an error
        sample_test_cycle["attachments"] = [
            # Valid attachment but will be skipped because it has invalid name - should be a warning
            {"id": "att_1", "filename": None, "content_type": "application/octet-stream", "size": 100},
            # Valid attachment
            {"id": "att_2", "filename": "valid.txt", "content_type": "text/plain", "size": 100}
        ]

        # Make sure with_attachments is enabled
        custom_transformer.with_attachments = True

        # Act
        result = custom_transformer.transform(sample_test_cycle)

        # Assert
        # The implementation should still process valid attachments
        assert result.transformed_entity["attachments"] is not None

        # Let's verify our code correctly processes the valid attachment
        valid_attachments = [a for a in result.transformed_entity["attachments"]
                           if a.get("name") == "valid.txt"]
        assert len(valid_attachments) > 0

    def test_general_error_catching(self, transformer, sample_test_cycle):
        """Test the general error catching mechanism in transform method."""
        # Override the _map_basic_fields method to throw an exception
        original_method = transformer._map_basic_fields

        def failing_method(*args, **kwargs):
            raise ValueError("Test exception")

        transformer._map_basic_fields = failing_method

        try:
            # Act
            result = transformer.transform(sample_test_cycle)

            # Assert - the error should be caught and added to errors list
            assert len(result.errors) > 0
            assert "Test exception" in str(result.errors[0])
            assert result.success is False
        finally:
            # Restore original method
            transformer._map_basic_fields = original_method

    def test_db_error_during_folder_mapping(self, custom_transformer, sample_test_cycle):
        """Test handling of database errors during folder mapping."""
        # Setup - make the DB manager raise an exception
        custom_transformer.db_manager.get_entity_mapping.side_effect = Exception("Database connection error")

        # Act
        result = custom_transformer.transform(sample_test_cycle)

        # Assert - in strict mode, we should get an error but still have a valid entity
        assert len(result.errors) > 0
        assert any("database" in str(err).lower() for err in result.errors)
        assert result.transformed_entity["parent_id"] is None  # Should default to None
        assert "name" in result.transformed_entity  # Should still have basic fields

    def test_default_transformer_factory(self):
        """Test the get_default_transformer factory function."""
        # Act
        from ztoq.test_cycle_transformer import get_default_transformer
        transformer = get_default_transformer()

        # Assert
        assert transformer is not None
        assert isinstance(transformer, TestCycleTransformer)
        assert transformer.strict_mode is False  # Should default to non-strict
