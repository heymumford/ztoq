"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import base64
from datetime import datetime, timezone
import uuid
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
    QTestScenarioFeature,
    QTestStep,
    QTestTestCase,
    QTestTestCycle,
    QTestTestExecution,
    QTestTestLog,
    QTestTestRun,
)

@pytest.mark.unit
class TestQTestModelRelationships:
    """Tests for relationships between qTest entity models."""
    
    def test_project_to_module_relationship(self):
        """Test relationship between projects and modules."""
        # Create a project
        project = QTestProject(
            id=12345,
            name="Test Project",
            description="Test Project Description",
            status="active"
        )
        
        # Create a module linked to the project
        module = QTestModule(
            id=101,
            name="Test Module",
            description="Test Module Description",
            projectId=project.id,
            parentId=None
        )
        
        # Validate relationship
        assert module.projectId == project.id
        
        # Create a child module
        child_module = QTestModule(
            id=102,
            name="Child Module",
            description="Child Module Description",
            projectId=project.id,
            parentId=module.id
        )
        
        # Validate parent-child relationship
        assert child_module.parentId == module.id
        assert child_module.projectId == project.id
    
    def test_module_to_test_case_relationship(self):
        """Test relationship between modules and test cases."""
        # Create a module
        module = QTestModule(
            id=101,
            name="Test Module",
            description="Test Module Description",
            projectId=12345,
            parentId=None
        )
        
        # Create a test case linked to the module
        test_case = QTestTestCase(
            id=201,
            name="Test Case",
            description="Test Case Description",
            projectId=12345,
            moduleId=module.id,
            precondition="Test precondition"
        )
        
        # Validate relationship
        assert test_case.moduleId == module.id
        assert test_case.projectId == module.projectId
        
        # Create test steps for the test case
        steps = [
            QTestStep(
                id=501,
                description="Step 1",
                expectedResult="Expected result 1",
                testCaseId=test_case.id,
                index=1
            ),
            QTestStep(
                id=502,
                description="Step 2",
                expectedResult="Expected result 2",
                testCaseId=test_case.id,
                index=2
            )
        ]
        
        # Validate step relationships
        for step in steps:
            assert step.testCaseId == test_case.id
    
    def test_full_test_execution_hierarchy(self):
        """Test full hierarchy from project to test execution."""
        # Create a project
        project = QTestProject(
            id=12345,
            name="Test Project",
            description="Test Project Description",
            status="active"
        )
        
        # Create a release
        release = QTestRelease(
            id=301,
            name="Release 1.0",
            description="First release",
            projectId=project.id,
            status="active"
        )
        
        # Create a test cycle
        test_cycle = QTestTestCycle(
            id=401,
            name="Test Cycle 1",
            description="First test cycle",
            projectId=project.id,
            releaseId=release.id,
            status="in_progress"
        )
        
        # Create a module
        module = QTestModule(
            id=101,
            name="Test Module",
            description="Test Module Description",
            projectId=project.id,
            parentId=None
        )
        
        # Create a test case
        test_case = QTestTestCase(
            id=201,
            name="Test Case",
            description="Test Case Description",
            projectId=project.id,
            moduleId=module.id,
            precondition="Test precondition"
        )
        
        # Create a test run
        test_run = QTestTestRun(
            id=601,
            name="Test Run 1",
            description="First test run",
            projectId=project.id,
            testCaseId=test_case.id,
            testCycleId=test_cycle.id,
            status="ready"
        )
        
        # Create a test log
        test_log = QTestTestLog(
            id=701,
            status="passed",
            executionDate=datetime.now(timezone.utc),
            testRunId=test_run.id,
            note="Test passed successfully"
        )
        
        # Validate relationships
        assert test_cycle.projectId == project.id
        assert test_cycle.releaseId == release.id
        assert release.projectId == project.id
        assert test_case.projectId == project.id
        assert test_case.moduleId == module.id
        assert test_run.testCaseId == test_case.id
        assert test_run.testCycleId == test_cycle.id
        assert test_log.testRunId == test_run.id
    
    def test_custom_field_relationships(self):
        """Test custom field relationships with other entities."""
        # Create a custom field for a test case
        custom_field = QTestCustomField(
            id=801,
            fieldName="Priority",
            fieldType="TEXT",
            entityType="TEST_CASE",
            isRequired=False,
            allowedValues=["High", "Medium", "Low"]
        )
        
        # Create a test case
        test_case = QTestTestCase(
            id=201,
            name="Test Case",
            description="Test Case Description",
            projectId=12345,
            moduleId=101,
            precondition="Test precondition",
            customFields=[
                {
                    "fieldId": custom_field.id,
                    "fieldName": custom_field.fieldName,
                    "fieldType": custom_field.fieldType,
                    "fieldValue": "High"
                }
            ]
        )
        
        # Validate relationship
        assert len(test_case.customFields) == 1
        assert test_case.customFields[0]["fieldId"] == custom_field.id
        assert test_case.customFields[0]["fieldName"] == custom_field.fieldName
        assert test_case.customFields[0]["fieldValue"] in custom_field.allowedValues

@pytest.mark.unit
class TestQTestModelValidations:
    """Tests for qTest model validations and constraints."""
    
    def test_qtest_config_validation(self):
        """Test validation rules for QTestConfig."""
        # Test valid URL
        valid_config = QTestConfig(
            base_url="https://example.qtest.com",
            username="test_user",
            password="test_password"
        )
        assert valid_config.base_url == "https://example.qtest.com"
        
        # Test URL normalization - adding trailing slash
        config_with_slash = QTestConfig(
            base_url="https://example.qtest.com/",
            username="test_user",
            password="test_password"
        )
        assert config_with_slash.base_url == "https://example.qtest.com"  # Trailing slash removed
        
        # Test adding protocol if missing
        config_without_protocol = QTestConfig(
            base_url="example.qtest.com",
            username="test_user",
            password="test_password"
        )
        assert config_without_protocol.base_url.startswith("https://")
        
        # Test invalid URL
        with pytest.raises(ValidationError) as excinfo:
            QTestConfig(
                base_url="not a valid url",
                username="test_user",
                password="test_password"
            )
        assert "Invalid URL" in str(excinfo.value)
    
    def test_project_validation(self):
        """Test validation rules for QTestProject."""
        # Test valid project
        valid_project = QTestProject(
            id=12345,
            name="Test Project",
            description="Test Project Description",
            status="active"
        )
        assert valid_project.name == "Test Project"
        
        # Test missing required field
        with pytest.raises(ValidationError) as excinfo:
            QTestProject(
                id=12345,
                description="Test Project Description",
                status="active"
            )
        assert "name" in str(excinfo.value) and "field required" in str(excinfo.value)
        
        # Test invalid status
        with pytest.raises(ValidationError) as excinfo:
            QTestProject(
                id=12345,
                name="Test Project",
                description="Test Project Description",
                status="invalid_status"
            )
        assert "status" in str(excinfo.value) and "Invalid status" in str(excinfo.value)
    
    def test_test_case_validation(self):
        """Test validation rules for QTestTestCase."""
        # Test valid test case
        valid_test_case = QTestTestCase(
            id=201,
            name="Test Case",
            description="Test Case Description",
            projectId=12345,
            moduleId=101
        )
        assert valid_test_case.name == "Test Case"
        
        # Test missing required field
        with pytest.raises(ValidationError) as excinfo:
            QTestTestCase(
                id=201,
                description="Test Case Description",
                projectId=12345,
                moduleId=101
            )
        assert "name" in str(excinfo.value) and "field required" in str(excinfo.value)
        
        # Test name length validation
        with pytest.raises(ValidationError) as excinfo:
            QTestTestCase(
                id=201,
                name="a" * 501,  # Exceed max length
                description="Test Case Description",
                projectId=12345,
                moduleId=101
            )
        assert "name" in str(excinfo.value) and "ensure this value has at most" in str(excinfo.value)
    
    def test_test_log_validation(self):
        """Test validation rules for QTestTestLog."""
        # Test valid test log
        valid_test_log = QTestTestLog(
            id=701,
            status="Passed",
            executionDate=datetime.now(timezone.utc),
            testRunId=601
        )
        assert valid_test_log.status == "Passed"
        
        # Test invalid status
        with pytest.raises(ValidationError) as excinfo:
            QTestTestLog(
                id=701,
                status="InvalidStatus",
                executionDate=datetime.now(timezone.utc),
                testRunId=601
            )
        assert "status" in str(excinfo.value) and "Invalid status" in str(excinfo.value)
        
        # Test test step logs validation
        valid_test_log_with_steps = QTestTestLog(
            id=701,
            status="Passed",
            executionDate=datetime.now(timezone.utc),
            testRunId=601,
            testStepLogs=[
                {
                    "id": 801,
                    "status": "Passed",
                    "description": "Step 1 executed",
                    "expectedResult": "Expected result 1",
                    "actualResult": "Actual result 1",
                    "order": 1
                },
                {
                    "id": 802,
                    "status": "Passed",
                    "description": "Step 2 executed",
                    "expectedResult": "Expected result 2",
                    "actualResult": "Actual result 2",
                    "order": 2
                }
            ]
        )
        assert len(valid_test_log_with_steps.testStepLogs) == 2
        
        # Test invalid test step log
        with pytest.raises(ValidationError) as excinfo:
            QTestTestLog(
                id=701,
                status="Passed",
                executionDate=datetime.now(timezone.utc),
                testRunId=601,
                testStepLogs=[
                    {
                        "id": 801,
                        "status": "InvalidStatus",  # Invalid status
                        "description": "Step 1 executed",
                        "expectedResult": "Expected result 1",
                        "actualResult": "Actual result 1",
                        "order": 1
                    }
                ]
            )
        assert "testStepLogs" in str(excinfo.value) and "Invalid status" in str(excinfo.value)
    
    def test_attachment_validation(self):
        """Test validation rules for QTestAttachment."""
        # Test valid attachment with content
        test_content = "Test content".encode("utf-8")
        base64_content = base64.b64encode(test_content).decode("utf-8")
        
        valid_attachment = QTestAttachment(
            id=901,
            name="test.txt",
            contentType="text/plain",
            content=base64_content,
            size=len(test_content),
            webUrl="https://example.qtest.com/attachments/901"
        )
        assert valid_attachment.name == "test.txt"
        assert valid_attachment.contentType == "text/plain"
        
        # Test name validation
        with pytest.raises(ValidationError) as excinfo:
            QTestAttachment(
                id=901,
                name="",  # Empty name
                contentType="text/plain",
                content=base64_content,
                size=len(test_content)
            )
        assert "name" in str(excinfo.value) and "ensure this value has at least" in str(excinfo.value)
        
        # Test content type validation
        with pytest.raises(ValidationError) as excinfo:
            QTestAttachment(
                id=901,
                name="test.txt",
                contentType="invalid/type",  # Invalid content type
                content=base64_content,
                size=len(test_content)
            )
        assert "contentType" in str(excinfo.value) and "Invalid content type" in str(excinfo.value)

@pytest.mark.unit
class TestQTestPulseModels:
    """Tests specifically for qTest Pulse models."""
    
    def test_pulse_rule_creation(self):
        """Test creating a complete Pulse rule with all components."""
        # Create a trigger condition
        condition = QTestPulseCondition(
            id=1001,
            field="priority",
            operator="equals",
            value="High",
            valueType="STRING"
        )
        
        # Create a trigger
        trigger = QTestPulseTrigger(
            id=1101,
            name="High Priority Test Case",
            description="Trigger for high priority test cases",
            projectId=12345,
            eventType=QTestPulseEventType.TEST_CASE_CREATED,
            conditions=[condition]
        )
        
        # Create action parameters
        action_param = QTestPulseActionParameter(
            id=1201,
            name="message",
            value="New high priority test case created",
            description="Message to display"
        )
        
        # Create action
        action = QTestPulseAction(
            id=1301,
            name="Send Notification",
            description="Send notification to team",
            projectId=12345,
            actionType=QTestPulseActionType.SEND_NOTIFICATION,
            parameters=[action_param]
        )
        
        # Create rule
        rule = QTestPulseRule(
            id=1401,
            name="High Priority Test Case Notification",
            description="Notify team when high priority test cases are created",
            projectId=12345,
            enabled=True,
            triggerId=trigger.id,
            actionId=action.id
        )
        
        # Verify components
        assert rule.name == "High Priority Test Case Notification"
        assert rule.enabled is True
        assert rule.triggerId == trigger.id
        assert rule.actionId == action.id
        
        assert trigger.eventType == QTestPulseEventType.TEST_CASE_CREATED
        assert len(trigger.conditions) == 1
        assert trigger.conditions[0].field == "priority"
        
        assert action.actionType == QTestPulseActionType.SEND_NOTIFICATION
        assert len(action.parameters) == 1
        assert action.parameters[0].name == "message"
    
    def test_pulse_event_type_enum(self):
        """Test QTestPulseEventType enum values."""
        # Verify common event types
        assert QTestPulseEventType.TEST_CASE_CREATED.name == "TEST_CASE_CREATED"
        assert QTestPulseEventType.TEST_CASE_UPDATED.name == "TEST_CASE_UPDATED"
        assert QTestPulseEventType.TEST_RUN_CREATED.name == "TEST_RUN_CREATED"
        assert QTestPulseEventType.TEST_RUN_UPDATED.name == "TEST_RUN_UPDATED"
        assert QTestPulseEventType.TEST_LOG_SUBMITTED.name == "TEST_LOG_SUBMITTED"
        
        # Test using enum in a model
        trigger = QTestPulseTrigger(
            id=1101,
            name="Test Case Created Trigger",
            description="Trigger when test case is created",
            projectId=12345,
            eventType=QTestPulseEventType.TEST_CASE_CREATED,
            conditions=[]
        )
        assert trigger.eventType == QTestPulseEventType.TEST_CASE_CREATED
    
    def test_pulse_action_type_enum(self):
        """Test QTestPulseActionType enum values."""
        # Verify common action types
        assert QTestPulseActionType.SEND_MAIL.name == "SEND_MAIL"
        assert QTestPulseActionType.CREATE_DEFECT.name == "CREATE_DEFECT"
        assert QTestPulseActionType.UPDATE_TEST_CASE.name == "UPDATE_TEST_CASE"
        assert QTestPulseActionType.SEND_NOTIFICATION.name == "SEND_NOTIFICATION"
        
        # Test using enum in a model
        action = QTestPulseAction(
            id=1301,
            name="Send Email Action",
            description="Send email notification",
            projectId=12345,
            actionType=QTestPulseActionType.SEND_MAIL,
            parameters=[]
        )
        assert action.actionType == QTestPulseActionType.SEND_MAIL

@pytest.mark.unit
class TestQTestParametersModels:
    """Tests specifically for qTest Parameters models."""
    
    def test_parameter_and_values(self):
        """Test parameter creation with values."""
        # Create parameter values
        values = [
            QTestParameterValue(id=1501, parameterId=1601, value="Value 1"),
            QTestParameterValue(id=1502, parameterId=1601, value="Value 2"),
            QTestParameterValue(id=1503, parameterId=1601, value="Value 3")
        ]
        
        # Create parameter
        parameter = QTestParameter(
            id=1601,
            name="Test Parameter",
            description="Test parameter description",
            projectId=12345,
            status="ACTIVE",
            values=values
        )
        
        # Verify parameter and values
        assert parameter.name == "Test Parameter"
        assert parameter.status == "ACTIVE"
        assert len(parameter.values) == 3
        assert parameter.values[0].value == "Value 1"
        assert parameter.values[0].parameterId == parameter.id
    
    def test_dataset_and_rows(self):
        """Test dataset creation with rows."""
        # Create dataset columns
        columns = [
            {"name": "Column 1", "dataType": "STRING"},
            {"name": "Column 2", "dataType": "BOOLEAN"},
            {"name": "Column 3", "dataType": "NUMERIC"}
        ]
        
        # Create dataset
        dataset = QTestDataset(
            id=1701,
            name="Test Dataset",
            description="Test dataset description",
            projectId=12345,
            columns=columns
        )
        
        # Create dataset rows
        row1 = QTestDatasetRow(
            id=1801,
            datasetId=dataset.id,
            cells=[
                {"columnName": "Column 1", "value": "Value 1"},
                {"columnName": "Column 2", "value": "true"},
                {"columnName": "Column 3", "value": "42"}
            ]
        )
        
        row2 = QTestDatasetRow(
            id=1802,
            datasetId=dataset.id,
            cells=[
                {"columnName": "Column 1", "value": "Value 2"},
                {"columnName": "Column 2", "value": "false"},
                {"columnName": "Column 3", "value": "43"}
            ]
        )
        
        # Verify dataset and rows
        assert dataset.name == "Test Dataset"
        assert len(dataset.columns) == 3
        
        assert row1.datasetId == dataset.id
        assert len(row1.cells) == 3
        assert row1.cells[0]["columnName"] == "Column 1"
        assert row1.cells[0]["value"] == "Value 1"
        
        assert row2.datasetId == dataset.id
        assert len(row2.cells) == 3
        assert row2.cells[2]["columnName"] == "Column 3"
        assert row2.cells[2]["value"] == "43"
    
    def test_dataset_validation(self):
        """Test dataset validation rules."""
        # Test valid dataset
        valid_dataset = QTestDataset(
            id=1701,
            name="Test Dataset",
            description="Test dataset description",
            projectId=12345,
            columns=[{"name": "Column 1", "dataType": "STRING"}]
        )
        assert valid_dataset.name == "Test Dataset"
        
        # Test missing required field
        with pytest.raises(ValidationError) as excinfo:
            QTestDataset(
                id=1701,
                description="Test dataset description",
                projectId=12345,
                columns=[{"name": "Column 1", "dataType": "STRING"}]
            )
        assert "name" in str(excinfo.value) and "field required" in str(excinfo.value)
        
        # Test invalid column data type
        with pytest.raises(ValidationError) as excinfo:
            QTestDataset(
                id=1701,
                name="Test Dataset",
                description="Test dataset description",
                projectId=12345,
                columns=[{"name": "Column 1", "dataType": "INVALID_TYPE"}]
            )
        assert "columns" in str(excinfo.value) and "INVALID_TYPE" in str(excinfo.value)

@pytest.mark.unit
class TestQTestScenarioModels:
    """Tests specifically for qTest Scenario models."""
    
    def test_scenario_feature(self):
        """Test scenario feature creation and validation."""
        # Test valid feature
        valid_feature = QTestScenarioFeature(
            id=1901,
            name="Test Feature",
            description="Test feature description",
            projectId=12345,
            content="""
            Feature: Login Functionality
              As a user
              I want to log in to the system
              So that I can access my account
              
              Scenario: Successful login
                Given I am on the login page
                When I enter valid credentials
                And I click the login button
                Then I should be logged in successfully
            """
        )
        assert valid_feature.name == "Test Feature"
        assert "Feature: Login Functionality" in valid_feature.content
        
        # Test missing required field
        with pytest.raises(ValidationError) as excinfo:
            QTestScenarioFeature(
                id=1901,
                description="Test feature description",
                projectId=12345,
                content="Feature: Login Functionality"
            )
        assert "name" in str(excinfo.value) and "field required" in str(excinfo.value)
        
        # Test missing content
        with pytest.raises(ValidationError) as excinfo:
            QTestScenarioFeature(
                id=1901,
                name="Test Feature",
                description="Test feature description",
                projectId=12345
            )
        assert "content" in str(excinfo.value) and "field required" in str(excinfo.value)

@pytest.mark.unit
class TestModelSerialization:
    """Tests for serialization and deserialization of models."""
    
    def test_model_to_dict_conversion(self):
        """Test converting models to dictionaries for API requests."""
        # Create a test case
        test_case = QTestTestCase(
            id=201,
            name="Test Case",
            description="Test Case Description",
            projectId=12345,
            moduleId=101,
            precondition="Test precondition",
            steps=[
                QTestStep(
                    id=501,
                    description="Step 1",
                    expectedResult="Expected result 1",
                    testCaseId=201,
                    index=1
                ),
                QTestStep(
                    id=502,
                    description="Step 2",
                    expectedResult="Expected result 2",
                    testCaseId=201,
                    index=2
                )
            ]
        )
        
        # Convert to dict and verify
        test_case_dict = test_case.model_dump()
        assert isinstance(test_case_dict, dict)
        assert test_case_dict["id"] == 201
        assert test_case_dict["name"] == "Test Case"
        assert len(test_case_dict["steps"]) == 2
        assert test_case_dict["steps"][0]["description"] == "Step 1"
        
        # Test with exclude
        test_case_dict_no_id = test_case.model_dump(exclude={"id"})
        assert "id" not in test_case_dict_no_id
        assert test_case_dict_no_id["name"] == "Test Case"
    
    def test_dict_to_model_conversion(self):
        """Test creating models from dictionaries (API responses)."""
        # Create a dict representing API response
        test_log_dict = {
            "id": 701,
            "status": "Passed",
            "executionDate": "2025-01-01T10:00:00Z",
            "testRunId": 601,
            "note": "Test passed successfully",
            "testStepLogs": [
                {
                    "id": 801,
                    "status": "Passed",
                    "description": "Step 1 executed",
                    "expectedResult": "Expected result 1",
                    "actualResult": "Actual result 1",
                    "order": 1
                }
            ]
        }
        
        # Convert to model
        test_log = QTestTestLog(**test_log_dict)
        
        # Verify conversion
        assert test_log.id == 701
        assert test_log.status == "Passed"
        assert test_log.testRunId == 601
        assert len(test_log.testStepLogs) == 1
        assert test_log.testStepLogs[0]["status"] == "Passed"
    
    def test_model_json_serialization(self):
        """Test JSON serialization of models."""
        # Create a model with various types
        release = QTestRelease(
            id=301,
            name="Release 1.0",
            description="First release",
            projectId=12345,
            status="active",
            startDate=datetime(2025, 1, 1, tzinfo=timezone.utc),
            endDate=datetime(2025, 12, 31, tzinfo=timezone.utc)
        )
        
        # Convert to JSON and verify
        release_json = release.model_dump_json()
        assert isinstance(release_json, str)
        
        # Import json to parse and verify
        import json
        release_dict = json.loads(release_json)
        assert release_dict["id"] == 301
        assert release_dict["name"] == "Release 1.0"
        assert release_dict["startDate"].startswith("2025-01-01")
        assert release_dict["endDate"].startswith("2025-12-31")

@pytest.mark.unit
class TestPaginatedResponse:
    """Tests for the paginated response model."""
    
    def test_paginated_response_parsing(self):
        """Test parsing paginated API responses."""
        # Create a paginated response of test cases
        test_cases_data = {
            "page": 1,
            "pageSize": 10,
            "total": 25,
            "items": [
                {
                    "id": 201,
                    "name": "Test Case 1",
                    "projectId": 12345,
                    "moduleId": 101
                },
                {
                    "id": 202,
                    "name": "Test Case 2",
                    "projectId": 12345,
                    "moduleId": 101
                }
            ]
        }
        
        # Parse as paginated response of test cases
        paginated_response = QTestPaginatedResponse(
            page=test_cases_data["page"],
            pageSize=test_cases_data["pageSize"],
            total=test_cases_data["total"],
            items=[QTestTestCase(**item) for item in test_cases_data["items"]]
        )
        
        # Verify response
        assert paginated_response.page == 1
        assert paginated_response.pageSize == 10
        assert paginated_response.total == 25
        assert len(paginated_response.items) == 2
        assert isinstance(paginated_response.items[0], QTestTestCase)
        assert paginated_response.items[0].name == "Test Case 1"
        assert paginated_response.items[1].name == "Test Case 2"
    
    def test_paginated_response_navigation(self):
        """Test navigation helpers in paginated responses."""
        # Create a paginated response with navigation info
        paginated_response = QTestPaginatedResponse(
            page=2,
            pageSize=10,
            total=25,
            items=[]  # Items not important for this test
        )
        
        # Verify navigation properties
        assert paginated_response.has_previous
        assert paginated_response.has_next
        assert paginated_response.pages == 3  # 25 items with 10 per page = 3 pages
        assert paginated_response.next_page == 3
        assert paginated_response.previous_page == 1
        
        # Test first page
        first_page = QTestPaginatedResponse(
            page=1,
            pageSize=10,
            total=25,
            items=[]
        )
        assert not first_page.has_previous
        assert first_page.has_next
        assert first_page.next_page == 2
        assert first_page.previous_page is None
        
        # Test last page
        last_page = QTestPaginatedResponse(
            page=3,
            pageSize=10,
            total=25,
            items=[]
        )
        assert last_page.has_previous
        assert not last_page.has_next
        assert last_page.next_page is None
        assert last_page.previous_page == 2