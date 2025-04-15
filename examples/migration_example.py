#!/usr/bin/env python3
"""
Example demonstrating how to use the ZTOQ migration module programmatically.

This example shows how to:
1. Configure Zephyr and qTest clients
2. Set up a database manager
3. Create a migration instance
4. Run a migration
5. Monitor migration state
6. Implement a custom progress callback

You can run this with:
    poetry run python examples/migration_example.py
"""

import logging
import os
import sys
import time
from pathlib import Path

# Add parent directory to path to import ztoq modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeElapsedColumn
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ztoq.core.db_models import Base
from ztoq.migration import ZephyrToQTestMigration
from ztoq.models import ZephyrConfig
from ztoq.qtest_models import QTestConfig

# Configure logging
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("migration_example")


class DatabaseManager:
    """Simple database manager for SQLite."""

    def __init__(self, db_path: str = "migration.db"):
        """Initialize database manager with SQLite database."""
        # Create SQLite connection
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

        # Create tables if they don't exist
        self._init_database()

    def _init_database(self):
        """Initialize database schema."""
        Base.metadata.create_all(self.engine)

    def get_migration_state(self, project_key: str) -> dict | None:
        """Get migration state for a project."""
        from ztoq.core.db_models import MigrationStateModel

        state = self.session.query(MigrationStateModel).filter_by(project_key=project_key).first()
        if state:
            return {
                "extraction_status": state.extraction_status,
                "transformation_status": state.transformation_status,
                "loading_status": state.loading_status,
                "error_message": state.error_message,
                "last_updated": state.updated_at.isoformat() if state.updated_at else None,
            }
        return None

    def update_migration_state(self, project_key: str, **kwargs):
        """Update migration state for a project."""
        from ztoq.core.db_models import MigrationStateModel

        state = self.session.query(MigrationStateModel).filter_by(project_key=project_key).first()
        if not state:
            state = MigrationStateModel(project_key=project_key)
            self.session.add(state)

        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)

        self.session.commit()

    # Implement other required methods for the migration module
    def save_project(self, project_data):
        """Save project data."""
        logger.info(f"Saving project data for {project_data.get('key', 'Unknown')}")
        # In a real implementation, you would save this to the database
        return True

    def save_folders(self, folders):
        """Save folders data."""
        logger.info(f"Saving {len(folders)} folders")
        return True

    def save_test_cases(self, test_cases):
        """Save test cases data."""
        logger.info(f"Saving {len(test_cases)} test cases")
        return True

    def save_test_cycles(self, test_cycles):
        """Save test cycles data."""
        logger.info(f"Saving {len(test_cycles)} test cycles")
        return True

    def save_test_executions(self, test_executions):
        """Save test executions data."""
        logger.info(f"Saving {len(test_executions)} test executions")
        return True

    def save_attachment(self, related_type, related_id, name, content, url=None):
        """Save attachment data."""
        logger.info(f"Saving attachment {name} for {related_type} {related_id}")
        return True

    def get_entity_batches(self, project_key, entity_type):
        """Get batches for an entity type."""
        from ztoq.core.db_models import EntityBatchModel

        batches = self.session.query(EntityBatchModel).filter_by(
            project_key=project_key, entity_type=entity_type,
        ).all()

        return [
            {
                "batch_num": batch.batch_num,
                "total_batches": batch.total_batches,
                "items_count": batch.items_count,
                "processed_count": batch.processed_count,
                "status": batch.status,
                "error": batch.error,
            }
            for batch in batches
        ]

    def get_pending_entity_batches(self, project_key, entity_type):
        """Get pending batches for an entity type."""
        from ztoq.core.db_models import EntityBatchModel

        batches = self.session.query(EntityBatchModel).filter_by(
            project_key=project_key, entity_type=entity_type, status="pending",
        ).all()

        return [
            {
                "batch_num": batch.batch_num,
                "total_batches": batch.total_batches,
                "items_count": batch.items_count,
                "processed_count": batch.processed_count,
                "status": batch.status,
                "error": batch.error,
            }
            for batch in batches
        ]

    def create_entity_batch(self, project_key, entity_type, batch_num, total_batches, items_count):
        """Create a new entity batch."""
        from ztoq.core.db_models import EntityBatchModel

        batch = EntityBatchModel(
            project_key=project_key,
            entity_type=entity_type,
            batch_num=batch_num,
            total_batches=total_batches,
            items_count=items_count,
            processed_count=0,
            status="pending",
        )

        self.session.add(batch)
        self.session.commit()

        logger.info(f"Created batch {batch_num+1}/{total_batches} for {entity_type}")
        return True

    def update_entity_batch(self, project_key, entity_type, batch_num, processed_count, status, error=None):
        """Update an entity batch."""
        from ztoq.core.db_models import EntityBatchModel

        batch = self.session.query(EntityBatchModel).filter_by(
            project_key=project_key, entity_type=entity_type, batch_num=batch_num,
        ).first()

        if batch:
            batch.processed_count = processed_count
            batch.status = status
            batch.error = error
            self.session.commit()

            logger.info(f"Updated batch {batch_num+1} for {entity_type} to {status}")
            return True

        logger.warning(f"Batch {batch_num} for {entity_type} not found")
        return False


class ConsoleProgressCallback:
    """A progress callback that shows progress in the console using Rich."""

    def __init__(self):
        """Initialize progress tracking."""
        self.progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
        )
        self.tasks = {}
        self.progress.start()

    def update_progress(self, phase, entity_type, completed, total, description=None):
        """Update progress for a specific phase and entity type."""
        task_id = f"{phase}_{entity_type}"

        if task_id not in self.tasks:
            task_name = description or f"{phase.capitalize()} {entity_type.replace('_', ' ')}"
            self.tasks[task_id] = self.progress.add_task(task_name, total=total)

        self.progress.update(self.tasks[task_id], completed=completed, total=total)

    def finish(self):
        """Stop the progress display."""
        self.progress.stop()


def mock_progress_callback(phase, entity_type, completed, total, description=None):
    """A simple progress callback that logs progress."""
    desc = description or f"{phase.capitalize()} {entity_type.replace('_', ' ')}"
    logger.info(f"{desc}: {completed}/{total} ({completed/total*100:.1f}%)")


def run_migration_example(dry_run=True):
    """Run the migration example."""
    try:
        # In a real application, you would get these from configuration or environment variables
        zephyr_config = ZephyrConfig(
            base_url="https://api.zephyrscale.example.com/v2",
            api_token="YOUR_ZEPHYR_API_TOKEN",  # Don't hardcode in real code!
            project_key="DEMO",
        )

        qtest_config = QTestConfig(
            base_url="https://example.qtest.com",
            username="your_qtest_username",
            password="your_qtest_password",  # Don't hardcode in real code!
            project_id=12345,
        )

        # Initialize database manager
        db_manager = DatabaseManager("migration_example.db")

        # Create a temporary directory for attachments
        attachments_dir = Path("./attachments")
        attachments_dir.mkdir(exist_ok=True)

        console.print("[bold green]Starting migration example[/bold green]")
        console.print(f"Project key: {zephyr_config.project_key}")
        console.print("SQLite database: migration_example.db")
        console.print(f"Attachments directory: {attachments_dir}")
        console.print("")

        # For this example, we'll just mock the API clients
        if dry_run:
            console.print("[yellow]Running in dry-run mode - mocking API calls[/yellow]")

            # Create the migration manager with mocked clients
            with Progress() as progress:
                # Create a migration instance
                migration = ZephyrToQTestMigration(
                    zephyr_config=zephyr_config,
                    qtest_config=qtest_config,
                    database_manager=db_manager,
                    batch_size=10,
                    max_workers=3,
                    attachments_dir=attachments_dir,
                )

                # Mock the API client methods to avoid real API calls
                migration.zephyr_client.get_project = lambda project_key: {
                    "id": "10001",
                    "key": project_key,
                    "name": "Demo Project",
                    "description": "Project for migration example",
                }

                migration.zephyr_client.get_folders = lambda: [
                    {"id": f"folder-{i}", "name": f"Folder {i}", "parentId": None if i == 1 else "folder-1"}
                    for i in range(1, 6)
                ]

                migration.zephyr_client.get_test_cases = lambda: [
                    {
                        "id": f"tc-{i:03d}",
                        "key": f"TC-{i:03d}",
                        "name": f"Test Case {i}",
                        "description": f"Description for test case {i}",
                        "folderId": f"folder-{(i % 5) + 1}",
                        "priority": "medium",
                        "attachments": [{"id": f"att-{i}", "filename": f"attachment_{i}.png"}] if i % 3 == 0 else [],
                    }
                    for i in range(1, 31)
                ]

                migration.zephyr_client.get_test_steps = lambda tc_id: [
                    {
                        "id": f"step-{tc_id}-{j}",
                        "description": f"Step {j} for {tc_id}",
                        "expectedResult": f"Expected result {j}",
                    }
                    for j in range(1, 4)
                ]

                migration.zephyr_client.get_test_cycles = lambda: [
                    {
                        "id": f"cycle-{i}",
                        "key": f"CYC-{i}",
                        "name": f"Sprint {i}",
                        "description": f"Test cycle for sprint {i}",
                        "folderId": f"folder-{(i % 5) + 1}",
                        "status": "Active",
                    }
                    for i in range(1, 6)
                ]

                migration.zephyr_client.get_test_executions = lambda: [
                    {
                        "id": f"exec-{i:03d}",
                        "testCaseId": f"tc-{(i % 30) + 1:03d}",
                        "testCycleId": f"cycle-{(i % 5) + 1}",
                        "status": "pass" if i % 4 == 0 else "fail" if i % 4 == 1 else "blocked" if i % 4 == 2 else "wip",
                        "executionTime": "2025-01-02",
                        "comment": f"Execution comment {i}",
                        "attachments": [],
                    }
                    for i in range(1, 51)
                ]

                # Mock download_attachment to return dummy data
                migration.zephyr_client.download_attachment = lambda attachment_id: b"mock image data"

                # Run the migration
                task = progress.add_task("Running migration", total=100)

                # Run extraction
                console.print("\n[bold]Running extraction phase[/bold]")
                migration.extract_data()
                progress.update(task, advance=33)

                # Run transformation
                console.print("\n[bold]Running transformation phase[/bold]")
                migration.transform_data()
                progress.update(task, advance=33)

                # Run loading
                console.print("\n[bold]Running loading phase[/bold]")
                migration.load_data()
                progress.update(task, advance=34)

            # Show final migration state
            state = db_manager.get_migration_state(zephyr_config.project_key)
            console.print("\n[bold]Migration completed with final state:[/bold]")
            console.print(f"  Extraction: {state['extraction_status']}")
            console.print(f"  Transformation: {state['transformation_status']}")
            console.print(f"  Loading: {state['loading_status']}")

            # Show entity statistics
            console.print("\n[bold]Migration statistics:[/bold]")
            for entity_type in ["folders", "test_cases", "test_cycles", "test_executions"]:
                batches = db_manager.get_entity_batches(zephyr_config.project_key, entity_type)
                total_items = sum(batch["items_count"] for batch in batches)
                console.print(f"  {entity_type.replace('_', ' ').title()}: {total_items} items in {len(batches)} batches")

        else:
            # In a real application, you would use the actual API clients
            console.print("[red]Warning: This will make real API calls![/red]")
            console.print("[red]Press Ctrl+C within 5 seconds to cancel...[/red]")

            try:
                for i in range(5, 0, -1):
                    console.print(f"Starting in {i}...")
                    time.sleep(1)
            except KeyboardInterrupt:
                console.print("\nMigration cancelled.")
                return

            # Create the progress callback
            progress_callback = ConsoleProgressCallback()

            # Create migration instance
            migration = ZephyrToQTestMigration(
                zephyr_config=zephyr_config,
                qtest_config=qtest_config,
                database_manager=db_manager,
                batch_size=50,
                max_workers=5,
                attachments_dir=attachments_dir,
            )

            # Run the migration
            try:
                # Run extraction phase
                console.print("\n[bold]Running extraction phase[/bold]")
                migration.extract_data()

                # Run transformation phase
                console.print("\n[bold]Running transformation phase[/bold]")
                migration.transform_data()

                # Run loading phase
                console.print("\n[bold]Running loading phase[/bold]")
                migration.load_data()

                # Finalize progress display
                progress_callback.finish()

                # Show final migration state
                state = db_manager.get_migration_state(zephyr_config.project_key)
                console.print("\n[bold]Migration completed with final state:[/bold]")
                console.print(f"  Extraction: {state['extraction_status']}")
                console.print(f"  Transformation: {state['transformation_status']}")
                console.print(f"  Loading: {state['loading_status']}")

            except Exception as e:
                progress_callback.finish()
                console.print(f"[red]Migration failed with error: {e!s}[/red]")
                raise

    except Exception as e:
        console.print(f"[red]Error: {e!s}[/red]")
        logger.exception("Migration example failed")
        raise


if __name__ == "__main__":
    # Check if we should run in dry-run mode
    dry_run = len(sys.argv) <= 1 or sys.argv[1].lower() != "live"

    if dry_run:
        console.print("[yellow]Running in dry-run mode (mock data)[/yellow]")
        console.print("[yellow]Use 'python migration_example.py live' to run with real API calls[/yellow]")
    else:
        console.print("[bold red]Warning: Running with real API calls![/bold red]")

    run_migration_example(dry_run=dry_run)
