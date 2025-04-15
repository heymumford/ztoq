"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Unit tests for critical path optimization module.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from tests.performance.test_critical_path import CriticalPathOptimizer


class TestCriticalPathOptimizer(unittest.TestCase):
    """Tests for the CriticalPathOptimizer class."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for test outputs
        self.test_output_dir = tempfile.mkdtemp()

        # Create a mock profile data directory
        self.profile_data_dir = tempfile.mkdtemp()

        # Mock pstats.Stats for testing
        self.patcher = patch("pstats.Stats")
        self.mock_stats = self.patcher.start()

        # Setup mock stats
        self.mock_stats_instance = MagicMock()
        self.mock_stats.return_value = self.mock_stats_instance

        # Setup sort_stats and print_stats methods
        self.mock_stats_instance.sort_stats.return_value = self.mock_stats_instance

        # Create optimizer instance
        self.optimizer = CriticalPathOptimizer(
            profile_data_dir=self.profile_data_dir,
            output_dir=self.test_output_dir,
        )

    def tearDown(self):
        """Tear down test environment."""
        # Stop patcher
        self.patcher.stop()

        # Clean up test directories
        import shutil
        shutil.rmtree(self.test_output_dir, ignore_errors=True)
        shutil.rmtree(self.profile_data_dir, ignore_errors=True)

    def test_initialization(self):
        """Test initialization of optimizer."""
        self.assertEqual(self.optimizer.profile_data_dir, Path(self.profile_data_dir))
        self.assertEqual(self.optimizer.output_dir, Path(self.test_output_dir))
        self.assertEqual(self.optimizer.hotspots, {})
        self.assertEqual(self.optimizer.call_graphs, {})
        self.assertEqual(self.optimizer.optimization_recommendations, [])

    @patch("tests.performance.test_critical_path.Path.glob")
    def test_find_profile_data(self, mock_glob):
        """Test finding profile data files."""
        # Mock glob to return some profile files
        mock_profile_files = [
            Path(self.profile_data_dir) / "extraction_b50_c1.prof",
            Path(self.profile_data_dir) / "transformation_b50_c1.prof",
        ]
        mock_glob.return_value = mock_profile_files

        # Call method
        result = self.optimizer.find_profile_data()

        # Verify result
        self.assertEqual(result, mock_profile_files)
        mock_glob.assert_called_once_with("**/*.prof")

    @patch("tests.performance.test_critical_path.io.StringIO")
    def test_analyze_profile(self, mock_stringio):
        """Test analyzing a profile file."""
        # Create a mock profile path
        profile_path = Path(self.profile_data_dir) / "extraction_b50_c1.prof"

        # Setup mock StringIO
        mock_io = MagicMock()
        mock_stringio.return_value = mock_io

        # Mock getvalue to return profile stats text
        mock_io.getvalue.return_value = """
         ncalls  tottime  percall  cumtime  percall filename:lineno(function)
             1    0.000    0.000    1.234    1.234 ztoq/migration.py:123(_extract_test_cases)
            10    0.050    0.005    0.800    0.080 ztoq/batch_strategies.py:45(create_batches)
            50    0.030    0.000    0.600    0.012 ztoq/work_queue.py:234(process)
        """

        # Call method
        result = self.optimizer.analyze_profile(profile_path)

        # Verify result
        self.assertEqual(result["phase"], "extraction")
        self.assertEqual(result["config"], "b50_c1")
        self.assertEqual(result["profile_path"], str(profile_path))

        # Check function stats
        self.assertIn("ztoq/migration.py:123(_extract_test_cases)", result["function_stats"])
        self.assertIn("ztoq/batch_strategies.py:45(create_batches)", result["function_stats"])
        self.assertIn("ztoq/work_queue.py:234(process)", result["function_stats"])

        # Check percentages
        total_time = 1.234 + 0.800 + 0.600
        for func_name, stats in result["function_stats"].items():
            cum_time = stats["cumulative_time"]
            expected_percentage = (cum_time / total_time) * 100
            self.assertAlmostEqual(stats["percentage"], expected_percentage, places=1)

    @patch.object(CriticalPathOptimizer, "find_profile_data")
    @patch.object(CriticalPathOptimizer, "analyze_profile")
    def test_analyze_all_profiles(self, mock_analyze, mock_find):
        """Test analyzing all profiles."""
        # Mock profile paths
        mock_profile_paths = [
            Path(self.profile_data_dir) / "extraction_b50_c1.prof",
            Path(self.profile_data_dir) / "transformation_b50_c1.prof",
        ]
        mock_find.return_value = mock_profile_paths

        # Mock analyze_profile results
        mock_analyze.side_effect = [
            {
                "phase": "extraction",
                "config": "b50_c1",
                "total_time": 5.0,
                "function_stats": {
                    "func1": {"percentage": 50.0, "cumulative_time": 2.5},
                    "func2": {"percentage": 30.0, "cumulative_time": 1.5},
                },
            },
            {
                "phase": "transformation",
                "config": "b50_c1",
                "total_time": 8.0,
                "function_stats": {
                    "func1": {"percentage": 40.0, "cumulative_time": 3.2},
                    "func3": {"percentage": 35.0, "cumulative_time": 2.8},
                },
            },
        ]

        # Call method
        result = self.optimizer.analyze_all_profiles()

        # Verify result
        self.assertEqual(len(result), 2)
        self.assertIn("extraction_b50_c1", result)
        self.assertIn("transformation_b50_c1", result)

        # Check that hotspots were stored correctly
        self.assertEqual(len(self.optimizer.hotspots), 2)
        self.assertIn("extraction", self.optimizer.hotspots)
        self.assertIn("transformation", self.optimizer.hotspots)
        self.assertIn("b50_c1", self.optimizer.hotspots["extraction"])
        self.assertIn("b50_c1", self.optimizer.hotspots["transformation"])

    def test_identify_common_hotspots(self):
        """Test identifying common hotspots across phases."""
        # Setup mock hotspots
        self.optimizer.hotspots = {
            "extraction": {
                "b50_c1": {
                    "function_stats": {
                        "func1": {"percentage": 50.0},
                        "func2": {"percentage": 30.0},
                    },
                },
            },
            "transformation": {
                "b50_c1": {
                    "function_stats": {
                        "func1": {"percentage": 40.0},
                        "func3": {"percentage": 35.0},
                    },
                },
            },
            "loading": {
                "b50_c1": {
                    "function_stats": {
                        "func2": {"percentage": 45.0},
                        "func3": {"percentage": 25.0},
                    },
                },
            },
        }

        # Call method
        result = self.optimizer.identify_common_hotspots()

        # Verify result
        self.assertEqual(len(result), 3)

        # func1 should be in extraction and transformation (90%)
        func1_entry = next((r for r in result if r[0] == "func1"), None)
        self.assertIsNotNone(func1_entry)
        self.assertAlmostEqual(func1_entry[1], 90.0)
        self.assertEqual(set(func1_entry[2]), {"extraction", "transformation"})

        # func2 should be in extraction and loading (75%)
        func2_entry = next((r for r in result if r[0] == "func2"), None)
        self.assertIsNotNone(func2_entry)
        self.assertAlmostEqual(func2_entry[1], 75.0)
        self.assertEqual(set(func2_entry[2]), {"extraction", "loading"})

        # func3 should be in transformation and loading (60%)
        func3_entry = next((r for r in result if r[0] == "func3"), None)
        self.assertIsNotNone(func3_entry)
        self.assertAlmostEqual(func3_entry[1], 60.0)
        self.assertEqual(set(func3_entry[2]), {"loading", "transformation"})

    def test_generate_recommendation_for_function(self):
        """Test generating recommendations for specific functions."""
        # Test batch strategies recommendation
        batch_func = "ztoq/batch_strategies.py:create_batches"
        batch_rec = self.optimizer._generate_recommendation_for_function(batch_func, ["extraction"])
        self.assertIn("Optimize batch creation logic", batch_rec)
        self.assertIn("pre-allocating arrays", batch_rec)

        # Test work queue recommendation
        queue_func = "ztoq/work_queue.py:process"
        queue_rec = self.optimizer._generate_recommendation_for_function(queue_func, ["extraction", "loading"])
        self.assertIn("Optimize the work queue processing", queue_rec)
        self.assertIn("synchronization overhead", queue_rec)

        # Test transformer recommendation
        transform_func = "ztoq/test_case_transformer.py:transform_test_case"
        transform_rec = self.optimizer._generate_recommendation_for_function(transform_func, ["transformation"])
        self.assertIn("Optimize transformation logic", transform_rec)
        self.assertIn("NumPy/Pandas", transform_rec)

        # Test database recommendation
        db_func = "ztoq/database_manager.py:get_entities"
        db_rec = self.optimizer._generate_recommendation_for_function(db_func, ["extraction", "transformation"])
        self.assertIn("Optimize database access", db_rec)
        self.assertIn("prepared statements", db_rec)

        # Test generic recommendation for unknown function
        unknown_func = "unknown_module.py:unknown_function"
        unknown_rec = self.optimizer._generate_recommendation_for_function(unknown_func, ["extraction"])
        self.assertIn("Profile this function more deeply", unknown_rec)

    @patch.object(CriticalPathOptimizer, "analyze_all_profiles")
    @patch.object(CriticalPathOptimizer, "generate_optimization_recommendations")
    @patch.object(CriticalPathOptimizer, "visualize_hotspots")
    @patch("builtins.open", new_callable=mock_open)
    def test_generate_optimization_report(self, mock_file, mock_viz, mock_rec, mock_analyze):
        """Test generating the optimization report."""
        # Setup mocks
        self.optimizer.hotspots = {
            "extraction": {"b50_c1": {}},
            "transformation": {"b50_c1": {}},
        }

        # Mock recommendations
        self.optimizer.optimization_recommendations = [
            {
                "function": "func1",
                "impact": 90.0,
                "phases": ["extraction", "transformation"],
                "recommendation": "Optimize this function",
                "priority": "high",
            },
            {
                "function": "func2",
                "impact": 15.0,
                "phases": ["loading"],
                "recommendation": "Consider optimizing this",
                "priority": "medium",
            },
        ]

        # Call method
        result = self.optimizer.generate_optimization_report()

        # Verify result
        self.assertTrue(result.endswith("critical_path_optimization_report.md"))

        # Verify file operations
        mock_file.assert_called()

        # Verify functions called
        mock_viz.assert_called_once()

        # Verify no redundant analysis if data already exists
        mock_analyze.assert_not_called()
        mock_rec.assert_not_called()

    def test_shorten_function_name(self):
        """Test shortening function names for display."""
        # Test with colon format
        colon_name = "very/long/module/path/to/file.py:method_name"
        short_colon = self.optimizer._shorten_function_name(colon_name)
        self.assertEqual(short_colon, "very/long/module/path/to/file.py: method_name")

        # Test with space format
        space_name = "very/long/module/path/to/file.py method_name"
        short_space = self.optimizer._shorten_function_name(space_name)
        self.assertEqual(short_space, "very/long/module/path/to/file.py: method_name")

        # Test with simple name (no separator)
        simple_name = "simple_function"
        short_simple = self.optimizer._shorten_function_name(simple_name)
        self.assertEqual(short_simple, "simple_function")

        # Test with very long name that needs truncation
        long_name = "extremely_long_function_name_that_needs_to_be_truncated_for_display_purposes"
        short_long = self.optimizer._shorten_function_name(long_name)
        self.assertEqual(short_long, "extremely_long_function_name_that_needs_to...")


@pytest.mark.unit
def test_critical_path_optimizer_initialization():
    """Test initialization of critical path optimizer."""
    with tempfile.TemporaryDirectory() as tmpdir:
        optimizer = CriticalPathOptimizer(output_dir=tmpdir)
        assert optimizer.output_dir == Path(tmpdir)
        assert optimizer.profile_data_dir is None
        assert optimizer.hotspots == {}


@pytest.mark.unit
def test_recommendation_generation():
    """Test recommendation generation logic."""
    optimizer = CriticalPathOptimizer()

    # Test batch strategies recommendation
    batch_rec = optimizer._generate_recommendation_for_function(
        "ztoq/batch_strategies.py:create_batches",
        ["extraction", "transformation"],
    )
    assert "pre-allocating arrays" in batch_rec

    # Test database recommendation
    db_rec = optimizer._generate_recommendation_for_function(
        "ztoq/database_manager.py:get_entities",
        ["extraction"],
    )
    assert "prepared statements" in db_rec
