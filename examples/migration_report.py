#!/usr/bin/env python3
"""
Example demonstrating how to generate a migration report.

This example shows how to:
1. Connect to the migration database
2. Extract migration statistics
3. Generate a detailed report
4. Export the report to HTML and JSON

You can run this with:
    poetry run python examples/migration_report.py
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import ztoq modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

    def generate_report(self):
        """Generate a comprehensive migration report."""
        report = {
            "project_key": self.project_key,
            "timestamp": datetime.now().isoformat(),
            "migration_state": self._get_migration_state(),
            "entity_counts": self._get_entity_counts(),
            "batch_statistics": self._get_batch_statistics(),
            "failure_details": self._get_failure_details(),
            "timing_info": self._get_timing_info(),
        }

        return report

    def _get_migration_state(self):
        """Get the current migration state."""
        with self.Session() as session:
            state = session.query(MigrationState).filter_by(project_key=self.project_key).first()
            if state:
                return {
                    "extraction_status": state.extraction_status,
                    "transformation_status": state.transformation_status,
                    "loading_status": state.loading_status,
                    "error_message": state.error_message,
                    "created_at": state.last_updated.isoformat() if state.last_updated else None,
                    "updated_at": state.last_updated.isoformat() if state.last_updated else None,
                }
            return None

    def _get_entity_counts(self):
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

    def _get_batch_statistics(self):
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
                    pending_batches = sum(1 for batch in batches if batch.status in ["not_started", "in_progress"])

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

    def _get_failure_details(self):
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

    def _get_timing_info(self):
        """Get timing information about the migration."""
        timing_info = {}

        with self.Session() as session:
            state = session.query(MigrationState).filter_by(project_key=self.project_key).first()

            if state and state.last_updated:
                # Get batch timing information
                extraction_batches = session.query(EntityBatchState).filter(
                    EntityBatchState.project_key == self.project_key,
                    EntityBatchState.entity_type.in_(["folders", "test_cases", "test_cycles", "test_executions"])
                ).all()

                transformation_batches = session.query(EntityBatchState).filter(
                    EntityBatchState.project_key == self.project_key,
                    EntityBatchState.entity_type.in_(["transformed_test_cases", "transformed_test_cycles",
                                               "transformed_test_executions"])
                ).all()

                loading_batches = session.query(EntityBatchState).filter(
                    EntityBatchState.project_key == self.project_key,
                    EntityBatchState.entity_type.in_(["loaded_test_cases", "loaded_test_cycles",
                                               "loaded_test_executions"])
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

    def _format_duration(self, seconds):
        """Format seconds into a human-readable duration string."""
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        elif minutes > 0:
            return f"{int(minutes)}m {int(seconds)}s"
        else:
            return f"{int(seconds)}s"

    def print_report(self, report=None):
        """Print a formatted report to the console."""
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

    def _format_status(self, status):
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

    def save_report_html(self, filename, report=None):
        """Save the report as an HTML file."""
        if report is None:
            report = self.generate_report()

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
                .summary {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; }}
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

    def save_report_json(self, filename, report=None):
        """Save the report as a JSON file."""
        if report is None:
            report = self.generate_report()

        with open(filename, "w") as f:
            json.dump(report, f, indent=2)

        console.print(f"JSON report saved to [bold]{filename}[/bold]")


class EntityMappingModel:
    """Dummy model for entity mappings used in the example."""
    def __init__(self, project_key, mapping_type, source_id, target_id):
        self.project_key = project_key
        self.mapping_type = mapping_type
        self.source_id = source_id
        self.target_id = target_id


def create_example_database():
    """Create a sample SQLite database with migration data for the example."""
    db_path = "migration_report_example.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        # Create migration state
        state = MigrationState(
            project_key="DEMO",
            extraction_status="completed",
            transformation_status="completed",
            loading_status="in_progress",
            error_message=None,
            last_updated=datetime.utcnow(),
        )
        session.add(state)

        # Create entity mappings (using raw SQL since we don't have a model)
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS entity_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_key VARCHAR(50) NOT NULL,
                mapping_type VARCHAR(50) NOT NULL,
                source_id VARCHAR(50) NOT NULL,
                target_id VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Insert sample entity mappings
        mapping_counts = {
            "folder_to_module": 12,
            "testcase_to_testcase": 150,
            "cycle_to_cycle": 8,
            "execution_to_run": 87,
        }

        for mapping_type, count in mapping_counts.items():
            for i in range(count):
                session.execute(text("""
                    INSERT INTO entity_mappings
                    (project_key, mapping_type, source_id, target_id)
                    VALUES (:project_key, :mapping_type, :source_id, :target_id)
                """), {
                    "project_key": "DEMO",
                    "mapping_type": mapping_type,
                    "source_id": f"src-{i}",
                    "target_id": f"tgt-{i}"
                })

        # Create entity batches
        batch_data = [
            # Entity type, total batches, items per batch, failed batches
            ("folders", 2, 6, 0),
            ("test_cases", 15, 10, 2),
            ("test_cycles", 1, 8, 0),
            ("test_executions", 9, 10, 1),
            ("transformed_test_cases", 15, 10, 1),
            ("transformed_test_cycles", 1, 8, 0),
            ("transformed_test_executions", 9, 10, 0),
            ("loaded_test_cases", 15, 10, 3),
            ("loaded_test_cycles", 1, 8, 0),
            ("loaded_test_executions", 5, 10, 0),  # Only some have been loaded so far
        ]

        now = datetime.utcnow()

        for entity_type, total_batches, items_per_batch, failed_batches in batch_data:
            for batch_num in range(total_batches):
                # Determine status
                if batch_num < failed_batches:
                    status = "failed"
                    error = f"Error processing {entity_type} batch {batch_num}"
                    processed_count = items_per_batch // 2  # Half processed before failure
                    started_at = now
                    completed_at = None
                elif entity_type.startswith("loaded_") and batch_num >= total_batches - 4:
                    status = "not_started"  # Some loading batches are still pending
                    error = None
                    processed_count = 0
                    started_at = None
                    completed_at = None
                else:
                    status = "completed"
                    error = None
                    processed_count = items_per_batch
                    # Create timestamps with appropriate offsets - older batches started earlier
                    started_at = datetime(now.year, now.month, now.day, now.hour - 2,
                                         now.minute - total_batches + batch_num)
                    completed_at = datetime(now.year, now.month, now.day, now.hour - 2,
                                           now.minute - total_batches + batch_num + 1)

                batch = EntityBatchState(
                    project_key="DEMO",
                    entity_type=entity_type,
                    batch_number=batch_num,
                    total_batches=total_batches,
                    items_count=items_per_batch,
                    processed_count=processed_count,
                    status=status,
                    error_message=error,
                    started_at=started_at,
                    completed_at=completed_at,
                    last_updated=now,
                )
                session.add(batch)

        session.commit()

    return db_path


def run_report_example():
    """Run the migration report example."""
    console.print("[bold green]Migration Report Example[/bold green]")
    console.print("This example shows how to generate a comprehensive migration report.\n")

    # Create a sample database
    with Progress() as progress:
        task = progress.add_task("Creating sample database...", total=100)
        db_path = create_example_database()
        progress.update(task, completed=100)

    # Create the report generator
    report_generator = MigrationReportGenerator(f"sqlite:///{db_path}", "DEMO")

    # Generate the report
    with Progress() as progress:
        task = progress.add_task("Generating migration report...", total=100)
        report = report_generator.generate_report()
        progress.update(task, completed=100)

    # Print the report
    report_generator.print_report(report)

    # Save as HTML and JSON
    report_generator.save_report_html("migration_report.html", report)
    report_generator.save_report_json("migration_report.json", report)

    console.print("\n[bold green]Report generation complete![/bold green]")
    console.print("This example demonstrates how to generate a detailed migration report.")
    console.print("In a real application, connect to your migration database to generate reports.")


if __name__ == "__main__":
    run_report_example()
