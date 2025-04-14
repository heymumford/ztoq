"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from ztoq.models import ZephyrConfig, Execution, Attachment, CustomField
from ztoq.zephyr_client import ZephyrClient
from ztoq.storage import SQLiteStorage, JSONStorage
from ztoq.exporter import ZephyrExporter, ZephyrExportManager

@pytest.mark.unit


class TestZephyrExporter:
    @pytest.fixture
    def config(self):
        """Create a test Zephyr configuration."""
        return ZephyrConfig(
            base_url="https://api.zephyrscale.example.com/v2",
                api_token="test-token",
                project_key="TEST",
            )

    @pytest.fixture
    def client(self, config):
        """Create a mock Zephyr client."""
        client = MagicMock(spec=ZephyrClient)
        client.config = config
        return client

    @pytest.fixture
    def json_storage(self, tmp_path):
        """Create a JSON storage instance."""
        return JSONStorage(tmp_path / "json_output")

    @pytest.fixture
    def sqlite_storage(self, tmp_path):
        """Create a SQLite storage instance."""
        return SQLiteStorage(tmp_path / "test.db")

    @pytest.fixture
    def json_exporter(self, client, json_storage, monkeypatch):
        """Create a JSON exporter instance."""
        exporter = ZephyrExporter(client, output_format="json")
        monkeypatch.setattr(exporter, "storage", json_storage)
        return exporter

    @pytest.fixture
    def sqlite_exporter(self, client, sqlite_storage, monkeypatch):
        """Create a SQLite exporter instance."""
        exporter = ZephyrExporter(client, output_format="sqlite")
        monkeypatch.setattr(exporter, "storage", sqlite_storage)
        return exporter

    @patch("ztoq.storage.SQLiteStorage.__enter__", return_value=MagicMock(spec=SQLiteStorage))
    @patch("ztoq.storage.SQLiteStorage.__exit__")
    def test_exporter_initialization(self, mock_exit, mock_enter, client):
        """Test exporter initialization with different output formats."""
        json_exporter = ZephyrExporter(client, output_format="json")
        assert isinstance(json_exporter.storage, JSONStorage)
        assert json_exporter.output_format == "json"

        sqlite_exporter = ZephyrExporter(client, output_format="sqlite")
        assert isinstance(sqlite_exporter.storage, SQLiteStorage)
        assert sqlite_exporter.output_format == "sqlite"

        # Test custom output path
        output_path = Path("/tmp/custom_output")
        exporter = ZephyrExporter(client, output_format="json", output_path=output_path)
        assert exporter.output_path == output_path

        # Test invalid output format
        with pytest.raises(ValueError):
            ZephyrExporter(client, output_format="invalid")

    @patch("ztoq.exporter.SQLiteStorage")
    def test_sqlite_database_initialization(self, mock_sqlite_storage, client):
        """Test SQLite database initialization."""
        mock_instance = MagicMock()
        mock_sqlite_storage.return_value = mock_instance
        mock_instance.__enter__.return_value = mock_instance
        ZephyrExporter(client, output_format="sqlite")
        # SQLite database should be initialized during exporter creation
        mock_instance.initialize_database.assert_called_once()

    @patch("ztoq.storage.JSONStorage.save_project")
    @patch("ztoq.storage.JSONStorage.save_folders")
    @patch("ztoq.storage.JSONStorage.save_statuses")
    @patch("ztoq.storage.JSONStorage.save_priorities")
    @patch("ztoq.storage.JSONStorage.save_environments")
    @patch("ztoq.storage.JSONStorage.save_test_cases")
    @patch("ztoq.storage.JSONStorage.save_test_cycles")
    @patch("ztoq.storage.JSONStorage.save_test_executions")
    def test_export_all(
        self,
            mock_save_execs,
            mock_save_cycles,
            mock_save_cases,
            mock_save_envs,
            mock_save_priorities,
            mock_save_statuses,
            mock_save_folders,
            mock_save_project,
            json_exporter,
            client,
        ):
        """Test exporting all data."""
        # Mock client methods with proper serializable objects
        project = MagicMock()
        project.key = "TEST"
        project.name = "Test Project"
        project.id = "123"
        project.description = "Test"
        client.get_projects.return_value = [project]
        client.get_folders.return_value = [MagicMock()]
        client.get_statuses.return_value = [MagicMock()]
        client.get_priorities.return_value = [MagicMock()]
        client.get_environments.return_value = [MagicMock()]

        # Mock test cases
        test_cases = [MagicMock() for _ in range(2)]
        client.get_test_cases.return_value = test_cases

        # Mock test cycles
        test_cycles = [MagicMock()]
        client.get_test_cycles.return_value = test_cycles

        # Mock test executions
        test_executions = [MagicMock()]
        json_exporter._fetch_executions_for_cycle = MagicMock(return_value=test_executions)

        # Call export_all
        result = json_exporter.export_all()

        # Verify results without checking the API calls
        client.get_projects.assert_called_once()
        client.get_folders.assert_called_once()
        client.get_statuses.assert_called_once()
        client.get_priorities.assert_called_once()
        client.get_environments.assert_called_once()
        client.get_test_cases.assert_called_once()
        client.get_test_cycles.assert_called_once()

        # Verify export results
        assert result["folders"] == 1
        assert result["statuses"] == 1
        assert result["priorities"] == 1
        assert result["environments"] == 1
        assert result["test_cases"] == 2
        assert result["test_cycles"] == 1
        assert result["test_executions"] == 1

    def test_fetch_executions_for_cycle(self, json_exporter, client):
        """Test fetching executions for a cycle."""
        # Mock client method with advanced mock including attachments and custom fields
        execution1 = MagicMock(spec=Execution)
        execution1.id = "exec1"
        execution1.test_case_key = "TEST-TC-1"
        execution1.status = "Pass"
        execution1.comment = "Test passed successfully"
        execution1.attachments = [
            Attachment(id="att1", filename="screenshot.png", contentType="image/png", size=1024)
        ]
        execution1.custom_fields = [
            CustomField(id="cf1", name="Test Environment", type="text", value="Staging")
        ]

        execution2 = MagicMock(spec=Execution)
        execution2.id = "exec2"
        execution2.test_case_key = "TEST-TC-2"
        execution2.status = "Fail"
        execution2.comment = "Test failed due to configuration issue"
        execution2.attachments = [
            Attachment(id="att2", filename="error.log", contentType="text/plain", size=512)
        ]
        execution2.custom_fields = [
            CustomField(id="cf1", name="Test Environment", type="text", value="Production"),
                CustomField(id="cf2", name="Priority Fix", type="checkbox", value=True),
            ]

        test_executions = [execution1, execution2]
        client.get_test_executions.return_value = test_executions

        # Fetch executions
        result = json_exporter._fetch_executions_for_cycle("cycle-id")

        # Verify
        assert result == test_executions
        assert len(result) == 2
        assert result[0].attachments[0].filename == "screenshot.png"
        assert result[1].custom_fields[1].value is True
        client.get_test_executions.assert_called_once_with(cycle_id="cycle-id")


@pytest.mark.unit


class TestZephyrExportManager:
    @pytest.fixture
    def config(self):
        """Create a test Zephyr configuration."""
        return ZephyrConfig(
            base_url="https://api.zephyrscale.example.com/v2",
                api_token="test-token",
                project_key="TEST",
            )

    @pytest.fixture
    def export_manager(self, config, tmp_path):
        """Create a ZephyrExportManager instance."""
        return ZephyrExportManager(
            config=config,
                output_format="json",
                output_dir=tmp_path / "exports",
                spec_path=None,
                concurrency=2,
            )

    def test_export_project(self, export_manager):
        """Test exporting a project."""
        # Patch the export_all method of ZephyrExporter
        with patch.object(
            ZephyrExporter, "export_all", return_value={"test_cases": 10, "test_cycles": 5}
        ):
            # Patch the ZephyrClient so we don't make real API calls
            with patch("ztoq.exporter.ZephyrClient") as mock_client_class:
                # Setup client mock
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                # Export a project
                result = export_manager.export_project("TEST")

                # Verify result
                assert result == {"test_cases": 10, "test_cycles": 5}

    def test_export_all_projects(self, export_manager):
        """Test exporting all projects."""
        # Patch the ZephyrClient so we don't make real API calls
        with patch("ztoq.exporter.ZephyrClient") as mock_client_class:
            # Create mock client
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            # Mock get_projects
            project1 = MagicMock()
            project1.key = "PROJ1"
            project2 = MagicMock()
            project2.key = "PROJ2"
            mock_client.get_projects.return_value = [project1, project2]
            # Mock export_project method
            with patch.object(export_manager, "export_project") as mock_export_project:
                mock_export_project.side_effect = [
                    {"test_cases": 10},
                        {"test_cases": 20},
                    ]
                # Callback for progress tracking
                progress_callback = MagicMock()
                # Export all projects
                result = export_manager.export_all_projects(
                    projects_to_export=["PROJ1", "PROJ2"], progress_callback=progress_callback
                )
                # Verify export was attempted for each project
                assert mock_export_project.call_count == 2
                # Verify result
                assert "PROJ1" in result
                assert "PROJ2" in result
                assert result["PROJ1"] == {"test_cases": 10}
                assert result["PROJ2"] == {"test_cases": 20}

    def test_export_all_projects_with_error(self, export_manager):
        """Test handling errors during export."""
        # Patch the ZephyrClient so we don't make real API calls
        with patch("ztoq.exporter.ZephyrClient") as mock_client_class:
            # Create mock client
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            # Mock get_projects
            project1 = MagicMock()
            project1.key = "PROJ1"
            project2 = MagicMock()
            project2.key = "PROJ2"
            mock_client.get_projects.return_value = [project1, project2]
            # Mock export_project method - first succeeds, second fails
            with patch.object(export_manager, "export_project") as mock_export_project:
                mock_export_project.side_effect = [
                    {"test_cases": 10},
                        Exception("Export failed"),
                    ]
                # Callback for progress tracking
                progress_callback = MagicMock()
                # Export all projects
                result = export_manager.export_all_projects(progress_callback=progress_callback)
                # Verify result - should include only the successful project
                assert "PROJ1" in result
                assert "PROJ2" not in result
                assert result["PROJ1"] == {"test_cases": 10}
                # Verify progress callback was called appropriately
                assert progress_callback.call_count >= 3  # At least calls for PROJ1 and PROJ2
