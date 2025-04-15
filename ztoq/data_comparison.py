"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Data comparison module for validating migration completeness and correctness.

This module provides functionality for comparing Zephyr and qTest data to ensure
that the migration was successful and data integrity was maintained.
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from ztoq.validation import (
    ValidationIssue,
    ValidationLevel,
    ValidationPhase,
    ValidationRule,
    ValidationScope,
)

logger = logging.getLogger("ztoq.data_comparison")


class DataComparisonValidator:
    """Validates migration by comparing source and target data for consistency."""

    def __init__(self, database_manager, project_key: str):
        """
        Initialize the data comparison validator.

        Args:
            database_manager: The database manager instance
            project_key: The Zephyr project key
        """
        self.db = database_manager
        self.project_key = project_key

    def validate_entity_counts(self) -> List[ValidationIssue]:
        """
        Compare entity counts between Zephyr and qTest.

        Returns:
            List of validation issues found
        """
        issues = []

        # Get counts from both systems
        zephyr_counts = self._get_zephyr_entity_counts()
        qtest_counts = self._get_qtest_entity_counts()

        # Compare counts and generate issues for mismatches
        for entity_type, zephyr_count in zephyr_counts.items():
            qtest_type = self._map_entity_type(entity_type)
            qtest_count = qtest_counts.get(qtest_type, 0)

            if zephyr_count > qtest_count:
                diff = zephyr_count - qtest_count
                missing_percentage = (diff / zephyr_count) * 100 if zephyr_count > 0 else 0

                # Determine validation level based on missing percentage
                level = ValidationLevel.INFO
                if missing_percentage > 1 and missing_percentage <= 5:
                    level = ValidationLevel.WARNING
                elif missing_percentage > 5 and missing_percentage <= 20:
                    level = ValidationLevel.ERROR
                elif missing_percentage > 20:
                    level = ValidationLevel.CRITICAL

                issue = ValidationIssue(
                    id=f"count_mismatch_{entity_type}_{int(time.time())}",
                    level=level,
                    scope=self._get_scope_for_entity(entity_type),
                    phase=ValidationPhase.POST_MIGRATION,
                    message=f"Found {diff} missing {entity_type} entities in qTest ({missing_percentage:.2f}%)",
                    entity_type=entity_type,
                    details={
                        "zephyr_count": zephyr_count,
                        "qtest_count": qtest_count,
                        "missing": diff,
                        "missing_percentage": missing_percentage,
                    },
                )
                issues.append(issue)

        return issues

    def validate_critical_entities(self) -> List[ValidationIssue]:
        """
        Verify all critical entities were migrated correctly.

        Returns:
            List of validation issues found
        """
        issues = []

        # Get high-priority test cases
        try:
            high_priority_cases = self.db.get_high_priority_test_cases(self.project_key)

            for case in high_priority_cases:
                # Check if the test case was migrated
                if not self.db.is_entity_migrated(self.project_key, "test_cases", case["id"]):
                    issue = ValidationIssue(
                        id=f"critical_testcase_missing_{case['id']}_{int(time.time())}",
                        level=ValidationLevel.CRITICAL,
                        scope=ValidationScope.TEST_CASE,
                        phase=ValidationPhase.POST_MIGRATION,
                        message=f"High-priority test case '{case['name']}' was not migrated",
                        entity_id=case["id"],
                        entity_type="test_case",
                        details={"name": case["name"], "priority": "High"},
                    )
                    issues.append(issue)
        except Exception as e:
            logger.error(f"Error validating critical test cases: {str(e)}")
            issue = ValidationIssue(
                id=f"critical_testcase_validation_error_{int(time.time())}",
                level=ValidationLevel.ERROR,
                scope=ValidationScope.SYSTEM,
                phase=ValidationPhase.POST_MIGRATION,
                message=f"Error validating critical test cases: {str(e)}",
                details={"error": str(e)},
            )
            issues.append(issue)

        return issues

    def validate_relationship_integrity(self) -> List[ValidationIssue]:
        """
        Verify relationships between entities are preserved.

        Returns:
            List of validation issues found
        """
        issues = []

        # Validate test case to folder relationships
        issues.extend(self._validate_testcase_folder_relationships())

        # Validate test execution to test case relationships
        issues.extend(self._validate_execution_testcase_relationships())

        # Validate test execution to test cycle relationships
        issues.extend(self._validate_execution_cycle_relationships())

        return issues

    def _validate_testcase_folder_relationships(self) -> List[ValidationIssue]:
        """
        Validate test case to folder relationships.

        Returns:
            List of validation issues found
        """
        issues = []

        try:
            # Get test cases with their folder information
            test_cases = self.db.get_test_cases_with_folders(self.project_key)

            for test_case in test_cases:
                zephyr_folder_id = test_case.get("folder_id")
                if not zephyr_folder_id:
                    continue

                # Get the mapped qTest module ID
                qtest_module_id = self.db.get_mapped_entity_id(
                    self.project_key, "folder_to_module", zephyr_folder_id
                )

                if not qtest_module_id:
                    continue

                # Get the mapped qTest test case ID
                qtest_testcase_id = self.db.get_mapped_entity_id(
                    self.project_key, "testcase_to_testcase", test_case["id"]
                )

                if not qtest_testcase_id:
                    continue

                # Check if the qTest test case is in the correct module
                qtest_module_for_testcase = self.db.get_qtest_module_for_testcase(qtest_testcase_id)

                if qtest_module_for_testcase != qtest_module_id:
                    issue = ValidationIssue(
                        id=f"testcase_module_mismatch_{test_case['id']}_{int(time.time())}",
                        level=ValidationLevel.ERROR,
                        scope=ValidationScope.RELATIONSHIP,
                        phase=ValidationPhase.POST_MIGRATION,
                        message=f"Test case '{test_case['name']}' is not in the correct qTest module",
                        entity_id=test_case["id"],
                        entity_type="test_case",
                        details={
                            "test_case_name": test_case["name"],
                            "zephyr_folder_id": zephyr_folder_id,
                            "expected_qtest_module": qtest_module_id,
                            "actual_qtest_module": qtest_module_for_testcase,
                        },
                    )
                    issues.append(issue)
        except Exception as e:
            logger.error(f"Error validating test case folder relationships: {str(e)}")
            issue = ValidationIssue(
                id=f"testcase_folder_validation_error_{int(time.time())}",
                level=ValidationLevel.ERROR,
                scope=ValidationScope.RELATIONSHIP,
                phase=ValidationPhase.POST_MIGRATION,
                message=f"Error validating test case folder relationships: {str(e)}",
                details={"error": str(e)},
            )
            issues.append(issue)

        return issues

    def _validate_execution_testcase_relationships(self) -> List[ValidationIssue]:
        """
        Validate test execution to test case relationships.

        Returns:
            List of validation issues found
        """
        issues = []

        try:
            # Get test executions with their test case information
            executions = self.db.get_test_executions_with_testcases(self.project_key)

            for execution in executions:
                zephyr_testcase_id = execution.get("test_case_id")
                if not zephyr_testcase_id:
                    continue

                # Get the mapped qTest test case ID
                qtest_testcase_id = self.db.get_mapped_entity_id(
                    self.project_key, "testcase_to_testcase", zephyr_testcase_id
                )

                if not qtest_testcase_id:
                    continue

                # Get the mapped qTest test run ID
                qtest_run_id = self.db.get_mapped_entity_id(
                    self.project_key, "execution_to_run", execution["id"]
                )

                if not qtest_run_id:
                    continue

                # Check if the qTest test run is linked to the correct test case
                qtest_testcase_for_run = self.db.get_qtest_testcase_for_run(qtest_run_id)

                if qtest_testcase_for_run != qtest_testcase_id:
                    issue = ValidationIssue(
                        id=f"execution_testcase_mismatch_{execution['id']}_{int(time.time())}",
                        level=ValidationLevel.ERROR,
                        scope=ValidationScope.RELATIONSHIP,
                        phase=ValidationPhase.POST_MIGRATION,
                        message="Test execution is not linked to the correct qTest test case",
                        entity_id=execution["id"],
                        entity_type="test_execution",
                        details={
                            "zephyr_test_case_id": zephyr_testcase_id,
                            "expected_qtest_testcase": qtest_testcase_id,
                            "actual_qtest_testcase": qtest_testcase_for_run,
                        },
                    )
                    issues.append(issue)
        except Exception as e:
            logger.error(f"Error validating test execution test case relationships: {str(e)}")
            issue = ValidationIssue(
                id=f"execution_testcase_validation_error_{int(time.time())}",
                level=ValidationLevel.ERROR,
                scope=ValidationScope.RELATIONSHIP,
                phase=ValidationPhase.POST_MIGRATION,
                message=f"Error validating test execution test case relationships: {str(e)}",
                details={"error": str(e)},
            )
            issues.append(issue)

        return issues

    def _validate_execution_cycle_relationships(self) -> List[ValidationIssue]:
        """
        Validate test execution to test cycle relationships.

        Returns:
            List of validation issues found
        """
        issues = []

        try:
            # Get test executions with their cycle information
            executions = self.db.get_test_executions_with_cycles(self.project_key)

            for execution in executions:
                zephyr_cycle_id = execution.get("cycle_id")
                if not zephyr_cycle_id:
                    continue

                # Get the mapped qTest test cycle ID
                qtest_cycle_id = self.db.get_mapped_entity_id(
                    self.project_key, "cycle_to_cycle", zephyr_cycle_id
                )

                if not qtest_cycle_id:
                    continue

                # Get the mapped qTest test run ID
                qtest_run_id = self.db.get_mapped_entity_id(
                    self.project_key, "execution_to_run", execution["id"]
                )

                if not qtest_run_id:
                    continue

                # Check if the qTest test run is in the correct test cycle
                qtest_cycle_for_run = self.db.get_qtest_cycle_for_run(qtest_run_id)

                if qtest_cycle_for_run != qtest_cycle_id:
                    issue = ValidationIssue(
                        id=f"execution_cycle_mismatch_{execution['id']}_{int(time.time())}",
                        level=ValidationLevel.ERROR,
                        scope=ValidationScope.RELATIONSHIP,
                        phase=ValidationPhase.POST_MIGRATION,
                        message="Test execution is not linked to the correct qTest test cycle",
                        entity_id=execution["id"],
                        entity_type="test_execution",
                        details={
                            "zephyr_cycle_id": zephyr_cycle_id,
                            "expected_qtest_cycle": qtest_cycle_id,
                            "actual_qtest_cycle": qtest_cycle_for_run,
                        },
                    )
                    issues.append(issue)
        except Exception as e:
            logger.error(f"Error validating test execution cycle relationships: {str(e)}")
            issue = ValidationIssue(
                id=f"execution_cycle_validation_error_{int(time.time())}",
                level=ValidationLevel.ERROR,
                scope=ValidationScope.RELATIONSHIP,
                phase=ValidationPhase.POST_MIGRATION,
                message=f"Error validating test execution cycle relationships: {str(e)}",
                details={"error": str(e)},
            )
            issues.append(issue)

        return issues

    def validate_custom_field_migration(self) -> List[ValidationIssue]:
        """
        Verify custom fields were migrated with correct types and values.

        Returns:
            List of validation issues found
        """
        issues = []

        try:
            # Get test cases with custom fields
            test_cases = self.db.get_test_cases_with_custom_fields(self.project_key)

            for test_case in test_cases:
                zephyr_custom_fields = test_case.get("custom_fields", {})
                if not zephyr_custom_fields:
                    continue

                # Get the mapped qTest test case ID
                qtest_testcase_id = self.db.get_mapped_entity_id(
                    self.project_key, "testcase_to_testcase", test_case["id"]
                )

                if not qtest_testcase_id:
                    continue

                # Get qTest custom fields for the test case
                qtest_custom_fields = self.db.get_qtest_custom_fields(qtest_testcase_id)

                # Check each custom field
                for field_name, field_value in zephyr_custom_fields.items():
                    # Get the mapped qTest field name
                    qtest_field_name = self._map_custom_field_name(field_name)

                    # Check if the field exists in qTest
                    if qtest_field_name not in qtest_custom_fields:
                        issue = ValidationIssue(
                            id=f"custom_field_missing_{test_case['id']}_{field_name}_{int(time.time())}",
                            level=ValidationLevel.WARNING,
                            scope=ValidationScope.CUSTOM_FIELD,
                            phase=ValidationPhase.POST_MIGRATION,
                            message=f"Custom field '{field_name}' was not migrated to qTest",
                            entity_id=test_case["id"],
                            entity_type="test_case",
                            field_name=field_name,
                            details={
                                "zephyr_field_name": field_name,
                                "qtest_field_name": qtest_field_name,
                                "zephyr_value": field_value,
                            },
                        )
                        issues.append(issue)
                        continue

                    # Check if the field value matches
                    qtest_value = qtest_custom_fields[qtest_field_name]
                    normalized_zephyr_value = self._normalize_custom_field_value(field_value)
                    normalized_qtest_value = self._normalize_custom_field_value(qtest_value)

                    if normalized_zephyr_value != normalized_qtest_value:
                        issue = ValidationIssue(
                            id=f"custom_field_value_mismatch_{test_case['id']}_{field_name}_{int(time.time())}",
                            level=ValidationLevel.WARNING,
                            scope=ValidationScope.CUSTOM_FIELD,
                            phase=ValidationPhase.POST_MIGRATION,
                            message=f"Custom field '{field_name}' value does not match qTest value",
                            entity_id=test_case["id"],
                            entity_type="test_case",
                            field_name=field_name,
                            details={
                                "zephyr_field_name": field_name,
                                "qtest_field_name": qtest_field_name,
                                "zephyr_value": normalized_zephyr_value,
                                "qtest_value": normalized_qtest_value,
                            },
                        )
                        issues.append(issue)
        except Exception as e:
            logger.error(f"Error validating custom field migration: {str(e)}")
            issue = ValidationIssue(
                id=f"custom_field_validation_error_{int(time.time())}",
                level=ValidationLevel.ERROR,
                scope=ValidationScope.CUSTOM_FIELD,
                phase=ValidationPhase.POST_MIGRATION,
                message=f"Error validating custom field migration: {str(e)}",
                details={"error": str(e)},
            )
            issues.append(issue)

        return issues

    def validate_attachment_migration(self) -> List[ValidationIssue]:
        """
        Verify all attachments were migrated correctly.

        Returns:
            List of validation issues found
        """
        issues = []

        try:
            # Get entities with attachments
            entities_with_attachments = self.db.get_entities_with_attachments(self.project_key)

            for entity in entities_with_attachments:
                entity_type = entity["entity_type"]
                entity_id = entity["entity_id"]
                zephyr_attachments = entity["attachments"]

                # Get the mapped qTest entity ID
                mapping_type = self._get_mapping_type_for_entity(entity_type)
                qtest_entity_id = self.db.get_mapped_entity_id(
                    self.project_key, mapping_type, entity_id
                )

                if not qtest_entity_id:
                    continue

                # Get qTest attachments for the entity
                qtest_attachments = self.db.get_qtest_attachments(entity_type, qtest_entity_id)

                # Compare attachment counts
                if len(zephyr_attachments) > len(qtest_attachments):
                    missing_count = len(zephyr_attachments) - len(qtest_attachments)
                    issue = ValidationIssue(
                        id=f"missing_attachments_{entity_type}_{entity_id}_{int(time.time())}",
                        level=ValidationLevel.WARNING,
                        scope=ValidationScope.ATTACHMENT,
                        phase=ValidationPhase.POST_MIGRATION,
                        message=f"{missing_count} attachments were not migrated for {entity_type} {entity_id}",
                        entity_id=entity_id,
                        entity_type=entity_type,
                        details={
                            "zephyr_attachment_count": len(zephyr_attachments),
                            "qtest_attachment_count": len(qtest_attachments),
                            "missing_count": missing_count,
                        },
                    )
                    issues.append(issue)
        except Exception as e:
            logger.error(f"Error validating attachment migration: {str(e)}")
            issue = ValidationIssue(
                id=f"attachment_validation_error_{int(time.time())}",
                level=ValidationLevel.ERROR,
                scope=ValidationScope.ATTACHMENT,
                phase=ValidationPhase.POST_MIGRATION,
                message=f"Error validating attachment migration: {str(e)}",
                details={"error": str(e)},
            )
            issues.append(issue)

        return issues

    def _get_zephyr_entity_counts(self) -> Dict[str, int]:
        """
        Get counts of entities from Zephyr.

        Returns:
            Dictionary mapping entity types to counts
        """
        counts = {}

        try:
            # Count folders
            counts["folders"] = self.db.count_entities(self.project_key, "folders")

            # Count test cases
            counts["test_cases"] = self.db.count_entities(self.project_key, "test_cases")

            # Count test cycles
            counts["test_cycles"] = self.db.count_entities(self.project_key, "test_cycles")

            # Count test executions
            counts["test_executions"] = self.db.count_entities(self.project_key, "test_executions")
        except Exception as e:
            logger.error(f"Error getting Zephyr entity counts: {str(e)}")

        return counts

    def _get_qtest_entity_counts(self) -> Dict[str, int]:
        """
        Get counts of entities from qTest.

        Returns:
            Dictionary mapping entity types to counts
        """
        counts = {}

        try:
            # Count modules (folders)
            counts["modules"] = self.db.count_entity_mappings(self.project_key, "folder_to_module")

            # Count test cases
            counts["test_cases"] = self.db.count_entity_mappings(
                self.project_key, "testcase_to_testcase"
            )

            # Count test cycles
            counts["test_cycles"] = self.db.count_entity_mappings(
                self.project_key, "cycle_to_cycle"
            )

            # Count test runs (executions)
            counts["test_runs"] = self.db.count_entity_mappings(
                self.project_key, "execution_to_run"
            )
        except Exception as e:
            logger.error(f"Error getting qTest entity counts: {str(e)}")

        return counts

    def _map_entity_type(self, zephyr_type: str) -> str:
        """
        Map Zephyr entity type to qTest entity type.

        Args:
            zephyr_type: Zephyr entity type

        Returns:
            Corresponding qTest entity type
        """
        mapping = {
            "folders": "modules",
            "test_cases": "test_cases",
            "test_cycles": "test_cycles",
            "test_executions": "test_runs",
        }
        return mapping.get(zephyr_type, zephyr_type)

    def _get_scope_for_entity(self, entity_type: str) -> ValidationScope:
        """
        Get validation scope for entity type.

        Args:
            entity_type: Entity type

        Returns:
            Corresponding validation scope
        """
        mapping = {
            "folders": ValidationScope.FOLDER,
            "test_cases": ValidationScope.TEST_CASE,
            "test_cycles": ValidationScope.TEST_CYCLE,
            "test_executions": ValidationScope.TEST_EXECUTION,
        }
        return mapping.get(entity_type, ValidationScope.SYSTEM)

    def _get_mapping_type_for_entity(self, entity_type: str) -> str:
        """
        Get mapping type for entity type.

        Args:
            entity_type: Entity type

        Returns:
            Corresponding mapping type
        """
        mapping = {
            "folders": "folder_to_module",
            "test_cases": "testcase_to_testcase",
            "test_cycles": "cycle_to_cycle",
            "test_executions": "execution_to_run",
        }
        return mapping.get(entity_type, "")

    def _map_custom_field_name(self, zephyr_field_name: str) -> str:
        """
        Map Zephyr custom field name to qTest custom field name.

        Args:
            zephyr_field_name: Zephyr custom field name

        Returns:
            Corresponding qTest custom field name
        """
        # In a real implementation, this would use a mapping configuration
        # For now, we'll use a simple sanitization approach
        return zephyr_field_name.replace(" ", "_").lower()

    def _normalize_custom_field_value(self, value: Any) -> str:
        """
        Normalize custom field value for comparison.

        Args:
            value: Custom field value

        Returns:
            Normalized value as string
        """
        if value is None:
            return ""

        if isinstance(value, bool):
            return str(value).lower()

        if isinstance(value, (int, float)):
            return str(value)

        return str(value).strip().lower()

    def run_all_validations(self) -> List[ValidationIssue]:
        """
        Run all data comparison validations.

        Returns:
            List of all validation issues found
        """
        issues = []

        # Entity count validation
        logger.info("Validating entity counts")
        entity_count_issues = self.validate_entity_counts()
        issues.extend(entity_count_issues)

        # Critical entity validation
        logger.info("Validating critical entities")
        critical_entity_issues = self.validate_critical_entities()
        issues.extend(critical_entity_issues)

        # Relationship integrity validation
        logger.info("Validating relationship integrity")
        relationship_issues = self.validate_relationship_integrity()
        issues.extend(relationship_issues)

        # Custom field validation
        logger.info("Validating custom field migration")
        custom_field_issues = self.validate_custom_field_migration()
        issues.extend(custom_field_issues)

        # Attachment validation
        logger.info("Validating attachment migration")
        attachment_issues = self.validate_attachment_migration()
        issues.extend(attachment_issues)

        logger.info(f"Data comparison validation complete: {len(issues)} issues found")
        return issues


class DataComparisonRule(ValidationRule):
    """Validation rule that utilizes the DataComparisonValidator."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        comparison_method: str,
        level: ValidationLevel = ValidationLevel.ERROR,
    ):
        """
        Initialize the data comparison rule.

        Args:
            id: Unique identifier for the rule
            name: Name of the rule
            description: Description of the rule
            comparison_method: Name of the method to call on DataComparisonValidator
            level: Validation level for issues found by this rule
        """
        super().__init__(
            id=id,
            name=name,
            description=description,
            scope=ValidationScope.SYSTEM,
            phase=ValidationPhase.POST_MIGRATION,
            level=level,
        )
        self.comparison_method = comparison_method

    def validate(self, entity: Any, context: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Execute the data comparison validation.

        Args:
            entity: Not used in this rule type
            context: Must contain 'database' and 'project_key'

        Returns:
            List of validation issues found
        """
        database = context.get("database")
        project_key = context.get("project_key")

        if not database or not project_key:
            logger.warning("Cannot perform data comparison without database and project_key")
            return []

        validator = DataComparisonValidator(database, project_key)

        # Call the specified comparison method
        method = getattr(validator, self.comparison_method, None)
        if method and callable(method):
            return method()

        logger.warning(f"Invalid comparison method: {self.comparison_method}")
        return []


def get_data_comparison_rules() -> List[ValidationRule]:
    """
    Get a list of data comparison validation rules.

    Returns:
        List of validation rules
    """
    rules = []

    # Entity count validation
    rules.append(
        DataComparisonRule(
            id="entity_count_comparison",
            name="Entity Count Comparison",
            description="Validates that all entities were migrated by comparing counts",
            comparison_method="validate_entity_counts",
            level=ValidationLevel.ERROR,
        )
    )

    # Critical entity validation
    rules.append(
        DataComparisonRule(
            id="critical_entity_validation",
            name="Critical Entity Validation",
            description="Validates that all critical entities were migrated correctly",
            comparison_method="validate_critical_entities",
            level=ValidationLevel.CRITICAL,
        )
    )

    # Relationship integrity validation
    rules.append(
        DataComparisonRule(
            id="relationship_integrity_validation",
            name="Relationship Integrity Validation",
            description="Validates that relationships between entities were preserved",
            comparison_method="validate_relationship_integrity",
            level=ValidationLevel.ERROR,
        )
    )

    # Custom field validation
    rules.append(
        DataComparisonRule(
            id="custom_field_migration_validation",
            name="Custom Field Migration Validation",
            description="Validates that custom fields were migrated correctly",
            comparison_method="validate_custom_field_migration",
            level=ValidationLevel.WARNING,
        )
    )

    # Attachment validation
    rules.append(
        DataComparisonRule(
            id="attachment_migration_validation",
            name="Attachment Migration Validation",
            description="Validates that attachments were migrated correctly",
            comparison_method="validate_attachment_migration",
            level=ValidationLevel.WARNING,
        )
    )

    return rules
