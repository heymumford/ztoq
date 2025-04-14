import pytest
from datetime import datetime
import base64
from pydantic import ValidationError

from ztoq.models import (
    ZephyrConfig,
    Link,
    CustomField,
    CustomFieldType,
    CaseStep,
    Case,
    Priority,
    PaginatedResponse,
    Attachment,
)


@pytest.mark.unit
class TestModels:
    def test_zephyr_config_validation(self):
        """Test ZephyrConfig validation."""
        # Valid config
        config = ZephyrConfig(
            base_url="https://api.zephyrscale.example.com/v2",
            api_token="test-token",
            project_key="TEST",
        )
        assert config.base_url == "https://api.zephyrscale.example.com/v2"
        assert config.api_token == "test-token"
        assert config.project_key == "TEST"

        # Missing required fields
        with pytest.raises(ValidationError):
            ZephyrConfig(base_url="https://api.example.com", api_token="token")

    def test_link_model(self):
        """Test Link model validation and defaults."""
        # With all fields
        link = Link(
            id="123",
            name="JIRA-123",
            url="https://jira.example.com/browse/JIRA-123",
            description="JIRA ticket",
            type="issue",
        )
        assert link.id == "123"
        assert link.name == "JIRA-123"
        assert link.url == "https://jira.example.com/browse/JIRA-123"
        assert link.description == "JIRA ticket"
        assert link.type == "issue"

        # Required fields only
        link = Link(name="Doc", url="https://example.com/doc", type="web")
        assert link.id is None
        assert link.name == "Doc"
        assert link.url == "https://example.com/doc"
        assert link.description is None
        assert link.type == "web"

    def test_case_step_model(self):
        """Test CaseStep model with alias fields and attachments."""
        # Create attachment
        attachment = Attachment(
            id="att1",
            filename="screenshot.png",
            contentType="image/png",
            size=1024,
            createdOn="2023-01-01T12:00:00",
            createdBy="user123",
        )

        # With all fields including attachments
        step = CaseStep(
            id="123",
            index=1,
            description="Do something",
            expectedResult="See something",
            data="Test data",
            actualResult="Saw something",
            status="Pass",
            attachments=[attachment],
        )
        assert step.id == "123"
        assert step.index == 1
        assert step.description == "Do something"
        assert step.expected_result == "See something"  # Alias field
        assert step.data == "Test data"
        assert step.actual_result == "Saw something"  # Alias field
        assert step.status == "Pass"
        assert len(step.attachments) == 1
        assert step.attachments[0].filename == "screenshot.png"

        # Test dict() output with original field names
        step_dict = step.model_dump(by_alias=True)
        assert "expectedResult" in step_dict
        assert "actualResult" in step_dict
        assert step_dict["expectedResult"] == "See something"
        assert "attachments" in step_dict

    def test_case_model(self):
        """Test Case model with nested objects including attachments and custom fields."""
        # Create priority
        priority = Priority(id="p1", name="High", rank=1, color="#ff0000")

        # Create steps with attachments
        step_attachment = Attachment(
            id="att1", filename="screenshot.png", contentType="image/png", size=1024
        )

        steps = [
            CaseStep(
                index=1,
                description="Step 1",
                expectedResult="Result 1",
                attachments=[step_attachment],
            )
        ]

        # Create different types of custom fields
        custom_fields = [
            CustomField(id="cf1", name="Text Field", type="text", value="Text value"),
            CustomField(id="cf2", name="Checkbox", type="checkbox", value=True),
            CustomField(id="cf3", name="Dropdown", type="dropdown", value="Option 1"),
            CustomField(
                id="cf4",
                name="Multiple Select",
                type="multipleSelect",
                value=["Option 1", "Option 2"],
            ),
            CustomField(id="cf5", name="Numeric", type="numeric", value=123),
        ]

        # Create case attachment
        case_attachment = Attachment(
            id="att2",
            filename="requirements.pdf",
            contentType="application/pdf",
            size=2048,
            createdOn=datetime.now(),
        )

        test_case = Case(
            id="tc1",
            key="TEST-TC-1",
            name="Case 1",
            status="Draft",
            priority=priority,
            steps=steps,
            custom_fields=custom_fields,
            labels=["regression", "smoke"],
            created_on=datetime.now(),
            attachments=[case_attachment],
        )

        assert test_case.id == "tc1"
        assert test_case.key == "TEST-TC-1"
        assert test_case.name == "Case 1"
        assert test_case.priority.name == "High"
        assert len(test_case.steps) == 1
        assert test_case.steps[0].description == "Step 1"
        assert len(test_case.steps[0].attachments) == 1
        assert test_case.steps[0].attachments[0].filename == "screenshot.png"
        assert len(test_case.custom_fields) == 5
        assert test_case.custom_fields[0].name == "Text Field"
        assert test_case.custom_fields[1].value is True
        assert isinstance(test_case.custom_fields[3].value, list)
        assert len(test_case.attachments) == 1
        assert test_case.attachments[0].filename == "requirements.pdf"
        assert "regression" in test_case.labels

    def test_custom_field_validation(self):
        """Test CustomField validation based on field type."""
        # Valid fields
        assert (
            CustomField(id="cf1", name="Text", type="text", value="Some text").value == "Some text"
        )
        assert CustomField(id="cf2", name="Checkbox", type="checkbox", value=True).value is True
        assert CustomField(id="cf3", name="Number", type="numeric", value=123).value == 123

        # Invalid field values should raise validation errors
        with pytest.raises(ValueError):
            CustomField(id="cf4", name="Checkbox", type="checkbox", value="not a boolean")

        with pytest.raises(ValueError):
            CustomField(id="cf5", name="Number", type="numeric", value="not a number")

        with pytest.raises(ValueError):
            CustomField(id="cf6", name="MultiSelect", type="multipleSelect", value="not a list")

    def test_attachment_model(self):
        """Test Attachment model including binary data handling."""
        # Basic attachment
        attachment = Attachment(
            id="att1",
            filename="document.pdf",
            contentType="application/pdf",
            size=1024,
        )
        assert attachment.id == "att1"
        assert attachment.filename == "document.pdf"
        assert attachment.content_type == "application/pdf"

        # Test binary data handling
        test_data = b"This is test binary data"
        binary_attachment = Attachment.from_binary(
            filename="test.bin", content_type="application/octet-stream", binary_data=test_data
        )

        assert binary_attachment.filename == "test.bin"
        assert binary_attachment.content_type == "application/octet-stream"
        assert binary_attachment.size == len(test_data)

        # Verify content is base64 encoded
        decoded = base64.b64decode(binary_attachment.content)
        assert decoded == test_data

    def test_paginated_response(self):
        """Test PaginatedResponse model."""
        response = PaginatedResponse(
            totalCount=100,
            startAt=0,
            maxResults=50,
            isLast=False,
            values=[{"id": "1", "name": "Item 1"}, {"id": "2", "name": "Item 2"}],
        )

        assert response.total_count == 100
        assert response.start_at == 0
        assert response.max_results == 50
        assert not response.is_last
        assert len(response.values) == 2
        assert response.values[0]["name"] == "Item 1"
