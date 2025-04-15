"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Simple test for the utils package.
"""

import unittest

from ztoq.utils import dependency_manager, package_info


class TestPackageInfo(unittest.TestCase):
    """Test the package_info module."""

    def test_get_version(self):
        """Test that get_version returns a string."""
        version = package_info.get_version()
        self.assertIsInstance(version, str)
        self.assertNotEqual(version, "unknown")

    def test_get_python_version(self):
        """Test that get_python_version returns a tuple of integers."""
        version = package_info.get_python_version()
        self.assertIsInstance(version, tuple)
        self.assertEqual(len(version), 3)
        for v in version:
            self.assertIsInstance(v, int)

    def test_get_package_metadata(self):
        """Test that get_package_metadata returns a dictionary with expected keys."""
        metadata = package_info.get_package_metadata()
        self.assertIsInstance(metadata, dict)
        self.assertIn("name", metadata)
        self.assertIn("version", metadata)
        self.assertEqual(metadata["name"], "ztoq")


class TestDependencyManager(unittest.TestCase):
    """Test the dependency_manager module."""

    def test_is_dependency_installed(self):
        """Test that is_dependency_installed works correctly."""
        # This should always be true since we're running in Python
        self.assertTrue(dependency_manager.is_dependency_installed("sys"))
        # This should always be false for a non-existent package
        self.assertFalse(dependency_manager.is_dependency_installed("nonexistent_package_12345"))


if __name__ == "__main__":
    unittest.main()
