"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
CLI commands for the ETL migration workflow orchestration.

This module provides CLI commands for managing the ETL migration workflow,
including running, resuming, and monitoring migrations.
"""

import asyncio
import logging
import os
import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional
from io import StringIO
import sys
import shutil
import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from ztoq.database_factory import DatabaseType, get_database_manager
from ztoq.models import ZephyrConfig
from ztoq.qtest_models import QTestConfig
from ztoq.workflow_orchestrator import WorkflowConfig, WorkflowOrchestrator, WorkflowPhase

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger("ztoq.workflow_cli")

# Create Typer app
workflow_app = typer.Typer(help="ETL Workflow Orchestration Commands")
console = Console()


class OutputFormat(str, Enum):
    """Output format for reports."""

    JSON = "json"
    HTML = "html"
    TEXT = "text"


@workflow_app.command("run")
def run_workflow(
    # Project information
    project_key: str = typer.Option(..., help="Zephyr project key to migrate"),
    # Database configuration
    db_type: DatabaseType = typer.Option(
        DatabaseType.SQLITE, help="Database type (sqlite or postgresql)"
    ),
    db_path: Optional[Path] = typer.Option(
        None, help="Path to SQLite database file (for SQLite only)"
    ),
    host: Optional[str] = typer.Option(None, help="PostgreSQL host (for PostgreSQL only)"),
    port: Optional[int] = typer.Option(None, help="PostgreSQL port (for PostgreSQL only)"),
    username: Optional[str] = typer.Option(None, help="PostgreSQL username (for PostgreSQL only)"),
    password: Optional[str] = typer.Option(None, help="PostgreSQL password (for PostgreSQL only)"),
    database: Optional[str] = typer.Option(
        None, help="PostgreSQL database name (for PostgreSQL only)"
    ),
    # Zephyr configuration
    zephyr_base_url: str = typer.Option(..., help="Zephyr Scale API base URL"),
    zephyr_api_token: str = typer.Option(..., help="Zephyr Scale API token"),
    # qTest configuration
    qtest_base_url: str = typer.Option(..., help="qTest API base URL"),
    qtest_username: str = typer.Option(..., help="qTest username"),
    qtest_password: str = typer.Option(..., help="qTest password"),
    qtest_project_id: int = typer.Option(..., help="qTest project ID"),
    # Workflow options
    phases: List[WorkflowPhase] = typer.Option(
        [WorkflowPhase.ALL], help="Phases to run (extract, transform, load, validate, all)"
    ),
    batch_size: int = typer.Option(50, help="Number of items to process in a batch"),
    max_workers: int = typer.Option(
        5, help="Maximum number of concurrent workers for parallel processing"
    ),
    timeout: int = typer.Option(3600, help="Timeout in seconds for each phase"),
    no_validation: bool = typer.Option(False, help="Disable validation"),
    # Output options
    output_dir: Optional[Path] = typer.Option(
        None, help="Directory for output files (reports, logs)"
    ),
    attachments_dir: Optional[Path] = typer.Option(
        None, help="Directory for storing attachments"
    ),
    report_format: OutputFormat = typer.Option(
        OutputFormat.JSON, help="Report output format (json, html, text)"
    ),
):
    """
    Run the ETL migration workflow.

    This command orchestrates the ETL (Extract, Transform, Load) workflow
    for migrating data from Zephyr Scale to qTest, with optional validation.
    """
    try:
        # Create configuration
        zephyr_config = ZephyrConfig(
            base_url=zephyr_base_url,
            api_token=zephyr_api_token,
            project_key=project_key,
        )

        qtest_config = QTestConfig(
            base_url=qtest_base_url,
            username=qtest_username,
            password=qtest_password,
            project_id=qtest_project_id,
        )

        workflow_config = WorkflowConfig(
            project_key=project_key,
            db_type=db_type.value,
            db_path=str(db_path) if db_path else None,
            pg_host=host,
            pg_port=port,
            pg_username=username,
            pg_password=password,
            pg_database=database,
            batch_size=batch_size,
            max_workers=max_workers,
            validation_enabled=not no_validation,
            attachments_dir=attachments_dir,
            output_dir=output_dir,
            timeout=timeout,
            zephyr_config=zephyr_config,
            qtest_config=qtest_config,
        )

        # Create orchestrator
        orchestrator = WorkflowOrchestrator(workflow_config)

        # Set up progress reporting
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # Run workflow
            console.print(f"Starting workflow for project {project_key}...")
            results = asyncio.run(orchestrator.run_workflow(
                phases=[p.value for p in phases],
                progress=progress,
            ))

            # Print summary
            console.print("\n✓ Workflow completed", style="green bold")

            # Print workflow status
            orchestrator.print_workflow_status(console=console)

            # Generate report if output directory is specified
            if output_dir:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_filename = f"migration_report_{project_key}_{timestamp}.{report_format.value}"
                report_path = Path(output_dir) / report_filename

                orchestrator.create_workflow_report(str(report_path))
                console.print(f"\nReport saved to: {report_path}", style="blue")

    except Exception as e:
        console.print(f"Error: {str(e)}", style="red bold")
        logger.exception("Error during workflow execution")
        raise typer.Exit(code=1)


@workflow_app.command("resume")
def resume_workflow(
    # Project information
    project_key: str = typer.Option(..., help="Zephyr project key to resume migration for"),
    # Database configuration
    db_type: DatabaseType = typer.Option(
        DatabaseType.SQLITE, help="Database type (sqlite or postgresql)"
    ),
    db_path: Optional[Path] = typer.Option(
        None, help="Path to SQLite database file (for SQLite only)"
    ),
    host: Optional[str] = typer.Option(None, help="PostgreSQL host (for PostgreSQL only)"),
    port: Optional[int] = typer.Option(None, help="PostgreSQL port (for PostgreSQL only)"),
    username: Optional[str] = typer.Option(None, help="PostgreSQL username (for PostgreSQL only)"),
    password: Optional[str] = typer.Option(None, help="PostgreSQL password (for PostgreSQL only)"),
    database: Optional[str] = typer.Option(
        None, help="PostgreSQL database name (for PostgreSQL only)"
    ),
    # Zephyr configuration
    zephyr_base_url: str = typer.Option(..., help="Zephyr Scale API base URL"),
    zephyr_api_token: str = typer.Option(..., help="Zephyr Scale API token"),
    # qTest configuration
    qtest_base_url: str = typer.Option(..., help="qTest API base URL"),
    qtest_username: str = typer.Option(..., help="qTest username"),
    qtest_password: str = typer.Option(..., help="qTest password"),
    qtest_project_id: int = typer.Option(..., help="qTest project ID"),
    # Workflow options
    phases: Optional[List[WorkflowPhase]] = typer.Option(
        None, help="Phases to resume (if not specified, resume all incomplete phases)"
    ),
    no_validation: bool = typer.Option(False, help="Disable validation"),
    # Output options
    output_dir: Optional[Path] = typer.Option(
        None, help="Directory for output files (reports, logs)"
    ),
):
    """
    Resume a previously interrupted workflow.

    This command resumes an ETL migration workflow that was interrupted or
    failed, picking up from where it left off.
    """
    try:
        # Create configuration
        zephyr_config = ZephyrConfig(
            base_url=zephyr_base_url,
            api_token=zephyr_api_token,
            project_key=project_key,
        )

        qtest_config = QTestConfig(
            base_url=qtest_base_url,
            username=qtest_username,
            password=qtest_password,
            project_id=qtest_project_id,
        )

        workflow_config = WorkflowConfig(
            project_key=project_key,
            db_type=db_type.value,
            db_path=str(db_path) if db_path else None,
            pg_host=host,
            pg_port=port,
            pg_username=username,
            pg_password=password,
            pg_database=database,
            validation_enabled=not no_validation,
            output_dir=output_dir,
            zephyr_config=zephyr_config,
            qtest_config=qtest_config,
        )

        # Create orchestrator
        orchestrator = WorkflowOrchestrator(workflow_config)

        # Get resume phases
        phase_values = [p.value for p in phases] if phases else None

        # Resume workflow
        console.print(f"Resuming workflow for project {project_key}...")
        results = orchestrator.resume_workflow(phase_values)

        # Print summary
        console.print("\n✓ Workflow resumed and completed", style="green bold")

        # Print workflow status
        orchestrator.print_workflow_status(console=console)

        # Generate report if output directory is specified
        if output_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = Path(output_dir) / f"migration_report_{project_key}_{timestamp}.json"

            orchestrator.create_workflow_report(str(report_path))
            console.print(f"\nReport saved to: {report_path}", style="blue")

    except Exception as e:
        console.print(f"Error: {str(e)}", style="red bold")
        logger.exception("Error during workflow resumption")
        raise typer.Exit(code=1)


@workflow_app.command("status")
def workflow_status(
    # Project information
    project_key: str = typer.Option(..., help="Zephyr project key to check status for"),
    # Database configuration
    db_type: DatabaseType = typer.Option(
        DatabaseType.SQLITE, help="Database type (sqlite or postgresql)"
    ),
    db_path: Optional[Path] = typer.Option(
        None, help="Path to SQLite database file (for SQLite only)"
    ),
    host: Optional[str] = typer.Option(None, help="PostgreSQL host (for PostgreSQL only)"),
    port: Optional[int] = typer.Option(None, help="PostgreSQL port (for PostgreSQL only)"),
    username: Optional[str] = typer.Option(None, help="PostgreSQL username (for PostgreSQL only)"),
    password: Optional[str] = typer.Option(None, help="PostgreSQL password (for PostgreSQL only)"),
    database: Optional[str] = typer.Option(
        None, help="PostgreSQL database name (for PostgreSQL only)"
    ),
    # Output options
    output_file: Optional[Path] = typer.Option(
        None, help="Save status to file instead of displaying it"
    ),
    json_format: bool = typer.Option(False, help="Output in JSON format"),
):
    """
    Check the status of a workflow.

    This command displays the current status of an ETL migration workflow,
    including progress, entity counts, and any issues.
    """
    try:
        # Create configuration
        workflow_config = WorkflowConfig(
            project_key=project_key,
            db_type=db_type.value,
            db_path=str(db_path) if db_path else None,
            pg_host=host,
            pg_port=port,
            pg_username=username,
            pg_password=password,
            pg_database=database,
        )

        # Create orchestrator
        orchestrator = WorkflowOrchestrator(workflow_config)

        # Get status
        status = orchestrator.get_workflow_status()

        # Output as JSON if requested
        if json_format:
            status_json = json.dumps(status, indent=2)

            if output_file:
                with open(output_file, "w") as f:
                    f.write(status_json)
                console.print(f"Status saved to: {output_file}", style="blue")
            else:
                console.print(status_json)

            return

        # Save to file if requested
        if output_file:
            orchestrator.create_workflow_report(str(output_file))
            console.print(f"Status report saved to: {output_file}", style="blue")
            return

        # Print status to console
        console.print(f"Workflow Status for Project: {project_key}\n", style="bold")
        orchestrator.print_workflow_status(console=console)

    except Exception as e:
        console.print(f"Error: {str(e)}", style="red bold")
        logger.exception("Error checking workflow status")
        raise typer.Exit(code=1)


@workflow_app.command("report")
def create_report(
    # Project information
    project_key: str = typer.Option(..., help="Zephyr project key to create report for"),
    # Database configuration
    db_type: DatabaseType = typer.Option(
        DatabaseType.SQLITE, help="Database type (sqlite or postgresql)"
    ),
    db_path: Optional[Path] = typer.Option(
        None, help="Path to SQLite database file (for SQLite only)"
    ),
    host: Optional[str] = typer.Option(None, help="PostgreSQL host (for PostgreSQL only)"),
    port: Optional[int] = typer.Option(None, help="PostgreSQL port (for PostgreSQL only)"),
    username: Optional[str] = typer.Option(None, help="PostgreSQL username (for PostgreSQL only)"),
    password: Optional[str] = typer.Option(None, help="PostgreSQL password (for PostgreSQL only)"),
    database: Optional[str] = typer.Option(
        None, help="PostgreSQL database name (for PostgreSQL only)"
    ),
    # Output options
    output_file: Path = typer.Option(..., help="Path to save the report"),
    report_format: OutputFormat = typer.Option(
        OutputFormat.JSON, help="Report output format (json, html, text)"
    ),
):
    """
    Create a comprehensive workflow report.

    This command generates a detailed report of the ETL migration workflow,
    including statistics, issues, and results.
    """
    try:
        # Create configuration
        workflow_config = WorkflowConfig(
            project_key=project_key,
            db_type=db_type.value,
            db_path=str(db_path) if db_path else None,
            pg_host=host,
            pg_port=port,
            pg_username=username,
            pg_password=password,
            pg_database=database,
        )

        # Create orchestrator
        orchestrator = WorkflowOrchestrator(workflow_config)

        # Generate report based on format
        if report_format == OutputFormat.JSON:
            report_path = str(output_file)
            if not report_path.endswith(".json"):
                report_path += ".json"

            orchestrator.create_workflow_report(report_path)
            console.print(f"JSON report saved to: {report_path}", style="blue")

        elif report_format == OutputFormat.HTML:
            # Create HTML report
            report_path = str(output_file)
            if not report_path.endswith(".html"):
                report_path += ".html"

            # Get status data
            status = orchestrator.get_workflow_status()
            summary = orchestrator._generate_workflow_summary()

            # Generate HTML report

            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Migration Report - {project_key}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1, h2, h3 {{ color: #333; }}
                    .section {{ margin-bottom: 20px; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                    .status-completed {{ color: green; }}
                    .status-in_progress {{ color: orange; }}
                    .status-failed {{ color: red; }}
                    .status-not_started {{ color: gray; }}
                </style>
            </head>
            <body>
                <h1>Migration Report</h1>
                <div class="section">
                    <h2>Project Information</h2>
                    <table>
                        <tr><th>Project Key</th><td>{project_key}</td></tr>
                        <tr><th>Report Generated</th><td>{timestamp}</td></tr>
                    </table>
                </div>

                <div class="section">
                    <h2>Workflow Status</h2>
                    <table>
                        <tr>
                            <th>Phase</th>
                            <th>Status</th>
                            <th>Duration</th>
                        </tr>
                        {phase_rows}
                    </table>
                </div>

                <div class="section">
                    <h2>Entity Counts</h2>
                    <table>
                        <tr>
                            <th>Entity Type</th>
                            <th>Source</th>
                            <th>Target</th>
                            <th>Mapped</th>
                        </tr>
                        {entity_rows}
                    </table>
                </div>

                <div class="section">
                    <h2>Recent Events</h2>
                    <table>
                        <tr>
                            <th>Timestamp</th>
                            <th>Phase</th>
                            <th>Status</th>
                            <th>Message</th>
                        </tr>
                        {event_rows}
                    </table>
                </div>

                <div class="section">
                    <h2>Validation Summary</h2>
                    <table>
                        <tr>
                            <th>Level</th>
                            <th>Count</th>
                        </tr>
                        {validation_rows}
                    </table>
                </div>

                <div class="section">
                    <h2>Raw Data</h2>
                    <pre>{raw_data}</pre>
                </div>
            </body>
            </html>
            """

            # Generate phase rows
            phase_rows = ""
            for phase, phase_status in status["phases"].items():
                duration = summary.get("duration", {}).get(phase, "N/A")
                duration_str = f"{duration:.2f}s" if isinstance(duration, (int, float)) else "N/A"

                status_class = f"status-{phase_status}"
                phase_rows += f"""
                <tr>
                    <td>{phase.capitalize()}</td>
                    <td class="{status_class}">{phase_status.replace('_', ' ').title()}</td>
                    <td>{duration_str}</td>
                </tr>
                """

            # Generate entity rows
            entity_rows = ""
            if "entity_counts" in status:
                source_counts = status["entity_counts"].get("source", {})
                target_counts = status["entity_counts"].get("target", {})
                mapping_counts = status["entity_counts"].get("mappings", {})

                # Get all entity types
                all_entity_types = set()
                all_entity_types.update(source_counts.keys())
                all_entity_types.update(target_counts.keys())
                all_entity_types.update(mapping_counts.keys())

                for entity_type in sorted(all_entity_types):
                    source_count = source_counts.get(entity_type, 0)
                    target_count = target_counts.get(entity_type, 0)
                    mapping_count = mapping_counts.get(entity_type, 0)

                    entity_rows += f"""
                    <tr>
                        <td>{entity_type.replace('_', ' ').title()}</td>
                        <td>{source_count}</td>
                        <td>{target_count}</td>
                        <td>{mapping_count}</td>
                    </tr>
                    """

            # Generate event rows
            event_rows = ""
            for event in status["events"]:
                phase = event["phase"].capitalize()
                event_status = event["status"].replace("_", " ").title()
                timestamp = datetime.fromisoformat(event["timestamp"]).strftime("%H:%M:%S")

                status_class = f"status-{event['status']}"
                event_rows += f"""
                <tr>
                    <td>{timestamp}</td>
                    <td>{phase}</td>
                    <td class="{status_class}">{event_status}</td>
                    <td>{event['message']}</td>
                </tr>
                """

            # Generate validation rows
            validation_rows = ""
            if "validation" in status and status["validation"]:
                validation = status["validation"]

                validation_rows += f"""
                <tr>
                    <td>Critical</td>
                    <td style="color: red;">{validation.get('critical_issues', 0)}</td>
                </tr>
                <tr>
                    <td>Error</td>
                    <td style="color: orange;">{validation.get('error_issues', 0)}</td>
                </tr>
                <tr>
                    <td>Warning</td>
                    <td style="color: blue;">{validation.get('warning_issues', 0)}</td>
                </tr>
                <tr>
                    <td>Info</td>
                    <td style="color: green;">{validation.get('info_issues', 0)}</td>
                </tr>
                """

            # Fill in the template
            html_content = html_template.format(
                project_key=project_key,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                phase_rows=phase_rows,
                entity_rows=entity_rows,
                event_rows=event_rows,
                validation_rows=validation_rows,
                raw_data=json.dumps(status, indent=2),
            )

            # Save HTML report
            with open(report_path, "w") as f:
                f.write(html_content)

            console.print(f"HTML report saved to: {report_path}", style="blue")

        elif report_format == OutputFormat.TEXT:
            # Create text report
            report_path = str(output_file)
            if not report_path.endswith(".txt"):
                report_path += ".txt"

            # Get and print status to a string

            # Redirect console output to a string
            original_stdout = sys.stdout
            string_buffer = StringIO()
            sys.stdout = string_buffer

            # Create a new console that writes to the string buffer
            string_console = Console(file=string_buffer, width=120)

            # Print status to the string console
            string_console.print(f"Workflow Status for Project: {project_key}\n", style="bold")
            orchestrator.print_workflow_status(console=string_console)

            # Restore original stdout
            sys.stdout = original_stdout

            # Get the text content
            text_content = string_buffer.getvalue()

            # Save text report
            with open(report_path, "w") as f:
                f.write(text_content)

            console.print(f"Text report saved to: {report_path}", style="blue")

    except Exception as e:
        console.print(f"Error: {str(e)}", style="red bold")
        logger.exception("Error creating workflow report")
        raise typer.Exit(code=1)


@workflow_app.command("cleanup")
def cleanup_workflow(
    # Project information
    project_key: str = typer.Option(..., help="Zephyr project key to clean up data for"),
    # Database configuration
    db_type: DatabaseType = typer.Option(
        DatabaseType.SQLITE, help="Database type (sqlite or postgresql)"
    ),
    db_path: Optional[Path] = typer.Option(
        None, help="Path to SQLite database file (for SQLite only)"
    ),
    host: Optional[str] = typer.Option(None, help="PostgreSQL host (for PostgreSQL only)"),
    port: Optional[int] = typer.Option(None, help="PostgreSQL port (for PostgreSQL only)"),
    username: Optional[str] = typer.Option(None, help="PostgreSQL username (for PostgreSQL only)"),
    password: Optional[str] = typer.Option(None, help="PostgreSQL password (for PostgreSQL only)"),
    database: Optional[str] = typer.Option(
        None, help="PostgreSQL database name (for PostgreSQL only)"
    ),
    # Cleanup options
    keep_reports: bool = typer.Option(False, help="Keep validation reports"),
    keep_mappings: bool = typer.Option(False, help="Keep entity mappings"),
    attachments_dir: Optional[Path] = typer.Option(
        None, help="Directory containing attachments to clean up"
    ),
    confirm: bool = typer.Option(False, help="Skip confirmation prompt"),
):
    """
    Clean up workflow data.

    This command removes workflow data from the database and attachment storage,
    allowing for a fresh migration.
    """
    try:
        # Create configuration
        workflow_config = WorkflowConfig(
            project_key=project_key,
            db_type=db_type.value,
            db_path=str(db_path) if db_path else None,
            pg_host=host,
            pg_port=port,
            pg_username=username,
            pg_password=password,
            pg_database=database,
            attachments_dir=attachments_dir,
        )

        # Create database manager
        db = get_database_manager(
            db_type=db_type.value,
            db_path=str(db_path) if db_path else None,
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
        )

        # Get entity counts
        entities = db.get_source_entity_counts(project_key)
        total_entities = sum(entities.values())

        # Confirm cleanup
        if not confirm:
            console.print(
                f"WARNING: This will delete all workflow data for project {project_key}.",
                style="yellow bold",
            )
            console.print(f"Found {total_entities} entities to delete.")

            if typer.confirm("Do you want to continue?", default=False) is False:
                console.print("Cleanup cancelled.")
                return

        # Clean up data
        console.print(f"Cleaning up workflow data for project {project_key}...")

        # Delete workflow events
        db.delete_workflow_events(project_key)
        console.print("✓ Deleted workflow events", style="green")

        # Delete validation issues
        db.delete_validation_issues(project_key)
        console.print("✓ Deleted validation issues", style="green")

        # Delete validation reports if not keeping them
        if not keep_reports:
            db.delete_validation_reports(project_key)
            console.print("✓ Deleted validation reports", style="green")

        # Delete entity mappings if not keeping them
        if not keep_mappings:
            db.delete_entity_mappings(project_key)
            console.print("✓ Deleted entity mappings", style="green")

        # Delete entity batches
        db.delete_entity_batches(project_key)
        console.print("✓ Deleted entity batch states", style="green")

        # Delete migration state
        db.delete_migration_state(project_key)
        console.print("✓ Deleted migration state", style="green")

        # Delete attachments if directory is provided
        if attachments_dir:
            # Check if project attachments directory exists
            project_attachments_dir = attachments_dir / project_key
            if project_attachments_dir.exists():
                shutil.rmtree(project_attachments_dir)
                console.print(f"✓ Deleted attachments for project {project_key}", style="green")

        console.print("\n✓ Cleanup completed successfully", style="green bold")

    except Exception as e:
        console.print(f"Error: {str(e)}", style="red bold")
        logger.exception("Error during workflow cleanup")
        raise typer.Exit(code=1)


@workflow_app.command("validate")
def validate_workflow(
    # Project information
    project_key: str = typer.Option(..., help="Zephyr project key to validate"),
    # Database configuration
    db_type: DatabaseType = typer.Option(
        DatabaseType.SQLITE, help="Database type (sqlite or postgresql)"
    ),
    db_path: Optional[Path] = typer.Option(
        None, help="Path to SQLite database file (for SQLite only)"
    ),
    host: Optional[str] = typer.Option(None, help="PostgreSQL host (for PostgreSQL only)"),
    port: Optional[int] = typer.Option(None, help="PostgreSQL port (for PostgreSQL only)"),
    username: Optional[str] = typer.Option(None, help="PostgreSQL username (for PostgreSQL only)"),
    password: Optional[str] = typer.Option(None, help="PostgreSQL password (for PostgreSQL only)"),
    database: Optional[str] = typer.Option(
        None, help="PostgreSQL database name (for PostgreSQL only)"
    ),
    # qTest configuration (optional for some validations)
    qtest_base_url: Optional[str] = typer.Option(None, help="qTest API base URL"),
    qtest_username: Optional[str] = typer.Option(None, help="qTest username"),
    qtest_password: Optional[str] = typer.Option(None, help="qTest password"),
    qtest_project_id: Optional[int] = typer.Option(None, help="qTest project ID"),
    # Output options
    output_file: Optional[Path] = typer.Option(
        None, help="Path to save the validation report"
    ),
):
    """
    Validate a migration workflow.

    This command runs validation checks on the migrated data to ensure its integrity,
    even if the workflow itself was run without validation.
    """
    try:
        # Create configuration
        qtest_config = None
        if qtest_base_url and qtest_username and qtest_password and qtest_project_id:
            qtest_config = QTestConfig(
                base_url=qtest_base_url,
                username=qtest_username,
                password=qtest_password,
                project_id=qtest_project_id,
            )

        workflow_config = WorkflowConfig(
            project_key=project_key,
            db_type=db_type.value,
            db_path=str(db_path) if db_path else None,
            pg_host=host,
            pg_port=port,
            pg_username=username,
            pg_password=password,
            pg_database=database,
            validation_enabled=True,
            qtest_config=qtest_config,
        )

        # Create orchestrator
        orchestrator = WorkflowOrchestrator(workflow_config)

        # Run validation
        console.print(f"Running validation for project {project_key}...")

        # Set up progress reporting
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Validating migration...", total=None)

            # Run validation phase
            validation_results = asyncio.run(orchestrator._run_validation_phase())

            progress.update(task, description="Validation completed", completed=1, total=1)

        # Print validation results
        console.print("\n✓ Validation completed", style="green bold")

        # Create table for validation summary
        table = Table(title="Validation Summary")
        table.add_column("Issue Level")
        table.add_column("Count")

        table.add_row("Critical", str(validation_results.get("critical_issues", 0)), style="red")
        table.add_row("Error", str(validation_results.get("error_issues", 0)), style="yellow")
        table.add_row("Warning", str(validation_results.get("warning_issues", 0)), style="blue")
        table.add_row("Info", str(validation_results.get("info_issues", 0)), style="green")
        table.add_row("Total", str(validation_results.get("total_issues", 0)), style="bold")

        console.print(table)

        # Print recent issues
        recent_issues = validation_results.get("recent_issues", [])
        if recent_issues:
            issues_table = Table(title="Recent Validation Issues")
            issues_table.add_column("Level")
            issues_table.add_column("Message")
            issues_table.add_column("Entity ID")

            for issue in recent_issues[:10]:  # Show only the first 10 issues
                level = issue.get("level", "").lower()
                message = issue.get("message", "")
                entity_id = issue.get("entity_id", "")

                style = "red" if level == "critical" else "yellow" if level == "error" else "blue" if level == "warning" else "green"
                issues_table.add_row(level.capitalize(), message, entity_id, style=style)

            console.print(issues_table)

        # Save report if output file is specified
        if output_file:
            report_path = str(output_file)
            if not report_path.endswith(".json"):
                report_path += ".json"

            with open(report_path, "w") as f:
                json.dump(validation_results, f, indent=2)

            console.print(f"\nValidation report saved to: {report_path}", style="blue")

    except Exception as e:
        console.print(f"Error: {str(e)}", style="red bold")
        logger.exception("Error during validation")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    workflow_app()