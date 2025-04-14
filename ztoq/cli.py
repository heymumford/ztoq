"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import typer
import json
import os
from enum import Enum
from pathlib import Path
from typing import List, Optional
import logging
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.logging import RichHandler
from ztoq.models import ZephyrConfig
from ztoq.zephyr_client import ZephyrClient
from ztoq.openapi_parser import load_openapi_spec, validate_zephyr_spec, extract_api_endpoints
from ztoq.exporter import ZephyrExportManager
from ztoq.core.db_manager import DatabaseConfig, SQLDatabaseManager
from alembic.config import Config
from alembic import command

# Update spec file paths
ZEPHYR_SPEC_PATH = Path(__file__).parent.parent / "docs" / "specs" / "z-openapi.yml"
QTEST_SPEC_PATH = Path(__file__).parent.parent / "docs" / "specs" / "qtest-openapi.yml"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger("ztoq")

app = typer.Typer(help="ZTOQ - Zephyr to qTest")
console = Console()


class OutputFormat(str, Enum):
    JSON = "json"
    SQLITE = "sqlite"
    SQL = "sql"  # New format for SQLAlchemy
    
class DatabaseType(str, Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


@app.command("validate")


def validate_spec(spec_path: Path = typer.Argument(..., help="Path to the OpenAPI spec file")):
    """Validate that the OpenAPI spec is for Zephyr Scale API."""
    try:
        console.print(f"Validating OpenAPI spec: {spec_path}")
        spec = load_openapi_spec(spec_path)

        is_valid = validate_zephyr_spec(spec)
        if is_valid:
            console.print("✅ Valid Zephyr Scale API specification", style="green")
        else:
            console.print("❌ Not a valid Zephyr Scale API specification", style="red")
            raise typer.Exit(code=1)

    except FileNotFoundError as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(code=1)


@app.command("list-endpoints")


def list_endpoints(spec_path: Path = typer.Argument(..., help="Path to the OpenAPI spec file")):
    """List all API endpoints in the OpenAPI spec."""
    try:
        console.print(f"Loading OpenAPI spec: {spec_path}")
        spec = load_openapi_spec(spec_path)

        endpoints = extract_api_endpoints(spec)

        table = Table(title="Zephyr Scale API Endpoints")
        table.add_column("Method")
        table.add_column("Path")
        table.add_column("Summary")

        for endpoint_id, details in endpoints.items():
            table.add_row(
                details["method"].upper(),
                    details["path"],
                    details["summary"],
                )

        console.print(table)

    except FileNotFoundError as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(code=1)


@app.command("get-projects")


def get_projects(
    spec_path: Path = typer.Argument(..., help="Path to the OpenAPI spec file"),
        base_url: str = typer.Option(..., help="Zephyr Scale API base URL"),
        api_token: str = typer.Option(..., help="Zephyr Scale API token"),
        output_file: Optional[Path] = typer.Option(None, help="Output file path for projects (JSON)"),
):
    """Get all projects available in Zephyr Scale."""
    try:
        config = ZephyrConfig(
            base_url=base_url,
                api_token=api_token,
                project_key="",  # Not needed for listing projects
        )

        client = ZephyrClient.from_openapi_spec(spec_path, config)

        console.print("Fetching projects")
        projects = client.get_projects()

        console.print(f"Found {len(projects)} projects")

        if output_file:
            with open(output_file, "w") as f:
                json.dump([project.dict() for project in projects], f, indent=2)
            console.print(f"Projects written to {output_file}", style="green")
        else:
            table = Table(title="Zephyr Scale Projects")
            table.add_column("Key")
            table.add_column("Name")
            table.add_column("ID")

            for project in projects:
                table.add_row(
                    project.key,
                        project.name,
                        project.id,
                    )

            console.print(table)

    except Exception as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(code=1)


@app.command("get-test-cases")


def get_test_cases(
    spec_path: Path = typer.Argument(..., help="Path to the OpenAPI spec file"),
        base_url: str = typer.Option(..., help="Zephyr Scale API base URL"),
        api_token: str = typer.Option(..., help="Zephyr Scale API token"),
        project_key: str = typer.Option(..., help="JIRA project key"),
        output_file: Optional[Path] = typer.Option(None, help="Output file path for test cases (JSON)"),
        limit: int = typer.Option(100, help="Maximum number of test cases to fetch"),
):
    """Get test cases for a project."""
    try:
        config = ZephyrConfig(
            base_url=base_url,
                api_token=api_token,
                project_key=project_key,
            )

        client = ZephyrClient.from_openapi_spec(spec_path, config)

        console.print(f"Fetching test cases for project: {project_key}")
        test_cases = []
        test_case_iter = client.get_test_cases()

        with Progress(
            TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
            task = progress.add_task("Fetching test cases", total=limit)

            for tc in test_case_iter:
                test_cases.append(tc)
                progress.update(task, advance=1)

                if len(test_cases) >= limit:
                    break

        console.print(f"Found {len(test_cases)} test cases")

        if output_file:
            with open(output_file, "w") as f:
                json.dump([tc.dict() for tc in test_cases], f, indent=2)
            console.print(f"Test cases written to {output_file}", style="green")
        else:
            table = Table(title=f"Test Cases for {project_key}")
            table.add_column("Key")
            table.add_column("Name")
            table.add_column("Status")

            for tc in test_cases:
                table.add_row(
                    tc.key,
                        tc.name,
                        tc.status or "N/A",
                    )

            console.print(table)

    except Exception as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(code=1)


@app.command("get-test-cycles")


def get_test_cycles(
    spec_path: Path = typer.Argument(..., help="Path to the OpenAPI spec file"),
        base_url: str = typer.Option(..., help="Zephyr Scale API base URL"),
        api_token: str = typer.Option(..., help="Zephyr Scale API token"),
        project_key: str = typer.Option(..., help="JIRA project key"),
        output_file: Optional[Path] = typer.Option(
        None, help="Output file path for test cycles (JSON)"
    ),
):
    """Get test cycles for a project."""
    try:
        config = ZephyrConfig(
            base_url=base_url,
                api_token=api_token,
                project_key=project_key,
            )

        client = ZephyrClient.from_openapi_spec(spec_path, config)

        console.print(f"Fetching test cycles for project: {project_key}")
        test_cycles = list(client.get_test_cycles())

        console.print(f"Found {len(test_cycles)} test cycles")

        if output_file:
            with open(output_file, "w") as f:
                json.dump([tc.dict() for tc in test_cycles], f, indent=2)
            console.print(f"Test cycles written to {output_file}", style="green")
        else:
            table = Table(title=f"Test Cycles for {project_key}")
            table.add_column("Key")
            table.add_column("Name")
            table.add_column("Status")

            for tc in test_cycles:
                table.add_row(
                    tc.key,
                        tc.name,
                        tc.status or "N/A",
                    )

            console.print(table)

    except Exception as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(code=1)


@app.command("export-project")
def export_project(
    spec_path: Path = typer.Argument(..., help="Path to the OpenAPI spec file"),
    base_url: str = typer.Option(..., help="Zephyr Scale API base URL"),
    api_token: str = typer.Option(..., help="Zephyr Scale API token"),
    project_key: str = typer.Option(..., help="JIRA project key"),
    output_dir: Path = typer.Option(..., help="Output directory for all test data"),
    format: OutputFormat = typer.Option(OutputFormat.JSON, help="Output format (json, sqlite, sql)"),
    concurrency: int = typer.Option(2, help="Number of concurrent API requests"),
    # Added database options for SQL format
    db_type: DatabaseType = typer.Option(
        DatabaseType.SQLITE, help="Database type for SQL format (sqlite or postgresql)"
    ),
    db_path: Optional[Path] = typer.Option(
        None, help="Path to SQLite database file for SQL format (for SQLite only)"
    ),
    host: Optional[str] = typer.Option(
        None, help="PostgreSQL host for SQL format (for PostgreSQL only)"
    ),
    port: Optional[int] = typer.Option(
        None, help="PostgreSQL port for SQL format (for PostgreSQL only)"
    ),
    username: Optional[str] = typer.Option(
        None, help="PostgreSQL username for SQL format (for PostgreSQL only)"
    ),
    password: Optional[str] = typer.Option(
        None, help="PostgreSQL password for SQL format (for PostgreSQL only)"
    ),
    database: Optional[str] = typer.Option(
        None, help="PostgreSQL database name for SQL format (for PostgreSQL only)"
    ),
):
    """Export all test data for a project."""
    try:
        config = ZephyrConfig(
            base_url=base_url,
            api_token=api_token,
            project_key=project_key,
        )

        # For SQL format, check if database options are properly provided
        if format == OutputFormat.SQL:
            # Check for environment variables if not provided directly (PostgreSQL)
            if db_type == DatabaseType.POSTGRESQL and not all([host, username, database]):
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
                    console.print(f"Using PostgreSQL settings from environment variables", style="blue")
                else:
                    console.print("Error: PostgreSQL connection details not provided", style="red")
                    raise typer.Exit(code=1)
            
            # Create database configuration
            db_config = DatabaseConfig(
                db_type=db_type.value,
                db_path=str(db_path) if db_path else None,
                host=host,
                port=port,
                username=username,
                password=password,
                database=database,
            )
            
            # Create database manager
            db_manager = SQLDatabaseManager(config=db_config)
            
            # Ensure the database is initialized
            console.print("Ensuring database schema is up to date...")
            
            # Get Alembic config
            alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
            alembic_cfg.set_main_option("sqlalchemy.url", db_config.get_connection_string())
            
            # Apply migrations
            command.upgrade(alembic_cfg, "head")

        # For legacy formats (JSON, SQLite)
        export_manager = ZephyrExportManager(
            config=config,
            output_format=format.value,
            output_dir=output_dir,
            spec_path=spec_path,
            concurrency=concurrency,
        )

        stats = {}
        if format == OutputFormat.SQL:
            # Use the SQLAlchemy-based database manager for SQL format
            console.print(f"Exporting project {project_key} to SQL database...")
            
            # Fetch data with the client
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                # Create Zephyr client
                client = ZephyrClient.from_openapi_spec(spec_path, config)
                
                # Fetch all entity types with progress reporting
                fetch_results = {}
                
                # Create tasks for progress tracking
                tasks = {}
                tasks["project"] = progress.add_task("Fetching project info...", total=1)
                tasks["folders"] = progress.add_task("Fetching folders...", total=None)
                tasks["statuses"] = progress.add_task("Fetching statuses...", total=None)
                tasks["priorities"] = progress.add_task("Fetching priorities...", total=None)
                tasks["environments"] = progress.add_task("Fetching environments...", total=None)
                tasks["test_cases"] = progress.add_task("Fetching test cases...", total=None)
                tasks["test_cycles"] = progress.add_task("Fetching test cycles...", total=None)
                tasks["test_executions"] = progress.add_task("Fetching test executions...", total=None)
                
                # Fetch project
                progress.update(tasks["project"], description="Fetching project info...")
                project = client.get_project(project_key)
                fetch_results["project"] = client.create_fetch_result("project", [project])
                progress.update(tasks["project"], completed=1)
                
                # Fetch folders
                progress.update(tasks["folders"], description="Fetching folders...")
                folders = list(client.get_folders())
                fetch_results["folders"] = client.create_fetch_result("folders", folders)
                progress.update(tasks["folders"], completed=len(folders), total=len(folders))
                
                # Fetch statuses
                progress.update(tasks["statuses"], description="Fetching statuses...")
                statuses = list(client.get_statuses())
                fetch_results["statuses"] = client.create_fetch_result("statuses", statuses)
                progress.update(tasks["statuses"], completed=len(statuses), total=len(statuses))
                
                # Fetch priorities
                progress.update(tasks["priorities"], description="Fetching priorities...")
                priorities = list(client.get_priorities())
                fetch_results["priorities"] = client.create_fetch_result("priorities", priorities)
                progress.update(tasks["priorities"], completed=len(priorities), total=len(priorities))
                
                # Fetch environments
                progress.update(tasks["environments"], description="Fetching environments...")
                environments = list(client.get_environments())
                fetch_results["environments"] = client.create_fetch_result("environments", environments)
                progress.update(tasks["environments"], completed=len(environments), total=len(environments))
                
                # Fetch test cases
                progress.update(tasks["test_cases"], description="Fetching test cases...")
                test_cases = list(client.get_test_cases())
                fetch_results["test_cases"] = client.create_fetch_result("test_cases", test_cases)
                progress.update(tasks["test_cases"], completed=len(test_cases), total=len(test_cases))
                
                # Fetch test cycles
                progress.update(tasks["test_cycles"], description="Fetching test cycles...")
                test_cycles = list(client.get_test_cycles())
                fetch_results["test_cycles"] = client.create_fetch_result("test_cycles", test_cycles)
                progress.update(tasks["test_cycles"], completed=len(test_cycles), total=len(test_cycles))
                
                # Fetch test executions
                progress.update(tasks["test_executions"], description="Fetching test executions...")
                test_executions = list(client.get_test_executions())
                fetch_results["test_executions"] = client.create_fetch_result("test_executions", test_executions)
                progress.update(tasks["test_executions"], completed=len(test_executions), total=len(test_executions))
                
                # Store in the database
                progress.update(tasks["project"], description="Saving data to database...")
                stats = db_manager.save_project_data(project_key, fetch_results)
        else:
            # Use the legacy exporter for JSON and SQLite formats
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                stats = export_manager.export_project(project_key, progress=progress)

        # Print summary
        table = Table(title=f"Export Summary for {project_key}")
        table.add_column("Data Type")
        table.add_column("Count")

        for data_type, count in stats.items():
            table.add_row(data_type.replace("_", " ").title(), str(count))

        console.print(table)
        
        if format == OutputFormat.SQL:
            console.print(f"\n✅ All test data exported to SQL database", style="green")
        else:
            console.print(f"\n✅ All test data exported to {output_dir}", style="green")

    except Exception as e:
        console.print(f"Error: {e}", style="red")
        logger.exception("Error during export")
        raise typer.Exit(code=1)


@app.command("export-all")


def export_all(
    spec_path: Path = typer.Argument(..., help="Path to the OpenAPI spec file"),
        base_url: str = typer.Option(..., help="Zephyr Scale API base URL"),
        api_token: str = typer.Option(..., help="Zephyr Scale API token"),
        output_dir: Path = typer.Option(..., help="Output directory for all test data"),
        format: OutputFormat = typer.Option(OutputFormat.JSON, help="Output format (json or sqlite)"),
        concurrency: int = typer.Option(2, help="Number of concurrent API requests"),
        projects: Optional[List[str]] = typer.Option(
        None, help="Specific projects to export (comma-separated)"
    ),
):
    """Export test data for all accessible projects."""
    try:
        # Create a config with an empty project key, we'll get the actual projects list first
        config = ZephyrConfig(
            base_url=base_url,
                api_token=api_token,
                project_key="",
            )

        # Create client to fetch projects
        client = ZephyrClient.from_openapi_spec(spec_path, config)

        # Get available projects
        all_projects = client.get_projects()
        project_list = [p.key for p in all_projects]

        # Filter projects if specified
        if projects:
            project_list = [p for p in project_list if p in projects]

        if not project_list:
            console.print("No projects to export.", style="yellow")
            return

        console.print(f"Exporting {len(project_list)} projects: {', '.join(project_list)}")

        # Create export manager
        export_manager = ZephyrExportManager(
            config=config,
                output_format=format.value,
                output_dir=output_dir,
                spec_path=spec_path,
                concurrency=concurrency,
            )

        # Process each project
        for idx, project_key in enumerate(project_list, 1):
            console.print(f"\n[{idx}/{len(project_list)}] Exporting {project_key}...")

            with Progress(
                TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    TimeElapsedColumn(),
                    console=console,
                ) as progress:
                try:
                    stats = export_manager.export_project(project_key, progress=progress)

                    # Print summary
                    table = Table(title=f"Export Summary for {project_key}")
                    table.add_column("Data Type")
                    table.add_column("Count")

                    for data_type, count in stats.items():
                        table.add_row(data_type.replace("_", " ").title(), str(count))

                    console.print(table)
                    console.print(f"✅ {project_key} export complete", style="green")
                except Exception as e:
                    console.print(f"❌ Error exporting {project_key}: {e}", style="red")
                    logger.exception(f"Error exporting {project_key}")

        console.print(f"\n✅ All projects exported to {output_dir}", style="green")

    except Exception as e:
        console.print(f"Error: {e}", style="red")
        logger.exception("Error during export")
        raise typer.Exit(code=1)


# Create a sub-command group for database operations
db_app = typer.Typer(help="Database operations")
app.add_typer(db_app, name="db")


@db_app.command("init")
def init_database(
    db_type: DatabaseType = typer.Option(
        DatabaseType.SQLITE, help="Database type (sqlite or postgresql)"
    ),
    db_path: Optional[Path] = typer.Option(
        None, help="Path to SQLite database file (for SQLite only)"
    ),
    host: Optional[str] = typer.Option(
        None, help="PostgreSQL host (for PostgreSQL only)"
    ),
    port: Optional[int] = typer.Option(
        None, help="PostgreSQL port (for PostgreSQL only)"
    ),
    username: Optional[str] = typer.Option(
        None, help="PostgreSQL username (for PostgreSQL only)"
    ),
    password: Optional[str] = typer.Option(
        None, help="PostgreSQL password (for PostgreSQL only)"
    ),
    database: Optional[str] = typer.Option(
        None, help="PostgreSQL database name (for PostgreSQL only)"
    ),
    drop_existing: bool = typer.Option(
        False, help="Drop existing tables before initializing"
    ),
):
    """Initialize the database schema using Alembic migrations."""
    try:
        # Check for environment variables if not provided directly
        if db_type == DatabaseType.POSTGRESQL and not all([host, username, database]):
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
                console.print(f"Using PostgreSQL settings from environment variables", style="blue")
            else:
                console.print("Error: PostgreSQL connection details not provided", style="red")
                raise typer.Exit(code=1)
        
        # Create database configuration
        db_config = DatabaseConfig(
            db_type=db_type.value,
            db_path=str(db_path) if db_path else None,
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
        )
        
        # Create database manager
        db_manager = SQLDatabaseManager(config=db_config)
        
        if drop_existing:
            console.print("⚠️ Dropping existing database tables...", style="yellow")
            db_manager.drop_all_tables()
            console.print("Existing tables dropped", style="green")
        
        # Get Alembic config
        alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", db_config.get_connection_string())
        
        # Apply migrations
        console.print("Applying database migrations...")
        command.upgrade(alembic_cfg, "head")
        console.print("✅ Database schema initialized successfully", style="green")
        
    except Exception as e:
        console.print(f"Error initializing database: {e}", style="red")
        logger.exception("Error during database initialization")
        raise typer.Exit(code=1)


@db_app.command("stats")
def database_stats(
    db_type: DatabaseType = typer.Option(
        DatabaseType.SQLITE, help="Database type (sqlite or postgresql)"
    ),
    db_path: Optional[Path] = typer.Option(
        None, help="Path to SQLite database file (for SQLite only)"
    ),
    host: Optional[str] = typer.Option(
        None, help="PostgreSQL host (for PostgreSQL only)"
    ),
    port: Optional[int] = typer.Option(
        None, help="PostgreSQL port (for PostgreSQL only)"
    ),
    username: Optional[str] = typer.Option(
        None, help="PostgreSQL username (for PostgreSQL only)"
    ),
    password: Optional[str] = typer.Option(
        None, help="PostgreSQL password (for PostgreSQL only)"
    ),
    database: Optional[str] = typer.Option(
        None, help="PostgreSQL database name (for PostgreSQL only)"
    ),
    project_key: str = typer.Option(
        ..., help="Project key to show statistics for"
    ),
):
    """Show database statistics for a project."""
    try:
        # Check for environment variables if not provided directly
        if db_type == DatabaseType.POSTGRESQL and not all([host, username, database]):
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
                console.print(f"Using PostgreSQL settings from environment variables", style="blue")
            else:
                console.print("Error: PostgreSQL connection details not provided", style="red")
                raise typer.Exit(code=1)
        
        # Create database configuration
        db_config = DatabaseConfig(
            db_type=db_type.value,
            db_path=str(db_path) if db_path else None,
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
        )
        
        # Create database manager
        db_manager = SQLDatabaseManager(config=db_config)
        
        # Get statistics
        stats = db_manager.get_statistics(project_key)
        
        # Display in a table
        table = Table(title=f"Database Statistics for {project_key}")
        table.add_column("Entity Type")
        table.add_column("Count")
        
        for entity_type, count in stats.items():
            table.add_row(
                entity_type.replace("_", " ").title(),
                str(count)
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"Error getting database statistics: {e}", style="red")
        logger.exception("Error getting database statistics")
        raise typer.Exit(code=1)


@db_app.command("migrate")
def run_migrations(
    db_type: DatabaseType = typer.Option(
        DatabaseType.SQLITE, help="Database type (sqlite or postgresql)"
    ),
    db_path: Optional[Path] = typer.Option(
        None, help="Path to SQLite database file (for SQLite only)"
    ),
    host: Optional[str] = typer.Option(
        None, help="PostgreSQL host (for PostgreSQL only)"
    ),
    port: Optional[int] = typer.Option(
        None, help="PostgreSQL port (for PostgreSQL only)"
    ),
    username: Optional[str] = typer.Option(
        None, help="PostgreSQL username (for PostgreSQL only)"
    ),
    password: Optional[str] = typer.Option(
        None, help="PostgreSQL password (for PostgreSQL only)"
    ),
    database: Optional[str] = typer.Option(
        None, help="PostgreSQL database name (for PostgreSQL only)"
    ),
):
    """Run pending database migrations."""
    try:
        # Check for environment variables if not provided directly
        if db_type == DatabaseType.POSTGRESQL and not all([host, username, database]):
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
                console.print(f"Using PostgreSQL settings from environment variables", style="blue")
            else:
                console.print("Error: PostgreSQL connection details not provided", style="red")
                raise typer.Exit(code=1)
        
        # Create database configuration
        db_config = DatabaseConfig(
            db_type=db_type.value,
            db_path=str(db_path) if db_path else None,
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
        )
        
        # Get Alembic config
        alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", db_config.get_connection_string())
        
        # Apply migrations
        console.print("Applying pending database migrations...")
        command.upgrade(alembic_cfg, "head")
        console.print("✅ Database migrations applied successfully", style="green")
        
    except Exception as e:
        console.print(f"Error running migrations: {e}", style="red")
        logger.exception("Error during migrations")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
