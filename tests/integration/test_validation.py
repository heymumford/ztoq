"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Integration tests for validation framework.
"""

import unittest
from unittest.mock import MagicMock, patch
from ztoq.validation import (
    MigrationValidator,
    ValidationIssue,
    ValidationLevel,
    ValidationManager,
    ValidationPhase,
    ValidationRule,
    ValidationScope,
)
from ztoq.validation_integration import EnhancedMigration
from ztoq.validation_rules import get_built_in_rules


class MockRule(ValidationRule):
    """Mock validation rule for testing."""

    def __init__(self, id, phase, scope, level=ValidationLevel.ERROR):
        """Initialize mock rule."""
        super().__init__(
            id=id,
            name=f"Mock {id}",
            description="Mock rule for testing",
            scope=scope,
            phase=phase,
            level=level,
        )
        self.called = False
        self.issue_to_return = None

    def validate(self, entity, context):
        """Mock validation implementation."""
        self.called = True
        if self.issue_to_return:
            return [self.issue_to_return]
        return []


class TestValidationIntegration(unittest.TestCase):
    """Integration tests for validation framework."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = MagicMock()
        self.project_key = "TEST"

        # Create validation manager
        self.validation_manager = ValidationManager(self.mock_db, self.project_key)

        # Clear built-in rules for testing
        self.validation_manager.registry.rules = {}
        self.validation_manager.registry.rules_by_scope = {scope: [] for scope in ValidationScope}
        self.validation_manager.registry.rules_by_phase = {phase: [] for phase in ValidationPhase}

        # Create validator
        self.validator = MigrationValidator(self.validation_manager)

        # Create mock migration
        self.mock_migration = MagicMock()
        self.mock_migration.extract_data.return_value = {
            "test_cases": [{"id": "123", "name": "Test Case"}]
        }
        self.mock_migration.transform_data.return_value = {
            "test_cases": [{"id": "456", "name": "Test Case in qTest"}]
        }
        self.mock_migration.load_data.return_value = {"success": True}

        # Add custom mock rules
        self.extract_rule = MockRule(
            "test_extract", ValidationPhase.EXTRACTION, ValidationScope.TEST_CASE
        )
        self.transform_rule = MockRule(
            "test_transform", ValidationPhase.TRANSFORMATION, ValidationScope.TEST_CASE
        )
        self.load_rule = MockRule("test_load", ValidationPhase.LOADING, ValidationScope.TEST_CASE)

        self.validation_manager.registry.register_rule(self.extract_rule)
        self.validation_manager.registry.register_rule(self.transform_rule)
        self.validation_manager.registry.register_rule(self.load_rule)

    def test_validation_manager_registry(self):
        """Test validation rule registry."""
        # Create a new validation manager with built-in rules
        validation_manager = ValidationManager(self.mock_db, self.project_key)

        # Verify built-in rules were registered
        self.assertTrue(len(validation_manager.registry.rules) > 0)

        # Verify rules are organized by scope and phase
        self.assertTrue(
            len(validation_manager.registry.rules_by_scope[ValidationScope.TEST_CASE]) > 0
        )
        self.assertTrue(
            len(validation_manager.registry.rules_by_phase[ValidationPhase.EXTRACTION]) > 0
        )

        # Verify we can get rules by scope and phase
        test_case_rules = validation_manager.registry.get_rules_for_scope(ValidationScope.TEST_CASE)
        self.assertTrue(len(test_case_rules) > 0)
        extraction_rules = validation_manager.registry.get_rules_for_phase(
            ValidationPhase.EXTRACTION
        )
        self.assertTrue(len(extraction_rules) > 0)

    def test_validation_issue_tracking(self):
        """Test validation issue tracking."""
        # Create a validation issue
        issue = ValidationIssue(
            id="test_issue",
            level=ValidationLevel.ERROR,
            scope=ValidationScope.TEST_CASE,
            phase=ValidationPhase.EXTRACTION,
            message="Test issue",
            entity_id="123",
            entity_type="test_case",
        )

        # Add issue to manager
        self.validation_manager.add_issue(issue)

        # Verify issue was tracked
        self.assertEqual(len(self.validation_manager.issues), 1)
        self.assertEqual(self.validation_manager.get_issue_count(), 1)
        self.assertEqual(self.validation_manager.get_issue_count(ValidationLevel.ERROR), 1)
        self.assertEqual(self.validation_manager.get_issue_count(ValidationLevel.WARNING), 0)

        # Verify we can get issues by criteria
        issues = self.validation_manager.get_issues(level=ValidationLevel.ERROR)
        self.assertEqual(len(issues), 1)
        issues = self.validation_manager.get_issues(scope=ValidationScope.TEST_CASE)
        self.assertEqual(len(issues), 1)
        issues = self.validation_manager.get_issues(entity_id="123")
        self.assertEqual(len(issues), 1)
        issues = self.validation_manager.get_issues(entity_id="456")
        self.assertEqual(len(issues), 0)

        # Verify has_error_issues and has_critical_issues
        self.assertTrue(self.validation_manager.has_error_issues())
        self.assertFalse(self.validation_manager.has_critical_issues())

    def test_execute_validation(self):
        """Test execute_validation method."""
        # Create test entity and context
        entity = {"id": "123", "name": "Test Case"}
        context = {"entity_type": "test_case"}

        # Configure rule to return an issue
        self.extract_rule.issue_to_return = ValidationIssue(
            id="test_execute_issue",
            level=ValidationLevel.ERROR,
            scope=ValidationScope.TEST_CASE,
            phase=ValidationPhase.EXTRACTION,
            message="Test validation issue",
            entity_id="123",
            entity_type="test_case",
        )

        # Execute validation
        issues = self.validation_manager.execute_validation(
            entity, ValidationScope.TEST_CASE, ValidationPhase.EXTRACTION, context
        )

        # Verify rule was called and issue was added
        self.assertTrue(self.extract_rule.called)
        self.assertEqual(len(issues), 1)
        self.assertEqual(self.validation_manager.get_issue_count(), 1)

    def test_migration_validation_phases(self):
        """Test validation integration in migration phases."""
        # Configure rules to return issues
        self.extract_rule.issue_to_return = ValidationIssue(
            id="extract_issue",
            level=ValidationLevel.WARNING,
            scope=ValidationScope.TEST_CASE,
            phase=ValidationPhase.EXTRACTION,
            message="Extraction issue",
            entity_id="123",
            entity_type="test_case",
        )

        self.transform_rule.issue_to_return = ValidationIssue(
            id="transform_issue",
            level=ValidationLevel.ERROR,
            scope=ValidationScope.TEST_CASE,
            phase=ValidationPhase.TRANSFORMATION,
            message="Transformation issue",
            entity_id="456",
            entity_type="test_case",
        )

        # Simulate validation phases
        test_case = {"id": "123", "name": "Test Case"}
        context = {"entity_type": "test_case"}

        # Execute extraction validation
        self.validation_manager.execute_validation(
            test_case, ValidationScope.TEST_CASE, ValidationPhase.EXTRACTION, context
        )

        # Execute transformation validation
        transformed_case = {"id": "456", "name": "Test Case in qTest"}
        self.validation_manager.execute_validation(
            transformed_case, ValidationScope.TEST_CASE, ValidationPhase.TRANSFORMATION, context
        )

        # Verify rules were called
        self.assertTrue(self.extract_rule.called)
        self.assertTrue(self.transform_rule.called)

        # Verify issues were tracked
        self.assertEqual(self.validation_manager.get_issue_count(), 2)
        self.assertEqual(self.validation_manager.get_issue_count(ValidationLevel.WARNING), 1)
        self.assertEqual(self.validation_manager.get_issue_count(ValidationLevel.ERROR), 1)

    def test_validation_report_generation(self):
        """Test validation report generation."""
        # Add test issues
        self.validation_manager.add_issue(
            ValidationIssue(
                id="report_issue_1",
                level=ValidationLevel.ERROR,
                scope=ValidationScope.TEST_CASE,
                phase=ValidationPhase.EXTRACTION,
                message="Test issue 1",
                entity_id="123",
                entity_type="test_case",
            )
        )

        self.validation_manager.add_issue(
            ValidationIssue(
                id="report_issue_2",
                level=ValidationLevel.WARNING,
                scope=ValidationScope.TEST_CYCLE,
                phase=ValidationPhase.TRANSFORMATION,
                message="Test issue 2",
                entity_id="456",
                entity_type="test_cycle",
            )
        )

        # Generate report
        report = self.validator.generate_validation_report()

        # Verify report contents
        self.assertEqual(report["total_issues"], 2)
        self.assertEqual(report["error_issue_count"], 1)
        self.assertEqual(report["warning_issue_count"], 1)
        self.assertEqual(len(report["counts_by_scope"]), 2)
        self.assertEqual(len(report["counts_by_phase"]), 2)
        self.assertTrue("issues_by_level" in report)
        self.assertTrue(ValidationLevel.ERROR.value in report["issues_by_level"])
        self.assertTrue(ValidationLevel.WARNING.value in report["issues_by_level"])

        # Verify database save was called
        self.mock_db.save_validation_report.assert_called_once()


if __name__ == "__main__":
    unittest.main()
