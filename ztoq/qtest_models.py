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
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, root_validator, validator

class QTestConfig(BaseModel):
    """Configuration for qTest API."""

    base_url: str
    username: str
    password: str
    project_id: int


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
    """Represents a link in qTest."""

    id: int | None = None
    name: str
    url: str
    icon_url: str | None = Field(None, alias="iconUrl")
    target: str | None = None

    model_config = {"populate_by_name": True}


class QTestCustomField(BaseModel):
    """Represents a custom field in qTest."""

    field_id: int = Field(..., alias="id")
    field_name: str = Field(..., alias="name")
    field_type: str = Field(..., alias="type")
    field_value: Any | None = Field(None, alias="value")
    is_required: bool | None = Field(None, alias="required")

    model_config = {"populate_by_name": True}


class QTestAttachment(BaseModel):
    """Represents a file attachment in qTest."""

    id: int | None = None
    name: str
    content_type: str = Field(..., alias="contentType")
    created_date: datetime | None = Field(None, alias="createdDate")
    web_url: str | None = Field(None, alias="webUrl")

    model_config = {"populate_by_name": True}

    @classmethod
    def from_binary(cls, name: str, content_type: str, binary_data: bytes):
        """Create an attachment from binary data."""
        encoded = base64.b64encode(binary_data).decode("utf-8")
        return {
            "name": name,
                "contentType": content_type,
                "size": len(binary_data),
                "data": encoded,
            }


class QTestProject(BaseModel):
    """Represents a qTest project."""

    id: int
    name: str
    description: str | None = None
    start_date: datetime | None = Field(None, alias="startDate")
    end_date: datetime | None = Field(None, alias="endDate")
    status_name: str | None = Field(None, alias="statusName")

    model_config = {"populate_by_name": True}


class QTestModule(BaseModel):
    """Represents a qTest module."""

    id: int | None = None
    name: str
    description: str | None = None
    parent_id: int | None = Field(None, alias="parentId")
    pid: str | None = None
    project_id: int | None = Field(None, alias="projectId")
    path: str | None = None

    model_config = {"populate_by_name": True}


class QTestField(BaseModel):
    """Represents a field in qTest."""

    id: int
    name: str
    label: str
    field_type: str = Field(..., alias="fieldType")
    entity_type: str = Field(..., alias="entityType")
    allowed_values: list[str] | None = Field(None, alias="allowedValues")
    required: bool = False

    model_config = {"populate_by_name": True}


class QTestStep(BaseModel):
    """Represents a test step in qTest."""

    id: int | None = None
    description: str
    expected_result: str | None = Field(None, alias="expectedResult")
    order: int
    attachments: list[QTestAttachment] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class QTestAutomationSettings(BaseModel):
    """Represents automation settings for a test case in qTest."""

    automation_id: str | None = Field(None, alias="automationId")
    framework_id: int | None = Field(None, alias="frameworkId")

    model_config = {"populate_by_name": True}


class QTestTestCase(BaseModel):
    """Represents a test case in qTest."""

    id: int | None = None
    pid: str | None = None
    name: str
    description: str | None = None
    precondition: str | None = None
    test_steps: list[QTestStep] = Field(default_factory=list, alias="steps")
    properties: list[QTestCustomField] | None = Field(default_factory=list)
    parent_id: int | None = Field(None, alias="parentId")
    module_id: int | None = Field(None, alias="moduleId")
    priority_id: int | None = Field(None, alias="priorityId")
    creator_id: int | None = Field(None, alias="creatorId")
    attachments: list[QTestAttachment] = Field(default_factory=list)
    create_date: datetime | None = Field(None, alias="createdDate")
    last_modified_date: datetime | None = Field(None, alias="lastModifiedDate")
    automation: QTestAutomationSettings | None = None

    model_config = {"populate_by_name": True}


class QTestRelease(BaseModel):
    """Represents a release in qTest."""

    id: int | None = None
    name: str
    description: str | None = None
    pid: str | None = None
    project_id: int | None = Field(None, alias="projectId")
    start_date: datetime | None = Field(None, alias="startDate")
    end_date: datetime | None = Field(None, alias="endDate")

    model_config = {"populate_by_name": True}


class QTestTestCycle(BaseModel):
    """Represents a test cycle in qTest."""

    id: int | None = None
    name: str
    description: str | None = None
    parent_id: int | None = Field(None, alias="parentId")
    pid: str | None = None
    release_id: int | None = Field(None, alias="releaseId")
    project_id: int | None = Field(None, alias="projectId")
    properties: list[QTestCustomField] | None = Field(default_factory=list)
    start_date: datetime | None = Field(None, alias="startDate")
    end_date: datetime | None = Field(None, alias="endDate")

    model_config = {"populate_by_name": True}


class QTestTestRun(BaseModel):
    """Represents a test run in qTest."""

    id: int | None = None
    name: str | None = None
    description: str | None = None
    pid: str | None = None
    test_case_version_id: int | None = Field(None, alias="testCaseVersionId")
    test_case_id: int | None = Field(None, alias="testCaseId")
    test_cycle_id: int | None = Field(None, alias="testCycleId")
    project_id: int | None = Field(None, alias="projectId")
    properties: list[QTestCustomField] | None = Field(default_factory=list)
    status: str | None = None

    model_config = {"populate_by_name": True}


class QTestTestLog(BaseModel):
    """Represents a test log in qTest."""

    id: int | None = None
    status: str
    execution_date: datetime | None = Field(None, alias="executionDate")
    note: str | None = None
    attachments: list[QTestAttachment] = Field(default_factory=list)
    properties: list[QTestCustomField] | None = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class QTestTestExecution(BaseModel):
    """Represents a test execution in qTest."""

    id: int | None = None
    test_run_id: int = Field(..., alias="testRunId")
    status: str
    execution_date: datetime = Field(..., alias="executionDate")
    executed_by: int | None = Field(None, alias="executedBy")
    note: str | None = None
    attachments: list[QTestAttachment] = Field(default_factory=list)
    test_step_logs: list[dict[str, Any]] | None = Field(None, alias="testStepLogs")

    model_config = {"populate_by_name": True}


class QTestParameterValue(BaseModel):
    """Represents a parameter value in qTest Parameters."""

    id: int | None = None
    value: str
    parameter_id: int | None = Field(None, alias="parameterId")

    model_config = {"populate_by_name": True}


class QTestParameter(BaseModel):
    """Represents a parameter in qTest Parameters."""

    id: int | None = None
    name: str
    description: str | None = None
    project_id: int | None = Field(None, alias="projectId")
    status: str | None = None
    values: list[QTestParameterValue] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class QTestDatasetRow(BaseModel):
    """Represents a dataset row in qTest Parameters."""

    id: int | None = None
    dataset_id: int | None = Field(None, alias="datasetId")
    values: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class QTestDataset(BaseModel):
    """Represents a dataset in qTest Parameters."""

    id: int | None = None
    name: str
    description: str | None = None
    project_id: int | None = Field(None, alias="projectId")
    status: str | None = None
    rows: list[QTestDatasetRow] = Field(default_factory=list)

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
    """Represents a condition in a Pulse rule."""

    field: str
    operator: str
    value: Any
    value_type: str | None = None

    model_config = {"populate_by_name": True}


class QTestPulseActionParameter(BaseModel):
    """Represents a parameter for a Pulse action."""

    name: str
    value: Any
    value_type: str | None = None

    model_config = {"populate_by_name": True}


class QTestPulseAction(BaseModel):
    """Represents an action in a Pulse rule."""

    id: int | None = None
    name: str
    action_type: str = Field(..., alias="actionType")
    project_id: int = Field(..., alias="projectId")
    parameters: list[QTestPulseActionParameter] = Field(default_factory=list)
    created_by: dict[str, Any] | None = Field(None, alias="createdBy")
    created_date: datetime | None = Field(None, alias="createdDate")
    updated_by: dict[str, Any] | None = Field(None, alias="updatedBy")
    updated_date: datetime | None = Field(None, alias="updatedDate")

    model_config = {"populate_by_name": True}




class QTestPulseTrigger(BaseModel):
    """Represents a trigger in a Pulse rule."""

    id: int | None = None
    name: str
    event_type: str = Field(..., alias="eventType")
    project_id: int = Field(..., alias="projectId")
    conditions: list[QTestPulseCondition] = Field(default_factory=list)
    created_by: dict[str, Any] | None = Field(None, alias="createdBy")
    created_date: datetime | None = Field(None, alias="createdDate")
    updated_by: dict[str, Any] | None = Field(None, alias="updatedBy")
    updated_date: datetime | None = Field(None, alias="updatedDate")

    model_config = {"populate_by_name": True}




class QTestPulseRule(BaseModel):
    """Represents a Pulse rule."""

    id: int | None = None
    name: str
    project_id: int = Field(..., alias="projectId")
    enabled: bool = True
    trigger_id: int = Field(..., alias="triggerId")
    action_id: int = Field(..., alias="actionId")
    description: str | None = None
    created_by: dict[str, Any] | None = Field(None, alias="createdBy")
    created_date: datetime | None = Field(None, alias="createdDate")
    updated_by: dict[str, Any] | None = Field(None, alias="updatedBy")
    updated_date: datetime | None = Field(None, alias="updatedDate")

    model_config = {"populate_by_name": True}




class QTestPulseConstant(BaseModel):
    """Represents a Pulse constant."""

    id: int | None = None
    name: str
    value: str
    description: str | None = None
    project_id: int = Field(..., alias="projectId")
    created_by: dict[str, Any] | None = Field(None, alias="createdBy")
    created_date: datetime | None = Field(None, alias="createdDate")
    updated_by: dict[str, Any] | None = Field(None, alias="updatedBy")
    updated_date: datetime | None = Field(None, alias="updatedDate")

    model_config = {"populate_by_name": True}




class QTestScenarioFeature(BaseModel):
    """Represents a BDD feature in qTest Scenario."""

    id: str | None = None
    name: str
    description: str | None = None
    project_id: int = Field(..., alias="projectId")
    content: str

    model_config = {"populate_by_name": True}

    @validator("id", pre=True, always=True)
    def set_id_if_none(cls, v):
        """Set UUID if id is None."""
        return v or str(uuid.uuid4())
