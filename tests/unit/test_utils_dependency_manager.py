"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

from unittest.mock import patch

import pytest

from ztoq.utils import dependency_manager


@pytest.mark.unit()
class TestDependencyManager:
    """Tests for the dependency_manager module."""

    def test_is_dependency_installed(self):
        """Test that is_dependency_installed checks if a dependency is installed."""
        # This should always be true since pytest is installed in the testing environment
        assert dependency_manager.is_dependency_installed("pytest") is True
        # This should always be false for a non-existent package
        assert dependency_manager.is_dependency_installed("nonexistent_package_12345") is False

    @patch("ztoq.utils.dependency_manager.is_dependency_installed")
    def test_check_dependencies(self, mock_is_installed):
        """Test that check_dependencies returns the correct tuple."""
        # Mock that all dependencies are installed
        mock_is_installed.return_value = True
        all_installed, missing = dependency_manager.check_dependencies(["dep1", "dep2"])
        assert all_installed is True
        assert missing == []

        # Mock that one dependency is not installed
        mock_is_installed.side_effect = [True, False]
        all_installed, missing = dependency_manager.check_dependencies(["dep1", "dep2"])
        assert all_installed is False
        assert missing == ["dep2"]

    @patch("ztoq.utils.dependency_manager.get_requirements")
    @patch("ztoq.utils.dependency_manager.check_dependencies")
    def test_check_all_project_dependencies(self, mock_check, mock_get_reqs):
        """Test that check_all_project_dependencies calls the correct functions."""
        mock_get_reqs.return_value = ["dep1", "dep2"]
        mock_check.return_value = (True, [])

        result = dependency_manager.check_all_project_dependencies()
        mock_get_reqs.assert_called_once()
        mock_check.assert_called_once_with(["dep1", "dep2"])
        assert result == (True, [])

    @patch("ztoq.utils.dependency_manager.get_optional_dependencies")
    @patch("ztoq.utils.dependency_manager.is_dependency_installed")
    def test_check_optional_dependency_group(self, mock_is_installed, mock_get_optionals):
        """Test that check_optional_dependency_group returns the correct tuple."""
        # Mock that the group exists and all dependencies are installed
        mock_get_optionals.return_value = {"dev": ["pytest", "black"]}
        mock_is_installed.return_value = True

        all_installed, missing = dependency_manager.check_optional_dependency_group("dev")
        assert all_installed is True
        assert missing == set()

        # Mock that the group doesn't exist
        mock_get_optionals.return_value = {"dev": ["pytest", "black"]}
        all_installed, missing = dependency_manager.check_optional_dependency_group("nonexistent")
        assert all_installed is False
        assert missing == {"Group 'nonexistent' not found"}

        # Mock that the group exists but some dependencies are not installed
        mock_get_optionals.return_value = {"dev": ["pytest", "black"]}
        mock_is_installed.side_effect = [True, False]

        all_installed, missing = dependency_manager.check_optional_dependency_group("dev")
        assert all_installed is False
        assert missing == {"black"}
