"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Base classes and utilities for performance testing.

This module provides the foundation for performance tests in ZTOQ, including
utilities for measuring performance, generating test data, and analyzing results.
"""

import gc
import json
import logging
import os
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

import matplotlib.pyplot as plt
import numpy as np
import psutil
from matplotlib.figure import Figure

# Configure logging
logger = logging.getLogger("ztoq.performance")


@dataclass
class PerformanceMeasurement:
    """Represents a single performance measurement."""

    name: str
    operation: str
    duration: float
    timestamp: float = field(default_factory=time.time)
    dataset_size: Optional[int] = None
    batch_size: Optional[int] = None
    concurrency: Optional[int] = None
    memory_before: Optional[float] = None
    memory_after: Optional[float] = None
    cpu_percent: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def memory_delta(self) -> Optional[float]:
        """Return memory usage delta if both before and after measurements are available."""
        if self.memory_before is not None and self.memory_after is not None:
            return self.memory_after - self.memory_before
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert measurement to dictionary for serialization."""
        result = {
            "name": self.name,
            "operation": self.operation,
            "duration": self.duration,
            "timestamp": self.timestamp,
        }

        # Add optional fields if they exist
        if self.dataset_size is not None:
            result["dataset_size"] = self.dataset_size
        if self.batch_size is not None:
            result["batch_size"] = self.batch_size
        if self.concurrency is not None:
            result["concurrency"] = self.concurrency
        if self.memory_before is not None:
            result["memory_before"] = self.memory_before
        if self.memory_after is not None:
            result["memory_after"] = self.memory_after
        if self.cpu_percent is not None:
            result["cpu_percent"] = self.cpu_percent
        if self.metadata:
            result["metadata"] = self.metadata

        return result


@dataclass
class PerformanceResult:
    """Collection of performance measurements with analysis capabilities."""

    name: str
    measurements: List[PerformanceMeasurement] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_measurement(self, measurement: PerformanceMeasurement) -> None:
        """Add a measurement to the result set."""
        self.measurements.append(measurement)

    def get_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Calculate statistics for the measurements."""
        filtered = (
            self.measurements if operation is None else [m for m in self.measurements if m.operation == operation]
        )

        if not filtered:
            return {"count": 0}

        durations = [m.duration for m in filtered]

        stats = {
            "count": len(filtered),
            "min": min(durations),
            "max": max(durations),
            "mean": statistics.mean(durations),
            "median": statistics.median(durations),
        }

        # Add standard deviation if we have enough measurements
        if len(filtered) > 1:
            stats["stddev"] = statistics.stdev(durations)

        # Calculate percentiles
        durations.sort()
        stats["p50"] = np.percentile(durations, 50)
        stats["p90"] = np.percentile(durations, 90)
        stats["p95"] = np.percentile(durations, 95)
        stats["p99"] = np.percentile(durations, 99)

        # Calculate throughput (operations per second)
        total_duration = sum(durations)
        stats["throughput"] = len(filtered) / total_duration if total_duration > 0 else 0

        # Calculate memory usage if available
        memory_deltas = [m.memory_delta for m in filtered if m.memory_delta is not None]
        if memory_deltas:
            stats["memory_mean_delta"] = statistics.mean(memory_deltas)
            stats["memory_max_delta"] = max(memory_deltas)

        return stats

    def plot_durations(self, operation: Optional[str] = None,
                       save_path: Optional[str] = None) -> Figure:
        """Plot performance measurements."""
        filtered = (
            self.measurements if operation is None else [m for m in self.measurements if m.operation == operation]
        )

        if not filtered:
            logger.warning(f"No measurements found for operation '{operation}'")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, "No data available", ha="center", va="center")
            return fig

        # Create figure with three subplots
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 15), sharex=False)

        # 1. Duration histogram
        durations = [m.duration for m in filtered]
        ax1.hist(durations, bins=20, alpha=0.7, color="skyblue")
        ax1.set_xlabel("Duration (seconds)")
        ax1.set_ylabel("Frequency")
        ax1.set_title(f"Distribution of operation durations: {operation or 'All operations'}")
        ax1.grid(True, linestyle="--", alpha=0.7)

        # 2. Duration over time (scatter plot)
        timestamps = [m.timestamp - filtered[0].timestamp for m in filtered]  # normalize to start time
        ax2.scatter(timestamps, durations, alpha=0.7, color="green")
        ax2.set_xlabel("Time since start (seconds)")
        ax2.set_ylabel("Duration (seconds)")
        ax2.set_title("Operation duration over time")
        ax2.grid(True, linestyle="--", alpha=0.7)

        # Calculate throughput over time windows
        if len(filtered) > 10:
            # 3. Throughput over time
            window_size = max(1, len(filtered) // 10)  # Adjust window size based on data
            throughputs = []
            window_times = []

            for i in range(0, len(filtered) - window_size, window_size):
                window = filtered[i:i + window_size]
                window_duration = (window[-1].timestamp - window[0].timestamp)

                # Avoid division by zero
                if window_duration > 0:
                    throughput = len(window) / window_duration
                    throughputs.append(throughput)
                    window_times.append((window[0].timestamp + window[-1].timestamp) / 2 - filtered[0].timestamp)

            if throughputs:
                ax3.plot(window_times, throughputs, marker='o', linestyle='-', color='purple')
                ax3.set_xlabel("Time since start (seconds)")
                ax3.set_ylabel("Throughput (ops/second)")
                ax3.set_title("Throughput over time")
                ax3.grid(True, linestyle="--", alpha=0.7)
            else:
                ax3.text(0.5, 0.5, "Insufficient data for throughput calculation",
                         ha="center", va="center", transform=ax3.transAxes)
        else:
            ax3.text(0.5, 0.5, "Need more samples for throughput calculation",
                     ha="center", va="center", transform=ax3.transAxes)

        plt.tight_layout()

        # Save the figure if path is provided
        if save_path:
            plt.savefig(save_path)
            logger.info(f"Performance plot saved to {save_path}")

        return fig

    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save performance results to a JSON file."""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        result_dict = {
            "name": self.name,
            "metadata": self.metadata,
            "timestamp": datetime.now().isoformat(),
            "measurements": [m.to_dict() for m in self.measurements],
        }

        with open(file_path, "w") as f:
            json.dump(result_dict, f, indent=2)

        logger.info(f"Performance results saved to {file_path}")

    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> "PerformanceResult":
        """Load performance results from a JSON file."""
        file_path = Path(file_path)

        with open(file_path, "r") as f:
            data = json.load(f)

        result = cls(name=data["name"], metadata=data.get("metadata", {}))

        for m_data in data["measurements"]:
            measurement = PerformanceMeasurement(
                name=m_data["name"],
                operation=m_data["operation"],
                duration=m_data["duration"],
                timestamp=m_data["timestamp"],
                dataset_size=m_data.get("dataset_size"),
                batch_size=m_data.get("batch_size"),
                concurrency=m_data.get("concurrency"),
                memory_before=m_data.get("memory_before"),
                memory_after=m_data.get("memory_after"),
                cpu_percent=m_data.get("cpu_percent"),
                metadata=m_data.get("metadata", {}),
            )
            result.add_measurement(measurement)

        return result


class PerformanceTest:
    """Base class for performance tests."""

    def __init__(self, name: str, output_dir: Optional[str] = None):
        """Initialize performance test.

        Args:
            name: Name of the performance test
            output_dir: Directory to store test results
        """
        self.name = name
        self.result = PerformanceResult(name=name)

        # Set up output directory
        self.output_dir = output_dir or os.environ.get(
            "ZTOQ_PERFORMANCE_OUTPUT", "/tmp/ztoq_performance"
        )
        self.output_path = Path(self.output_dir) / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Setup logging
        logging.basicConfig(level=logging.INFO)

    def setup(self) -> None:
        """Set up the performance test environment."""
        # Create output directory
        self.output_path.mkdir(parents=True, exist_ok=True)

        # Disable garbage collection during tests for more consistent results
        gc.disable()

    def teardown(self) -> None:
        """Clean up after performance test."""
        # Re-enable garbage collection
        gc.enable()

        # Save results
        results_file = self.output_path / "results.json"
        self.result.save_to_file(results_file)

        # Generate plots
        self.generate_reports()

    def measure(
        self,
        operation: str,
        dataset_size: Optional[int] = None,
        batch_size: Optional[int] = None,
        concurrency: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Callable:
        """Decorator to measure performance of a function.

        Args:
            operation: Name of the operation being measured
            dataset_size: Size of the dataset being processed
            batch_size: Batch size used for processing
            concurrency: Level of concurrency (threads/processes)
            metadata: Additional metadata for the measurement

        Returns:
            Decorated function
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                # Record memory usage before
                process = psutil.Process(os.getpid())
                memory_before = process.memory_info().rss / 1024 / 1024  # MB

                # Measure performance
                start_time = time.time()
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # Record memory and CPU after
                memory_after = process.memory_info().rss / 1024 / 1024  # MB
                cpu_percent = process.cpu_percent()

                # Create measurement
                measurement = PerformanceMeasurement(
                    name=self.name,
                    operation=operation,
                    duration=duration,
                    dataset_size=dataset_size,
                    batch_size=batch_size,
                    concurrency=concurrency,
                    memory_before=memory_before,
                    memory_after=memory_after,
                    cpu_percent=cpu_percent,
                    metadata=metadata or {},
                )

                # Add measurement to results
                self.result.add_measurement(measurement)

                # Log the measurement
                logger.info(
                    f"Operation '{operation}' completed in {duration:.4f}s "
                    f"(Memory: {memory_before:.1f}MB → {memory_after:.1f}MB, "
                    f"CPU: {cpu_percent:.1f}%)"
                )

                return result

            return wrapper

        return decorator

    def generate_reports(self) -> None:
        """Generate performance reports and plots."""
        # Generate overall stats
        stats = self.result.get_stats()
        stats_file = self.output_path / "stats.json"

        with open(stats_file, "w") as f:
            json.dump(stats, f, indent=2)

        # Generate stats per operation
        operations = {m.operation for m in self.result.measurements}
        operation_stats = {op: self.result.get_stats(op) for op in operations}

        op_stats_file = self.output_path / "operation_stats.json"
        with open(op_stats_file, "w") as f:
            json.dump(operation_stats, f, indent=2)

        # Generate plots
        for operation in operations:
            plot_file = self.output_path / f"plot_{operation.replace(' ', '_')}.png"
            self.result.plot_durations(operation=operation, save_path=str(plot_file))

        # Generate overall plot
        overall_plot_file = self.output_path / "plot_overall.png"
        self.result.plot_durations(save_path=str(overall_plot_file))

        logger.info(f"Performance reports generated in {self.output_path}")

    def run(self) -> PerformanceResult:
        """Run the performance test."""
        try:
            self.setup()
            self._run_test()
        finally:
            self.teardown()

        return self.result

    def _run_test(self) -> None:
        """Run the performance test implementation.

        This method should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement _run_test method")


class DataGenerator:
    """Utility for generating test data for performance tests."""

    @staticmethod
    def generate_test_cases(count: int, with_steps: bool = True) -> List[Dict[str, Any]]:
        """Generate test case data for performance testing.

        Args:
            count: Number of test cases to generate
            with_steps: Whether to include test steps

        Returns:
            List of dictionaries representing test cases
        """
        test_cases = []

        for i in range(count):
            test_case = {
                "id": i + 1,
                "key": f"TC-{i+1}",
                "name": f"Test Case {i+1}",
                "objective": f"Test objective for test case {i+1}",
                "precondition": f"Preconditions for test case {i+1}",
                "priority": "High" if i % 3 == 0 else "Medium" if i % 3 == 1 else "Low",
                "status": "Active" if i % 2 == 0 else "Draft",
                "owner": f"user{i % 10 + 1}@example.com",
                "custom_fields": {
                    f"custom_field_{j}": f"value_{i}_{j}" for j in range(1, 6)
                }
            }

            if with_steps:
                test_case["steps"] = [
                    {
                        "id": i * 100 + j,
                        "order": j,
                        "description": f"Step {j} description for test case {i+1}",
                        "expected_result": f"Expected result for step {j} of test case {i+1}"
                    } for j in range(1, 6)  # 5 steps per test case
                ]

            test_cases.append(test_case)

        return test_cases

    @staticmethod
    def generate_test_cycles(count: int, test_cases_per_cycle: int = 10) -> List[Dict[str, Any]]:
        """Generate test cycle data for performance testing.

        Args:
            count: Number of test cycles to generate
            test_cases_per_cycle: Number of test cases to include in each cycle

        Returns:
            List of dictionaries representing test cycles
        """
        test_cycles = []

        for i in range(count):
            test_cycle = {
                "id": i + 1,
                "key": f"CYC-{i+1}",
                "name": f"Test Cycle {i+1}",
                "description": f"Description for test cycle {i+1}",
                "status": "Active" if i % 2 == 0 else "Completed",
                "owner": f"user{i % 10 + 1}@example.com",
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "test_cases": [
                    {
                        "id": j + 1,
                        "key": f"TC-{j+1}",
                        "name": f"Test Case {j+1}"
                    } for j in range(i * test_cases_per_cycle, (i + 1) * test_cases_per_cycle)
                ],
                "custom_fields": {
                    f"custom_field_{j}": f"value_{i}_{j}" for j in range(1, 3)
                }
            }

            test_cycles.append(test_cycle)

        return test_cycles

    @staticmethod
    def generate_test_executions(count: int, steps_per_execution: int = 5) -> List[Dict[str, Any]]:
        """Generate test execution data for performance testing.

        Args:
            count: Number of test executions to generate
            steps_per_execution: Number of steps per execution

        Returns:
            List of dictionaries representing test executions
        """
        test_executions = []

        for i in range(count):
            test_case_id = (i % 100) + 1
            test_cycle_id = (i // 100) + 1

            execution = {
                "id": i + 1,
                "test_case_id": test_case_id,
                "test_cycle_id": test_cycle_id,
                "key": f"EXEC-{i+1}",
                "status": "Passed" if i % 3 == 0 else "Failed" if i % 3 == 1 else "Blocked",
                "executed_by": f"user{i % 10 + 1}@example.com",
                "executed_on": "2025-06-15",
                "environment": f"Environment {i % 5 + 1}",
                "comment": f"Execution comment for execution {i+1}",
                "steps": [
                    {
                        "id": i * 100 + j,
                        "order": j,
                        "status": "Passed" if j % 3 != 1 else "Failed",
                        "comment": f"Step {j} result for execution {i+1}"
                    } for j in range(1, steps_per_execution + 1)
                ],
                "custom_fields": {
                    f"custom_field_{j}": f"value_{i}_{j}" for j in range(1, 4)
                }
            }

            test_executions.append(execution)

        return test_executions


# Helper functions for performance testing
def format_duration(seconds: float) -> str:
    """Format duration in a human-readable way."""
    if seconds < 0.001:
        return f"{seconds * 1000000:.2f} µs"
    elif seconds < 1:
        return f"{seconds * 1000:.2f} ms"
    elif seconds < 60:
        return f"{seconds:.2f} s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{int(minutes)}m {secs:.2f}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{int(hours)}h {int(minutes)}m {secs:.2f}s"


def format_memory(bytes_value: float) -> str:
    """Format memory in a human-readable way."""
    kb = bytes_value / 1024
    if kb < 1024:
        return f"{kb:.2f} KB"
    mb = kb / 1024
    if mb < 1024:
        return f"{mb:.2f} MB"
    gb = mb / 1024
    return f"{gb:.2f} GB"
