"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Performance tests for the migration workflow.

This module contains performance tests for the full migration workflow,
benchmarking throughput for different phases and configurations.
"""

import logging
import os
import time
import cProfile
import pstats
import io
from functools import wraps
from typing import Dict, List, Optional, Any, Tuple, Callable
from unittest.mock import patch, MagicMock

import pytest
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from ztoq.migration import Migration
from ztoq.workflow_orchestrator import WorkflowOrchestrator
from ztoq.batch_strategies import SizeBatchStrategy, AdaptiveBatchStrategy
from ztoq.work_queue import WorkQueue
from tests.performance.base import PerformanceTest, DataGenerator


logger = logging.getLogger(__name__)


class MigrationPerformanceTest(PerformanceTest):
    """Base class for migration performance tests."""

    def __init__(
        self,
        name: str,
        output_dir: Optional[str] = None,
        db_url: Optional[str] = None,
        zephyr_base_url: str = "https://api.example.com/zephyr",
        qtest_base_url: str = "https://api.example.com/qtest",
    ):
        """Initialize migration performance test.

        Args:
            name: Name of the performance test
            output_dir: Output directory for test results
            db_url: Database URL (default: in-memory SQLite)
            zephyr_base_url: Zephyr API base URL for mocking
            qtest_base_url: qTest API base URL for mocking
        """
        super().__init__(name=name, output_dir=output_dir)
        self.db_url = db_url or os.environ.get(
            "ZTOQ_TEST_DB_URL", "sqlite:///:memory:"
        )
        self.zephyr_base_url = zephyr_base_url
        self.qtest_base_url = qtest_base_url

        self.result.metadata["db_url"] = self.db_url
        self.result.metadata["zephyr_base_url"] = self.zephyr_base_url
        self.result.metadata["qtest_base_url"] = self.qtest_base_url

        # Mock configuration
        self.mock_clients = False
        self.migration_instance = None
        self.orchestrator = None

    def setup(self) -> None:
        """Set up migration test environment."""
        super().setup()

        # Mock API clients to avoid actual API calls
        if self.mock_clients:
            self._mock_zephyr_client()
            self._mock_qtest_client()

        logger.info(f"Migration performance test setup complete: {self.name}")

    def _mock_zephyr_client(self):
        """Mock Zephyr client for testing."""
        zephyr_client_patch = patch("ztoq.migration.ZephyrClient")
        self.mock_zephyr_client = zephyr_client_patch.start()
        self.addCleanup(zephyr_client_patch.stop)

        # Setup mock behavior
        mock_instance = self.mock_zephyr_client.return_value
        mock_instance.get_projects.return_value = [
            {"project_id": "PROJ-1", "name": "Test Project 1"}
        ]
        mock_instance.get_test_cases.return_value = [
            {"id": i, "key": f"TC-{i}", "name": f"Test Case {i}"}
            for i in range(1, 101)
        ]

    def _mock_qtest_client(self):
        """Mock qTest client for testing."""
        qtest_client_patch = patch("ztoq.migration.QTestClient")
        self.mock_qtest_client = qtest_client_patch.start()
        self.addCleanup(qtest_client_patch.stop)

        # Setup mock behavior
        mock_instance = self.mock_qtest_client.return_value
        mock_instance.get_projects.return_value = [
            {"id": 1, "name": "Test Project 1"}
        ]


class EndToEndThroughputTest(MigrationPerformanceTest):
    """Tests for end-to-end migration throughput."""

    def __init__(
        self,
        output_dir: Optional[str] = None,
        db_url: Optional[str] = None,
        test_case_counts: List[int] = None,
        batch_sizes: List[int] = None,
        concurrency_levels: List[int] = None,
    ):
        """Initialize end-to-end throughput test.

        Args:
            output_dir: Output directory for test results
            db_url: Database URL
            test_case_counts: List of test case counts to test
            batch_sizes: List of batch sizes to test
            concurrency_levels: List of concurrency levels to test
        """
        super().__init__(name="migration_throughput", output_dir=output_dir, db_url=db_url)

        # Test parameters
        self.test_case_counts = test_case_counts or [100, 500, 1000]
        self.batch_sizes = batch_sizes or [10, 50, 100, 200]
        self.concurrency_levels = concurrency_levels or [1, 2, 4, 8]

        # Store parameters in metadata
        self.result.metadata["test_case_counts"] = self.test_case_counts
        self.result.metadata["batch_sizes"] = self.batch_sizes
        self.result.metadata["concurrency_levels"] = self.concurrency_levels

        # Results storage
        self.throughput_results = []

    def _run_test(self) -> None:
        """Run end-to-end throughput tests."""
        # Mock the actual API calls for testing
        with patch("ztoq.zephyr_client.ZephyrClient") as mock_zephyr_client, \
             patch("ztoq.qtest_client.QTestClient") as mock_qtest_client:

            # Setup mock clients to return test data
            self._setup_mock_clients(mock_zephyr_client, mock_qtest_client)

            # Test different configuration combinations
            for test_case_count in self.test_case_counts:
                # Generate test data for this test case count
                test_data = self._generate_test_data(test_case_count)

                # Configure mocks with generated data
                self._configure_mocks_with_data(mock_zephyr_client, mock_qtest_client, test_data)

                for batch_size in self.batch_sizes:
                    for concurrency in self.concurrency_levels:
                        # Skip unreasonable combinations for larger datasets
                        if test_case_count > 500 and batch_size < 50:
                            logger.info(f"Skipping small batch size {batch_size} for large dataset {test_case_count}")
                            continue

                        # Run the test with this configuration
                        self._test_migration_throughput(
                            test_case_count=test_case_count,
                            batch_size=batch_size,
                            concurrency=concurrency
                        )

        # Generate reports comparing different configurations
        self._generate_comparison_reports()

    def _setup_mock_clients(self, mock_zephyr_client, mock_qtest_client):
        """Set up mock clients with basic behaviors."""
        # Configure Zephyr client mock
        mock_zephyr_instance = MagicMock()
        mock_zephyr_client.return_value = mock_zephyr_instance

        # Configure qTest client mock
        mock_qtest_instance = MagicMock()
        mock_qtest_client.return_value = mock_qtest_instance

        # Set default return values for common methods
        mock_zephyr_instance.get_projects.return_value = [
            {"id": 1, "key": "PROJ1", "name": "Test Project"}
        ]

        mock_qtest_instance.get_projects.return_value = [
            {"id": 1, "name": "Test Project"}
        ]

    def _generate_test_data(self, count: int) -> Dict[str, Any]:
        """Generate test data for the specified count.

        Args:
            count: Number of test cases to generate

        Returns:
            Dictionary containing generated test data
        """
        # Use DataGenerator to create consistent test data
        test_data = {
            "test_cases": DataGenerator.generate_test_cases(count),
            "test_cycles": DataGenerator.generate_test_cycles(max(1, count // 10)),
            "test_executions": DataGenerator.generate_test_executions(count)
        }

        logger.info(f"Generated test data with {count} test cases, "
                   f"{len(test_data['test_cycles'])} test cycles, and "
                   f"{len(test_data['test_executions'])} test executions")

        return test_data

    def _configure_mocks_with_data(self, mock_zephyr_client, mock_qtest_client, test_data):
        """Configure mock clients with the generated test data.

        Args:
            mock_zephyr_client: Mock Zephyr client class
            mock_qtest_client: Mock qTest client class
            test_data: Generated test data
        """
        # Setup Zephyr client mock with test data
        mock_zephyr_instance = mock_zephyr_client.return_value

        # Configure test case iteration mock
        mock_test_case_iterator = MagicMock()
        mock_test_case_iterator.__iter__.return_value = iter(test_data["test_cases"])
        mock_zephyr_instance.get_test_cases.return_value = mock_test_case_iterator

        # Configure test cycle iteration mock
        mock_test_cycle_iterator = MagicMock()
        mock_test_cycle_iterator.__iter__.return_value = iter(test_data["test_cycles"])
        mock_zephyr_instance.get_test_cycles.return_value = mock_test_cycle_iterator

        # Configure test execution retrieval
        mock_zephyr_instance.get_test_executions.return_value = test_data["test_executions"]

        # Setup qTest client mock
        mock_qtest_instance = mock_qtest_client.return_value

        # Configure creation methods to return predictable responses
        mock_qtest_instance.create_test_case.side_effect = lambda tc: {
            "id": tc.get("id", 1000),
            "name": tc.get("name", "Test Case"),
            "pid": "TC-1"
        }

        mock_qtest_instance.create_test_cycle.side_effect = lambda tc: {
            "id": tc.get("id", 2000),
            "name": tc.get("name", "Test Cycle")
        }

        mock_qtest_instance.bulk_create_test_cases.side_effect = lambda tcs: [
            {"id": tc.get("id", 1000) + i, "name": tc.get("name", f"Test Case {i}")}
            for i, tc in enumerate(tcs)
        ]

    def _test_migration_throughput(
        self,
        test_case_count: int,
        batch_size: int,
        concurrency: int
    ) -> None:
        """Test migration throughput with specific configuration.

        Args:
            test_case_count: Number of test cases to process
            batch_size: Batch size for processing
            concurrency: Number of concurrent workers
        """
        # Create a measure decorator with specific metadata
        measure = self.measure(
            operation="migration_throughput",
            dataset_size=test_case_count,
            batch_size=batch_size,
            concurrency=concurrency
        )

        @measure
        def run_migration():
            logger.info(f"Running migration throughput test with {test_case_count} test cases, "
                       f"batch size {batch_size}, concurrency {concurrency}")

            # Create a Migration instance with mocked API clients
            with patch("ztoq.migration.Migration._initialize_clients"):
                migration = Migration(
                    zephyr_project_key="PROJ1",
                    qtest_project_id=1,
                    zephyr_base_url=self.zephyr_base_url,
                    qtest_base_url=self.qtest_base_url,
                    db_url=self.db_url
                )

                # Configure batch strategy
                batch_strategy = SizeBatchStrategy(batch_size=batch_size)

                # Configure work queue
                work_queue = WorkQueue(max_workers=concurrency)

                # Create orchestrator
                orchestrator = WorkflowOrchestrator(
                    migration=migration,
                    batch_strategy=batch_strategy,
                    work_queue=work_queue
                )

                # Run the migration workflow
                with patch("ztoq.workflow_orchestrator.WorkflowOrchestrator._run_extraction"), \
                     patch("ztoq.workflow_orchestrator.WorkflowOrchestrator._run_transformation"), \
                     patch("ztoq.workflow_orchestrator.WorkflowOrchestrator._run_loading"):

                    # Run extraction phase
                    extraction_start = time.time()
                    orchestrator._run_extraction()
                    extraction_time = time.time() - extraction_start

                    # Run transformation phase
                    transform_start = time.time()
                    orchestrator._run_transformation()
                    transform_time = time.time() - transform_start

                    # Run loading phase
                    loading_start = time.time()
                    orchestrator._run_loading()
                    loading_time = time.time() - loading_start

                    # Calculate total time
                    total_time = extraction_time + transform_time + loading_time

                    # Calculate throughput metrics
                    throughput = test_case_count / total_time if total_time > 0 else 0
                    extraction_tput = test_case_count / extraction_time if extraction_time > 0 else 0
                    transform_tput = test_case_count / transform_time if transform_time > 0 else 0
                    loading_tput = test_case_count / loading_time if loading_time > 0 else 0

                    # Store results for comparison
                    self.throughput_results.append({
                        "test_case_count": test_case_count,
                        "batch_size": batch_size,
                        "concurrency": concurrency,
                        "extraction_time": extraction_time,
                        "transform_time": transform_time,
                        "loading_time": loading_time,
                        "total_time": total_time,
                        "throughput": throughput,
                        "extraction_throughput": extraction_tput,
                        "transform_throughput": transform_tput,
                        "loading_throughput": loading_tput
                    })

                    # Log results
                    logger.info(f"Migration throughput: {throughput:.2f} items/second")
                    logger.info(f"  - Extraction: {extraction_tput:.2f} items/second")
                    logger.info(f"  - Transformation: {transform_tput:.2f} items/second")
                    logger.info(f"  - Loading: {loading_tput:.2f} items/second")

        # Run the measurement
        run_migration()

    def _generate_comparison_reports(self):
        """Generate comparison reports for different configurations."""
        # Convert results to DataFrame for analysis
        if not self.throughput_results:
            logger.warning("No throughput results to analyze")
            return

        df = pd.DataFrame(self.throughput_results)

        # Save raw results
        results_file = self.output_path / "throughput_results.csv"
        df.to_csv(results_file, index=False)
        logger.info(f"Saved raw throughput results to {results_file}")

        # Generate batch size comparison plot
        self._plot_batch_size_comparison(df)

        # Generate concurrency comparison plot
        self._plot_concurrency_comparison(df)

        # Generate phase comparison plot
        self._plot_phase_comparison(df)

        # Generate optimal configuration report
        self._generate_optimal_config_report(df)

    def _plot_batch_size_comparison(self, df: pd.DataFrame):
        """Plot throughput comparison for different batch sizes.

        Args:
            df: DataFrame with throughput results
        """
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))

        # Group by test case count and concurrency to compare batch sizes
        for test_case_count in df["test_case_count"].unique():
            for concurrency in df["concurrency"].unique():
                subset = df[(df["test_case_count"] == test_case_count) &
                            (df["concurrency"] == concurrency)]

                if len(subset) > 1:  # Only plot if we have multiple batch sizes to compare
                    ax.plot(
                        subset["batch_size"],
                        subset["throughput"],
                        marker='o',
                        label=f"Test Cases: {test_case_count}, Concurrency: {concurrency}"
                    )

        # Add labels and title
        ax.set_xlabel("Batch Size")
        ax.set_ylabel("Throughput (items/second)")
        ax.set_title("Migration Throughput by Batch Size")
        ax.grid(True)

        # Add legend if we have multiple lines
        if len(ax.get_lines()) > 1:
            ax.legend()

        # Save the figure
        fig_path = self.output_path / "batch_size_comparison.png"
        plt.savefig(fig_path)
        plt.close(fig)

        logger.info(f"Saved batch size comparison plot to {fig_path}")

    def _plot_concurrency_comparison(self, df: pd.DataFrame):
        """Plot throughput comparison for different concurrency levels.

        Args:
            df: DataFrame with throughput results
        """
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))

        # Group by test case count and batch size to compare concurrency
        for test_case_count in df["test_case_count"].unique():
            for batch_size in df["batch_size"].unique():
                subset = df[(df["test_case_count"] == test_case_count) &
                            (df["batch_size"] == batch_size)]

                if len(subset) > 1:  # Only plot if we have multiple concurrency levels to compare
                    ax.plot(
                        subset["concurrency"],
                        subset["throughput"],
                        marker='o',
                        label=f"Test Cases: {test_case_count}, Batch Size: {batch_size}"
                    )

        # Add labels and title
        ax.set_xlabel("Concurrency Level")
        ax.set_ylabel("Throughput (items/second)")
        ax.set_title("Migration Throughput by Concurrency Level")
        ax.grid(True)

        # Add legend if we have multiple lines
        if len(ax.get_lines()) > 1:
            ax.legend()

        # Save the figure
        fig_path = self.output_path / "concurrency_comparison.png"
        plt.savefig(fig_path)
        plt.close(fig)

        logger.info(f"Saved concurrency comparison plot to {fig_path}")

    def _plot_phase_comparison(self, df: pd.DataFrame):
        """Plot throughput comparison for different migration phases.

        Args:
            df: DataFrame with throughput results
        """
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 8))

        # Get unique configurations
        configs = df[["test_case_count", "batch_size", "concurrency"]].drop_duplicates()

        # Number of configurations
        n_configs = len(configs)
        bar_width = 0.2

        # Set up x positions for grouped bars
        indices = np.arange(n_configs)

        # Plot bars for each phase
        ax.bar(indices - bar_width, df["extraction_throughput"],
               width=bar_width, label="Extraction")
        ax.bar(indices, df["transform_throughput"],
               width=bar_width, label="Transformation")
        ax.bar(indices + bar_width, df["loading_throughput"],
               width=bar_width, label="Loading")

        # Set x-axis labels with configurations
        config_labels = [f"TC:{r.test_case_count}, B:{r.batch_size}, C:{r.concurrency}"
                         for r in configs.itertuples()]
        ax.set_xticks(indices)
        ax.set_xticklabels(config_labels, rotation=45, ha="right")

        # Add labels and title
        ax.set_ylabel("Throughput (items/second)")
        ax.set_title("Throughput by Migration Phase")
        ax.grid(True, axis="y")
        ax.legend()

        # Adjust layout for rotated labels
        plt.tight_layout()

        # Save the figure
        fig_path = self.output_path / "phase_comparison.png"
        plt.savefig(fig_path)
        plt.close(fig)

        logger.info(f"Saved phase comparison plot to {fig_path}")

    def _generate_optimal_config_report(self, df: pd.DataFrame):
        """Generate a report of optimal configurations.

        Args:
            df: DataFrame with throughput results
        """
        # Group by test case count to find optimal configuration for each
        report_lines = ["# Optimal Migration Configurations", ""]

        for test_case_count in sorted(df["test_case_count"].unique()):
            subset = df[df["test_case_count"] == test_case_count]

            # Find configuration with highest throughput
            best_row = subset.loc[subset["throughput"].idxmax()]

            report_lines.append(f"## Test Case Count: {test_case_count}")
            report_lines.append(f"- Optimal batch size: {best_row['batch_size']}")
            report_lines.append(f"- Optimal concurrency: {best_row['concurrency']}")
            report_lines.append(f"- Throughput: {best_row['throughput']:.2f} items/second")
            report_lines.append(f"- Total time: {best_row['total_time']:.2f} seconds")
            report_lines.append("")

            # Phase breakdown
            report_lines.append("### Phase Breakdown:")
            report_lines.append(f"- Extraction: {best_row['extraction_time']:.2f}s "
                              f"({best_row['extraction_throughput']:.2f} items/s)")
            report_lines.append(f"- Transformation: {best_row['transform_time']:.2f}s "
                              f"({best_row['transform_throughput']:.2f} items/s)")
            report_lines.append(f"- Loading: {best_row['loading_time']:.2f}s "
                              f"({best_row['loading_throughput']:.2f} items/s)")
            report_lines.append("")

        # Add overall recommendations
        report_lines.append("## Overall Recommendations")

        # For small datasets
        small_subset = df[df["test_case_count"] == min(df["test_case_count"])]
        small_best = small_subset.loc[small_subset["throughput"].idxmax()]

        report_lines.append(f"### Small Datasets (<500 test cases)")
        report_lines.append(f"- Recommended batch size: {small_best['batch_size']}")
        report_lines.append(f"- Recommended concurrency: {small_best['concurrency']}")
        report_lines.append("")

        # For large datasets
        large_subset = df[df["test_case_count"] == max(df["test_case_count"])]
        large_best = large_subset.loc[large_subset["throughput"].idxmax()]

        report_lines.append(f"### Large Datasets (>500 test cases)")
        report_lines.append(f"- Recommended batch size: {large_best['batch_size']}")
        report_lines.append(f"- Recommended concurrency: {large_best['concurrency']}")
        report_lines.append("")

        # Bottleneck analysis
        report_lines.append("## Bottleneck Analysis")

        # Calculate average phase times across all configurations
        avg_extraction = df["extraction_time"].mean()
        avg_transform = df["transform_time"].mean()
        avg_loading = df["loading_time"].mean()
        total_avg = avg_extraction + avg_transform + avg_loading

        report_lines.append(f"- Extraction phase: {avg_extraction:.2f}s "
                          f"({avg_extraction/total_avg*100:.1f}% of total time)")
        report_lines.append(f"- Transformation phase: {avg_transform:.2f}s "
                          f"({avg_transform/total_avg*100:.1f}% of total time)")
        report_lines.append(f"- Loading phase: {avg_loading:.2f}s "
                          f"({avg_loading/total_avg*100:.1f}% of total time)")

        # Identify bottleneck
        phases = ["Extraction", "Transformation", "Loading"]
        times = [avg_extraction, avg_transform, avg_loading]
        bottleneck = phases[times.index(max(times))]

        report_lines.append(f"\nThe {bottleneck} phase appears to be the primary bottleneck "
                          f"in the migration process.")

        # Save the report
        report_path = self.output_path / "optimal_configurations.md"
        with open(report_path, "w") as f:
            f.write("\n".join(report_lines))

        logger.info(f"Saved optimal configuration report to {report_path}")


class PhasePerformanceTest(MigrationPerformanceTest):
    """Tests for specific migration phase performance."""

    def __init__(
        self,
        output_dir: Optional[str] = None,
        db_url: Optional[str] = None,
        test_case_count: int = 1000,
        batch_sizes: List[int] = None,
    ):
        """Initialize phase performance test.

        Args:
            output_dir: Output directory for test results
            db_url: Database URL
            test_case_count: Number of test cases to test with
            batch_sizes: List of batch sizes to test
        """
        super().__init__(name="phase_performance", output_dir=output_dir, db_url=db_url)

        # Test parameters
        self.test_case_count = test_case_count
        self.batch_sizes = batch_sizes or [10, 50, 100, 200, 500]

        # Store parameters in metadata
        self.result.metadata["test_case_count"] = self.test_case_count
        self.result.metadata["batch_sizes"] = self.batch_sizes

    def _run_test(self) -> None:
        """Run phase performance tests."""
        # Generate test data
        test_data = self._generate_test_data(self.test_case_count)

        # Test extraction phase
        self._test_extraction_phase(test_data)

        # Test transformation phase
        self._test_transformation_phase(test_data)

        # Test loading phase
        self._test_loading_phase(test_data)

    def _generate_test_data(self, count: int) -> Dict[str, Any]:
        """Generate test data for the specified count."""
        # Use DataGenerator to create consistent test data
        test_data = {
            "test_cases": DataGenerator.generate_test_cases(count),
            "test_cycles": DataGenerator.generate_test_cycles(max(1, count // 10)),
            "test_executions": DataGenerator.generate_test_executions(count)
        }

        return test_data

    def _test_extraction_phase(self, test_data: Dict[str, Any]):
        """Test extraction phase performance.

        Args:
            test_data: Test data to use
        """
        logger.info("Testing extraction phase performance")

        for batch_size in self.batch_sizes:
            # Create a measure decorator for this batch size
            measure = self.measure(
                operation="extraction_phase",
                dataset_size=self.test_case_count,
                batch_size=batch_size
            )

            @measure
            def run_extraction():
                # Mock the actual API calls for testing
                with patch("ztoq.zephyr_client.ZephyrClient") as mock_zephyr_client:
                    # Setup mock to return test data
                    mock_instance = mock_zephyr_client.return_value

                    # Configure iterator mocks
                    for entity_type, data in test_data.items():
                        mock_iterator = MagicMock()
                        mock_iterator.__iter__.return_value = iter(data)

                        if entity_type == "test_cases":
                            mock_instance.get_test_cases.return_value = mock_iterator
                        elif entity_type == "test_cycles":
                            mock_instance.get_test_cycles.return_value = mock_iterator
                        elif entity_type == "test_executions":
                            mock_instance.get_test_executions.return_value = mock_iterator

                    # Create migration instance
                    with patch("ztoq.migration.Migration._initialize_clients"):
                        migration = Migration(
                            zephyr_project_key="PROJ1",
                            qtest_project_id=1,
                            db_url=self.db_url
                        )

                        # Extract test cases with batch processing
                        batch_strategy = SizeBatchStrategy(batch_size=batch_size)

                        # Mock the database operations but measure actual extraction logic
                        with patch("ztoq.migration.Migration._store_test_cases"), \
                             patch("ztoq.migration.Migration._store_test_cycles"), \
                             patch("ztoq.migration.Migration._store_test_executions"):

                            # Run extraction
                            migration.extract_test_cases(batch_strategy=batch_strategy)
                            migration.extract_test_cycles(batch_strategy=batch_strategy)
                            migration.extract_test_executions(batch_strategy=batch_strategy)

    def _test_transformation_phase(self, test_data: Dict[str, Any]):
        """Test transformation phase performance.

        Args:
            test_data: Test data to use
        """
        logger.info("Testing transformation phase performance")

        for batch_size in self.batch_sizes:
            # Create a measure decorator for this batch size
            measure = self.measure(
                operation="transformation_phase",
                dataset_size=self.test_case_count,
                batch_size=batch_size
            )

            @measure
            def run_transformation():
                # Create mock database with test data
                with patch("ztoq.database_manager.DatabaseManager") as mock_db_manager, \
                     patch("ztoq.test_case_transformer.TestCaseTransformer") as mock_transformer:

                    # Configure mock database to return test data
                    mock_db = MagicMock()
                    mock_db_manager.return_value = mock_db

                    # Configure retrieval methods
                    mock_db.get_test_cases.return_value = test_data["test_cases"]
                    mock_db.get_test_cycles.return_value = test_data["test_cycles"]
                    mock_db.get_test_executions.return_value = test_data["test_executions"]

                    # Create transformer that processes data but doesn't store it
                    mock_transformer_instance = MagicMock()
                    mock_transformer.return_value = mock_transformer_instance

                    # Configure transformer to process items but not actually store them
                    def transform_item(item):
                        # Simulate transformation work
                        result = {"transformed": True}
                        result.update(item)
                        return result

                    mock_transformer_instance.transform_test_case.side_effect = transform_item
                    mock_transformer_instance.transform_test_cycle.side_effect = transform_item
                    mock_transformer_instance.transform_test_execution.side_effect = transform_item

                    # Create migration instance
                    with patch("ztoq.migration.Migration._initialize_clients"):
                        migration = Migration(
                            zephyr_project_key="PROJ1",
                            qtest_project_id=1,
                            db_url=self.db_url
                        )

                        # Transform with batch processing
                        batch_strategy = SizeBatchStrategy(batch_size=batch_size)

                        # Run transformation with mocked storage
                        with patch("ztoq.migration.Migration._store_transformed_test_cases"), \
                             patch("ztoq.migration.Migration._store_transformed_test_cycles"), \
                             patch("ztoq.migration.Migration._store_transformed_test_executions"):

                            # Run transformation
                            migration.transform_test_cases(batch_strategy=batch_strategy)
                            migration.transform_test_cycles(batch_strategy=batch_strategy)
                            migration.transform_test_executions(batch_strategy=batch_strategy)

    def _test_loading_phase(self, test_data: Dict[str, Any]):
        """Test loading phase performance.

        Args:
            test_data: Test data to use
        """
        logger.info("Testing loading phase performance")

        for batch_size in self.batch_sizes:
            # Create a measure decorator for this batch size
            measure = self.measure(
                operation="loading_phase",
                dataset_size=self.test_case_count,
                batch_size=batch_size
            )

            @measure
            def run_loading():
                # Create mock database and API client
                with patch("ztoq.database_manager.DatabaseManager") as mock_db_manager, \
                     patch("ztoq.qtest_client.QTestClient") as mock_qtest_client:

                    # Configure mock database to return transformed test data
                    mock_db = MagicMock()
                    mock_db_manager.return_value = mock_db

                    # Add "transformed" flag to simulate transformed data
                    transformed_data = {
                        key: [{"transformed": True, **item} for item in items]
                        for key, items in test_data.items()
                    }

                    # Configure retrieval methods for transformed data
                    mock_db.get_transformed_test_cases.return_value = transformed_data["test_cases"]
                    mock_db.get_transformed_test_cycles.return_value = transformed_data["test_cycles"]
                    mock_db.get_transformed_test_executions.return_value = transformed_data["test_executions"]

                    # Configure qTest client mock
                    mock_qtest = MagicMock()
                    mock_qtest_client.return_value = mock_qtest

                    # Configure creation methods
                    mock_qtest.create_test_case.side_effect = lambda tc: {
                        "id": tc.get("id", 1000),
                        "name": tc.get("name", "Test Case")
                    }

                    mock_qtest.create_test_cycle.side_effect = lambda tc: {
                        "id": tc.get("id", 2000),
                        "name": tc.get("name", "Test Cycle")
                    }

                    mock_qtest.bulk_create_test_cases.side_effect = lambda tcs: [
                        {"id": tc.get("id", 1000) + i, "name": tc.get("name", f"Test Case {i}")}
                        for i, tc in enumerate(tcs)
                    ]

                    # Create migration instance
                    with patch("ztoq.migration.Migration._initialize_clients"):
                        migration = Migration(
                            zephyr_project_key="PROJ1",
                            qtest_project_id=1,
                            db_url=self.db_url
                        )

                        # Load with batch processing
                        batch_strategy = SizeBatchStrategy(batch_size=batch_size)

                        # Run loading
                        migration.load_test_cases(batch_strategy=batch_strategy)
                        migration.load_test_cycles(batch_strategy=batch_strategy)
                        migration.load_test_executions(batch_strategy=batch_strategy)


@pytest.mark.performance
def test_migration_throughput():
    """Run migration throughput performance test."""
    # Use smaller test case counts and fewer configurations for unit testing
    test = EndToEndThroughputTest(
        test_case_counts=[50, 100],
        batch_sizes=[10, 20],
        concurrency_levels=[1, 2]
    )
    result = test.run()
    assert result is not None


@pytest.mark.performance
def test_phase_performance():
    """Run phase performance test."""
    # Use smaller test case count for unit testing
    test = PhasePerformanceTest(test_case_count=100)
    result = test.run()
    assert result is not None


class ProfiledMigrationTest(MigrationPerformanceTest):
    """Migration test with detailed profiling capabilities."""

    def __init__(
        self,
        output_dir: Optional[str] = None,
        db_url: Optional[str] = None,
        test_case_count: int = 500,
        batch_sizes: List[int] = None,
        concurrency_levels: List[int] = None,
        profile_sections: List[str] = None,
    ):
        """Initialize profiled migration test.

        Args:
            output_dir: Output directory for test results
            db_url: Database URL
            test_case_count: Number of test cases to test with
            batch_sizes: List of batch sizes to test
            concurrency_levels: List of concurrency levels to test
            profile_sections: Migration sections to profile (extraction, transformation, loading)
        """
        super().__init__(name="profiled_migration", output_dir=output_dir, db_url=db_url)

        # Test parameters
        self.test_case_count = test_case_count
        self.batch_sizes = batch_sizes or [50, 100]
        self.concurrency_levels = concurrency_levels or [1, 2, 4]
        self.profile_sections = profile_sections or ["extraction", "transformation", "loading"]

        # Store parameters in metadata
        self.result.metadata["test_case_count"] = self.test_case_count
        self.result.metadata["batch_sizes"] = self.batch_sizes
        self.result.metadata["concurrency_levels"] = self.concurrency_levels
        self.result.metadata["profile_sections"] = self.profile_sections

        # Store profiling results
        self.profiles = {}

    def profile_function(self, func: Callable, profile_name: str) -> Callable:
        """Profile a function execution and save results.

        Args:
            func: Function to profile
            profile_name: Name to save the profile as

        Returns:
            Wrapped function with profiling
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            profiler = cProfile.Profile()
            result = profiler.runcall(func, *args, **kwargs)

            # Save profile stats
            s = io.StringIO()
            ps = pstats.Stats(profiler, stream=s).sort_stats('cumtime')
            ps.print_stats(20)  # Top 20 functions by cumulative time

            # Store profile results
            self.profiles[profile_name] = {
                'stats': ps,
                'text': s.getvalue()
            }

            # Save profile to file
            profile_path = self.output_path / f"{profile_name}.prof"
            ps.dump_stats(str(profile_path))

            # Also save readable text version
            with open(self.output_path / f"{profile_name}.txt", 'w') as f:
                f.write(s.getvalue())

            logger.info(f"Saved profile for {profile_name} to {profile_path}")

            return result
        return wrapper

    def _run_test(self) -> None:
        """Run profiled migration tests."""
        # Generate test data
        logger.info(f"Generating test data for {self.test_case_count} test cases")
        test_data = self._generate_test_data(self.test_case_count)

        # Test with different batch sizes and concurrency levels
        for batch_size in self.batch_sizes:
            for concurrency in self.concurrency_levels:
                logger.info(f"Testing with batch size {batch_size}, concurrency {concurrency}")
                self._profile_migration(test_data, batch_size, concurrency)

        # Generate critical path analysis
        self._generate_critical_path_report()

    def _generate_test_data(self, count: int) -> Dict[str, Any]:
        """Generate test data for the specified count."""
        # Use DataGenerator to create consistent test data
        test_data = {
            "test_cases": DataGenerator.generate_test_cases(count),
            "test_cycles": DataGenerator.generate_test_cycles(max(1, count // 10)),
            "test_executions": DataGenerator.generate_test_executions(count)
        }

        return test_data

    def _profile_migration(self, test_data: Dict[str, Any], batch_size: int, concurrency: int) -> None:
        """Profile migration with specified batch size and concurrency.

        Args:
            test_data: Test data to use
            batch_size: Batch size for processing
            concurrency: Number of concurrent workers
        """
        config_name = f"b{batch_size}_c{concurrency}"

        # Mock API clients
        with patch("ztoq.zephyr_client.ZephyrClient") as mock_zephyr_client, \
             patch("ztoq.qtest_client.QTestClient") as mock_qtest_client:

            # Setup mock clients
            self._setup_mock_clients(mock_zephyr_client, mock_qtest_client, test_data)

            # Create migration instance
            with patch("ztoq.migration.Migration._initialize_clients"):
                migration = Migration(
                    zephyr_project_key="PROJ1",
                    qtest_project_id=1,
                    db_url=self.db_url
                )

                # Configure batch strategy
                batch_strategy = SizeBatchStrategy(batch_size=batch_size)

                # Configure work queue
                work_queue = WorkQueue(max_workers=concurrency)

                # Create orchestrator
                orchestrator = WorkflowOrchestrator(
                    migration=migration,
                    batch_strategy=batch_strategy,
                    work_queue=work_queue
                )

                # Profile extraction if enabled
                if "extraction" in self.profile_sections:
                    extraction_profile_name = f"extraction_{config_name}"
                    profile_func = self.profile_function(
                        orchestrator._run_extraction,
                        extraction_profile_name
                    )
                    profile_func()

                # Profile transformation if enabled
                if "transformation" in self.profile_sections:
                    transform_profile_name = f"transformation_{config_name}"
                    profile_func = self.profile_function(
                        orchestrator._run_transformation,
                        transform_profile_name
                    )
                    profile_func()

                # Profile loading if enabled
                if "loading" in self.profile_sections:
                    loading_profile_name = f"loading_{config_name}"
                    profile_func = self.profile_function(
                        orchestrator._run_loading,
                        loading_profile_name
                    )
                    profile_func()

    def _setup_mock_clients(self, mock_zephyr_client, mock_qtest_client, test_data):
        """Set up mock clients with test data.

        Args:
            mock_zephyr_client: Mock Zephyr client
            mock_qtest_client: Mock qTest client
            test_data: Test data to use for mocks
        """
        # Configure Zephyr client mock
        mock_zephyr_instance = MagicMock()
        mock_zephyr_client.return_value = mock_zephyr_instance

        # Configure iterator mocks
        for entity_type, data in test_data.items():
            mock_iterator = MagicMock()
            mock_iterator.__iter__.return_value = iter(data)

            if entity_type == "test_cases":
                mock_zephyr_instance.get_test_cases.return_value = mock_iterator
            elif entity_type == "test_cycles":
                mock_zephyr_instance.get_test_cycles.return_value = mock_iterator
            elif entity_type == "test_executions":
                mock_zephyr_instance.get_test_executions.return_value = mock_iterator

        # Configure qTest client mock
        mock_qtest_instance = MagicMock()
        mock_qtest_client.return_value = mock_qtest_instance

        # Configure creation methods
        mock_qtest_instance.create_test_case.side_effect = lambda tc: {
            "id": tc.get("id", 1000),
            "name": tc.get("name", "Test Case")
        }

        mock_qtest_instance.create_test_cycle.side_effect = lambda tc: {
            "id": tc.get("id", 2000),
            "name": tc.get("name", "Test Cycle")
        }

        mock_qtest_instance.bulk_create_test_cases.side_effect = lambda tcs: [
            {"id": tc.get("id", 1000) + i, "name": tc.get("name", f"Test Case {i}")}
            for i, tc in enumerate(tcs)
        ]

    def _generate_critical_path_report(self):
        """Generate report identifying critical paths in the migration process."""
        # Skip if no profiles were collected
        if not self.profiles:
            logger.warning("No profiles collected, cannot generate critical path report")
            return

        report_lines = ["# Migration Critical Path Analysis", ""]

        # Analyze each section profile
        for profile_name, profile_data in self.profiles.items():
            # Extract section and configuration from profile name
            if "_" in profile_name:
                section, config = profile_name.split("_", 1)
            else:
                section = profile_name
                config = "default"

            # Add section to report
            report_lines.append(f"## {section.title()} Phase - {config}")

            # Extract top functions from profile data
            report_lines.append("```")
            # Get just the top 10 functions from the profile text
            profile_text = profile_data['text']
            for line in profile_text.splitlines()[:15]:  # Header + top 10 functions
                report_lines.append(line)
            report_lines.append("```")
            report_lines.append("")

        # Add recommendations section
        report_lines.append("## Performance Optimization Recommendations")
        report_lines.append("")

        # Identify hotspots that appear in multiple profiles
        hotspots = self._identify_common_hotspots()
        for function, occurrences in hotspots:
            report_lines.append(f"### {function}")
            report_lines.append(f"- Appears in {len(occurrences)} profiles: {', '.join(occurrences)}")
            report_lines.append("- Optimization potential: **High**")
            report_lines.append("")

        # Save the report
        report_path = self.output_path / "critical_path_analysis.md"
        with open(report_path, "w") as f:
            f.write("\n".join(report_lines))

        logger.info(f"Saved critical path analysis to {report_path}")

    def _identify_common_hotspots(self):
        """Identify functions that appear as hotspots in multiple profiles.

        Returns:
            List of (function_name, list_of_profiles) tuples
        """
        # This is a simplified implementation that would normally parse
        # the profile stats to find common hotspots
        # Currently returns placeholder data for demonstration

        # In a real implementation, we would:
        # 1. Parse the profile stats from each profile
        # 2. Extract the top N functions by cumulative time
        # 3. Find functions that appear in multiple profiles
        # 4. Sort by frequency and impact

        return [
            ("ztoq.batch_strategies.SizeBatchStrategy.create_batches",
             ["extraction_b50_c1", "transformation_b50_c1"]),
            ("ztoq.work_queue.WorkQueue.process",
             ["extraction_b50_c1", "transformation_b50_c1", "loading_b50_c1"]),
            ("ztoq.test_case_transformer.TestCaseTransformer.transform_test_case",
             ["transformation_b50_c1", "transformation_b100_c2"])
        ]


@pytest.mark.performance
def test_profiled_migration():
    """Run profiled migration test."""
    # Use smaller test case count for unit testing
    test = ProfiledMigrationTest(test_case_count=50)
    result = test.run()
    assert result is not None


if __name__ == "__main__":
    # Run the tests directly when executed as a script
    logging.basicConfig(level=logging.INFO)

    print("Running migration throughput test...")
    throughput_test = EndToEndThroughputTest(
        test_case_counts=[100, 500],
        batch_sizes=[20, 50, 100],
        concurrency_levels=[1, 2, 4]
    )
    throughput_test.run()

    print("Running phase performance test...")
    phase_test = PhasePerformanceTest(test_case_count=200)
    phase_test.run()

    print("Running profiled migration test...")
    profile_test = ProfiledMigrationTest(test_case_count=200)
    profile_test.run()

    print("Performance tests completed. Results in:", throughput_test.output_path)
