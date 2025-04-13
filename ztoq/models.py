from typing import Any, List, Optional
from datetime import datetime
from enum import Enum
import base64
from pydantic import BaseModel, Field, validator


class ZephyrConfig(BaseModel):
    """Configuration for Zephyr Scale API."""

    base_url: str
    api_token: str
    project_key: str


class Link(BaseModel):
    """Represents a link to an issue, web page, or test cycle."""

    id: Optional[str] = None
    name: str
    url: str
    description: Optional[str] = None
    type: str  # "issue", "web", or "testCycle"


class CustomFieldType(str, Enum):
    """Types of custom fields supported by Zephyr Scale."""
    
    TEXT = "text"
    PARAGRAPH = "paragraph"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    DROPDOWN = "dropdown"
    MULTIPLE_SELECT = "multipleSelect"
    DATE = "date"
    DATETIME = "datetime"
    USER = "user"
    NUMERIC = "numeric"
    URL = "url"
    TABLE = "table"
    FILE = "file"
    # Enterprise-specific field types
    HIERARCHICAL_SELECT = "hierarchicalSelect"
    USER_GROUP = "userGroup"
    LABEL = "label"
    SPRINT = "sprint"
    VERSION = "version"
    COMPONENT = "component"


class CustomField(BaseModel):
    """Represents a custom field and its value."""

    id: str
    name: str
    type: str
    value: Any
    
    @validator('value')
    def validate_value_by_type(cls, v, values):
        """Validate that the value is appropriate for the field type."""
        if 'type' not in values:
            return v
            
        field_type = values['type']
        
        # Validate based on field type
        if field_type == CustomFieldType.CHECKBOX and not isinstance(v, bool):
            raise ValueError(f"Field type {field_type} requires a boolean value")
        elif field_type == CustomFieldType.NUMERIC and not (isinstance(v, int) or isinstance(v, float)):
            raise ValueError(f"Field type {field_type} requires a numeric value")
        elif field_type == CustomFieldType.TABLE and not isinstance(v, list):
            raise ValueError(f"Field type {field_type} requires a list of table rows")
        elif field_type == CustomFieldType.MULTIPLE_SELECT and not isinstance(v, list):
            raise ValueError(f"Field type {field_type} requires a list of selected values")
            
        return v


class Attachment(BaseModel):
    """Represents a file attachment in Zephyr Scale."""
    
    id: Optional[str] = None
    filename: str
    content_type: str = Field(..., alias="contentType")
    size: Optional[int] = None
    created_on: Optional[datetime] = Field(None, alias="createdOn")
    created_by: Optional[str] = Field(None, alias="createdBy")
    content: Optional[str] = None  # Base64 encoded content when applicable
    
    model_config = {"populate_by_name": True}
    
    @classmethod
    def from_binary(cls, filename: str, content_type: str, binary_data: bytes):
        """Create an attachment from binary data by encoding it as base64."""
        encoded = base64.b64encode(binary_data).decode('utf-8')
        return cls(
            filename=filename,
            contentType=content_type,
            size=len(binary_data),
            content=encoded,
            createdOn=datetime.now(),
            createdBy="system"
        )


class CaseStep(BaseModel):
    """Represents a step in a test case or execution."""

    id: Optional[str] = None
    index: int
    description: str
    expected_result: Optional[str] = Field(None, alias="expectedResult")
    data: Optional[str] = None
    actual_result: Optional[str] = Field(None, alias="actualResult")
    status: Optional[str] = None
    attachments: List[Attachment] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class ScriptFile(BaseModel):
    """Represents a script file attached to a test case."""

    id: str
    filename: str
    type: str  # e.g. "cucumber", "python", "javascript"
    content: Optional[str] = None


class CaseVersion(BaseModel):
    """Represents a version of a test case."""

    id: str
    name: str
    description: Optional[str] = None
    status: Optional[str] = None
    created_at: datetime = Field(..., alias="createdAt")
    created_by: Optional[str] = Field(None, alias="createdBy")

    model_config = {"populate_by_name": True}


class Folder(BaseModel):
    """Represents a folder in the Zephyr Scale structure."""

    id: str
    name: str
    folder_type: str = Field(..., alias="folderType")  # "TEST_CASE", "TEST_CYCLE", etc.
    parent_id: Optional[str] = Field(None, alias="parentId")
    project_key: str = Field(..., alias="projectKey")

    model_config = {"populate_by_name": True}


class Status(BaseModel):
    """Represents a status in Zephyr Scale."""

    id: str
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    type: str  # "TEST_CASE", "TEST_CYCLE", "TEST_EXECUTION", etc.


class Priority(BaseModel):
    """Represents a priority in Zephyr Scale."""

    id: str
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    rank: int


class Environment(BaseModel):
    """Represents an environment in Zephyr Scale."""

    id: str
    name: str
    description: Optional[str] = None


class Case(BaseModel):
    """Represents a Zephyr test case."""

    id: str
    key: str
    name: str
    objective: Optional[str] = None
    precondition: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[Priority] = None
    priority_name: Optional[str] = Field(None, alias="priorityName")
    folder: Optional[str] = None
    folder_name: Optional[str] = Field(None, alias="folderName")
    owner: Optional[str] = None
    owner_name: Optional[str] = Field(None, alias="ownerName")
    component: Optional[str] = None
    component_name: Optional[str] = Field(None, alias="componentName")
    created_on: Optional[datetime] = Field(None, alias="createdOn")
    created_by: Optional[str] = Field(None, alias="createdBy")
    updated_on: Optional[datetime] = Field(None, alias="updatedOn")
    updated_by: Optional[str] = Field(None, alias="updatedBy")
    version: Optional[str] = None
    estimated_time: Optional[int] = Field(None, alias="estimatedTime")
    labels: List[str] = Field(default_factory=list)
    steps: List[CaseStep] = Field(default_factory=list)
    custom_fields: List[CustomField] = Field(default_factory=list, alias="customFields")
    links: List[Link] = Field(default_factory=list)
    scripts: List[ScriptFile] = Field(default_factory=list)
    versions: List[CaseVersion] = Field(default_factory=list, alias="caseVersions")
    attachments: List[Attachment] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class CycleInfo(BaseModel):
    """Represents a Zephyr test cycle."""

    id: str
    key: str
    name: str
    description: Optional[str] = None
    status: Optional[str] = None
    status_name: Optional[str] = Field(None, alias="statusName")
    folder: Optional[str] = None
    folder_name: Optional[str] = Field(None, alias="folderName")
    project_key: str = Field(..., alias="projectKey")
    owner: Optional[str] = None
    owner_name: Optional[str] = Field(None, alias="ownerName")
    created_on: Optional[datetime] = Field(None, alias="createdOn")
    created_by: Optional[str] = Field(None, alias="createdBy")
    updated_on: Optional[datetime] = Field(None, alias="updatedOn")
    updated_by: Optional[str] = Field(None, alias="updatedBy")
    custom_fields: List[CustomField] = Field(default_factory=list, alias="customFields")
    links: List[Link] = Field(default_factory=list)
    attachments: List[Attachment] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class Plan(BaseModel):
    """Represents a Zephyr test plan."""

    id: str
    key: str
    name: str
    description: Optional[str] = None
    status: Optional[str] = None
    status_name: Optional[str] = Field(None, alias="statusName")
    folder: Optional[str] = None
    folder_name: Optional[str] = Field(None, alias="folderName")
    project_key: str = Field(..., alias="projectKey")
    owner: Optional[str] = None
    owner_name: Optional[str] = Field(None, alias="ownerName")
    created_on: Optional[datetime] = Field(None, alias="createdOn")
    created_by: Optional[str] = Field(None, alias="createdBy")
    updated_on: Optional[datetime] = Field(None, alias="updatedOn")
    updated_by: Optional[str] = Field(None, alias="updatedBy")
    custom_fields: List[CustomField] = Field(default_factory=list, alias="customFields")
    links: List[Link] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class Execution(BaseModel):
    """Represents a Zephyr test execution."""

    id: str
    test_case_key: str = Field(..., alias="testCaseKey")
    cycle_id: str = Field(..., alias="cycleId")
    cycle_name: Optional[str] = Field(None, alias="cycleName")
    status: str
    status_name: Optional[str] = Field(None, alias="statusName")
    environment: Optional[str] = None
    environment_name: Optional[str] = Field(None, alias="environmentName")
    executed_by: Optional[str] = Field(None, alias="executedBy")
    executed_by_name: Optional[str] = Field(None, alias="executedByName")
    executed_on: Optional[datetime] = Field(None, alias="executedOn")
    created_on: Optional[datetime] = Field(None, alias="createdOn")
    created_by: Optional[str] = Field(None, alias="createdBy")
    updated_on: Optional[datetime] = Field(None, alias="updatedOn")
    updated_by: Optional[str] = Field(None, alias="updatedBy")
    actual_time: Optional[int] = Field(None, alias="actualTime")
    comment: Optional[str] = None
    steps: List[CaseStep] = Field(default_factory=list)
    custom_fields: List[CustomField] = Field(default_factory=list, alias="customFields")
    links: List[Link] = Field(default_factory=list)
    attachments: List[Attachment] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class PaginatedResponse(BaseModel):
    """Represents a paginated response from the Zephyr Scale API."""

    total_count: int = Field(..., alias="totalCount")
    start_at: int = Field(..., alias="startAt")
    max_results: int = Field(..., alias="maxResults")
    is_last: bool = Field(..., alias="isLast")
    values: List[Any] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class Project(BaseModel):
    """Represents a Zephyr Scale project."""

    id: str
    key: str
    name: str
    description: Optional[str] = None

# Compatibility aliases for backward compatibility
TestStep = CaseStep
TestCase = Case
TestCycleInfo = CycleInfo
TestPlan = Plan
TestExecution = Execution
TestScript = ScriptFile
TestVersion = CaseVersion
