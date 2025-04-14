import typer
import json
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
    format: OutputFormat = typer.Option(OutputFormat.JSON, help="Output format (json or sqlite)"),
    concurrency: int = typer.Option(2, help="Number of concurrent API requests"),
):
    """Export all test data for a project."""
    try:
        config = ZephyrConfig(
            base_url=base_url,
            api_token=api_token,
            project_key=project_key,
        )

        export_manager = ZephyrExportManager(
            config=config,
            output_format=format.value,
            output_dir=output_dir,
            spec_path=spec_path,
            concurrency=concurrency,
        )

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


if __name__ == "__main__":
    app()
