"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import pytest

from ztoq.utils import package_info


@pytest.mark.unit()
class TestPackageInfo:
    """Tests for the package_info module."""

    def test_get_version(self):
        """Test that get_version returns a string."""
        version = package_info.get_version()
        assert isinstance(version, str)
        assert version != "unknown"

    def test_get_python_version(self):
        """Test that get_python_version returns a tuple of integers."""
        version = package_info.get_python_version()
        assert isinstance(version, tuple)
        assert len(version) == 3
        assert all(isinstance(v, int) for v in version)

    def test_get_package_metadata(self):
        """Test that get_package_metadata returns a dictionary with expected keys."""
        metadata = package_info.get_package_metadata()
        assert isinstance(metadata, dict)
        assert "name" in metadata
        assert "version" in metadata
        assert metadata["name"] == "ztoq"
