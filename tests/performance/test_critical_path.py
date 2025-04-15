"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Critical path identification and optimization module.

This module analyzes profiling data to identify critical paths in the migration
workflow and provides optimization recommendations for improving performance.
"""

import json
import logging
import pstats
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)


class CriticalPathOptimizer:
    """
    Analyzes profiling data to identify critical paths and optimize performance.
    
    This class takes profiling data from the performance tests and identifies
    the critical paths (bottlenecks) in the code, providing specific
    optimization recommendations.
    """

    def __init__(
        self,
        profile_data_dir: str | None = None,
        output_dir: str | None = None,
    ):
        """
        Initialize the critical path optimizer.
        
        Args:
            profile_data_dir: Directory containing profiling data
            output_dir: Directory to store optimization results
        """
        self.profile_data_dir = Path(profile_data_dir) if profile_data_dir else None
        self.output_dir = Path(output_dir) if output_dir else Path("/tmp/ztoq_optimizations")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Storage for analysis results
        self.hotspots = {}
        self.call_graphs = {}
        self.optimization_recommendations = []

    def find_profile_data(self) -> list[Path]:
        """
        Find all profile data files in the profile data directory.
        
        Returns:
            List of paths to profile data files
        """
        if not self.profile_data_dir:
            # Look in default locations for performance test output
            default_dirs = [
                Path("/tmp/ztoq_performance"),
                Path("./performance_results"),
            ]

            for directory in default_dirs:
                if directory.exists():
                    self.profile_data_dir = directory
                    break

            if not self.profile_data_dir:
                raise ValueError("No profile data directory specified and no default directory found")

        # Find all .prof files
        prof_files = list(self.profile_data_dir.glob("**/*.prof"))

        if not prof_files:
            raise ValueError(f"No profile data files found in {self.profile_data_dir}")

        logger.info(f"Found {len(prof_files)} profile data files in {self.profile_data_dir}")
        return prof_files

    def analyze_profile(self, profile_path: Path) -> dict[str, Any]:
        """
        Analyze a profile data file to identify hotspots.
        
        Args:
            profile_path: Path to the profile data file
            
        Returns:
            Dictionary with analysis results
        """
        # Load stats from profile
        stats = pstats.Stats(str(profile_path))

        # Extract phase and config from filename
        filename = profile_path.stem
        phase = "unknown"
        config = "unknown"

        if "_" in filename:
            parts = filename.split("_", 1)
            phase = parts[0]
            config = parts[1] if len(parts) > 1 else "default"

        # Get top functions by cumulative time
        function_stats = {}

        # Create a string buffer to capture output
        import io
        output = io.StringIO()

        # Print stats to the buffer
        stats.sort_stats("cumulative").print_stats(20, file=output)

        # Extract hotspots from the output
        output.seek(0)
        lines = output.getvalue().split("\n")

        # Skip header lines
        data_lines = []
        for i, line in enumerate(lines):
            if line.strip().startswith("ncalls"):
                data_lines = lines[i+1:]
                break

        # Parse function stats
        for line in data_lines:
            if not line.strip():
                continue

            try:
                parts = line.strip().split()
                if len(parts) >= 6:
                    # Extract stats and function name
                    cum_time = float(parts[3])
                    per_call = float(parts[4])

                    # Function name is the rest of the line after the last number
                    func_name = " ".join(parts[5:])

                    # Clean up function name
                    func_name = func_name.strip()

                    # Add to function stats
                    function_stats[func_name] = {
                        "cumulative_time": cum_time,
                        "per_call": per_call,
                    }
            except Exception as e:
                logger.warning(f"Error parsing line '{line}': {e!s}")
                continue

        # Calculate percentage of total time
        total_time = sum(stat["cumulative_time"] for stat in function_stats.values())

        for func_name, stat in function_stats.items():
            if total_time > 0:
                stat["percentage"] = (stat["cumulative_time"] / total_time) * 100
            else:
                stat["percentage"] = 0

        # Return analysis results
        return {
            "phase": phase,
            "config": config,
            "profile_path": str(profile_path),
            "total_time": total_time,
            "function_stats": function_stats,
        }

    def analyze_all_profiles(self) -> dict[str, dict[str, Any]]:
        """
        Analyze all profile data files to identify hotspots across phases.
        
        Returns:
            Dictionary with analysis results by profile
        """
        # Find all profile data files
        profile_paths = self.find_profile_data()

        # Analyze each profile
        analysis_results = {}

        for profile_path in profile_paths:
            try:
                # Analyze profile
                analysis = self.analyze_profile(profile_path)

                # Store analysis results
                analysis_results[profile_path.stem] = analysis

                # Extract phase and config
                phase = analysis["phase"]
                config = analysis["config"]

                # Store hotspots by phase and config
                if phase not in self.hotspots:
                    self.hotspots[phase] = {}

                self.hotspots[phase][config] = analysis

            except Exception as e:
                logger.error(f"Error analyzing profile {profile_path}: {e!s}", exc_info=True)

        return analysis_results

    def identify_common_hotspots(self) -> list[tuple[str, float, list[str]]]:
        """
        Identify functions that are hotspots across multiple phases.
        
        Returns:
            List of (function_name, total_percentage, phases) tuples
        """
        # Track functions that appear in multiple phases
        function_occurrences = {}

        # Iterate through all hotspots
        for phase, configs in self.hotspots.items():
            for config, analysis in configs.items():
                function_stats = analysis.get("function_stats", {})

                for func_name, stats in function_stats.items():
                    if func_name not in function_occurrences:
                        function_occurrences[func_name] = {
                            "phases": set(),
                            "total_percentage": 0,
                        }

                    function_occurrences[func_name]["phases"].add(phase)
                    function_occurrences[func_name]["total_percentage"] += stats.get("percentage", 0)

        # Convert to list of tuples, sorted by frequency and impact
        common_hotspots = [
            (func_name, data["total_percentage"], sorted(data["phases"]))
            for func_name, data in function_occurrences.items()
            if len(data["phases"]) > 1  # Only include functions that appear in multiple phases
        ]

        # Sort by total percentage (impact) in descending order
        common_hotspots.sort(key=lambda x: x[1], reverse=True)

        return common_hotspots

    def generate_optimization_recommendations(self) -> list[dict[str, Any]]:
        """
        Generate optimization recommendations based on profiling analysis.
        
        Returns:
            List of optimization recommendation dictionaries
        """
        # Find common hotspots
        common_hotspots = self.identify_common_hotspots()

        # Generate recommendations
        recommendations = []

        if not common_hotspots:
            logger.warning("No common hotspots identified, cannot generate recommendations")
            return recommendations

        # Process each hotspot
        for func_name, total_percentage, phases in common_hotspots:
            # Skip functions with low impact
            if total_percentage < 5.0:
                continue

            # Generate recommendation
            recommendation = {
                "function": func_name,
                "impact": total_percentage,
                "phases": phases,
                "recommendation": self._generate_recommendation_for_function(func_name, phases),
                "priority": "high" if total_percentage > 20 else "medium" if total_percentage > 10 else "low",
            }

            recommendations.append(recommendation)

        # Add recommendations for specific phases
        for phase, configs in self.hotspots.items():
            for config, analysis in configs.items():
                # Find the top 3 functions in this phase
                function_stats = analysis.get("function_stats", {})

                top_functions = sorted(
                    function_stats.items(),
                    key=lambda x: x[1].get("percentage", 0),
                    reverse=True,
                )[:3]

                for func_name, stats in top_functions:
                    # Skip if already covered in common hotspots
                    if any(func_name == h[0] for h in common_hotspots):
                        continue

                    # Skip functions with low impact
                    if stats.get("percentage", 0) < 10.0:
                        continue

                    # Generate recommendation
                    recommendation = {
                        "function": func_name,
                        "impact": stats.get("percentage", 0),
                        "phases": [phase],
                        "recommendation": self._generate_recommendation_for_function(func_name, [phase]),
                        "priority": "high" if stats.get("percentage", 0) > 20 else "medium" if stats.get("percentage", 0) > 10 else "low",
                    }

                    recommendations.append(recommendation)

        # Sort recommendations by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        recommendations.sort(key=lambda x: (priority_order[x["priority"]], -x["impact"]))

        # Store recommendations
        self.optimization_recommendations = recommendations

        return recommendations

    def _generate_recommendation_for_function(self, func_name: str, phases: list[str]) -> str:
        """
        Generate a specific optimization recommendation for a function.
        
        Args:
            func_name: Name of the function
            phases: List of phases where the function is a hotspot
            
        Returns:
            Optimization recommendation text
        """
        # Extract module and function name
        parts = func_name.split(":")
        if len(parts) > 1:
            module_path = parts[0].strip()
            method_name = parts[1].strip()
        else:
            # Try alternative format
            parts = func_name.split(" ")
            if len(parts) > 1:
                module_path = parts[0].strip()
                method_name = parts[1].strip()
            else:
                module_path = func_name
                method_name = ""

        # Generate recommendation based on function name
        if "batch_strategies" in module_path and "create_batches" in method_name:
            return (
                "Optimize batch creation logic by pre-allocating arrays and using "
                "more efficient data structures. Consider caching batch calculation "
                "results for similar inputs."
            )

        if "work_queue" in module_path and "process" in method_name:
            return (
                "Optimize the work queue processing by reducing synchronization overhead. "
                "Consider using a more specialized queue implementation for the specific "
                "workload pattern. For network-heavy workloads, increase concurrency; "
                "for CPU-bound workloads, adjust worker type to match characteristics."
            )

        if "test_case_transformer" in module_path and "transform_" in method_name:
            return (
                "Optimize transformation logic by using vectorized operations with NumPy/Pandas. "
                "Reduce memory allocations and consider implementing field-selective transformation "
                "to avoid processing unchanged fields."
            )

        if "database_manager" in module_path or "_db_" in module_path:
            return (
                "Optimize database access by implementing prepared statements, adding "
                "specific indexes for frequently queried fields, and enabling query caching. "
                "Use bulk operations for inserts and updates."
            )

        if "http" in module_path.lower() or "client" in module_path.lower():
            return (
                "Optimize API client performance by enabling connection pooling, implementing "
                "request batching, and using parallel requests for independent operations. "
                "Consider adding application-level caching for frequently accessed data."
            )

        if "json" in module_path.lower() or "serialize" in module_path.lower():
            return (
                "Optimize serialization/deserialization performance by using a faster JSON library "
                "like ujson or orjson. For large payloads, consider using a binary format like "
                "msgpack or protocol buffers."
            )

        if "migration" in module_path and ("extract" in method_name or "load" in method_name):
            return (
                "Optimize I/O operations by increasing batch sizes and concurrency. "
                "Use asynchronous I/O with asyncio for network operations. Consider "
                "implementing data compression for large transfers."
            )

        # Generic recommendation
        return (
            "Profile this function more deeply to identify specific optimization opportunities. "
            "Consider algorithmic improvements, caching results, or parallelizing operations "
            "if appropriate for the workload."
        )

    def generate_optimization_report(self) -> str:
        """
        Generate a comprehensive optimization report.
        
        Returns:
            Path to the generated report file
        """
        # Analyze profiles if not already done
        if not self.hotspots:
            self.analyze_all_profiles()

        # Generate recommendations if not already done
        if not self.optimization_recommendations:
            self.generate_optimization_recommendations()

        # Create report
        report_lines = ["# Critical Path Optimization Report", ""]

        # Add summary
        report_lines.append("## Summary")
        report_lines.append("")
        report_lines.append(f"This report analyzes {len(self.hotspots)} phases across different configurations.")
        report_lines.append("Based on profiling data, the following optimization opportunities were identified:")
        report_lines.append("")

        # Add high-priority recommendations
        high_priority_recs = [r for r in self.optimization_recommendations if r["priority"] == "high"]
        if high_priority_recs:
            report_lines.append("### High Priority Optimizations")
            report_lines.append("")
            for rec in high_priority_recs:
                report_lines.append(f"- **{rec['function']}** ({rec['impact']:.1f}% impact)")
                report_lines.append(f"  - Phases: {', '.join(rec['phases'])}")
                report_lines.append(f"  - Recommendation: {rec['recommendation']}")
                report_lines.append("")

        # Add medium-priority recommendations
        medium_priority_recs = [r for r in self.optimization_recommendations if r["priority"] == "medium"]
        if medium_priority_recs:
            report_lines.append("### Medium Priority Optimizations")
            report_lines.append("")
            for rec in medium_priority_recs:
                report_lines.append(f"- **{rec['function']}** ({rec['impact']:.1f}% impact)")
                report_lines.append(f"  - Phases: {', '.join(rec['phases'])}")
                report_lines.append(f"  - Recommendation: {rec['recommendation']}")
                report_lines.append("")

        # Add phase-specific analysis
        report_lines.append("## Phase-Specific Analysis")
        report_lines.append("")

        for phase, configs in self.hotspots.items():
            report_lines.append(f"### {phase.title()} Phase")
            report_lines.append("")

            for config, analysis in configs.items():
                report_lines.append(f"#### Configuration: {config}")
                report_lines.append("")
                report_lines.append(f"Total time: {analysis.get('total_time', 0):.2f} seconds")
                report_lines.append("")
                report_lines.append("Top functions by cumulative time:")
                report_lines.append("")

                # Sort functions by percentage
                function_stats = analysis.get("function_stats", {})
                sorted_functions = sorted(
                    function_stats.items(),
                    key=lambda x: x[1].get("percentage", 0),
                    reverse=True,
                )

                # Add table header
                report_lines.append("| Function | % of Total Time | Cumulative Time (s) |")
                report_lines.append("|---------|----------------|---------------------|")

                # Add top 10 functions
                for func_name, stats in sorted_functions[:10]:
                    percentage = stats.get("percentage", 0)
                    cum_time = stats.get("cumulative_time", 0)
                    report_lines.append(f"| {func_name} | {percentage:.1f}% | {cum_time:.3f} |")

                report_lines.append("")

        # Add implementation plan
        report_lines.append("## Implementation Plan")
        report_lines.append("")
        report_lines.append("Based on the identified critical paths, the following implementation plan is recommended:")
        report_lines.append("")

        # Add tasks for each high-priority recommendation
        for i, rec in enumerate(high_priority_recs, 1):
            report_lines.append(f"1. Optimize {rec['function']} function:")
            report_lines.append(f"   - Implement {rec['recommendation']}")
            report_lines.append("   - Add performance tests to measure improvement")
            report_lines.append(f"   - Expected impact: {rec['impact']:.1f}% improvement in {', '.join(rec['phases'])} phase(s)")
            report_lines.append("")

        # Add tasks for medium-priority recommendations
        for i, rec in enumerate(medium_priority_recs, len(high_priority_recs) + 1):
            report_lines.append(f"{i}. Optimize {rec['function']} function:")
            report_lines.append(f"   - Implement {rec['recommendation']}")
            report_lines.append("   - Add performance tests to measure improvement")
            report_lines.append(f"   - Expected impact: {rec['impact']:.1f}% improvement in {', '.join(rec['phases'])} phase(s)")
            report_lines.append("")

        # Save report
        report_path = self.output_dir / "critical_path_optimization_report.md"
        with open(report_path, "w") as f:
            f.write("\n".join(report_lines))

        logger.info(f"Saved optimization report to {report_path}")

        # Also save recommendations as JSON for programmatic use
        json_path = self.output_dir / "optimization_recommendations.json"
        with open(json_path, "w") as f:
            json.dump(self.optimization_recommendations, f, indent=2)

        logger.info(f"Saved optimization recommendations to {json_path}")

        return str(report_path)

    def visualize_hotspots(self) -> None:
        """
        Create visualizations of the identified hotspots.
        """
        if not self.hotspots:
            self.analyze_all_profiles()

        # Create directory for visualizations
        viz_dir = self.output_dir / "visualizations"
        viz_dir.mkdir(exist_ok=True)

        # Visualize hotspots by phase
        self._create_phase_comparison_chart(viz_dir)

        # Visualize hotspots by function
        self._create_function_impact_chart(viz_dir)

        # Visualize phase timings
        self._create_phase_timing_chart(viz_dir)

        logger.info(f"Saved visualizations to {viz_dir}")

    def _create_phase_comparison_chart(self, output_dir: Path) -> None:
        """
        Create a chart comparing the performance of different phases.
        
        Args:
            output_dir: Directory to save visualization
        """
        # Collect phase timing data
        phase_timings = {}

        for phase, configs in self.hotspots.items():
            for config, analysis in configs.items():
                if phase not in phase_timings:
                    phase_timings[phase] = []

                phase_timings[phase].append(analysis.get("total_time", 0))

        if not phase_timings:
            logger.warning("No phase timing data available for visualization")
            return

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))

        # Prepare data for plotting
        phases = list(phase_timings.keys())
        median_times = [np.median(phase_timings[phase]) for phase in phases]

        # Plot bar chart
        bars = ax.bar(phases, median_times, alpha=0.7)

        # Add data labels
        for bar, time in zip(bars, median_times, strict=False):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.,
                height,
                f"{time:.2f}s",
                ha="center",
                va="bottom",
                fontsize=10,
            )

        # Add labels and title
        ax.set_xlabel("Migration Phase")
        ax.set_ylabel("Median Time (seconds)")
        ax.set_title("Comparison of Phase Execution Times")

        # Format y-axis to start at 0
        ax.set_ylim(bottom=0)

        # Add grid
        ax.grid(axis="y", linestyle="--", alpha=0.7)

        # Save chart
        output_path = output_dir / "phase_comparison_chart.png"
        plt.savefig(output_path)
        plt.close()

    def _create_function_impact_chart(self, output_dir: Path) -> None:
        """
        Create a chart showing the impact of different functions.
        
        Args:
            output_dir: Directory to save visualization
        """
        # Collect function impact data
        function_impacts = {}

        for phase, configs in self.hotspots.items():
            for config, analysis in configs.items():
                function_stats = analysis.get("function_stats", {})

                for func_name, stats in function_stats.items():
                    if func_name not in function_impacts:
                        function_impacts[func_name] = {
                            "impact": 0,
                            "phases": set(),
                        }

                    function_impacts[func_name]["impact"] += stats.get("percentage", 0)
                    function_impacts[func_name]["phases"].add(phase)

        if not function_impacts:
            logger.warning("No function impact data available for visualization")
            return

        # Get top 10 functions by impact
        top_functions = sorted(
            function_impacts.items(),
            key=lambda x: x[1]["impact"],
            reverse=True,
        )[:10]

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 8))

        # Prepare data for plotting
        func_names = [self._shorten_function_name(func) for func, _ in top_functions]
        impacts = [data["impact"] for _, data in top_functions]
        colors = ["#FF9999" if len(data["phases"]) > 1 else "#66B2FF" for _, data in top_functions]

        # Plot horizontal bar chart
        bars = ax.barh(func_names, impacts, alpha=0.7, color=colors)

        # Add data labels
        for bar, impact in zip(bars, impacts, strict=False):
            width = bar.get_width()
            ax.text(
                width,
                bar.get_y() + bar.get_height() / 2.,
                f"{impact:.1f}%",
                ha="left",
                va="center",
                fontsize=10,
            )

        # Add labels and title
        ax.set_xlabel("Impact (% of Total Time)")
        ax.set_title("Top 10 Functions by Performance Impact")

        # Add legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor="#FF9999", label="Multiple Phases"),
            Patch(facecolor="#66B2FF", label="Single Phase"),
        ]
        ax.legend(handles=legend_elements)

        # Format x-axis to start at 0
        ax.set_xlim(left=0)

        # Add grid
        ax.grid(axis="x", linestyle="--", alpha=0.7)

        # Adjust layout to fit function names
        plt.tight_layout()

        # Save chart
        output_path = output_dir / "function_impact_chart.png"
        plt.savefig(output_path)
        plt.close()

    def _create_phase_timing_chart(self, output_dir: Path) -> None:
        """
        Create a chart showing the timing breakdown of different configurations.
        
        Args:
            output_dir: Directory to save visualization
        """
        # Collect configuration timing data
        config_timings = {}

        for phase, configs in self.hotspots.items():
            for config, analysis in configs.items():
                if config not in config_timings:
                    config_timings[config] = {}

                config_timings[config][phase] = analysis.get("total_time", 0)

        if not config_timings:
            logger.warning("No configuration timing data available for visualization")
            return

        # Prepare data for plotting
        configs = list(config_timings.keys())
        phases = set()

        for config_data in config_timings.values():
            phases.update(config_data.keys())

        phases = sorted(phases)

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 8))

        # Set width of bars
        bar_width = 0.8 / len(phases)

        # Create bars
        for i, phase in enumerate(phases):
            phase_times = [config_timings[config].get(phase, 0) for config in configs]
            x_positions = [j + i * bar_width for j in range(len(configs))]

            ax.bar(
                x_positions,
                phase_times,
                width=bar_width,
                label=phase.title(),
                alpha=0.7,
            )

        # Add labels and title
        ax.set_xlabel("Configuration")
        ax.set_ylabel("Time (seconds)")
        ax.set_title("Phase Timing by Configuration")

        # Set x-tick positions and labels
        ax.set_xticks([i + bar_width * (len(phases) - 1) / 2 for i in range(len(configs))])
        ax.set_xticklabels(configs, rotation=45, ha="right")

        # Add legend
        ax.legend()

        # Format y-axis to start at 0
        ax.set_ylim(bottom=0)

        # Add grid
        ax.grid(axis="y", linestyle="--", alpha=0.7)

        # Adjust layout
        plt.tight_layout()

        # Save chart
        output_path = output_dir / "phase_timing_by_config_chart.png"
        plt.savefig(output_path)
        plt.close()

    def _shorten_function_name(self, full_name: str) -> str:
        """
        Shorten a function name for display in charts.
        
        Args:
            full_name: Full function name
            
        Returns:
            Shortened function name
        """
        # Extract module and function name
        parts = full_name.split(":")
        if len(parts) > 1:
            module_path = parts[0].strip()
            method_name = parts[1].strip()
        else:
            # Try alternative format
            parts = full_name.split(" ")
            if len(parts) > 1:
                module_path = parts[0].strip()
                method_name = parts[1].strip()
            else:
                return full_name[:40] + "..." if len(full_name) > 40 else full_name

        # Shorten module path
        if len(module_path) > 25:
            # Keep only the package and module name
            mod_parts = module_path.split(".")
            if len(mod_parts) > 2:
                module_path = f"{mod_parts[0]}...{mod_parts[-1]}"

        # Return shortened name
        return f"{module_path}: {method_name}"


def run_critical_path_analysis(profile_data_dir: str | None = None, output_dir: str | None = None) -> str:
    """
    Run critical path analysis and generate optimization report.
    
    Args:
        profile_data_dir: Directory containing profiling data
        output_dir: Directory to store optimization results
        
    Returns:
        Path to the generated report file
    """
    optimizer = CriticalPathOptimizer(profile_data_dir, output_dir)
    optimizer.analyze_all_profiles()
    optimizer.generate_optimization_recommendations()
    optimizer.visualize_hotspots()
    return optimizer.generate_optimization_report()


def main():
    """
    Main entry point when run as a script.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Analyze profile data and identify critical paths")
    parser.add_argument(
        "--profile-dir",
        type=str,
        help="Directory containing profiling data",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/tmp/ztoq_optimizations",
        help="Directory to store optimization results",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run analysis
    report_path = run_critical_path_analysis(args.profile_dir, args.output_dir)

    print(f"Critical path analysis complete. Report saved to: {report_path}")


if __name__ == "__main__":
    main()
