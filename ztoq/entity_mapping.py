"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Entity mapping module for defining transformations between Zephyr Scale and qTest entities.

This module provides the core entity mapping definitions and validation rules as specified
in the entity-mapping.md document. It includes mapping definitions for all major entity types
(projects, folders, test cases, cycles, executions) and their fields.
"""

import logging
from collections.abc import Callable
from enum import Enum
from typing import Any

from pydantic import BaseModel

from ztoq.custom_field_mapping import get_default_field_mapper

logger = logging.getLogger("ztoq.entity_mapping")


class EntityType(str, Enum):
    """Enum defining entity types that can be mapped."""

    PROJECT = "project"
    FOLDER = "folder"
    TEST_CASE = "test_case"
    TEST_STEP = "test_step"
    TEST_CYCLE = "test_cycle"
    TEST_EXECUTION = "test_execution"
    TEST_STEP_RESULT = "test_step_result"
    ATTACHMENT = "attachment"


class ValidationAction(str, Enum):
    """Enum defining actions to take when validation fails."""

    ERROR = "error"  # Raise an error and halt
    WARNING = "warning"  # Log a warning but continue
    TRANSFORM = "transform"  # Try to transform data to valid format
    DEFAULT = "default"  # Use default value
    SKIP = "skip"  # Skip field mapping


class FieldMapping(BaseModel):
    """
    Defines mapping for a single field from Zephyr to qTest.

    This model specifies how a field should be transformed, validated,
    and what to do when validation fails.
    """

    source_field: str
    target_field: str
    required: bool = False
    transform_function: Callable | None = None
    validation_function: Callable | None = None
    validation_action: ValidationAction = ValidationAction.WARNING
    default_value: Any = None
    description: str | None = None

    def validate_and_transform(self, source_value: Any) -> tuple[bool, Any, str | None]:
        """
        Validate and transform a source value according to mapping rules.

        Args:
            source_value: The value from the source entity

        Returns:
            Tuple of (is_valid, transformed_value, error_message)

        """
        transformed_value = source_value
        is_valid = True
        error_message = None

        # Handle if source value is None
        if source_value is None:
            if self.required:
                is_valid = False
                error_message = f"Required field '{self.source_field}' is missing"

                # Apply default value if validation action is DEFAULT
                if (
                    self.validation_action == ValidationAction.DEFAULT
                    and self.default_value is not None
                ):
                    transformed_value = self.default_value
                    is_valid = True
                    error_message = None
            # Apply transform function for None values even if not required
            # This allows transform functions to provide default values for None
            elif self.transform_function and callable(self.transform_function):
                try:
                    transformed_value = self.transform_function(None)
                    is_valid = True
                except Exception:
                    # If transform fails on None, keep None value and stay valid
                    pass

            return is_valid, transformed_value, error_message

        # Apply transformation if provided
        if self.transform_function and callable(self.transform_function):
            try:
                transformed_value = self.transform_function(source_value)
            except Exception as e:
                is_valid = False
                error_message = f"Transform failed for '{self.source_field}': {e!s}"
                # Handle transform error based on validation action
                if self.validation_action == ValidationAction.ERROR:
                    raise ValueError(error_message)
                if self.validation_action == ValidationAction.DEFAULT:
                    transformed_value = self.default_value
                    is_valid = True
                    error_message = None

        # Apply validation if provided
        if is_valid and self.validation_function and callable(self.validation_function):
            try:
                is_valid = self.validation_function(transformed_value)
                if not is_valid:
                    error_message = f"Validation failed for '{self.source_field}'"

                    # Handle validation error based on validation action
                    if self.validation_action == ValidationAction.ERROR:
                        raise ValueError(error_message)
                    if self.validation_action == ValidationAction.DEFAULT:
                        transformed_value = self.default_value
                        is_valid = True
                        error_message = None
            except Exception as e:
                is_valid = False
                error_message = f"Validation error for '{self.source_field}': {e!s}"

                # Handle validation exception based on validation action
                if self.validation_action == ValidationAction.ERROR:
                    raise ValueError(error_message)
                if self.validation_action == ValidationAction.DEFAULT:
                    transformed_value = self.default_value
                    is_valid = True
                    error_message = None

        return is_valid, transformed_value, error_message


class EntityMapping(BaseModel):
    """
    Defines mapping between entity types from Zephyr to qTest.

    This model specifies how an entire entity should be mapped, including
    field-level mappings, custom field handling, and relationship preservation.
    """

    source_type: EntityType
    target_type: str  # The target qTest entity type
    field_mappings: list[FieldMapping]
    custom_field_mapping_enabled: bool = True
    description: str | None = None

    def map_entity(self, source_entity: dict[str, Any], field_mapper=None) -> dict[str, Any]:
        """
        Map a source entity to a target entity based on the mapping definitions.

        Args:
            source_entity: The source entity from Zephyr
            field_mapper: Optional custom field mapper instance

        Returns:
            Dict representing the mapped target entity

        Raises:
            ValueError: If a required field is missing and validation action is ERROR

        """
        if field_mapper is None:
            field_mapper = get_default_field_mapper()

        target_entity = {}
        validation_issues = []

        # Apply field mappings
        for mapping in self.field_mappings:
            source_value = source_entity.get(mapping.source_field)
            is_valid, transformed_value, error_message = mapping.validate_and_transform(
                source_value,
            )

            # If field is not valid and action is ERROR, raise exception immediately
            if (
                not is_valid
                and error_message
                and mapping.validation_action == ValidationAction.ERROR
            ):
                raise ValueError(error_message)

            # Add field to target entity if valid or if we're using a default value
            if is_valid or mapping.validation_action != ValidationAction.SKIP:
                target_entity[mapping.target_field] = transformed_value

            # Track validation issues and log warnings
            if not is_valid and error_message:
                validation_issues.append(error_message)
                if mapping.validation_action == ValidationAction.WARNING:
                    logger.warning(error_message)

        # Handle custom fields if enabled
        if self.custom_field_mapping_enabled and source_entity.get("customFields", []):
            # Apply the specific mapping based on entity type
            if self.source_type == EntityType.TEST_CASE:
                target_entity["properties"] = field_mapper.map_testcase_fields(source_entity)
            elif self.source_type == EntityType.TEST_CYCLE:
                target_entity["properties"] = field_mapper.map_testcycle_fields(source_entity)
            elif self.source_type == EntityType.TEST_EXECUTION:
                target_entity["properties"] = field_mapper.map_testrun_fields(source_entity)
            else:
                # Generic custom field mapping
                target_entity["properties"] = field_mapper.map_custom_fields(
                    source_entity.get("customFields", []),
                )

        return target_entity


class MappingRegistry:
    """Registry for all entity mappings defined in the system."""

    def __init__(self):
        """Initialize the mapping registry."""
        self.mappings: dict[EntityType, EntityMapping] = {}
        self.field_mapper = get_default_field_mapper()
        self._initialize_mappings()

    def _initialize_mappings(self):
        """Initialize all predefined entity mappings."""
        # Project mapping
        self.register_mapping(self._create_project_mapping())

        # Folder mapping
        self.register_mapping(self._create_folder_mapping())

        # Test case mapping
        self.register_mapping(self._create_test_case_mapping())

        # Test step mapping
        self.register_mapping(self._create_test_step_mapping())

        # Test cycle mapping
        self.register_mapping(self._create_test_cycle_mapping())

        # Test execution mapping
        self.register_mapping(self._create_test_execution_mapping())

        # Test step result mapping
        self.register_mapping(self._create_test_step_result_mapping())

        # Attachment mapping
        self.register_mapping(self._create_attachment_mapping())

    def register_mapping(self, mapping: EntityMapping):
        """
        Register an entity mapping.

        Args:
            mapping: The entity mapping to register

        """
        self.mappings[mapping.source_type] = mapping

    def get_mapping(self, entity_type: EntityType) -> EntityMapping | None:
        """
        Get the entity mapping for a specific type.

        Args:
            entity_type: The entity type to get mapping for

        Returns:
            EntityMapping if found, None otherwise

        """
        return self.mappings.get(entity_type)

    def map_entity(self, entity_type: EntityType, source_entity: dict[str, Any]) -> dict[str, Any]:
        """
        Map a source entity to a target entity.

        Args:
            entity_type: The type of entity to map
            source_entity: The source entity from Zephyr

        Returns:
            Dict representing the mapped target entity

        Raises:
            ValueError: If no mapping exists for the entity type

        """
        mapping = self.get_mapping(entity_type)
        if not mapping:
            raise ValueError(f"No mapping found for entity type {entity_type}")

        return mapping.map_entity(source_entity, self.field_mapper)

    # Create mapping definitions for each entity type
    def _create_project_mapping(self) -> EntityMapping:
        """Create mapping for Project entity."""
        return EntityMapping(
            source_type=EntityType.PROJECT,
            target_type="QTestProject",
            description="Maps Zephyr project to qTest project",
            field_mappings=[
                FieldMapping(
                    source_field="name",
                    target_field="name",
                    required=True,
                    validation_action=ValidationAction.ERROR,
                    description="Project name",
                ),
                FieldMapping(
                    source_field="description",
                    target_field="description",
                    description="Project description",
                ),
                # qTest project ID comes from config, not mapped from Zephyr
                FieldMapping(
                    source_field="key",
                    target_field="zephyr_key",
                    transform_function=lambda x: x,  # Store for reference
                    description="Zephyr project key",
                ),
            ],
            custom_field_mapping_enabled=False,
        )

    def _create_folder_mapping(self) -> EntityMapping:
        """Create mapping for Folder entity."""
        return EntityMapping(
            source_type=EntityType.FOLDER,
            target_type="QTestModule",
            description="Maps Zephyr folder to qTest module",
            field_mappings=[
                FieldMapping(
                    source_field="name",
                    target_field="name",
                    required=True,
                    validation_action=ValidationAction.ERROR,
                    description="Folder name",
                ),
                FieldMapping(
                    source_field="description",
                    target_field="description",
                    default_value="",
                    description="Folder description",
                ),
                FieldMapping(
                    source_field="parentId",
                    target_field="parent_id",
                    description="Parent folder ID (must be mapped to module ID)",
                ),
                # folderType is not directly mapped but can be used for custom logic
            ],
            custom_field_mapping_enabled=False,
        )

    def _create_test_case_mapping(self) -> EntityMapping:
        """Create mapping for TestCase entity."""
        return EntityMapping(
            source_type=EntityType.TEST_CASE,
            target_type="QTestTestCase",
            description="Maps Zephyr test case to qTest test case",
            field_mappings=[
                FieldMapping(
                    source_field="name",
                    target_field="name",
                    required=True,
                    validation_action=ValidationAction.ERROR,
                    description="Test case name",
                ),
                FieldMapping(
                    source_field="objective",
                    target_field="description",
                    description="Test case objective/description",
                ),
                FieldMapping(
                    source_field="precondition",
                    target_field="precondition",
                    description="Test case precondition",
                ),
                FieldMapping(
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
                    description="Test case priority (mapped to qTest priority ID)",
                ),
                FieldMapping(
                    source_field="folderId",
                    target_field="module_id",
                    description="Parent folder ID (must be mapped to module ID)",
                ),
                # Steps are handled separately
                # Attachments are handled separately
            ],
            custom_field_mapping_enabled=True,
        )

    def _create_test_step_mapping(self) -> EntityMapping:
        """Create mapping for TestStep entity."""
        return EntityMapping(
            source_type=EntityType.TEST_STEP,
            target_type="QTestStep",
            description="Maps Zephyr test step to qTest test step",
            field_mappings=[
                FieldMapping(
                    source_field="description",
                    target_field="description",
                    required=True,
                    validation_action=ValidationAction.ERROR,
                    description="Test step description",
                ),
                FieldMapping(
                    source_field="expectedResult",
                    target_field="expected_result",
                    description="Test step expected result",
                ),
                FieldMapping(
                    source_field="testData",
                    target_field="test_data",
                    # testData is combined with description in final transformation
                    description="Test step test data",
                ),
                FieldMapping(
                    source_field="order",
                    target_field="order",
                    default_value=1,
                    description="Test step order/sequence",
                ),
            ],
            custom_field_mapping_enabled=False,
        )

    def _create_test_cycle_mapping(self) -> EntityMapping:
        """Create mapping for TestCycle entity."""
        return EntityMapping(
            source_type=EntityType.TEST_CYCLE,
            target_type="QTestTestCycle",
            description="Maps Zephyr test cycle to qTest test cycle",
            field_mappings=[
                FieldMapping(
                    source_field="name",
                    target_field="name",
                    required=True,
                    validation_action=ValidationAction.ERROR,
                    description="Test cycle name",
                ),
                FieldMapping(
                    source_field="description",
                    target_field="description",
                    description="Test cycle description",
                ),
                FieldMapping(
                    source_field="startDate",
                    target_field="start_date",
                    description="Test cycle start date",
                ),
                FieldMapping(
                    source_field="endDate",
                    target_field="end_date",
                    description="Test cycle end date",
                ),
                FieldMapping(
                    source_field="folderId",
                    target_field="parent_id",
                    description="Parent folder ID (must be mapped to module ID)",
                ),
                # Key is stored in custom fields
            ],
            custom_field_mapping_enabled=True,
        )

    def _create_test_execution_mapping(self) -> EntityMapping:
        """Create mapping for TestExecution entity."""

        def _map_status(status: str) -> str:
            """Map Zephyr execution status to qTest status."""
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

        return EntityMapping(
            source_type=EntityType.TEST_EXECUTION,
            target_type="QTestTestRun",
            description="Maps Zephyr test execution to qTest test run",
            field_mappings=[
                FieldMapping(
                    source_field="name",
                    target_field="name",
                    default_value="Test Run",
                    description="Test run name",
                ),
                FieldMapping(
                    source_field="testCaseId",
                    target_field="test_case_id",
                    required=True,
                    validation_action=ValidationAction.ERROR,
                    description="Associated test case ID (must be mapped to qTest test case ID)",
                ),
                FieldMapping(
                    source_field="testCycleId",
                    target_field="test_cycle_id",
                    description="Associated test cycle ID (must be mapped to qTest test cycle ID)",
                ),
                FieldMapping(
                    source_field="status",
                    target_field="status",
                    transform_function=_map_status,
                    description="Execution status mapped to qTest status",
                ),
                FieldMapping(
                    source_field="comment",
                    target_field="note",
                    description="Execution comment/notes",
                ),
                FieldMapping(
                    source_field="executedBy",
                    target_field="executed_by",
                    description="User who executed the test",
                ),
                FieldMapping(
                    source_field="executedOn",
                    target_field="execution_date",
                    description="Date when the test was executed",
                ),
                # Attachments are handled separately
            ],
            custom_field_mapping_enabled=True,
        )

    def _create_test_step_result_mapping(self) -> EntityMapping:
        """Create mapping for TestStepResult entity."""
        return EntityMapping(
            source_type=EntityType.TEST_STEP_RESULT,
            target_type="QTestStepLog",
            description="Maps Zephyr test step result to qTest step log",
            field_mappings=[
                FieldMapping(
                    source_field="status",
                    target_field="status",
                    transform_function=lambda s: {
                        "pass": "PASSED",
                        "fail": "FAILED",
                        "wip": "IN_PROGRESS",
                        "blocked": "BLOCKED",
                        "unexecuted": "NOT_RUN",
                        "not_executed": "NOT_RUN",
                        "passed": "PASSED",
                        "failed": "FAILED",
                    }.get(str(s).lower(), "NOT_RUN")
                    if s
                    else "NOT_RUN",
                    description="Step result status",
                ),
                FieldMapping(
                    source_field="comment",
                    target_field="actual_result",
                    description="Step result comment mapped to actual result",
                ),
                FieldMapping(
                    source_field="order",
                    target_field="order",
                    required=True,
                    default_value=1,
                    description="Step order/sequence",
                ),
                # Attachments are handled separately
                # Defects are mapped to custom fields
            ],
            custom_field_mapping_enabled=False,
        )

    def _create_attachment_mapping(self) -> EntityMapping:
        """Create mapping for Attachment entity."""
        return EntityMapping(
            source_type=EntityType.ATTACHMENT,
            target_type="QTestAttachment",
            description="Maps Zephyr attachment to qTest attachment",
            field_mappings=[
                FieldMapping(
                    source_field="filename",
                    target_field="name",
                    required=True,
                    validation_action=ValidationAction.ERROR,
                    description="Attachment filename",
                ),
                FieldMapping(
                    source_field="contentType",
                    target_field="content_type",
                    default_value="application/octet-stream",
                    description="Attachment content type/MIME type",
                ),
                FieldMapping(
                    source_field="fileSize",
                    target_field="size",
                    description="Attachment file size in bytes",
                ),
                FieldMapping(
                    source_field="content",
                    target_field="content",
                    description="Attachment binary content (handled separately in most cases)",
                ),
                FieldMapping(
                    source_field="relatedEntityId",
                    target_field="related_id",
                    required=True,
                    description="ID of the entity this attachment belongs to",
                ),
                FieldMapping(
                    source_field="relatedEntityType",
                    target_field="related_type",
                    required=True,
                    description="Type of entity this attachment belongs to",
                ),
            ],
            custom_field_mapping_enabled=False,
        )


# Global registry instance for convenience
_registry = MappingRegistry()


def get_mapping_registry() -> MappingRegistry:
    """Get the global mapping registry instance."""
    return _registry


def map_entity(entity_type: EntityType, source_entity: dict[str, Any]) -> dict[str, Any]:
    """
    Map a source entity to a target entity using the global registry.

    Args:
        entity_type: The type of entity to map
        source_entity: The source entity from Zephyr

    Returns:
        Dict representing the mapped target entity

    """
    return _registry.map_entity(entity_type, source_entity)


# Convenience functions for common mapping operations
def map_project(project: dict[str, Any]) -> dict[str, Any]:
    """Map a Zephyr project to a qTest project."""
    return map_entity(EntityType.PROJECT, project)


def map_folder(folder: dict[str, Any]) -> dict[str, Any]:
    """Map a Zephyr folder to a qTest module."""
    return map_entity(EntityType.FOLDER, folder)


def map_test_case(test_case: dict[str, Any]) -> dict[str, Any]:
    """Map a Zephyr test case to a qTest test case."""
    return map_entity(EntityType.TEST_CASE, test_case)


def map_test_cycle(test_cycle: dict[str, Any]) -> dict[str, Any]:
    """Map a Zephyr test cycle to a qTest test cycle."""
    return map_entity(EntityType.TEST_CYCLE, test_cycle)


def map_test_execution(test_execution: dict[str, Any]) -> dict[str, Any]:
    """Map a Zephyr test execution to a qTest test run."""
    return map_entity(EntityType.TEST_EXECUTION, test_execution)
