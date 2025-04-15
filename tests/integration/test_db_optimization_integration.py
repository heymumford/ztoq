"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Integration tests for the database optimization integration.

These tests verify that the optimized database manager is properly integrated
with the database factory and helpers.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pytest

from ztoq.database_factory import DatabaseFactory, DatabaseType
from ztoq.db_optimization_helpers import (
    get_database_performance_report,
    get_optimized_database_manager,
    migrate_to_optimized_manager,
    optimize_for_reads,
    optimize_for_writes,
    reset_performance_tracking,
)
from ztoq.optimized_database_manager import OptimizedDatabaseManager


@pytest.mark.integration
class TestDatabaseOptimizationIntegration(unittest.TestCase):
    """Integration tests for database optimization features."""

    def setUp(self):
        """Set up test fixtures for database optimization integration."""
        # Create a temporary directory for database files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test.db")

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_get_optimized_database_manager(self):
        """Test getting an optimized database manager."""
        # Mock the DatabaseFactory.create_database_manager method
        with patch.object(DatabaseFactory, "create_database_manager") as mock_create:
            # Create a mock OptimizedDatabaseManager
            mock_optimized = MagicMock(spec=OptimizedDatabaseManager)
            mock_create.return_value = mock_optimized

            # Call the get_optimized_database_manager function
            manager = get_optimized_database_manager(
                db_type=DatabaseType.SQLITE, db_path=self.db_path,
            )

            # Verify that the mock was returned and the function was called with optimize=True
            self.assertEqual(manager, mock_optimized)
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            self.assertTrue(call_kwargs.get("optimize", False))

    def test_migrate_to_optimized_manager(self):
        """Test migrating from a standard manager to an optimized one."""
        # Create a mock standard manager
        mock_standard_manager = MagicMock()

        # Mock the OptimizedDatabaseManager constructor
        with patch("ztoq.db_optimization_helpers.OptimizedDatabaseManager") as mock_optimized_class:
            # Create a mock for the optimized manager instance
            mock_optimized_instance = MagicMock(spec=OptimizedDatabaseManager)
            mock_optimized_class.return_value = mock_optimized_instance

            # Call the migrate_to_optimized_manager function
            result = migrate_to_optimized_manager(mock_standard_manager)

            # Verify that the mock optimized manager was returned
            self.assertEqual(result, mock_optimized_instance)

            # Verify that the constructor was called with the standard manager
            mock_optimized_class.assert_called_once_with(base_manager=mock_standard_manager)

    def test_performance_reporting_integration(self):
        """Test integration of performance reporting with database operations."""
        # Reset performance tracking
        reset_performance_tracking()

        # Get a performance report (should be empty initially)
        report = get_database_performance_report()

        # Verify that the report has the expected structure
        self.assertIn("statistics", report)
        self.assertIn("recommendations", report)
        self.assertIn("cache", report)

        # Optimize for different workloads and verify they don't raise exceptions
        optimize_for_reads()
        optimize_for_writes()

    def test_environment_variable_integration(self):
        """Test integration with environment variables."""
        # Use patch.dict to set environment variables
        with patch.dict(
            "os.environ",
            {
                "ZTOQ_DB_TYPE": DatabaseType.SQLITE,
                "ZTOQ_DB_PATH": self.db_path,
                "ZTOQ_OPTIMIZE_DB": "true",
            },
            clear=True,
        ):
            # Mock the create_database_manager to avoid actual file system operations
            with patch.object(DatabaseFactory, "create_database_manager") as mock_create:
                # Create a mock instance to return
                mock_instance = MagicMock(spec=OptimizedDatabaseManager)
                mock_create.return_value = mock_instance

                # Call the get_database_manager function
                from ztoq.database_factory import get_database_manager

                manager = get_database_manager()

                # Verify the mock was called
                mock_create.assert_called_once()

                # Since we're testing the environment variable integration, we just need
                # to verify the mock was called and returned the mock instance
                self.assertEqual(manager, mock_instance)


if __name__ == "__main__":
    unittest.main()
