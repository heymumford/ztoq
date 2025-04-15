"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Command line interface for database indexing functionality in ZTOQ.

This module provides a command-line interface to analyze, recommend, apply, 
and validate database indexes for performance optimization.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from ztoq.core.db_manager import DatabaseConfig
from ztoq.db_indexing import (
    analyze_database_indexes,
    get_index_manager,
    optimize_database_indexes,
    validate_database_indexes,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger("ztoq.db_index")

app = typer.Typer(help="ZTOQ Database Indexing Utility")
console = Console()


def get_database_connection(
    db_type: str,
    db_path: Path | None = None,
    host: str | None = None,
    port: int | None = None,
    username: str | None = None,
    password: str | None = None,
    database: str | None = None,
) -> str:
    """
    Get a database connection string based on the parameters.
    
    Args:
        db_type: Database type (sqlite or postgresql)
        db_path: Path to SQLite database file (for SQLite)
        host: Database host (for PostgreSQL)
        port: Database port (for PostgreSQL)
        username: Database username (for PostgreSQL)
        password: Database password (for PostgreSQL)
        database: Database name (for PostgreSQL)
        
    Returns:
        Database connection string

    """
    # Check for environment variables if not provided directly (PostgreSQL)
    if db_type == "postgresql" and not all([host, username, database]):
        env_host = os.environ.get("ZTOQ_PG_HOST")
        env_port = os.environ.get("ZTOQ_PG_PORT")
        env_user = os.environ.get("ZTOQ_PG_USER")
        env_pass = os.environ.get("ZTOQ_PG_PASSWORD")
        env_db = os.environ.get("ZTOQ_PG_DATABASE")

        if env_host and env_user and env_db:
            host = env_host
            port = int(env_port) if env_port else 5432
            username = env_user
            password = env_pass
            database = env_db
            console.print("Using PostgreSQL settings from environment variables", style="blue")
        else:
            console.print("Error: PostgreSQL connection details not provided", style="red")
            raise typer.Exit(code=1)

    # Create database configuration
    db_config = DatabaseConfig(
        db_type=db_type,
        db_path=str(db_path) if db_path else None,
        host=host,
        port=port,
        username=username,
        password=password,
        database=database,
    )

    return db_config.get_connection_string()


@app.command("analyze")
def analyze_indexes(
    db_type: str = typer.Option(
        "sqlite", help="Database type (sqlite or postgresql)",
    ),
    db_path: Path | None = typer.Option(
        None, help="Path to SQLite database file (for SQLite only)",
    ),
    host: str | None = typer.Option(
        None, help="PostgreSQL host (for PostgreSQL only)",
    ),
    port: int | None = typer.Option(
        None, help="PostgreSQL port (for PostgreSQL only)",
    ),
    username: str | None = typer.Option(
        None, help="PostgreSQL username (for PostgreSQL only)",
    ),
    password: str | None = typer.Option(
        None, help="PostgreSQL password (for PostgreSQL only)",
    ),
    database: str | None = typer.Option(
        None, help="PostgreSQL database name (for PostgreSQL only)",
    ),
    output_file: Path | None = typer.Option(
        None, help="Output file path for analysis report (JSON)",
    ),
):
    """
    Analyze database indexes and provide recommendations.
    
    This command examines the database, analyzes existing indexes, identifies unused
    or inefficient indexes, and provides recommendations for improvements.
    """
    try:
        # Get connection string
        connection_string = get_database_connection(
            db_type, db_path, host, port, username, password, database,
        )

        console.print("Analyzing database indexes...", style="blue")

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing...", total=1)

            # Analyze the database
            analysis_results = analyze_database_indexes(connection_string)

            progress.update(task, completed=1)

        # Display summary of analysis
        console.print("\n[bold]Index Analysis Summary[/bold]")

        summary = analysis_results.get("summary", {})

        table = Table(title="Index Analysis")
        table.add_column("Metric")
        table.add_column("Value")

        table.add_row("Total Indexes", str(summary.get("total_indexes", 0)))
        table.add_row("Ineffective Indexes", str(summary.get("ineffective_indexes", 0)))
        table.add_row("Recommendations", str(summary.get("recommendation_count", 0)))

        console.print(table)

        # Display recommendations
        if analysis_results.get("recommendations"):
            console.print("\n[bold]Recommended Actions[/bold]")

            rec_table = Table(title="Recommendations")
            rec_table.add_column("Action")
            rec_table.add_column("Target")
            rec_table.add_column("Priority")
            rec_table.add_column("Rationale")

            for rec in analysis_results.get("recommendations", []):
                action = rec.get("action", "")
                target = rec.get("existing_index_name", "") or (
                    f"{rec.get('index_definition', {}).get('table_name', '')}."
                    f"{', '.join(rec.get('index_definition', {}).get('column_names', []))}"
                )
                priority = rec.get("priority", "")
                rationale = rec.get("rationale", "")

                rec_table.add_row(
                    action,
                    target,
                    priority,
                    rationale,
                )

            console.print(rec_table)

        # Save to file if requested
        if output_file:
            with open(output_file, "w") as f:
                json.dump(analysis_results, f, indent=2, default=str)
            console.print(f"\nAnalysis report saved to {output_file}", style="green")

    except Exception as e:
        console.print(f"Error analyzing indexes: {e}", style="red")
        logger.exception("Error during index analysis")
        raise typer.Exit(code=1)


@app.command("apply")
def apply_recommendations(
    db_type: str = typer.Option(
        "sqlite", help="Database type (sqlite or postgresql)",
    ),
    db_path: Path | None = typer.Option(
        None, help="Path to SQLite database file (for SQLite only)",
    ),
    host: str | None = typer.Option(
        None, help="PostgreSQL host (for PostgreSQL only)",
    ),
    port: int | None = typer.Option(
        None, help="PostgreSQL port (for PostgreSQL only)",
    ),
    username: str | None = typer.Option(
        None, help="PostgreSQL username (for PostgreSQL only)",
    ),
    password: str | None = typer.Option(
        None, help="PostgreSQL password (for PostgreSQL only)",
    ),
    database: str | None = typer.Option(
        None, help="PostgreSQL database name (for PostgreSQL only)",
    ),
    report_file: Path | None = typer.Option(
        None, help="Output file path for applied changes report (JSON)",
    ),
    confirm: bool = typer.Option(
        False, "--yes", help="Skip confirmation prompt",
    ),
):
    """
    Apply recommended database indexes.
    
    This command creates recommended indexes based on prior analysis 
    to improve database performance.
    """
    try:
        # Get connection string
        connection_string = get_database_connection(
            db_type, db_path, host, port, username, password, database,
        )

        # Get the index manager and recommendations
        index_manager = get_index_manager(connection_string)
        recommended_indexes = index_manager.get_recommended_indexes()

        # Display recommendations first
        console.print(f"Found {len(recommended_indexes)} recommended indexes:", style="blue")

        rec_table = Table(title="Recommended Indexes")
        rec_table.add_column("Index Name")
        rec_table.add_column("Table")
        rec_table.add_column("Columns")

        for idx in recommended_indexes:
            rec_table.add_row(
                idx.index_name,
                idx.table_name,
                ", ".join(idx.column_names),
            )

        console.print(rec_table)

        # Get confirmation if needed
        if not confirm:
            confirmed = typer.confirm("Do you want to apply these recommended indexes?")
            if not confirmed:
                console.print("Operation cancelled.", style="yellow")
                raise typer.Exit()

        # Apply the recommendations
        console.print("\nApplying recommended indexes...", style="blue")

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Applying...", total=1)

            # Apply the recommendations
            results = optimize_database_indexes(connection_string)

            progress.update(task, completed=1)

        # Display results
        console.print("\n[bold]Index Application Results[/bold]")

        table = Table(title="Results")
        table.add_column("Metric")
        table.add_column("Value")

        table.add_row("Successfully Created", str(results.get("success_count", 0)))
        table.add_row("Failed", str(results.get("failed_count", 0)))
        table.add_row("Skipped (Already Exists)", str(results.get("skipped_count", 0)))

        console.print(table)

        # Display details of operations
        details_table = Table(title="Operation Details")
        details_table.add_column("Index Name")
        details_table.add_column("Status")
        details_table.add_column("Details")

        for detail in results.get("details", []):
            status = detail.get("status", "")
            status_style = "green" if status == "created" else "yellow" if status == "skipped" else "red"

            details_table.add_row(
                detail.get("index_name", ""),
                f"[{status_style}]{status}[/{status_style}]",
                detail.get("reason", "") or f"Table: {detail.get('table_name', '')}, Columns: {', '.join(detail.get('columns', []))}",
            )

        console.print(details_table)

        # Save to file if requested
        if report_file:
            with open(report_file, "w") as f:
                json.dump(results, f, indent=2, default=str)
            console.print(f"\nApplication report saved to {report_file}", style="green")

    except Exception as e:
        console.print(f"Error applying index recommendations: {e}", style="red")
        logger.exception("Error during index application")
        raise typer.Exit(code=1)


@app.command("report")
def generate_usage_report(
    db_type: str = typer.Option(
        "sqlite", help="Database type (sqlite or postgresql)",
    ),
    db_path: Path | None = typer.Option(
        None, help="Path to SQLite database file (for SQLite only)",
    ),
    host: str | None = typer.Option(
        None, help="PostgreSQL host (for PostgreSQL only)",
    ),
    port: int | None = typer.Option(
        None, help="PostgreSQL port (for PostgreSQL only)",
    ),
    username: str | None = typer.Option(
        None, help="PostgreSQL username (for PostgreSQL only)",
    ),
    password: str | None = typer.Option(
        None, help="PostgreSQL password (for PostgreSQL only)",
    ),
    database: str | None = typer.Option(
        None, help="PostgreSQL database name (for PostgreSQL only)",
    ),
    output_file: Path | None = typer.Option(
        None, help="Output file path for usage report (JSON)",
    ),
):
    """
    Generate a report on index usage.
    
    This command analyzes and reports on how indexes are being used in the database,
    including statistics on index size and usage frequency.
    """
    try:
        # Get connection string
        connection_string = get_database_connection(
            db_type, db_path, host, port, username, password, database,
        )

        console.print("Generating index usage report...", style="blue")

        # Get the index manager
        index_manager = get_index_manager(connection_string)

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing index usage...", total=1)

            # Get index usage statistics
            index_stats = index_manager.analyze_index_usage()

            progress.update(task, completed=1)

        # Display results
        console.print("\n[bold]Index Usage Report[/bold]")

        usage_table = Table(title="Index Usage")
        usage_table.add_column("Index Name")
        usage_table.add_column("Table")
        usage_table.add_column("Columns")
        usage_table.add_column("Type")
        usage_table.add_column("Size")
        usage_table.add_column("Usage Count")
        usage_table.add_column("Status")

        for stat in index_stats:
            size_str = f"{stat.size_bytes // 1024} KB" if stat.size_bytes else "N/A"
            usage_count = str(stat.usage_count) if stat.usage_count is not None else "N/A"

            status = "Effective" if stat.is_effective else "Unused" if stat.is_effective is False else "Unknown"
            status_style = "green" if status == "Effective" else "red" if status == "Unused" else "yellow"

            usage_table.add_row(
                stat.index_name,
                stat.table_name,
                ", ".join(stat.column_names),
                stat.index_type,
                size_str,
                usage_count,
                f"[{status_style}]{status}[/{status_style}]",
            )

        console.print(usage_table)

        # Compute summary statistics
        total_indexes = len(index_stats)
        effective_indexes = sum(1 for stat in index_stats if stat.is_effective)
        unused_indexes = sum(1 for stat in index_stats if stat.is_effective is False)
        unknown_status = sum(1 for stat in index_stats if stat.is_effective is None)

        summary_table = Table(title="Summary")
        summary_table.add_column("Metric")
        summary_table.add_column("Value")

        summary_table.add_row("Total Indexes", str(total_indexes))
        summary_table.add_row("Effective Indexes", str(effective_indexes))
        summary_table.add_row("Unused Indexes", str(unused_indexes))
        summary_table.add_row("Unknown Status", str(unknown_status))

        console.print(summary_table)

        # Prepare report for file output
        if output_file:
            report = {
                "generated_at": datetime.now().isoformat(),
                "database_type": db_type,
                "total_indexes": total_indexes,
                "effective_indexes": effective_indexes,
                "unused_indexes": unused_indexes,
                "unknown_status": unknown_status,
                "indexes": [vars(stat) for stat in index_stats],
            }

            with open(output_file, "w") as f:
                json.dump(report, f, indent=2, default=str)

            console.print(f"\nIndex usage report saved to {output_file}", style="green")

    except Exception as e:
        console.print(f"Error generating index usage report: {e}", style="red")
        logger.exception("Error during index usage reporting")
        raise typer.Exit(code=1)


@app.command("validate")
def validate_effectiveness(
    db_type: str = typer.Option(
        "sqlite", help="Database type (sqlite or postgresql)",
    ),
    db_path: Path | None = typer.Option(
        None, help="Path to SQLite database file (for SQLite only)",
    ),
    host: str | None = typer.Option(
        None, help="PostgreSQL host (for PostgreSQL only)",
    ),
    port: int | None = typer.Option(
        None, help="PostgreSQL port (for PostgreSQL only)",
    ),
    username: str | None = typer.Option(
        None, help="PostgreSQL username (for PostgreSQL only)",
    ),
    password: str | None = typer.Option(
        None, help="PostgreSQL password (for PostgreSQL only)",
    ),
    database: str | None = typer.Option(
        None, help="PostgreSQL database name (for PostgreSQL only)",
    ),
    output_file: Path | None = typer.Option(
        None, help="Output file path for validation report (JSON)",
    ),
):
    """
    Validate index effectiveness.
    
    This command validates how effectively indexes are being used and identifies
    areas for improvement.
    """
    try:
        # Get connection string
        connection_string = get_database_connection(
            db_type, db_path, host, port, username, password, database,
        )

        console.print("Validating index effectiveness...", style="blue")

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Validating...", total=1)

            # Validate database indexes
            validation_results = validate_database_indexes(connection_string)

            progress.update(task, completed=1)

        # Display results
        console.print("\n[bold]Index Validation Report[/bold]")

        table = Table(title="Validation Summary")
        table.add_column("Metric")
        table.add_column("Value")

        table.add_row("Total Indexes Validated", str(validation_results.get("indexes_validated", 0)))
        table.add_row("Indexes Used", str(validation_results.get("indexes_used", 0)))
        table.add_row("Indexes Unused", str(validation_results.get("indexes_unused", 0)))

        console.print(table)

        # Display details
        if validation_results.get("details"):
            details_table = Table(title="Index Details")
            details_table.add_column("Index Name")
            details_table.add_column("Table")
            details_table.add_column("Status")
            details_table.add_column("Usage Count")
            details_table.add_column("Recommendation")

            for detail in validation_results.get("details", []):
                status = "Used" if detail.get("is_used") else "Unused"
                status_style = "green" if status == "Used" else "red"

                details_table.add_row(
                    detail.get("index_name", ""),
                    detail.get("table_name", ""),
                    f"[{status_style}]{status}[/{status_style}]",
                    str(detail.get("usage_count", "N/A")),
                    detail.get("recommendation", ""),
                )

            console.print(details_table)

        # Save to file if requested
        if output_file:
            with open(output_file, "w") as f:
                json.dump(validation_results, f, indent=2, default=str)
            console.print(f"\nValidation report saved to {output_file}", style="green")

    except Exception as e:
        console.print(f"Error validating index effectiveness: {e}", style="red")
        logger.exception("Error during index validation")
        raise typer.Exit(code=1)


@app.command("verify")
def verify_query_index(
    query: str = typer.Argument(..., help="SQL query to verify index usage for"),
    index_name: str = typer.Argument(..., help="Name of the index to check"),
    db_type: str = typer.Option(
        "sqlite", help="Database type (sqlite or postgresql)",
    ),
    db_path: Path | None = typer.Option(
        None, help="Path to SQLite database file (for SQLite only)",
    ),
    host: str | None = typer.Option(
        None, help="PostgreSQL host (for PostgreSQL only)",
    ),
    port: int | None = typer.Option(
        None, help="PostgreSQL port (for PostgreSQL only)",
    ),
    username: str | None = typer.Option(
        None, help="PostgreSQL username (for PostgreSQL only)",
    ),
    password: str | None = typer.Option(
        None, help="PostgreSQL password (for PostgreSQL only)",
    ),
    database: str | None = typer.Option(
        None, help="PostgreSQL database name (for PostgreSQL only)",
    ),
    output_file: Path | None = typer.Option(
        None, help="Output file path for verification report (JSON)",
    ),
):
    """
    Verify index usage for specific queries.
    
    This command checks if a specific index is being used for a particular query
    and provides details about the query execution plan.
    """
    try:
        # Get connection string
        connection_string = get_database_connection(
            db_type, db_path, host, port, username, password, database,
        )

        console.print(f"Verifying if index '{index_name}' is used for query:", style="blue")
        console.print(f"\n{query}\n", style="yellow")

        # Get the index manager
        index_manager = get_index_manager(connection_string)

        # Verify index usage
        verification_result = index_manager.verify_index_usage(index_name, query)

        # Display results
        if verification_result.get("is_used"):
            console.print(f"✅ Index '{index_name}' is used for this query.", style="green")
        else:
            console.print(f"❌ Index '{index_name}' is NOT used for this query.", style="red")

        if verification_result.get("explanation"):
            console.print("\nExplanation:", style="blue")
            console.print(verification_result.get("explanation"))

        # Show execution plan if available
        if verification_result.get("execution_plan"):
            console.print("\nExecution Plan:", style="blue")
            if isinstance(verification_result.get("execution_plan"), str):
                console.print(verification_result.get("execution_plan"))
            else:
                # Format the JSON plan if it's not a string
                plan_json = json.dumps(verification_result.get("execution_plan"), indent=2)
                console.print(plan_json)

        # Save to file if requested
        if output_file:
            with open(output_file, "w") as f:
                json.dump(verification_result, f, indent=2, default=str)
            console.print(f"\nVerification report saved to {output_file}", style="green")

    except Exception as e:
        console.print(f"Error verifying index usage: {e}", style="red")
        logger.exception("Error during index verification")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
