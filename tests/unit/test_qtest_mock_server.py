import pytest
import json
from unittest.mock import MagicMock, patch
import uuid
from datetime import datetime

from ztoq.qtest_mock_server import QTestMockServer


@pytest.mark.unit
class TestQTestMockServer:
    @pytest.fixture
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

    def test_handle_get_rules(self, mock_server):
        """Test getting Pulse rules."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]

        # Get rules
        result = mock_server._handle_get_rules(project_id)

        # Verify result
        assert "data" in result
        assert isinstance(result["data"], list)

        # Should contain rules with matching project ID
        for rule in result["data"]:
            assert rule["projectId"] == project_id

    def test_handle_create_rule(self, mock_server):
        """Test creating a Pulse rule."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]

        # Rule data
        rule_data = {
            "name": "New Rule",
            "description": "New rule description",
            "projectId": project_id,
            "enabled": True,
            "conditions": [{"field": "status", "operator": "equals", "value": "PASS"}],
            "actions": [
                {
                    "type": "email",
                    "configuration": {"to": "test@example.com", "subject": "Test passed"},
                }
            ],
        }

        # Create rule
        result = mock_server._handle_create_rule(rule_data)

        # Verify result
        assert "data" in result
        assert result["data"]["name"] == "New Rule"
        assert result["data"]["description"] == "New rule description"
        assert result["data"]["projectId"] == project_id

        # Verify rule was stored
        rule_id = result["data"]["id"]
        assert rule_id in mock_server.data["pulse"]["rules"]

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
