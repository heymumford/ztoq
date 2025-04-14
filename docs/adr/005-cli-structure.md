# ADR-005: CLI Structure Using Typer

## Status

Accepted

## Context

ZTOQ is primarily a command-line tool, so it needs a well-structured, user-friendly command-line interface. We need to provide a variety of commands for different operations (validating OpenAPI specs, listing endpoints, exporting data, etc.) with appropriate arguments and options.

Options considered for CLI implementation:
1. Python's built-in argparse library
2. Click library
3. Typer (built on top of Click)
4. docopt
5. Fire (automatic CLI from any object)

Key requirements for our CLI:
- Type-annotated parameters for better documentation and validation
- Good help text generation
- Support for sub-commands
- Support for progress bars and rich terminal output
- Easy to extend with new commands
- Intuitive interface for users

## Decision

We will use Typer for implementing the CLI, combined with Rich for terminal output formatting.

## Consequences

### Positive

- Typer leverages Python type annotations for automatic parameter validation
- Built on top of Click, a mature and stable CLI library
- Excellent help text generation and documentation
- First-class support for subcommands and command groups
- Good integration with Rich for progress bars, tables, and formatted output
- Less boilerplate compared to argparse
- Type checking support for IDE assistance and runtime validation

### Negative

- Additional dependencies in the project
- Slightly more complex than simpler solutions like Fire for very basic CLIs
- Less flexible than raw Click in some advanced cases (though this is rarely an issue)

## Implementation Details

The CLI will be structured as a Typer application with multiple commands:

```python
import typer
from pathlib import Path
from typing import Optional, List
import rich

app = typer.Typer(help="ZTOQ - Zephyr to qTest")

@app.command("validate")
def validate_spec(spec_path: Path = typer.Argument(..., help="Path to the OpenAPI spec file")):
    """Validate that the OpenAPI spec is for Zephyr Scale API."""
    # Implementation...

@app.command("list-endpoints")
def list_endpoints(spec_path: Path = typer.Argument(..., help="Path to the OpenAPI spec file")):
    """List all API endpoints in the OpenAPI spec."""
    # Implementation...

@app.command("export-project")
def export_project(
    spec_path: Path = typer.Argument(..., help="Path to the OpenAPI spec file"),
    base_url: str = typer.Option(..., help="Zephyr Scale API base URL"),
    api_token: str = typer.Option(..., help="Zephyr Scale API token"),
    project_key: str = typer.Option(..., help="JIRA project key"),
    output_dir: Path = typer.Option(..., help="Output directory for all test data"),
    format: str = typer.Option("json", help="Output format (json or sqlite)"),
):
    """Export all test data for a project."""
    # Implementation...
```

We'll use Rich for enhanced terminal output:

```python
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn

console = Console()

# For tables
table = Table(title="Test Cases")
table.add_column("Key")
table.add_column("Name")
table.add_column("Status")
# Add rows
console.print(table)

# For progress bars
with Progress(
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TaskProgressColumn(),
    console=console
) as progress:
    task = progress.add_task("Downloading...", total=100)
    # Update progress
```

This structure will provide a consistent, user-friendly interface that is easy to extend as we add more functionality.