"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Unit tests for the data_fetcher module.
"""

import pytest
from unittest.mock import MagicMock, patch
from ztoq.models import (
    ZephyrConfig, Project, Case, CycleInfo, Execution, 
    Folder, Status, Priority, Environment
)
from ztoq.zephyr_client import ZephyrClient
from ztoq.data_fetcher import (
    create_authenticated_client,
    fetch_projects,
    fetch_all_test_cases,
    fetch_all_test_cycles,
    fetch_all_test_executions,
    fetch_folders,
    fetch_statuses,
    fetch_priorities,
    fetch_environments,
    fetch_all_project_data,
    fetch_all_projects_data,
    FetchResult,
)

@pytest.fixture


def config():
    """Create a test Zephyr configuration."""
    return ZephyrConfig(
        base_url="https://api.zephyrscale.example.com/v2",
            api_token="test-token",
            project_key="TEST",
        )


@pytest.fixture


def mock_client():
    """Create a mock Zephyr client."""
    client = MagicMock(spec=ZephyrClient)
    return client


@pytest.mark.unit


class TestDataFetcher:
    """Test data fetcher functions."""

    def test_create_authenticated_client(self, config):
        """Test creating an authenticated client."""
        with patch("ztoq.data_fetcher.ZephyrClient") as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_class.return_value = mock_client_instance

            client = create_authenticated_client(config)

            mock_client_class.assert_called_once_with(config)
            assert client == mock_client_instance

    def test_fetch_projects(self, mock_client):
        """Test fetching projects."""
        # Create mock projects
        projects = [
            Project(id="1", key="PROJ1", name="Project 1"),
                Project(id="2", key="PROJ2", name="Project 2"),
            ]
        mock_client.get_projects.return_value = projects

        result = fetch_projects(mock_client)

        assert result == projects
        mock_client.get_projects.assert_called_once()

    def test_fetch_projects_error(self, mock_client):
        """Test fetching projects with error."""
        mock_client.get_projects.side_effect = Exception("API error")

        result = fetch_projects(mock_client)

        assert result == []
        mock_client.get_projects.assert_called_once()

    def test_fetch_all_test_cases(self, mock_client):
        """Test fetching all test cases."""
        # Create mock test cases
        test_cases = [
            Case(id="tc1", key="TEST-1", name="Test Case 1"),
                Case(id="tc2", key="TEST-2", name="Test Case 2"),
            ]
        mock_client.get_test_cases.return_value = test_cases

        result = fetch_all_test_cases(mock_client, "TEST")

        assert result.entity_type == "test_cases"
        assert result.project_key == "TEST"
        assert result.items == test_cases
        assert result.count == 2
        assert result.success is True
        assert result.error is None
        mock_client.get_test_cases.assert_called_once_with(project_key="TEST")

    def test_fetch_all_test_cases_error(self, mock_client):
        """Test fetching all test cases with error."""
        mock_client.get_test_cases.side_effect = Exception("API error")

        result = fetch_all_test_cases(mock_client, "TEST")

        assert result.entity_type == "test_cases"
        assert result.project_key == "TEST"
        assert result.items == []
        assert result.count == 0
        assert result.success is False
        assert "API error" in result.error
        mock_client.get_test_cases.assert_called_once_with(project_key="TEST")

    def test_fetch_all_test_cycles(self, mock_client):
        """Test fetching all test cycles."""
        # Create mock test cycles
        test_cycles = [CycleInfo(id="cy1", key="CYCLE-1", name="Test Cycle 1", project_key="TEST")]
        mock_client.get_test_cycles.return_value = test_cycles

        result = fetch_all_test_cycles(mock_client, "TEST")

        assert result.entity_type == "test_cycles"
        assert result.project_key == "TEST"
        assert result.items == test_cycles
        assert result.count == 1
        assert result.success is True
        mock_client.get_test_cycles.assert_called_once_with(project_key="TEST")

    def test_fetch_all_test_executions(self, mock_client):
        """Test fetching all test executions."""
        # Create mock test executions
        test_executions = [
            Execution(id="ex1", test_case_key="TEST-1", cycle_id="cy1", status="Pass")
        ]
        mock_client.get_test_executions.return_value = test_executions

        result = fetch_all_test_executions(mock_client, "TEST")

        assert result.entity_type == "test_executions"
        assert result.project_key == "TEST"
        assert result.items == test_executions
        assert result.count == 1
        assert result.success is True
        mock_client.get_test_executions.assert_called_once_with(project_key="TEST")

    def test_fetch_folders(self, mock_client):
        """Test fetching folders."""
        # Create mock folders
        folders = [Folder(id="f1", name="Folder 1", folder_type="TEST_CASE", project_key="TEST")]
        mock_client.get_folders.return_value = folders

        result = fetch_folders(mock_client, "TEST")

        assert result.entity_type == "folders"
        assert result.project_key == "TEST"
        assert result.items == folders
        assert result.count == 1
        assert result.success is True
        mock_client.get_folders.assert_called_once_with(project_key="TEST")

    def test_fetch_statuses(self, mock_client):
        """Test fetching statuses."""
        # Create mock statuses
        statuses = [Status(id="s1", name="Pass", type="TEST_EXECUTION")]
        mock_client.get_statuses.return_value = statuses

        result = fetch_statuses(mock_client, "TEST")

        assert result.entity_type == "statuses"
        assert result.project_key == "TEST"
        assert result.items == statuses
        assert result.count == 1
        assert result.success is True
        mock_client.get_statuses.assert_called_once_with(project_key="TEST")

    def test_fetch_priorities(self, mock_client):
        """Test fetching priorities."""
        # Create mock priorities
        priorities = [Priority(id="p1", name="High", rank=1)]
        mock_client.get_priorities.return_value = priorities

        result = fetch_priorities(mock_client, "TEST")

        assert result.entity_type == "priorities"
        assert result.project_key == "TEST"
        assert result.items == priorities
        assert result.count == 1
        assert result.success is True
        mock_client.get_priorities.assert_called_once_with(project_key="TEST")

    def test_fetch_environments(self, mock_client):
        """Test fetching environments."""
        # Create mock environments
        environments = [Environment(id="e1", name="Production")]
        mock_client.get_environments.return_value = environments

        result = fetch_environments(mock_client, "TEST")

        assert result.entity_type == "environments"
        assert result.project_key == "TEST"
        assert result.items == environments
        assert result.count == 1
        assert result.success is True
        mock_client.get_environments.assert_called_once_with(project_key="TEST")

    @patch("ztoq.data_fetcher.fetch_all_test_cases")
    @patch("ztoq.data_fetcher.fetch_all_test_cycles")
    @patch("ztoq.data_fetcher.fetch_all_test_executions")
    @patch("ztoq.data_fetcher.fetch_folders")
    @patch("ztoq.data_fetcher.fetch_statuses")
    @patch("ztoq.data_fetcher.fetch_priorities")
    @patch("ztoq.data_fetcher.fetch_environments")
    def test_fetch_all_project_data(
        self,
            mock_fetch_environments,
            mock_fetch_priorities,
            mock_fetch_statuses,
            mock_fetch_folders,
            mock_fetch_executions,
            mock_fetch_cycles,
            mock_fetch_cases,
            mock_client,
        ):
        """Test fetching all project data."""
        # Create mock results
        mock_fetch_cases.return_value = FetchResult(
            entity_type="test_cases", project_key="TEST", items=[], count=0, success=True
        )
        mock_fetch_cycles.return_value = FetchResult(
            entity_type="test_cycles", project_key="TEST", items=[], count=0, success=True
        )
        mock_fetch_executions.return_value = FetchResult(
            entity_type="test_executions", project_key="TEST", items=[], count=0, success=True
        )
        mock_fetch_folders.return_value = FetchResult(
            entity_type="folders", project_key="TEST", items=[], count=0, success=True
        )
        mock_fetch_statuses.return_value = FetchResult(
            entity_type="statuses", project_key="TEST", items=[], count=0, success=True
        )
        mock_fetch_priorities.return_value = FetchResult(
            entity_type="priorities", project_key="TEST", items=[], count=0, success=True
        )
        mock_fetch_environments.return_value = FetchResult(
            entity_type="environments", project_key="TEST", items=[], count=0, success=True
        )

        # Create mock callback
        callback = MagicMock()

        # Call function
        result = fetch_all_project_data(mock_client, "TEST", callback)

        # Check result
        assert len(result) == 7
        assert "test_cases" in result
        assert "test_cycles" in result
        assert "test_executions" in result
        assert "folders" in result
        assert "statuses" in result
        assert "priorities" in result
        assert "environments" in result

        # Check callback was called
        assert callback.call_count == 7

    @patch("ztoq.data_fetcher.fetch_projects")
    @patch("ztoq.data_fetcher.fetch_all_project_data")
    def test_fetch_all_projects_data(
        self, mock_fetch_all_project_data, mock_fetch_projects, mock_client
    ):
        """Test fetching data for all projects."""
        # Create mock projects
        mock_projects = [
            Project(id="1", key="PROJ1", name="Project 1"),
                Project(id="2", key="PROJ2", name="Project 2"),
            ]
        mock_fetch_projects.return_value = mock_projects

        # Create mock project data results
        mock_fetch_all_project_data.return_value = {
            "test_cases": FetchResult(
                entity_type="test_cases", project_key="PROJ1", items=[], count=0, success=True
            )
        }

        # Call function with no project keys (should fetch all)
        result = fetch_all_projects_data(mock_client)

        # Check result
        assert len(result) == 2
        assert "PROJ1" in result
        assert "PROJ2" in result

        # Check fetch_projects was called
        mock_fetch_projects.assert_called_once()

        # Check fetch_all_project_data was called twice (once for each project)
        assert mock_fetch_all_project_data.call_count == 2

        # Now test with specified project keys
        mock_fetch_all_project_data.reset_mock()
        mock_fetch_projects.reset_mock()

        result = fetch_all_projects_data(mock_client, ["PROJ1"])

        # Check result
        assert len(result) == 1
        assert "PROJ1" in result

        # Check fetch_projects was not called
        mock_fetch_projects.assert_not_called()

        # Check fetch_all_project_data was called once
        mock_fetch_all_project_data.assert_called_once()
