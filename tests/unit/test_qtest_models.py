"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import base64
from datetime import datetime

import pytest
from pydantic import ValidationError

from ztoq.qtest_models import (
    QTestAttachment,
    QTestConfig,
    QTestCustomField,
    QTestDataset,
    QTestDatasetRow,
    QTestLink,
    QTestModule,
    QTestPaginatedResponse,
    QTestParameter,
    QTestParameterValue,
    QTestProject,
    QTestPulseAction,
    QTestPulseActionParameter,
    QTestPulseActionType,
    QTestPulseCondition,
    QTestPulseConstant,
    QTestPulseEventType,
    QTestPulseRule,
    QTestPulseTrigger,
    QTestRelease,
    QTestStep,
    QTestTestCase,
    QTestTestCycle,
    QTestTestExecution,
    QTestTestLog,
    QTestTestRun,
)


@pytest.mark.unit
class TestQTestModels:
    def test_qtest_config(self):
        """Test QTestConfig model."""
        # Valid config
        config = QTestConfig(
            base_url="https://example.qtest.com",
            username="test_user",
            password="test_password",
            project_id=12345,
        )
        assert config.base_url == "https://example.qtest.com"
        assert config.username == "test_user"
        assert config.password == "test_password"
        assert config.project_id == 12345

        # Missing fields should fail validation
        with pytest.raises(ValidationError):
            QTestConfig(base_url="https://example.com", username="user")

    def test_qtest_paginated_response(self):
        """Test QTestPaginatedResponse model."""
        # Manager API style pagination
        manager_response = QTestPaginatedResponse(
            items=[{"id": 1}, {"id": 2}], page=1, page_size=10, total=2, is_last=True,
        )
        assert len(manager_response.items) == 2
        assert manager_response.page == 1
        assert manager_response.page_size == 10
        assert manager_response.total == 2
        assert manager_response.is_last is True

        # Parameters API style pagination
        params_response = QTestPaginatedResponse(
            items=[{"id": 1}, {"id": 2}], offset=0, limit=10, total=2, is_last=True,
        )
        assert len(params_response.items) == 2
        assert params_response.offset == 0
        assert params_response.limit == 10
        assert params_response.total == 2
        assert params_response.is_last is True

        # Minimal required fields
        minimal_response = QTestPaginatedResponse(items=[], total=0, is_last=True)
        assert len(minimal_response.items) == 0
        assert minimal_response.total == 0
        assert minimal_response.is_last is True

    def test_qtest_link(self):
        """Test QTestLink model."""

        # Create with all fields
        link = QTestLink(
            id=1,
            name="Test Link",
            url="https://example.com",
            icon_url="https://example.com/icon.png",
            target="_blank",
        )
        assert link.id == 1
        assert link.name == "Test Link"
        assert link.url == "https://example.com"
        assert link.icon_url == "https://example.com/icon.png"
        assert link.target == "_blank"

        # Test alias mapping (populate_by_name = True)
        link_from_alias = QTestLink(
            id=1,
            name="Test Link",
            url="https://example.com",
            iconUrl="https://example.com/icon.png",
            target="_blank",
        )
        assert link_from_alias.icon_url == "https://example.com/icon.png"

    def test_qtest_custom_field(self):
        """Test QTestCustomField model."""
        # Create with all fields
        custom_field = QTestCustomField(
            id=1, name="Priority", type="STRING", value="High", required=True,
        )
        assert custom_field.field_id == 1  # Note the alias mapping
        assert custom_field.field_name == "Priority"
        assert custom_field.field_type == "STRING"
        assert custom_field.field_value == "High"
        assert custom_field.is_required is True

        # Test different field types
        number_field = QTestCustomField(id=2, name="Points", type="NUMBER", value=5)
        assert number_field.field_type == "NUMBER"
        assert number_field.field_value == 5

        bool_field = QTestCustomField(id=3, name="IsAutomated", type="CHECKBOX", value=True)
        assert bool_field.field_type == "CHECKBOX"
        assert bool_field.field_value is True

    def test_qtest_attachment(self):
        """Test QTestAttachment model."""
        # Create with all fields
        now = datetime.now()
        attachment = QTestAttachment(
            id=1,
            name="test.pdf",
            content_type="application/pdf",
            created_date=now,
            web_url="https://example.com/attachments/1",
        )
        assert attachment.id == 1
        assert attachment.name == "test.pdf"
        assert attachment.content_type == "application/pdf"
        assert attachment.created_date == now
        assert attachment.web_url == "https://example.com/attachments/1"

        # Test from_binary method
        binary_data = b"Test binary data"
        binary_attachment = QTestAttachment.from_binary(
            name="test.txt", content_type="text/plain", binary_data=binary_data,
        )
        assert binary_attachment["name"] == "test.txt"
        assert binary_attachment["contentType"] == "text/plain"
        assert binary_attachment["size"] == len(binary_data)
        assert binary_attachment["data"] == base64.b64encode(binary_data).decode("utf-8")

    def test_qtest_project(self):
        """Test QTestProject model."""
        # Create with all fields
        start_date = datetime.now()
        end_date = datetime.now()
        project = QTestProject(
            id=1,
            name="Test Project",
            description="A test project",
            start_date=start_date,
            end_date=end_date,
            status_name="Active",
        )
        assert project.id == 1
        assert project.name == "Test Project"
        assert project.description == "A test project"
        assert project.start_date == start_date
        assert project.end_date == end_date
        assert project.status_name == "Active"

        # Create with minimum fields
        min_project = QTestProject(id=2, name="Minimal Project")
        assert min_project.id == 2
        assert min_project.name == "Minimal Project"
        assert min_project.description is None

    def test_qtest_module(self):
        """Test QTestModule model."""
        # Create with all fields
        module = QTestModule(
            id=1, name="Test Module", description="A test module", parent_id=None, pid="MD-1",
        )
        assert module.id == 1
        assert module.name == "Test Module"
        assert module.description == "A test module"
        assert module.parent_id is None
        assert module.pid == "MD-1"

        # Create with minimum fields
        min_module = QTestModule(name="Minimal Module")
        assert min_module.id is None
        assert min_module.name == "Minimal Module"
        assert min_module.description is None
        assert min_module.parent_id is None
        assert min_module.pid is None

    def test_qtest_step(self):
        """Test QTestStep model."""
        # Create with all fields
        step = QTestStep(
            id=1,
            description="Navigate to login page",
            expected_result="Login page is displayed",
            order=1,
            attachments=[QTestAttachment(id=1, name="screenshot.png", content_type="image/png")],
        )
        assert step.id == 1
        assert step.description == "Navigate to login page"
        assert step.expected_result == "Login page is displayed"
        assert step.order == 1
        assert len(step.attachments) == 1
        assert step.attachments[0].name == "screenshot.png"

        # Create with minimum fields
        min_step = QTestStep(description="Minimal step", order=1)
        assert min_step.id is None
        assert min_step.description == "Minimal step"
        assert min_step.expected_result is None
        assert min_step.order == 1
        assert len(min_step.attachments) == 0

    def test_qtest_test_case(self):
        """Test QTestTestCase model."""
        # Create with all fields
        now = datetime.now()
        test_case = QTestTestCase(
            id=1,
            pid="TC-1",
            name="Login Test",
            description="Test the login functionality",
            precondition="User is registered",
            test_steps=[
                QTestStep(
                    description="Navigate to login page",
                    expected_result="Login page is displayed",
                    order=1,
                ),
                QTestStep(
                    description="Enter valid credentials",
                    expected_result="Credentials accepted",
                    order=2,
                ),
            ],
            properties=[QTestCustomField(id=1, name="Priority", type="STRING", value="High")],
            parent_id=None,
            module_id=100,
            priority_id=1,
            creator_id=1001,
            attachments=[QTestAttachment(id=1, name="screenshot.png", content_type="image/png")],
            create_date=now,
            last_modified_date=now,
        )
        assert test_case.id == 1
        assert test_case.pid == "TC-1"
        assert test_case.name == "Login Test"
        assert test_case.description == "Test the login functionality"
        assert test_case.precondition == "User is registered"
        assert len(test_case.test_steps) == 2
        assert test_case.test_steps[0].description == "Navigate to login page"
        assert test_case.test_steps[1].expected_result == "Credentials accepted"
        assert len(test_case.properties) == 1
        assert test_case.properties[0].field_name == "Priority"
        assert test_case.module_id == 100
        assert len(test_case.attachments) == 1
        assert test_case.attachments[0].name == "screenshot.png"
        assert test_case.create_date == now
        assert test_case.last_modified_date == now

        # Create with minimum fields
        min_test_case = QTestTestCase(name="Minimal Test Case")
        assert min_test_case.id is None
        assert min_test_case.name == "Minimal Test Case"
        assert min_test_case.description is None
        assert len(min_test_case.test_steps) == 0
        assert len(min_test_case.properties) == 0
        assert min_test_case.module_id is None
        assert len(min_test_case.attachments) == 0

    def test_qtest_test_cycle(self):
        """Test QTestTestCycle model."""
        # Create with all fields
        start_date = datetime.now()
        end_date = datetime.now()
        test_cycle = QTestTestCycle(
            id=1,
            name="Sprint 1 Test Cycle",
            description="Tests for Sprint 1",
            parent_id=None,
            pid="CY-1",
            release_id=101,
            properties=[QTestCustomField(id=1, name="Status", type="STRING", value="Active")],
            start_date=start_date,
            end_date=end_date,
        )
        assert test_cycle.id == 1
        assert test_cycle.name == "Sprint 1 Test Cycle"
        assert test_cycle.description == "Tests for Sprint 1"
        assert test_cycle.parent_id is None
        assert test_cycle.pid == "CY-1"
        assert test_cycle.release_id == 101
        assert len(test_cycle.properties) == 1
        assert test_cycle.properties[0].field_name == "Status"
        assert test_cycle.start_date == start_date
        assert test_cycle.end_date == end_date

        # Create with minimum fields
        min_test_cycle = QTestTestCycle(name="Minimal Test Cycle")
        assert min_test_cycle.id is None
        assert min_test_cycle.name == "Minimal Test Cycle"
        assert min_test_cycle.description is None
        assert min_test_cycle.release_id is None
        assert len(min_test_cycle.properties) == 0
        assert min_test_cycle.start_date is None
        assert min_test_cycle.end_date is None

    def test_qtest_release(self):
        """Test QTestRelease model."""
        # Create with all fields
        start_date = datetime.now()
        end_date = datetime.now()
        release = QTestRelease(
            id=1,
            name="Release 1.0",
            description="First major release",
            pid="RL-1",
            start_date=start_date,
            end_date=end_date,
        )
        assert release.id == 1
        assert release.name == "Release 1.0"
        assert release.description == "First major release"
        assert release.pid == "RL-1"
        assert release.start_date == start_date
        assert release.end_date == end_date

        # Create with minimum fields
        min_release = QTestRelease(name="Minimal Release")
        assert min_release.id is None
        assert min_release.name == "Minimal Release"
        assert min_release.description is None
        assert min_release.pid is None
        assert min_release.start_date is None
        assert min_release.end_date is None

    def test_qtest_test_run(self):
        """Test QTestTestRun model."""
        # Create with all fields
        test_run = QTestTestRun(
            id=1,
            name="Login Test Run",
            description="Login test execution",
            pid="TR-1",
            test_case_version_id=1,
            test_case_id=101,
            test_cycle_id=201,
            status="Not Run",
            properties=[
                QTestCustomField(id=1, name="Environment", type="STRING", value="Production"),
            ],
        )
        assert test_run.id == 1
        assert test_run.name == "Login Test Run"
        assert test_run.description == "Login test execution"
        assert test_run.pid == "TR-1"
        assert test_run.test_case_version_id == 1
        assert test_run.test_case_id == 101
        assert test_run.test_cycle_id == 201
        assert len(test_run.properties) == 1
        assert test_run.properties[0].field_name == "Environment"

        # Create with minimum fields - note we need to provide required fields
        min_test_run = QTestTestRun(id=2, test_case_id=102)  # With ID to bypass creation validation
        assert min_test_run.id == 2
        assert min_test_run.name is None
        assert min_test_run.description is None
        assert min_test_run.test_case_id == 102
        assert min_test_run.test_cycle_id is None
        assert len(min_test_run.properties) == 0

    def test_qtest_test_log(self):
        """Test QTestTestLog model."""
        # Create with all fields
        execution_date = datetime.now()
        test_log = QTestTestLog(
            id=1,
            status="Passed",  # Updated to use valid status
            execution_date=execution_date,
            note="Test passed successfully",
            test_run_id=123,  # Added required field
            attachments=[QTestAttachment(id=1, name="result.log", content_type="text/plain")],
            properties=[QTestCustomField(id=1, name="Execution Time", type="NUMBER", value=5.2)],
        )
        assert test_log.id == 1
        assert test_log.status == "Passed"
        assert test_log.execution_date == execution_date
        assert test_log.note == "Test passed successfully"
        assert test_log.test_run_id == 123
        assert len(test_log.attachments) == 1
        assert test_log.attachments[0].name == "result.log"
        assert len(test_log.properties) == 1
        assert test_log.properties[0].field_name == "Execution Time"

        # Create with minimum fields
        min_test_log = QTestTestLog(
            id=2,  # With ID to bypass creation validation
            status="Failed",  # Updated to use valid status
        )
        assert min_test_log.id == 2
        assert min_test_log.status == "Failed"
        assert min_test_log.execution_date is None
        assert min_test_log.note is None
        assert len(min_test_log.attachments) == 0
        assert len(min_test_log.properties) == 0

    def test_qtest_test_execution(self):
        """Test QTestTestExecution model."""
        # Create with all fields
        execution_date = datetime.now()
        test_execution = QTestTestExecution(
            id=1,
            test_run_id=101,
            status="Passed",  # Updated to match valid status
            execution_date=execution_date,
            executed_by=1001,
            note="Test passed successfully",
            attachments=[QTestAttachment(id=1, name="result.log", content_type="text/plain")],
            test_step_logs=[
                {
                    "stepId": 201,
                    "status": "Passed",
                    "actualResult": "Login page displayed correctly",
                },
                {"stepId": 202, "status": "Passed", "actualResult": "Logged in successfully"},
            ],
        )
        assert test_execution.id == 1
        assert test_execution.test_run_id == 101
        assert test_execution.status == "Passed"
        assert test_execution.execution_date == execution_date
        assert test_execution.executed_by == 1001
        assert test_execution.note == "Test passed successfully"
        assert len(test_execution.attachments) == 1
        assert test_execution.attachments[0].name == "result.log"
        assert len(test_execution.test_step_logs) == 2
        assert test_execution.test_step_logs[0]["stepId"] == 201
        assert test_execution.test_step_logs[1]["status"] == "Passed"

        # Validation should fail if required fields are missing
        with pytest.raises(ValidationError):
            QTestTestExecution(id=1, status="Passed")  # Missing test_run_id and execution_date

    def test_qtest_parameter(self):
        """Test QTestParameter model."""
        # Create with all fields

        parameter = QTestParameter(
            id=1,
            name="Browser",
            description="Browser type",
            project_id=12345,
            status="Active",  # Updated to match valid status
            values=[
                QTestParameterValue(id=101, value="Chrome", parameter_id=1),
                QTestParameterValue(id=102, value="Firefox", parameter_id=1),
            ],
        )
        assert parameter.id == 1
        assert parameter.name == "Browser"
        assert parameter.description == "Browser type"
        assert parameter.project_id == 12345
        assert parameter.status == "Active"
        assert len(parameter.values) == 2
        assert parameter.values[0].value == "Chrome"
        assert parameter.values[1].value == "Firefox"

        # Create with minimum fields
        min_parameter = QTestParameter(name="Minimal Parameter")
        assert min_parameter.id is None
        assert min_parameter.name == "Minimal Parameter"
        assert min_parameter.description is None
        assert min_parameter.project_id is None
        assert min_parameter.status is None
        assert len(min_parameter.values) == 0

    def test_qtest_pulse_event_type(self):
        """Test QTestPulseEventType enum."""
        # Verify enum values
        assert "TEST_CASE_CREATED" in QTestPulseEventType.__members__
        assert "TEST_LOG_CREATED" in QTestPulseEventType.__members__
        assert "TEST_CASE_UPDATED" in QTestPulseEventType.__members__

        # Use enum values
        assert QTestPulseEventType.TEST_CASE_CREATED == "TEST_CASE_CREATED"
        assert QTestPulseEventType.TEST_LOG_CREATED == "TEST_LOG_CREATED"

    def test_qtest_pulse_action_type(self):
        """Test QTestPulseActionType enum."""
        # Verify enum values
        assert "CREATE_DEFECT" in QTestPulseActionType.__members__
        assert "SEND_MAIL" in QTestPulseActionType.__members__
        assert "UPDATE_FIELD_VALUE" in QTestPulseActionType.__members__

        # Use enum values
        assert QTestPulseActionType.CREATE_DEFECT == "CREATE_DEFECT"
        assert QTestPulseActionType.SEND_MAIL == "SEND_MAIL"

    def test_qtest_pulse_trigger(self):
        """Test QTestPulseTrigger model."""
        # Create with all fields
        now = datetime.now().isoformat()

        trigger = QTestPulseTrigger(
            id=1,
            name="Test Trigger",
            event_type=QTestPulseEventType.TEST_CASE_CREATED,
            project_id=12345,
            conditions=[QTestPulseCondition(field="status", operator="equals", value="FAIL")],
            created_by={"id": 100, "name": "Admin"},
            created_date=now,
        )

        assert trigger.id == 1
        assert trigger.name == "Test Trigger"
        assert trigger.event_type == "TEST_CASE_CREATED"
        assert trigger.project_id == 12345
        assert len(trigger.conditions) == 1
        assert trigger.conditions[0].field == "status"
        assert trigger.created_by["id"] == 100
        assert isinstance(trigger.created_date, datetime)
        assert trigger.updated_by is None
        assert trigger.updated_date is None

        # Create with minimum fields
        min_trigger = QTestPulseTrigger(
            name="Minimal Trigger",
            event_type="TEST_CASE_CREATED",
            project_id=12345,
            created_by={"id": 100, "name": "Admin"},
            created_date=now,
        )
        assert min_trigger.id is None
        assert min_trigger.name == "Minimal Trigger"
        assert min_trigger.event_type == "TEST_CASE_CREATED"
        assert len(min_trigger.conditions) == 0

    def test_qtest_pulse_action(self):
        """Test QTestPulseAction model."""
        # Create with all fields
        now = datetime.now().isoformat()
        action = QTestPulseAction(
            id=1,
            name="Send Email",
            action_type=QTestPulseActionType.SEND_MAIL,
            project_id=12345,
            parameters=[
                QTestPulseActionParameter(name="recipients", value="test@example.com"),
                QTestPulseActionParameter(name="subject", value="Test Failed"),
            ],
            created_by={"id": 100, "name": "Admin"},
            created_date=now,
        )

        assert action.id == 1
        assert action.name == "Send Email"
        assert action.action_type == "SEND_MAIL"
        assert action.project_id == 12345
        assert len(action.parameters) == 2
        assert action.parameters[0].name == "recipients"
        assert action.created_by["id"] == 100
        assert isinstance(action.created_date, datetime)
        assert action.updated_by is None
        assert action.updated_date is None

        # Create with minimum fields
        min_action = QTestPulseAction(
            name="Minimal Action",
            action_type="CREATE_DEFECT",
            project_id=12345,
            created_by={"id": 100, "name": "Admin"},
            created_date=now,
        )
        assert min_action.id is None
        assert min_action.name == "Minimal Action"
        assert min_action.action_type == "CREATE_DEFECT"
        assert len(min_action.parameters) == 0

    def test_qtest_pulse_constant(self):
        """Test QTestPulseConstant model."""
        # Create with all fields
        now = datetime.now().isoformat()
        constant = QTestPulseConstant(
            id=1,
            name="EMAIL_RECIPIENT",
            value="test@example.com",
            description="Default email recipient",
            project_id=12345,
            created_by={"id": 100, "name": "Admin"},
            created_date=now,
        )

        assert constant.id == 1
        assert constant.name == "EMAIL_RECIPIENT"
        assert constant.value == "test@example.com"
        assert constant.description == "Default email recipient"
        assert constant.project_id == 12345
        assert constant.created_by["id"] == 100
        assert isinstance(constant.created_date, datetime)
        assert constant.updated_by is None
        assert constant.updated_date is None

        # Create with minimum fields
        min_constant = QTestPulseConstant(
            name="API_KEY",
            value="abc123",
            project_id=12345,
            created_by={"id": 100, "name": "Admin"},
            created_date=now,
        )
        assert min_constant.id is None
        assert min_constant.name == "API_KEY"
        assert min_constant.value == "abc123"
        assert min_constant.description is None

    def test_qtest_pulse_rule(self):
        """Test QTestPulseRule model."""
        # Create with all fields
        now = datetime.now().isoformat()
        rule = QTestPulseRule(
            id=1,
            name="Test Failure Notification",
            description="Send email when test fails",
            project_id=12345,
            enabled=True,
            trigger_id=101,
            action_id=201,
            created_by={"id": 100, "name": "Admin"},
            created_date=now,
        )

        assert rule.id == 1
        assert rule.name == "Test Failure Notification"
        assert rule.description == "Send email when test fails"
        assert rule.project_id == 12345
        assert rule.enabled is True
        assert rule.trigger_id == 101
        assert rule.action_id == 201
        assert rule.created_by["id"] == 100
        assert isinstance(rule.created_date, datetime)
        assert rule.updated_by is None
        assert rule.updated_date is None

        # Create with minimum fields
        min_rule = QTestPulseRule(
            name="Minimal Rule",
            project_id=12345,
            trigger_id=101,
            action_id=201,
            created_by={"id": 100, "name": "Admin"},
            created_date=now,
        )
        assert min_rule.id is None
        assert min_rule.name == "Minimal Rule"
        assert min_rule.description is None
        assert min_rule.enabled is True  # Default value

    def test_qtest_dataset(self):
        """Test QTestDataset model."""
        # Create with all fields

        dataset = QTestDataset(
            id=1,
            name="Login Test Data",
            description="Test data for login scenarios",
            project_id=12345,
            status="Active",  # Updated to match valid status
            parameter_names=["username", "password", "expected"],  # Added parameter names
            rows=[
                QTestDatasetRow(
                    id=201,
                    dataset_id=1,
                    values={"username": "user1", "password": "pass1", "expected": "success"},
                ),
                QTestDatasetRow(
                    id=202,
                    dataset_id=1,
                    values={"username": "user2", "password": "wrong", "expected": "failure"},
                ),
            ],
        )
        assert dataset.id == 1
        assert dataset.name == "Login Test Data"
        assert dataset.description == "Test data for login scenarios"
        assert dataset.project_id == 12345
        assert dataset.status == "Active"
        assert len(dataset.rows) == 2
        assert dataset.rows[0].values["username"] == "user1"
        assert dataset.rows[1].values["expected"] == "failure"

        # Create with minimum fields
        min_dataset = QTestDataset(name="Minimal Dataset")
        assert min_dataset.id is None
        assert min_dataset.name == "Minimal Dataset"
        assert min_dataset.description is None
        assert min_dataset.project_id is None
        assert min_dataset.status is None
        assert len(min_dataset.rows) == 0
