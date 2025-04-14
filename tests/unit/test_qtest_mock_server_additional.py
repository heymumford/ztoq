"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import pytest
import json
from ztoq.qtest_mock_server import QTestMockServer
from ztoq.qtest_models import (
    QTestCustomField,
    QTestRelease,
    QTestTestCycle,
    QTestTestCase
)

@pytest.mark.unit
class TestQTestMockServerCustomFields:
    @pytest.fixture
    def mock_server(self):
        """Create a test qTest mock server instance."""
        return QTestMockServer()

    def test_handle_get_custom_fields(self, mock_server):
        """Test retrieving custom fields for an object type."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Test getting custom fields for test cases
        result = mock_server._handle_get_custom_fields(project_id, "test-cases")
        
        # Verify result structure
        assert isinstance(result, list)
        
        # Check for sample custom fields
        for field in result:
            assert "id" in field
            assert "fieldName" in field
            assert "fieldType" in field
    
    def test_handle_create_custom_field(self, mock_server):
        """Test creating a custom field."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create custom field data
        field_data = {
            "fieldName": "Test Custom Field",
            "fieldType": "TEXT",
            "entityType": "TEST_CASE",
            "isRequired": False,
            "allowedValues": ["Value 1", "Value 2"]
        }
        
        # Create custom field
        result = mock_server._handle_create_custom_field(project_id, field_data)
        
        # Verify result
        assert result["id"] > 0
        assert result["fieldName"] == "Test Custom Field"
        assert result["fieldType"] == "TEXT"
        assert result["entityType"] == "TEST_CASE"
        assert not result["isRequired"]
        assert len(result["allowedValues"]) == 2
        
        # Verify custom field was stored
        assert result["id"] in mock_server.data["manager"]["custom_fields"]
    
    def test_handle_get_custom_field(self, mock_server):
        """Test retrieving a specific custom field."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create a custom field first
        field_data = {
            "fieldName": "Test Custom Field For Get",
            "fieldType": "TEXT",
            "entityType": "TEST_CASE",
        }
        created_field = mock_server._handle_create_custom_field(project_id, field_data)
        
        # Get the custom field
        result = mock_server._handle_get_custom_field(created_field["id"])
        
        # Verify result
        assert result["id"] == created_field["id"]
        assert result["fieldName"] == "Test Custom Field For Get"
        
        # Test with non-existent ID
        result = mock_server._handle_get_custom_field(99999)
        assert "error" in result
    
    def test_handle_update_custom_field(self, mock_server):
        """Test updating a custom field."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create a custom field first
        field_data = {
            "fieldName": "Test Custom Field For Update",
            "fieldType": "TEXT",
            "entityType": "TEST_CASE",
        }
        created_field = mock_server._handle_create_custom_field(project_id, field_data)
        
        # Update data
        update_data = {
            "fieldName": "Updated Custom Field",
            "isRequired": True,
            "allowedValues": ["New Value 1", "New Value 2", "New Value 3"]
        }
        
        # Update the custom field
        result = mock_server._handle_update_custom_field(created_field["id"], update_data)
        
        # Verify result
        assert result["id"] == created_field["id"]
        assert result["fieldName"] == "Updated Custom Field"
        assert result["isRequired"] is True
        assert len(result["allowedValues"]) == 3
    
    def test_handle_delete_custom_field(self, mock_server):
        """Test deleting a custom field."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create a custom field first
        field_data = {
            "fieldName": "Test Custom Field For Delete",
            "fieldType": "TEXT",
            "entityType": "TEST_CASE",
        }
        created_field = mock_server._handle_create_custom_field(project_id, field_data)
        
        # Delete the custom field
        result = mock_server._handle_delete_custom_field(created_field["id"])
        
        # Verify result
        assert "success" in result
        assert created_field["id"] not in mock_server.data["manager"]["custom_fields"]

@pytest.mark.unit
class TestQTestMockServerReleases:
    @pytest.fixture
    def mock_server(self):
        """Create a test qTest mock server instance."""
        return QTestMockServer()
    
    def test_handle_get_releases(self, mock_server):
        """Test retrieving releases for a project."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Get releases
        result = mock_server._handle_get_releases(project_id)
        
        # Verify result structure
        assert "items" in result
        assert "total" in result
        assert "page" in result
        assert "pageSize" in result
        
        # Check items
        for release in result["items"]:
            assert release["projectId"] == project_id
    
    def test_handle_create_release(self, mock_server):
        """Test creating a release."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create release data
        release_data = {
            "name": "Test Release",
            "description": "Test release description",
            "startDate": "2025-01-01T00:00:00Z",
            "endDate": "2025-12-31T23:59:59Z",
            "status": "ACTIVE"
        }
        
        # Create release
        result = mock_server._handle_create_release(project_id, release_data)
        
        # Verify result
        assert result["id"] > 0
        assert result["name"] == "Test Release"
        assert result["description"] == "Test release description"
        assert result["projectId"] == project_id
        assert result["status"] == "ACTIVE"
        
        # Verify release was stored
        assert result["id"] in mock_server.data["manager"]["releases"]
    
    def test_handle_get_release(self, mock_server):
        """Test retrieving a specific release."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create a release first
        release_data = {
            "name": "Test Release For Get",
            "status": "ACTIVE"
        }
        created_release = mock_server._handle_create_release(project_id, release_data)
        
        # Get the release
        result = mock_server._handle_get_release(created_release["id"])
        
        # Verify result
        assert result["id"] == created_release["id"]
        assert result["name"] == "Test Release For Get"
        
        # Test with non-existent ID
        result = mock_server._handle_get_release(99999)
        assert "error" in result
    
    def test_handle_update_release(self, mock_server):
        """Test updating a release."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create a release first
        release_data = {
            "name": "Test Release For Update",
            "status": "ACTIVE"
        }
        created_release = mock_server._handle_create_release(project_id, release_data)
        
        # Update data
        update_data = {
            "name": "Updated Release Name",
            "description": "Updated description",
            "status": "COMPLETED"
        }
        
        # Update the release
        result = mock_server._handle_update_release(created_release["id"], update_data)
        
        # Verify result
        assert result["id"] == created_release["id"]
        assert result["name"] == "Updated Release Name"
        assert result["description"] == "Updated description"
        assert result["status"] == "COMPLETED"
    
    def test_handle_delete_release(self, mock_server):
        """Test deleting a release."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create a release first
        release_data = {
            "name": "Test Release For Delete",
            "status": "ACTIVE"
        }
        created_release = mock_server._handle_create_release(project_id, release_data)
        
        # Delete the release
        result = mock_server._handle_delete_release(created_release["id"])
        
        # Verify result
        assert "success" in result
        assert created_release["id"] not in mock_server.data["manager"]["releases"]

@pytest.mark.unit
class TestQTestMockServerTestCycles:
    @pytest.fixture
    def mock_server(self):
        """Create a test qTest mock server instance."""
        return QTestMockServer()
    
    def test_handle_get_test_cycles(self, mock_server):
        """Test retrieving test cycles for a project."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Get test cycles
        result = mock_server._handle_get_test_cycles(project_id)
        
        # Verify result structure
        assert "items" in result
        assert "total" in result
        assert "page" in result
        assert "pageSize" in result
        
        # Check items
        for cycle in result["items"]:
            assert cycle["projectId"] == project_id
    
    def test_handle_create_test_cycle(self, mock_server):
        """Test creating a test cycle."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create release first to link the cycle to
        release_data = {
            "name": "Release for Test Cycle",
            "status": "ACTIVE"
        }
        created_release = mock_server._handle_create_release(project_id, release_data)
        
        # Create test cycle data
        cycle_data = {
            "name": "Test Cycle",
            "description": "Test cycle description",
            "releaseId": created_release["id"],
            "status": "IN_PROGRESS"
        }
        
        # Create test cycle
        result = mock_server._handle_create_test_cycle(project_id, cycle_data)
        
        # Verify result
        assert result["id"] > 0
        assert result["name"] == "Test Cycle"
        assert result["description"] == "Test cycle description"
        assert result["releaseId"] == created_release["id"]
        assert result["projectId"] == project_id
        assert result["status"] == "IN_PROGRESS"
        
        # Verify test cycle was stored
        assert result["id"] in mock_server.data["manager"]["test_cycles"]
    
    def test_handle_get_test_cycle(self, mock_server):
        """Test retrieving a specific test cycle."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create a test cycle first
        cycle_data = {
            "name": "Test Cycle For Get",
            "status": "IN_PROGRESS"
        }
        created_cycle = mock_server._handle_create_test_cycle(project_id, cycle_data)
        
        # Get the test cycle
        result = mock_server._handle_get_test_cycle(created_cycle["id"])
        
        # Verify result
        assert result["id"] == created_cycle["id"]
        assert result["name"] == "Test Cycle For Get"
        
        # Test with non-existent ID
        result = mock_server._handle_get_test_cycle(99999)
        assert "error" in result
    
    def test_handle_update_test_cycle(self, mock_server):
        """Test updating a test cycle."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create a test cycle first
        cycle_data = {
            "name": "Test Cycle For Update",
            "status": "IN_PROGRESS"
        }
        created_cycle = mock_server._handle_create_test_cycle(project_id, cycle_data)
        
        # Update data
        update_data = {
            "name": "Updated Test Cycle Name",
            "description": "Updated description",
            "status": "COMPLETED"
        }
        
        # Update the test cycle
        result = mock_server._handle_update_test_cycle(created_cycle["id"], update_data)
        
        # Verify result
        assert result["id"] == created_cycle["id"]
        assert result["name"] == "Updated Test Cycle Name"
        assert result["description"] == "Updated description"
        assert result["status"] == "COMPLETED"
    
    def test_handle_delete_test_cycle(self, mock_server):
        """Test deleting a test cycle."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create a test cycle first
        cycle_data = {
            "name": "Test Cycle For Delete",
            "status": "IN_PROGRESS"
        }
        created_cycle = mock_server._handle_create_test_cycle(project_id, cycle_data)
        
        # Delete the test cycle
        result = mock_server._handle_delete_test_cycle(created_cycle["id"])
        
        # Verify result
        assert "success" in result
        assert created_cycle["id"] not in mock_server.data["manager"]["test_cycles"]

@pytest.mark.unit
class TestQTestMockServerValidationAndErrorHandling:
    @pytest.fixture
    def mock_server(self):
        """Create a test qTest mock server instance."""
        return QTestMockServer()
    
    def test_validation_for_project(self, mock_server):
        """Test validation for project creation."""
        # Valid project data
        valid_data = {
            "name": "Valid Project",
            "description": "Valid project description",
            "status": "active"
        }
        
        # Create project
        result = mock_server._handle_create_project(valid_data)
        assert result["id"] > 0
        assert result["name"] == "Valid Project"
        
        # Invalid project data - missing required field
        invalid_data = {"description": "Missing required name field"}
        result = mock_server._handle_create_project(invalid_data)
        assert "error" in result
        
        # Invalid project data - invalid status value
        invalid_status_data = {
            "name": "Invalid Status Project",
            "status": "INVALID"
        }
        result = mock_server._handle_create_project(invalid_status_data)
        assert "error" in result
    
    def test_validation_for_test_case(self, mock_server):
        """Test validation for test case creation."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Valid test case data
        valid_data = {
            "name": "Valid Test Case",
            "description": "Valid test case description",
            "moduleId": list(mock_server.data["manager"]["modules"].keys())[0]
        }
        
        # Create test case
        result = mock_server._handle_create_test_case(project_id, valid_data)
        assert result["id"] > 0
        assert result["name"] == "Valid Test Case"
        
        # Invalid test case data - missing required field
        invalid_data = {"description": "Missing required name field"}
        result = mock_server._handle_create_test_case(project_id, invalid_data)
        assert "error" in result
        
        # Invalid test case data - non-existent module ID
        invalid_module_data = {
            "name": "Invalid Module Test Case",
            "moduleId": 999999
        }
        # Temporarily turn off validation to allow this test to run
        original_validation_mode = mock_server.validation_mode
        mock_server.validation_mode = False
        try:
            result = mock_server._handle_create_test_case(project_id, invalid_module_data)
            assert "error" in result
            assert "Module not found" in result["error"]["message"]
        finally:
            mock_server.validation_mode = original_validation_mode
    
    def test_error_responses(self, mock_server):
        """Test various error responses for non-existent resources."""
        # Test non-existent project ID
        non_existent_project_id = 99999
        result = mock_server._handle_get_project(non_existent_project_id)
        assert "error" in result
        assert result["error"]["code"] == 404
        
        # Test non-existent test case ID
        non_existent_test_case_id = 99999
        result = mock_server._handle_get_test_case(non_existent_test_case_id)
        assert "error" in result
        assert result["error"]["code"] == 404
        
        # Test non-existent test cycle ID
        non_existent_test_cycle_id = 99999
        result = mock_server._handle_get_test_cycle(non_existent_test_cycle_id)
        assert "error" in result
        assert result["error"]["code"] == 404
        
        # Test non-existent test run ID
        non_existent_test_run_id = 99999
        result = mock_server._handle_get_test_run(non_existent_test_run_id)
        assert "error" in result
        assert result["error"]["code"] == 404
    
    def test_error_handling_for_invalid_api_type(self, mock_server):
        """Test error handling for invalid API type."""
        result = mock_server.handle_request(
            api_type="invalid_api",
            method="GET",
            endpoint="/test",
            params={}
        )
        assert "error" in result
        assert "Unknown API type" in result["error"]["message"]
    
    def test_error_handling_for_invalid_method(self, mock_server):
        """Test error handling for invalid HTTP method."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        result = mock_server.handle_request(
            api_type="manager",
            method="INVALID",
            endpoint=f"/projects/{project_id}",
            params={}
        )
        assert "error" in result
        assert "Unknown method" in result["error"]["message"]
    
    def test_error_handling_for_unknown_endpoint(self, mock_server):
        """Test error handling for unknown endpoint."""
        result = mock_server.handle_request(
            api_type="manager",
            method="GET",
            endpoint="/unknown/endpoint",
            params={}
        )
        assert "error" in result
        assert "Unknown endpoint" in result["error"]["message"]

@pytest.mark.unit
class TestQTestMockServerDatasetOperations:
    @pytest.fixture
    def mock_server(self):
        """Create a test qTest mock server instance."""
        return QTestMockServer()
    
    def test_handle_get_datasets(self, mock_server):
        """Test retrieving datasets for a project."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Get datasets
        result = mock_server._handle_get_datasets(project_id)
        
        # Verify result structure
        assert "data" in result
        assert isinstance(result["data"], list)
        
        # Check that datasets contain correct project ID
        for dataset in result["data"]:
            assert dataset["projectId"] == project_id
    
    def test_handle_create_dataset(self, mock_server):
        """Test creating a dataset."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create dataset data
        dataset_data = {
            "name": "Test Dataset",
            "description": "Test dataset description",
            "projectId": project_id,
            "columns": [
                {"name": "Column 1", "dataType": "STRING"},
                {"name": "Column 2", "dataType": "BOOLEAN"},
                {"name": "Column 3", "dataType": "NUMERIC"}
            ]
        }
        
        # Create dataset
        result = mock_server._handle_create_dataset(dataset_data)
        
        # Verify result
        assert "status" in result
        assert result["status"] == "SUCCESS"
        assert "data" in result
        assert result["data"]["id"] > 0
        assert result["data"]["name"] == "Test Dataset"
        assert result["data"]["description"] == "Test dataset description"
        assert len(result["data"]["columns"]) == 3
        
        # Verify dataset was stored
        dataset_id = result["data"]["id"]
        assert dataset_id in mock_server.data["parameters"]["datasets"]
    
    def test_handle_get_dataset(self, mock_server):
        """Test retrieving a specific dataset."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create a dataset first
        dataset_data = {
            "name": "Test Dataset For Get",
            "description": "Test dataset description",
            "projectId": project_id,
            "columns": [{"name": "Column 1", "dataType": "STRING"}]
        }
        created_dataset = mock_server._handle_create_dataset(dataset_data)
        dataset_id = created_dataset["data"]["id"]
        
        # Get the dataset
        result = mock_server._handle_get_dataset(dataset_id)
        
        # Verify result
        assert "status" in result
        assert result["status"] == "SUCCESS"
        assert "data" in result
        assert result["data"]["id"] == dataset_id
        assert result["data"]["name"] == "Test Dataset For Get"
        
        # Test with non-existent ID
        result = mock_server._handle_get_dataset(99999)
        assert "error" in result or (result.get("status") == "ERROR" and "message" in result)
    
    def test_handle_update_dataset(self, mock_server):
        """Test updating a dataset."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create a dataset first
        dataset_data = {
            "name": "Test Dataset For Update",
            "description": "Test dataset description",
            "projectId": project_id,
            "columns": [{"name": "Column 1", "dataType": "STRING"}]
        }
        created_dataset = mock_server._handle_create_dataset(dataset_data)
        dataset_id = created_dataset["data"]["id"]
        
        # Update data
        update_data = {
            "name": "Updated Dataset Name",
            "description": "Updated description",
            "columns": [
                {"name": "Column 1", "dataType": "STRING"},
                {"name": "New Column", "dataType": "BOOLEAN"}
            ]
        }
        
        # Update the dataset
        result = mock_server._handle_update_dataset(dataset_id, update_data)
        
        # Verify result
        assert "status" in result
        assert result["status"] == "SUCCESS"
        assert "data" in result
        assert result["data"]["id"] == dataset_id
        assert result["data"]["name"] == "Updated Dataset Name"
        assert result["data"]["description"] == "Updated description"
        assert len(result["data"]["columns"]) == 2
    
    def test_handle_delete_dataset(self, mock_server):
        """Test deleting a dataset."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create a dataset first
        dataset_data = {
            "name": "Test Dataset For Delete",
            "description": "Test dataset description",
            "projectId": project_id,
            "columns": [{"name": "Column 1", "dataType": "STRING"}]
        }
        created_dataset = mock_server._handle_create_dataset(dataset_data)
        dataset_id = created_dataset["data"]["id"]
        
        # Delete the dataset
        result = mock_server._handle_delete_dataset(dataset_id)
        
        # Verify result
        assert "status" in result
        assert result["status"] == "SUCCESS"
        assert dataset_id not in mock_server.data["parameters"]["datasets"]

@pytest.mark.unit
class TestQTestMockServerDatasetRows:
    @pytest.fixture
    def mock_server(self):
        """Create a test qTest mock server instance."""
        return QTestMockServer()
    
    def test_handle_get_dataset_rows(self, mock_server):
        """Test retrieving rows for a dataset."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create a dataset first
        dataset_data = {
            "name": "Test Dataset For Rows",
            "description": "Test dataset description",
            "projectId": project_id,
            "columns": [
                {"name": "Column 1", "dataType": "STRING"},
                {"name": "Column 2", "dataType": "BOOLEAN"}
            ]
        }
        created_dataset = mock_server._handle_create_dataset(dataset_data)
        dataset_id = created_dataset["data"]["id"]
        
        # Create rows for the dataset
        rows_data = {
            "rows": [
                {"cells": [{"columnName": "Column 1", "value": "Value 1"}, {"columnName": "Column 2", "value": "true"}]},
                {"cells": [{"columnName": "Column 1", "value": "Value 2"}, {"columnName": "Column 2", "value": "false"}]}
            ]
        }
        mock_server._handle_create_dataset_rows(dataset_id, rows_data)
        
        # Get dataset rows
        result = mock_server._handle_get_dataset_rows(dataset_id)
        
        # Verify result
        assert "status" in result
        assert result["status"] == "SUCCESS"
        assert "data" in result
        assert len(result["data"]) == 2
        assert result["data"][0]["cells"][0]["value"] in ["Value 1", "Value 2"]
    
    def test_handle_create_dataset_rows(self, mock_server):
        """Test creating rows for a dataset."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create a dataset first
        dataset_data = {
            "name": "Test Dataset For Creating Rows",
            "description": "Test dataset description",
            "projectId": project_id,
            "columns": [
                {"name": "Column 1", "dataType": "STRING"},
                {"name": "Column 2", "dataType": "BOOLEAN"}
            ]
        }
        created_dataset = mock_server._handle_create_dataset(dataset_data)
        dataset_id = created_dataset["data"]["id"]
        
        # Create rows data
        rows_data = {
            "rows": [
                {"cells": [{"columnName": "Column 1", "value": "Value 1"}, {"columnName": "Column 2", "value": "true"}]},
                {"cells": [{"columnName": "Column 1", "value": "Value 2"}, {"columnName": "Column 2", "value": "false"}]}
            ]
        }
        
        # Create dataset rows
        result = mock_server._handle_create_dataset_rows(dataset_id, rows_data)
        
        # Verify result
        assert "status" in result
        assert result["status"] == "SUCCESS"
        assert "data" in result
        assert len(result["data"]) == 2
        
        # Verify rows were stored
        dataset_rows = [row for row in mock_server.data["parameters"]["dataset_rows"].values() 
                        if row["datasetId"] == dataset_id]
        assert len(dataset_rows) == 2
    
    def test_handle_update_dataset_row(self, mock_server):
        """Test updating a dataset row."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create a dataset first
        dataset_data = {
            "name": "Test Dataset For Updating Row",
            "description": "Test dataset description",
            "projectId": project_id,
            "columns": [
                {"name": "Column 1", "dataType": "STRING"},
                {"name": "Column 2", "dataType": "BOOLEAN"}
            ]
        }
        created_dataset = mock_server._handle_create_dataset(dataset_data)
        dataset_id = created_dataset["data"]["id"]
        
        # Create a row
        rows_data = {
            "rows": [
                {"cells": [{"columnName": "Column 1", "value": "Value 1"}, {"columnName": "Column 2", "value": "true"}]}
            ]
        }
        created_rows = mock_server._handle_create_dataset_rows(dataset_id, rows_data)
        row_id = created_rows["data"][0]["id"]
        
        # Update data
        update_data = {
            "cells": [
                {"columnName": "Column 1", "value": "Updated Value"},
                {"columnName": "Column 2", "value": "false"}
            ]
        }
        
        # Update the row
        result = mock_server._handle_update_dataset_row(dataset_id, row_id, update_data)
        
        # Verify result
        assert "status" in result
        assert result["status"] == "SUCCESS"
        assert "data" in result
        
        # Find the cell with Column 1 and verify its value
        for cell in result["data"]["cells"]:
            if cell["columnName"] == "Column 1":
                assert cell["value"] == "Updated Value"
    
    def test_handle_delete_dataset_row(self, mock_server):
        """Test deleting a dataset row."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create a dataset first
        dataset_data = {
            "name": "Test Dataset For Deleting Row",
            "description": "Test dataset description",
            "projectId": project_id,
            "columns": [{"name": "Column 1", "dataType": "STRING"}]
        }
        created_dataset = mock_server._handle_create_dataset(dataset_data)
        dataset_id = created_dataset["data"]["id"]
        
        # Create a row
        rows_data = {
            "rows": [{"cells": [{"columnName": "Column 1", "value": "Value 1"}]}]
        }
        created_rows = mock_server._handle_create_dataset_rows(dataset_id, rows_data)
        row_id = created_rows["data"][0]["id"]
        
        # Delete the row
        result = mock_server._handle_delete_dataset_row(dataset_id, row_id)
        
        # Verify result
        assert "status" in result
        assert result["status"] == "SUCCESS"
        assert row_id not in mock_server.data["parameters"]["dataset_rows"]

@pytest.mark.unit
class TestQTestMockServerIntegrationWorkflows:
    @pytest.fixture
    def mock_server(self):
        """Create a test qTest mock server instance."""
        return QTestMockServer()
    
    def test_test_execution_workflow(self, mock_server):
        """Test a complete test execution workflow."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # 1. Create a module
        module_data = {
            "name": "Test Execution Module",
            "description": "Module for test execution workflow",
            "parentId": None,
            "projectId": project_id
        }
        module = mock_server._handle_create_module(project_id, module_data)
        module_id = module["id"]
        
        # 2. Create a test case
        test_case_data = {
            "name": "Test Case for Execution",
            "description": "Test case for execution workflow",
            "precondition": "System is ready for testing",
            "moduleId": module_id,
            "steps": [
                {"description": "Step 1", "expectedResult": "Result 1"},
                {"description": "Step 2", "expectedResult": "Result 2"}
            ]
        }
        test_case = mock_server._handle_create_test_case(project_id, test_case_data)
        test_case_id = test_case["id"]
        
        # 3. Create a release
        release_data = {
            "name": "Test Execution Release",
            "description": "Release for test execution workflow",
            "status": "ACTIVE"
        }
        release = mock_server._handle_create_release(project_id, release_data)
        release_id = release["id"]
        
        # 4. Create a test cycle
        test_cycle_data = {
            "name": "Test Execution Cycle",
            "description": "Test cycle for execution workflow",
            "releaseId": release_id,
            "status": "IN_PROGRESS"
        }
        test_cycle = mock_server._handle_create_test_cycle(project_id, test_cycle_data)
        test_cycle_id = test_cycle["id"]
        
        # 5. Create a test run
        test_run_data = {
            "name": "Test Run for Execution",
            "description": "Test run for execution workflow",
            "testCaseId": test_case_id,
            "testCycleId": test_cycle_id,
            "status": "NOT_EXECUTED"
        }
        test_run = mock_server._handle_create_test_run(project_id, test_run_data)
        test_run_id = test_run["id"]
        
        # 6. Submit a test log
        test_log_data = {
            "status": "Passed",
            "executionDate": "2025-01-01T10:00:00Z",
            "note": "Test passed successfully",
            "actualResults": "Expected result was observed",
            "testStepLogs": [
                {"description": "Step 1 executed", "expectedResult": "Result 1", "actualResult": "Result 1 achieved", "status": "Passed"},
                {"description": "Step 2 executed", "expectedResult": "Result 2", "actualResult": "Result 2 achieved", "status": "Passed"}
            ]
        }
        test_log = mock_server._handle_submit_test_log(test_run_id, test_log_data)
        test_log_id = test_log["id"]
        
        # 7. Verify the workflow
        # Get test case
        retrieved_test_case = mock_server._handle_get_test_case(test_case_id)
        assert retrieved_test_case["name"] == "Test Case for Execution"
        
        # Get test cycle
        retrieved_test_cycle = mock_server._handle_get_test_cycle(test_cycle_id)
        assert retrieved_test_cycle["name"] == "Test Execution Cycle"
        
        # Get test run (should be updated with Passed status)
        retrieved_test_run = mock_server._handle_get_test_run(test_run_id)
        assert retrieved_test_run["status"] == "Passed"
        
        # Get test logs
        test_logs = mock_server._handle_get_test_logs(test_run_id)
        assert test_logs["total"] > 0
        
        # Check that our log is there
        found = False
        for log in test_logs["items"]:
            if log["id"] == test_log_id:
                found = True
                assert log["status"] == "Passed"
                break
        assert found, "Created test log not found in test_logs result"
    
    def test_auto_test_logs_workflow(self, mock_server):
        """Test the auto test logs workflow from test case creation to execution."""
        # Get project ID from sample data
        project_id = mock_server.data["manager"]["projects"][0]["id"]
        
        # Create auto test logs data with a new test case
        auto_test_logs_data = {
            "testLogs": [
                {
                    "name": "Auto Test Case Execution",
                    "status": "Passed",
                    "note": "Test executed successfully via auto-test-logs",
                    "executionDate": "2025-01-01T10:00:00Z",
                    "testCase": {
                        "name": "Auto Test Case",
                        "description": "Test case created via auto-test-logs",
                        "steps": [
                            {"description": "Step 1", "expectedResult": "Result 1"},
                            {"description": "Step 2", "expectedResult": "Result 2"}
                        ]
                    }
                }
            ]
        }
        
        # Submit auto test logs
        result = mock_server._handle_submit_auto_test_logs(project_id, auto_test_logs_data)
        
        # Verify result structure
        assert "total" in result
        assert result["total"] == 1
        assert "successful" in result
        assert result["successful"] == 1
        assert "failed" in result
        assert result["failed"] == 0
        assert "testLogs" in result
        assert len(result["testLogs"]) == 1
        
        # Extract IDs
        log_result = result["testLogs"][0]
        assert "testCase" in log_result
        test_case_id = log_result["testCase"]["id"]
        assert "testLog" in log_result
        test_log_id = log_result["testLog"]["id"]
        assert "testRun" in log_result
        test_run_id = log_result["testRun"]["id"]
        assert "testCycle" in log_result
        test_cycle_id = log_result["testCycle"]["id"]
        
        # Verify entities were created
        # Test case
        retrieved_test_case = mock_server._handle_get_test_case(test_case_id)
        assert retrieved_test_case["id"] == test_case_id
        assert retrieved_test_case["name"] == "Auto Test Case"
        assert len(retrieved_test_case["steps"]) == 2
        
        # Test run
        retrieved_test_run = mock_server._handle_get_test_run(test_run_id)
        assert retrieved_test_run["id"] == test_run_id
        assert retrieved_test_run["testCaseId"] == test_case_id
        assert retrieved_test_run["testCycleId"] == test_cycle_id
        assert retrieved_test_run["status"] == "Passed"
        
        # Test log
        retrieved_test_logs = mock_server._handle_get_test_logs(test_run_id)
        found = False
        for log in retrieved_test_logs["items"]:
            if log["id"] == test_log_id:
                found = True
                assert log["status"] == "Passed"
                assert log["note"] == "Test executed successfully via auto-test-logs"
                break
        assert found, "Created test log not found in test_logs result"
        
        # Test cycle
        retrieved_test_cycle = mock_server._handle_get_test_cycle(test_cycle_id)
        assert retrieved_test_cycle["id"] == test_cycle_id
        assert retrieved_test_cycle["name"] == "Automation"  # Default name for auto-created cycles
        assert retrieved_test_cycle["projectId"] == project_id