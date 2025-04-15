"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Validation rules for ZTOQ migrations.

This module defines specific validation rules applied during the migration process
to ensure data quality and integrity.
"""

import re
import time
import jsonschema
from typing import Any, Dict, List, Optional, Pattern, Tuple
from ztoq.data_comparison import get_data_comparison_rules
from ztoq.validation import (
    ValidationIssue,
    ValidationLevel,
    ValidationPhase,
    ValidationRule,
    ValidationScope,
)
from ztoq.custom_field_mapping import get_default_field_mapper


class RequiredFieldRule(ValidationRule):
    """Rule that validates required fields are present and non-empty."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        scope: ValidationScope,
        phase: ValidationPhase,
        required_fields: List[str],
        level: ValidationLevel = ValidationLevel.ERROR,
    ):
        """
        Initialize the required field rule.

        Args:
            id: Unique identifier for the rule
            name: Name of the rule
            description: Description of the rule
            scope: Scope where the rule applies
            phase: Phase where the rule applies
            required_fields: List of field names that must be present and non-empty
            level: Validation level for issues found by this rule
        """
        super().__init__(id, name, description, scope, phase, level)
        self.required_fields = required_fields

    def validate(self, entity: Any, context: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate that required fields are present and non-empty.

        Args:
            entity: The entity to validate
            context: Additional context for validation

        Returns:
            List of validation issues found
        """
        issues = []

        # Handle different entity types
        if isinstance(entity, dict):
            # For dictionary-like entities
            entity_id = entity.get("id") or entity.get("key") or str(id(entity))
            entity_type = context.get("entity_type", self.scope.value)

            for field in self.required_fields:
                if field not in entity or entity[field] is None or entity[field] == "":
                    issue = ValidationIssue(
                        id=f"required_field_{field}_{entity_id}_{int(time.time())}",
                        level=self.level,
                        scope=self.scope,
                        phase=self.phase,
                        message=f"Required field '{field}' is missing or empty",
                        entity_id=str(entity_id),
                        entity_type=entity_type,
                        field_name=field,
                    )
                    issues.append(issue)
        else:
            # For object-like entities
            entity_id = getattr(entity, "id", None) or str(id(entity))
            entity_type = context.get("entity_type", self.scope.value)

            for field in self.required_fields:
                if (
                    not hasattr(entity, field)
                    or getattr(entity, field) is None
                    or getattr(entity, field) == ""
                ):
                    issue = ValidationIssue(
                        id=f"required_field_{field}_{entity_id}_{int(time.time())}",
                        level=self.level,
                        scope=self.scope,
                        phase=self.phase,
                        message=f"Required field '{field}' is missing or empty",
                        entity_id=str(entity_id),
                        entity_type=entity_type,
                        field_name=field,
                    )
                    issues.append(issue)

        return issues


class StringLengthRule(ValidationRule):
    """Rule that validates string field lengths."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        scope: ValidationScope,
        phase: ValidationPhase,
        field_limits: Dict[str, Dict[str, int]],
        level: ValidationLevel = ValidationLevel.ERROR,
    ):
        """
        Initialize the string length rule.

        Args:
            id: Unique identifier for the rule
            name: Name of the rule
            description: Description of the rule
            scope: Scope where the rule applies
            phase: Phase where the rule applies
            field_limits: Dict mapping field names to min/max length limits
            level: Validation level for issues found by this rule
        """
        super().__init__(id, name, description, scope, phase, level)
        self.field_limits = field_limits

    def validate(self, entity: Any, context: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate string field lengths.

        Args:
            entity: The entity to validate
            context: Additional context for validation

        Returns:
            List of validation issues found
        """
        issues = []

        # Handle different entity types
        if isinstance(entity, dict):
            # For dictionary-like entities
            entity_id = entity.get("id") or entity.get("key") or str(id(entity))
            entity_type = context.get("entity_type", self.scope.value)

            for field, limits in self.field_limits.items():
                if field in entity and entity[field] is not None and isinstance(entity[field], str):
                    field_value = entity[field]
                    field_len = len(field_value)

                    # Check minimum length
                    if "min" in limits and field_len < limits["min"]:
                        issue = ValidationIssue(
                            id=f"min_length_{field}_{entity_id}_{int(time.time())}",
                            level=self.level,
                            scope=self.scope,
                            phase=self.phase,
                            message=f"Field '{field}' length ({field_len}) is less than minimum ({limits['min']})",
                            entity_id=str(entity_id),
                            entity_type=entity_type,
                            field_name=field,
                            details={
                                "value": field_value,
                                "length": field_len,
                                "min": limits["min"],
                            },
                        )
                        issues.append(issue)

                    # Check maximum length
                    if "max" in limits and field_len > limits["max"]:
                        issue = ValidationIssue(
                            id=f"max_length_{field}_{entity_id}_{int(time.time())}",
                            level=self.level,
                            scope=self.scope,
                            phase=self.phase,
                            message=f"Field '{field}' length ({field_len}) exceeds maximum ({limits['max']})",
                            entity_id=str(entity_id),
                            entity_type=entity_type,
                            field_name=field,
                            details={
                                "value": field_value[:50] + "..."
                                if field_len > 50
                                else field_value,
                                "length": field_len,
                                "max": limits["max"],
                            },
                        )
                        issues.append(issue)
        else:
            # For object-like entities
            entity_id = getattr(entity, "id", None) or str(id(entity))
            entity_type = context.get("entity_type", self.scope.value)

            for field, limits in self.field_limits.items():
                if (
                    hasattr(entity, field)
                    and getattr(entity, field) is not None
                    and isinstance(getattr(entity, field), str)
                ):
                    field_value = getattr(entity, field)
                    field_len = len(field_value)

                    # Check minimum length
                    if "min" in limits and field_len < limits["min"]:
                        issue = ValidationIssue(
                            id=f"min_length_{field}_{entity_id}_{int(time.time())}",
                            level=self.level,
                            scope=self.scope,
                            phase=self.phase,
                            message=f"Field '{field}' length ({field_len}) is less than minimum ({limits['min']})",
                            entity_id=str(entity_id),
                            entity_type=entity_type,
                            field_name=field,
                            details={
                                "value": field_value,
                                "length": field_len,
                                "min": limits["min"],
                            },
                        )
                        issues.append(issue)

                    # Check maximum length
                    if "max" in limits and field_len > limits["max"]:
                        issue = ValidationIssue(
                            id=f"max_length_{field}_{entity_id}_{int(time.time())}",
                            level=self.level,
                            scope=self.scope,
                            phase=self.phase,
                            message=f"Field '{field}' length ({field_len}) exceeds maximum ({limits['max']})",
                            entity_id=str(entity_id),
                            entity_type=entity_type,
                            field_name=field,
                            details={
                                "value": field_value[:50] + "..."
                                if field_len > 50
                                else field_value,
                                "length": field_len,
                                "max": limits["max"],
                            },
                        )
                        issues.append(issue)

        return issues


class PatternMatchRule(ValidationRule):
    """Rule that validates field values match a regex pattern."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        scope: ValidationScope,
        phase: ValidationPhase,
        field_patterns: Dict[str, str],
        level: ValidationLevel = ValidationLevel.ERROR,
    ):
        """
        Initialize the pattern match rule.

        Args:
            id: Unique identifier for the rule
            name: Name of the rule
            description: Description of the rule
            scope: Scope where the rule applies
            phase: Phase where the rule applies
            field_patterns: Dict mapping field names to regex patterns
            level: Validation level for issues found by this rule
        """
        super().__init__(id, name, description, scope, phase, level)
        self.field_patterns = {
            field: re.compile(pattern) for field, pattern in field_patterns.items()
        }

    def validate(self, entity: Any, context: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate field values match regex patterns.

        Args:
            entity: The entity to validate
            context: Additional context for validation

        Returns:
            List of validation issues found
        """
        issues = []

        # Handle different entity types
        if isinstance(entity, dict):
            # For dictionary-like entities
            entity_id = entity.get("id") or entity.get("key") or str(id(entity))
            entity_type = context.get("entity_type", self.scope.value)

            for field, pattern in self.field_patterns.items():
                if field in entity and entity[field] is not None and isinstance(entity[field], str):
                    field_value = entity[field]

                    if not pattern.match(field_value):
                        issue = ValidationIssue(
                            id=f"pattern_mismatch_{field}_{entity_id}_{int(time.time())}",
                            level=self.level,
                            scope=self.scope,
                            phase=self.phase,
                            message=f"Field '{field}' value does not match required pattern",
                            entity_id=str(entity_id),
                            entity_type=entity_type,
                            field_name=field,
                            details={
                                "value": field_value[:50] + "..."
                                if len(field_value) > 50
                                else field_value,
                                "pattern": pattern.pattern,
                            },
                        )
                        issues.append(issue)
        else:
            # For object-like entities
            entity_id = getattr(entity, "id", None) or str(id(entity))
            entity_type = context.get("entity_type", self.scope.value)

            for field, pattern in self.field_patterns.items():
                if (
                    hasattr(entity, field)
                    and getattr(entity, field) is not None
                    and isinstance(getattr(entity, field), str)
                ):
                    field_value = getattr(entity, field)

                    if not pattern.match(field_value):
                        issue = ValidationIssue(
                            id=f"pattern_mismatch_{field}_{entity_id}_{int(time.time())}",
                            level=self.level,
                            scope=self.scope,
                            phase=self.phase,
                            message=f"Field '{field}' value does not match required pattern",
                            entity_id=str(entity_id),
                            entity_type=entity_type,
                            field_name=field,
                            details={
                                "value": field_value[:50] + "..."
                                if len(field_value) > 50
                                else field_value,
                                "pattern": pattern.pattern,
                            },
                        )
                        issues.append(issue)

        return issues


class RelationshipRule(ValidationRule):
    """Rule that validates entity relationships."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        scope: ValidationScope,
        phase: ValidationPhase,
        relation_field: str,
        related_entity_type: str,
        level: ValidationLevel = ValidationLevel.ERROR,
    ):
        """
        Initialize the relationship rule.

        Args:
            id: Unique identifier for the rule
            name: Name of the rule
            description: Description of the rule
            scope: Scope where the rule applies
            phase: Phase where the rule applies
            relation_field: Field that should contain the related entity ID
            related_entity_type: Type of the related entity
            level: Validation level for issues found by this rule
        """
        super().__init__(id, name, description, scope, phase, level)
        self.relation_field = relation_field
        self.related_entity_type = related_entity_type

    def validate(self, entity: Any, context: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate entity relationships.

        Args:
            entity: The entity to validate
            context: Additional context for validation

        Returns:
            List of validation issues found
        """
        issues = []
        database = context.get("database")

        if not database:
            # Cannot validate relationships without database access
            return issues

        # Handle different entity types
        if isinstance(entity, dict):
            # For dictionary-like entities
            entity_id = entity.get("id") or entity.get("key") or str(id(entity))
            entity_type = context.get("entity_type", self.scope.value)

            if self.relation_field in entity and entity[self.relation_field] is not None:
                related_id = entity[self.relation_field]

                # Check if the related entity exists
                if not database.entity_exists(self.related_entity_type, related_id):
                    issue = ValidationIssue(
                        id=f"invalid_relation_{self.relation_field}_{entity_id}_{int(time.time())}",
                        level=self.level,
                        scope=self.scope,
                        phase=self.phase,
                        message=f"Field '{self.relation_field}' references non-existent {self.related_entity_type}",
                        entity_id=str(entity_id),
                        entity_type=entity_type,
                        field_name=self.relation_field,
                        details={
                            "related_entity_type": self.related_entity_type,
                            "related_id": str(related_id),
                        },
                    )
                    issues.append(issue)
        else:
            # For object-like entities
            entity_id = getattr(entity, "id", None) or str(id(entity))
            entity_type = context.get("entity_type", self.scope.value)

            if (
                hasattr(entity, self.relation_field)
                and getattr(entity, self.relation_field) is not None
            ):
                related_id = getattr(entity, self.relation_field)

                # Check if the related entity exists
                if not database.entity_exists(self.related_entity_type, related_id):
                    issue = ValidationIssue(
                        id=f"invalid_relation_{self.relation_field}_{entity_id}_{int(time.time())}",
                        level=self.level,
                        scope=self.scope,
                        phase=self.phase,
                        message=f"Field '{self.relation_field}' references non-existent {self.related_entity_type}",
                        entity_id=str(entity_id),
                        entity_type=entity_type,
                        field_name=self.relation_field,
                        details={
                            "related_entity_type": self.related_entity_type,
                            "related_id": str(related_id),
                        },
                    )
                    issues.append(issue)

        return issues


class UniqueValueRule(ValidationRule):
    """Rule that validates field values are unique across entities."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        scope: ValidationScope,
        phase: ValidationPhase,
        unique_fields: List[str],
        level: ValidationLevel = ValidationLevel.ERROR,
    ):
        """
        Initialize the unique value rule.

        Args:
            id: Unique identifier for the rule
            name: Name of the rule
            description: Description of the rule
            scope: Scope where the rule applies
            phase: Phase where the rule applies
            unique_fields: List of fields that should have unique values
            level: Validation level for issues found by this rule
        """
        super().__init__(id, name, description, scope, phase, level)
        self.unique_fields = unique_fields

    def validate(self, entity: Any, context: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate field values are unique.

        Args:
            entity: The entity to validate
            context: Additional context for validation

        Returns:
            List of validation issues found
        """
        issues = []
        database = context.get("database")

        if not database:
            # Cannot validate uniqueness without database access
            return issues

        # Handle different entity types
        if isinstance(entity, dict):
            # For dictionary-like entities
            entity_id = entity.get("id") or entity.get("key") or str(id(entity))
            entity_type = context.get("entity_type", self.scope.value)

            for field in self.unique_fields:
                if field in entity and entity[field] is not None:
                    field_value = entity[field]

                    # Check if another entity has the same value for this field
                    duplicates = database.find_duplicates(
                        entity_type, field, field_value, exclude_id=entity_id
                    )

                    if duplicates:
                        issue = ValidationIssue(
                            id=f"duplicate_value_{field}_{entity_id}_{int(time.time())}",
                            level=self.level,
                            scope=self.scope,
                            phase=self.phase,
                            message=f"Field '{field}' value is not unique",
                            entity_id=str(entity_id),
                            entity_type=entity_type,
                            field_name=field,
                            details={
                                "value": field_value,
                                "duplicate_ids": [str(dup) for dup in duplicates[:5]],
                                "duplicate_count": len(duplicates),
                            },
                        )
                        issues.append(issue)
        else:
            # For object-like entities
            entity_id = getattr(entity, "id", None) or str(id(entity))
            entity_type = context.get("entity_type", self.scope.value)

            for field in self.unique_fields:
                if hasattr(entity, field) and getattr(entity, field) is not None:
                    field_value = getattr(entity, field)

                    # Check if another entity has the same value for this field
                    duplicates = database.find_duplicates(
                        entity_type, field, field_value, exclude_id=entity_id
                    )

                    if duplicates:
                        issue = ValidationIssue(
                            id=f"duplicate_value_{field}_{entity_id}_{int(time.time())}",
                            level=self.level,
                            scope=self.scope,
                            phase=self.phase,
                            message=f"Field '{field}' value is not unique",
                            entity_id=str(entity_id),
                            entity_type=entity_type,
                            field_name=field,
                            details={
                                "value": field_value,
                                "duplicate_ids": [str(dup) for dup in duplicates[:5]],
                                "duplicate_count": len(duplicates),
                            },
                        )
                        issues.append(issue)

        return issues


class CustomFieldRule(ValidationRule):
    """Rule that validates custom fields conform to expected types and constraints."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        scope: ValidationScope,
        phase: ValidationPhase,
        field_constraints: Dict[str, Dict[str, Any]],
        level: ValidationLevel = ValidationLevel.WARNING,
    ):
        """
        Initialize the custom field rule.

        Args:
            id: Unique identifier for the rule
            name: Name of the rule
            description: Description of the rule
            scope: Scope where the rule applies
            phase: Phase where the rule applies
            field_constraints: Dict mapping field names to constraints
            level: Validation level for issues found by this rule
        """
        super().__init__(id, name, description, scope, phase, level)
        self.field_constraints = field_constraints

    def validate(self, entity: Any, context: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate custom fields.

        Args:
            entity: The entity to validate
            context: Additional context for validation

        Returns:
            List of validation issues found
        """
        issues = []

        # Get custom fields from the entity
        custom_fields = None
        entity_id = None
        entity_type = context.get("entity_type", self.scope.value)

        if isinstance(entity, dict):
            entity_id = entity.get("id") or entity.get("key") or str(id(entity))
            custom_fields = entity.get("customFields", {})
        else:
            entity_id = getattr(entity, "id", None) or str(id(entity))
            custom_fields = getattr(entity, "custom_fields", None) or getattr(
                entity, "customFields", {}
            )

        if not custom_fields or not isinstance(custom_fields, dict):
            return issues

        # Validate each custom field against constraints
        for field_name, field_value in custom_fields.items():
            if field_name in self.field_constraints:
                constraints = self.field_constraints[field_name]

                # Validate field type
                if "type" in constraints:
                    expected_type = constraints["type"]

                    if expected_type == "string" and not isinstance(field_value, str):
                        issue = ValidationIssue(
                            id=f"custom_field_type_{field_name}_{entity_id}_{int(time.time())}",
                            level=self.level,
                            scope=ValidationScope.CUSTOM_FIELD,
                            phase=self.phase,
                            message=f"Custom field '{field_name}' should be a string",
                            entity_id=str(entity_id),
                            entity_type=entity_type,
                            field_name=field_name,
                            details={"value": field_value, "expected_type": expected_type},
                        )
                        issues.append(issue)

                    elif expected_type == "number" and not isinstance(field_value, (int, float)):
                        issue = ValidationIssue(
                            id=f"custom_field_type_{field_name}_{entity_id}_{int(time.time())}",
                            level=self.level,
                            scope=ValidationScope.CUSTOM_FIELD,
                            phase=self.phase,
                            message=f"Custom field '{field_name}' should be a number",
                            entity_id=str(entity_id),
                            entity_type=entity_type,
                            field_name=field_name,
                            details={"value": field_value, "expected_type": expected_type},
                        )
                        issues.append(issue)

                    elif expected_type == "boolean" and not isinstance(field_value, bool):
                        issue = ValidationIssue(
                            id=f"custom_field_type_{field_name}_{entity_id}_{int(time.time())}",
                            level=self.level,
                            scope=ValidationScope.CUSTOM_FIELD,
                            phase=self.phase,
                            message=f"Custom field '{field_name}' should be a boolean",
                            entity_id=str(entity_id),
                            entity_type=entity_type,
                            field_name=field_name,
                            details={"value": field_value, "expected_type": expected_type},
                        )
                        issues.append(issue)

                    elif expected_type == "date" and not isinstance(field_value, str):
                        issue = ValidationIssue(
                            id=f"custom_field_type_{field_name}_{entity_id}_{int(time.time())}",
                            level=self.level,
                            scope=ValidationScope.CUSTOM_FIELD,
                            phase=self.phase,
                            message=f"Custom field '{field_name}' should be a date string",
                            entity_id=str(entity_id),
                            entity_type=entity_type,
                            field_name=field_name,
                            details={"value": field_value, "expected_type": expected_type},
                        )
                        issues.append(issue)

                # Validate allowed values
                if (
                    "allowed_values" in constraints
                    and field_value not in constraints["allowed_values"]
                ):
                    issue = ValidationIssue(
                        id=f"custom_field_value_{field_name}_{entity_id}_{int(time.time())}",
                        level=self.level,
                        scope=ValidationScope.CUSTOM_FIELD,
                        phase=self.phase,
                        message=f"Custom field '{field_name}' has invalid value",
                        entity_id=str(entity_id),
                        entity_type=entity_type,
                        field_name=field_name,
                        details={
                            "value": field_value,
                            "allowed_values": constraints["allowed_values"],
                        },
                    )
                    issues.append(issue)

        return issues


class AttachmentRule(ValidationRule):
    """Rule that validates attachments."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        phase: ValidationPhase,
        max_size: Optional[int] = None,
        allowed_extensions: Optional[List[str]] = None,
        level: ValidationLevel = ValidationLevel.WARNING,
    ):
        """
        Initialize the attachment rule.

        Args:
            id: Unique identifier for the rule
            name: Name of the rule
            description: Description of the rule
            phase: Phase where the rule applies
            max_size: Maximum allowed attachment size in bytes
            allowed_extensions: List of allowed file extensions
            level: Validation level for issues found by this rule
        """
        super().__init__(id, name, description, ValidationScope.ATTACHMENT, phase, level)
        self.max_size = max_size
        self.allowed_extensions = allowed_extensions

    def validate(self, entity: Any, context: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate attachments.

        Args:
            entity: The attachment to validate
            context: Additional context for validation

        Returns:
            List of validation issues found
        """
        issues = []

        # Extract attachment information
        attachment_id = None
        attachment_name = None
        attachment_size = None
        related_id = None
        related_type = None

        if isinstance(entity, dict):
            attachment_id = entity.get("id") or str(id(entity))
            attachment_name = entity.get("name") or entity.get("filename")
            attachment_size = entity.get("size") or len(entity.get("content", b""))
            related_id = entity.get("related_id")
            related_type = entity.get("related_type")
        else:
            attachment_id = getattr(entity, "id", None) or str(id(entity))
            attachment_name = getattr(entity, "name", None) or getattr(entity, "filename", None)
            attachment_size = getattr(entity, "size", None) or len(getattr(entity, "content", b""))
            related_id = getattr(entity, "related_id", None)
            related_type = getattr(entity, "related_type", None)

        # Validate maximum size
        if self.max_size is not None and attachment_size > self.max_size:
            issue = ValidationIssue(
                id=f"attachment_size_{attachment_id}_{int(time.time())}",
                level=self.level,
                scope=self.scope,
                phase=self.phase,
                message=f"Attachment exceeds maximum size of {self.max_size} bytes",
                entity_id=str(attachment_id),
                entity_type="Attachment",
                details={
                    "name": attachment_name,
                    "size": attachment_size,
                    "max_size": self.max_size,
                    "related_id": related_id,
                    "related_type": related_type,
                },
            )
            issues.append(issue)

        # Validate file extension
        if self.allowed_extensions is not None and attachment_name is not None:
            extension = attachment_name.split(".")[-1].lower() if "." in attachment_name else ""

            if extension not in self.allowed_extensions:
                issue = ValidationIssue(
                    id=f"attachment_extension_{attachment_id}_{int(time.time())}",
                    level=self.level,
                    scope=self.scope,
                    phase=self.phase,
                    message=f"Attachment has disallowed file extension: {extension}",
                    entity_id=str(attachment_id),
                    entity_type="Attachment",
                    details={
                        "name": attachment_name,
                        "extension": extension,
                        "allowed_extensions": self.allowed_extensions,
                        "related_id": related_id,
                        "related_type": related_type,
                    },
                )
                issues.append(issue)

        return issues


class JsonSchemaRule(ValidationRule):
    """Rule that validates entities against a JSON schema."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        scope: ValidationScope,
        phase: ValidationPhase,
        schema: Dict[str, Any],
        level: ValidationLevel = ValidationLevel.ERROR,
    ):
        """
        Initialize the JSON schema rule.

        Args:
            id: Unique identifier for the rule
            name: Name of the rule
            description: Description of the rule
            scope: Scope where the rule applies
            phase: Phase where the rule applies
            schema: The JSON schema to validate against
            level: Validation level for issues found by this rule
        """
        super().__init__(id, name, description, scope, phase, level)
        self.schema = schema
        try:
            # Import jsonschema library if available

            self.jsonschema = jsonschema
        except ImportError:
            self.jsonschema = None

    def validate(self, entity: Any, context: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate entity against JSON schema.

        Args:
            entity: The entity to validate
            context: Additional context for validation

        Returns:
            List of validation issues found
        """
        issues = []

        if not self.jsonschema:
            # Cannot validate without jsonschema library
            issue = ValidationIssue(
                id=f"json_schema_missing_library_{int(time.time())}",
                level=ValidationLevel.ERROR,
                scope=ValidationScope.SYSTEM,
                phase=self.phase,
                message="Cannot validate JSON schema: jsonschema library not available",
            )
            issues.append(issue)
            return issues

        # Extract entity information
        if isinstance(entity, dict):
            entity_id = entity.get("id") or entity.get("key") or str(id(entity))
            entity_type = context.get("entity_type", self.scope.value)
        else:
            entity_id = getattr(entity, "id", None) or str(id(entity))
            entity_type = context.get("entity_type", self.scope.value)

            # Convert object to dict if necessary
            if not isinstance(entity, dict):
                try:
                    # Try to convert to dict using model's dict() method (for Pydantic)
                    if hasattr(entity, "dict") and callable(entity.dict):
                        entity = entity.dict()
                    # Try to convert using __dict__
                    elif hasattr(entity, "__dict__"):
                        entity = entity.__dict__
                    else:
                        # Cannot validate non-dict entity
                        issue = ValidationIssue(
                            id=f"json_schema_not_dict_{entity_id}_{int(time.time())}",
                            level=self.level,
                            scope=self.scope,
                            phase=self.phase,
                            message="Cannot validate JSON schema: entity is not a dictionary",
                            entity_id=str(entity_id),
                            entity_type=entity_type,
                        )
                        issues.append(issue)
                        return issues
                except Exception as e:
                    # Error converting to dict
                    issue = ValidationIssue(
                        id=f"json_schema_conversion_error_{entity_id}_{int(time.time())}",
                        level=self.level,
                        scope=self.scope,
                        phase=self.phase,
                        message=f"Error converting entity to dictionary: {str(e)}",
                        entity_id=str(entity_id),
                        entity_type=entity_type,
                    )
                    issues.append(issue)
                    return issues

        # Validate against schema
        try:
            self.jsonschema.validate(entity, self.schema)
        except self.jsonschema.exceptions.ValidationError as e:
            # Create validation issue with details
            issue = ValidationIssue(
                id=f"json_schema_validation_{entity_id}_{int(time.time())}",
                level=self.level,
                scope=self.scope,
                phase=self.phase,
                message=f"JSON schema validation failed: {e.message}",
                entity_id=str(entity_id),
                entity_type=entity_type,
                details={
                    "schema_path": list(e.schema_path),
                    "absolute_path": list(e.absolute_path),
                    "validator": e.validator,
                    "validator_value": e.validator_value,
                },
            )
            issues.append(issue)

        return issues


class TestStepValidationRule(ValidationRule):
    """Rule that validates test case steps."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        phase: ValidationPhase,
        level: ValidationLevel = ValidationLevel.WARNING,
    ):
        """
        Initialize the test step validation rule.

        Args:
            id: Unique identifier for the rule
            name: Name of the rule
            description: Description of the rule
            phase: Phase where the rule applies
            level: Validation level for issues found by this rule
        """
        super().__init__(id, name, description, ValidationScope.TEST_CASE_STEP, phase, level)

    def validate(self, entity: Any, context: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate test case steps.

        Args:
            entity: The test case to validate
            context: Additional context for validation

        Returns:
            List of validation issues found
        """
        issues = []

        # Extract test case information
        test_case_id = None
        test_case_name = None
        steps = None

        if isinstance(entity, dict):
            test_case_id = entity.get("id") or entity.get("key") or str(id(entity))
            test_case_name = entity.get("name")
            steps = entity.get("steps") or []
        else:
            test_case_id = getattr(entity, "id", None) or str(id(entity))
            test_case_name = getattr(entity, "name", None)
            steps = getattr(entity, "steps", None) or []

        # Check for empty steps
        if not steps:
            issue = ValidationIssue(
                id=f"test_case_no_steps_{test_case_id}_{int(time.time())}",
                level=self.level,
                scope=self.scope,
                phase=self.phase,
                message="Test case has no steps",
                entity_id=str(test_case_id),
                entity_type="test_case",
                details={"test_case_name": test_case_name},
            )
            issues.append(issue)
            return issues

        # Validate each step
        for step_index, step in enumerate(steps):
            step_data = None

            if isinstance(step, dict):
                step_data = step
            elif hasattr(step, "__dict__"):
                step_data = step.__dict__
            else:
                continue

            # Check for empty step description
            description = step_data.get("description", "") or getattr(step, "description", "")
            if not description or description.strip() == "":
                issue = ValidationIssue(
                    id=f"test_step_empty_description_{test_case_id}_{step_index}_{int(time.time())}",
                    level=self.level,
                    scope=self.scope,
                    phase=self.phase,
                    message=f"Test step {step_index + 1} has empty description",
                    entity_id=str(test_case_id),
                    entity_type="test_case",
                    field_name=f"steps[{step_index}].description",
                    details={"test_case_name": test_case_name, "step_index": step_index},
                )
                issues.append(issue)

            # Check for empty expected result if required
            if self.phase != ValidationPhase.PRE_MIGRATION:  # Skip for initial validation
                expected_result = step_data.get("expected_result", "") or getattr(
                    step, "expected_result", ""
                )
                if not expected_result or expected_result.strip() == "":
                    issue = ValidationIssue(
                        id=f"test_step_empty_expected_result_{test_case_id}_{step_index}_{int(time.time())}",
                        level=ValidationLevel.INFO,  # Lower severity for expected results
                        scope=self.scope,
                        phase=self.phase,
                        message=f"Test step {step_index + 1} has empty expected result",
                        entity_id=str(test_case_id),
                        entity_type="test_case",
                        field_name=f"steps[{step_index}].expected_result",
                        details={"test_case_name": test_case_name, "step_index": step_index},
                    )
                    issues.append(issue)

        return issues


class DataIntegrityRule(ValidationRule):
    """Rule that validates data integrity during transformation."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        scope: ValidationScope,
        fields_to_compare: List[Tuple[str, str]],
        level: ValidationLevel = ValidationLevel.ERROR,
    ):
        """
        Initialize the data integrity rule.

        Args:
            id: Unique identifier for the rule
            name: Name of the rule
            description: Description of the rule
            scope: Scope where the rule applies
            fields_to_compare: List of tuples (source_field, target_field) to compare
            level: Validation level for issues found by this rule
        """
        super().__init__(id, name, description, scope, ValidationPhase.TRANSFORMATION, level)
        self.fields_to_compare = fields_to_compare

    def validate(self, entity: Any, context: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate data integrity during transformation.

        Args:
            entity: Not used directly
            context: Must contain 'source_entity' and 'target_entity'

        Returns:
            List of validation issues found
        """
        issues = []

        # Get source and target entities from context
        source_entity = context.get("source_entity")
        target_entity = context.get("target_entity")

        if not source_entity or not target_entity:
            return issues

        # Extract entity information
        if isinstance(source_entity, dict):
            source_id = (
                source_entity.get("id") or source_entity.get("key") or str(id(source_entity))
            )
        else:
            source_id = getattr(source_entity, "id", None) or str(id(source_entity))

        entity_type = context.get("entity_type", self.scope.value)

        # Compare fields
        for source_field, target_field in self.fields_to_compare:
            source_value = self._get_field_value(source_entity, source_field)
            target_value = self._get_field_value(target_entity, target_field)

            # Skip if either field is None
            if source_value is None or target_value is None:
                continue

            # Compare normalized values
            if self._normalize_value(source_value) != self._normalize_value(target_value):
                issue = ValidationIssue(
                    id=f"data_integrity_{source_field}_{source_id}_{int(time.time())}",
                    level=self.level,
                    scope=self.scope,
                    phase=ValidationPhase.TRANSFORMATION,
                    message=f"Data integrity issue: source field '{source_field}' value does not match target field '{target_field}' value",
                    entity_id=str(source_id),
                    entity_type=entity_type,
                    field_name=source_field,
                    details={
                        "source_field": source_field,
                        "target_field": target_field,
                        "source_value": source_value,
                        "target_value": target_value,
                    },
                )
                issues.append(issue)

        return issues

    def _get_field_value(self, entity: Any, field: str) -> Any:
        """Get field value from entity."""
        if isinstance(entity, dict):
            return entity.get(field)
        return getattr(entity, field, None)

    def _normalize_value(self, value: Any) -> str:
        """Normalize value for comparison."""
        if value is None:
            return ""

        if isinstance(value, bool):
            return str(value).lower()

        if isinstance(value, (int, float)):
            return str(value)

        return str(value).strip().lower()


class TestStatusMappingRule(ValidationRule):
    """Rule that validates test status mappings during transformation."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        status_mappings: Dict[str, str],
        level: ValidationLevel = ValidationLevel.WARNING,
    ):
        """
        Initialize the test status mapping rule.

        Args:
            id: Unique identifier for the rule
            name: Name of the rule
            description: Description of the rule
            status_mappings: Dict mapping Zephyr statuses to qTest statuses
            level: Validation level for issues found by this rule
        """
        super().__init__(
            id,
            name,
            description,
            ValidationScope.TEST_EXECUTION,
            ValidationPhase.TRANSFORMATION,
            level,
        )
        self.status_mappings = status_mappings

    def validate(self, entity: Any, context: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate test status mappings.

        Args:
            entity: Not used directly
            context: Must contain 'source_entity' and 'target_entity'

        Returns:
            List of validation issues found
        """
        issues = []

        # Get source and target entities from context
        source_entity = context.get("source_entity")
        target_entity = context.get("target_entity")

        if not source_entity or not target_entity:
            return issues

        # Extract entity information
        if isinstance(source_entity, dict):
            source_id = (
                source_entity.get("id") or source_entity.get("key") or str(id(source_entity))
            )
            source_status = source_entity.get("status")
        else:
            source_id = getattr(source_entity, "id", None) or str(id(source_entity))
            source_status = getattr(source_entity, "status", None)

        if isinstance(target_entity, dict):
            target_status = target_entity.get("status")
        else:
            target_status = getattr(target_entity, "status", None)

        # Skip if either status is None
        if source_status is None or target_status is None:
            return issues

        # Check if status mapping is correct
        expected_target_status = self.status_mappings.get(source_status)

        if expected_target_status and expected_target_status != target_status:
            issue = ValidationIssue(
                id=f"status_mapping_{source_id}_{int(time.time())}",
                level=self.level,
                scope=self.scope,
                phase=ValidationPhase.TRANSFORMATION,
                message=f"Test status mapping issue: Zephyr status '{source_status}' should map to qTest status '{expected_target_status}', but got '{target_status}'",
                entity_id=str(source_id),
                entity_type="test_execution",
                field_name="status",
                details={
                    "zephyr_status": source_status,
                    "qtest_status": target_status,
                    "expected_qtest_status": expected_target_status,
                },
            )
            issues.append(issue)

        return issues


class ReferentialIntegrityRule(ValidationRule):
    """Rule that validates referential integrity during migration."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        scope: ValidationScope,
        reference_field: str,
        mapping_type: str,
        level: ValidationLevel = ValidationLevel.ERROR,
    ):
        """
        Initialize the referential integrity rule.

        Args:
            id: Unique identifier for the rule
            name: Name of the rule
            description: Description of the rule
            scope: Scope where the rule applies
            reference_field: The field containing the reference ID
            mapping_type: The type of mapping to check
            level: Validation level for issues found by this rule
        """
        super().__init__(id, name, description, scope, ValidationPhase.TRANSFORMATION, level)
        self.reference_field = reference_field
        self.mapping_type = mapping_type

    def validate(self, entity: Any, context: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate referential integrity.

        Args:
            entity: The entity to validate
            context: Additional context for validation

        Returns:
            List of validation issues found
        """
        issues = []
        database = context.get("database")
        project_key = context.get("project_key")

        if not database or not project_key:
            # Cannot validate referential integrity without database access
            return issues

        # Extract entity information
        if isinstance(entity, dict):
            entity_id = entity.get("id") or entity.get("key") or str(id(entity))
            reference_id = entity.get(self.reference_field)
        else:
            entity_id = getattr(entity, "id", None) or str(id(entity))
            reference_id = getattr(entity, self.reference_field, None)

        entity_type = context.get("entity_type", self.scope.value)

        # Skip if no reference
        if not reference_id:
            return issues

        # Check if the reference exists in the mapping
        mapped_id = database.get_mapped_entity_id(project_key, self.mapping_type, reference_id)

        if not mapped_id:
            issue = ValidationIssue(
                id=f"referential_integrity_{self.reference_field}_{entity_id}_{int(time.time())}",
                level=self.level,
                scope=self.scope,
                phase=ValidationPhase.TRANSFORMATION,
                message=f"Referential integrity issue: referenced entity '{reference_id}' in field '{self.reference_field}' has no mapping",
                entity_id=str(entity_id),
                entity_type=entity_type,
                field_name=self.reference_field,
                details={
                    "reference_field": self.reference_field,
                    "reference_id": reference_id,
                    "mapping_type": self.mapping_type,
                },
            )
            issues.append(issue)

        return issues


def get_test_status_mappings() -> Dict[str, str]:
    """
    Get default test status mappings from Zephyr to qTest.

    Returns:
        Dictionary mapping Zephyr statuses to qTest statuses
    """
    return {
        "PASS": "PASSED",
        "FAIL": "FAILED",
        "WIP": "IN_PROGRESS",
        "BLOCKED": "BLOCKED",
        "NOT_EXECUTED": "NOT_RUN",
        "UNEXECUTED": "NOT_RUN",
    }


class CustomFieldTransformationRule(ValidationRule):
    """Rule that validates custom field transformations."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        scope: ValidationScope,
        phase: ValidationPhase,
        level: ValidationLevel = ValidationLevel.WARNING,
    ):
        """
        Initialize the custom field transformation rule.

        Args:
            id: Unique identifier for the rule
            name: Name of the rule
            description: Description of the rule
            scope: Scope where the rule applies
            phase: Phase where the rule applies
            level: Validation level for issues found by this rule
        """
        super().__init__(id, name, description, scope, phase, level)
        # Import the custom field mapper to test transformations

        self.field_mapper = get_default_field_mapper()

    def validate(self, entity: Any, context: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate custom field transformations.

        Args:
            entity: The entity to validate with custom fields
            context: Additional context for validation

        Returns:
            List of validation issues found
        """
        issues = []

        # Extract custom fields
        custom_fields = None
        entity_id = None
        entity_type = context.get("entity_type", self.scope.value)

        if isinstance(entity, dict):
            entity_id = entity.get("id") or entity.get("key") or str(id(entity))
            custom_fields = entity.get("customFields", {})
        else:
            entity_id = getattr(entity, "id", None) or str(id(entity))
            custom_fields = getattr(entity, "custom_fields", None) or getattr(
                entity, "customFields", {}
            )

        if not custom_fields:
            return issues

        # Validate each field transformation
        for field_name, field_data in custom_fields.items():
            field_type = None
            field_value = None

            # Extract field type and value
            if isinstance(field_data, dict):
                field_type = field_data.get("type")
                field_value = field_data.get("value")
            else:
                field_value = field_data

            # Skip if we can't determine type or value is None
            if field_type is None or field_value is None:
                continue

            try:
                # Test transformation
                transformed_value = self.field_mapper.transform_field_value(
                    field_name, field_type, field_value
                )

                # Check if transformation resulted in empty string when we had a value
                if field_value and transformed_value == "":
                    issue = ValidationIssue(
                        id=f"custom_field_transformation_{field_name}_{entity_id}_{int(time.time())}",
                        level=self.level,
                        scope=ValidationScope.CUSTOM_FIELD,
                        phase=self.phase,
                        message=f"Custom field '{field_name}' transformation resulted in empty value",
                        entity_id=str(entity_id),
                        entity_type=entity_type,
                        field_name=field_name,
                        details={
                            "original_value": str(field_value)[:100] + "..."
                            if len(str(field_value)) > 100
                            else str(field_value),
                            "field_type": field_type,
                        },
                    )
                    issues.append(issue)

                # Additional checks could be added here for specific field types
                # For example, check if numeric fields are properly transformed to numbers
                if field_type == "NUMERIC" and not isinstance(transformed_value, (int, float)):
                    issue = ValidationIssue(
                        id=f"custom_field_numeric_{field_name}_{entity_id}_{int(time.time())}",
                        level=self.level,
                        scope=ValidationScope.CUSTOM_FIELD,
                        phase=self.phase,
                        message=f"Custom field '{field_name}' not properly transformed to numeric value",
                        entity_id=str(entity_id),
                        entity_type=entity_type,
                        field_name=field_name,
                        details={
                            "original_value": str(field_value)[:100] + "..."
                            if len(str(field_value)) > 100
                            else str(field_value),
                            "transformed_value": transformed_value,
                            "field_type": field_type,
                        },
                    )
                    issues.append(issue)

            except Exception as e:
                # Capture transformation errors
                issue = ValidationIssue(
                    id=f"custom_field_error_{field_name}_{entity_id}_{int(time.time())}",
                    level=ValidationLevel.ERROR,
                    scope=ValidationScope.CUSTOM_FIELD,
                    phase=self.phase,
                    message=f"Error transforming custom field '{field_name}': {str(e)}",
                    entity_id=str(entity_id),
                    entity_type=entity_type,
                    field_name=field_name,
                    details={
                        "error": str(e),
                        "field_type": field_type,
                    },
                )
                issues.append(issue)

        return issues


def get_built_in_rules() -> List[ValidationRule]:
    """
    Get a list of built-in validation rules.

    Returns:
        List of validation rules
    """
    rules = []

    # Project validation rules
    rules.append(
        RequiredFieldRule(
            id="project_required_fields",
            name="Project Required Fields",
            description="Validates that required project fields are present",
            scope=ValidationScope.PROJECT,
            phase=ValidationPhase.EXTRACTION,
            required_fields=["key", "name"],
            level=ValidationLevel.ERROR,
        )
    )

    # Test case validation rules
    rules.append(
        RequiredFieldRule(
            id="test_case_required_fields",
            name="Test Case Required Fields",
            description="Validates that required test case fields are present",
            scope=ValidationScope.TEST_CASE,
            phase=ValidationPhase.EXTRACTION,
            required_fields=["key", "name"],
            level=ValidationLevel.ERROR,
        )
    )

    rules.append(
        StringLengthRule(
            id="test_case_name_length",
            name="Test Case Name Length",
            description="Validates test case name length",
            scope=ValidationScope.TEST_CASE,
            phase=ValidationPhase.TRANSFORMATION,
            field_limits={"name": {"min": 1, "max": 255}},
            level=ValidationLevel.WARNING,
        )
    )

    rules.append(
        PatternMatchRule(
            id="test_case_key_pattern",
            name="Test Case Key Pattern",
            description="Validates test case key follows the expected pattern",
            scope=ValidationScope.TEST_CASE,
            phase=ValidationPhase.EXTRACTION,
            field_patterns={"key": r"^[A-Z]+-\d+$"},
            level=ValidationLevel.WARNING,
        )
    )

    rules.append(
        TestStepValidationRule(
            id="test_case_steps_validation",
            name="Test Case Steps Validation",
            description="Validates test case steps are properly defined",
            phase=ValidationPhase.EXTRACTION,
            level=ValidationLevel.WARNING,
        )
    )

    # Test cycle validation rules
    rules.append(
        RequiredFieldRule(
            id="test_cycle_required_fields",
            name="Test Cycle Required Fields",
            description="Validates that required test cycle fields are present",
            scope=ValidationScope.TEST_CYCLE,
            phase=ValidationPhase.EXTRACTION,
            required_fields=["key", "name"],
            level=ValidationLevel.ERROR,
        )
    )

    # Test execution validation rules
    rules.append(
        RequiredFieldRule(
            id="test_execution_required_fields",
            name="Test Execution Required Fields",
            description="Validates that required test execution fields are present",
            scope=ValidationScope.TEST_EXECUTION,
            phase=ValidationPhase.EXTRACTION,
            required_fields=["id", "testCaseId"],
            level=ValidationLevel.ERROR,
        )
    )

    rules.append(
        TestStatusMappingRule(
            id="test_status_mapping",
            name="Test Status Mapping",
            description="Validates test statuses are mapped correctly",
            status_mappings=get_test_status_mappings(),
            level=ValidationLevel.WARNING,
        )
    )

    # Attachment validation rules
    rules.append(
        AttachmentRule(
            id="attachment_size_limit",
            name="Attachment Size Limit",
            description="Validates that attachments are within size limits",
            phase=ValidationPhase.EXTRACTION,
            max_size=10 * 1024 * 1024,  # 10MB
            level=ValidationLevel.WARNING,
        )
    )

    rules.append(
        AttachmentRule(
            id="attachment_extension",
            name="Attachment File Extension",
            description="Validates that attachments have allowed file extensions",
            phase=ValidationPhase.EXTRACTION,
            allowed_extensions=[
                "pdf",
                "doc",
                "docx",
                "xls",
                "xlsx",
                "ppt",
                "pptx",
                "txt",
                "csv",
                "jpg",
                "jpeg",
                "png",
                "gif",
                "bmp",
                "svg",
                "zip",
                "json",
                "xml",
            ],
            level=ValidationLevel.WARNING,
        )
    )

    # Custom field validation rules
    rules.append(
        CustomFieldRule(
            id="custom_field_type",
            name="Custom Field Type",
            description="Validates that custom fields have correct types",
            scope=ValidationScope.CUSTOM_FIELD,
            phase=ValidationPhase.TRANSFORMATION,
            field_constraints={
                "priority": {
                    "type": "string",
                    "allowed_values": ["Low", "Medium", "High", "Critical"],
                },
                "component": {"type": "string"},
                "version": {"type": "string"},
                "sprint": {"type": "string"},
                "story_points": {"type": "number"},
                "automated": {"type": "boolean"},
            },
            level=ValidationLevel.WARNING,
        )
    )

    # Add custom field transformation validation
    rules.append(
        CustomFieldTransformationRule(
            id="custom_field_transformation",
            name="Custom Field Transformation",
            description="Validates custom field transformations work correctly",
            scope=ValidationScope.TEST_CASE,
            phase=ValidationPhase.TRANSFORMATION,
            level=ValidationLevel.WARNING,
        )
    )

    rules.append(
        CustomFieldTransformationRule(
            id="custom_field_transformation_cycle",
            name="Test Cycle Custom Field Transformation",
            description="Validates test cycle custom field transformations work correctly",
            scope=ValidationScope.TEST_CYCLE,
            phase=ValidationPhase.TRANSFORMATION,
            level=ValidationLevel.WARNING,
        )
    )

    rules.append(
        CustomFieldTransformationRule(
            id="custom_field_transformation_execution",
            name="Test Execution Custom Field Transformation",
            description="Validates test execution custom field transformations work correctly",
            scope=ValidationScope.TEST_EXECUTION,
            phase=ValidationPhase.TRANSFORMATION,
            level=ValidationLevel.WARNING,
        )
    )

    # Referential integrity rules
    rules.append(
        ReferentialIntegrityRule(
            id="testcase_folder_reference",
            name="Test Case Folder Reference",
            description="Validates test case folder references can be mapped",
            scope=ValidationScope.TEST_CASE,
            reference_field="folderId",
            mapping_type="folder_to_module",
            level=ValidationLevel.ERROR,
        )
    )

    rules.append(
        ReferentialIntegrityRule(
            id="execution_testcase_reference",
            name="Test Execution Test Case Reference",
            description="Validates test execution test case references can be mapped",
            scope=ValidationScope.TEST_EXECUTION,
            reference_field="testCaseId",
            mapping_type="testcase_to_testcase",
            level=ValidationLevel.ERROR,
        )
    )

    rules.append(
        ReferentialIntegrityRule(
            id="execution_cycle_reference",
            name="Test Execution Cycle Reference",
            description="Validates test execution cycle references can be mapped",
            scope=ValidationScope.TEST_EXECUTION,
            reference_field="cycleId",
            mapping_type="cycle_to_cycle",
            level=ValidationLevel.ERROR,
        )
    )

    # Data integrity rules
    rules.append(
        DataIntegrityRule(
            id="testcase_data_integrity",
            name="Test Case Data Integrity",
            description="Validates test case data is preserved during transformation",
            scope=ValidationScope.TEST_CASE,
            fields_to_compare=[
                ("name", "name"),
                ("description", "description"),
                ("priority", "priority"),
                ("status", "status"),
            ],
            level=ValidationLevel.ERROR,
        )
    )

    rules.append(
        DataIntegrityRule(
            id="testcycle_data_integrity",
            name="Test Cycle Data Integrity",
            description="Validates test cycle data is preserved during transformation",
            scope=ValidationScope.TEST_CYCLE,
            fields_to_compare=[
                ("name", "name"),
                ("description", "description"),
            ],
            level=ValidationLevel.ERROR,
        )
    )

    # Add data comparison rules
    rules.extend(get_data_comparison_rules())

    return rules
