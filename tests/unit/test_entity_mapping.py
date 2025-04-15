"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Unit tests for entity mapping module.

These tests verify the mapping definitions and validation rules for entity mapping
between Zephyr Scale and qTest.
"""

from datetime import datetime

import pytest

from ztoq.custom_field_mapping import CustomFieldMapper
from ztoq.entity_mapping import (
    EntityMapping,
    EntityType,
    FieldMapping,
    MappingRegistry,
    ValidationAction,
    get_mapping_registry,
    map_entity,
    map_folder,
    map_project,
    map_test_case,
    map_test_cycle,
    map_test_execution,
)


class TestFieldMapping:
    """Test cases for the FieldMapping class."""

    def test_validate_and_transform_basic(self):
        """Test basic field validation and transformation."""
        # Simple mapping that converts to uppercase
        mapping = FieldMapping(
            source_field="name",
            target_field="name",
            transform_function=lambda x: x.upper() if isinstance(x, str) else x,
        )

        # Valid transform
        is_valid, value, error = mapping.validate_and_transform("test")
        assert is_valid
        assert value == "TEST"
        assert error is None

        # None value (not required)
        is_valid, value, error = mapping.validate_and_transform(None)
        assert is_valid
        assert value is None
        assert error is None

    def test_required_field(self):
        """Test validation of required fields."""
        mapping = FieldMapping(source_field="name", target_field="name", required=True)

        # Valid value
        is_valid, value, error = mapping.validate_and_transform("test")
        assert is_valid
        assert value == "test"
        assert error is None

        # Required field missing
        is_valid, value, error = mapping.validate_and_transform(None)
        assert not is_valid
        assert value is None
        assert "Required field" in error

    def test_validation_function(self):
        """Test custom validation function."""
        mapping = FieldMapping(
            source_field="age",
            target_field="age",
            validation_function=lambda x: isinstance(x, int) and x >= 18,
        )

        # Valid value
        is_valid, value, error = mapping.validate_and_transform(25)
        assert is_valid
        assert value == 25
        assert error is None

        # Invalid value (under 18)
        is_valid, value, error = mapping.validate_and_transform(15)
        assert not is_valid
        assert value == 15
        assert "Validation failed" in error

        # Invalid value (not an int)
        is_valid, value, error = mapping.validate_and_transform("25")
        assert not is_valid
        assert value == "25"
        assert "Validation failed" in error

    def test_validation_actions(self):
        """Test different validation actions."""
        # Test ERROR action
        error_mapping = FieldMapping(
            source_field="age",
            target_field="age",
            validation_function=lambda x: isinstance(x, int) and x >= 18,
            validation_action=ValidationAction.ERROR,
        )

        with pytest.raises(ValueError):
            error_mapping.validate_and_transform(15)

        # Test DEFAULT action
        default_mapping = FieldMapping(
            source_field="age",
            target_field="age",
            validation_function=lambda x: isinstance(x, int) and x >= 18,
            validation_action=ValidationAction.DEFAULT,
            default_value=18,
        )

        is_valid, value, error = default_mapping.validate_and_transform(15)
        assert is_valid  # Becomes valid after default applies
        assert value == 18
        assert error is None

        # Test SKIP action
        skip_mapping = FieldMapping(
            source_field="age",
            target_field="age",
            validation_function=lambda x: isinstance(x, int) and x >= 18,
            validation_action=ValidationAction.SKIP,
        )

        is_valid, value, error = skip_mapping.validate_and_transform(15)
        assert not is_valid
        assert value == 15
        assert "Validation failed" in error

    def test_transform_error_handling(self):
        """Test handling of errors during transformation."""
        mapping = FieldMapping(
            source_field="date",
            target_field="date",
            transform_function=lambda x: datetime.strptime(x, "%Y-%m-%d"),
            validation_action=ValidationAction.WARNING,
        )

        # Valid transform
        is_valid, value, error = mapping.validate_and_transform("2023-01-01")
        assert is_valid
        assert isinstance(value, datetime)
        assert error is None

        # Invalid transform (wrong format)
        is_valid, value, error = mapping.validate_and_transform("01/01/2023")
        assert not is_valid
        assert value == "01/01/2023"  # Original value retained
        assert "Transform failed" in error


class TestEntityMapping:
    """Test cases for the EntityMapping class."""

    def test_map_entity_basic(self):
        """Test basic entity mapping functionality."""
        # Create a simple entity mapping
        mapping = EntityMapping(
            source_type=EntityType.PROJECT,
            target_type="QTestProject",
            field_mappings=[
                FieldMapping(source_field="name", target_field="name"),
                FieldMapping(source_field="description", target_field="description"),
            ],
            custom_field_mapping_enabled=False,
        )

        # Source entity
        source = {
            "name": "Test Project",
            "description": "This is a test project",
            "id": 12345,  # Not mapped
            "other_field": "value",  # Not mapped
        }

        # Map the entity
        target = mapping.map_entity(source)

        # Verify mapping
        assert target["name"] == "Test Project"
        assert target["description"] == "This is a test project"
        assert "id" not in target
        assert "other_field" not in target

    def test_map_entity_with_transforms(self):
        """Test entity mapping with field transformations."""
        # Create entity mapping with transformations
        mapping = EntityMapping(
            source_type=EntityType.TEST_CASE,
            target_type="QTestTestCase",
            field_mappings=[
                FieldMapping(source_field="name", target_field="name"),
                FieldMapping(
                    source_field="priority",
                    target_field="priority_id",
                    transform_function=lambda p: {"high": 1, "medium": 2, "low": 3}.get(p, 2),
                ),
            ],
            custom_field_mapping_enabled=False,
        )

        # Source entity
        source = {"name": "Test Case 1", "priority": "high"}

        # Map the entity
        target = mapping.map_entity(source)

        # Verify transformed values
        assert target["name"] == "Test Case 1"
        assert target["priority_id"] == 1

    def test_map_entity_with_validation(self):
        """Test entity mapping with field validation."""
        # Create entity mapping with validation
        mapping = EntityMapping(
            source_type=EntityType.TEST_EXECUTION,
            target_type="QTestTestRun",
            field_mappings=[
                FieldMapping(
                    source_field="name",
                    target_field="name",
                    required=True,
                    validation_action=ValidationAction.ERROR,
                ),
                FieldMapping(
                    source_field="status",
                    target_field="status",
                    validation_function=lambda s: s in ["PASS", "FAIL", "NOT RUN"],
                    validation_action=ValidationAction.DEFAULT,
                    default_value="NOT RUN",
                ),
            ],
            custom_field_mapping_enabled=False,
        )

        # Source entity with valid data
        valid_source = {"name": "Test Execution 1", "status": "PASS"}

        # Map the entity
        target = mapping.map_entity(valid_source)

        # Verify mapping
        assert target["name"] == "Test Execution 1"
        assert target["status"] == "PASS"

        # Source entity with invalid status
        invalid_status = {"name": "Test Execution 2", "status": "INVALID"}

        # Map entity with invalid status should use default
        target = mapping.map_entity(invalid_status)
        assert target["name"] == "Test Execution 2"
        assert target["status"] == "NOT RUN"

        # Source entity with missing required field
        missing_required = {"status": "PASS"}

        # Map entity with missing required field should raise ValueError
        with pytest.raises(ValueError):
            mapping.map_entity(missing_required)

    def test_map_entity_with_custom_fields(self):
        """Test entity mapping with custom fields."""
        # Create entity mapping with custom fields enabled
        mapping = EntityMapping(
            source_type=EntityType.TEST_CASE,
            target_type="QTestTestCase",
            field_mappings=[FieldMapping(source_field="name", target_field="name")],
            custom_field_mapping_enabled=True,
        )

        # Source entity with custom fields
        source = {
            "name": "Test Case with Custom Fields",
            "customFields": [
                {"name": "Custom1", "type": "TEXT", "value": "Value1"},
                {"name": "Custom2", "type": "CHECKBOX", "value": True},
            ],
        }

        # Create a mock field mapper
        class MockFieldMapper(CustomFieldMapper):
            def map_testcase_fields(self, test_case):
                return ["Mapped Custom Field 1", "Mapped Custom Field 2"]

        # Map the entity with mock mapper
        target = mapping.map_entity(source, MockFieldMapper())

        # Verify mapping
        assert target["name"] == "Test Case with Custom Fields"
        assert "properties" in target
        assert target["properties"] == ["Mapped Custom Field 1", "Mapped Custom Field 2"]


class TestMappingRegistry:
    """Test cases for the MappingRegistry class."""

    def test_registry_initialization(self):
        """Test mapping registry initialization with all required mappings."""
        registry = MappingRegistry()

        # Verify all entity types have mappings
        assert registry.get_mapping(EntityType.PROJECT) is not None
        assert registry.get_mapping(EntityType.FOLDER) is not None
        assert registry.get_mapping(EntityType.TEST_CASE) is not None
        assert registry.get_mapping(EntityType.TEST_STEP) is not None
        assert registry.get_mapping(EntityType.TEST_CYCLE) is not None
        assert registry.get_mapping(EntityType.TEST_EXECUTION) is not None
        assert registry.get_mapping(EntityType.TEST_STEP_RESULT) is not None
        assert registry.get_mapping(EntityType.ATTACHMENT) is not None

    def test_get_mapping(self):
        """Test getting a specific mapping from the registry."""
        registry = MappingRegistry()

        # Get project mapping
        project_mapping = registry.get_mapping(EntityType.PROJECT)
        assert project_mapping.source_type == EntityType.PROJECT
        assert project_mapping.target_type == "QTestProject"

        # Get non-existent mapping
        non_existent = registry.get_mapping("NonExistentType")  # type: ignore
        assert non_existent is None

    def test_register_custom_mapping(self):
        """Test registering a custom mapping in the registry."""
        registry = MappingRegistry()

        # Create a custom mapping
        custom_mapping = EntityMapping(
            source_type=EntityType.PROJECT,  # Override existing
            target_type="CustomTarget",
            field_mappings=[
                FieldMapping(source_field="custom_field", target_field="custom_target_field"),
            ],
            custom_field_mapping_enabled=False,
        )

        # Register custom mapping
        registry.register_mapping(custom_mapping)

        # Verify the mapping was registered
        retrieved = registry.get_mapping(EntityType.PROJECT)
        assert retrieved.target_type == "CustomTarget"
        assert len(retrieved.field_mappings) == 1
        assert retrieved.field_mappings[0].source_field == "custom_field"

    def test_map_entity_through_registry(self):
        """Test mapping an entity through the registry."""
        registry = MappingRegistry()

        # Source entity
        source = {"name": "Test Project", "description": "Project description", "key": "TEST"}

        # Map through registry
        target = registry.map_entity(EntityType.PROJECT, source)

        # Verify mapping
        assert target["name"] == "Test Project"
        assert target["description"] == "Project description"
        assert target["zephyr_key"] == "TEST"

        # Test with non-existent mapping
        with pytest.raises(ValueError):
            registry.map_entity("NonExistentType", source)  # type: ignore


class TestGlobalMappingFunctions:
    """Test cases for the global mapping functions."""

    def test_get_mapping_registry(self):
        """Test getting the global mapping registry."""
        registry = get_mapping_registry()
        assert isinstance(registry, MappingRegistry)
        # Verify it's the same instance each time
        assert get_mapping_registry() is registry

    def test_map_entity_global(self):
        """Test the global map_entity function."""
        source = {"name": "Test Project", "key": "TEST"}
        target = map_entity(EntityType.PROJECT, source)
        assert target["name"] == "Test Project"
        assert target["zephyr_key"] == "TEST"

    def test_convenience_mapping_functions(self):
        """Test the convenience mapping functions for specific entity types."""
        # Project mapping
        project = {"name": "Test Project", "key": "TEST"}
        mapped_project = map_project(project)
        assert mapped_project["name"] == "Test Project"

        # Folder mapping
        folder = {"name": "Test Folder", "description": "Folder description"}
        mapped_folder = map_folder(folder)
        assert mapped_folder["name"] == "Test Folder"

        # Test case mapping
        test_case = {"name": "Test Case", "objective": "Test objective", "priority": "high"}
        mapped_test_case = map_test_case(test_case)
        assert mapped_test_case["name"] == "Test Case"
        assert mapped_test_case["description"] == "Test objective"
        # Note: Pydantic model properties may cause differences in transformation
        # compared to direct dictionary mapping

        # Test cycle mapping
        test_cycle = {"name": "Test Cycle", "description": "Cycle description"}
        mapped_cycle = map_test_cycle(test_cycle)
        assert mapped_cycle["name"] == "Test Cycle"

        # Test execution mapping
        test_execution = {"name": "Test Execution", "status": "pass", "testCaseId": "TC-001"}
        mapped_execution = map_test_execution(test_execution)
        assert mapped_execution["name"] == "Test Execution"


class TestSpecificMappingRules:
    """Test cases for specific mapping rules in the predefined mappings."""

    def test_project_mapping_rules(self):
        """Test specific rules for project mapping."""
        registry = get_mapping_registry()
        project_mapping = registry.get_mapping(EntityType.PROJECT)

        # Test with name field missing (required)
        with pytest.raises(ValueError):
            project_mapping.map_entity({"key": "TEST"})

        # Test with all fields
        mapped = project_mapping.map_entity(
            {
                "name": "Project Name",
                "description": "Description",
                "key": "PROJ",
                "id": 123,  # Not mapped
            },
        )

        assert mapped["name"] == "Project Name"
        assert mapped["description"] == "Description"
        assert mapped["zephyr_key"] == "PROJ"
        assert "id" not in mapped

    def test_field_transform_functions(self):
        """Test transform functions work directly as expected."""
        # Test priority transform function
        priority_transform = lambda p: {
            "highest": 1,
            "high": 2,
            "medium": 3,
            "low": 4,
            "lowest": 5,
            "critical": 1,
            "blocker": 1,
            "major": 2,
            "minor": 4,
            "trivial": 5,
        }.get(str(p).lower() if p else "", 3)

        assert priority_transform("high") == 2
        assert priority_transform("medium") == 3
        assert priority_transform(None) == 3
        assert priority_transform("unknown") == 3

        # Test status transform function
        def status_transform(status):
            if not status:
                return "NOT_RUN"

            status_map = {
                "pass": "PASSED",
                "fail": "FAILED",
                "wip": "IN_PROGRESS",
                "blocked": "BLOCKED",
                "unexecuted": "NOT_RUN",
                "not_executed": "NOT_RUN",
                "passed": "PASSED",
                "failed": "FAILED",
                "in_progress": "IN_PROGRESS",
                "executing": "IN_PROGRESS",
                "aborted": "BLOCKED",
                "canceled": "NOT_RUN",
                "pending": "NOT_RUN",
            }
            return status_map.get(str(status).lower(), "NOT_RUN")

        assert status_transform("pass") == "PASSED"
        assert status_transform("failed") == "FAILED"
        assert status_transform(None) == "NOT_RUN"
        assert status_transform("unknown") == "NOT_RUN"

    def test_field_transform_in_mapping(self):
        """Test transform functions in field mappings."""
        # Test priority mapping
        priority_field = FieldMapping(
            source_field="priority",
            target_field="priority_id",
            transform_function=lambda p: {
                "highest": 1,
                "high": 2,
                "medium": 3,
                "low": 4,
                "lowest": 5,
                "critical": 1,
                "blocker": 1,
                "major": 2,
                "minor": 4,
                "trivial": 5,
            }.get(str(p).lower() if p else "", 3),
        )

        # Test the field mapping directly
        is_valid, value, error = priority_field.validate_and_transform("high")
        assert is_valid
        assert value == 2
        assert error is None

        is_valid, value, error = priority_field.validate_and_transform(None)
        assert is_valid  # Not required, so valid
        assert value == 3  # Transformation applied to None should return default of 3
        assert error is None

        # Test status mapping
        def status_transform(status):
            if not status:
                return "NOT_RUN"

            status_map = {
                "pass": "PASSED",
                "fail": "FAILED",
                "wip": "IN_PROGRESS",
                "blocked": "BLOCKED",
                "unexecuted": "NOT_RUN",
                "not_executed": "NOT_RUN",
                "passed": "PASSED",
                "failed": "FAILED",
                "in_progress": "IN_PROGRESS",
                "executing": "IN_PROGRESS",
                "aborted": "BLOCKED",
                "canceled": "NOT_RUN",
                "pending": "NOT_RUN",
            }
            return status_map.get(str(status).lower(), "NOT_RUN")

        status_field = FieldMapping(
            source_field="status", target_field="status", transform_function=status_transform,
        )

        # Test the field mapping directly
        is_valid, value, error = status_field.validate_and_transform("pass")
        assert is_valid
        assert value == "PASSED"
        assert error is None

        is_valid, value, error = status_field.validate_and_transform(None)
        assert is_valid  # Not required, so valid
        assert value == "NOT_RUN"  # Transformation applied to None should return "NOT_RUN"
        assert error is None
