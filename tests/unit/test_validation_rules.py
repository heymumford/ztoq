"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Unit tests for validation rules.
"""

import unittest
from unittest.mock import MagicMock, patch
from ztoq.validation import (
    ValidationIssue,
    ValidationLevel,
    ValidationPhase,
    ValidationScope,
)
from ztoq.validation_rules import (
    AttachmentRule,
    CustomFieldRule,
    DataIntegrityRule,
    PatternMatchRule,
    ReferentialIntegrityRule,
    RelationshipRule,
    RequiredFieldRule,
    StringLengthRule,
    TestStatusMappingRule,
    TestStepValidationRule,
    UniqueValueRule,
    get_built_in_rules,
    get_test_status_mappings,
)


class TestRequiredFieldRule(unittest.TestCase):
    """Test RequiredFieldRule implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.rule = RequiredFieldRule(
            id="test_required_fields",
            name="Test Required Fields",
            description="Test rule",
            scope=ValidationScope.TEST_CASE,
            phase=ValidationPhase.EXTRACTION,
            required_fields=["name", "description"],
            level=ValidationLevel.ERROR,
        )

    def test_validate_dict_entity_missing_fields(self):
        """Test validation with dictionary entity missing required fields."""
        entity = {"id": "123", "key": "TEST-123"}
        context = {"entity_type": "test_case"}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0].field_name, "name")
        self.assertEqual(issues[1].field_name, "description")
        self.assertEqual(issues[0].level, ValidationLevel.ERROR)

    def test_validate_dict_entity_with_empty_fields(self):
        """Test validation with dictionary entity having empty fields."""
        entity = {"id": "123", "key": "TEST-123", "name": "", "description": None}
        context = {"entity_type": "test_case"}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0].field_name, "name")
        self.assertEqual(issues[1].field_name, "description")

    def test_validate_dict_entity_with_valid_fields(self):
        """Test validation with dictionary entity having valid fields."""
        entity = {
            "id": "123",
            "key": "TEST-123",
            "name": "Test Case",
            "description": "Test description",
        }
        context = {"entity_type": "test_case"}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 0)

    def test_validate_object_entity_missing_fields(self):
        """Test validation with object entity missing required fields."""

        class TestCase:
            def __init__(self):
                self.id = "123"

        entity = TestCase()
        context = {"entity_type": "test_case"}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0].field_name, "name")
        self.assertEqual(issues[1].field_name, "description")

    def test_validate_object_entity_with_empty_fields(self):
        """Test validation with object entity having empty fields."""

        class TestCase:
            def __init__(self):
                self.id = "123"
                self.name = ""
                self.description = None

        entity = TestCase()
        context = {"entity_type": "test_case"}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0].field_name, "name")
        self.assertEqual(issues[1].field_name, "description")

    def test_validate_object_entity_with_valid_fields(self):
        """Test validation with object entity having valid fields."""

        class TestCase:
            def __init__(self):
                self.id = "123"
                self.name = "Test Case"
                self.description = "Test description"

        entity = TestCase()
        context = {"entity_type": "test_case"}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 0)


class TestStringLengthRule(unittest.TestCase):
    """Test StringLengthRule implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.rule = StringLengthRule(
            id="test_string_length",
            name="Test String Length",
            description="Test rule",
            scope=ValidationScope.TEST_CASE,
            phase=ValidationPhase.EXTRACTION,
            field_limits={"name": {"min": 3, "max": 10}, "description": {"min": 10}},
            level=ValidationLevel.WARNING,
        )

    def test_validate_dict_entity_with_invalid_length(self):
        """Test validation with dictionary entity having invalid field lengths."""
        entity = {"id": "123", "name": "AB", "description": "Short"}
        context = {"entity_type": "test_case"}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0].field_name, "name")
        self.assertEqual(issues[1].field_name, "description")
        self.assertEqual(issues[0].level, ValidationLevel.WARNING)

    def test_validate_dict_entity_with_long_name(self):
        """Test validation with dictionary entity having too long name."""
        entity = {
            "id": "123",
            "name": "This name is too long",
            "description": "Long enough description",
        }
        context = {"entity_type": "test_case"}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].field_name, "name")
        self.assertTrue("exceeds maximum" in issues[0].message)

    def test_validate_dict_entity_with_valid_lengths(self):
        """Test validation with dictionary entity having valid field lengths."""
        entity = {"id": "123", "name": "Valid", "description": "Long enough description"}
        context = {"entity_type": "test_case"}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 0)


class TestPatternMatchRule(unittest.TestCase):
    """Test PatternMatchRule implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.rule = PatternMatchRule(
            id="test_pattern_match",
            name="Test Pattern Match",
            description="Test rule",
            scope=ValidationScope.TEST_CASE,
            phase=ValidationPhase.EXTRACTION,
            field_patterns={
                "key": r"^[A-Z]+-\d+$",
                "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            },
            level=ValidationLevel.ERROR,
        )

    def test_validate_dict_entity_with_invalid_patterns(self):
        """Test validation with dictionary entity having invalid patterns."""
        entity = {"id": "123", "key": "test-123", "email": "invalid-email"}
        context = {"entity_type": "test_case"}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0].field_name, "key")
        self.assertEqual(issues[1].field_name, "email")

    def test_validate_dict_entity_with_valid_patterns(self):
        """Test validation with dictionary entity having valid patterns."""
        entity = {"id": "123", "key": "TEST-123", "email": "test@example.com"}
        context = {"entity_type": "test_case"}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 0)


class TestRelationshipRule(unittest.TestCase):
    """Test RelationshipRule implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.rule = RelationshipRule(
            id="test_relationship",
            name="Test Relationship",
            description="Test rule",
            scope=ValidationScope.TEST_CASE,
            phase=ValidationPhase.EXTRACTION,
            relation_field="folder_id",
            related_entity_type="folders",
            level=ValidationLevel.ERROR,
        )

    def test_validate_with_invalid_relationship(self):
        """Test validation with invalid relationship."""
        mock_database = MagicMock()
        mock_database.entity_exists.return_value = False

        entity = {"id": "123", "folder_id": "456"}
        context = {"entity_type": "test_case", "database": mock_database}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].field_name, "folder_id")
        mock_database.entity_exists.assert_called_once_with("folders", "456")

    def test_validate_with_valid_relationship(self):
        """Test validation with valid relationship."""
        mock_database = MagicMock()
        mock_database.entity_exists.return_value = True

        entity = {"id": "123", "folder_id": "456"}
        context = {"entity_type": "test_case", "database": mock_database}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 0)
        mock_database.entity_exists.assert_called_once_with("folders", "456")

    def test_validate_without_database(self):
        """Test validation without database in context."""
        entity = {"id": "123", "folder_id": "456"}
        context = {"entity_type": "test_case"}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 0)


class TestCustomFieldRule(unittest.TestCase):
    """Test CustomFieldRule implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.rule = CustomFieldRule(
            id="test_custom_field",
            name="Test Custom Field",
            description="Test rule",
            scope=ValidationScope.TEST_CASE,
            phase=ValidationPhase.TRANSFORMATION,
            field_constraints={
                "priority": {"type": "string", "allowed_values": ["Low", "Medium", "High"]},
                "points": {"type": "number"},
                "automated": {"type": "boolean"},
            },
            level=ValidationLevel.WARNING,
        )

    def test_validate_with_invalid_custom_fields(self):
        """Test validation with invalid custom fields."""
        entity = {
            "id": "123",
            "customFields": {
                "priority": "Critical",  # Not in allowed values
                "points": "5",  # Should be a number
                "automated": "true",  # Should be a boolean
            },
        }
        context = {"entity_type": "test_case"}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 3)
        self.assertTrue(any(issue.field_name == "priority" for issue in issues))
        self.assertTrue(any(issue.field_name == "points" for issue in issues))
        self.assertTrue(any(issue.field_name == "automated" for issue in issues))

    def test_validate_with_valid_custom_fields(self):
        """Test validation with valid custom fields."""
        entity = {
            "id": "123",
            "customFields": {
                "priority": "High",
                "points": 5,
                "automated": True,
            },
        }
        context = {"entity_type": "test_case"}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 0)


class TestAttachmentRule(unittest.TestCase):
    """Test AttachmentRule implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.rule = AttachmentRule(
            id="test_attachment",
            name="Test Attachment",
            description="Test rule",
            phase=ValidationPhase.EXTRACTION,
            max_size=1024,  # 1KB
            allowed_extensions=["pdf", "jpg", "png"],
            level=ValidationLevel.WARNING,
        )

    def test_validate_with_oversized_attachment(self):
        """Test validation with oversized attachment."""
        entity = {
            "id": "123",
            "name": "test.jpg",
            "size": 2048,  # 2KB
        }
        context = {}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 1)
        self.assertTrue("exceeds maximum size" in issues[0].message)

    def test_validate_with_invalid_extension(self):
        """Test validation with invalid extension."""
        entity = {
            "id": "123",
            "name": "test.exe",
            "size": 512,
        }
        context = {}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 1)
        self.assertTrue("disallowed file extension" in issues[0].message)

    def test_validate_with_valid_attachment(self):
        """Test validation with valid attachment."""
        entity = {
            "id": "123",
            "name": "test.pdf",
            "size": 512,
        }
        context = {}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 0)


class TestTestStepValidationRule(unittest.TestCase):
    """Test TestStepValidationRule implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.rule = TestStepValidationRule(
            id="test_steps_validation",
            name="Test Steps Validation",
            description="Test rule",
            phase=ValidationPhase.EXTRACTION,
            level=ValidationLevel.WARNING,
        )

    def test_validate_with_no_steps(self):
        """Test validation with no steps."""
        entity = {"id": "123", "name": "Test Case", "steps": []}
        context = {}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 1)
        self.assertTrue("no steps" in issues[0].message)

    def test_validate_with_empty_step_description(self):
        """Test validation with empty step description."""
        entity = {
            "id": "123",
            "name": "Test Case",
            "steps": [{"description": "", "expected_result": "Expected result"}],
        }
        context = {}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 1)
        self.assertTrue("empty description" in issues[0].message)

    def test_validate_with_valid_steps(self):
        """Test validation with valid steps."""
        entity = {
            "id": "123",
            "name": "Test Case",
            "steps": [
                {"description": "Step 1", "expected_result": "Expected result 1"},
                {"description": "Step 2", "expected_result": "Expected result 2"},
            ],
        }
        context = {}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 0)


class TestDataIntegrityRule(unittest.TestCase):
    """Test DataIntegrityRule implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.rule = DataIntegrityRule(
            id="test_data_integrity",
            name="Test Data Integrity",
            description="Test rule",
            scope=ValidationScope.TEST_CASE,
            fields_to_compare=[("name", "name"), ("description", "description")],
            level=ValidationLevel.ERROR,
        )

    def test_validate_with_data_mismatch(self):
        """Test validation with data mismatch."""
        source_entity = {"id": "123", "name": "Test Case", "description": "Original description"}
        target_entity = {
            "id": "456",
            "name": "Test Case Modified",
            "description": "Changed description",
        }
        context = {
            "entity_type": "test_case",
            "source_entity": source_entity,
            "target_entity": target_entity,
        }

        issues = self.rule.validate(None, context)

        self.assertEqual(len(issues), 2)
        self.assertTrue(any(issue.field_name == "name" for issue in issues))
        self.assertTrue(any(issue.field_name == "description" for issue in issues))

    def test_validate_with_matching_data(self):
        """Test validation with matching data."""
        source_entity = {"id": "123", "name": "Test Case", "description": "Test description"}
        target_entity = {"id": "456", "name": "Test Case", "description": "Test description"}
        context = {
            "entity_type": "test_case",
            "source_entity": source_entity,
            "target_entity": target_entity,
        }

        issues = self.rule.validate(None, context)

        self.assertEqual(len(issues), 0)


class TestTestStatusMappingRule(unittest.TestCase):
    """Test TestStatusMappingRule implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.rule = TestStatusMappingRule(
            id="test_status_mapping",
            name="Test Status Mapping",
            description="Test rule",
            status_mappings={"PASS": "PASSED", "FAIL": "FAILED"},
            level=ValidationLevel.WARNING,
        )

    def test_validate_with_incorrect_mapping(self):
        """Test validation with incorrect mapping."""
        source_entity = {"id": "123", "status": "PASS"}
        target_entity = {"id": "456", "status": "FAILED"}  # Should be PASSED
        context = {"source_entity": source_entity, "target_entity": target_entity}

        issues = self.rule.validate(None, context)

        self.assertEqual(len(issues), 1)
        self.assertTrue("should map to" in issues[0].message)

    def test_validate_with_correct_mapping(self):
        """Test validation with correct mapping."""
        source_entity = {"id": "123", "status": "PASS"}
        target_entity = {"id": "456", "status": "PASSED"}  # Correct mapping
        context = {"source_entity": source_entity, "target_entity": target_entity}

        issues = self.rule.validate(None, context)

        self.assertEqual(len(issues), 0)


class TestReferentialIntegrityRule(unittest.TestCase):
    """Test ReferentialIntegrityRule implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.rule = ReferentialIntegrityRule(
            id="test_referential_integrity",
            name="Test Referential Integrity",
            description="Test rule",
            scope=ValidationScope.TEST_CASE,
            reference_field="folder_id",
            mapping_type="folder_to_module",
            level=ValidationLevel.ERROR,
        )

    def test_validate_with_missing_mapping(self):
        """Test validation with missing mapping."""
        mock_database = MagicMock()
        mock_database.get_mapped_entity_id.return_value = None

        entity = {"id": "123", "folder_id": "456"}
        context = {"entity_type": "test_case", "database": mock_database, "project_key": "TEST"}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 1)
        self.assertTrue("has no mapping" in issues[0].message)
        mock_database.get_mapped_entity_id.assert_called_once_with(
            "TEST", "folder_to_module", "456"
        )

    def test_validate_with_valid_mapping(self):
        """Test validation with valid mapping."""
        mock_database = MagicMock()
        mock_database.get_mapped_entity_id.return_value = "789"

        entity = {"id": "123", "folder_id": "456"}
        context = {"entity_type": "test_case", "database": mock_database, "project_key": "TEST"}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 0)
        mock_database.get_mapped_entity_id.assert_called_once_with(
            "TEST", "folder_to_module", "456"
        )


class TestUniqueValueRule(unittest.TestCase):
    """Test UniqueValueRule implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.rule = UniqueValueRule(
            id="test_unique_value",
            name="Test Unique Value",
            description="Test rule",
            scope=ValidationScope.TEST_CASE,
            phase=ValidationPhase.EXTRACTION,
            unique_fields=["key", "name"],
            level=ValidationLevel.ERROR,
        )

    def test_validate_with_duplicate_values(self):
        """Test validation with duplicate values."""
        mock_database = MagicMock()
        mock_database.find_duplicates.return_value = ["789"]

        entity = {"id": "123", "key": "TEST-123", "name": "Test Case"}
        context = {"entity_type": "test_case", "database": mock_database}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 2)  # Both key and name have duplicates
        self.assertTrue(any(issue.field_name == "key" for issue in issues))
        self.assertTrue(any(issue.field_name == "name" for issue in issues))
        self.assertEqual(mock_database.find_duplicates.call_count, 2)

    def test_validate_with_unique_values(self):
        """Test validation with unique values."""
        mock_database = MagicMock()
        mock_database.find_duplicates.return_value = []

        entity = {"id": "123", "key": "TEST-123", "name": "Test Case"}
        context = {"entity_type": "test_case", "database": mock_database}

        issues = self.rule.validate(entity, context)

        self.assertEqual(len(issues), 0)
        self.assertEqual(mock_database.find_duplicates.call_count, 2)


class TestBuiltInRules(unittest.TestCase):
    """Test built-in rules functions."""

    def test_get_test_status_mappings(self):
        """Test get_test_status_mappings function."""
        mappings = get_test_status_mappings()

        self.assertIsInstance(mappings, dict)
        self.assertIn("PASS", mappings)
        self.assertEqual(mappings["PASS"], "PASSED")
        self.assertIn("FAIL", mappings)
        self.assertEqual(mappings["FAIL"], "FAILED")

    def test_get_built_in_rules(self):
        """Test get_built_in_rules function."""
        with patch("ztoq.validation_rules.get_data_comparison_rules", return_value=[]):
            rules = get_built_in_rules()

            self.assertIsInstance(rules, list)
            self.assertTrue(len(rules) > 0)

            # Check that all objects are ValidationRule instances
            for rule in rules:
                self.assertTrue(hasattr(rule, "validate"))
                self.assertTrue(hasattr(rule, "id"))
                self.assertTrue(hasattr(rule, "scope"))
                self.assertTrue(hasattr(rule, "phase"))


if __name__ == "__main__":
    unittest.main()
