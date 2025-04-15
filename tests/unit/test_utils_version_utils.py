"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

from unittest.mock import patch

import pytest

from ztoq.utils import version_utils


@pytest.mark.unit
class TestVersionUtils:
    """Tests for the version_utils module."""

    @patch("ztoq.utils.version_utils.get_version")
    def test_get_version_parts(self, mock_get_version):
        """Test that get_version_parts correctly parses version strings."""
        mock_get_version.return_value = "1.2.3"
        parts = version_utils.get_version_parts()
        assert parts == {
            "major": "1",
            "minor": "2",
            "patch": "3",
            "suffix": "",
            "full": "1.2.3",
        }

        # Test with suffix
        mock_get_version.return_value = "1.2.3-beta"
        parts = version_utils.get_version_parts()
        assert parts == {
            "major": "1",
            "minor": "2",
            "patch": "3",
            "suffix": "-beta",
            "full": "1.2.3-beta",
        }

        # Test invalid version format
        mock_get_version.return_value = "invalid"
        with pytest.raises(ValueError):
            version_utils.get_version_parts()

    @patch("os.path.exists")
    @patch("pathlib.Path.read_text")
    @patch("pathlib.Path.write_text")
    def test_update_version(self, mock_write, mock_read, mock_exists):
        """Test that update_version updates version numbers in files."""
        mock_exists.return_value = True
        mock_read.side_effect = [
            '__version__ = "0.4.0"',  # VERSION_PATH
            'version = "0.4.0"',       # PYPROJECT_PATH
        ]

        # Test normal update
        result = version_utils.update_version("0.5.0")
        assert result[str(version_utils.VERSION_PATH)] is True
        assert result[str(version_utils.PYPROJECT_PATH)] is True
        assert mock_write.call_count == 2

        # Test dry run
        mock_write.reset_mock()
        result = version_utils.update_version("0.5.0", dry_run=True)
        assert result[str(version_utils.VERSION_PATH)] is True
        assert result[str(version_utils.PYPROJECT_PATH)] is True
        assert mock_write.call_count == 0

    @patch("ztoq.utils.version_utils.get_version")
    @patch("ztoq.utils.version_utils.update_version")
    def test_bump_version(self, mock_update, mock_get_version):
        """Test that bump_version correctly increments version numbers."""
        mock_get_version.return_value = "1.2.3"
        mock_update.return_value = {"file1": True, "file2": True}

        # Test patch bump
        new_version, updated = version_utils.bump_version("patch")
        assert new_version == "1.2.4"
        mock_update.assert_called_once_with("1.2.4", False)

        # Test minor bump
        mock_update.reset_mock()
        new_version, updated = version_utils.bump_version("minor")
        assert new_version == "1.3.0"
        mock_update.assert_called_once_with("1.3.0", False)

        # Test major bump
        mock_update.reset_mock()
        new_version, updated = version_utils.bump_version("major")
        assert new_version == "2.0.0"
        mock_update.assert_called_once_with("2.0.0", False)

        # Test invalid part
        with pytest.raises(ValueError):
            version_utils.bump_version("invalid")

    @patch("ztoq.utils.version_utils.get_version")
    @patch("os.path.exists")
    @patch("pathlib.Path.read_text")
    def test_check_version_consistency(self, mock_read, mock_exists, mock_get_version):
        """Test that check_version_consistency correctly identifies inconsistent files."""
        mock_get_version.return_value = "1.2.3"
        mock_exists.return_value = True

        # Test when all versions are consistent
        mock_read.side_effect = [
            '__version__ = "1.2.3"',  # VERSION_PATH
            'version = "1.2.3"',       # PYPROJECT_PATH
        ]
        inconsistent = version_utils.check_version_consistency()
        assert inconsistent == []

        # Test when __init__.py is inconsistent
        mock_read.side_effect = [
            '__version__ = "1.2.2"',  # VERSION_PATH (inconsistent)
            'version = "1.2.3"',       # PYPROJECT_PATH
        ]
        inconsistent = version_utils.check_version_consistency()
        assert str(version_utils.VERSION_PATH) in inconsistent
        assert str(version_utils.PYPROJECT_PATH) not in inconsistent

        # Test when both files are inconsistent
        mock_read.side_effect = [
            '__version__ = "1.2.2"',  # VERSION_PATH (inconsistent)
            'version = "1.2.4"',       # PYPROJECT_PATH (inconsistent)
        ]
        inconsistent = version_utils.check_version_consistency()
        assert str(version_utils.VERSION_PATH) in inconsistent
        assert str(version_utils.PYPROJECT_PATH) in inconsistent
