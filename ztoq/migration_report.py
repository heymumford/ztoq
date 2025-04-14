#!/usr/bin/env python3
"""
Migration report generation module.

This module provides tools for generating detailed reports on migration progress
and results. It can connect to the migration database and produce reports in
various formats including console, HTML, JSON, and CSV.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for headless environments
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.table import Table
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from ztoq.core.db_models import Base, EntityBatchState, MigrationState

# Configure rich console
console = Console()


class MigrationReportGenerator:
    """Class for generating migration reports from the database."""

    def __init__(self, db_url: str, project_key: str):
        """Initialize the report generator.

        Args:
            db_url: SQLAlchemy database URL (e.g., 'sqlite:///migration.db')
            project_key: The Zephyr project key to generate the report for
        """
        self.db_url = db_url
        self.project_key = project_key
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)

    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive migration report.

        Returns:
            Dict containing the complete migration report data
        """
        report = {
            "project_key": self.project_key,
                "timestamp": datetime.now().isoformat(),
                "migration_state": self._get_migration_state(),
                "entity_counts": self._get_entity_counts(),
                "batch_statistics": self._get_batch_statistics(),
                "validation_statistics": self._get_validation_statistics(),
                "validation_issues": self._get_recent_validation_issues(),
                "failure_details": self._get_failure_details(),
                "timing_info": self._get_timing_info(),
                "performance_metrics": self._get_performance_metrics(),
            }

        return report

    def _get_migration_state(self) -> Optional[Dict[str, Any]]:
        """Get the current migration state."""
        with self.Session() as session:
            state = session.query(MigrationState).filter_by(project_key=self.project_key).first()
            if state:
                return {
                    "extraction_status": state.extraction_status,
                        "transformation_status": state.transformation_status,
                        "loading_status": state.loading_status,
                        "error_message": state.error_message,
                        "created_at": state.created_at.isoformat() if state.created_at else None,
                        "updated_at": state.last_updated.isoformat() if state.last_updated else None,
                    }
            return None

    def _get_entity_counts(self) -> Dict[str, Dict[str, int]]:
        """Get counts of migrated entities."""
        entity_counts = {}

        with self.Session() as session:
            # Get counts of mapped entities
            mapping_counts = {}
            mapping_types = [
                "folder_to_module",
                    "testcase_to_testcase",
                    "cycle_to_cycle",
                    "execution_to_run",
                ]

            for mapping_type in mapping_types:
                count = session.execute(text(
                    """
                    SELECT COUNT(*)
                    FROM entity_mappings
                    WHERE project_key = :project_key
                    AND mapping_type = :mapping_type
                    """
                ), {"project_key": self.project_key, "mapping_type": mapping_type}).scalar() or 0

                mapping_counts[mapping_type] = count

            entity_counts["mappings"] = mapping_counts

            # Get source entity counts from batches
            source_counts = {}
            entity_types = [
                "folders",
                    "test_cases",
                    "test_cycles",
                    "test_executions",
                ]

            for entity_type in entity_types:
                # Get batch info for this entity type
                batches = session.query(EntityBatchState).filter_by(
                    project_key=self.project_key, entity_type=entity_type
                ).all()

                if batches:
                    # Sum up the items_count across all batches
                    total_items = sum(batch.items_count for batch in batches)
                    source_counts[entity_type] = total_items
                else:
                    source_counts[entity_type] = 0

            entity_counts["source"] = source_counts

            # Get transformed entity counts
            transformed_counts = {}
            transformed_types = [
                "transformed_test_cases",
                    "transformed_test_cycles",
                    "transformed_test_executions",
                ]

            for entity_type in transformed_types:
                batches = session.query(EntityBatchState).filter_by(
                    project_key=self.project_key, entity_type=entity_type
                ).all()

                if batches:
                    total_processed = sum(batch.processed_count for batch in batches if batch.status == "completed")
                    transformed_counts[entity_type] = total_processed
                else:
                    transformed_counts[entity_type] = 0

            entity_counts["transformed"] = transformed_counts

            # Get loaded entity counts
            loaded_counts = {}
            loaded_types = [
                "loaded_test_cases",
                    "loaded_test_cycles",
                    "loaded_test_executions",
                ]

            for entity_type in loaded_types:
                batches = session.query(EntityBatchState).filter_by(
                    project_key=self.project_key, entity_type=entity_type
                ).all()

                if batches:
                    total_processed = sum(batch.processed_count for batch in batches if batch.status == "completed")
                    loaded_counts[entity_type] = total_processed
                else:
                    loaded_counts[entity_type] = 0

            entity_counts["loaded"] = loaded_counts

        return entity_counts

    def _get_batch_statistics(self) -> Dict[str, Dict[str, Union[int, float]]]:
        """Get statistics about batch processing."""
        batch_stats = {}

        with self.Session() as session:
            # Get all entity types that have batches
            entity_types = []
            result = session.execute(text(
                """
                SELECT DISTINCT entity_type
                FROM entity_batch_state
                WHERE project_key = :project_key
                """
            ), {"project_key": self.project_key})

            for row in result:
                entity_types.append(row[0])

            # Get stats for each entity type
            for entity_type in entity_types:
                batches = session.query(EntityBatchState).filter_by(
                    project_key=self.project_key, entity_type=entity_type
                ).all()

                if batches:
                    # Calculate statistics
                    total_batches = len(batches)
                    completed_batches = sum(1 for batch in batches if batch.status == "completed")
                    failed_batches = sum(1 for batch in batches if batch.status == "failed")
                    pending_batches = sum(1 for batch in batches
                                         if batch.status in ["not_started", "in_progress"])

                    total_items = sum(batch.items_count for batch in batches)
                    processed_items = sum(batch.processed_count for batch in batches)

                    if total_items > 0:
                        completion_percentage = (processed_items / total_items) * 100
                    else:
                        completion_percentage = 0

                    batch_stats[entity_type] = {
                        "total_batches": total_batches,
                            "completed_batches": completed_batches,
                            "failed_batches": failed_batches,
                            "pending_batches": pending_batches,
                            "total_items": total_items,
                            "processed_items": processed_items,
                            "completion_percentage": completion_percentage,
                        }

        return batch_stats

    def _get_failure_details(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get details about batch processing failures."""
        failure_details = {}

        with self.Session() as session:
            # Find all failed batches
            failed_batches = session.query(EntityBatchState).filter_by(
                project_key=self.project_key, status="failed"
            ).all()

            for batch in failed_batches:
                entity_type = batch.entity_type

                if entity_type not in failure_details:
                    failure_details[entity_type] = []

                failure_details[entity_type].append({
                    "batch_num": batch.batch_number,
                        "items_count": batch.items_count,
                        "processed_count": batch.processed_count,
                        "error": batch.error_message,
                        "updated_at": batch.last_updated.isoformat() if batch.last_updated else None,
                    })

        return failure_details

    def _get_timing_info(self) -> Dict[str, Union[float, str]]:
        """Get timing information about the migration."""
        timing_info = {}

        with self.Session() as session:
            state = session.query(MigrationState).filter_by(project_key=self.project_key).first()

            if state:
                # Get batch timing information
                extraction_batches = session.query(EntityBatchState).filter(
                    EntityBatchState.project_key == self.project_key,
                        EntityBatchState.entity_type.in_(
                        ["folders", "test_cases", "test_cycles", "test_executions"]
                    )
                ).all()

                transformation_batches = session.query(EntityBatchState).filter(
                    EntityBatchState.project_key == self.project_key,
                        EntityBatchState.entity_type.in_(
                        ["transformed_test_cases", "transformed_test_cycles",
                             "transformed_test_executions"]
                    )
                ).all()

                loading_batches = session.query(EntityBatchState).filter(
                    EntityBatchState.project_key == self.project_key,
                        EntityBatchState.entity_type.in_(
                        ["loaded_test_cases", "loaded_test_cycles",
                             "loaded_test_executions"]
                    )
                ).all()

                # Calculate extraction time
                if extraction_batches:
                    started_times = [b.started_at for b in extraction_batches if b.started_at]
                    completed_times = [b.completed_at for b in extraction_batches if b.completed_at]

                    if started_times and completed_times:
                        extraction_start = min(started_times)
                        extraction_end = max(completed_times)
                        extraction_seconds = (extraction_end - extraction_start).total_seconds()
                        timing_info["extraction_seconds"] = extraction_seconds
                        timing_info["extraction_formatted"] = self._format_duration(extraction_seconds)

                # Calculate transformation time
                if transformation_batches:
                    started_times = [b.started_at for b in transformation_batches if b.started_at]
                    completed_times = [b.completed_at for b in transformation_batches if b.completed_at]

                    if started_times and completed_times:
                        transform_start = min(started_times)
                        transform_end = max(completed_times)
                        transform_seconds = (transform_end - transform_start).total_seconds()
                        timing_info["transformation_seconds"] = transform_seconds
                        timing_info["transformation_formatted"] = self._format_duration(transform_seconds)

                # Calculate loading time
                if loading_batches:
                    started_times = [b.started_at for b in loading_batches if b.started_at]
                    completed_times = [b.completed_at for b in loading_batches if b.completed_at]

                    if started_times and completed_times:
                        loading_start = min(started_times)
                        loading_end = max(completed_times)
                        loading_seconds = (loading_end - loading_start).total_seconds()
                        timing_info["loading_seconds"] = loading_seconds
                        timing_info["loading_formatted"] = self._format_duration(loading_seconds)

                # Estimate total time based on all available timestamps
                all_batches = extraction_batches + transformation_batches + loading_batches
                if all_batches:
                    started_times = [b.started_at for b in all_batches if b.started_at]
                    completed_times = [b.completed_at for b in all_batches if b.completed_at]

                    if started_times and completed_times:
                        total_start = min(started_times)
                        total_end = max(completed_times)
                        total_seconds = (total_end - total_start).total_seconds()
                        timing_info["total_elapsed_seconds"] = total_seconds
                        timing_info["total_elapsed_formatted"] = self._format_duration(total_seconds)

        return timing_info

    def _get_validation_statistics(self) -> Dict[str, Any]:
        """Get statistics about validation issues.

        Returns:
            Dictionary containing validation issue statistics
        """
        validation_stats = {
            "issues_by_level": {},
                "issues_by_scope": {},
                "issues_by_phase": {},
                "critical_issues": 0,
                "error_issues": 0,
                "warning_issues": 0,
                "info_issues": 0,
                "total_issues": 0,
                "has_critical_issues": False,
            }

        with self.Session() as session:
            try:
                # Check if validation_issues table exists
                table_exists = False
                result = session.execute(text(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='validation_issues'
                    UNION
                    SELECT tablename FROM pg_catalog.pg_tables
                    WHERE schemaname='public' AND tablename='validation_issues'
                    """
                ))

                for row in result:
                    table_exists = True
                    break

                if not table_exists:
                    return validation_stats

                # Get total count of issues
                total_count = session.execute(text(
                    """
                    SELECT COUNT(*)
                    FROM validation_issues
                    WHERE project_key = :project_key AND resolved = 0
                    """
                ), {"project_key": self.project_key}).scalar() or 0

                validation_stats["total_issues"] = total_count

                # Get counts by level
                level_counts = session.execute(text(
                    """
                    SELECT level, COUNT(*) as count
                    FROM validation_issues
                    WHERE project_key = :project_key AND resolved = 0
                    GROUP BY level
                    """
                ), {"project_key": self.project_key}).fetchall()

                for level_count in level_counts:
                    level = level_count.level
                    count = level_count.count

                    validation_stats["issues_by_level"][level] = count

                    if level == "critical":
                        validation_stats["critical_issues"] = count
                        validation_stats["has_critical_issues"] = count > 0
                    elif level == "error":
                        validation_stats["error_issues"] = count
                    elif level == "warning":
                        validation_stats["warning_issues"] = count
                    elif level == "info":
                        validation_stats["info_issues"] = count

                # Get counts by scope
                scope_counts = session.execute(text(
                    """
                    SELECT scope, COUNT(*) as count
                    FROM validation_issues
                    WHERE project_key = :project_key AND resolved = 0
                    GROUP BY scope
                    """
                ), {"project_key": self.project_key}).fetchall()

                for scope_count in scope_counts:
                    validation_stats["issues_by_scope"][scope_count.scope] = scope_count.count

                # Get counts by phase
                phase_counts = session.execute(text(
                    """
                    SELECT phase, COUNT(*) as count
                    FROM validation_issues
                    WHERE project_key = :project_key AND resolved = 0
                    GROUP BY phase
                    """
                ), {"project_key": self.project_key}).fetchall()

                for phase_count in phase_counts:
                    validation_stats["issues_by_phase"][phase_count.phase] = phase_count.count

            except Exception as e:
                console.print(f"[bold red]Error retrieving validation statistics:[/bold red] {str(e)}")

        return validation_stats

    def _get_recent_validation_issues(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent validation issues.

        Args:
            limit: Maximum number of issues to return

        Returns:
            List of dictionaries containing validation issue details
        """
        issues = []

        with self.Session() as session:
            try:
                # Check if validation_issues table exists
                table_exists = False
                result = session.execute(text(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='validation_issues'
                    UNION
                    SELECT tablename FROM pg_catalog.pg_tables
                    WHERE schemaname='public' AND tablename='validation_issues'
                    """
                ))

                for row in result:
                    table_exists = True
                    break

                if not table_exists:
                    return issues

                # Get recent critical and error issues
                recent_issues = session.execute(text(
                    """
                    SELECT id, rule_id, level, message, entity_id, scope, phase, created_on, context
                    FROM validation_issues
                    WHERE project_key = :project_key
                    AND resolved = 0
                    ORDER BY created_on DESC
                    LIMIT :limit
                    """
                ), {"project_key": self.project_key, "limit": limit}).fetchall()

                for issue in recent_issues:
                    context = {}
                    if issue.context:
                        try:
                            context = json.loads(issue.context)
                        except:
                            pass

                    issues.append({
                        "id": issue.id,
                            "rule_id": issue.rule_id,
                            "level": issue.level,
                            "message": issue.message,
                            "entity_id": issue.entity_id,
                            "scope": issue.scope,
                            "phase": issue.phase,
                            "created_on": issue.created_on if isinstance(issue.created_on, str)
                                   else issue.created_on.isoformat(),
                            "context": context
                    })

            except Exception as e:
                console.print(f"[bold red]Error retrieving validation issues:[/bold red] {str(e)}")

        return issues

    def _get_performance_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get performance metrics for different entity types."""
        performance_metrics = {}
        timing_info = self._get_timing_info()
        entity_counts = self._get_entity_counts()

        # Calculate throughput (entities per second) for each phase if timing data exists
        if "extraction_seconds" in timing_info and timing_info["extraction_seconds"] > 0:
            total_extracted = sum(entity_counts["source"].values())
            extraction_throughput = total_extracted / timing_info["extraction_seconds"]

            performance_metrics["extraction"] = {
                "total_entities": total_extracted,
                    "processing_time_seconds": timing_info["extraction_seconds"],
                    "entities_per_second": extraction_throughput,
                    "entities_per_minute": extraction_throughput * 60
            }

        if "transformation_seconds" in timing_info and timing_info["transformation_seconds"] > 0:
            total_transformed = sum(entity_counts["transformed"].values())
            transformation_throughput = total_transformed / timing_info["transformation_seconds"]

            performance_metrics["transformation"] = {
                "total_entities": total_transformed,
                    "processing_time_seconds": timing_info["transformation_seconds"],
                    "entities_per_second": transformation_throughput,
                    "entities_per_minute": transformation_throughput * 60
            }

        if "loading_seconds" in timing_info and timing_info["loading_seconds"] > 0:
            total_loaded = sum(entity_counts["loaded"].values())
            loading_throughput = total_loaded / timing_info["loading_seconds"]

            performance_metrics["loading"] = {
                "total_entities": total_loaded,
                    "processing_time_seconds": timing_info["loading_seconds"],
                    "entities_per_second": loading_throughput,
                    "entities_per_minute": loading_throughput * 60
            }

        # Calculate overall throughput
        if "total_elapsed_seconds" in timing_info and timing_info["total_elapsed_seconds"] > 0:
            total_loaded = sum(entity_counts["loaded"].values())
            overall_throughput = total_loaded / timing_info["total_elapsed_seconds"]

            performance_metrics["overall"] = {
                "total_entities": total_loaded,
                    "processing_time_seconds": timing_info["total_elapsed_seconds"],
                    "entities_per_second": overall_throughput,
                    "entities_per_minute": overall_throughput * 60
            }

        return performance_metrics

    def _format_duration(self, seconds: float) -> str:
        """Format seconds into a human-readable duration string."""
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        elif minutes > 0:
            return f"{int(minutes)}m {int(seconds)}s"
        else:
            return f"{int(seconds)}s"

    def print_report(self, report: Optional[Dict[str, Any]] = None) -> None:
        """Print a formatted report to the console.

        Args:
            report: Optional report data. If not provided, it will be generated.
        """
        if report is None:
            report = self.generate_report()

        console.print(Panel.fit(f"[bold]Migration Report for {self.project_key}[/bold]"))
        console.print(f"Generated: {report['timestamp']}\n")

        # Print migration state
        state = report["migration_state"]
        if state:
            state_table = Table(title="Migration State")
            state_table.add_column("Phase")
            state_table.add_column("Status")
            state_table.add_column("Last Updated")

            state_table.add_row(
                "Extraction",
                    self._format_status(state["extraction_status"]),
                    state["updated_at"]
            )
            state_table.add_row(
                "Transformation",
                    self._format_status(state["transformation_status"]),
                    state["updated_at"]
            )
            state_table.add_row(
                "Loading",
                    self._format_status(state["loading_status"]),
                    state["updated_at"]
            )

            console.print(state_table)

            if state["error_message"]:
                console.print(f"[bold red]Error:[/bold red] {state['error_message']}\n")

        # Print entity counts
        entity_counts = report["entity_counts"]
        counts_table = Table(title="Entity Counts")
        counts_table.add_column("Entity Type")
        counts_table.add_column("Source Count")
        counts_table.add_column("Transformed")
        counts_table.add_column("Loaded")
        counts_table.add_column("Success Rate")

        entity_types = {
            "folders": "Folders",
                "test_cases": "Test Cases",
                "test_cycles": "Test Cycles",
                "test_executions": "Test Executions"
        }

        for entity_type, display_name in entity_types.items():
            source_count = entity_counts["source"].get(entity_type, 0)
            transformed_type = f"transformed_{entity_type}"
            loaded_type = f"loaded_{entity_type}"

            transformed_count = entity_counts["transformed"].get(transformed_type, 0)
            loaded_count = entity_counts["loaded"].get(loaded_type, 0)

            if source_count > 0:
                success_rate = f"{(loaded_count / source_count) * 100:.1f}%"
            else:
                success_rate = "N/A"

            counts_table.add_row(
                display_name,
                    str(source_count),
                    str(transformed_count),
                    str(loaded_count),
                    success_rate
            )

        console.print(counts_table)

        # Print batch statistics
        batch_stats = report["batch_statistics"]
        if batch_stats:
            batch_table = Table(title="Batch Processing Statistics")
            batch_table.add_column("Process Type")
            batch_table.add_column("Total Batches")
            batch_table.add_column("Completed")
            batch_table.add_column("Failed")
            batch_table.add_column("Pending")
            batch_table.add_column("Completion")

            for entity_type, stats in batch_stats.items():
                display_name = entity_type.replace("_", " ").title()
                completion = f"{stats['completion_percentage']:.1f}%"

                batch_table.add_row(
                    display_name,
                        str(stats["total_batches"]),
                        str(stats["completed_batches"]),
                        str(stats["failed_batches"]),
                        str(stats["pending_batches"]),
                        completion
                )

            console.print(batch_table)

        # Print timing information
        timing_info = report["timing_info"]
        if timing_info:
            timing_table = Table(title="Timing Information")
            timing_table.add_column("Phase")
            timing_table.add_column("Duration")

            timing_table.add_row("Extraction", timing_info.get("extraction_formatted", "N/A"))
            timing_table.add_row("Transformation", timing_info.get("transformation_formatted", "N/A"))
            timing_table.add_row("Loading", timing_info.get("loading_formatted", "N/A"))
            timing_table.add_row("Total Migration", timing_info.get("total_elapsed_formatted", "N/A"))

            console.print(timing_table)

        # Print performance metrics
        performance_metrics = report["performance_metrics"]
        if performance_metrics and "overall" in performance_metrics:
            perf_table = Table(title="Performance Metrics")
            perf_table.add_column("Phase")
            perf_table.add_column("Entities/Second")
            perf_table.add_column("Entities/Minute")

            for phase in ["extraction", "transformation", "loading", "overall"]:
                if phase in performance_metrics:
                    metrics = performance_metrics[phase]
                    entities_per_second = f"{metrics['entities_per_second']:.2f}"
                    entities_per_minute = f"{metrics['entities_per_minute']:.1f}"

                    perf_table.add_row(
                        phase.title(),
                            entities_per_second,
                            entities_per_minute
                    )

            console.print(perf_table)

        # Print validation statistics
        validation_stats = report["validation_statistics"]
        validation_issues = report["validation_issues"]

        if validation_stats["total_issues"] > 0:
            console.print(Panel.fit("[bold yellow]Validation Issues[/bold yellow]"))

            # Create validation summary table
            validation_table = Table(title="Validation Summary")
            validation_table.add_column("Level")
            validation_table.add_column("Count")
            validation_table.add_column("Percentage")

            total_issues = validation_stats["total_issues"]

            for level in ["critical", "error", "warning", "info"]:
                count = validation_stats.get(f"{level}_issues", 0)
                percentage = (count / total_issues) * 100 if total_issues > 0 else 0

                level_color = "red" if level == "critical" else "yellow" if level == "error" else "blue" if level == "warning" else "cyan"

                validation_table.add_row(
                    f"[{level_color}]{level.title()}[/{level_color}]",
                        str(count),
                        f"{percentage:.1f}%"
                )

            # Add total row
            validation_table.add_row(
                "[bold]Total[/bold]",
                    f"[bold]{total_issues}[/bold]",
                    "100.0%"
            )

            console.print(validation_table)

            # Print validation by phase and scope if available
            if validation_stats["issues_by_phase"] or validation_stats["issues_by_scope"]:
                detail_table = Table(title="Validation Details")
                detail_table.add_column("By Phase", style="cyan")
                detail_table.add_column("Count", style="cyan")
                detail_table.add_column("By Scope", style="magenta")
                detail_table.add_column("Count", style="magenta")

                # Combine phase and scope data
                phases = list(validation_stats["issues_by_phase"].items())
                scopes = list(validation_stats["issues_by_scope"].items())
                max_rows = max(len(phases), len(scopes))

                for i in range(max_rows):
                    phase_data = phases[i] if i < len(phases) else ("", "")
                    scope_data = scopes[i] if i < len(scopes) else ("", "")

                    phase_name = phase_data[0].replace("_", " ").title() if phase_data[0] else ""
                    phase_count = str(phase_data[1]) if phase_data[1] else ""

                    scope_name = scope_data[0].replace("_", " ").title() if scope_data[0] else ""
                    scope_count = str(scope_data[1]) if scope_data[1] else ""

                    detail_table.add_row(
                        phase_name, phase_count,
                            scope_name, scope_count
                    )

                console.print(detail_table)

            # Print recent validation issues
            if validation_issues:
                issues_table = Table(title="Recent Validation Issues")
                issues_table.add_column("Level")
                issues_table.add_column("Phase")
                issues_table.add_column("Scope")
                issues_table.add_column("Message")

                for issue in validation_issues[:5]:  # Show only first 5 issues
                    level = issue["level"]
                    level_color = "red" if level == "critical" else "yellow" if level == "error" else "blue" if level == "warning" else "cyan"

                    issues_table.add_row(
                        f"[{level_color}]{level.title()}[/{level_color}]",
                            issue["phase"].replace("_", " ").title(),
                            issue["scope"].replace("_", " ").title(),
                            issue["message"][:50] + ("..." if len(issue["message"]) > 50 else "")
                    )

                console.print(issues_table)

                if len(validation_issues) > 5:
                    console.print(f"... and {len(validation_issues) - 5} more validation issues\n")

        # Print failure summary
        failure_details = report["failure_details"]
        if failure_details:
            console.print(Panel.fit("[bold red]Failure Summary[/bold red]"))

            for entity_type, failures in failure_details.items():
                if failures:
                    console.print(f"[bold]{entity_type.replace('_', ' ').title()}[/bold]: {len(failures)} failed batches")

                    for i, failure in enumerate(failures[:3]):  # Show only first 3 failures
                        console.print(f"  Batch {failure['batch_num']}: {failure['error']}")

                    if len(failures) > 3:
                        console.print(f"  ... and {len(failures) - 3} more failures")

            console.print("")

        # Print success summary
        console.print(Panel.fit("[bold green]Migration Summary[/bold green]"))

        # Calculate overall success rate
        total_source = sum(entity_counts["source"].values())
        total_loaded = sum(
            count for entity_type, count in entity_counts["loaded"].items()
            if entity_type.startswith("loaded_")
        )

        if total_source > 0:
            overall_success = (total_loaded / total_source) * 100
            console.print(f"Overall Success Rate: [bold]{overall_success:.1f}%[/bold]")

        # Show time taken
        if "total_elapsed_formatted" in timing_info:
            console.print(f"Total Migration Time: [bold]{timing_info['total_elapsed_formatted']}[/bold]")

    def _format_status(self, status: Optional[str]) -> str:
        """Format the status with color."""
        if not status:
            return "[yellow]Not Started[/yellow]"

        if status == "completed":
            return "[green]Completed[/green]"
        elif status == "in_progress":
            return "[blue]In Progress[/blue]"
        elif status == "failed":
            return "[red]Failed[/red]"
        else:
            return status.replace("_", " ").title()

    def save_report_html(self, filename: str, report: Optional[Dict[str, Any]] = None) -> None:
        """Save the report as an HTML file with visualizations.

        Args:
            filename: The path to save the HTML report
            report: Optional report data. If not provided, it will be generated.
        """
        if report is None:
            report = self.generate_report()

        # Create report directory if it doesn't exist
        report_dir = os.path.dirname(filename)
        if report_dir and not os.path.exists(report_dir):
            os.makedirs(report_dir)

        # Create visualizations
        charts_html = self._generate_visualizations(report, os.path.dirname(filename))

        # Create a simple HTML report
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Migration Report for {self.project_key}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .completed {{ color: green; }}
                .in-progress {{ color: blue; }}
                .failed {{ color: red; }}
                .not-started {{ color: orange; }}
                .summary {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; }}
                .charts {{ display: flex; flex-wrap: wrap; justify-content: space-between; }}
                .chart {{ width: 48%; margin-bottom: 20px; }}
                @media (max-width: 768px) {{ .chart {{ width: 100%; }} }}
            </style>
        </head>
        <body>
            <h1>Migration Report for {self.project_key}</h1>
            <p>Generated: {report['timestamp']}</p>

            <h2>Migration State</h2>
            <table>
                <tr>
                    <th>Phase</th>
                    <th>Status</th>
                    <th>Last Updated</th>
                </tr>
        """

        # Add migration state
        state = report["migration_state"]
        if state:
            status_class = lambda s: s if s else "not-started"
            status_text = lambda s: s.replace("_", " ").title() if s else "Not Started"

            html += f"""
                <tr>
                    <td>Extraction</td>
                    <td class="{status_class(state['extraction_status'])}">{status_text(state['extraction_status'])}</td>
                    <td>{state['updated_at']}</td>
                </tr>
                <tr>
                    <td>Transformation</td>
                    <td class="{status_class(state['transformation_status'])}">{status_text(state['transformation_status'])}</td>
                    <td>{state['updated_at']}</td>
                </tr>
                <tr>
                    <td>Loading</td>
                    <td class="{status_class(state['loading_status'])}">{status_text(state['loading_status'])}</td>
                    <td>{state['updated_at']}</td>
                </tr>
            </table>
            """

            if state["error_message"]:
                html += f"""
                <div style="color: red; margin-bottom: 20px;">
                    <strong>Error:</strong> {state['error_message']}
                </div>
                """

        # Add entity counts
        entity_counts = report["entity_counts"]
        html += """
            <h2>Entity Counts</h2>
            <table>
                <tr>
                    <th>Entity Type</th>
                    <th>Source Count</th>
                    <th>Transformed</th>
                    <th>Loaded</th>
                    <th>Success Rate</th>
                </tr>
        """

        entity_types = {
            "folders": "Folders",
                "test_cases": "Test Cases",
                "test_cycles": "Test Cycles",
                "test_executions": "Test Executions"
        }

        for entity_type, display_name in entity_types.items():
            source_count = entity_counts["source"].get(entity_type, 0)
            transformed_type = f"transformed_{entity_type}"
            loaded_type = f"loaded_{entity_type}"

            transformed_count = entity_counts["transformed"].get(transformed_type, 0)
            loaded_count = entity_counts["loaded"].get(loaded_type, 0)

            if source_count > 0:
                success_rate = f"{(loaded_count / source_count) * 100:.1f}%"
            else:
                success_rate = "N/A"

            html += f"""
                <tr>
                    <td>{display_name}</td>
                    <td>{source_count}</td>
                    <td>{transformed_count}</td>
                    <td>{loaded_count}</td>
                    <td>{success_rate}</td>
                </tr>
            """

        html += """
            </table>

            <h2>Batch Processing Statistics</h2>
            <table>
                <tr>
                    <th>Process Type</th>
                    <th>Total Batches</th>
                    <th>Completed</th>
                    <th>Failed</th>
                    <th>Pending</th>
                    <th>Completion</th>
                </tr>
        """

        # Add batch statistics
        batch_stats = report["batch_statistics"]
        for entity_type, stats in batch_stats.items():
            display_name = entity_type.replace("_", " ").title()
            completion = f"{stats['completion_percentage']:.1f}%"

            html += f"""
                <tr>
                    <td>{display_name}</td>
                    <td>{stats['total_batches']}</td>
                    <td>{stats['completed_batches']}</td>
                    <td>{stats['failed_batches']}</td>
                    <td>{stats['pending_batches']}</td>
                    <td>{completion}</td>
                </tr>
            """

        html += """
            </table>

            <h2>Timing Information</h2>
            <table>
                <tr>
                    <th>Phase</th>
                    <th>Duration</th>
                </tr>
        """

        # Add timing information
        timing_info = report["timing_info"]
        if timing_info:
            html += f"""
                <tr>
                    <td>Extraction</td>
                    <td>{timing_info.get('extraction_formatted', 'N/A')}</td>
                </tr>
                <tr>
                    <td>Transformation</td>
                    <td>{timing_info.get('transformation_formatted', 'N/A')}</td>
                </tr>
                <tr>
                    <td>Loading</td>
                    <td>{timing_info.get('loading_formatted', 'N/A')}</td>
                </tr>
                <tr>
                    <td><strong>Total Migration</strong></td>
                    <td><strong>{timing_info.get('total_elapsed_formatted', 'N/A')}</strong></td>
                </tr>
            </table>
            """

        # Add performance metrics
        performance_metrics = report["performance_metrics"]
        if performance_metrics:
            html += """
            <h2>Performance Metrics</h2>
            <table>
                <tr>
                    <th>Phase</th>
                    <th>Entities/Second</th>
                    <th>Entities/Minute</th>
                </tr>
            """

            for phase in ["extraction", "transformation", "loading", "overall"]:
                if phase in performance_metrics:
                    metrics = performance_metrics[phase]
                    entities_per_second = f"{metrics['entities_per_second']:.2f}"
                    entities_per_minute = f"{metrics['entities_per_minute']:.1f}"

                    html += f"""
                    <tr>
                        <td>{phase.title()}</td>
                        <td>{entities_per_second}</td>
                        <td>{entities_per_minute}</td>
                    </tr>
                    """

            html += """
            </table>
            """

        # Add validation statistics
        validation_stats = report["validation_statistics"]
        validation_issues = report["validation_issues"]

        if validation_stats["total_issues"] > 0:
            html += """
            <h2 style="color: #f0ad4e;">Validation Issues</h2>

            <table>
                <tr>
                    <th>Level</th>
                    <th>Count</th>
                    <th>Percentage</th>
                </tr>
            """

            total_issues = validation_stats["total_issues"]

            # Define colors for each level
            level_colors = {
                "critical": "#dc3545",  # red
                "error": "#f0ad4e",     # yellow
                "warning": "#0275d8",   # blue
                "info": "#5bc0de"       # cyan
            }

            for level in ["critical", "error", "warning", "info"]:
                count = validation_stats.get(f"{level}_issues", 0)
                percentage = (count / total_issues) * 100 if total_issues > 0 else 0
                color = level_colors.get(level, "#000")

                html += f"""
                <tr>
                    <td><span style="color: {color}; font-weight: bold;">{level.title()}</span></td>
                    <td>{count}</td>
                    <td>{percentage:.1f}%</td>
                </tr>
                """

            # Add total row
            html += f"""
                <tr style="font-weight: bold;">
                    <td>Total</td>
                    <td>{total_issues}</td>
                    <td>100.0%</td>
                </tr>
            </table>
            """

            # Add validation details tables
            if validation_stats["issues_by_phase"] or validation_stats["issues_by_scope"]:
                html += """
                <div style="display: flex; justify-content: space-between; margin-top: 20px;">
                    <div style="width: 48%;">
                        <h3>Validation Issues by Phase</h3>
                        <table>
                            <tr>
                                <th>Phase</th>
                                <th>Count</th>
                            </tr>
                """

                for phase, count in validation_stats["issues_by_phase"].items():
                    phase_name = phase.replace("_", " ").title()
                    html += f"""
                    <tr>
                        <td>{phase_name}</td>
                        <td>{count}</td>
                    </tr>
                    """

                html += """
                        </table>
                    </div>

                    <div style="width: 48%;">
                        <h3>Validation Issues by Scope</h3>
                        <table>
                            <tr>
                                <th>Scope</th>
                                <th>Count</th>
                            </tr>
                """

                for scope, count in validation_stats["issues_by_scope"].items():
                    scope_name = scope.replace("_", " ").title()
                    html += f"""
                    <tr>
                        <td>{scope_name}</td>
                        <td>{count}</td>
                    </tr>
                    """

                html += """
                        </table>
                    </div>
                </div>
                """

            # Add recent validation issues
            if validation_issues:
                html += """
                <h3>Recent Validation Issues</h3>
                <table>
                    <tr>
                        <th>Level</th>
                        <th>Phase</th>
                        <th>Scope</th>
                        <th>Message</th>
                    </tr>
                """

                for issue in validation_issues[:10]:  # Show top 10 issues
                    level = issue["level"]
                    color = level_colors.get(level, "#000")

                    html += f"""
                    <tr>
                        <td><span style="color: {color}; font-weight: bold;">{level.title()}</span></td>
                        <td>{issue["phase"].replace("_", " ").title()}</td>
                        <td>{issue["scope"].replace("_", " ").title()}</td>
                        <td>{issue["message"][:100] + ("..." if len(issue["message"]) > 100 else "")}</td>
                    </tr>
                    """

                html += """
                </table>
                """

        # Add charts
        html += f"""
        <h2>Visualizations</h2>
        {charts_html}
        """

        # Add failure summary
        failure_details = report["failure_details"]
        if failure_details:
            html += """
            <h2 style="color: red;">Failure Summary</h2>
            """

            for entity_type, failures in failure_details.items():
                if failures:
                    html += f"""
                    <h3>{entity_type.replace('_', ' ').title()}: {len(failures)} failed batches</h3>
                    <ul>
                    """

                    for i, failure in enumerate(failures[:5]):  # Show only first 5 failures
                        html += f"""
                        <li>Batch {failure['batch_num']}: {failure['error']}</li>
                        """

                    if len(failures) > 5:
                        html += f"""
                        <li>... and {len(failures) - 5} more failures</li>
                        """

                    html += """
                    </ul>
                    """

        # Add success summary
        html += """
            <div class="summary">
                <h2>Migration Summary</h2>
        """

        # Calculate overall success rate
        total_source = sum(entity_counts["source"].values())
        total_loaded = sum(
            count for entity_type, count in entity_counts["loaded"].items()
            if entity_type.startswith("loaded_")
        )

        if total_source > 0:
            overall_success = (total_loaded / total_source) * 100
            html += f"""
                <p>Overall Success Rate: <strong>{overall_success:.1f}%</strong></p>
            """

        # Show time taken
        if "total_elapsed_formatted" in timing_info:
            html += f"""
                <p>Total Migration Time: <strong>{timing_info['total_elapsed_formatted']}</strong></p>
            """

        html += """
            </div>
        </body>
        </html>
        """

        # Write to file
        with open(filename, "w") as f:
            f.write(html)

        console.print(f"HTML report saved to [bold]{filename}[/bold]")

    def _generate_visualizations(self, report: Dict[str, Any], output_dir: str) -> str:
        """Generate data visualizations for the report.

        Args:
            report: The report data
            output_dir: Directory to save visualization images

        Returns:
            HTML fragment with embedded visualizations
        """
        # Create directory for charts if it doesn't exist
        charts_dir = os.path.join(output_dir, "charts")
        if not os.path.exists(charts_dir):
            os.makedirs(charts_dir)

        charts_html = '<div class="charts">'

        # Generate validation issues chart if validation data exists
        validation_stats = report["validation_statistics"]
        if validation_stats["total_issues"] > 0:
            validation_chart_path = self._create_validation_chart(validation_stats, charts_dir)
            charts_html += f"""
            <div class="chart">
                <h3>Validation Issues by Level</h3>
                <img src="{validation_chart_path}" alt="Validation Issues" width="100%">
            </div>
            """

        # Generate progress bar chart
        entity_counts = report["entity_counts"]
        entity_types = {
            "folders": "Folders",
                "test_cases": "Test Cases",
                "test_cycles": "Test Cycles",
                "test_executions": "Test Executions"
        }

        # Prepare data for progress chart
        progress_data = []
        for entity_type, display_name in entity_types.items():
            source_count = entity_counts["source"].get(entity_type, 0)
            if source_count == 0:
                continue

            transformed_type = f"transformed_{entity_type}"
            loaded_type = f"loaded_{entity_type}"

            transformed_count = entity_counts["transformed"].get(transformed_type, 0)
            loaded_count = entity_counts["loaded"].get(loaded_type, 0)

            progress_data.append({
                "Entity Type": display_name,
                    "Source": source_count,
                    "Transformed": transformed_count,
                    "Loaded": loaded_count
            })

        if progress_data:
            progress_chart_path = self._create_progress_chart(progress_data, charts_dir)
            charts_html += f"""
            <div class="chart">
                <h3>Migration Progress</h3>
                <img src="{progress_chart_path}" alt="Migration Progress" width="100%">
            </div>
            """

        # Generate phase timing chart
        timing_info = report["timing_info"]
        if timing_info:
            timing_data = []

            if "extraction_seconds" in timing_info:
                timing_data.append({
                    "Phase": "Extraction",
                        "Seconds": timing_info["extraction_seconds"]
                })

            if "transformation_seconds" in timing_info:
                timing_data.append({
                    "Phase": "Transformation",
                        "Seconds": timing_info["transformation_seconds"]
                })

            if "loading_seconds" in timing_info:
                timing_data.append({
                    "Phase": "Loading",
                        "Seconds": timing_info["loading_seconds"]
                })

            if timing_data:
                timing_chart_path = self._create_timing_chart(timing_data, charts_dir)
                charts_html += f"""
                <div class="chart">
                    <h3>Phase Timing</h3>
                    <img src="{timing_chart_path}" alt="Phase Timing" width="100%">
                </div>
                """

        # Generate batch status chart
        batch_stats = report["batch_statistics"]
        if batch_stats:
            batch_data = []

            for entity_type, stats in batch_stats.items():
                display_name = entity_type.replace("_", " ").title()

                batch_data.append({
                    "Process Type": display_name,
                        "Completed": stats["completed_batches"],
                        "Failed": stats["failed_batches"],
                        "Pending": stats["pending_batches"]
                })

            if batch_data:
                batch_chart_path = self._create_batch_status_chart(batch_data, charts_dir)
                charts_html += f"""
                <div class="chart">
                    <h3>Batch Status</h3>
                    <img src="{batch_chart_path}" alt="Batch Status" width="100%">
                </div>
                """

        # Generate performance chart
        performance_metrics = report["performance_metrics"]
        if performance_metrics:
            perf_data = []

            for phase in ["extraction", "transformation", "loading", "overall"]:
                if phase in performance_metrics:
                    metrics = performance_metrics[phase]

                    perf_data.append({
                        "Phase": phase.title(),
                            "Entities/Second": metrics["entities_per_second"],
                            "Entities/Minute": metrics["entities_per_minute"]
                    })

            if perf_data:
                perf_chart_path = self._create_performance_chart(perf_data, charts_dir)
                charts_html += f"""
                <div class="chart">
                    <h3>Performance Metrics</h3>
                    <img src="{perf_chart_path}" alt="Performance Metrics" width="100%">
                </div>
                """

        charts_html += '</div>'
        return charts_html

    def _create_progress_chart(self, data: List[Dict[str, Any]], output_dir: str) -> str:
        """Create a progress bar chart showing migration progress.

        Args:
            data: List of dictionaries with entity type and counts
            output_dir: Directory to save the chart

        Returns:
            Relative path to the chart image
        """
        df = pd.DataFrame(data)

        # Calculate percentages
        for idx, row in df.iterrows():
            df.at[idx, "Transformed %"] = (row["Transformed"] / row["Source"]) * 100 if row["Source"] > 0 else 0
            df.at[idx, "Loaded %"] = (row["Loaded"] / row["Source"]) * 100 if row["Source"] > 0 else 0

        # Create the chart
        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot the bars
        bar_width = 0.35
        x = range(len(df))

        ax.barh(x, df["Transformed %"], bar_width, label="Transformed", color="skyblue")
        ax.barh([i + bar_width for i in x], df["Loaded %"], bar_width, label="Loaded", color="orange")

        # Customize the chart
        ax.set_yticks([i + bar_width/2 for i in x])
        ax.set_yticklabels(df["Entity Type"])
        ax.set_xlabel("Completion Percentage")
        ax.set_xlim(0, 100)
        ax.set_title("Migration Progress by Entity Type")
        ax.legend()

        # Add percentage labels
        for i, p in enumerate(df["Transformed %"]):
            ax.annotate(f"{p:.1f}%", xy=(p + 1, i), va="center")

        for i, p in enumerate(df["Loaded %"]):
            ax.annotate(f"{p:.1f}%", xy=(p + 1, i + bar_width), va="center")

        plt.tight_layout()

        # Save the chart
        chart_path = os.path.join(output_dir, "progress_chart.png")
        plt.savefig(chart_path)
        plt.close(fig)

        return os.path.join("charts", "progress_chart.png")

    def _create_timing_chart(self, data: List[Dict[str, Any]], output_dir: str) -> str:
        """Create a bar chart showing timing information.

        Args:
            data: List of dictionaries with phase and timing data
            output_dir: Directory to save the chart

        Returns:
            Relative path to the chart image
        """
        df = pd.DataFrame(data)

        # Create the chart
        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot the bars
        bars = ax.bar(df["Phase"], df["Seconds"], color="lightgreen")

        # Customize the chart
        ax.set_ylabel("Seconds")
        ax.set_title("Processing Time by Phase")

        # Add time labels
        for bar in bars:
            height = bar.get_height()
            ax.annotate(self._format_duration(height),
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),  # 3 points vertical offset
                       textcoords="offset points",
                           ha='center', va='bottom')

        plt.tight_layout()

        # Save the chart
        chart_path = os.path.join(output_dir, "timing_chart.png")
        plt.savefig(chart_path)
        plt.close(fig)

        return os.path.join("charts", "timing_chart.png")

    def _create_batch_status_chart(self, data: List[Dict[str, Any]], output_dir: str) -> str:
        """Create a stacked bar chart showing batch status.

        Args:
            data: List of dictionaries with process type and batch status counts
            output_dir: Directory to save the chart

        Returns:
            Relative path to the chart image
        """
        df = pd.DataFrame(data)

        # Create the chart
        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot the stacked bars
        process_types = df["Process Type"]
        completed = df["Completed"]
        failed = df["Failed"]
        pending = df["Pending"]

        ax.barh(process_types, completed, color="green", label="Completed")
        ax.barh(process_types, failed, left=completed, color="red", label="Failed")
        ax.barh(process_types, pending, left=completed + failed, color="orange", label="Pending")

        # Customize the chart
        ax.set_xlabel("Number of Batches")
        ax.set_title("Batch Status by Process Type")
        ax.legend(loc="best")

        # Add count labels
        for i, (comp, fail, pend) in enumerate(zip(completed, failed, pending)):
            total = comp + fail + pend
            if total > 0:
                ax.annotate(f"{comp} of {total}",
                               xy=(comp/2, i),
                               ha='center', va='center',
                               color='white' if comp > 3 else 'black')

        plt.tight_layout()

        # Save the chart
        chart_path = os.path.join(output_dir, "batch_status_chart.png")
        plt.savefig(chart_path)
        plt.close(fig)

        return os.path.join("charts", "batch_status_chart.png")

    def _create_validation_chart(self, validation_stats: Dict[str, Any], output_dir: str) -> str:
        """Create a pie chart showing validation issues by level.

        Args:
            validation_stats: Dictionary with validation statistics
            output_dir: Directory to save the chart

        Returns:
            Relative path to the chart image
        """
        # Prepare data
        levels = ["critical", "error", "warning", "info"]
        labels = ["Critical", "Error", "Warning", "Info"]
        counts = [validation_stats.get(f"{level}_issues", 0) for level in levels]

        # Only include non-zero values
        non_zero_indices = [i for i, count in enumerate(counts) if count > 0]
        filtered_labels = [labels[i] for i in non_zero_indices]
        filtered_counts = [counts[i] for i in non_zero_indices]

        if not filtered_counts:
            # No validation issues, create dummy chart
            filtered_labels = ["No Issues"]
            filtered_counts = [1]

        # Create the chart
        fig, ax = plt.subplots(figsize=(10, 6))

        # Define colors for each level
        colors = ["#dc3545", "#f0ad4e", "#0275d8", "#5bc0de"]  # red, yellow, blue, cyan
        filtered_colors = [colors[i] for i in non_zero_indices] if non_zero_indices else ["#eeeeee"]

        # Create the pie chart
        wedges, texts, autotexts = ax.pie(
            filtered_counts,
                labels=filtered_labels,
                colors=filtered_colors,
                autopct='%1.1f%%',
                startangle=90,
                wedgeprops={'edgecolor': 'white', 'linewidth': 1}
        )

        # Style the text
        for text in texts:
            text.set_fontsize(12)
        for autotext in autotexts:
            autotext.set_fontsize(10)
            autotext.set_color('white')

        # Equal aspect ratio ensures the pie chart is circular
        ax.axis('equal')
        ax.set_title('Validation Issues by Level', fontsize=14)

        # Add total count annotation
        total_issues = validation_stats.get("total_issues", 0)
        if total_issues > 0:
            ax.annotate(
                f"Total: {total_issues} issues",
                    xy=(0, 0),
                    xytext=(0, -30),
                    textcoords="offset points",
                    ha='center',
                    va='center',
                    fontsize=12,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8)
            )

        plt.tight_layout()

        # Save the chart
        chart_path = os.path.join(output_dir, "validation_chart.png")
        plt.savefig(chart_path)
        plt.close(fig)

        return os.path.join("charts", "validation_chart.png")

    def _create_performance_chart(self, data: List[Dict[str, Any]], output_dir: str) -> str:
        """Create a bar chart showing performance metrics.

        Args:
            data: List of dictionaries with performance metrics by phase
            output_dir: Directory to save the chart

        Returns:
            Relative path to the chart image
        """
        df = pd.DataFrame(data)

        # Create the chart
        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot the bars for entities per minute (more readable scale)
        bars = ax.bar(df["Phase"], df["Entities/Minute"], color="purple")

        # Customize the chart
        ax.set_ylabel("Entities per Minute")
        ax.set_title("Migration Performance by Phase")

        # Add rate labels
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f"{height:.1f}",
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom')

        plt.tight_layout()

        # Save the chart
        chart_path = os.path.join(output_dir, "performance_chart.png")
        plt.savefig(chart_path)
        plt.close(fig)

        return os.path.join("charts", "performance_chart.png")

    def save_report_json(self, filename: str, report: Optional[Dict[str, Any]] = None) -> None:
        """Save the report as a JSON file.

        Args:
            filename: The path to save the JSON report
            report: Optional report data. If not provided, it will be generated.
        """
        if report is None:
            report = self.generate_report()

        # Create report directory if it doesn't exist
        report_dir = os.path.dirname(filename)
        if report_dir and not os.path.exists(report_dir):
            os.makedirs(report_dir)

        with open(filename, "w") as f:
            json.dump(report, f, indent=2)

        console.print(f"JSON report saved to [bold]{filename}[/bold]")

    def save_report_csv(self, filename: str, report: Optional[Dict[str, Any]] = None) -> None:
        """Save the entity counts and batch statistics as CSV files.

        Args:
            filename: Base filename for CSV reports (without extension)
            report: Optional report data. If not provided, it will be generated.
        """
        if report is None:
            report = self.generate_report()

        # Create report directory if it doesn't exist
        report_dir = os.path.dirname(filename)
        if report_dir and not os.path.exists(report_dir):
            os.makedirs(report_dir)

        # Save entity counts
        base_name = os.path.splitext(filename)[0]
        entity_file = f"{base_name}_entities.csv"
        batch_file = f"{base_name}_batches.csv"

        # Create entity counts DataFrame
        entity_data = []
        entity_counts = report["entity_counts"]

        entity_types = {
            "folders": "Folders",
                "test_cases": "Test Cases",
                "test_cycles": "Test Cycles",
                "test_executions": "Test Executions"
        }

        for entity_type, display_name in entity_types.items():
            source_count = entity_counts["source"].get(entity_type, 0)
            transformed_type = f"transformed_{entity_type}"
            loaded_type = f"loaded_{entity_type}"

            transformed_count = entity_counts["transformed"].get(transformed_type, 0)
            loaded_count = entity_counts["loaded"].get(loaded_type, 0)

            if source_count > 0:
                success_rate = (loaded_count / source_count) * 100
            else:
                success_rate = 0.0

            entity_data.append({
                "Entity Type": display_name,
                    "Source Count": source_count,
                    "Transformed Count": transformed_count,
                    "Loaded Count": loaded_count,
                    "Success Rate (%)": success_rate,
                })

        # Save entity counts
        pd.DataFrame(entity_data).to_csv(entity_file, index=False)
        console.print(f"Entity counts saved to [bold]{entity_file}[/bold]")

        # Create batch statistics DataFrame
        batch_data = []
        batch_stats = report["batch_statistics"]

        for entity_type, stats in batch_stats.items():
            display_name = entity_type.replace("_", " ").title()

            batch_data.append({
                "Process Type": display_name,
                    "Total Batches": stats["total_batches"],
                    "Completed Batches": stats["completed_batches"],
                    "Failed Batches": stats["failed_batches"],
                    "Pending Batches": stats["pending_batches"],
                    "Total Items": stats["total_items"],
                    "Processed Items": stats["processed_items"],
                    "Completion (%)": stats["completion_percentage"],
                })

        # Save batch statistics
        pd.DataFrame(batch_data).to_csv(batch_file, index=False)
        console.print(f"Batch statistics saved to [bold]{batch_file}[/bold]")


def parse_db_url(db_type: str, host: Optional[str] = None, port: Optional[int] = None,
                    name: Optional[str] = None, user: Optional[str] = None,
                    password: Optional[str] = None, path: Optional[str] = None) -> str:
    """Parse database connection parameters into a SQLAlchemy URL.

    Args:
        db_type: Database type (sqlite or postgresql)
        host: Database host (for postgresql)
        port: Database port (for postgresql)
        name: Database name (for postgresql)
        user: Database user (for postgresql)
        password: Database password (for postgresql)
        path: Database file path (for sqlite)

    Returns:
        SQLAlchemy database URL
    """
    if db_type == "sqlite":
        if not path:
            path = "ztoq_data.db"
        return f"sqlite:///{path}"
    elif db_type == "postgresql":
        if not all([host, name, user, password]):
            raise ValueError("PostgreSQL connection requires host, name, user, and password")
        port_str = f":{port}" if port else ""
        return f"postgresql://{user}:{password}@{host}{port_str}/{name}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def main() -> None:
    """Main entry point for the migration report command-line tool."""
    parser = argparse.ArgumentParser(description="Generate a migration report")

    # Database connection parameters
    parser.add_argument("--db-type", choices=["sqlite", "postgresql"], default="sqlite",
                           help="Database type (sqlite or postgresql)")
    parser.add_argument("--db-path", help="Path to SQLite database file")
    parser.add_argument("--db-host", help="PostgreSQL database host")
    parser.add_argument("--db-port", type=int, help="PostgreSQL database port")
    parser.add_argument("--db-name", help="PostgreSQL database name")
    parser.add_argument("--db-user", help="PostgreSQL database user")
    parser.add_argument("--db-password", help="PostgreSQL database password")

    # Report parameters
    parser.add_argument("--project-key", required=True, help="Zephyr project key")
    parser.add_argument("--output-format", choices=["console", "html", "json", "csv", "all"],
                           default="console", help="Output format for the report")
    parser.add_argument("--output-file", help="Output file path (required for html, json, csv formats)")

    args = parser.parse_args()

    # Check environment variables for database connection if not provided as arguments
    if args.db_type == "postgresql":
        args.db_host = args.db_host or os.environ.get("ZTOQ_DB_HOST")
        args.db_port = args.db_port or int(os.environ.get("ZTOQ_DB_PORT", "5432"))
        args.db_name = args.db_name or os.environ.get("ZTOQ_DB_NAME")
        args.db_user = args.db_user or os.environ.get("ZTOQ_DB_USER")
        args.db_password = args.db_password or os.environ.get("ZTOQ_DB_PASSWORD")
    else:  # sqlite
        args.db_path = args.db_path or os.environ.get("ZTOQ_DB_PATH", "ztoq_data.db")

    # Create database URL
    try:
        db_url = parse_db_url(
            db_type=args.db_type,
                host=args.db_host,
                port=args.db_port,
                name=args.db_name,
                user=args.db_user,
                password=args.db_password,
                path=args.db_path
        )
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)

    # Check output file is provided for file-based outputs
    if args.output_format in ["html", "json", "csv"] and not args.output_file:
        console.print("[bold red]Error:[/bold red] --output-file is required for html, json, and csv formats")
        sys.exit(1)

    try:
        # Create report generator
        report_generator = MigrationReportGenerator(db_url, args.project_key)

        # Generate the report once and reuse for all output formats
        with Progress() as progress:
            task = progress.add_task("Generating migration report...", total=100)
            report = report_generator.generate_report()
            progress.update(task, completed=100)

        # Output based on selected format
        if args.output_format == "console" or args.output_format == "all":
            report_generator.print_report(report)

        if args.output_format == "html" or args.output_format == "all":
            report_generator.save_report_html(args.output_file, report)

        if args.output_format == "json" or args.output_format == "all":
            json_file = args.output_file
            if args.output_format == "all":
                base_name = os.path.splitext(args.output_file)[0]
                json_file = f"{base_name}.json"
            report_generator.save_report_json(json_file, report)

        if args.output_format == "csv" or args.output_format == "all":
            csv_file = args.output_file
            if args.output_format == "all":
                base_name = os.path.splitext(args.output_file)[0]
                csv_file = f"{base_name}.csv"
            report_generator.save_report_csv(csv_file, report)

    except Exception as e:
        console.print(f"[bold red]Error generating report:[/bold red] {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
