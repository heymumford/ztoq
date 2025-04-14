"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Validation and error handling framework for ZTOQ migrations.

This module provides comprehensive validation and error handling capabilities
for the migration process, ensuring data quality, integrity, and detailed
error reporting.
"""

import collections
import enum
import functools
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from ztoq.validation_rules import get_built_in_rules
import requests.exceptions
import httpx

logger = logging.getLogger("ztoq.validation")


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
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    field_name: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
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
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationIssue":
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
                timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            )


@dataclass


class ValidationRule:
    """Definition of a validation rule to be applied."""

    id: str  # Unique identifier for the rule
    name: str
    description: str
    scope: ValidationScope
    phase: ValidationPhase
    level: ValidationLevel = ValidationLevel.ERROR
    enabled: bool = True

    def validate(self, entity: Any, context: Dict[str, Any]) -> List[ValidationIssue]:
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


class ValidationRuleRegistry:
    """Registry for all validation rules."""

    def __init__(self):
        """Initialize the registry."""
        self.rules: Dict[str, ValidationRule] = {}
        self.rules_by_scope: Dict[ValidationScope, List[ValidationRule]] = {
            scope: [] for scope in ValidationScope
        }
        self.rules_by_phase: Dict[ValidationPhase, List[ValidationRule]] = {
            phase: [] for phase in ValidationPhase
        }

    def register_rule(self, rule: ValidationRule) -> None:
        """
        Register a validation rule.

        Args:
            rule: The validation rule to register
        """
        if rule.id in self.rules:
            logger.warning(f"Rule with ID {rule.id} already exists, overwriting")

        self.rules[rule.id] = rule
        self.rules_by_scope[rule.scope].append(rule)
        self.rules_by_phase[rule.phase].append(rule)

        logger.debug(f"Registered validation rule: {rule.id} ({rule.name})")

    def get_rules_for_scope(self, scope: ValidationScope) -> List[ValidationRule]:
        """
        Get all rules for a specific scope.

        Args:
            scope: The scope to filter by

        Returns:
            List of validation rules for the scope
        """
        return self.rules_by_scope.get(scope, [])

    def get_rules_for_phase(self, phase: ValidationPhase) -> List[ValidationRule]:
        """
        Get all rules for a specific phase.

        Args:
            phase: The phase to filter by

        Returns:
            List of validation rules for the phase
        """
        return self.rules_by_phase.get(phase, [])

    def get_active_rules(
        self, scope: Optional[ValidationScope] = None, phase: Optional[ValidationPhase] = None
    ) -> List[ValidationRule]:
        """
        Get all active rules, optionally filtered by scope and phase.

        Args:
            scope: Optional scope to filter by
            phase: Optional phase to filter by

        Returns:
            List of active validation rules
        """
        rules = [rule for rule in self.rules.values() if rule.enabled]

        if scope:
            rules = [rule for rule in rules if rule.scope == scope]

        if phase:
            rules = [rule for rule in rules if rule.phase == phase]

        return rules


class ValidationManager:
    """
    Manager for tracking and reporting validation issues during migration.

    This class acts as a central repository for validation issues that
    occur during the migration process. It provides methods for capturing,
        aggregating, and reporting on validation results.
    """

    def __init__(self, database: Any, project_key: str):
        """
        Initialize the validation manager.

        Args:
            database: Database manager instance
            project_key: The Zephyr project key
        """
        self.database = database
        self.project_key = project_key
        self.registry = ValidationRuleRegistry()
        self.issues: List[ValidationIssue] = []
        self.issue_counts: Dict[ValidationLevel, int] = {
            level: 0 for level in ValidationLevel
        }

        # Register built-in validation rules
        self._register_built_in_rules()

        # Save rules to the database
        self._save_rules_to_database()

    def _save_rules_to_database(self) -> None:
        """Save registered validation rules to the database."""
        try:
            for rule in self.registry.rules.values():
                self.database.save_validation_rule(rule)
        except Exception as e:
            logger.error(f"Failed to save validation rules to database: {str(e)}")

    def _register_built_in_rules(self) -> None:
        """Register the built-in validation rules."""


        for rule in get_built_in_rules():
            self.registry.register_rule(rule)

    def add_issue(self, issue: ValidationIssue) -> None:
        """
        Add a validation issue.

        Args:
            issue: The validation issue to add
        """
        self.issues.append(issue)
        self.issue_counts[issue.level] += 1

        # Log the issue
        log_level = logging.INFO
        if issue.level == ValidationLevel.WARNING:
            log_level = logging.WARNING
        elif issue.level == ValidationLevel.ERROR:
            log_level = logging.ERROR
        elif issue.level == ValidationLevel.CRITICAL:
            log_level = logging.CRITICAL

        logger.log(
            log_level,
                f"Validation issue: {issue.level.value.upper()} - {issue.message} "
            f"[{issue.scope.value}/{issue.entity_type or 'N/A'}/{issue.entity_id or 'N/A'}]",
            )

        # Save to database
        self._save_issue(issue)

    def _save_issue(self, issue: ValidationIssue) -> None:
        """
        Save a validation issue to the database.

        Args:
            issue: The validation issue to save
        """
        try:
            self.database.save_validation_issue(
                issue=issue,
                    project_key=self.project_key,
                )
        except Exception as e:
            logger.error(f"Failed to save validation issue to database: {str(e)}")

    def get_issues(
        self,
            level: Optional[ValidationLevel] = None,
            scope: Optional[ValidationScope] = None,
            phase: Optional[ValidationPhase] = None,
            entity_type: Optional[str] = None,
            entity_id: Optional[str] = None,
        ) -> List[ValidationIssue]:
        """
        Get validation issues filtered by various criteria.

        Args:
            level: Optional level to filter by
            scope: Optional scope to filter by
            phase: Optional phase to filter by
            entity_type: Optional entity type to filter by
            entity_id: Optional entity ID to filter by

        Returns:
            List of validation issues matching the criteria
        """
        issues = self.issues

        if level:
            issues = [issue for issue in issues if issue.level == level]

        if scope:
            issues = [issue for issue in issues if issue.scope == scope]

        if phase:
            issues = [issue for issue in issues if issue.phase == phase]

        if entity_type:
            issues = [issue for issue in issues if issue.entity_type == entity_type]

        if entity_id:
            issues = [issue for issue in issues if issue.entity_id == entity_id]

        return issues

    def get_issue_count(self, level: Optional[ValidationLevel] = None) -> int:
        """
        Get the count of validation issues, optionally filtered by level.

        Args:
            level: Optional level to filter by

        Returns:
            Count of validation issues
        """
        if level:
            return self.issue_counts[level]
        return sum(self.issue_counts.values())

    def has_critical_issues(self) -> bool:
        """
        Check if there are any critical validation issues.

        Returns:
            True if there are critical issues, False otherwise
        """
        return self.issue_counts[ValidationLevel.CRITICAL] > 0

    def has_error_issues(self) -> bool:
        """
        Check if there are any error validation issues.

        Returns:
            True if there are error issues, False otherwise
        """
        return self.issue_counts[ValidationLevel.ERROR] > 0

    def execute_validation(
        self,
            entity: Any,
            scope: ValidationScope,
            phase: ValidationPhase,
            context: Optional[Dict[str, Any]] = None,
        ) -> List[ValidationIssue]:
        """
        Execute validation rules for a given entity.

        Args:
            entity: The entity to validate
            scope: The scope of validation
            phase: The phase of validation
            context: Additional context for validation

        Returns:
            List of validation issues found
        """
        if context is None:
            context = {}

        # Get rules for the scope and phase
        rules = [
            rule
            for rule in self.registry.get_active_rules()
            if rule.scope == scope and rule.phase == phase
        ]

        if not rules:
            logger.debug(f"No validation rules found for {scope.value}/{phase.value}")
            return []

        # Execute each rule and collect issues
        all_issues = []
        for rule in rules:
            try:
                issues = rule.validate(entity, context)
                for issue in issues:
                    self.add_issue(issue)
                all_issues.extend(issues)
            except Exception as e:
                logger.error(f"Error executing validation rule {rule.id}: {str(e)}")
                # Create a system-level validation issue for the rule failure
                error_issue = ValidationIssue(
                    id=f"rule_execution_error_{int(time.time())}",
                        level=ValidationLevel.ERROR,
                        scope=ValidationScope.SYSTEM,
                        phase=phase,
                        message=f"Validation rule execution failed: {rule.id}",
                        details={"rule_id": rule.id, "error": str(e)},
                    )
                self.add_issue(error_issue)
                all_issues.append(error_issue)

        return all_issues

    def execute_all_validations(
        self, phase: ValidationPhase, entities_by_scope: Dict[ValidationScope, List[Any]]
    ) -> Dict[ValidationScope, List[ValidationIssue]]:
        """
        Execute all validation rules for the given phase.

        Args:
            phase: The phase of validation
            entities_by_scope: Dictionary mapping scopes to lists of entities

        Returns:
            Dictionary mapping scopes to lists of validation issues
        """
        results = {scope: [] for scope in ValidationScope}

        for scope, entities in entities_by_scope.items():
            scope_results = []
            for entity in entities:
                context = {"phase": phase.value, "scope": scope.value}
                issues = self.execute_validation(entity, scope, phase, context)
                scope_results.extend(issues)
            results[scope] = scope_results

        return results

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all validation issues.

        Returns:
            Dictionary containing validation summary
        """
        return {
            "project_key": self.project_key,
                "total_issues": len(self.issues),
                "counts_by_level": {level.value: count for level, count in self.issue_counts.items()},
                "counts_by_scope": self._count_by_field("scope"),
                "counts_by_phase": self._count_by_field("phase"),
                "critical_issue_count": self.issue_counts[ValidationLevel.CRITICAL],
                "error_issue_count": self.issue_counts[ValidationLevel.ERROR],
                "warning_issue_count": self.issue_counts[ValidationLevel.WARNING],
                "info_issue_count": self.issue_counts[ValidationLevel.INFO],
                "has_critical_issues": self.has_critical_issues(),
                "has_error_issues": self.has_error_issues(),
            }

    def _count_by_field(self, field: str) -> Dict[str, int]:
        """
        Count issues by a specific field.

        Args:
            field: The field to count by

        Returns:
            Dictionary mapping field values to counts
        """
        counts = collections.Counter()
        for issue in self.issues:
            value = getattr(issue, field).value
            counts[value] += 1
        return dict(counts)

    def get_report(
        self, include_details: bool = True, max_issues_per_category: int = 100
    ) -> Dict[str, Any]:
        """
        Generate a detailed validation report.

        Args:
            include_details: Whether to include issue details in the report
            max_issues_per_category: Maximum number of issues to include per category

        Returns:
            Dictionary containing the validation report
        """
        summary = self.get_summary()

        if not include_details:
            return summary

        # Group issues by level
        issues_by_level = {}
        for level in ValidationLevel:
            level_issues = self.get_issues(level=level)
            if level_issues:
                # Limit the number of issues per level
                truncated = len(level_issues) > max_issues_per_category
                issues_by_level[level.value] = {
                    "count": len(level_issues),
                        "truncated": truncated,
                        "issues": [issue.to_dict() for issue in level_issues[:max_issues_per_category]],
                    }

        # Add details to report
        report = {
            **summary,
                "issues_by_level": issues_by_level,
                "generated_at": datetime.now().isoformat(),
            }

        return report

    def save_report(self, filename: str, include_details: bool = True) -> None:
        """
        Save the validation report to a file.

        Args:
            filename: Path to save the report
            include_details: Whether to include issue details in the report
        """
        report = self.get_report(include_details=include_details)

        # Save to database
        try:
            self.database.save_validation_report(self.project_key, report)
        except Exception as e:
            logger.error(f"Failed to save validation report to database: {str(e)}")

        # Also save to file if filename is provided
        if filename:
            with open(filename, "w") as f:
                json.dump(report, f, indent=2)

            logger.info(f"Validation report saved to {filename}")

        return report


class MigrationValidator:
    """
    High-level validator for migration processes.

    This class orchestrates validation across different migration phases,
        coordinating with the ValidationManager to track and report issues.
    """

    def __init__(self, validation_manager: ValidationManager):
        """
        Initialize the migration validator.

        Args:
            validation_manager: The validation manager instance
        """
        self.validation_manager = validation_manager
        self.project_key = validation_manager.project_key
        self.database = validation_manager.database

    def validate_pre_migration(self, zephyr_client: Any, qtest_client: Any) -> bool:
        """
        Validate pre-migration requirements and configuration.

        Args:
            zephyr_client: The Zephyr client instance
            qtest_client: The qTest client instance

        Returns:
            True if validation passes, False otherwise
        """
        logger.info("Validating pre-migration requirements and configuration")

        # Context for validation
        context = {
            "zephyr_client": zephyr_client,
                "qtest_client": qtest_client,
                "project_key": self.project_key,
            }

        # Validate project connectivity
        self._validate_zephyr_connectivity(zephyr_client, context)
        self._validate_qtest_connectivity(qtest_client, context)

        # Validate project existence
        self._validate_zephyr_project(zephyr_client, context)
        self._validate_qtest_project(qtest_client, context)

        # Check for critical issues
        if self.validation_manager.has_critical_issues():
            logger.critical("Pre-migration validation found critical issues, migration cannot proceed")
            return False

        # Warn if there are error issues
        if self.validation_manager.has_error_issues():
            logger.error(
                "Pre-migration validation found error issues, migration may encounter problems"
            )

        logger.info("Pre-migration validation completed")
        return True

    def _validate_zephyr_connectivity(self, zephyr_client: Any, context: Dict[str, Any]) -> None:
        """
        Validate connectivity to Zephyr Scale API.

        Args:
            zephyr_client: The Zephyr client instance
            context: Additional context for validation
        """
        try:
            # Try to make a simple API call
            zephyr_client.check_connection()
        except Exception as e:
            issue = ValidationIssue(
                id=f"zephyr_connectivity_{int(time.time())}",
                    level=ValidationLevel.CRITICAL,
                    scope=ValidationScope.SYSTEM,
                    phase=ValidationPhase.PRE_MIGRATION,
                    message="Cannot connect to Zephyr Scale API",
                    details={"error": str(e)},
                )
            self.validation_manager.add_issue(issue)

    def _validate_qtest_connectivity(self, qtest_client: Any, context: Dict[str, Any]) -> None:
        """
        Validate connectivity to qTest API.

        Args:
            qtest_client: The qTest client instance
            context: Additional context for validation
        """
        try:
            # Try to make a simple API call
            qtest_client.check_connection()
        except Exception as e:
            issue = ValidationIssue(
                id=f"qtest_connectivity_{int(time.time())}",
                    level=ValidationLevel.CRITICAL,
                    scope=ValidationScope.SYSTEM,
                    phase=ValidationPhase.PRE_MIGRATION,
                    message="Cannot connect to qTest API",
                    details={"error": str(e)},
                )
            self.validation_manager.add_issue(issue)

    def _validate_zephyr_project(self, zephyr_client: Any, context: Dict[str, Any]) -> None:
        """
        Validate that the Zephyr project exists.

        Args:
            zephyr_client: The Zephyr client instance
            context: Additional context for validation
        """
        try:
            project = zephyr_client.get_project(self.project_key)
            if not project:
                issue = ValidationIssue(
                    id=f"zephyr_project_not_found_{int(time.time())}",
                        level=ValidationLevel.CRITICAL,
                        scope=ValidationScope.PROJECT,
                        phase=ValidationPhase.PRE_MIGRATION,
                        message=f"Zephyr project '{self.project_key}' not found",
                    )
                self.validation_manager.add_issue(issue)
        except Exception as e:
            issue = ValidationIssue(
                id=f"zephyr_project_error_{int(time.time())}",
                    level=ValidationLevel.CRITICAL,
                    scope=ValidationScope.PROJECT,
                    phase=ValidationPhase.PRE_MIGRATION,
                    message=f"Error checking Zephyr project '{self.project_key}'",
                    details={"error": str(e)},
                )
            self.validation_manager.add_issue(issue)

    def _validate_qtest_project(self, qtest_client: Any, context: Dict[str, Any]) -> None:
        """
        Validate that the qTest project exists.

        Args:
            qtest_client: The qTest client instance
            context: Additional context for validation
        """
        try:
            project_id = qtest_client.config.project_id
            project = qtest_client.get_project(project_id)
            if not project:
                issue = ValidationIssue(
                    id=f"qtest_project_not_found_{int(time.time())}",
                        level=ValidationLevel.CRITICAL,
                        scope=ValidationScope.PROJECT,
                        phase=ValidationPhase.PRE_MIGRATION,
                        message=f"qTest project with ID {project_id} not found",
                    )
                self.validation_manager.add_issue(issue)
        except Exception as e:
            issue = ValidationIssue(
                id=f"qtest_project_error_{int(time.time())}",
                    level=ValidationLevel.CRITICAL,
                    scope=ValidationScope.PROJECT,
                    phase=ValidationPhase.PRE_MIGRATION,
                    message=f"Error checking qTest project",
                    details={"error": str(e)},
                )
            self.validation_manager.add_issue(issue)

    def validate_extraction(self, extracted_data: Dict[str, List[Any]]) -> bool:
        """
        Validate extracted data from Zephyr.

        Args:
            extracted_data: Dictionary mapping entity types to lists of entities

        Returns:
            True if validation passes, False otherwise
        """
        logger.info("Validating extracted data")

        # Map entity types to validation scopes
        entities_by_scope = {
            ValidationScope.PROJECT: extracted_data.get("project", []),
                ValidationScope.FOLDER: extracted_data.get("folders", []),
                ValidationScope.TEST_CASE: extracted_data.get("test_cases", []),
                ValidationScope.TEST_CYCLE: extracted_data.get("test_cycles", []),
                ValidationScope.TEST_EXECUTION: extracted_data.get("test_executions", []),
                ValidationScope.ATTACHMENT: extracted_data.get("attachments", []),
            }

        # Execute validations for all entities
        self.validation_manager.execute_all_validations(
            ValidationPhase.EXTRACTION, entities_by_scope
        )

        # Check for critical issues
        if self.validation_manager.has_critical_issues():
            logger.critical("Extraction validation found critical issues")
            return False

        logger.info("Extraction validation completed")
        return True

    def validate_transformation(self, transformed_data: Dict[str, List[Any]]) -> bool:
        """
        Validate transformed data.

        Args:
            transformed_data: Dictionary mapping entity types to lists of entities

        Returns:
            True if validation passes, False otherwise
        """
        logger.info("Validating transformed data")

        # Map entity types to validation scopes
        entities_by_scope = {
            ValidationScope.TEST_CASE: transformed_data.get("test_cases", []),
                ValidationScope.TEST_CYCLE: transformed_data.get("test_cycles", []),
                ValidationScope.TEST_EXECUTION: transformed_data.get("test_executions", []),
            }

        # Execute validations for all entities
        self.validation_manager.execute_all_validations(
            ValidationPhase.TRANSFORMATION, entities_by_scope
        )

        # Check for critical issues
        if self.validation_manager.has_critical_issues():
            logger.critical("Transformation validation found critical issues")
            return False

        logger.info("Transformation validation completed")
        return True

    def validate_loading(self, loaded_data: Dict[str, List[Any]]) -> bool:
        """
        Validate loaded data in qTest.

        Args:
            loaded_data: Dictionary mapping entity types to lists of entities

        Returns:
            True if validation passes, False otherwise
        """
        logger.info("Validating loaded data")

        # Map entity types to validation scopes
        entities_by_scope = {
            ValidationScope.TEST_CASE: loaded_data.get("test_cases", []),
                ValidationScope.TEST_CYCLE: loaded_data.get("test_cycles", []),
                ValidationScope.TEST_EXECUTION: loaded_data.get("test_executions", []),
            }

        # Execute validations for all entities
        self.validation_manager.execute_all_validations(ValidationPhase.LOADING, entities_by_scope)

        # Check for critical issues
        if self.validation_manager.has_critical_issues():
            logger.critical("Loading validation found critical issues")
            return False

        logger.info("Loading validation completed")
        return True

    def validate_post_migration(self, qtest_client: Any) -> bool:
        """
        Validate the completeness and correctness of the migration.

        Args:
            qtest_client: The qTest client instance

        Returns:
            True if validation passes, False otherwise
        """
        logger.info("Performing post-migration validation")

        # Get entity counts from database
        source_counts = self._get_source_entity_counts()
        loaded_counts = self._get_loaded_entity_counts()

        # Validate entity counts
        self._validate_entity_counts(source_counts, loaded_counts)

        # Check relationship integrity
        self._validate_relationships()

        # Execute advanced data comparison validation
        # Create context for validation
        context = {
            "database": self.database,
                "project_key": self.project_key,
                "qtest_client": qtest_client,
                "phase": ValidationPhase.POST_MIGRATION.value,
            }

        # Run validation rules for POST_MIGRATION phase
        logger.info("Running data comparison validation rules")
        rules = self.validation_manager.registry.get_rules_for_phase(ValidationPhase.POST_MIGRATION)
        rules = [r for r in rules if r.enabled and r.scope == ValidationScope.SYSTEM]

        for rule in rules:
            logger.info(f"Running validation rule: {rule.name}")
            self.validation_manager.execute_validation(None, rule.scope, ValidationPhase.POST_MIGRATION, context)

        # Check for critical issues
        if self.validation_manager.has_critical_issues():
            logger.critical("Post-migration validation found critical issues")
            return False

        logger.info("Post-migration validation completed")
        return True

    def _get_source_entity_counts(self) -> Dict[str, int]:
        """
        Get counts of source entities.

        Returns:
            Dictionary mapping entity types to counts
        """
        counts = {}

        try:
            # Count folders
            counts["folders"] = self.database.count_entities(self.project_key, "folders")

            # Count test cases
            counts["test_cases"] = self.database.count_entities(self.project_key, "test_cases")

            # Count test cycles
            counts["test_cycles"] = self.database.count_entities(self.project_key, "test_cycles")

            # Count test executions
            counts["test_executions"] = self.database.count_entities(
                self.project_key, "test_executions"
            )
        except Exception as e:
            logger.error(f"Error getting source entity counts: {str(e)}")
            issue = ValidationIssue(
                id=f"source_count_error_{int(time.time())}",
                    level=ValidationLevel.ERROR,
                    scope=ValidationScope.DATABASE,
                    phase=ValidationPhase.POST_MIGRATION,
                    message="Error getting source entity counts",
                    details={"error": str(e)},
                )
            self.validation_manager.add_issue(issue)

        return counts

    def _get_loaded_entity_counts(self) -> Dict[str, int]:
        """
        Get counts of loaded entities.

        Returns:
            Dictionary mapping entity types to counts
        """
        counts = {}

        try:
            # Count modules (folders)
            counts["modules"] = self.database.count_entity_mappings(
                self.project_key, "folder_to_module"
            )

            # Count test cases
            counts["test_cases"] = self.database.count_entity_mappings(
                self.project_key, "testcase_to_testcase"
            )

            # Count test cycles
            counts["test_cycles"] = self.database.count_entity_mappings(
                self.project_key, "cycle_to_cycle"
            )

            # Count test executions
            counts["test_executions"] = self.database.count_entity_mappings(
                self.project_key, "execution_to_run"
            )
        except Exception as e:
            logger.error(f"Error getting loaded entity counts: {str(e)}")
            issue = ValidationIssue(
                id=f"loaded_count_error_{int(time.time())}",
                    level=ValidationLevel.ERROR,
                    scope=ValidationScope.DATABASE,
                    phase=ValidationPhase.POST_MIGRATION,
                    message="Error getting loaded entity counts",
                    details={"error": str(e)},
                )
            self.validation_manager.add_issue(issue)

        return counts

    def _validate_entity_counts(
        self, source_counts: Dict[str, int], loaded_counts: Dict[str, int]
    ) -> None:
        """
        Validate that entity counts match.

        Args:
            source_counts: Dictionary mapping entity types to source counts
            loaded_counts: Dictionary mapping entity types to loaded counts
        """
        # Check folders vs modules
        if "folders" in source_counts and "modules" in loaded_counts:
            source_count = source_counts["folders"]
            loaded_count = loaded_counts["modules"]

            if loaded_count < source_count:
                missing_count = source_count - loaded_count
                issue = ValidationIssue(
                    id=f"missing_modules_{int(time.time())}",
                        level=ValidationLevel.ERROR,
                        scope=ValidationScope.FOLDER,
                        phase=ValidationPhase.POST_MIGRATION,
                        message=f"{missing_count} of {source_count} folders were not migrated to modules",
                        details={"source_count": source_count, "loaded_count": loaded_count},
                    )
                self.validation_manager.add_issue(issue)

        # Check test cases
        if "test_cases" in source_counts and "test_cases" in loaded_counts:
            source_count = source_counts["test_cases"]
            loaded_count = loaded_counts["test_cases"]

            if loaded_count < source_count:
                missing_count = source_count - loaded_count
                issue = ValidationIssue(
                    id=f"missing_test_cases_{int(time.time())}",
                        level=ValidationLevel.ERROR,
                        scope=ValidationScope.TEST_CASE,
                        phase=ValidationPhase.POST_MIGRATION,
                        message=f"{missing_count} of {source_count} test cases were not migrated",
                        details={"source_count": source_count, "loaded_count": loaded_count},
                    )
                self.validation_manager.add_issue(issue)

        # Check test cycles
        if "test_cycles" in source_counts and "test_cycles" in loaded_counts:
            source_count = source_counts["test_cycles"]
            loaded_count = loaded_counts["test_cycles"]

            if loaded_count < source_count:
                missing_count = source_count - loaded_count
                issue = ValidationIssue(
                    id=f"missing_test_cycles_{int(time.time())}",
                        level=ValidationLevel.ERROR,
                        scope=ValidationScope.TEST_CYCLE,
                        phase=ValidationPhase.POST_MIGRATION,
                        message=f"{missing_count} of {source_count} test cycles were not migrated",
                        details={"source_count": source_count, "loaded_count": loaded_count},
                    )
                self.validation_manager.add_issue(issue)

        # Check test executions
        if "test_executions" in source_counts and "test_executions" in loaded_counts:
            source_count = source_counts["test_executions"]
            loaded_count = loaded_counts["test_executions"]

            if loaded_count < source_count:
                missing_count = source_count - loaded_count
                issue = ValidationIssue(
                    id=f"missing_test_executions_{int(time.time())}",
                        level=ValidationLevel.ERROR,
                        scope=ValidationScope.TEST_EXECUTION,
                        phase=ValidationPhase.POST_MIGRATION,
                        message=f"{missing_count} of {source_count} test executions were not migrated",
                        details={"source_count": source_count, "loaded_count": loaded_count},
                    )
                self.validation_manager.add_issue(issue)

    def _validate_relationships(self) -> None:
        """Validate relationships between entities."""
        # Check test cases have valid module (folder) references
        try:
            # Get test cases with invalid module references
            invalid_module_refs = self.database.find_invalid_references(
                self.project_key, "test_cases", "module_id", "modules", "id"
            )

            if invalid_module_refs:
                issue = ValidationIssue(
                    id=f"invalid_module_refs_{int(time.time())}",
                        level=ValidationLevel.ERROR,
                        scope=ValidationScope.RELATIONSHIP,
                        phase=ValidationPhase.POST_MIGRATION,
                        message=f"{len(invalid_module_refs)} test cases have invalid module references",
                        details={"invalid_references": invalid_module_refs[:10]},
                    )
                self.validation_manager.add_issue(issue)
        except Exception as e:
            logger.error(f"Error validating module references: {str(e)}")

        # Check test executions have valid test case references
        try:
            # Get test executions with invalid test case references
            invalid_testcase_refs = self.database.find_invalid_references(
                self.project_key, "test_runs", "test_case_id", "test_cases", "id"
            )

            if invalid_testcase_refs:
                issue = ValidationIssue(
                    id=f"invalid_testcase_refs_{int(time.time())}",
                        level=ValidationLevel.ERROR,
                        scope=ValidationScope.RELATIONSHIP,
                        phase=ValidationPhase.POST_MIGRATION,
                        message=f"{len(invalid_testcase_refs)} test runs have invalid test case references",
                        details={"invalid_references": invalid_testcase_refs[:10]},
                    )
                self.validation_manager.add_issue(issue)
        except Exception as e:
            logger.error(f"Error validating test case references: {str(e)}")

        # Check test executions have valid test cycle references
        try:
            # Get test executions with invalid test cycle references
            invalid_cycle_refs = self.database.find_invalid_references(
                self.project_key, "test_runs", "test_cycle_id", "test_cycles", "id"
            )

            if invalid_cycle_refs:
                issue = ValidationIssue(
                    id=f"invalid_cycle_refs_{int(time.time())}",
                        level=ValidationLevel.ERROR,
                        scope=ValidationScope.RELATIONSHIP,
                        phase=ValidationPhase.POST_MIGRATION,
                        message=f"{len(invalid_cycle_refs)} test runs have invalid test cycle references",
                        details={"invalid_references": invalid_cycle_refs[:10]},
                    )
                self.validation_manager.add_issue(issue)
        except Exception as e:
            logger.error(f"Error validating test cycle references: {str(e)}")

    def generate_validation_report(self, filename: str = None) -> Dict[str, Any]:
        """
        Generate a validation report and optionally save it to a file.

        Args:
            filename: Optional path to save the report

        Returns:
            Dictionary containing the validation report
        """
        return self.validation_manager.save_report(filename)

    def validate_pre_phase(self, phase: ValidationPhase) -> bool:
        """
        Validate before a specific phase.

        Args:
            phase: The phase to validate before

        Returns:
            True if validation passes, False otherwise
        """
        logger.info(f"Running pre-{phase.value} validation")

        # Simple validation that triggers rules for the phase
        context = {"phase": phase.value, "pre_phase": True}

        # Get rules for the phase
        rules = self.validation_manager.registry.get_rules_for_phase(phase)
        rules = [r for r in rules if r.enabled]

        # Run system-level validations
        for rule in rules:
            if rule.scope == ValidationScope.SYSTEM:
                self.validation_manager.execute_validation(None, rule.scope, phase, context)

        # Check for critical issues
        if self.validation_manager.has_critical_issues():
            logger.critical(f"Pre-{phase.value} validation found critical issues")
            return False

        logger.info(f"Pre-{phase.value} validation completed")
        return True

    def validate_post_phase(self, phase: ValidationPhase) -> bool:
        """
        Validate after a specific phase.

        Args:
            phase: The phase to validate after

        Returns:
            True if validation passes, False otherwise
        """
        logger.info(f"Running post-{phase.value} validation")

        # Simple validation that triggers rules for the phase
        context = {"phase": phase.value, "post_phase": True}

        # Get rules for the phase
        rules = self.validation_manager.registry.get_rules_for_phase(phase)
        rules = [r for r in rules if r.enabled]

        # Run system-level validations
        for rule in rules:
            if rule.scope == ValidationScope.SYSTEM:
                self.validation_manager.execute_validation(None, rule.scope, phase, context)

        # Check for critical issues
        if self.validation_manager.has_critical_issues():
            logger.critical(f"Post-{phase.value} validation found critical issues")
            return False

        logger.info(f"Post-{phase.value} validation completed")
        return True


class RetryPolicy:
    """
    Defines a retry policy for handling transient errors during migration.

    This class provides mechanisms for determining when and how to retry
    operations that fail with transient errors.
    """

    def __init__(
        self,
            max_retries: int = 3,
            retry_delay: float = 1.0,
            backoff_factor: float = 2.0,
            retry_codes: Optional[Set[int]] = None,
            retry_exceptions: Optional[List[type]] = None,
        ):
        """
        Initialize the retry policy.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds
            backoff_factor: Factor to increase delay with each retry
            retry_codes: Set of HTTP status codes to retry on
            retry_exceptions: List of exception types to retry on
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self.retry_codes = retry_codes or {429, 500, 502, 503, 504}
        self.retry_exceptions = retry_exceptions or []

        # Automatically include connection and timeout errors
        retry_exception_classes = [
            TimeoutError,
                ConnectionError,
                ConnectionRefusedError,
                ConnectionResetError,
            ]

        # Add requests exceptions if available
        try:


            retry_exception_classes.extend(
                [
                    requests.exceptions.Timeout,
                        requests.exceptions.ConnectionError,
                        requests.exceptions.HTTPError,
                        requests.exceptions.ChunkedEncodingError,
                        requests.exceptions.TooManyRedirects,
                    ]
            )
        except ImportError:
            pass

        # Add httpx exceptions if available
        try:


            retry_exception_classes.extend(
                [
                    httpx.TimeoutException,
                        httpx.ConnectError,
                        httpx.ReadError,
                        httpx.WriteError,
                        httpx.PoolTimeout,
                        httpx.NetworkError,
                        httpx.ProtocolError,
                    ]
            )
        except ImportError:
            pass

        # Add user-specified exceptions
        for exc in self.retry_exceptions:
            if exc not in retry_exception_classes:
                retry_exception_classes.append(exc)

        self.retry_exceptions = retry_exception_classes

    def should_retry(self, attempt: int, exception: Exception = None, status_code: int = None) -> bool:
        """
        Determine if an operation should be retried.

        Args:
            attempt: Current attempt number (0-based)
            exception: The exception that was raised, if any
            status_code: HTTP status code, if applicable

        Returns:
            True if the operation should be retried, False otherwise
        """
        # Check if we've exceeded the maximum retries
        if attempt >= self.max_retries:
            return False

        # Check if the status code is in our retry list
        if status_code is not None and status_code in self.retry_codes:
            return True

        # Check if the exception is one we should retry
        if exception is not None:
            for exc_type in self.retry_exceptions:
                if isinstance(exception, exc_type):
                    return True

        return False

    def get_delay(self, attempt: int) -> float:
        """
        Calculate the delay before the next retry.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Delay in seconds before the next retry
        """
        return self.retry_delay * (self.backoff_factor ** attempt)


class MigrationRetryHandler:
    """
    Handles retries for operations that may fail with transient errors.

    This class provides decorators and context managers for retrying
    operations according to a specified retry policy.
    """

    def __init__(self, retry_policy: RetryPolicy = None):
        """
        Initialize the retry handler.

        Args:
            retry_policy: The retry policy to use
        """
        self.retry_policy = retry_policy or RetryPolicy()
        self.logger = logging.getLogger("ztoq.migration.retry")

    def with_retry(self, retry_on_exceptions=None, phase=None, scope=None):
        """
        Decorator factory to retry a function according to the retry policy.

        Args:
            retry_on_exceptions: List of exception types to retry on (in addition to defaults)
            phase: Optional phase information for logging
            scope: Optional scope information for logging

        Returns:
            Decorator function that adds retry logic
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                attempt = 0

                # Add specified exceptions to retry policy
                if retry_on_exceptions:
                    for exc in retry_on_exceptions:
                        if exc not in self.retry_policy.retry_exceptions:
                            self.retry_policy.retry_exceptions.append(exc)

                while True:
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        # Try to extract status code if it's an HTTP error
                        status_code = None
                        try:
                            status_code = getattr(e, "status_code", None)
                            if status_code is None:
                                # Check if it's a requests.exceptions.HTTPError
                                if hasattr(e, "response") and hasattr(e.response, "status_code"):
                                    status_code = e.response.status_code
                        except:
                            pass

                        # Check if we should retry
                        if self.retry_policy.should_retry(attempt, e, status_code):
                            delay = self.retry_policy.get_delay(attempt)

                            # Enhanced logging with phase/scope info if provided
                            log_context = ""
                            if phase and scope:
                                log_context = f" [{phase}/{scope}]"
                            elif phase:
                                log_context = f" [{phase}]"
                            elif scope:
                                log_context = f" [{scope}]"

                            self.logger.warning(
                                f"Retrying {func.__name__}{log_context} after error: {str(e)}. "
                                f"Attempt {attempt + 1}/{self.retry_policy.max_retries}. "
                                f"Waiting {delay:.2f}s"
                            )
                            time.sleep(delay)
                            attempt += 1
                        else:
                            self.logger.error(
                                f"Failed to execute {func.__name__} after "
                                f"{attempt + 1} attempts: {str(e)}"
                            )
                            raise

            return wrapper

        return decorator
