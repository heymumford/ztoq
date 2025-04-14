"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime
import json

from ztoq.qtest_client import QTestClient, QTestPaginatedIterator
from ztoq.qtest_models import (
    QTestConfig,
    QTestProject,
    QTestTestCase,
    QTestTestCycle,
    QTestModule,
    QTestAttachment,
    QTestParameter,
    QTestDataset,
)


@pytest.mark.unit
class TestQTestClient:
    @pytest.fixture
    def config(self):
        """Create a test qTest configuration."""
        return QTestConfig(
            base_url="https://example.qtest.com",
            username="test-user",
            password="test-password",
            project_id=12345,
        )

    @pytest.fixture
    def client(self, config):
        """Create a test qTest client with mocked authentication."""
        with patch("ztoq.qtest_client.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"access_token": "mock-token"}
            mock_post.return_value = mock_response
            mock_response.raise_for_status = MagicMock()

            return QTestClient(config)

    def test_client_initialization(self, client, config):
        """Test client initialization with config."""
        assert client.config == config
        assert client.headers["Authorization"] == "Bearer mock-token"
        assert client.headers["Content-Type"] == "application/json"
        assert client.rate_limit_remaining == 1000
        assert client.rate_limit_reset == 0

    @patch("ztoq.qtest_client.requests.request")
    def test_make_request(self, mock_request, client):
        """Test making an API request."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "value"}
        mock_response.status_code = 200
        mock_response.headers = {
            "X-RateLimit-Remaining": "950",
            "X-RateLimit-Reset": "1633046400",
        }
        mock_response.content = b"content"
        mock_request.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        # Make request
        result = client._make_request("GET", "/test-endpoint", params={"param": "value"})

        # Verify
        assert result == {"key": "value"}
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]["method"] == "GET"
        assert call_args[1]["url"] == "https://example.qtest.com/api/v3/test-endpoint"
        assert call_args[1]["headers"] == client.headers
        assert call_args[1]["params"] == {"param": "value"}
        assert client.rate_limit_remaining == 950
        assert client.rate_limit_reset == 1633046400

    @patch("ztoq.qtest_client.requests.request")
    def test_get_projects(self, mock_request, client):
        """Test getting projects."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "page": 1,
            "pageSize": 10,
            "total": 2,
            "items": [
                {"id": 1, "name": "Project 1", "description": "Test Project 1"},
                {"id": 2, "name": "Project 2", "description": "Test Project 2"},
            ],
        }
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        # Call the method
        result = client.get_projects()

        # Verify
        assert len(result) == 2
        assert isinstance(result[0], QTestProject)
        assert result[0].id == 1
        assert result[0].name == "Project 1"
        assert result[1].id == 2
        assert result[1].name == "Project 2"

        # Verify request details
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]["method"] == "GET"
        assert call_args[1]["url"] == "https://example.qtest.com/api/v3/projects"

    def test_paginated_iterator_manager_api(self, client):
        """Test the paginated iterator with Manager API format."""
        # Test data for Manager API format
        mock_data = [
            {
                "page": 1,
                "pageSize": 2,
                "total": 3,
                "items": [
                    {"id": 1, "name": "Test Case 1"},
                    {"id": 2, "name": "Test Case 2"},
                ],
            },
            {
                "page": 2,
                "pageSize": 2,
                "total": 3,
                "items": [
                    {"id": 3, "name": "Test Case 3"},
                ],
            },
        ]

        # Setup mock to return paginated data
        client._make_request = MagicMock()
        client._make_request.side_effect = lambda method, endpoint, params=None, **kwargs: (
            mock_data[0] if params.get("page") == 1 else mock_data[1]
        )

        # Get iterator
        iterator = QTestPaginatedIterator[QTestTestCase](
            client=client, endpoint="/test-cases", model_class=QTestTestCase, page_size=2
        )

        # Iterate and verify
        test_cases = list(iterator)
        assert len(test_cases) == 3
        assert isinstance(test_cases[0], QTestTestCase)
        assert test_cases[0].id == 1
        assert test_cases[1].id == 2
        assert test_cases[2].id == 3

        # Verify correct number of calls
        assert client._make_request.call_count == 2

    def test_paginated_iterator_parameters_api(self, client):
        """Test the paginated iterator with Parameters API format."""
        # Test data for Parameters API format
        client.api_type = "parameters"
        mock_data = [
            {
                "offset": 0,
                "limit": 2,
                "total": 3,
                "data": [
                    {"id": 1, "name": "Parameter 1"},
                    {"id": 2, "name": "Parameter 2"},
                ],
            },
            {
                "offset": 2,
                "limit": 2,
                "total": 3,
                "data": [
                    {"id": 3, "name": "Parameter 3"},
                ],
            },
        ]

        # Setup mock to return paginated data
        client._make_request = MagicMock()
        client._make_request.side_effect = lambda method, endpoint, params=None, **kwargs: (
            mock_data[0]
            if "params" in kwargs and kwargs["params"].get("offset") == 0
            else mock_data[1]
        )

        # Get iterator
        iterator = QTestPaginatedIterator[QTestParameter](
            client=client, endpoint="/parameters", model_class=QTestParameter, page_size=2
        )

        # Iterate and verify
        parameters = list(iterator)
        assert len(parameters) == 3
        assert isinstance(parameters[0], QTestParameter)
        assert parameters[0].id == 1
        assert parameters[1].id == 2
        assert parameters[2].id == 3

        # Verify correct number of calls
        assert client._make_request.call_count == 2

    @patch("ztoq.qtest_client.requests.request")
    def test_get_test_cases(self, mock_request, client):
        """Test getting test cases."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "page": 1,
            "pageSize": 10,
            "total": 2,
            "items": [
                {
                    "id": 101,
                    "name": "Login Test",
                    "description": "Test login functionality",
                    "precondition": "User is registered",
                    "steps": [
                        {
                            "id": 201,
                            "description": "Navigate to login page",
                            "expectedResult": "Login page is displayed",
                            "order": 1,
                        }
                    ],
                },
                {
                    "id": 102,
                    "name": "Registration Test",
                    "description": "Test user registration",
                    "precondition": "User is not registered",
                    "steps": [],
                },
            ],
        }
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        # Setup iterator mock to return actual values from the above mock response
        with patch("ztoq.qtest_client.QTestPaginatedIterator.__next__") as mock_next:
            mock_next.side_effect = [
                QTestTestCase(**mock_response.json.return_value["items"][0]),
                QTestTestCase(**mock_response.json.return_value["items"][1]),
                StopIteration(),
            ]

            # Call the method
            iterator = client.get_test_cases()

            # Consume the iterator
            test_cases = list(iterator)

            # Verify
            assert len(test_cases) == 2
            assert test_cases[0].id == 101
            assert test_cases[0].name == "Login Test"
            assert test_cases[1].id == 102
            assert test_cases[1].name == "Registration Test"

    @patch("ztoq.qtest_client.requests.request")
    def test_get_test_case(self, mock_request, client):
        """Test getting a single test case."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 101,
            "name": "Login Test",
            "description": "Test login functionality",
            "precondition": "User is registered",
            "steps": [
                {
                    "id": 201,
                    "description": "Navigate to login page",
                    "expectedResult": "Login page is displayed",
                    "order": 1,
                }
            ],
        }
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        # Call the method
        result = client.get_test_case(101)

        # Verify
        assert isinstance(result, QTestTestCase)
        assert result.id == 101
        assert result.name == "Login Test"
        assert len(result.test_steps) == 1
        assert result.test_steps[0].id == 201

        # Verify request
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]["method"] == "GET"
        assert "/projects/12345/test-cases/101" in call_args[1]["url"]

    @patch("ztoq.qtest_client.requests.request")
    def test_create_test_case(self, mock_request, client):
        """Test creating a test case."""
        # Create test case to submit
        test_case = QTestTestCase(
            name="New Test Case",
            description="Description",
            precondition="Precondition",
            test_steps=[{"description": "Step 1", "expectedResult": "Result 1", "order": 1}],
        )

        # Setup mock
        mock_response = MagicMock()
        # Return the test case with added ID
        response_data = test_case.model_dump(exclude_unset=True)
        response_data["id"] = 201
        mock_response.json.return_value = response_data
        mock_response.status_code = 201
        mock_request.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        # Call the method
        result = client.create_test_case(test_case)

        # Verify
        assert isinstance(result, QTestTestCase)
        assert result.id == 201
        assert result.name == "New Test Case"

        # Verify request
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]["method"] == "POST"
        assert "/projects/12345/test-cases" in call_args[1]["url"]
        assert call_args[1]["json"] == test_case.model_dump(exclude_unset=True)

    @patch("ztoq.qtest_client.requests.request")
    def test_upload_attachment(self, mock_request, client, tmp_path):
        """Test uploading an attachment."""
        # Create a temporary file
        test_file = tmp_path / "test_attachment.txt"
        test_file.write_text("Test content")

        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 301,
            "name": "test_attachment.txt",
            "contentType": "text/plain",
            "size": 12,
            "createdDate": "2023-01-01T12:00:00Z",
            "webUrl": "https://example.com/attachments/301",
        }
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        # Call the method
        result = client.upload_attachment(
            object_type="test-cases", object_id=101, file_path=test_file
        )

        # Verify
        assert isinstance(result, QTestAttachment)
        assert result.id == 301
        assert result.name == "test_attachment.txt"
        assert result.content_type == "text/plain"

        # Verify request
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]["method"] == "POST"
        assert "/projects/12345/test-cases/101/blob-handles" in call_args[1]["url"]
        assert "files" in call_args[1]
        assert "file" in call_args[1]["files"]

    @patch("ztoq.qtest_client.requests.request")
    def test_get_modules(self, mock_request, client):
        """Test getting modules."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "page": 1,
            "pageSize": 10,
            "total": 2,
            "items": [
                {
                    "id": 401,
                    "name": "Module 1",
                    "description": "First module",
                    "parentId": None,
                    "pid": "MD-1",
                },
                {
                    "id": 402,
                    "name": "Module 2",
                    "description": "Second module",
                    "parentId": 401,
                    "pid": "MD-2",
                },
            ],
        }
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        # Setup iterator mock to return actual values
        with patch("ztoq.qtest_client.QTestPaginatedIterator.__next__") as mock_next:
            mock_next.side_effect = [
                QTestModule(**mock_response.json.return_value["items"][0]),
                QTestModule(**mock_response.json.return_value["items"][1]),
                StopIteration(),
            ]

            # Call the method
            iterator = client.get_modules()

            # Consume the iterator
            modules = list(iterator)

            # Verify
            assert len(modules) == 2
            assert modules[0].id == 401
            assert modules[0].name == "Module 1"
            assert modules[1].id == 402
            assert modules[1].name == "Module 2"
            assert modules[1].parent_id == 401

    @patch("ztoq.qtest_client.requests.request")
    def test_get_parameters(self, mock_request, client):
        """Test getting parameters with the Parameters API."""
        # Set API type to parameters for this test
        client.api_type = "parameters"

        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "offset": 0,
            "limit": 10,
            "total": 2,
            "data": [
                {
                    "id": 701,
                    "name": "Browser",
                    "description": "Browser type",
                    "projectId": 12345,
                    "status": "ACTIVE",
                },
                {
                    "id": 702,
                    "name": "Environment",
                    "description": "Test environment",
                    "projectId": 12345,
                    "status": "ACTIVE",
                },
            ],
        }
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        # Setup iterator mock to return actual values
        with patch("ztoq.qtest_client.QTestPaginatedIterator.__next__") as mock_next:
            mock_next.side_effect = [
                QTestParameter(**mock_response.json.return_value["data"][0]),
                QTestParameter(**mock_response.json.return_value["data"][1]),
                StopIteration(),
            ]

            # Call the method
            iterator = client.get_parameters()

            # Consume the iterator
            parameters = list(iterator)

            # Verify
            assert len(parameters) == 2
            assert parameters[0].id == 701
            assert parameters[0].name == "Browser"
            assert parameters[1].id == 702
            assert parameters[1].name == "Environment"

    @patch("ztoq.qtest_client.requests.request")
    def test_create_parameter(self, mock_request, client):
        """Test creating a parameter in the Parameters API."""
        # Set API type to parameters for this test
        client.api_type = "parameters"

        # Create parameter to submit
        parameter = QTestParameter(
            name="New Parameter",
            description="Description",
            values=[{"value": "Value 1"}, {"value": "Value 2"}],
        )

        # Setup mock
        mock_response = MagicMock()
        # Return the parameter with added ID
        response_data = {
            "status": "SUCCESS",
            "data": {
                "id": 801,
                "name": "New Parameter",
                "description": "Description",
                "projectId": 12345,
                "status": "ACTIVE",
            },
        }
        mock_response.json.return_value = response_data
        mock_response.status_code = 201
        mock_request.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        # Call the method
        result = client.create_parameter(parameter)

        # Verify
        assert isinstance(result, QTestParameter)
        assert result.id == 801
        assert result.name == "New Parameter"

        # Verify request
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]["method"] == "POST"
        assert "/parameters/create" in call_args[1]["url"]
        # Check that projectId was added
        assert call_args[1]["json"]["projectId"] == 12345

    @patch("ztoq.qtest_client.requests.request")
    def test_rate_limiting(self, mock_request, client):
        """Test rate limiting behavior."""
        import time

        # Mock time.time and time.sleep
        with (
            patch("ztoq.qtest_client.time.time") as mock_time,
            patch("ztoq.qtest_client.time.sleep") as mock_sleep,
        ):

            # Setup mock_time to simulate passage of time
            mock_time.side_effect = [100, 101]  # First call returns 100, second returns 101

            # Setup client with rate limit reached
            client.rate_limit_remaining = 0
            client.rate_limit_reset = 102  # 2 seconds in the future

            # Setup response mock
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": "success"}
            mock_response.status_code = 200
            mock_response.headers = {"X-RateLimit-Remaining": "999"}
            mock_request.return_value = mock_response
            mock_response.raise_for_status = MagicMock()

            # Make request
            result = client._make_request("GET", "/test-endpoint")

            # Verify sleep was called with correct duration
            mock_sleep.assert_called_once_with(2)  # Should sleep for 2 seconds

            # Verify response
            assert result == {"data": "success"}
            assert client.rate_limit_remaining == 999

    @patch("ztoq.qtest_client.requests.request")
    def test_token_refresh(self, mock_request, client):
        """Test token refresh on 401 response."""
        # Setup 401 response followed by successful response
        unauthorized_response = MagicMock()
        unauthorized_response.status_code = 401
        unauthorized_response.raise_for_status.side_effect = Exception("Unauthorized")

        success_response = MagicMock()
        success_response.json.return_value = {"data": "success"}
        success_response.status_code = 200
        success_response.headers = {}
        success_response.raise_for_status = MagicMock()

        mock_request.side_effect = [unauthorized_response, success_response]

        # Mock authenticate method
        client._authenticate = MagicMock()

        # Make request that should trigger re-authentication
        with pytest.raises(Exception):
            client._make_request("GET", "/test-endpoint")

        # Verify authenticate was called
        client._authenticate.assert_called_once()

    @patch("ztoq.qtest_client.requests.request")
    def test_get_rules(self, mock_request, client):
        """Test getting Pulse rules."""
        # Set API type to pulse for this test
        client.api_type = "pulse"

        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "rule1",
                    "name": "JIRA Integration Rule",
                    "description": "Update JIRA when test fails",
                    "projectId": 12345,
                    "enabled": True,
                },
                {
                    "id": "rule2",
                    "name": "Email Notification Rule",
                    "description": "Send email on test completion",
                    "projectId": 12345,
                    "enabled": True,
                },
            ]
        }
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        # Call the method
        result = client.get_rules()

        # Verify
        assert len(result) == 2
        assert result[0]["id"] == "rule1"
        assert result[0]["name"] == "JIRA Integration Rule"
        assert result[1]["id"] == "rule2"

        # Verify request
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]["method"] == "GET"
        assert "/rules" in call_args[1]["url"]
        assert call_args[1]["params"]["projectId"] == 12345

    @patch("ztoq.qtest_client.requests.request")
    def test_get_features(self, mock_request, client):
        """Test getting Scenario features."""
        # Set API type to scenario for this test
        client.api_type = "scenario"

        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "feature1",
                    "name": "User Authentication",
                    "description": "User login and registration",
                    "projectId": 12345,
                    "content": "Feature: User Authentication...",
                },
                {
                    "id": "feature2",
                    "name": "Shopping Cart",
                    "description": "Shopping cart functionality",
                    "projectId": 12345,
                    "content": "Feature: Shopping Cart...",
                },
            ]
        }
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        mock_response.raise_for_status = MagicMock()

        # Call the method
        result = client.get_features()

        # Verify
        assert len(result) == 2
        assert result[0]["id"] == "feature1"
        assert result[0]["name"] == "User Authentication"
        assert result[1]["id"] == "feature2"

        # Verify request
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]["method"] == "GET"
        assert "/features" in call_args[1]["url"]
        assert call_args[1]["params"]["projectId"] == 12345

    @patch("ztoq.qtest_client.requests.request")
    def test_mask_sensitive_data(self, mock_request, client):
        """Test masking of sensitive data in logs."""
        # Create data with sensitive information
        data = {
            "username": "test-user",
            "password": "secret-password",
            "apiToken": "secret-token",
            "config": {"secretKey": "very-secret", "credentials": {"password": "nested-password"}},
            "normal": "not-sensitive",
        }

        # Mask the data
        masked = client._mask_sensitive_data(data)

        # Verify sensitive fields are masked
        assert masked["username"] == "test-user"  # Not sensitive
        assert masked["password"] == "********"  # Sensitive
        assert masked["apiToken"] == "********"  # Sensitive
        assert masked["config"]["secretKey"] == "********"  # Sensitive
        assert masked["config"]["credentials"]["password"] == "********"  # Nested sensitive
        assert masked["normal"] == "not-sensitive"  # Not sensitive

        # Original data should be unchanged
        assert data["password"] == "secret-password"
