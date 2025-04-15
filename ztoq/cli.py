"""
Copyright (c) 2025 Eric C.

Mumford (@heymumford) This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.

"""

import json
import logging
import os
from enum import Enum
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

# Bypass local imports to ensure we use the installed alembic
import sys
import os
from pathlib import Path

# Use project root in path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import our alembic proxy that ensures we use the virtualenv version
try:
    # Try to use environment variable if available
    if os.environ.get("ALEMBIC_PATH"):
        alembic_path = os.environ["ALEMBIC_PATH"]
        sys.path.insert(0, alembic_path)
        import alembic.command as alembic_command
        import alembic.config as alembic_config
        sys.path.pop(0)
    # Otherwise, import with a workaround to skip local directory
    else:
        # Try a simple approach - rename local alembic temporarily
        local_alembic = project_root / "alembic"
        local_alembic_tmp = project_root / "alembic_tmp"
        
        alembic_renamed = False
        if local_alembic.exists():
            try:
                os.rename(local_alembic, local_alembic_tmp)
                alembic_renamed = True
                
                # Now import alembic from the environment
                import alembic.command as alembic_command
                import alembic.config as alembic_config
            finally:
                # Restore the original name
                if alembic_renamed:
                    os.rename(local_alembic_tmp, local_alembic)
        else:
            # No local alembic to worry about
            import alembic.command as alembic_command
            import alembic.config as alembic_config
except ImportError as e:
    # If all else fails, use a fallback mechanism
    import subprocess
    result = subprocess.run(
        ["poetry", "run", "python", "-c", 
         "import sys; print(sys.path)"],
        capture_output=True,
        text=True
    )
    sys_path = result.stdout.strip()
    
    # Print error for debugging
    print(f"Failed to import alembic: {e}")
    print(f"Python path: {sys_path}")
    
    # Raise the original error
    raise
from ztoq.core.config import (
    DatabaseConfig,
    QTestConfig,
    ZephyrConfig,
    init_app_config,
)
from ztoq.core.db_manager import SQLDatabaseManager
from ztoq.database_factory import DatabaseFactory, DatabaseType
from ztoq.exporter import ZephyrExportManager
from ztoq.migration import ZephyrToQTestMigration
from ztoq.openapi_parser import (
    extract_api_endpoints,
    load_openapi_spec,
    validate_zephyr_spec,
)
from ztoq.workflow_cli import workflow_app
from ztoq.zephyr_client import ZephyrClient

# Version info
__version__ = "0.4.1"

# Update spec file paths
ZEPHYR_SPEC_PATH = Path(__file__).parent.parent / "docs" / "specs" / "z-openapi.yml"
QTEST_SPEC_PATH = Path(__file__).parent.parent / "docs" / "specs" / "qtest-openapi.yml"

# Initialize console for rich output
console = Console()

# Initialize the CLI app
app = typer.Typer(help="ZTOQ - Zephyr to qTest")


def configure_app(debug: bool = False):
    """
    Configure the application with the specified settings.

    Args:
    ----
        debug: Whether to enable debug mode

    """
    # Initialize the application configuration
    config = init_app_config(debug=debug, app_version=__version__)

    # Configure logging directly
    from ztoq.core.config import configure_logging

    configure_logging(debug=debug)

    return config


# Add CLI callback for global options
@app.callback()
def callback(
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode with verbose logging"),
    version: bool = typer.Option(False, "--version", help="Show the application version and exit"),
):
    """
    ZTOQ - A tool for migrating test data from Zephyr Scale to qTest.

    Use --debug to enable verbose logging.
    """
    if version:
        console.print(f"ZTOQ version: {__version__}")
        raise typer.Exit()

    # Configure application with debug mode if set
    configure_app(debug=debug)


# Get the logger after configuration
logger = logging.getLogger("ztoq")


class OutputFormat(str, Enum):
    JSON = "json"
    SQLITE = "sqlite"
    SQL = "sql"  # New format for SQLAlchemy


class DatabaseType(str, Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


class MigrationPhase(str, Enum):
    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"
    ALL = "all"


@app.command("validate")
def validate_spec(spec_path: Path = typer.Argument(..., help="Path to the OpenAPI spec file")):
    """
    Validate that the OpenAPI spec is for Zephyr Scale API.
    """
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
    """
    List all API endpoints in the OpenAPI spec.
    """
    try:
        console.print(f"Loading OpenAPI spec: {spec_path}")
        spec = load_openapi_spec(spec_path)

        endpoints = extract_api_endpoints(spec)

        table = Table(title="Zephyr Scale API Endpoints")
        table.add_column("Method")
        table.add_column("Path")
        table.add_column("Summary")

        for _endpoint_id, details in endpoints.items():
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
    output_file: Path | None = typer.Option(None, help="Output file path for projects (JSON)"),
):
    """
    Get all projects available in Zephyr Scale.
    """
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
    output_file: Path | None = typer.Option(None, help="Output file path for test cases (JSON)"),
    limit: int = typer.Option(100, help="Maximum number of test cases to fetch"),
):
    """
    Get test cases for a project.
    """
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
    output_file: Path | None = typer.Option(None, help="Output file path for test cycles (JSON)"),
):
    """
    Get test cycles for a project.
    """
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
    format: OutputFormat = typer.Option(
        OutputFormat.JSON,
        help="Output format (json, sqlite, sql)",
    ),
    concurrency: int = typer.Option(2, help="Number of concurrent API requests"),
    # Added database options for SQL format
    db_type: DatabaseType = typer.Option(
        DatabaseType.SQLITE,
        help="Database type for SQL format (sqlite or postgresql)",
    ),
    db_path: Path | None = typer.Option(
        None,
        help="Path to SQLite database file for SQL format (for SQLite only)",
    ),
    host: str | None = typer.Option(
        None,
        help="PostgreSQL host for SQL format (for PostgreSQL only)",
    ),
    port: int | None = typer.Option(
        None,
        help="PostgreSQL port for SQL format (for PostgreSQL only)",
    ),
    username: str | None = typer.Option(
        None,
        help="PostgreSQL username for SQL format (for PostgreSQL only)",
    ),
    password: str | None = typer.Option(
        None,
        help="PostgreSQL password for SQL format (for PostgreSQL only)",
    ),
    database: str | None = typer.Option(
        None,
        help="PostgreSQL database name for SQL format (for PostgreSQL only)",
    ),
):
    """
    Export all test data for a project.
    """
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
                    console.print(
                        "Using PostgreSQL settings from environment variables",
                        style="blue",
                    )
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
            alembic_cfg = alembic_config.Config(str(Path(__file__).parent.parent / "alembic.ini"))
            alembic_cfg.set_main_option("sqlalchemy.url", db_config.get_connection_string())

            # Apply migrations
            alembic_command.upgrade(alembic_cfg, "head")

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
                tasks["test_executions"] = progress.add_task(
                    "Fetching test executions...",
                    total=None,
                )

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
                progress.update(
                    tasks["priorities"],
                    completed=len(priorities),
                    total=len(priorities),
                )

                # Fetch environments
                progress.update(tasks["environments"], description="Fetching environments...")
                environments = list(client.get_environments())
                fetch_results["environments"] = client.create_fetch_result(
                    "environments",
                    environments,
                )
                progress.update(
                    tasks["environments"],
                    completed=len(environments),
                    total=len(environments),
                )

                # Fetch test cases
                progress.update(tasks["test_cases"], description="Fetching test cases...")
                test_cases = list(client.get_test_cases())
                fetch_results["test_cases"] = client.create_fetch_result("test_cases", test_cases)
                progress.update(
                    tasks["test_cases"],
                    completed=len(test_cases),
                    total=len(test_cases),
                )

                # Fetch test cycles
                progress.update(tasks["test_cycles"], description="Fetching test cycles...")
                test_cycles = list(client.get_test_cycles())
                fetch_results["test_cycles"] = client.create_fetch_result(
                    "test_cycles",
                    test_cycles,
                )
                progress.update(
                    tasks["test_cycles"],
                    completed=len(test_cycles),
                    total=len(test_cycles),
                )

                # Fetch test executions
                progress.update(tasks["test_executions"], description="Fetching test executions...")
                test_executions = list(client.get_test_executions())
                fetch_results["test_executions"] = client.create_fetch_result(
                    "test_executions",
                    test_executions,
                )
                progress.update(
                    tasks["test_executions"],
                    completed=len(test_executions),
                    total=len(test_executions),
                )

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
            console.print("\n✅ All test data exported to SQL database", style="green")
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
    projects: list[str] | None = typer.Option(
        None,
        help="Specific projects to export (comma-separated)",
    ),
):
    """
    Export test data for all accessible projects.
    """
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
        DatabaseType.SQLITE,
        help="Database type (sqlite or postgresql)",
    ),
    db_path: Path | None = typer.Option(
        None,
        help="Path to SQLite database file (for SQLite only)",
    ),
    host: str | None = typer.Option(None, help="PostgreSQL host (for PostgreSQL only)"),
    port: int | None = typer.Option(None, help="PostgreSQL port (for PostgreSQL only)"),
    username: str | None = typer.Option(None, help="PostgreSQL username (for PostgreSQL only)"),
    password: str | None = typer.Option(None, help="PostgreSQL password (for PostgreSQL only)"),
    database: str | None = typer.Option(
        None,
        help="PostgreSQL database name (for PostgreSQL only)",
    ),
    drop_existing: bool = typer.Option(False, help="Drop existing tables before initializing"),
):
    """
    Initialize the database schema using Alembic migrations.
    """
    try:
        # Get the appropriate database manager using the factory
        if db_type.value == DatabaseType.SQLITE:
            # For SQLite, use SQLDatabaseManager with Alembic
            db_config = DatabaseConfig(
                db_type=db_type.value,
                db_path=str(db_path) if db_path else None,
            )
            db_manager = SQLDatabaseManager(config=db_config)
        elif db_type.value == DatabaseType.POSTGRESQL:
            # For PostgreSQL, use SQLDatabaseManager with Alembic for schema migrations
            # Check for environment variables if not provided directly
            if not all([host, username, database]):
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
                    console.print(
                        "Using PostgreSQL settings from environment variables",
                        style="blue",
                    )
                else:
                    console.print("Error: PostgreSQL connection details not provided", style="red")
                    raise typer.Exit(code=1)

            db_config = DatabaseConfig(
                db_type=db_type.value,
                host=host,
                port=port,
                username=username,
                password=password,
                database=database,
            )
            db_manager = SQLDatabaseManager(config=db_config)
        else:
            console.print(f"Error: Unsupported database type: {db_type}", style="red")
            raise typer.Exit(code=1)

        if drop_existing:
            console.print("⚠️ Dropping existing database tables...", style="yellow")
            db_manager.drop_all_tables()
            console.print("Existing tables dropped", style="green")

        # Get Alembic config
        alembic_cfg = alembic_config.Config(str(Path(__file__).parent.parent / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", db_config.get_connection_string())

        # Apply migrations
        console.print("Applying database migrations...")
        alembic_command.upgrade(alembic_cfg, "head")
        console.print("✅ Database schema initialized successfully", style="green")

    except Exception as e:
        console.print(f"Error initializing database: {e}", style="red")
        logger.exception("Error during database initialization")
        raise typer.Exit(code=1)


@db_app.command("stats")
def database_stats(
    db_type: DatabaseType = typer.Option(
        DatabaseType.SQLITE,
        help="Database type (sqlite or postgresql)",
    ),
    db_path: Path | None = typer.Option(
        None,
        help="Path to SQLite database file (for SQLite only)",
    ),
    host: str | None = typer.Option(None, help="PostgreSQL host (for PostgreSQL only)"),
    port: int | None = typer.Option(None, help="PostgreSQL port (for PostgreSQL only)"),
    username: str | None = typer.Option(None, help="PostgreSQL username (for PostgreSQL only)"),
    password: str | None = typer.Option(None, help="PostgreSQL password (for PostgreSQL only)"),
    database: str | None = typer.Option(
        None,
        help="PostgreSQL database name (for PostgreSQL only)",
    ),
    project_key: str = typer.Option(..., help="Project key to show statistics for"),
):
    """
    Show database statistics for a project.
    """
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
                console.print("Using PostgreSQL settings from environment variables", style="blue")
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

        # Create database manager using the factory
        db_manager = DatabaseFactory.create_database_manager(
            db_type=DatabaseType.SQLALCHEMY,  # Use SQLAlchemy for migrations
            db_path=str(db_path) if db_path else None,
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
            pool_size=5,
            max_overflow=10,
        )

        # Get statistics
        stats = db_manager.get_statistics(project_key)

        # Display in a table
        table = Table(title=f"Database Statistics for {project_key}")
        table.add_column("Entity Type")
        table.add_column("Count")

        for entity_type, count in stats.items():
            table.add_row(entity_type.replace("_", " ").title(), str(count))

        console.print(table)

    except Exception as e:
        console.print(f"Error getting database statistics: {e}", style="red")
        logger.exception("Error getting database statistics")
        raise typer.Exit(code=1)


@db_app.command("migrate")
def run_migrations(
    db_type: DatabaseType = typer.Option(
        DatabaseType.SQLITE,
        help="Database type (sqlite or postgresql)",
    ),
    db_path: Path | None = typer.Option(
        None,
        help="Path to SQLite database file (for SQLite only)",
    ),
    host: str | None = typer.Option(None, help="PostgreSQL host (for PostgreSQL only)"),
    port: int | None = typer.Option(None, help="PostgreSQL port (for PostgreSQL only)"),
    username: str | None = typer.Option(None, help="PostgreSQL username (for PostgreSQL only)"),
    password: str | None = typer.Option(None, help="PostgreSQL password (for PostgreSQL only)"),
    database: str | None = typer.Option(
        None,
        help="PostgreSQL database name (for PostgreSQL only)",
    ),
):
    """
    Run pending database migrations.
    """
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
                console.print("Using PostgreSQL settings from environment variables", style="blue")
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
        alembic_cfg = alembic_config.Config(str(Path(__file__).parent.parent / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", db_config.get_connection_string())

        # Apply migrations
        console.print("Applying pending database migrations...")
        alembic_command.upgrade(alembic_cfg, "head")
        console.print("✅ Database migrations applied successfully", style="green")

    except Exception as e:
        console.print(f"Error running migrations: {e}", style="red")
        logger.exception("Error during migrations")
        raise typer.Exit(code=1)


# Create a sub-command group for migration operations
migrate_app = typer.Typer(help="Zephyr to qTest migration operations")
app.add_typer(migrate_app, name="migrate")

# Create a sub-command group for docs operations
docs_app = typer.Typer(help="Documentation operations")
app.add_typer(docs_app, name="docs")

# Add workflow orchestration commands
app.add_typer(workflow_app, name="workflow")


@docs_app.command("serve")
def serve_docs(
    port: int = typer.Option(8000, help="Port to host the documentation server on"),
    no_browser: bool = typer.Option(
        False,
        help="Don't automatically open the docs in a web browser",
    ),
    format: str = typer.Option(
        "html",
        help="Output format for the documentation (html, dirhtml, singlehtml)",
    ),
):
    """
    Build and serve Sphinx documentation in a web browser.

    This command builds the Sphinx documentation and starts a local web server
    to make the docs accessible via a web browser.
    """
    try:
        # Import here to avoid dependencies for those who don't need docs
        import http.server
        import importlib.util
        import os
        import socketserver
        import subprocess
        import sys
        import threading
        import time
        import webbrowser
        from pathlib import Path

        # Find the project root and docs directory
        project_root = Path(__file__).resolve().parent.parent
        docs_path = project_root / "docs"
        scripts_path = project_root / "scripts"
        docs_script = scripts_path / "build_and_host_docs.py"

        console.print("Building and serving documentation...")

        # Execute the docs script if it exists
        if docs_script.exists():
            args = [sys.executable, str(docs_script)]
            if port != 8000:
                args.extend(["--port", str(port)])
            if no_browser:
                args.append("--no-browser")
            if format != "html":
                args.extend(["--format", format])

            try:
                subprocess.run(args, check=True)
                return  # If the script ran successfully, we can return
            except subprocess.CalledProcessError as e:
                console.print(f"Documentation script encountered an error: {e}", style="yellow")
                console.print("Falling back to built-in documentation server...", style="yellow")
        else:
            console.print(
                "Documentation script not found. Building documentation directly...",
                style="yellow",
            )

        # Fallback to built-in documentation server
        # Check dependencies
        dependencies = ["sphinx", "sphinx_rtd_theme", "recommonmark", "myst_parser"]
        missing = []

        for dep in dependencies:
            if importlib.util.find_spec(dep) is None:
                missing.append(dep)

        if missing:
            console.print(f"Missing dependencies: {', '.join(missing)}", style="yellow")
            console.print("Installing missing dependencies...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
                console.print("Dependencies installed successfully.", style="green")
            except subprocess.CalledProcessError:
                console.print(
                    "Failed to install dependencies. Please install them manually:",
                    style="red",
                )
                console.print(f"pip install {' '.join(missing)}")
                console.print("Then run 'ztoq docs serve' again.")
                raise typer.Exit(code=1)

        # Build docs
        sphinx_dir = docs_path / "sphinx"
        if not sphinx_dir.exists():
            console.print(f"Sphinx directory not found: {sphinx_dir}", style="red")
            raise typer.Exit(code=1)

        console.print(f"Building {format} documentation...")
        try:
            process = subprocess.run(
                ["make", "-C", str(sphinx_dir), format],
                capture_output=True,
                text=True,
                check=True,
            )
            if process.stdout:
                console.print("Build output:", style="blue")
                console.print(process.stdout)

            html_dir = sphinx_dir / "build" / format
            if not html_dir.exists():
                console.print(f"Build directory not found: {html_dir}", style="red")
                raise typer.Exit(code=1)

            # Start HTTP server
            os.chdir(html_dir)

            class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
                def log_message(self, format, *args):
                    # Override to be quieter
                    pass

            # Find an available port - try up to 10 ports
            max_attempts = 10
            attempts = 0
            current_port = port
            httpd = None

            while attempts < max_attempts and not httpd:
                try:
                    httpd = socketserver.TCPServer(("", current_port), QuietHTTPRequestHandler)
                except OSError:
                    console.print(
                        f"Port {current_port} is in use, trying {current_port+1}...",
                        style="yellow",
                    )
                    current_port += 1
                    attempts += 1

            if not httpd:
                console.print(
                    f"Failed to find an available port after {max_attempts} attempts",
                    style="red",
                )
                console.print(
                    f"You can view the documentation directly by opening: {html_dir}/index.html",
                    style="blue",
                )
                raise typer.Exit(code=1)

            console.print(
                f"Serving documentation at http://localhost:{current_port}/",
                style="green",
            )

            # Open browser
            if not no_browser:

                def open_browser_delayed():
                    time.sleep(1.0)  # Give the server a moment to start
                    webbrowser.open(f"http://localhost:{current_port}/")

                threading.Thread(target=open_browser_delayed).start()

            console.print("Press Ctrl+C to stop the server")

            try:
                httpd.serve_forever()
            except (KeyboardInterrupt, ValueError, OSError) as e:
                if isinstance(e, KeyboardInterrupt):
                    console.print("Server stopped by user", style="yellow")
                else:
                    console.print(f"Server error: {e}", style="red")

                # Show alternative way to access docs
                console.print(
                    f"You can view the documentation directly by opening: {html_dir}/index.html",
                    style="blue",
                )

        except subprocess.CalledProcessError as e:
            console.print(f"Failed to build documentation: {e}", style="red")
            if e.stderr:
                console.print("Error details:", style="red")
                console.print(e.stderr)
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(f"Error serving documentation: {e}", style="red")
        logger.exception("Error serving documentation")
        console.print(
            "You can try running 'make -C docs/sphinx html' and then 'python -m http.server 8000' in the build directory.",
            style="blue",
        )
        raise typer.Exit(code=1)


@migrate_app.command("run")
def run_migration(
    # Zephyr configuration
    zephyr_spec_path: Path = typer.Option(
        ZEPHYR_SPEC_PATH,
        help="Path to the Zephyr OpenAPI spec file",
    ),
    zephyr_base_url: str = typer.Option(..., help="Zephyr Scale API base URL"),
    zephyr_api_token: str = typer.Option(..., help="Zephyr Scale API token"),
    zephyr_project_key: str = typer.Option(..., help="Zephyr project key to migrate"),
    # qTest configuration
    qtest_base_url: str = typer.Option(..., help="qTest API base URL"),
    qtest_username: str = typer.Option(..., help="qTest username"),
    qtest_password: str = typer.Option(..., help="qTest password"),
    qtest_project_id: int = typer.Option(..., help="qTest project ID"),
    # Database configuration
    db_type: DatabaseType = typer.Option(
        DatabaseType.SQLITE,
        help="Database type (sqlite or postgresql)",
    ),
    db_path: Path | None = typer.Option(
        None,
        help="Path to SQLite database file (for SQLite only)",
    ),
    host: str | None = typer.Option(None, help="PostgreSQL host (for PostgreSQL only)"),
    port: int | None = typer.Option(None, help="PostgreSQL port (for PostgreSQL only)"),
    username: str | None = typer.Option(None, help="PostgreSQL username (for PostgreSQL only)"),
    password: str | None = typer.Option(None, help="PostgreSQL password (for PostgreSQL only)"),
    database: str | None = typer.Option(
        None,
        help="PostgreSQL database name (for PostgreSQL only)",
    ),
    # Migration options
    phase: MigrationPhase = typer.Option(
        MigrationPhase.ALL,
        help="Migration phase to run (extract, transform, load, or all)",
    ),
    batch_size: int = typer.Option(50, help="Number of items to process in a batch"),
    max_workers: int = typer.Option(
        5,
        help="Maximum number of concurrent workers for parallel processing",
    ),
    attachments_dir: Path | None = typer.Option(
        None,
        help="Optional directory for storing attachments",
    ),
):
    """
    Run migration from Zephyr Scale to qTest.

    This command migrates test data from Zephyr Scale to qTest using a three-
    phase ETL (Extract, Transform, Load) process with a database as an
    intermediate store.

    """
    try:
        # Setup configurations
        zephyr_config = ZephyrConfig(
            base_url=zephyr_base_url,
            api_token=zephyr_api_token,
            project_key=zephyr_project_key,
        )

        qtest_config = QTestConfig(
            base_url=qtest_base_url,
            username=qtest_username,
            password=qtest_password,
            project_id=qtest_project_id,
        )

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
                console.print("Using PostgreSQL settings from environment variables", style="blue")
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

        # Create database manager using the factory
        db_manager = DatabaseFactory.create_database_manager(
            db_type=DatabaseType.SQLALCHEMY,  # Use SQLAlchemy for migrations
            db_path=str(db_path) if db_path else None,
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
            pool_size=5,
            max_overflow=10,
        )

        # Ensure the database is initialized
        console.print("Ensuring database schema is up to date...")
        alembic_cfg = alembic_config.Config(str(Path(__file__).parent.parent / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", db_config.get_connection_string())
        alembic_command.upgrade(alembic_cfg, "head")

        # Create migration manager
        migration = ZephyrToQTestMigration(
            zephyr_config=zephyr_config,
            qtest_config=qtest_config,
            database_manager=db_manager,
            batch_size=batch_size,
            max_workers=max_workers,
            attachments_dir=attachments_dir,
        )

        # Determine phases to run
        phases = []
        phases = ["extract", "transform", "load"] if phase == MigrationPhase.ALL else [phase.value]

        # Run migration
        console.print(
            f"Starting migration for project {zephyr_project_key} to qTest project {qtest_project_id}",
        )
        console.print(f"Running phases: {', '.join(phases)}")

        # Execute migration with progress tracking
        migration.run_migration(phases=phases)

        # Print migration status
        table = Table(title=f"Migration Status for {zephyr_project_key}")
        table.add_column("Phase")
        table.add_column("Status")

        table.add_row("Extract", migration.state.extraction_status)
        table.add_row("Transform", migration.state.transformation_status)
        table.add_row("Load", migration.state.loading_status)

        console.print(table)

        if migration.state.error_message:
            console.print(f"Error during migration: {migration.state.error_message}", style="red")
        else:
            console.print("✅ Migration completed successfully", style="green")

    except Exception as e:
        console.print(f"Error during migration: {e}", style="red")
        logger.exception("Error during migration")
        raise typer.Exit(code=1)


@migrate_app.command("status")
def migration_status(
    # Database configuration
    db_type: DatabaseType = typer.Option(
        DatabaseType.SQLITE,
        help="Database type (sqlite or postgresql)",
    ),
    db_path: Path | None = typer.Option(
        None,
        help="Path to SQLite database file (for SQLite only)",
    ),
    host: str | None = typer.Option(None, help="PostgreSQL host (for PostgreSQL only)"),
    port: int | None = typer.Option(None, help="PostgreSQL port (for PostgreSQL only)"),
    username: str | None = typer.Option(None, help="PostgreSQL username (for PostgreSQL only)"),
    password: str | None = typer.Option(None, help="PostgreSQL password (for PostgreSQL only)"),
    database: str | None = typer.Option(
        None,
        help="PostgreSQL database name (for PostgreSQL only)",
    ),
    # Project key
    project_key: str = typer.Option(..., help="Zephyr project key to check status for"),
):
    """
    Check the status of an ongoing migration.
    """
    try:
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
                console.print("Using PostgreSQL settings from environment variables", style="blue")
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

        # Create database manager using the factory
        db_manager = DatabaseFactory.create_database_manager(
            db_type=DatabaseType.SQLALCHEMY,  # Use SQLAlchemy for migrations
            db_path=str(db_path) if db_path else None,
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
            pool_size=5,
            max_overflow=10,
        )

        # Get migration state
        state = db_manager.get_migration_state(project_key)

        if not state:
            console.print(f"No migration found for project {project_key}", style="yellow")
            return

        # Print migration status
        table = Table(title=f"Migration Status for {project_key}")
        table.add_column("Phase")
        table.add_column("Status")
        table.add_column("Last Updated")

        table.add_row(
            "Extract",
            state.get("extraction_status", "not_started"),
            state.get("last_updated", ""),
        )
        table.add_row(
            "Transform",
            state.get("transformation_status", "not_started"),
            state.get("last_updated", ""),
        )
        table.add_row(
            "Load",
            state.get("loading_status", "not_started"),
            state.get("last_updated", ""),
        )

        console.print(table)

        if state.get("error_message"):
            console.print(f"Error: {state.get('error_message')}", style="red")

        # Show counts of migrated entities
        entity_counts = db_manager.get_entity_mapping_counts(project_key)

        if entity_counts:
            count_table = Table(title="Migrated Entities")
            count_table.add_column("Entity Type")
            count_table.add_column("Count")

            for entity_type, count in entity_counts.items():
                # Format entity type for display
                display_name = entity_type.replace("_", " ").title()
                count_table.add_row(display_name, str(count))

            console.print(count_table)

    except Exception as e:
        console.print(f"Error checking migration status: {e}", style="red")
        logger.exception("Error checking migration status")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
