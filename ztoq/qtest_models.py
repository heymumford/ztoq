"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
qTest Models module.

This module provides Pydantic models for qTest entities including:
- qTest Manager: projects, modules, test cases, test cycles, etc.
- qTest Parameters: parameters, parameter values, datasets, etc.
- qTest Pulse: rules, actions, triggers, constants, etc.
- qTest Scenario: features, scenarios, steps, etc.
"""

import base64
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, ClassVar
from pydantic import BaseModel, Field, root_validator, validator

class QTestConfig(BaseModel):
    """Configuration for qTest API."""

    base_url: str = Field(..., description="Base URL for qTest API (e.g., https://example.qtest.com)")
    username: str = Field(..., description="Username for qTest authentication")
    password: str = Field(..., description="Password for qTest authentication")
    project_id: int = Field(..., description="Project ID to work with", gt=0)

    @validator('base_url')
    def validate_base_url(cls, value):
        """Validate base URL format."""
        if not value.startswith(('http://', 'https://')):
            raise ValueError('base_url must start with http:// or https://')
        return value


class QTestPaginatedResponse(BaseModel):
    """Represents a paginated response from the qTest API."""

    items: list[dict[str, Any]] = Field(default_factory=list)
    page: int | None = None
    page_size: int | None = None
    offset: int | None = None
    limit: int | None = None
    total: int
    is_last: bool


class QTestLink(BaseModel):
    """
    Represents a link in qTest.

    In qTest, links can be associated with various entities such as
    test cases, test cycles, and test executions.
    """

    id: int | None = Field(None, description="Link ID in qTest system")
    name: str = Field(..., description="Display name for the link", min_length=1, max_length=255)
    url: str = Field(..., description="URL for the link")
    icon_url: str | None = Field(None, description="URL for the link icon", alias="iconUrl")
    target: str | None = Field(None, description="Target for the link (e.g., '_blank')")

    @validator('url')
    def validate_url(cls, value):
        """Validate URL format."""
        if not value.startswith(('http://', 'https://')):
            raise ValueError('url must start with http:// or https://')
        return value

    model_config = {"populate_by_name": True}


class QTestCustomField(BaseModel):
    """
    Represents a custom field in qTest.

    qTest supports various field types including STRING, NUMBER, CHECKBOX, DATE, DATETIME,
    USER, MULTI_VALUE, and more. The field_value type depends on the field_type.
    """

    field_id: int = Field(..., alias="id", description="Unique identifier for the custom field")
    field_name: str = Field(..., alias="name", description="Name of the custom field", min_length=1)
    field_type: str = Field(..., alias="type", description="Data type of the custom field")
    field_value: Any | None = Field(None, alias="value", description="Value of the custom field")
    is_required: bool | None = Field(None, alias="required", description="Whether the field is required")

    # List of supported custom field types in qTest
    SUPPORTED_TYPES: ClassVar[list[str]] = [
        "STRING", "NUMBER", "CHECKBOX", "DATE", "DATETIME", "USER", "MULTI_USER",
        "MULTI_VALUE", "RICH_TEXT", "TREE", "TABLE"
    ]

    @validator('field_type')
    def validate_field_type(cls, v):
        """Validate that the field type is supported."""
        v_upper = v.upper()
        if v_upper not in cls.SUPPORTED_TYPES:
            raise ValueError(f"Field type '{v}' is not supported. Must be one of: {', '.join(cls.SUPPORTED_TYPES)}")
        return v_upper

    @root_validator(skip_on_failure=True)
    def validate_field_value(cls, values):
        """Validate that the field value matches the field type."""
        field_type = values.get('field_type')
        field_value = values.get('field_value')

        if field_value is not None and field_type:
            if field_type == "NUMBER" and not isinstance(field_value, (int, float)):
                raise ValueError(f"Field value for NUMBER type must be numeric, got {type(field_value).__name__}")
            elif field_type == "CHECKBOX" and not isinstance(field_value, bool):
                raise ValueError(f"Field value for CHECKBOX type must be boolean, got {type(field_value).__name__}")
            elif field_type in ["DATE", "DATETIME"] and not isinstance(field_value, (str, datetime)):
                raise ValueError(f"Field value for {field_type} type must be datetime or string, got {type(field_value).__name__}")

        return values

    model_config = {"populate_by_name": True}


class QTestAttachment(BaseModel):
    """
    Represents a file attachment in qTest.

    Attachments in qTest can be associated with various entities including
    test cases, test runs, and defects. They can be binary files like
    screenshots, logs, or documents.
    """

    id: int | None = Field(None, description="Attachment ID in qTest")
    name: str = Field(..., description="Filename of the attachment", min_length=1, max_length=255)
    content_type: str = Field(..., alias="contentType", description="MIME type of the attachment")
    size: int | None = Field(None, description="Size of the attachment in bytes")
    created_date: datetime | None = Field(None, alias="createdDate", description="Date when the attachment was created")
    created_by: dict | None = Field(None, alias="createdBy", description="User who created the attachment")
    web_url: str | None = Field(None, alias="webUrl", description="URL to access the attachment in qTest web UI")

    model_config = {"populate_by_name": True}

    @validator('name')
    def validate_name(cls, value):
        """Validate that attachment name has a valid extension."""
        if not '.' in value:
            raise ValueError("Attachment name must include a file extension")
        return value

    @validator('content_type')
    def validate_content_type(cls, value):
        """Validate content type format."""
        if not '/' in value:
            raise ValueError("Content type must be in format 'type/subtype', e.g. 'image/png'")
        return value

    @classmethod
    def from_binary(cls, name: str, content_type: str, binary_data: bytes):
        """
        Create an attachment from binary data.

        Args:
            name: Filename of the attachment
            content_type: MIME type of the attachment
            binary_data: Binary content of the attachment

        Returns:
            Dictionary representation of the attachment suitable for API upload
        """
        encoded = base64.b64encode(binary_data).decode("utf-8")
        return {
            "name": name,
            "contentType": content_type,
            "size": len(binary_data),
            "data": encoded
        }


class QTestProject(BaseModel):
    """
    Represents a qTest project.

    Projects in qTest are the top-level organizational unit that contain all test assets
    including test cases, test cycles, test runs, and requirements.
    """

    id: int = Field(..., description="Unique identifier for the project")
    name: str = Field(..., description="Name of the project", min_length=1, max_length=255)
    description: str | None = Field(None, description="Description of the project")
    start_date: datetime | None = Field(None, alias="startDate", description="Project start date")
    end_date: datetime | None = Field(None, alias="endDate", description="Project end date")
    status_name: str | None = Field(None, alias="statusName", description="Status of the project (e.g., Active, Inactive)")
    created_date: datetime | None = Field(None, alias="createdDate", description="Date when the project was created")
    created_by: dict | None = Field(None, alias="createdBy", description="User who created the project")
    updated_date: datetime | None = Field(None, alias="updatedDate", description="Date when the project was last updated")
    updated_by: dict | None = Field(None, alias="updatedBy", description="User who last updated the project")
    avatar_path: str | None = Field(None, alias="avatarPath", description="Path to project avatar image")

    # Project statuses supported by qTest
    VALID_STATUSES: ClassVar[list[str]] = ["Active", "Inactive", "Completed", "Archived"]

    @validator('status_name')
    def validate_status_name(cls, v):
        """Validate project status."""
        if v is not None and v not in cls.VALID_STATUSES:
            raise ValueError(f"Status '{v}' is not valid. Must be one of: {', '.join(cls.VALID_STATUSES)}")
        return v

    @root_validator(skip_on_failure=True)
    def validate_dates(cls, values):
        """Validate that start_date is before end_date."""
        start_date = values.get('start_date')
        end_date = values.get('end_date')

        if start_date and end_date and start_date > end_date:
            raise ValueError("start_date must be before end_date")

        return values

    model_config = {"populate_by_name": True}


class QTestModule(BaseModel):
    """
    Represents a qTest module.

    Modules in qTest are containers for organizing test assets hierarchically.
    They can be nested to create a folder-like structure for test organization.
    """

    id: int | None = Field(None, description="Unique identifier for the module")
    name: str = Field(..., description="Name of the module", min_length=1, max_length=255)
    description: str | None = Field(None, description="Description of the module")
    parent_id: int | None = Field(None, alias="parentId", description="ID of the parent module (for nested modules)")
    pid: str | None = Field(None, description="Project-specific ID (e.g., 'MD-123')")
    project_id: int | None = Field(None, alias="projectId", description="ID of the project containing this module")
    path: str | None = Field(None, description="Full path to the module in the hierarchy")

    @validator('name')
    def validate_name(cls, value):
        """Validate module name isn't empty or just whitespace."""
        if value.strip() == "":
            raise ValueError("Module name cannot be empty or only whitespace")
        return value

    model_config = {"populate_by_name": True}


class QTestField(BaseModel):
    """
    Represents a field in qTest.

    Fields define the structure of data in qTest. They can be system fields
    that are built-in to qTest or custom fields created by users. Each field
    has a type, entity association, and optional validation rules.
    """

    id: int = Field(..., description="Unique identifier for the field")
    name: str = Field(..., description="API name of the field", min_length=1)
    label: str = Field(..., description="Display label of the field", min_length=1)
    field_type: str = Field(..., alias="fieldType", description="Data type of the field")
    entity_type: str = Field(..., alias="entityType", description="Entity type this field applies to")
    allowed_values: list[str] | None = Field(None, alias="allowedValues", description="List of allowed values for this field")
    required: bool = Field(False, description="Whether the field is required when creating/updating entities")

    # Valid field types in qTest
    VALID_FIELD_TYPES: ClassVar[list[str]] = [
        "STRING", "NUMBER", "CHECKBOX", "DATE", "DATETIME", "USER", "MULTI_USER",
        "MULTI_VALUE", "RICH_TEXT", "TREE", "TABLE"
    ]

    # Valid entity types in qTest
    VALID_ENTITY_TYPES: ClassVar[list[str]] = [
        "TEST_CASE", "TEST_CYCLE", "TEST_RUN", "TEST_LOG", "REQUIREMENT", "DEFECT", "RELEASE"
    ]

    @validator('field_type')
    def validate_field_type(cls, v):
        """Validate that field type is supported."""
        v_upper = v.upper()
        if v_upper not in cls.VALID_FIELD_TYPES:
            raise ValueError(f"Field type '{v}' is not valid. Must be one of: {', '.join(cls.VALID_FIELD_TYPES)}")
        return v_upper

    @validator('entity_type')
    def validate_entity_type(cls, v):
        """Validate that entity type is supported."""
        v_upper = v.upper()
        if v_upper not in cls.VALID_ENTITY_TYPES:
            raise ValueError(f"Entity type '{v}' is not valid. Must be one of: {', '.join(cls.VALID_ENTITY_TYPES)}")
        return v_upper

    model_config = {"populate_by_name": True}


class QTestStep(BaseModel):
    """
    Represents a test step in qTest.

    Test steps define the procedural steps to execute a test case. Each step
    includes a description of the action to take and the expected result
    of that action. Steps are ordered sequentially.
    """

    id: int | None = Field(None, description="Unique identifier for the test step")
    description: str = Field(..., description="Description of the action to take in this step", min_length=1)
    expected_result: str | None = Field(None, alias="expectedResult", description="Expected outcome of this step")
    order: int = Field(..., description="Sequential order of this step in the test case", ge=1)
    attachments: list[QTestAttachment] = Field(default_factory=list, description="Attachments related to this step")

    @validator('description')
    def validate_description(cls, value):
        """Validate step description isn't empty or just whitespace."""
        if value.strip() == "":
            raise ValueError("Step description cannot be empty or only whitespace")
        return value

    @validator('expected_result')
    def validate_expected_result(cls, value):
        """Validate expected result if provided."""
        if value is not None and value.strip() == "":
            raise ValueError("Expected result cannot be empty or only whitespace if provided")
        return value

    model_config = {"populate_by_name": True}


class QTestAutomationSettings(BaseModel):
    """
    Represents automation settings for a test case in qTest.

    Automated test cases in qTest can be linked to test automation frameworks
    and have specific automation identifiers to connect manual test cases
    with their automated implementation.
    """

    automation_id: str | None = Field(None, alias="automationId", description="ID used in the automation framework to identify this test")
    framework_id: int | None = Field(None, alias="frameworkId", description="ID of the automation framework used for this test")
    framework_name: str | None = Field(None, alias="frameworkName", description="Name of the automation framework")
    parameters: dict[str, str] | None = Field(None, description="Custom parameters for automated execution")
    is_parameterized: bool | None = Field(None, alias="isParameterized", description="Whether the automated test accepts parameters")
    external_id: str | None = Field(None, alias="externalId", description="External system ID for this test")

    @validator('automation_id')
    def validate_automation_id(cls, value):
        """Validate automation ID format if provided."""
        if value is not None and value.strip() == "":
            raise ValueError("Automation ID cannot be empty or only whitespace if provided")
        return value

    model_config = {"populate_by_name": True}


class QTestTestCase(BaseModel):
    """
    Represents a test case in qTest.

    Test cases are the primary testing units in qTest. They define what to test,
    how to test it, and what the expected results are. They can include test steps,
    preconditions, and custom fields.
    """

    id: int | None = Field(None, description="Unique identifier for the test case")
    pid: str | None = Field(None, description="Project-specific ID (e.g., 'TC-123')")
    name: str = Field(..., description="Name of the test case", min_length=1)
    description: str | None = Field(None, description="Detailed description of the test case")
    precondition: str | None = Field(None, description="Prerequisites for running the test case")
    test_steps: list[QTestStep] = Field(default_factory=list, alias="steps", description="Steps to execute the test case")
    properties: list[QTestCustomField] | None = Field(default_factory=list, description="Custom fields associated with the test case")
    parent_id: int | None = Field(None, alias="parentId", description="ID of the parent test case (for hierarchical test cases)")
    module_id: int | None = Field(None, alias="moduleId", description="ID of the module containing this test case")
    priority_id: int | None = Field(None, alias="priorityId", description="Priority of the test case")
    creator_id: int | None = Field(None, alias="creatorId", description="ID of the user who created the test case")
    attachments: list[QTestAttachment] = Field(default_factory=list, description="Attachments associated with the test case")
    create_date: datetime | None = Field(None, alias="createdDate", description="Date when the test case was created")
    last_modified_date: datetime | None = Field(None, alias="lastModifiedDate", description="Date when the test case was last updated")
    automation: QTestAutomationSettings | None = Field(None, description="Automation settings for the test case")
    shared: bool | None = Field(None, description="Whether the test case is shared across projects")
    test_case_version_id: int | None = Field(None, alias="testCaseVersionId", description="ID of the test case version")
    version: int | None = Field(None, description="Version number of the test case")

    # Additional fields for test case creation/update
    project_id: int | None = Field(None, alias="projectId", description="ID of the project containing the test case")
    origin: str | None = Field(None, description="Origin of the test case")

    @root_validator(skip_on_failure=True)
    def validate_test_steps(cls, values):
        """Validate that test steps have sequential order."""
        test_steps = values.get('test_steps')

        if test_steps and len(test_steps) > 1:
            # Check that step orders are sequential
            step_orders = [step.order for step in test_steps if step.order is not None]
            if step_orders and len(step_orders) > 1:
                for i in range(1, len(step_orders)):
                    if step_orders[i] <= step_orders[i-1]:
                        raise ValueError("Test step orders must be sequential and increasing")

        return values

    model_config = {"populate_by_name": True}


class QTestRelease(BaseModel):
    """
    Represents a release in qTest.

    Releases in qTest represent software delivery milestones. They contain test cycles
    and are used for organizing testing activities around product releases.
    """

    id: int | None = Field(None, description="Unique identifier for the release")
    name: str = Field(..., description="Name of the release", min_length=1, max_length=255)
    description: str | None = Field(None, description="Detailed description of the release")
    pid: str | None = Field(None, description="Project-specific ID (e.g., 'RL-123')")
    project_id: int | None = Field(None, alias="projectId", description="ID of the project containing this release")
    start_date: datetime | None = Field(None, alias="startDate", description="Planned start date for the release")
    end_date: datetime | None = Field(None, alias="endDate", description="Planned end date for the release")
    status: str | None = Field(None, description="Status of the release (e.g., Planning, In Progress, Completed)")
    created_date: datetime | None = Field(None, alias="createdDate", description="Date when the release was created")
    created_by: dict | None = Field(None, alias="createdBy", description="User who created the release")

    # Common release statuses in qTest
    VALID_STATUSES: ClassVar[list[str]] = ["Planning", "In Progress", "Completed", "Cancelled", "Delayed"]

    @validator('name')
    def validate_name(cls, value):
        """Validate release name isn't empty or just whitespace."""
        if value.strip() == "":
            raise ValueError("Release name cannot be empty or only whitespace")
        return value

    @validator('status')
    def validate_status(cls, value):
        """Validate release status if provided."""
        if value is not None and value not in cls.VALID_STATUSES:
            raise ValueError(f"Status '{value}' is not valid. Common statuses are: {', '.join(cls.VALID_STATUSES)}")
        return value

    @root_validator(skip_on_failure=True)
    def validate_dates(cls, values):
        """Validate that start_date is before end_date."""
        start_date = values.get('start_date')
        end_date = values.get('end_date')

        if start_date and end_date and start_date > end_date:
            raise ValueError("start_date must be before end_date")

        return values

    model_config = {"populate_by_name": True}


class QTestTestCycle(BaseModel):
    """
    Represents a test cycle in qTest.

    Test cycles are containers for organizing test executions. They represent a specific
    testing phase or iteration and can be associated with releases. Test cycles can
    contain test runs and can be nested hierarchically.
    """

    id: int | None = Field(None, description="Unique identifier for the test cycle")
    name: str = Field(..., description="Name of the test cycle", min_length=1, max_length=255)
    description: str | None = Field(None, description="Detailed description of the test cycle")
    parent_id: int | None = Field(None, alias="parentId", description="ID of the parent test cycle (for nested cycles)")
    pid: str | None = Field(None, description="Project-specific ID (e.g., 'CY-123')")
    release_id: int | None = Field(None, alias="releaseId", description="ID of the release containing this test cycle")
    project_id: int | None = Field(None, alias="projectId", description="ID of the project containing this test cycle")
    properties: list[QTestCustomField] | None = Field(default_factory=list, description="Custom fields associated with the test cycle")
    start_date: datetime | None = Field(None, alias="startDate", description="Planned start date for the test cycle")
    end_date: datetime | None = Field(None, alias="endDate", description="Planned end date for the test cycle")
    creator_id: int | None = Field(None, alias="creatorId", description="ID of the user who created the test cycle")
    created_date: datetime | None = Field(None, alias="createdDate", description="Date when the test cycle was created")
    last_modified_date: datetime | None = Field(None, alias="lastModifiedDate", description="Date when the test cycle was last updated")
    status: str | None = Field(None, description="Status of the test cycle")

    # Common test cycle statuses in qTest
    VALID_STATUSES: ClassVar[list[str]] = ["Not Started", "In Progress", "Completed", "Blocked", "Deferred"]

    @validator('name')
    def validate_name(cls, value):
        """Validate test cycle name isn't empty or just whitespace."""
        if value.strip() == "":
            raise ValueError("Test cycle name cannot be empty or only whitespace")
        return value

    @validator('status')
    def validate_status(cls, value):
        """Validate test cycle status if provided."""
        if value is not None and value not in cls.VALID_STATUSES:
            raise ValueError(f"Status '{value}' is not valid. Common statuses are: {', '.join(cls.VALID_STATUSES)}")
        return value

    @root_validator(skip_on_failure=True)
    def validate_dates(cls, values):
        """Validate that start_date is before end_date."""
        start_date = values.get('start_date')
        end_date = values.get('end_date')

        if start_date and end_date and start_date > end_date:
            raise ValueError("start_date must be before end_date")

        return values

    model_config = {"populate_by_name": True}


class QTestTestRun(BaseModel):
    """
    Represents a test run in qTest.

    Test runs are instances of test cases scheduled for execution. They represent
    specific executions of test cases within test cycles and track the execution
    status, assigned testers, and test logs.
    """

    id: int | None = Field(None, description="Unique identifier for the test run")
    name: str | None = Field(None, description="Name of the test run (often derived from test case)")
    description: str | None = Field(None, description="Detailed description of the test run")
    pid: str | None = Field(None, description="Project-specific ID (e.g., 'TR-123')")
    test_case_version_id: int | None = Field(None, alias="testCaseVersionId", description="ID of the test case version this run is based on")
    test_case_id: int | None = Field(None, alias="testCaseId", description="ID of the test case this run is based on")
    test_cycle_id: int | None = Field(None, alias="testCycleId", description="ID of the test cycle containing this run")
    project_id: int | None = Field(None, alias="projectId", description="ID of the project containing this test run")
    properties: list[QTestCustomField] | None = Field(default_factory=list, description="Custom fields associated with the test run")
    status: str | None = Field(None, description="Current status of the test run (e.g., Not Run, Passed, Failed)")
    assigned_to: dict | None = Field(None, alias="assignedTo", description="User assigned to execute this test run")
    created_date: datetime | None = Field(None, alias="createdDate", description="Date when the test run was created")
    created_by: dict | None = Field(None, alias="createdBy", description="User who created the test run")
    planned_execution_date: datetime | None = Field(None, alias="plannedExecutionDate", description="Planned date for execution")
    actual_execution_date: datetime | None = Field(None, alias="actualExecutionDate", description="Actual date of execution")
    latest_test_log_id: int | None = Field(None, alias="latestTestLogId", description="ID of the most recent test log for this run")

    # Common test run statuses in qTest
    VALID_STATUSES: ClassVar[list[str]] = ["Not Run", "Passed", "Failed", "Blocked", "Incomplete", "Skipped"]

    @validator('status')
    def validate_status(cls, value):
        """Validate test run status if provided."""
        if value is not None and value not in cls.VALID_STATUSES:
            raise ValueError(f"Status '{value}' is not valid. Common statuses are: {', '.join(cls.VALID_STATUSES)}")
        return value

    @root_validator(skip_on_failure=True)
    def validate_required_fields_for_creation(cls, values):
        """Validate that either test_case_id or test_case_version_id is provided for new test runs."""
        if values.get('id') is None:  # Only validate for new test runs (no ID yet)
            test_case_id = values.get('test_case_id')
            test_case_version_id = values.get('test_case_version_id')

            if test_case_id is None and test_case_version_id is None:
                raise ValueError("Either test_case_id or test_case_version_id must be provided for new test runs")

            if values.get('test_cycle_id') is None:
                raise ValueError("test_cycle_id is required for new test runs")

        return values

    model_config = {"populate_by_name": True}


class QTestTestLog(BaseModel):
    """
    Represents a test log in qTest.

    Test logs record the results of test run executions. They capture the status,
    execution date, notes, and any attachments associated with a specific test run
    execution instance. A test run can have multiple test logs representing its
    execution history.
    """

    id: int | None = Field(None, description="Unique identifier for the test log")
    status: str = Field(..., description="Status of the test execution (e.g., Passed, Failed)")
    execution_date: datetime | None = Field(None, alias="executionDate", description="Date and time of execution")
    note: str | None = Field(None, description="Notes or comments about the test execution")
    attachments: list[QTestAttachment] = Field(default_factory=list, description="Attachments related to the test execution")
    properties: list[QTestCustomField] | None = Field(default_factory=list, description="Custom fields associated with the test log")
    test_run_id: int | None = Field(None, alias="testRunId", description="ID of the test run this log belongs to")
    executed_by: dict | None = Field(None, alias="executedBy", description="User who executed the test")
    defects: list[dict] | None = Field(default_factory=list, description="Defects associated with this test execution")
    test_step_logs: list[dict] | None = Field(None, alias="testStepLogs", description="Logs for individual test steps")
    actual_results: str | None = Field(None, alias="actualResults", description="Overall actual results of the test execution")

    # Valid test execution statuses in qTest
    VALID_STATUSES: ClassVar[list[str]] = ["Passed", "Failed", "Blocked", "Incomplete", "Skipped", "Unexecuted"]

    @validator('status')
    def validate_status(cls, value):
        """Validate test execution status."""
        if value not in cls.VALID_STATUSES:
            raise ValueError(f"Status '{value}' is not valid. Must be one of: {', '.join(cls.VALID_STATUSES)}")
        return value

    @validator('note')
    def validate_note(cls, value):
        """Validate note field if provided."""
        if value is not None and value.strip() == "":
            raise ValueError("Note cannot be empty or only whitespace if provided")
        return value

    @root_validator(skip_on_failure=True)
    def validate_required_fields_for_creation(cls, values):
        """Validate that test_run_id is provided for new test logs."""
        if values.get('id') is None:  # Only validate for new test logs (no ID yet)
            if values.get('test_run_id') is None:
                raise ValueError("test_run_id is required for new test logs")

            if values.get('execution_date') is None:
                # Set execution date to current time if not provided
                values['execution_date'] = datetime.now()

        return values

    model_config = {"populate_by_name": True}


class QTestTestExecution(BaseModel):
    """
    Represents a test execution in qTest.

    Test executions are similar to test logs but provide a more structured format
    for recording test run results, particularly focused on test step execution
    status and results. This model is especially useful for API-driven test
    automation integrations.
    """

    id: int | None = Field(None, description="Unique identifier for the test execution")
    test_run_id: int = Field(..., alias="testRunId", description="ID of the test run this execution belongs to", gt=0)
    status: str = Field(..., description="Overall status of the test execution (e.g., Passed, Failed)")
    execution_date: datetime = Field(..., alias="executionDate", description="Date and time of execution")
    executed_by: int | None = Field(None, alias="executedBy", description="ID of the user who executed the test")
    note: str | None = Field(None, description="Notes or comments about the test execution")
    attachments: list[QTestAttachment] = Field(default_factory=list, description="Attachments related to the test execution")
    test_step_logs: list[dict[str, Any]] | None = Field(None, alias="testStepLogs", description="Logs for individual test steps")
    build: str | None = Field(None, description="Build version tested in this execution")
    build_url: str | None = Field(None, alias="buildUrl", description="URL to the build used for this execution")
    duration: int | None = Field(None, description="Duration of the test execution in milliseconds", ge=0)

    # Valid test execution statuses in qTest
    VALID_STATUSES: ClassVar[list[str]] = ["Passed", "Failed", "Blocked", "Incomplete", "Skipped", "Unexecuted"]

    @validator('status')
    def validate_status(cls, value):
        """Validate test execution status."""
        if value not in cls.VALID_STATUSES:
            raise ValueError(f"Status '{value}' is not valid. Must be one of: {', '.join(cls.VALID_STATUSES)}")
        return value

    @validator('test_step_logs')
    def validate_test_step_logs(cls, value):
        """Validate test step logs format if provided."""
        if value is not None:
            for i, step_log in enumerate(value):
                if not isinstance(step_log, dict):
                    raise ValueError(f"Step log at index {i} must be a dictionary")

                # Required fields for step logs
                required_fields = ["stepId", "status"]
                for field in required_fields:
                    if field not in step_log:
                        raise ValueError(f"Step log at index {i} missing required field '{field}'")

                # Validate step status
                if "status" in step_log and step_log["status"] not in cls.VALID_STATUSES:
                    raise ValueError(f"Step log at index {i} has invalid status '{step_log['status']}'")

        return value

    @validator('build_url')
    def validate_build_url(cls, value):
        """Validate build URL format if provided."""
        if value is not None and not value.startswith(('http://', 'https://')):
            raise ValueError('build_url must start with http:// or https://')
        return value

    model_config = {"populate_by_name": True}


class QTestParameterValue(BaseModel):
    """
    Represents a parameter value in qTest Parameters.

    Parameter values are specific options or values associated with a parameter.
    For example, a "Browser" parameter might have values like "Chrome", "Firefox", etc.
    """

    id: int | None = Field(None, description="Unique identifier for the parameter value")
    value: str = Field(..., description="The actual value", min_length=1)
    parameter_id: int | None = Field(None, alias="parameterId", description="ID of the parameter this value belongs to")

    @validator('value')
    def validate_value(cls, value):
        """Validate parameter value isn't empty or just whitespace."""
        if value.strip() == "":
            raise ValueError("Parameter value cannot be empty or only whitespace")
        return value

    model_config = {"populate_by_name": True}


class QTestParameter(BaseModel):
    """
    Represents a parameter in qTest Parameters.

    Parameters in qTest Parameters are used for parameterized testing. They define
    variables that can be used across test cases with different values to create
    data-driven tests.
    """

    id: int | None = Field(None, description="Unique identifier for the parameter")
    name: str = Field(..., description="Name of the parameter", min_length=1, max_length=255)
    description: str | None = Field(None, description="Detailed description of the parameter")
    project_id: int | None = Field(None, alias="projectId", description="ID of the project containing this parameter")
    status: str | None = Field(None, description="Status of the parameter (e.g., Active, Inactive)")
    values: list[QTestParameterValue] = Field(default_factory=list, description="List of values for this parameter")
    created_date: datetime | None = Field(None, alias="createdDate", description="Date when the parameter was created")
    created_by: dict | None = Field(None, alias="createdBy", description="User who created the parameter")

    # Valid parameter statuses in qTest
    VALID_STATUSES: ClassVar[list[str]] = ["Active", "Inactive", "Archived"]

    @validator('name')
    def validate_name(cls, value):
        """Validate parameter name isn't empty or just whitespace."""
        if value.strip() == "":
            raise ValueError("Parameter name cannot be empty or only whitespace")
        return value

    @validator('status')
    def validate_status(cls, value):
        """Validate parameter status if provided."""
        if value is not None and value not in cls.VALID_STATUSES:
            raise ValueError(f"Status '{value}' is not valid. Must be one of: {', '.join(cls.VALID_STATUSES)}")
        return value

    model_config = {"populate_by_name": True}


class QTestDatasetRow(BaseModel):
    """
    Represents a dataset row in qTest Parameters.

    Dataset rows contain parameter value combinations for data-driven testing.
    Each row represents a set of values that can be used for a test execution.
    """

    id: int | None = Field(None, description="Unique identifier for the dataset row")
    dataset_id: int | None = Field(None, alias="datasetId", description="ID of the dataset this row belongs to")
    values: dict[str, Any] = Field(default_factory=dict, description="Parameter name to value mappings for this row")
    name: str | None = Field(None, description="Optional name for this dataset row")
    description: str | None = Field(None, description="Optional description of this dataset row")

    @validator('values')
    def validate_values(cls, value):
        """Validate that values dictionary is not empty."""
        if not value:
            raise ValueError("Values dictionary cannot be empty for a dataset row")
        return value

    model_config = {"populate_by_name": True}


class QTestDataset(BaseModel):
    """
    Represents a dataset in qTest Parameters.

    Datasets in qTest Parameters are collections of data rows used for data-driven
    testing. Each dataset contains rows with parameter value combinations that can
    be used to run the same test with different inputs.
    """

    id: int | None = Field(None, description="Unique identifier for the dataset")
    name: str = Field(..., description="Name of the dataset", min_length=1, max_length=255)
    description: str | None = Field(None, description="Detailed description of the dataset")
    project_id: int | None = Field(None, alias="projectId", description="ID of the project containing this dataset")
    status: str | None = Field(None, description="Status of the dataset (e.g., Active, Inactive)")
    rows: list[QTestDatasetRow] = Field(default_factory=list, description="Rows of parameter values in this dataset")
    created_date: datetime | None = Field(None, alias="createdDate", description="Date when the dataset was created")
    created_by: dict | None = Field(None, alias="createdBy", description="User who created the dataset")
    parameter_names: list[str] | None = Field(None, alias="parameterNames", description="Names of parameters used in this dataset")

    # Valid dataset statuses in qTest
    VALID_STATUSES: ClassVar[list[str]] = ["Active", "Inactive", "Archived"]

    @validator('name')
    def validate_name(cls, value):
        """Validate dataset name isn't empty or just whitespace."""
        if value.strip() == "":
            raise ValueError("Dataset name cannot be empty or only whitespace")
        return value

    @validator('status')
    def validate_status(cls, value):
        """Validate dataset status if provided."""
        if value is not None and value not in cls.VALID_STATUSES:
            raise ValueError(f"Status '{value}' is not valid. Must be one of: {', '.join(cls.VALID_STATUSES)}")
        return value

    @root_validator(skip_on_failure=True)
    def validate_parameter_consistency(cls, values):
        """Validate that all rows use the same parameter names if parameter_names is provided."""
        rows = values.get('rows', [])
        parameter_names = values.get('parameter_names')

        if parameter_names and rows:
            for i, row in enumerate(rows):
                row_params = set(row.values.keys())
                if not row_params.issubset(set(parameter_names)):
                    extra_params = row_params - set(parameter_names)
                    raise ValueError(f"Row {i} contains parameters {extra_params} not defined in parameter_names")

        return values

    model_config = {"populate_by_name": True}


# Pulse API Models


class QTestPulseEventType(str, Enum):
    """Types of events that can trigger Pulse rules."""

    TEST_CASE_CREATED = "TEST_CASE_CREATED"
    TEST_CASE_UPDATED = "TEST_CASE_UPDATED"
    TEST_CASE_DELETED = "TEST_CASE_DELETED"
    TEST_RUN_CREATED = "TEST_RUN_CREATED"
    TEST_RUN_UPDATED = "TEST_RUN_UPDATED"
    TEST_RUN_DELETED = "TEST_RUN_DELETED"
    TEST_LOG_CREATED = "TEST_LOG_CREATED"
    TEST_LOG_UPDATED = "TEST_LOG_UPDATED"
    REQUIREMENT_CREATED = "REQUIREMENT_CREATED"
    REQUIREMENT_UPDATED = "REQUIREMENT_UPDATED"
    DEFECT_CREATED = "DEFECT_CREATED"
    DEFECT_UPDATED = "DEFECT_UPDATED"
    SCHEDULED = "SCHEDULED"
    MANUAL = "MANUAL"


class QTestPulseActionType(str, Enum):
    """Types of actions that can be performed by Pulse rules."""

    CREATE_DEFECT = "CREATE_DEFECT"
    UPDATE_DEFECT = "UPDATE_DEFECT"
    SEND_MAIL = "SEND_MAIL"
    UPDATE_FIELD_VALUE = "UPDATE_FIELD_VALUE"
    WEBHOOK = "WEBHOOK"
    SLACK = "SLACK"
    UPDATE_TEST_RUN_STATUS = "UPDATE_TEST_RUN_STATUS"
    CREATE_TEST_CASE = "CREATE_TEST_CASE"
    UPDATE_TEST_CASE = "UPDATE_TEST_CASE"
    EXECUTE_SCRIPT = "EXECUTE_SCRIPT"


class QTestPulseCondition(BaseModel):
    """
    Represents a condition in a Pulse rule.

    Conditions determine when a Pulse rule should trigger. Each condition
    consists of a field, operator, and value to compare against. Multiple
    conditions can be combined to create complex trigger rules.
    """

    field: str = Field(..., description="The field to evaluate in the condition", min_length=1)
    operator: str = Field(..., description="The comparison operator to use", min_length=1)
    value: Any = Field(..., description="The value to compare against")
    value_type: str | None = Field(None, description="The data type of the value (string, number, boolean)")

    # Valid comparison operators in qTest Pulse
    VALID_OPERATORS: ClassVar[list[str]] = [
        "equals", "not_equals", "contains", "not_contains", "starts_with",
        "ends_with", "greater_than", "less_than", "is_empty", "is_not_empty"
    ]

    # Valid value types in qTest Pulse
    VALID_VALUE_TYPES: ClassVar[list[str]] = ["string", "number", "boolean", "array", "object", "null"]

    @validator('operator')
    def validate_operator(cls, value):
        """Validate that the operator is supported."""
        if value not in cls.VALID_OPERATORS:
            raise ValueError(f"Operator '{value}' is not valid. Must be one of: {', '.join(cls.VALID_OPERATORS)}")
        return value

    @validator('value_type')
    def validate_value_type(cls, value):
        """Validate that the value type is supported if provided."""
        if value is not None and value.lower() not in cls.VALID_VALUE_TYPES:
            raise ValueError(f"Value type '{value}' is not valid. Must be one of: {', '.join(cls.VALID_VALUE_TYPES)}")
        return value.lower() if value is not None else value

    @root_validator(skip_on_failure=True)
    def validate_value_consistency(cls, values):
        """Validate that value is consistent with value_type if provided."""
        value = values.get('value')
        value_type = values.get('value_type')

        if value is not None and value_type:
            if value_type == "number" and not isinstance(value, (int, float)):
                raise ValueError(f"Value '{value}' is not a valid number")
            elif value_type == "boolean" and not isinstance(value, bool):
                raise ValueError(f"Value '{value}' is not a valid boolean")
            elif value_type == "array" and not isinstance(value, list):
                raise ValueError(f"Value '{value}' is not a valid array")
            elif value_type == "object" and not isinstance(value, dict):
                raise ValueError(f"Value '{value}' is not a valid object")

        return values

    model_config = {"populate_by_name": True}


class QTestPulseActionParameter(BaseModel):
    """
    Represents a parameter for a Pulse action.

    Action parameters configure how a Pulse action behaves when triggered.
    Each parameter has a name, value, and optional type information.
    """

    name: str = Field(..., description="Name of the parameter", min_length=1)
    value: Any = Field(..., description="Value of the parameter")
    value_type: str | None = Field(None, description="The data type of the value (string, number, boolean)")

    # Valid value types in qTest Pulse
    VALID_VALUE_TYPES: ClassVar[list[str]] = ["string", "number", "boolean", "array", "object", "null"]

    @validator('name')
    def validate_name(cls, value):
        """Validate parameter name isn't empty or just whitespace."""
        if value.strip() == "":
            raise ValueError("Parameter name cannot be empty or only whitespace")
        return value

    @validator('value_type')
    def validate_value_type(cls, value):
        """Validate that the value type is supported if provided."""
        if value is not None and value.lower() not in cls.VALID_VALUE_TYPES:
            raise ValueError(f"Value type '{value}' is not valid. Must be one of: {', '.join(cls.VALID_VALUE_TYPES)}")
        return value.lower() if value is not None else value

    @root_validator(skip_on_failure=True)
    def validate_value_consistency(cls, values):
        """Validate that value is consistent with value_type if provided."""
        value = values.get('value')
        value_type = values.get('value_type')

        if value is not None and value_type:
            if value_type == "number" and not isinstance(value, (int, float)):
                raise ValueError(f"Value '{value}' is not a valid number")
            elif value_type == "boolean" and not isinstance(value, bool):
                raise ValueError(f"Value '{value}' is not a valid boolean")
            elif value_type == "array" and not isinstance(value, list):
                raise ValueError(f"Value '{value}' is not a valid array")
            elif value_type == "object" and not isinstance(value, dict):
                raise ValueError(f"Value '{value}' is not a valid object")

        return values

    model_config = {"populate_by_name": True}


class QTestPulseAction(BaseModel):
    """
    Represents an action in a Pulse rule.

    Actions define what happens when a Pulse rule is triggered. They can perform
    operations like sending emails, creating defects, updating field values, or
    triggering webhooks.
    """

    id: int | None = Field(None, description="Unique identifier for the action")
    name: str = Field(..., description="Name of the action", min_length=1, max_length=255)
    action_type: str = Field(..., alias="actionType", description="Type of action to perform")
    project_id: int = Field(..., alias="projectId", description="ID of the project containing this action", gt=0)
    parameters: list[QTestPulseActionParameter] = Field(default_factory=list, description="Parameters configuring this action")
    created_by: dict[str, Any] | None = Field(None, alias="createdBy", description="User who created the action")
    created_date: datetime | None = Field(None, alias="createdDate", description="Date when the action was created")
    updated_by: dict[str, Any] | None = Field(None, alias="updatedBy", description="User who last updated the action")
    updated_date: datetime | None = Field(None, alias="updatedDate", description="Date when the action was last updated")

    @validator('name')
    def validate_name(cls, value):
        """Validate action name isn't empty or just whitespace."""
        if value.strip() == "":
            raise ValueError("Action name cannot be empty or only whitespace")
        return value

    @validator('action_type')
    def validate_action_type(cls, value):
        """Validate that action type is valid."""
        try:
            # Check if the value is a valid QTestPulseActionType
            QTestPulseActionType(value)
            return value
        except ValueError:
            valid_types = [e.value for e in QTestPulseActionType]
            raise ValueError(f"Action type '{value}' is not valid. Must be one of: {', '.join(valid_types)}")

    @root_validator(skip_on_failure=True)
    def validate_required_parameters(cls, values):
        """Validate that required parameters are provided based on action type."""
        action_type = values.get('action_type')
        parameters = values.get('parameters', [])

        param_names = {param.name for param in parameters}

        # Define required parameters for each action type
        required_params = {
            QTestPulseActionType.SEND_MAIL: {"recipients", "subject"},
            QTestPulseActionType.WEBHOOK: {"url", "method"},
            QTestPulseActionType.SLACK: {"webhook_url", "message"},
            QTestPulseActionType.UPDATE_FIELD_VALUE: {"field_id", "field_value"},
            QTestPulseActionType.UPDATE_TEST_RUN_STATUS: {"status"},
        }

        if action_type in required_params:
            missing = required_params[action_type] - param_names
            if missing:
                raise ValueError(f"Action type '{action_type}' requires parameters: {', '.join(missing)}")

        return values

    model_config = {"populate_by_name": True}




class QTestPulseTrigger(BaseModel):
    """
    Represents a trigger in a Pulse rule.

    Triggers define when a Pulse rule should be activated. They consist of an
    event type (like test case creation or test log updates) and optional
    conditions that must be met for the trigger to fire.
    """

    id: int | None = Field(None, description="Unique identifier for the trigger")
    name: str = Field(..., description="Name of the trigger", min_length=1, max_length=255)
    event_type: str = Field(..., alias="eventType", description="Type of event that activates this trigger")
    project_id: int = Field(..., alias="projectId", description="ID of the project containing this trigger", gt=0)
    conditions: list[QTestPulseCondition] = Field(default_factory=list, description="Conditions that must be met for the trigger to fire")
    created_by: dict[str, Any] | None = Field(None, alias="createdBy", description="User who created the trigger")
    created_date: datetime | None = Field(None, alias="createdDate", description="Date when the trigger was created")
    updated_by: dict[str, Any] | None = Field(None, alias="updatedBy", description="User who last updated the trigger")
    updated_date: datetime | None = Field(None, alias="updatedDate", description="Date when the trigger was last updated")

    @validator('name')
    def validate_name(cls, value):
        """Validate trigger name isn't empty or just whitespace."""
        if value.strip() == "":
            raise ValueError("Trigger name cannot be empty or only whitespace")
        return value

    @validator('event_type')
    def validate_event_type(cls, value):
        """Validate that event type is valid."""
        try:
            # Check if the value is a valid QTestPulseEventType
            QTestPulseEventType(value)
            return value
        except ValueError:
            valid_types = [e.value for e in QTestPulseEventType]
            raise ValueError(f"Event type '{value}' is not valid. Must be one of: {', '.join(valid_types)}")

    @root_validator(skip_on_failure=True)
    def validate_scheduled_trigger(cls, values):
        """Validate that scheduled triggers have appropriate conditions."""
        event_type = values.get('event_type')
        conditions = values.get('conditions', [])

        if event_type == QTestPulseEventType.SCHEDULED and not conditions:
            raise ValueError("Scheduled triggers must have at least one condition defining the schedule")

        return values

    model_config = {"populate_by_name": True}




class QTestPulseRule(BaseModel):
    """
    Represents a Pulse rule.

    Pulse rules connect triggers with actions to automate workflows in qTest.
    When a trigger's conditions are met, the associated action is executed.
    Rules can be enabled or disabled to control when they are active.
    """

    id: int | None = Field(None, description="Unique identifier for the rule")
    name: str = Field(..., description="Name of the rule", min_length=1, max_length=255)
    project_id: int = Field(..., alias="projectId", description="ID of the project containing this rule", gt=0)
    enabled: bool = Field(True, description="Whether the rule is currently active")
    trigger_id: int = Field(..., alias="triggerId", description="ID of the trigger that activates this rule", gt=0)
    action_id: int = Field(..., alias="actionId", description="ID of the action to execute when triggered", gt=0)
    description: str | None = Field(None, description="Detailed description of the rule and its purpose")
    created_by: dict[str, Any] | None = Field(None, alias="createdBy", description="User who created the rule")
    created_date: datetime | None = Field(None, alias="createdDate", description="Date when the rule was created")
    updated_by: dict[str, Any] | None = Field(None, alias="updatedBy", description="User who last updated the rule")
    updated_date: datetime | None = Field(None, alias="updatedDate", description="Date when the rule was last updated")
    priority: int | None = Field(None, description="Priority order for rule execution (lower runs first)", ge=1)

    @validator('name')
    def validate_name(cls, value):
        """Validate rule name isn't empty or just whitespace."""
        if value.strip() == "":
            raise ValueError("Rule name cannot be empty or only whitespace")
        return value

    @validator('description')
    def validate_description(cls, value):
        """Validate rule description if provided."""
        if value is not None and value.strip() == "":
            raise ValueError("Rule description cannot be empty or only whitespace if provided")
        return value

    model_config = {"populate_by_name": True}




class QTestPulseConstant(BaseModel):
    """
    Represents a Pulse constant.

    Pulse constants are named values that can be referenced in triggers and actions.
    They provide a way to define reusable values that can be centrally managed
    and updated across multiple Pulse rules.
    """

    id: int | None = Field(None, description="Unique identifier for the constant")
    name: str = Field(..., description="Name of the constant (used as reference key)", min_length=1, max_length=255)
    value: str = Field(..., description="Value of the constant", min_length=1)
    description: str | None = Field(None, description="Detailed description of the constant and its purpose")
    project_id: int = Field(..., alias="projectId", description="ID of the project containing this constant", gt=0)
    created_by: dict[str, Any] | None = Field(None, alias="createdBy", description="User who created the constant")
    created_date: datetime | None = Field(None, alias="createdDate", description="Date when the constant was created")
    updated_by: dict[str, Any] | None = Field(None, alias="updatedBy", description="User who last updated the constant")
    updated_date: datetime | None = Field(None, alias="updatedDate", description="Date when the constant was last updated")

    @validator('name')
    def validate_name(cls, value):
        """Validate constant name format."""
        if value.strip() == "":
            raise ValueError("Constant name cannot be empty or only whitespace")

        # Constant names are typically uppercase with underscores
        if not value.isupper() and "_" not in value:
            raise ValueError("Constant name should be UPPER_CASE_WITH_UNDERSCORES format")

        # Check for spaces or special characters
        import re
        if not re.match(r'^[A-Z0-9_]+$', value):
            raise ValueError("Constant name should only contain uppercase letters, numbers, and underscores")

        return value

    @validator('value')
    def validate_value(cls, value):
        """Validate constant value isn't empty."""
        if value.strip() == "":
            raise ValueError("Constant value cannot be empty or only whitespace")
        return value

    @validator('description')
    def validate_description(cls, value):
        """Validate constant description if provided."""
        if value is not None and value.strip() == "":
            raise ValueError("Constant description cannot be empty or only whitespace if provided")
        return value

    model_config = {"populate_by_name": True}




class QTestScenarioFeature(BaseModel):
    """
    Represents a BDD feature in qTest Scenario.

    Features in qTest Scenario are top-level BDD components that contain scenarios
    and describe a specific function or aspect of the application being tested.
    They follow the Gherkin syntax used in Behavior-Driven Development.
    """

    id: str | None = Field(None, description="Unique identifier for the feature (UUID format)")
    name: str = Field(..., description="Name of the feature", min_length=1, max_length=255)
    description: str | None = Field(None, description="Detailed description of the feature")
    project_id: int = Field(..., alias="projectId", description="ID of the project containing this feature", gt=0)
    content: str = Field(..., description="Full Gherkin content of the feature", min_length=1)
    path: str | None = Field(None, description="File path where this feature is stored")
    tags: list[str] | None = Field(default_factory=list, description="Tags associated with this feature")
    created_date: datetime | None = Field(None, alias="createdDate", description="Date when the feature was created")
    created_by: dict | None = Field(None, alias="createdBy", description="User who created the feature")
    updated_date: datetime | None = Field(None, alias="updatedDate", description="Date when the feature was last updated")

    @validator("id", pre=True, always=True)
    def set_id_if_none(cls, v):
        """Set UUID if id is None."""
        return v or str(uuid.uuid4())

    @validator('name')
    def validate_name(cls, value):
        """Validate feature name isn't empty or just whitespace."""
        if value.strip() == "":
            raise ValueError("Feature name cannot be empty or only whitespace")
        return value

    @validator('content')
    def validate_content(cls, value):
        """Validate feature content has proper Gherkin format."""
        if not value.strip():
            raise ValueError("Feature content cannot be empty or only whitespace")

        # Basic validation for Gherkin format - must start with "Feature:"
        if not value.lstrip().startswith("Feature:"):
            raise ValueError("Feature content must start with 'Feature:' keyword")

        # Should contain at least one Scenario or Scenario Outline
        if not any(line.lstrip().startswith(("Scenario:", "Scenario Outline:"))
                  for line in value.split("\n")):
            raise ValueError("Feature must contain at least one Scenario or Scenario Outline")

        return value

    model_config = {"populate_by_name": True}
