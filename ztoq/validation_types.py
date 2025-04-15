"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Validation types and enums for ZTOQ validations.

This module provides common type definitions used across validation modules.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ValidationLevel(Enum):
    """Validation levels for different severity of issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationScope(Enum):
    """Scopes where validation can be applied."""

    PROJECT = "project"
    FOLDER = "folder"
    TEST_CASE = "test_case"
    TEST_CASE_STEP = "test_case_step"
    TEST_CYCLE = "test_cycle"
    TEST_EXECUTION = "test_execution"
    ATTACHMENT = "attachment"
    CUSTOM_FIELD = "custom_field"
    RELATIONSHIP = "relationship"
    SYSTEM = "system"
    DATABASE = "database"


class ValidationPhase(Enum):
    """Migration phases where validation can occur."""

    PRE_MIGRATION = "pre_migration"
    EXTRACTION = "extraction"
    TRANSFORMATION = "transformation"
    LOADING = "loading"
    POST_MIGRATION = "post_migration"


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""

    id: str  # Unique identifier for the issue
    level: ValidationLevel
    scope: ValidationScope
    phase: ValidationPhase
    message: str
    entity_id: str | None = None
    entity_type: str | None = None
    field_name: str | None = None
    details: dict[str, Any] | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert the issue to a dictionary."""
        return {
            "id": self.id,
            "level": self.level.value,
            "scope": self.scope.value,
            "phase": self.phase.value,
            "message": self.message,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "field_name": self.field_name,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValidationIssue":
        """Create a ValidationIssue from a dictionary."""
        return cls(
            id=data["id"],
            level=ValidationLevel(data["level"]),
            scope=ValidationScope(data["scope"]),
            phase=ValidationPhase(data["phase"]),
            message=data["message"],
            entity_id=data.get("entity_id"),
            entity_type=data.get("entity_type"),
            field_name=data.get("field_name"),
            details=data.get("details"),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if "timestamp" in data
            else datetime.now(),
        )


class ValidationRule:
    """Definition of a validation rule to be applied."""

    def __init__(
        self,
        id: str,  # Unique identifier for the rule
        name: str,
        description: str,
        scope: ValidationScope,
        phase: ValidationPhase,
        level: ValidationLevel = ValidationLevel.ERROR,
        enabled: bool = True,
    ):
        """
        Initialize the validation rule.

        Args:
            id: Unique identifier for the rule
            name: Name of the rule
            description: Description of the rule
            scope: The scope where the rule applies
            phase: The phase where the rule applies
            level: Validation level for issues
            enabled: Whether the rule is enabled

        """
        self.id = id
        self.name = name
        self.description = description
        self.scope = scope
        self.phase = phase
        self.level = level
        self.enabled = enabled

    def validate(self, entity: Any, context: dict[str, Any]) -> list[ValidationIssue]:
        """
        Execute the validation logic on an entity.

        This is a base implementation that should be overridden by subclasses.

        Args:
            entity: The entity to validate
            context: Additional context for validation

        Returns:
            List of validation issues found

        """
        return []
