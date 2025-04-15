"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import pytest
from ztoq.qtest_mock_server import QTestMockServer


@pytest.mark.unit()
class TestQTestMockServer:
    @pytest.fixture()
    def mock_server(self):
        """Create a test qTest mock server instance."""
        return QTestMockServer()

    def test_initialization(self, mock_server):
        """Test mock server initialization."""
        # Verify data stores are initialized
        assert "manager" in mock_server.data
        assert "parameters" in mock_server.data
        assert "pulse" in mock_server.data
        assert "scenario" in mock_server.data

        # Verify sample data was loaded
        assert len(mock_server.data["manager"]["projects"]) > 0
        assert len(mock_server.data["manager"]["modules"]) > 0
        assert len(mock_server.data["manager"]["test_cases"]) > 0
        assert len(mock_server.data["manager"]["test_cycles"]) > 0

    def test_handle_auth(self, mock_server):
        """Test authentication handler."""
        # Test for Manager API
        manager_auth = mock_server._handle_auth("manager")
        assert "access_token" in manager_auth
        assert manager_auth["token_type"] == "bearer"
        assert manager_auth["expires_in"] > 0

        # Test for Parameters API
        params_auth = mock_server._handle_auth("parameters")
        assert "access_token" in params_auth
        assert params_auth["token_type"] == "bearer"
        assert params_auth["expires_in"] > 0

    def test_handle_get_projects(self, mock_server):
        """Test getting projects."""
        # Test with default pagination
        result = mock_server._handle_get_projects({})
        assert "page" in result
        assert "pageSize" in result
        assert "total" in result
        assert "items" in result
        assert len(result["items"]) > 0

        # Test with custom pagination
        result = mock_server._handle_get_projects({"page": 1, "pageSize": 1})
        assert result["page"] == 1
        assert result["pageSize"] == 1
        assert len(result["items"]) <= 1

    def test_handle_get_test_cases(self, mock_server):
        """Test getting test cases."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]

        # Test with default parameters
        result = mock_server._handle_get_test_cases(project_id, {})
        assert "page" in result
        assert "pageSize" in result
        assert "total" in result
        assert "items" in result
        assert len(result["items"]) > 0

        # Test filtering by module
        module_id = mock_server.data["manager"]["modules"][102]["id"]
        result = mock_server._handle_get_test_cases(project_id, {"parentId": module_id})
        for tc in result["items"]:
            assert tc["moduleId"] == module_id

    def test_handle_get_test_case(self, mock_server):
        """Test getting a single test case."""
        # Get first test case ID
        first_tc_id = next(iter(mock_server.data["manager"]["test_cases"]))

        # Get test case
        result = mock_server._handle_get_test_case(first_tc_id)
        assert result["id"] == first_tc_id
        assert "name" in result
        assert "steps" in result

        # Test with non-existent ID
        result = mock_server._handle_get_test_case(99999)
        assert "error" in result

    def test_handle_create_test_case(self, mock_server):
        """Test creating a test case."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]

        # Create test case data
        test_case_data = {
            "name": "New Test Case",
            "description": "Description of new test case",
            "precondition": "Precondition for test case",
            "moduleId": list(mock_server.data["manager"]["modules"].keys())[0],
            "steps": [
                {"description": "Step 1", "expectedResult": "Result 1"},
                {"description": "Step 2", "expectedResult": "Result 2"},
            ],
        }

        # Create test case
        result = mock_server._handle_create_test_case(project_id, test_case_data)

        # Verify result
        assert result["id"] > 0
        assert result["name"] == "New Test Case"
        assert result["description"] == "Description of new test case"
        assert len(result["steps"]) == 2
        assert result["steps"][0]["description"] == "Step 1"
        assert result["steps"][1]["expectedResult"] == "Result 2"

        # Verify the test case was stored in the mock server
        assert result["id"] in mock_server.data["manager"]["test_cases"]
        # Verify steps were stored
        for step in result["steps"]:
            assert step["id"] in mock_server.data["manager"]["test_steps"]

    def test_handle_upload_attachment(self, mock_server):
        """Test uploading an attachment."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]

        # Define object type and ID
        object_type = "test-cases"
        object_id = list(mock_server.data["manager"]["test_cases"].keys())[0]

        # Create mock file
        filename = "test_file.txt"
        content = b"This is test content"
        content_type = "text/plain"
        files = {"file": (filename, content, content_type)}

        # Upload attachment
        result = mock_server._handle_upload_attachment(project_id, object_type, object_id, files)

        # Verify result
        assert result["id"] > 0
        assert result["name"] == filename
        assert result["contentType"] == content_type
        assert result["size"] == len(content)
        assert "webUrl" in result

        # Verify attachment was stored
        assert result["id"] in mock_server.data["manager"]["attachments"]

    def test_handle_query_parameters(self, mock_server):
        """Test querying parameters."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]

        # Query parameters
        result = mock_server._handle_query_parameters(project_id, {"offset": 0, "limit": 10})

        # Verify result structure
        assert "offset" in result
        assert "limit" in result
        assert "total" in result
        assert "data" in result
        assert isinstance(result["data"], list)

        # Should contain parameters with matching project ID
        for param in result["data"]:
            assert param["projectId"] == project_id

    def test_handle_create_parameter(self, mock_server):
        """Test creating a parameter."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]

        # Parameter data
        param_data = {
            "name": "New Parameter",
            "description": "New parameter description",
            "projectId": project_id,
            "status": "ACTIVE",
            "values": [{"value": "Value 1"}, {"value": "Value 2"}],
        }

        # Create parameter
        result = mock_server._handle_create_parameter(param_data)

        # Verify result structure
        assert "status" in result
        assert result["status"] == "SUCCESS"
        assert "data" in result
        assert result["data"]["name"] == "New Parameter"
        assert result["data"]["description"] == "New parameter description"

        # Verify parameter was stored
        param_id = result["data"]["id"]
        assert param_id in mock_server.data["parameters"]["parameters"]

        # Verify parameter values were stored if provided
        if "values" in param_data:
            values = [
                v
                for v in mock_server.data["parameters"]["parameter_values"].values()
                if v.get("parameterId") == param_id
            ]
            assert len(values) == len(param_data["values"])

    def test_handle_pulse_api(self, mock_server):
        """Test Pulse API functionality."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]

        # Test getting rules
        rules_result = mock_server._handle_get_rules(project_id)
        assert "data" in rules_result
        assert isinstance(rules_result["data"], list)

        # Test creating a rule
        rule_data = {
            "name": "New Test Rule",
            "description": "New rule description",
            "projectId": project_id,
            "enabled": True,
            "triggerId": 1001,  # Use existing sample trigger ID
            "actionId": 2001,  # Use existing sample action ID
        }
        create_rule_result = mock_server._handle_create_rule(rule_data)
        assert "data" in create_rule_result
        assert create_rule_result["data"]["name"] == "New Test Rule"
        rule_id = create_rule_result["data"]["id"]

        # Test getting a specific rule
        get_rule_result = mock_server._handle_get_rule(rule_id)
        assert "data" in get_rule_result
        assert get_rule_result["data"]["name"] == "New Test Rule"

        # Test updating a rule
        update_data = {"name": "Updated Rule Name", "description": "Updated description"}
        update_rule_result = mock_server._handle_update_rule(rule_id, update_data)
        assert "data" in update_rule_result
        assert update_rule_result["data"]["name"] == "Updated Rule Name"

        # Test executing a rule
        execute_rule_result = mock_server._handle_execute_rule(rule_id)
        assert "data" in execute_rule_result
        assert "message" in execute_rule_result["data"]

        # Test deleting a rule
        delete_rule_result = mock_server._handle_delete_rule(rule_id)
        assert "success" in delete_rule_result
        assert rule_id not in mock_server.data["pulse"]["rules"]

    def test_handle_pulse_triggers(self, mock_server):
        """Test Pulse API trigger functionality."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]

        # Test getting triggers
        triggers_result = mock_server._handle_get_triggers(project_id)
        assert "data" in triggers_result
        assert isinstance(triggers_result["data"], list)

        # Test creating a trigger
        trigger_data = {
            "name": "New Test Trigger",
            "eventType": "TEST_CASE_UPDATED",
            "projectId": project_id,
            "conditions": [{"field": "priority", "operator": "equals", "value": "High"}],
        }
        create_trigger_result = mock_server._handle_create_trigger(trigger_data)
        assert "data" in create_trigger_result
        assert create_trigger_result["data"]["name"] == "New Test Trigger"
        trigger_id = create_trigger_result["data"]["id"]

        # Test getting a specific trigger
        get_trigger_result = mock_server._handle_get_trigger(str(trigger_id))
        assert "data" in get_trigger_result
        assert get_trigger_result["data"]["name"] == "New Test Trigger"

        # Test updating a trigger
        update_data = {"name": "Updated Trigger Name", "conditions": []}
        update_trigger_result = mock_server._handle_update_trigger(str(trigger_id), update_data)
        assert "data" in update_trigger_result
        assert update_trigger_result["data"]["name"] == "Updated Trigger Name"

        # Test deleting a trigger
        delete_trigger_result = mock_server._handle_delete_trigger(str(trigger_id))
        assert "success" in delete_trigger_result
        assert trigger_id not in mock_server.data["pulse"]["triggers"]

    def test_handle_pulse_actions(self, mock_server):
        """Test Pulse API action functionality."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]

        # Test getting actions
        actions_result = mock_server._handle_get_actions(project_id)
        assert "data" in actions_result
        assert isinstance(actions_result["data"], list)

        # Test creating an action
        action_data = {
            "name": "New Test Action",
            "actionType": "SEND_MAIL",
            "projectId": project_id,
            "parameters": [
                {"name": "recipients", "value": "test@example.com"},
                {"name": "subject", "value": "Test Subject"},
            ],
        }
        create_action_result = mock_server._handle_create_action(action_data)
        assert "data" in create_action_result
        assert create_action_result["data"]["name"] == "New Test Action"
        action_id = create_action_result["data"]["id"]

        # Test getting a specific action
        get_action_result = mock_server._handle_get_action(str(action_id))
        assert "data" in get_action_result
        assert get_action_result["data"]["name"] == "New Test Action"

        # Test updating an action
        update_data = {
            "name": "Updated Action Name",
            "parameters": [{"name": "recipients", "value": "updated@example.com"}],
        }
        update_action_result = mock_server._handle_update_action(str(action_id), update_data)
        assert "data" in update_action_result
        assert update_action_result["data"]["name"] == "Updated Action Name"

        # Test deleting an action
        delete_action_result = mock_server._handle_delete_action(str(action_id))
        assert "success" in delete_action_result
        assert action_id not in mock_server.data["pulse"]["actions"]

    def test_handle_pulse_constants(self, mock_server):
        """Test Pulse API constant functionality."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]

        # Test getting constants
        constants_result = mock_server._handle_get_constants(project_id)
        assert "data" in constants_result
        assert isinstance(constants_result["data"], list)

        # Test creating a constant
        constant_data = {
            "name": "NEW_TEST_CONSTANT",
            "value": "test value",
            "description": "Test constant description",
            "projectId": project_id,
        }
        create_constant_result = mock_server._handle_create_constant(constant_data)
        assert "data" in create_constant_result
        assert create_constant_result["data"]["name"] == "NEW_TEST_CONSTANT"
        constant_id = create_constant_result["data"]["id"]

        # Test getting a specific constant
        get_constant_result = mock_server._handle_get_constant(str(constant_id))
        assert "data" in get_constant_result
        assert get_constant_result["data"]["name"] == "NEW_TEST_CONSTANT"

        # Test updating a constant
        update_data = {"name": "UPDATED_CONSTANT", "value": "updated value"}
        update_constant_result = mock_server._handle_update_constant(str(constant_id), update_data)
        assert "data" in update_constant_result
        assert update_constant_result["data"]["name"] == "UPDATED_CONSTANT"

        # Test deleting a constant
        delete_constant_result = mock_server._handle_delete_constant(str(constant_id))
        assert "success" in delete_constant_result
        assert constant_id not in mock_server.data["pulse"]["constants"]

    def test_handle_get_features(self, mock_server):
        """Test getting Scenario features."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]

        # Get features
        result = mock_server._handle_get_features(project_id)

        # Verify result
        assert "data" in result
        assert isinstance(result["data"], list)

        # Should contain features with matching project ID
        for feature in result["data"]:
            assert feature["projectId"] == project_id

    def test_handle_create_feature(self, mock_server):
        """Test creating a Scenario feature."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]

        # Feature data
        feature_data = {
            "name": "New Feature",
            "description": "New feature description",
            "projectId": project_id,
            "content": """
            Feature: New Feature
              As a user
              I want to test a new feature
              So that I can verify it works

              Scenario: First scenario
                Given I am testing
                When I perform an action
                Then I expect a result
            """,
        }

        # Create feature
        result = mock_server._handle_create_feature(feature_data)

        # Verify result
        assert "data" in result
        assert result["data"]["name"] == "New Feature"
        assert result["data"]["description"] == "New feature description"
        assert result["data"]["projectId"] == project_id
        assert "content" in result["data"]

        # Verify feature was stored
        feature_id = result["data"]["id"]
        assert feature_id in mock_server.data["scenario"]["features"]

    def test_handle_request(self, mock_server):
        """Test handling different types of requests."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]

        # Test authentication request
        auth_result = mock_server.handle_request(
            api_type="manager",
            method="POST",
            endpoint="/oauth/token",
            data={"username": "test", "password": "test"},
        )
        assert "access_token" in auth_result

        # Test manager API request
        projects_result = mock_server.handle_request(
            api_type="manager", method="GET", endpoint="/projects", params={}
        )
        assert "items" in projects_result
        assert len(projects_result["items"]) > 0

        # Test parameters API request
        params_result = mock_server.handle_request(
            api_type="parameters",
            method="POST",
            endpoint="/parameters/query",
            data={"projectId": project_id, "offset": 0, "limit": 10},
        )
        assert "data" in params_result

        # Test pulse API request
        rules_result = mock_server.handle_request(
            api_type="pulse", method="GET", endpoint="/rules", params={"projectId": project_id}
        )
        assert "data" in rules_result

        # Test scenario API request
        features_result = mock_server.handle_request(
            api_type="scenario",
            method="GET",
            endpoint="/features",
            params={"projectId": project_id},
        )
        assert "data" in features_result

        # Test unknown API type
        unknown_result = mock_server.handle_request(
            api_type="unknown", method="GET", endpoint="/test", params={}
        )
        assert "error" in unknown_result

    def test_handle_submit_test_log(self, mock_server):
        """Test submitting a test log for a test run."""
        # Get a test run ID from sample data
        test_run_id = list(mock_server.data["manager"]["test_runs"].keys())[0]

        # Create test log data
        test_log_data = {
            "status": "Passed",  # Using valid status from QTestTestLog.VALID_STATUSES
            "executionDate": "2023-03-15T10:00:00Z",
            "note": "Test executed successfully",
            "actualResults": "Expected output was observed",
            "testStepLogs": [],
        }

        # Submit test log
        result = mock_server._handle_submit_test_log(test_run_id, test_log_data)

        # Verify result
        assert "id" in result
        assert result["status"] == "Passed"  # Using valid status from QTestTestLog.VALID_STATUSES
        assert result["note"] == "Test executed successfully"
        assert result["testRunId"] == test_run_id

        # Verify test log was stored
        assert result["id"] in mock_server.data["manager"]["test_logs"]

        # Verify test run status was updated
        assert mock_server.data["manager"]["test_runs"][test_run_id]["status"] == "Passed"

    def test_handle_submit_auto_test_logs(self, mock_server):
        """Test submitting bulk test logs via auto-test-logs endpoint."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]

        # Get a test case ID from sample data
        test_case_id = list(mock_server.data["manager"]["test_cases"].keys())[0]

        # Create auto test logs data with existing test case
        auto_test_logs_data = {
            "testLogs": [
                {
                    "name": "Automated Test 1",
                    "status": "Passed",
                    "note": "Test 1 executed successfully",
                    "testCaseId": test_case_id,
                    "executionDate": "2023-03-15T10:00:00Z",
                },
                {
                    "name": "Automated Test 2",
                    "status": "Failed",
                    "note": "Test 2 failed",
                    "testCaseId": test_case_id,
                    "executionDate": "2023-03-15T10:15:00Z",
                },
            ]
        }

        # Submit auto test logs
        result = mock_server._handle_submit_auto_test_logs(project_id, auto_test_logs_data)

        # Verify result
        assert "total" in result
        assert result["total"] == 2
        assert "successful" in result
        assert result["successful"] == 2
        assert "failed" in result
        assert result["failed"] == 0
        assert "testLogs" in result
        assert len(result["testLogs"]) == 2

        # Verify test logs were created in the storage
        for log_result in result["testLogs"]:
            assert "testLog" in log_result
            test_log_id = log_result["testLog"]["id"]
            assert test_log_id in mock_server.data["manager"]["test_logs"]

            # Verify test runs were created
            assert "testRun" in log_result
            test_run_id = log_result["testRun"]["id"]
            assert test_run_id in mock_server.data["manager"]["test_runs"]

            # Verify test cycle was created/linked
            assert "testCycle" in log_result
            test_cycle_id = log_result["testCycle"]["id"]
            assert test_cycle_id in mock_server.data["manager"]["test_cycles"]

    def test_handle_submit_auto_test_logs_with_new_test_case(self, mock_server):
        """Test submitting bulk test logs with new test case creation."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]

        # Create auto test logs data with new test case
        auto_test_logs_data = {
            "testLogs": [
                {
                    "name": "New Test Case Execution",
                    "status": "Passed",
                    "note": "New test case executed successfully",
                    "testCase": {
                        "name": "Auto-generated Test Case",
                        "description": "This test case was auto-generated",
                        "steps": [
                            {"description": "Step 1", "expectedResult": "Expected result 1"},
                            {"description": "Step 2", "expectedResult": "Expected result 2"},
                        ],
                    },
                    "executionDate": "2023-03-15T11:00:00Z",
                }
            ]
        }

        # Submit auto test logs
        result = mock_server._handle_submit_auto_test_logs(project_id, auto_test_logs_data)

        # Verify result
        assert "total" in result
        assert result["total"] == 1
        assert "successful" in result
        assert result["successful"] == 1
        assert "failed" in result
        assert result["failed"] == 0
        assert "testLogs" in result
        assert len(result["testLogs"]) == 1

        # Verify test case was created
        log_result = result["testLogs"][0]
        assert "testCase" in log_result
        test_case_id = log_result["testCase"]["id"]
        assert test_case_id in mock_server.data["manager"]["test_cases"]
        assert log_result["testCase"]["name"] == "Auto-generated Test Case"

        # Verify test log was created
        assert "testLog" in log_result
        test_log_id = log_result["testLog"]["id"]
        assert test_log_id in mock_server.data["manager"]["test_logs"]

        # Verify test run was created
        assert "testRun" in log_result
        test_run_id = log_result["testRun"]["id"]
        assert test_run_id in mock_server.data["manager"]["test_runs"]
        assert log_result["testRun"]["testCaseId"] == test_case_id

    def test_handle_submit_auto_test_logs_validation(self, mock_server):
        """Test validation in auto test logs submission."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]

        # Test missing testLogs field
        result = mock_server._handle_submit_auto_test_logs(project_id, {})
        assert "error" in result
        assert "Missing required field: testLogs" in result["error"]["message"]

        # Test missing required fields in test log entry
        auto_test_logs_data = {
            "testLogs": [
                {
                    # Missing name
                    "status": "Passed"
                },
                {
                    "name": "Test with missing status"
                    # Missing status
                },
                {"name": "Test with invalid status", "status": "INVALID_STATUS"},  # Invalid status
                {
                    "name": "Test with neither testCaseId nor testCase",
                    "status": "Passed"
                    # Missing both testCaseId and testCase
                },
            ]
        }

        result = mock_server._handle_submit_auto_test_logs(project_id, auto_test_logs_data)
        assert result["total"] == 4
        assert result["successful"] == 0
        assert result["failed"] == 4
        assert len(result["errors"]) == 4

    def test_validate_model(self, mock_server):
        """Test model validation functionality."""
        # Test valid data with QTestTestCase model
        from ztoq.qtest_models import QTestTestCase

        # Valid data
        valid_data = {
            "name": "Valid Test Case",
            "description": "A test case with valid data",
            "precondition": "System is ready for testing",
            "moduleId": 102,
            "pid": "TC-100",
            "projectId": 12345,
        }

        is_valid, validated_data, error = mock_server._validate_model(valid_data, QTestTestCase)
        assert is_valid is True
        assert validated_data is not None
        assert error is None

        # Invalid data - missing required field
        invalid_data = {
            "description": "Missing required name field"
            # Missing 'name' field which is required
        }

        is_valid, validated_data, error = mock_server._validate_model(invalid_data, QTestTestCase)
        assert is_valid is False
        assert validated_data is None
        assert error is not None
        assert "name" in error  # Error message should mention the missing field

        # Test with invalid type for a field
        invalid_type_data = {
            "name": "Test Case",
            "description": "A test case with invalid type",
            "precondition": "System is ready for testing",
            "moduleId": "not-a-number",  # Should be an integer
            "projectId": 12345,
        }

        is_valid, validated_data, error = mock_server._validate_model(
            invalid_type_data, QTestTestCase
        )
        assert is_valid is False
        assert validated_data is None
        assert error is not None
        assert "moduleId" in error or "not-a-number" in error

    def test_format_error_response(self, mock_server):
        """Test error response formatting."""
        # Test with default status code
        error_message = "This is a test error message"
        error_response = mock_server._format_error_response(error_message)

        assert "error" in error_response
        assert error_response["error"]["message"] == error_message
        assert error_response["error"]["code"] == 400  # Default status code
        assert "timestamp" in error_response["error"]

        # Test with custom status code
        custom_status = 404
        custom_error_response = mock_server._format_error_response(
            "Resource not found", custom_status
        )

        assert "error" in custom_error_response
        assert custom_error_response["error"]["message"] == "Resource not found"
        assert custom_error_response["error"]["code"] == custom_status
        assert "timestamp" in custom_error_response["error"]

    def test_request_tracking(self, mock_server):
        """Test request tracking functionality."""
        # Clear request history
        mock_server.request_history = []

        # Make test request
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        mock_server.handle_request(
            api_type="manager",
            method="GET",
            endpoint=f"/projects/{project_id}/test-cases",
            params={"page": 1, "pageSize": 10},
        )

        # Verify request was tracked
        assert len(mock_server.request_history) == 1
        tracked_request = mock_server.request_history[0]

        # Check request details were captured
        assert tracked_request["api_type"] == "manager"
        assert tracked_request["method"] == "GET"
        assert tracked_request["endpoint"] == f"/projects/{project_id}/test-cases"
        assert tracked_request["params"] == {"page": 1, "pageSize": 10}
        assert "timestamp" in tracked_request

    def test_mock_server_configuration(self, mock_server):
        """Test mock server configuration options."""
        # Test default configuration
        assert mock_server.error_rate == 0.0
        assert mock_server.response_delay == 0.0
        assert mock_server.validation_mode is True

        # Test changing configuration
        mock_server.error_rate = 0.5
        mock_server.response_delay = 0.1
        mock_server.validation_mode = False

        assert mock_server.error_rate == 0.5
        assert mock_server.response_delay == 0.1
        assert mock_server.validation_mode is False

        # Reset for other tests
        mock_server.error_rate = 0.0
        mock_server.response_delay = 0.0
        mock_server.validation_mode = True

    def test_handle_get_test_run(self, mock_server):
        """Test getting a test run."""
        # Get a test run ID from sample data
        test_run_id = list(mock_server.data["manager"]["test_runs"].keys())[0]

        # Get test run
        result = mock_server._handle_get_test_run(test_run_id)

        # Verify result
        assert result["id"] == test_run_id
        assert "name" in result
        assert "description" in result
        assert "testCaseId" in result
        assert "testCycleId" in result
        assert "status" in result

        # Test with non-existent ID
        result = mock_server._handle_get_test_run(99999)
        assert "error" in result

    def test_handle_get_test_runs(self, mock_server):
        """Test getting multiple test runs."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]

        # Get test runs with default parameters
        result = mock_server._handle_get_test_runs(project_id, {})

        # Verify result structure
        assert "page" in result
        assert "pageSize" in result
        assert "total" in result
        assert "items" in result
        assert len(result["items"]) > 0

        # Verify all items have the correct project ID
        for item in result["items"]:
            assert item["projectId"] == project_id

    def test_handle_create_test_run(self, mock_server):
        """Test creating a test run."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]

        # Get a test case ID and test cycle ID from sample data
        test_case_id = list(mock_server.data["manager"]["test_cases"].keys())[0]
        test_cycle_id = list(mock_server.data["manager"]["test_cycles"].keys())[0]

        # Create test run data
        test_run_data = {
            "name": "New Test Run",
            "description": "Description for new test run",
            "testCaseId": test_case_id,
            "testCycleId": test_cycle_id,
            "properties": [{"name": "Environment", "value": "QA"}],
            "status": "NOT_EXECUTED",
        }

        # Create test run
        result = mock_server._handle_create_test_run(project_id, test_run_data)

        # Verify result
        assert result["id"] > 0
        assert result["name"] == "New Test Run"
        assert result["description"] == "Description for new test run"
        assert result["testCaseId"] == test_case_id
        assert result["testCycleId"] == test_cycle_id
        assert result["projectId"] == project_id
        assert result["status"] == "NOT_EXECUTED"

        # Verify the test run was stored in the mock server
        assert result["id"] in mock_server.data["manager"]["test_runs"]

    def test_handle_get_test_logs(self, mock_server):
        """Test getting test logs for a test run."""
        # Create a test log first
        test_run_id = list(mock_server.data["manager"]["test_runs"].keys())[0]

        # Create test log data
        test_log_data = {
            "status": "Passed",
            "executionDate": "2023-03-15T10:00:00Z",
            "note": "Test log for get_test_logs test",
        }

        # Submit test log
        result = mock_server._handle_submit_test_log(test_run_id, test_log_data)

        # Now get the test logs
        logs_result = mock_server._handle_get_test_logs(test_run_id)

        # Verify result
        assert "items" in logs_result
        assert "total" in logs_result
        assert logs_result["total"] > 0

        # Verify the created test log is in the results
        found = False
        for log in logs_result["items"]:
            if log["id"] == result["id"]:
                found = True
                assert log["status"] == "Passed"
                assert log["note"] == "Test log for get_test_logs test"
                break

        assert found, "Created test log not found in get_test_logs result"

    def test_auto_test_log_with_test_case(self, mock_server):
        """Test auto test log submission with an existing test case."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]

        # Get a test case ID from sample data
        test_case_id = list(mock_server.data["manager"]["test_cases"].keys())[0]

        # Create test log data
        test_log_data = {
            "name": "Auto Test Log Test",
            "status": "Passed",
            "note": "Test executed successfully",
            "testCaseId": test_case_id,
            "executionDate": "2023-03-15T10:00:00Z",
        }

        # Submit auto test log
        result = mock_server._handle_auto_test_log_with_test_case(project_id, test_log_data)

        # Verify result structure
        assert "testLog" in result
        assert "testRun" in result
        assert "testCycle" in result

        # Verify test log
        assert result["testLog"]["status"] == "Passed"
        assert result["testLog"]["note"] == "Test executed successfully"

        # Verify test run
        assert result["testRun"]["testCaseId"] == test_case_id
        assert result["testRun"]["name"] == "Auto Test Log Test"

        # Verify test cycle
        assert result["testCycle"]["name"] == "Automation"
        assert result["testCycle"]["projectId"] == project_id

        # Verify with existing test cycle
        test_cycle_id = result["testCycle"]["id"]
        test_log_data_with_cycle = {
            "name": "Auto Test Log With Cycle",
            "status": "Passed",
            "note": "Test with existing cycle",
            "testCaseId": test_case_id,
            "testCycleId": test_cycle_id,
        }

        result_with_cycle = mock_server._handle_auto_test_log_with_test_case(
            project_id, test_log_data_with_cycle
        )
        assert result_with_cycle["testCycle"]["id"] == test_cycle_id

        # Test with non-existent test case
        invalid_test_log_data = {
            "name": "Invalid Test Case",
            "status": "Passed",
            "testCaseId": 99999,
        }

        invalid_result = mock_server._handle_auto_test_log_with_test_case(
            project_id, invalid_test_log_data
        )
        assert "error" in invalid_result
        assert "Test case not found: 99999" in invalid_result["error"]

    def test_auto_test_log_with_new_test_case(self, mock_server):
        """Test auto test log submission with a new test case."""
        # Temporarily turn off validation for this test
        original_validation_mode = mock_server.validation_mode
        mock_server.validation_mode = False

        try:
            # Get project ID from sample data
            project_id = mock_server.data["manager"]["projects"][0]["id"]

            # Get a module ID from sample data
            module_id = list(mock_server.data["manager"]["modules"].keys())[0]

            # Create test log data with new test case
            test_log_data = {
                "name": "New Test Case Auto Log",
                "status": "Passed",
                "note": "Test with new test case creation",
                "testCase": {
                    "name": "Generated Test Case",
                    "description": "Test case generated during auto test log",
                    "moduleId": module_id,  # Required field
                    "projectId": project_id,  # Required field
                    "steps": [
                        {"description": "Step 1", "expectedResult": "Result 1"},
                        {"description": "Step 2", "expectedResult": "Result 2"},
                    ],
                },
            }

            # Submit auto test log with new test case
            result = mock_server._handle_auto_test_log_with_new_test_case(project_id, test_log_data)

            # Verify result structure
            assert "testCase" in result
            assert "testLog" in result
            assert "testRun" in result
            assert "testCycle" in result

            # Verify test case
            assert result["testCase"]["name"] == "Generated Test Case"
            assert result["testCase"]["description"] == "Test case generated during auto test log"
            assert len(result["testCase"]["steps"]) == 2

            # Verify test log
            assert result["testLog"]["status"] == "Passed"
            assert result["testLog"]["note"] == "Test with new test case creation"

            # Verify test run
            assert result["testRun"]["testCaseId"] == result["testCase"]["id"]

            # Test with invalid test case data
            invalid_test_log_data = {
                "name": "Invalid Test Case Data",
                "status": "Passed",
                "testCase": {
                    # Missing required fields intentionally for testing error handling
                },
            }

            # Turn validation back on for this specific test
            mock_server.validation_mode = True

            invalid_result = mock_server._handle_auto_test_log_with_new_test_case(
                project_id, invalid_test_log_data
            )
            assert "error" in invalid_result
            assert "Failed to create test case" in invalid_result["error"]

        finally:
            # Restore original validation mode
            mock_server.validation_mode = original_validation_mode
