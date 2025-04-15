"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Custom field mapping module for transforming fields between Zephyr Scale and qTest.

This module implements the mapping logic for custom fields as specified in the
entity-mapping.md document.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from ztoq.models import CustomField, CustomFieldType
from ztoq.qtest_models import QTestCustomField
from dateutil import parser

logger = logging.getLogger("ztoq.custom_field_mapping")


class CustomFieldMapper:
    """
    Maps custom fields between Zephyr Scale and qTest.

    This class handles the transformation of custom fields from Zephyr Scale format
    to qTest format, including type conversions and special field handling.
    """

    def __init__(self, field_mappings: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Initialize the custom field mapper.

        Args:
            field_mappings: Optional dictionary of custom field mappings.
                If not provided, default mappings will be used.
        """
        # Default field type mappings from Zephyr to qTest
        self.type_mappings = {
            CustomFieldType.TEXT: "STRING",
            CustomFieldType.PARAGRAPH: "STRING",
            CustomFieldType.CHECKBOX: "CHECKBOX",
            CustomFieldType.RADIO: "STRING",
            CustomFieldType.DROPDOWN: "STRING",
            CustomFieldType.MULTIPLE_SELECT: "STRING",
            CustomFieldType.NUMERIC: "NUMBER",
            CustomFieldType.DATE: "DATE",
            CustomFieldType.DATETIME: "DATE",
            CustomFieldType.USER: "STRING",
            CustomFieldType.URL: "STRING",
            CustomFieldType.TABLE: "STRING",
            # Enterprise fields
            CustomFieldType.HIERARCHICAL_SELECT: "STRING",
            CustomFieldType.USER_GROUP: "STRING",
            CustomFieldType.LABEL: "STRING",
            CustomFieldType.SPRINT: "STRING",
            CustomFieldType.VERSION: "STRING",
            CustomFieldType.COMPONENT: "STRING",
        }

        # Special field mappings (Zephyr field name to qTest field name)
        self.field_name_mappings = {
            "Epic Link": "Epic_Link",
            "Components": "Components",
            "Labels": "Tags",
            "Sprint": "Sprint_Release",
            "Automated": "Automation",
            "Test Type": "Test_Type",
            "Severity": "Severity",
            "Risk Level": "Risk_Level",
        }

        # Default status mappings from Zephyr to qTest
        self.status_mappings = {
            "PASS": "PASSED",
            "FAIL": "FAILED",
            "WIP": "IN_PROGRESS",
            "BLOCKED": "BLOCKED",
            "NOT EXECUTED": "NOT_RUN",
            "UNEXECUTED": "NOT_RUN",
            "PASS WITH WARNINGS": "PASSED",
            "CONDITIONAL PASS": "PASSED",
            "IN PROGRESS": "IN_PROGRESS",
            "EXECUTING": "IN_PROGRESS",
            "ABORTED": "BLOCKED",
            "CANCELED": "NOT_RUN",
            "PENDING": "NOT_RUN",
            "PASSED": "PASSED",
            "FAILED": "FAILED",
            "NOT_RUN": "NOT_RUN",
            "IN_PROGRESS": "IN_PROGRESS",
        }

        # Default priority mappings from Zephyr to qTest
        self.priority_mappings = {
            "HIGHEST": "CRITICAL",
            "HIGH": "HIGH",
            "MEDIUM": "MEDIUM",
            "LOW": "LOW",
            "LOWEST": "TRIVIAL",
            "BLOCKER": "CRITICAL",
            "CRITICAL": "CRITICAL",
            "MAJOR": "HIGH",
            "MINOR": "LOW",
            "TRIVIAL": "TRIVIAL",
        }

        # Additional mappings provided by the user
        self.custom_mappings = field_mappings or {}

    def get_qtest_field_name(self, zephyr_field_name: str) -> str:
        """
        Get the qTest field name for a Zephyr field name.

        Args:
            zephyr_field_name: The Zephyr field name

        Returns:
            The corresponding qTest field name
        """
        # Check if this is a special field with a direct mapping
        if zephyr_field_name in self.field_name_mappings:
            return self.field_name_mappings[zephyr_field_name]

        # Check custom mappings
        if self.custom_mappings and zephyr_field_name in self.custom_mappings:
            mapping = self.custom_mappings[zephyr_field_name]
            if "qtest_field_name" in mapping:
                return mapping["qtest_field_name"]

        # Default: sanitize the field name for qTest
        # Replace spaces with underscores and ensure it's lowercase
        return zephyr_field_name.replace(" ", "_").lower()

    def get_qtest_field_type(self, zephyr_field_type: str) -> str:
        """
        Get the qTest field type for a Zephyr field type.

        Args:
            zephyr_field_type: The Zephyr field type

        Returns:
            The corresponding qTest field type
        """
        # Check if we have a direct mapping for this type
        if zephyr_field_type in self.type_mappings:
            return self.type_mappings[zephyr_field_type]

        # Check custom mappings
        if self.custom_mappings:
            for field_name, mapping in self.custom_mappings.items():
                if (
                    mapping.get("zephyr_field_type") == zephyr_field_type
                    and "qtest_field_type" in mapping
                ):
                    return mapping["qtest_field_type"]

        # Default to STRING for unknown types
        logger.warning(f"Unknown Zephyr field type: {zephyr_field_type}, defaulting to STRING")
        return "STRING"

    def transform_field_value(self, field_name: str, field_type: str, value: Any) -> Any:
        """
        Transform a field value from Zephyr format to qTest format.

        Args:
            field_name: The name of the field
            field_type: The Zephyr field type
            value: The field value in Zephyr format

        Returns:
            The transformed value in qTest format
        """
        # Check custom transformations first
        if self.custom_mappings and field_name in self.custom_mappings:
            mapping = self.custom_mappings[field_name]
            if "transform_function" in mapping and callable(mapping["transform_function"]):
                try:
                    return mapping["transform_function"](value)
                except Exception as e:
                    logger.error(f"Error applying custom transformation for {field_name}: {str(e)}")

        # Handle null values
        if value is None:
            return ""

        # Special handling based on field name
        if field_name.lower() in ("status", "execution_status"):
            return self.map_status(str(value))

        if field_name.lower() in ("priority", "importance"):
            return self.map_priority(str(value))

        # Apply standard transformations based on field type
        if field_type == CustomFieldType.MULTIPLE_SELECT:
            # Join multiple selections with comma
            if isinstance(value, list):
                return ", ".join(str(v) for v in value)
            return str(value)

        elif field_type in (CustomFieldType.DATE, CustomFieldType.DATETIME):
            # Format date as ISO string
            if isinstance(value, datetime):
                return value.isoformat()

            # Try to parse string dates
            if isinstance(value, str) and value.strip():
                try:
                    # Try common date formats

                    dt = parser.parse(value)
                    return dt.isoformat()
                except (ImportError, ValueError, AttributeError):
                    # If parsing fails, return as is
                    pass

            return str(value)

        elif field_type == CustomFieldType.TABLE:
            # Enhanced table formatting
            return self._transform_table_field(value)

        elif field_type in (
            CustomFieldType.HIERARCHICAL_SELECT,
            CustomFieldType.USER_GROUP,
            CustomFieldType.COMPONENT,
            CustomFieldType.VERSION,
            CustomFieldType.LABEL,
            CustomFieldType.SPRINT,
        ):
            # Handle hierarchical and complex structured fields
            return self._transform_hierarchical_field(value)

        elif field_type == CustomFieldType.CHECKBOX:
            # Ensure boolean values
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "yes", "1", "on")
            return bool(value)

        elif field_type == CustomFieldType.NUMERIC:
            # Ensure numeric values
            try:
                if isinstance(value, (int, float)):
                    return value
                if isinstance(value, str) and value.strip():
                    return float(value)
                return 0
            except (ValueError, TypeError):
                logger.warning(f"Could not convert {value} to numeric, defaulting to 0")
                return 0

        elif field_type == CustomFieldType.USER:
            # Handle user fields (could be string, dict, or other formats)
            if isinstance(value, dict):
                # Extract username or display name
                for key in ("name", "displayName", "username", "value"):
                    if key in value and value[key]:
                        return str(value[key])
                # If no name found, return the ID or first available value
                for key in ("id", "accountId"):
                    if key in value and value[key]:
                        return str(value[key])
            return str(value)

        # For all other types, convert to string
        return str(value) if value is not None else ""

    def _transform_table_field(self, value: Any) -> str:
        """
        Transform a table field value to a well-formatted string representation.

        Args:
            value: The table field value (typically a list of rows)

        Returns:
            A formatted string representation of the table
        """
        if not value:
            return ""

        if not isinstance(value, list):
            return str(value)

        # Empty table
        if len(value) == 0:
            return ""

        # Handle different table formats
        first_item = value[0]

        # Case: List of dictionaries (most common table format)
        if isinstance(first_item, dict):
            # Extract column headers from all rows to handle non-uniform dictionaries
            headers = set()
            for row in value:
                if isinstance(row, dict):
                    headers.update(row.keys())

            # Convert headers to a sorted list for consistent output
            headers = sorted(headers)

            # Format the header row
            header_row = " | ".join(headers)
            separator = "-" * len(header_row)

            # Format the data rows
            rows = [header_row, separator]
            for row in value:
                if isinstance(row, dict):
                    # Extract values for each column, handling missing values
                    values = [str(row.get(header, "")) for header in headers]
                    rows.append(" | ".join(values))
                else:
                    rows.append(str(row))

            return "\n".join(rows)

        # Case: List of lists (matrix format)
        elif isinstance(first_item, list):
            # Consider first row as headers if it has string values
            has_headers = all(isinstance(cell, str) for cell in first_item)

            if has_headers:
                # Format with headers
                headers = first_item
                separator = "-" * sum(len(str(h)) + 3 for h in headers)

                rows = [" | ".join(str(h) for h in headers), separator]
                for row in value[1:]:
                    if isinstance(row, list):
                        # Ensure row has same length as headers
                        if len(row) < len(headers):
                            row = row + [""] * (len(headers) - len(row))
                        elif len(row) > len(headers):
                            row = row[: len(headers)]

                        rows.append(" | ".join(str(cell) for cell in row))
                    else:
                        rows.append(str(row))
            else:
                # Format without headers
                rows = []
                for row in value:
                    if isinstance(row, list):
                        rows.append(" | ".join(str(cell) for cell in row))
                    else:
                        rows.append(str(row))

            return "\n".join(rows)

        # Case: Simple list of values
        else:
            return "\n".join(str(item) for item in value)

    def _transform_hierarchical_field(self, value: Any) -> str:
        """
        Transform a hierarchical field value to a string representation.

        Args:
            value: The hierarchical field value

        Returns:
            A string representation of the hierarchical field
        """
        if not value:
            return ""

        # Handle hierarchical structure (typically a dictionary or nested list)
        if isinstance(value, dict):
            # Case: Dictionary with hierarchical structure
            if "id" in value and "name" in value:
                # Common format for hierarchical items
                return value.get("name", "")
            elif "value" in value and "label" in value:
                # Another common format
                return value.get("label", "")
            else:
                # Generic dictionary format
                return " > ".join(f"{k}: {v}" for k, v in value.items())

        elif isinstance(value, list):
            # Case: List of hierarchical items
            if all(isinstance(item, dict) for item in value):
                # Try to extract the hierarchy path
                path_items = []
                for item in value:
                    if "name" in item:
                        path_items.append(item["name"])
                    elif "label" in item:
                        path_items.append(item["label"])
                    elif "value" in item:
                        path_items.append(str(item["value"]))

                if path_items:
                    return " > ".join(path_items)

            # Default list handling
            return ", ".join(str(item) for item in value)

        # Default fallback
        return str(value)

    def map_status(self, zephyr_status: str) -> str:
        """
        Map a Zephyr status to the corresponding qTest status.

        Args:
            zephyr_status: The Zephyr status value

        Returns:
            The corresponding qTest status
        """
        if not zephyr_status:
            return "NOT_RUN"

        # Normalize status for lookup
        status_key = zephyr_status.upper().strip()

        # Use mapping or default to NOT_RUN
        return self.status_mappings.get(status_key, "NOT_RUN")

    def map_priority(self, zephyr_priority: str) -> str:
        """
        Map a Zephyr priority to the corresponding qTest priority.

        Args:
            zephyr_priority: The Zephyr priority value

        Returns:
            The corresponding qTest priority
        """
        if not zephyr_priority:
            return "MEDIUM"

        # Normalize priority for lookup
        priority_key = zephyr_priority.upper().strip()

        # Use mapping or default to MEDIUM
        return self.priority_mappings.get(priority_key, "MEDIUM")

    def extract_and_map_field(
        self,
        entity: Dict[str, Any],
        field_name: str,
        default_value: Any = None,
        target_type: str = None,
    ) -> Any:
        """
        Extract a field from an entity and apply mapping if needed.

        Args:
            entity: The source entity (dictionary)
            field_name: The field name to extract
            default_value: The default value if field is not found
            target_type: Optional target type for conversion

        Returns:
            The extracted and mapped field value
        """
        # Check if field exists
        if field_name not in entity:
            return default_value

        value = entity[field_name]
        if value is None:
            return default_value

        # Apply special mapping for known fields
        if field_name.lower() in ("status", "execution_status"):
            return self.map_status(str(value))

        if field_name.lower() in ("priority", "importance"):
            return self.map_priority(str(value))

        # Apply type conversion if needed
        if target_type:
            if target_type == "STRING":
                return str(value)
            elif target_type == "NUMBER":
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return 0
            elif target_type == "CHECKBOX" or target_type == "BOOLEAN":
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ("true", "yes", "1", "on")
                return bool(value)

        # Return as is
        return value

    def map_custom_fields(
        self, zephyr_fields: List[Union[CustomField, Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Map Zephyr custom fields to qTest custom fields.

        Args:
            zephyr_fields: List of Zephyr custom fields

        Returns:
            List of qTest custom fields as dictionaries
        """
        qtest_fields = []

        for field in zephyr_fields:
            # Extract field data
            if isinstance(field, CustomField):
                field_name = field.name
                field_type = field.type
                field_value = field.value
            elif isinstance(field, dict):
                field_name = field.get("name", "")
                field_type = field.get("type", "")
                field_value = field.get("value")
            else:
                logger.warning(f"Skipping invalid field: {field}")
                continue

            # Skip empty fields
            if field_value is None:
                continue

            # Get qTest field name and type
            qtest_field_name = self.get_qtest_field_name(field_name)
            qtest_field_type = self.get_qtest_field_type(field_type)

            # Transform the value
            qtest_field_value = self.transform_field_value(field_name, field_type, field_value)

            # Create qTest custom field as a dictionary
            qtest_field = {
                "field_id": 0,  # This will be set during creation in qTest
                "field_name": qtest_field_name,
                "field_type": qtest_field_type,
                "field_value": qtest_field_value,
            }

            qtest_fields.append(qtest_field)

        return qtest_fields

    def map_zephyr_key_to_custom_field(self, zephyr_key: str) -> Dict[str, Any]:
        """
        Create a qTest custom field to store the Zephyr key for reference.

        Args:
            zephyr_key: The Zephyr entity key

        Returns:
            A qTest custom field dictionary containing the Zephyr key
        """
        return {
            "field_id": 0,
            "field_name": "zephyr_key",
            "field_type": "STRING",
            "field_value": zephyr_key,
        }

    def map_testcase_fields(self, zephyr_testcase: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Map Zephyr test case fields to qTest custom fields.

        Args:
            zephyr_testcase: Zephyr test case data

        Returns:
            List of qTest custom fields as dictionaries
        """
        qtest_fields = []

        # Map Zephyr key
        if "key" in zephyr_testcase:
            qtest_fields.append(self.map_zephyr_key_to_custom_field(zephyr_testcase["key"]))

        # Map labels if present
        if "labels" in zephyr_testcase and zephyr_testcase["labels"]:
            labels_str = ", ".join(zephyr_testcase["labels"])
            qtest_fields.append(
                {
                    "field_id": 0,
                    "field_name": "Tags",
                    "field_type": "STRING",
                    "field_value": labels_str,
                }
            )

        # Map status if present
        if "status" in zephyr_testcase and zephyr_testcase["status"]:
            qtest_fields.append(
                {
                    "field_id": 0,
                    "field_name": "status",
                    "field_type": "STRING",
                    "field_value": zephyr_testcase["status"],
                }
            )

        # Map estimated time if present
        if "estimatedTime" in zephyr_testcase and zephyr_testcase["estimatedTime"]:
            qtest_fields.append(
                {
                    "field_id": 0,
                    "field_name": "estimated_time",
                    "field_type": "NUMBER",
                    "field_value": zephyr_testcase["estimatedTime"],
                }
            )

        # Map component if present
        if "component" in zephyr_testcase and zephyr_testcase["component"]:
            qtest_fields.append(
                {
                    "field_id": 0,
                    "field_name": "Components",
                    "field_type": "STRING",
                    "field_value": zephyr_testcase["component"],
                }
            )

        # Map custom fields
        if "customFields" in zephyr_testcase and zephyr_testcase["customFields"]:
            custom_fields = self.map_custom_fields(zephyr_testcase["customFields"])
            qtest_fields.extend(custom_fields)

        return qtest_fields

    def map_testcycle_fields(self, zephyr_cycle: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Map Zephyr test cycle fields to qTest custom fields.

        Args:
            zephyr_cycle: Zephyr test cycle data

        Returns:
            List of qTest custom fields as dictionaries
        """
        qtest_fields = []

        # Map Zephyr key
        if "key" in zephyr_cycle:
            qtest_fields.append(self.map_zephyr_key_to_custom_field(zephyr_cycle["key"]))

        # Map environment if present
        if "environment" in zephyr_cycle and zephyr_cycle["environment"]:
            qtest_fields.append(
                {
                    "field_id": 0,
                    "field_name": "environment",
                    "field_type": "STRING",
                    "field_value": zephyr_cycle["environment"],
                }
            )

        # Map status if present
        if "status" in zephyr_cycle and zephyr_cycle["status"]:
            qtest_fields.append(
                {
                    "field_id": 0,
                    "field_name": "status",
                    "field_type": "STRING",
                    "field_value": zephyr_cycle["status"],
                }
            )

        # Map owner if present
        if "owner" in zephyr_cycle and zephyr_cycle["owner"]:
            qtest_fields.append(
                {
                    "field_id": 0,
                    "field_name": "owner",
                    "field_type": "STRING",
                    "field_value": zephyr_cycle["owner"],
                }
            )

        # Map custom fields
        if "customFields" in zephyr_cycle and zephyr_cycle["customFields"]:
            custom_fields = self.map_custom_fields(zephyr_cycle["customFields"])
            qtest_fields.extend(custom_fields)

        return qtest_fields

    def map_testrun_fields(self, zephyr_execution: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Map Zephyr test execution fields to qTest test run custom fields.

        Args:
            zephyr_execution: Zephyr test execution data

        Returns:
            List of qTest custom fields as dictionaries
        """
        qtest_fields = []

        # Map environment if present
        if "environment" in zephyr_execution and zephyr_execution["environment"]:
            qtest_fields.append(
                {
                    "field_id": 0,
                    "field_name": "environment",
                    "field_type": "STRING",
                    "field_value": zephyr_execution["environment"],
                }
            )

        # Map actual time if present
        if "actualTime" in zephyr_execution and zephyr_execution["actualTime"]:
            qtest_fields.append(
                {
                    "field_id": 0,
                    "field_name": "actual_time",
                    "field_type": "NUMBER",
                    "field_value": zephyr_execution["actualTime"],
                }
            )

        # Map executed by if present
        if "executedBy" in zephyr_execution and zephyr_execution["executedBy"]:
            qtest_fields.append(
                {
                    "field_id": 0,
                    "field_name": "executed_by",
                    "field_type": "STRING",
                    "field_value": zephyr_execution["executedBy"],
                }
            )

        # Map execution date if present
        if "executedOn" in zephyr_execution and zephyr_execution["executedOn"]:
            qtest_fields.append(
                {
                    "field_id": 0,
                    "field_name": "execution_date",
                    "field_type": "DATE",
                    "field_value": str(zephyr_execution["executedOn"]),
                }
            )

        # Map defects if present
        if "defects" in zephyr_execution and zephyr_execution["defects"]:
            defects_str = ", ".join(
                [defect.get("key", "") for defect in zephyr_execution["defects"]]
            )
            if defects_str:
                qtest_fields.append(
                    {
                        "field_id": 0,
                        "field_name": "defects",
                        "field_type": "STRING",
                        "field_value": defects_str,
                    }
                )

        # Map custom fields
        if "customFields" in zephyr_execution and zephyr_execution["customFields"]:
            custom_fields = self.map_custom_fields(zephyr_execution["customFields"])
            qtest_fields.extend(custom_fields)

        return qtest_fields


def get_default_field_mapper() -> CustomFieldMapper:
    """
    Get the default field mapper instance.

    Returns:
        CustomFieldMapper: The default field mapper
    """
    return CustomFieldMapper()
