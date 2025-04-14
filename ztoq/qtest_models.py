"""
Pydantic models for qTest API objects.
"""

from typing import Any, List, Dict, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
import base64


class QTestConfig(BaseModel):
    """Configuration for qTest API."""

    base_url: str
    username: str
    password: str
    project_id: int


class QTestPaginatedResponse(BaseModel):
    """Represents a paginated response from the qTest API."""

    items: List[Dict[str, Any]] = Field(default_factory=list)
    page: Optional[int] = None
    page_size: Optional[int] = None
    offset: Optional[int] = None
    limit: Optional[int] = None
    total: int
    is_last: bool


class QTestLink(BaseModel):
    """Represents a link in qTest."""

    id: Optional[int] = None
    name: str
    url: str
    icon_url: Optional[str] = Field(None, alias="iconUrl")
    target: Optional[str] = None

    model_config = {"populate_by_name": True}


class QTestCustomField(BaseModel):
    """Represents a custom field in qTest."""

    field_id: int = Field(..., alias="id")
    field_name: str = Field(..., alias="name")
    field_type: str = Field(..., alias="type")
    field_value: Optional[Any] = Field(None, alias="value")
    is_required: Optional[bool] = Field(None, alias="required")

    model_config = {"populate_by_name": True}


class QTestAttachment(BaseModel):
    """Represents a file attachment in qTest."""

    id: Optional[int] = None
    name: str
    content_type: str = Field(..., alias="contentType")
    created_date: Optional[datetime] = Field(None, alias="createdDate")
    web_url: Optional[str] = Field(None, alias="webUrl")

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
    description: Optional[str] = None
    start_date: Optional[datetime] = Field(None, alias="startDate")
    end_date: Optional[datetime] = Field(None, alias="endDate")
    status_name: Optional[str] = Field(None, alias="statusName")

    model_config = {"populate_by_name": True}


class QTestModule(BaseModel):
    """Represents a qTest module."""

    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = Field(None, alias="parentId")
    pid: Optional[str] = None

    model_config = {"populate_by_name": True}


class QTestField(BaseModel):
    """Represents a field in qTest."""

    id: int
    name: str
    label: str
    field_type: str = Field(..., alias="fieldType")
    entity_type: str = Field(..., alias="entityType")
    allowed_values: Optional[List[str]] = Field(None, alias="allowedValues")
    required: bool = False

    model_config = {"populate_by_name": True}


class QTestStep(BaseModel):
    """Represents a test step in qTest."""

    id: Optional[int] = None
    description: str
    expected_result: Optional[str] = Field(None, alias="expectedResult")
    order: int
    attachments: List[QTestAttachment] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class QTestAutomationSettings(BaseModel):
    """Represents automation settings for a test case in qTest."""

    automation_id: Optional[str] = Field(None, alias="automationId")
    framework_id: Optional[int] = Field(None, alias="frameworkId")

    model_config = {"populate_by_name": True}


class QTestTestCase(BaseModel):
    """Represents a test case in qTest."""

    id: Optional[int] = None
    pid: Optional[str] = None
    name: str
    description: Optional[str] = None
    precondition: Optional[str] = None
    test_steps: List[QTestStep] = Field(default_factory=list, alias="steps")
    properties: Optional[List[QTestCustomField]] = Field(default_factory=list)
    parent_id: Optional[int] = Field(None, alias="parentId")
    module_id: Optional[int] = Field(None, alias="moduleId")
    priority_id: Optional[int] = Field(None, alias="priorityId")
    creator_id: Optional[int] = Field(None, alias="creatorId")
    attachments: List[QTestAttachment] = Field(default_factory=list)
    create_date: Optional[datetime] = Field(None, alias="createdDate")
    last_modified_date: Optional[datetime] = Field(None, alias="lastModifiedDate")
    automation: Optional[QTestAutomationSettings] = None

    model_config = {"populate_by_name": True}


class QTestRelease(BaseModel):
    """Represents a release in qTest."""

    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    pid: Optional[str] = None
    start_date: Optional[datetime] = Field(None, alias="startDate")
    end_date: Optional[datetime] = Field(None, alias="endDate")

    model_config = {"populate_by_name": True}


class QTestTestCycle(BaseModel):
    """Represents a test cycle in qTest."""

    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = Field(None, alias="parentId")
    pid: Optional[str] = None
    release_id: Optional[int] = Field(None, alias="releaseId")
    properties: Optional[List[QTestCustomField]] = Field(default_factory=list)
    start_date: Optional[datetime] = Field(None, alias="startDate")
    end_date: Optional[datetime] = Field(None, alias="endDate")

    model_config = {"populate_by_name": True}


class QTestTestRun(BaseModel):
    """Represents a test run in qTest."""

    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    pid: Optional[str] = None
    test_case_version_id: Optional[int] = Field(None, alias="testCaseVersionId")
    test_case_id: Optional[int] = Field(None, alias="testCaseId")
    test_cycle_id: Optional[int] = Field(None, alias="testCycleId")
    properties: Optional[List[QTestCustomField]] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class QTestTestLog(BaseModel):
    """Represents a test log in qTest."""

    id: Optional[int] = None
    status: str
    execution_date: Optional[datetime] = Field(None, alias="executionDate")
    note: Optional[str] = None
    attachments: List[QTestAttachment] = Field(default_factory=list)
    properties: Optional[List[QTestCustomField]] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class QTestTestExecution(BaseModel):
    """Represents a test execution in qTest."""

    id: Optional[int] = None
    test_run_id: int = Field(..., alias="testRunId")
    status: str
    execution_date: datetime = Field(..., alias="executionDate")
    executed_by: Optional[int] = Field(None, alias="executedBy")
    note: Optional[str] = None
    attachments: List[QTestAttachment] = Field(default_factory=list)
    test_step_logs: Optional[List[Dict[str, Any]]] = Field(None, alias="testStepLogs")

    model_config = {"populate_by_name": True}


class QTestParameterValue(BaseModel):
    """Represents a parameter value in qTest Parameters."""

    id: Optional[int] = None
    value: str
    parameter_id: Optional[int] = Field(None, alias="parameterId")

    model_config = {"populate_by_name": True}


class QTestParameter(BaseModel):
    """Represents a parameter in qTest Parameters."""

    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    project_id: Optional[int] = Field(None, alias="projectId")
    status: Optional[str] = None
    values: List[QTestParameterValue] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class QTestDatasetRow(BaseModel):
    """Represents a dataset row in qTest Parameters."""

    id: Optional[int] = None
    dataset_id: Optional[int] = Field(None, alias="datasetId")
    values: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class QTestDataset(BaseModel):
    """Represents a dataset in qTest Parameters."""

    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    project_id: Optional[int] = Field(None, alias="projectId")
    status: Optional[str] = None
    rows: List[QTestDatasetRow] = Field(default_factory=list)

    model_config = {"populate_by_name": True}
