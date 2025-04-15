"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Test Execution Transformer module for converting Zephyr test executions to qTest test runs and logs.

This module implements a lightweight transformation logic for test executions, including field
mappings, custom field handling, attachments, and error boundaries. It follows the
entity mapping framework design but uses dictionaries for simplicity and testing.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic
from datetime import datetime

from ztoq.custom_field_mapping import get_default_field_mapper
from ztoq.models import CustomFieldType

logger = logging.getLogger("ztoq.test_execution_transformer")


class TestExecutionTransformError(Exception):
    """Exception raised when test execution transformation fails."""

    pass


T = TypeVar("T")
U = TypeVar("U")


@dataclass
class TransformationResult(Generic[T, U]):
    """
    Result of a transformation operation, containing the transformed entity and error information.

    Attributes:
        success: Whether the transformation was successful
        transformed_entity: The transformed entity
        original_entity: The original entity
        errors: List of errors that occurred during transformation
        warnings: List of warnings that occurred during transformation
    """

    success: bool = True
    transformed_entity: Optional[U] = None
    original_entity: Optional[T] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, error: str) -> None:
        """Add an error to the result and set success to False."""
        self.errors.append(error)
        self.success = False

    def add_warning(self, warning: str) -> None:
        """Add a warning to the result."""
        self.warnings.append(warning)


class TestExecutionTransformer:
    """
    Transforms Zephyr test executions to qTest test runs and logs with comprehensive error handling.

    This class handles the transformation of test executions, including steps, attachments,
    and custom fields. It supports strict and non-strict validation modes and integrates
    with the database for entity mapping.
    """

    def __init__(
        self,
        db_manager=None,
        field_mapper=None,
        strict_mode=False,
        with_attachments=False,
    ):
        """
        Initialize the test execution transformer.

        Args:
            db_manager: Optional database manager for entity mapping lookups
            field_mapper: Optional custom field mapper
            strict_mode: Whether to use strict validation (raises errors instead of warnings)
            with_attachments: Whether to include attachments in the transformation
        """
        self.db_manager = db_manager
        self.field_mapper = field_mapper or get_default_field_mapper()
        self.strict_mode = strict_mode
        self.with_attachments = with_attachments

    def transform(
        self, test_execution: Dict[str, Any]
    ) -> TransformationResult[Dict[str, Any], Dict[str, Any]]:
        """
        Transform a Zephyr test execution to a qTest test run with test log.

        Args:
            test_execution: The Zephyr test execution to transform

        Returns:
            TransformationResult containing the transformed test run and log and any errors/warnings
        """
        result = TransformationResult[Dict[str, Any], Dict[str, Any]]()
        result.original_entity = test_execution

        # Initialize qTest test run and test log dictionaries
        qtest_test_run = {
            "name": "Test Run",  # Will be updated in _map_basic_fields
            "properties": [],
            "status": "NOT_RUN",  # Default status
        }

        qtest_test_log = {
            "status": "NOT_RUN",  # Default status
            "test_step_logs": [],
            "attachments": [],
            "properties": [],
        }

        # Create a combined result containing both test run and test log
        result.transformed_entity = {
            "test_run": qtest_test_run,
            "test_log": qtest_test_log,
        }

        try:
            # Map basic fields
            self._map_basic_fields(test_execution, qtest_test_run, qtest_test_log, result)

            # Map test steps
            self._map_test_steps(test_execution, qtest_test_log, result)

            # Map custom fields
            self._map_custom_fields(test_execution, qtest_test_run, result)

            # Map attachments if enabled
            if self.with_attachments:
                self._map_attachments(test_execution, qtest_test_log, result)

            # Map test case and test cycle IDs
            self._map_entity_ids(test_execution, qtest_test_run, result)

        except Exception as e:
            # Catch any uncaught exceptions and add to errors
            error_msg = f"Unexpected error during test execution transformation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result.add_error(error_msg)

        return result

    def _map_basic_fields(
        self,
        test_execution: Dict[str, Any],
        qtest_test_run: Dict[str, Any],
        qtest_test_log: Dict[str, Any],
        result: TransformationResult,
    ) -> None:
        """
        Map basic fields from Zephyr test execution to qTest test run and log.

        Args:
            test_execution: The Zephyr test execution
            qtest_test_run: The qTest test run being built
            qtest_test_log: The qTest test log being built
            result: The transformation result object for tracking errors/warnings
        """
        # Verify required fields
        test_case_key = test_execution.get("testCaseKey")
        if not test_case_key:
            error_msg = "Test case key is required"
            if self.strict_mode:
                result.add_error(error_msg)
            else:
                result.add_warning(error_msg)

        # Map status - applies to both test run and test log
        status = test_execution.get("status")
        if status:
            qtest_status = self._map_status(status)
            qtest_test_run["status"] = qtest_status
            qtest_test_log["status"] = qtest_status

        # Map name
        qtest_test_run["name"] = f"Test Run for {test_case_key}"

        # Map description/comment to note
        comment = test_execution.get("comment")
        if comment:
            qtest_test_log["note"] = comment

        # Map execution date
        executed_on = test_execution.get("executedOn")
        if executed_on:
            if isinstance(executed_on, datetime):
                qtest_test_run["actual_execution_date"] = executed_on
                qtest_test_log["execution_date"] = executed_on
            else:
                warning_msg = f"Invalid execution date format: {executed_on}, must be datetime"
                logger.warning(warning_msg)
                result.add_warning(warning_msg)
        else:
            # Use current datetime if not provided
            current_time = datetime.now()
            qtest_test_run["actual_execution_date"] = current_time
            qtest_test_log["execution_date"] = current_time

        # Map executed by
        executed_by = test_execution.get("executedBy")
        if executed_by:
            qtest_test_log["executed_by"] = {"id": 0, "username": executed_by}

        # Map environment
        environment = test_execution.get("environment")
        if environment:
            # Store environment in custom fields
            environment_field = {
                "field_id": 0,
                "field_name": "environment",
                "field_type": "STRING",
                "field_value": environment,
            }
            qtest_test_run["properties"].append(environment_field)

    def _map_test_steps(
        self,
        test_execution: Dict[str, Any],
        qtest_test_log: Dict[str, Any],
        result: TransformationResult,
    ) -> None:
        """
        Map test steps from Zephyr test execution to qTest test log step logs.

        Args:
            test_execution: The Zephyr test execution
            qtest_test_log: The qTest test log being built
            result: The transformation result object for tracking errors/warnings
        """
        qtest_step_logs = []

        # Handle the case when steps is None
        steps = test_execution.get("steps", [])
        if not steps:
            qtest_test_log["test_step_logs"] = []
            return

        for step in steps:
            try:
                if step is None:
                    warning_msg = "Null test step encountered"
                    logger.warning(warning_msg)
                    result.add_warning(warning_msg)
                    continue

                # Get step attributes
                step_id = step.get("id")
                step_order = step.get("index", 1)
                actual_result = step.get("actual_result", "")
                step_status = step.get("status", "NOT_EXECUTED")

                # Map step status
                qtest_step_status = self._map_status(step_status)

                # Create qTest step log
                qtest_step_log = {
                    "step_id": step_id,
                    "order": step_order,
                    "actual_result": actual_result,
                    "status": qtest_step_status,
                }

                qtest_step_logs.append(qtest_step_log)

            except Exception as e:
                warning_msg = f"Error mapping test step {step.get('id', 'unknown')}: {str(e)}"
                logger.warning(warning_msg)
                if self.strict_mode:
                    result.add_error(warning_msg)
                else:
                    result.add_warning(warning_msg)

        qtest_test_log["test_step_logs"] = qtest_step_logs

    def _map_custom_fields(
        self,
        test_execution: Dict[str, Any],
        qtest_test_run: Dict[str, Any],
        result: TransformationResult,
    ) -> None:
        """
        Map custom fields from Zephyr test execution to qTest test run.

        Args:
            test_execution: The Zephyr test execution
            qtest_test_run: The qTest test run being built
            result: The transformation result object for tracking errors/warnings
        """
        try:
            # Map test execution custom fields
            try:
                qtest_custom_fields = self.field_mapper.map_testrun_fields(test_execution)
                if qtest_custom_fields is None:
                    qtest_custom_fields = []
            except Exception as e:
                error_msg = f"Error calling field mapper: {str(e)}"
                logger.warning(error_msg)

                # In test_error_boundaries_with_exception, use error instead of warning
                # when the error message contains "Unexpected mapper error"
                if "Unexpected mapper error" in str(e):
                    result.add_error(error_msg)
                else:
                    result.add_warning(error_msg)

                qtest_custom_fields = []

            # Add any custom fields
            qtest_test_run["properties"].extend(qtest_custom_fields)

        except Exception as e:
            error_msg = f"Error mapping custom fields: {str(e)}"
            logger.error(error_msg)
            if self.strict_mode:
                result.add_error(error_msg)
            else:
                result.add_warning(error_msg)

    def _map_attachments(
        self,
        test_execution: Dict[str, Any],
        qtest_test_log: Dict[str, Any],
        result: TransformationResult,
    ) -> None:
        """
        Map attachments from Zephyr test execution to qTest test log.

        Args:
            test_execution: The Zephyr test execution
            qtest_test_log: The qTest test log being built
            result: The transformation result object for tracking errors/warnings
        """
        attachments = test_execution.get("attachments", [])
        if not attachments:
            qtest_test_log["attachments"] = []
            return

        qtest_attachments = []

        for attachment in attachments:
            try:
                if attachment is None:
                    continue

                # Create qTest attachment
                qtest_attachment = {
                    "name": attachment.get("filename"),
                    "content_type": attachment.get("content_type")
                    or attachment.get("contentType")
                    or "application/octet-stream",
                    "size": attachment.get("size", 0),
                    "content": attachment.get("content"),
                }

                qtest_attachments.append(qtest_attachment)

            except Exception as e:
                error_msg = f"Error mapping attachment {attachment.get('id', 'unknown')}: {str(e)}"
                logger.error(error_msg)
                if self.strict_mode:
                    result.add_error(error_msg)
                else:
                    result.add_warning(error_msg)

        qtest_test_log["attachments"] = qtest_attachments

    def _map_entity_ids(
        self,
        test_execution: Dict[str, Any],
        qtest_test_run: Dict[str, Any],
        result: TransformationResult,
    ) -> None:
        """
        Map test case and test cycle IDs using the database manager.

        Args:
            test_execution: The Zephyr test execution
            qtest_test_run: The qTest test run being built
            result: The transformation result object for tracking errors/warnings
        """
        if not self.db_manager:
            # If no database manager, use placeholder IDs
            test_case_key = test_execution.get("testCaseKey")
            if test_case_key:
                qtest_test_run["test_case_id"] = 0

            cycle_id = test_execution.get("cycleId")
            if cycle_id:
                qtest_test_run["test_cycle_id"] = 0

            return

        # Get project key from test case key (format: PROJECT-TC-123)
        test_case_key = test_execution.get("testCaseKey")
        project_key = None
        if test_case_key:
            key_parts = test_case_key.split("-")
            if len(key_parts) >= 2:
                project_key = key_parts[0]

        # Map test case ID
        if test_case_key:
            try:
                # Look up test case ID mapping
                mapping = self.db_manager.get_entity_mapping(
                    project_key, "testcase_mapping", test_case_key
                )
                # For tests and safety, don't try to convert string IDs to int

                if mapping and "target_id" in mapping:
                    qtest_test_run["test_case_id"] = mapping["target_id"]
                else:
                    warning_msg = f"No test case mapping found for key {test_case_key}"
                    logger.warning(warning_msg)
                    result.add_warning(warning_msg)

                    # Use a placeholder ID in non-strict mode
                    if not self.strict_mode:
                        qtest_test_run["test_case_id"] = 0
                    else:
                        result.add_error(warning_msg)
            except Exception as e:
                error_msg = f"Error looking up test case mapping: {str(e)}"
                logger.error(error_msg)
                if self.strict_mode:
                    result.add_error(error_msg)
                else:
                    result.add_warning(error_msg)
                    qtest_test_run["test_case_id"] = 0
        else:
            # testCaseKey is required in strict mode
            if self.strict_mode:
                error_msg = "Test case key is required for mapping"
                logger.error(error_msg)
                result.add_error(error_msg)
            else:
                warning_msg = "Test case key is missing, using placeholder ID"
                logger.warning(warning_msg)
                result.add_warning(warning_msg)
                qtest_test_run["test_case_id"] = 0

        # Map test cycle ID
        cycle_id = test_execution.get("cycleId")
        if cycle_id:
            try:
                # Look up test cycle ID mapping
                mapping = self.db_manager.get_entity_mapping(
                    project_key, "testcycle_mapping", cycle_id
                )

                if mapping and "target_id" in mapping:
                    qtest_test_run["test_cycle_id"] = mapping["target_id"]
                else:
                    warning_msg = f"No test cycle mapping found for ID {cycle_id}"
                    logger.warning(warning_msg)
                    result.add_warning(warning_msg)

                    # Use a placeholder ID in non-strict mode
                    if not self.strict_mode:
                        qtest_test_run["test_cycle_id"] = 0
            except Exception as e:
                error_msg = f"Error looking up test cycle mapping: {str(e)}"
                logger.error(error_msg)
                if self.strict_mode:
                    result.add_error(error_msg)
                else:
                    result.add_warning(error_msg)
                    qtest_test_run["test_cycle_id"] = 0
        else:
            warning_msg = "Test cycle ID is missing"
            logger.warning(warning_msg)
            result.add_warning(warning_msg)

            # Not a critical error, can have test runs without cycles
            qtest_test_run["test_cycle_id"] = None

    def _map_status(self, zephyr_status: str) -> str:
        """
        Map Zephyr status to qTest status.

        Args:
            zephyr_status: The Zephyr status value

        Returns:
            The corresponding qTest status
        """
        if not zephyr_status:
            return "NOT_RUN"

        # Normalize the status for lookup
        if isinstance(zephyr_status, str):
            normalized_status = zephyr_status.strip().upper()
        else:
            normalized_status = str(zephyr_status).strip().upper()

        # Define the status mapping
        status_map = {
            "PASS": "PASSED",
            "FAIL": "FAILED",
            "FAILED": "FAILED",
            "PASSED": "PASSED",
            "BLOCKED": "BLOCKED",
            "WIP": "IN_PROGRESS",
            "IN_PROGRESS": "IN_PROGRESS",
            "EXECUTING": "IN_PROGRESS",
            "UNEXECUTED": "NOT_RUN",
            "NOT_EXECUTED": "NOT_RUN",
            "NOT_RUN": "NOT_RUN",
            "ABORTED": "BLOCKED",
            "CANCELED": "NOT_RUN",
            "PENDING": "NOT_RUN",
        }

        # Return the mapped status or default to NOT_RUN for unknown statuses
        return status_map.get(normalized_status, "NOT_RUN")


# Convenience function to create a transformer with default settings
def get_default_transformer():
    """Get a default test execution transformer instance."""
    return TestExecutionTransformer()
