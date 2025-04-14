"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Union, Callable
from rich.progress import Progress
from concurrent.futures import ThreadPoolExecutor, as_completed
from ztoq.models import ZephyrConfig, TestExecution
from ztoq.zephyr_client import ZephyrClient
from ztoq.storage import SQLiteStorage, JSONStorage

logger = logging.getLogger(__name__)


class ZephyrExporter:
    """Exporter for downloading and storing Zephyr Scale test data."""

    def __init__(
        self,
            client: ZephyrClient,
            output_format: str = "json",
            output_path: Optional[Path] = None,
            concurrency: int = 2,
        ):
        """Initialize the Zephyr exporter.

        Args:
            client: ZephyrClient instance
            output_format: Output format - "json" or "sqlite"
            output_path: Output path for data (directory for JSON, file for SQLite)
            concurrency: Number of concurrent requests for bulk operations
        """
        self.client = client
        self.output_format = output_format.lower()
        self.output_path = output_path or Path(f"zephyr_export_{self.client.config.project_key}")
        self.concurrency = concurrency

        if self.output_format == "json":
            self.storage: Union[JSONStorage, SQLiteStorage] = JSONStorage(self.output_path)
        elif self.output_format == "sqlite":
            self.storage = SQLiteStorage(self.output_path)
            # Initialize SQLite database
            with self.storage as sqlite_storage:
                sqlite_storage.initialize_database()
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

    def export_all(self, progress: Optional[Progress] = None) -> Dict[str, int]:
        """Export all test data for the configured project.

        Args:
            progress: Optional Progress instance for progress reporting

        Returns:
            Dictionary with counts of exported items
        """
        project_key = self.client.config.project_key
        counts = {}

        if progress:
            task = progress.add_task(f"[cyan]Exporting Zephyr data for {project_key}...", total=7)

        # Export basic project data
        logger.info(f"Exporting project {project_key}")
        projects = self.client.get_projects()
        project = next((p for p in projects if p.key == project_key), None)

        if not project:
            raise ValueError(f"Project {project_key} not found")

        with self.storage:
            self.storage.save_project(project.key, project.name, project.id, project.description)

        if progress:
            progress.update(task, advance=1, description="[cyan]Exported project info")

        # Export folders, statuses, priorities, environments
        folders = self.client.get_folders()
        statuses = self.client.get_statuses()
        priorities = self.client.get_priorities()
        environments = self.client.get_environments()

        with self.storage:
            self.storage.save_folders(folders, project_key)
            self.storage.save_statuses(statuses, project_key)
            self.storage.save_priorities(priorities, project_key)
            self.storage.save_environments(environments, project_key)

        counts["folders"] = len(folders)
        counts["statuses"] = len(statuses)
        counts["priorities"] = len(priorities)
        counts["environments"] = len(environments)

        if progress:
            progress.update(task, advance=1, description="[cyan]Exported metadata")

        # Export test cases in batches
        test_cases = list(self.client.get_test_cases())
        counts["test_cases"] = len(test_cases)

        if progress:
            progress.update(
                task, advance=1, description=f"[cyan]Exported {len(test_cases)} test cases"
            )

        # Save test cases
        with self.storage:
            if isinstance(self.storage, JSONStorage):
                self.storage.save_test_cases(test_cases, project_key)
            else:
                for tc in test_cases:
                    self.storage.save_test_case(tc, project_key)

        # Export test cycles
        test_cycles = list(self.client.get_test_cycles())
        counts["test_cycles"] = len(test_cycles)

        if progress:
            progress.update(
                task, advance=1, description=f"[cyan]Exported {len(test_cycles)} test cycles"
            )

        # Save test cycles
        with self.storage:
            if isinstance(self.storage, JSONStorage):
                self.storage.save_test_cycles(test_cycles, project_key)
            else:
                for tc in test_cycles:
                    self.storage.save_test_cycle(tc)

        # Export test executions in parallel
        all_executions = []

        if progress:
            exec_task = progress.add_task(
                f"[yellow]Fetching executions for {len(test_cycles)} test cycles...",
                    total=len(test_cycles),
                )

        if len(test_cycles) > 0:
            with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
                # Submit all tasks
                future_to_cycle = {
                    executor.submit(self._fetch_executions_for_cycle, cycle.id): cycle
                    for cycle in test_cycles
                }

                # Process results as they complete
                for future in as_completed(future_to_cycle):
                    cycle = future_to_cycle[future]
                    try:
                        executions = future.result()
                        all_executions.extend(executions)
                        if progress:
                            progress.update(
                                exec_task,
                                    advance=1,
                                    description=(
                                    f"[yellow]{len(executions)} executions for cycle {cycle.name}"
                                ),
                                )
                    except Exception as e:
                        logger.error(f"Error fetching executions for cycle {cycle.id}: {e}")
                        if progress:
                            progress.update(
                                exec_task,
                                    advance=1,
                                    description=f"[red]Error with cycle {cycle.name}",
                                )

        counts["test_executions"] = len(all_executions)

        if progress:
            progress.update(
                task, advance=1, description=f"[cyan]Exported {len(all_executions)} test executions"
            )

        # Save test executions
        with self.storage:
            if isinstance(self.storage, JSONStorage):
                self.storage.save_test_executions(all_executions, project_key)
            else:
                for te in all_executions:
                    self.storage.save_test_execution(te, project_key)

        if progress:
            progress.update(
                task, advance=1, description=f"[green]Completed export for {project_key}"
            )

        return counts

    def _fetch_executions_for_cycle(self, cycle_id: str) -> List[TestExecution]:
        """Fetch all executions for a test cycle.

        Args:
            cycle_id: Test cycle ID

        Returns:
            List of test executions
        """
        return list(self.client.get_test_executions(cycle_id=cycle_id))


class ZephyrExportManager:
    """Manager for handling exports from multiple projects."""

    def __init__(
        self,
            config: ZephyrConfig,
            output_format: str = "json",
            output_dir: Optional[Path] = None,
            spec_path: Optional[Path] = None,
            concurrency: int = 2,
        ):
        """Initialize the export manager.

        Args:
            config: ZephyrConfig object
            output_format: Output format - "json" or "sqlite"
            output_dir: Base output directory
            spec_path: Path to OpenAPI spec file
            concurrency: Number of concurrent requests for bulk operations
        """
        self.config = config
        self.output_format = output_format
        self.output_dir = output_dir or Path("zephyr_exports")
        self.spec_path = spec_path
        self.concurrency = concurrency

    def export_project(
        self, project_key: Optional[str] = None, progress: Optional[Progress] = None
    ) -> Dict[str, int]:
        """Export data for a specific project.

        Args:
            project_key: Project key (defaults to config's project_key)
            progress: Optional Progress instance for progress reporting

        Returns:
            Dictionary with counts of exported items
        """
        pk = project_key or self.config.project_key

        # Update config to use the specified project key
        config = ZephyrConfig(
            base_url=self.config.base_url, api_token=self.config.api_token, project_key=pk
        )

        # Create client
        if self.spec_path:
            client = ZephyrClient.from_openapi_spec(self.spec_path, config)
        else:
            client = ZephyrClient(config)

        # Configure output path
        output_path = self.output_dir / pk
        if self.output_format == "sqlite":
            output_path = self.output_dir / f"{pk}.db"

        # Create exporter
        exporter = ZephyrExporter(
            client=client,
                output_format=self.output_format,
                output_path=output_path,
                concurrency=self.concurrency,
            )

        # Run the export
        return exporter.export_all(progress=progress)

    def export_all_projects(
        self,
            projects_to_export: Optional[List[str]] = None,
            progress_callback: Optional[Callable[[str, str, int, int], None]] = None,
        ) -> Dict[str, Dict[str, int]]:
        """Export data for multiple projects.

        Args:
            projects_to_export: List of project keys to export (defaults to all projects)
            progress_callback: Optional callback for progress reporting
                Args: project_key, status, current, total

        Returns:
            Dictionary mapping project keys to export statistics
        """
        # Create client to get projects list
        if self.spec_path:
            client = ZephyrClient.from_openapi_spec(self.spec_path, self.config)
        else:
            client = ZephyrClient(self.config)

        # Get projects
        projects = client.get_projects()

        # Filter projects if needed
        if projects_to_export:
            projects = [p for p in projects if p.key in projects_to_export]

        results = {}
        total_projects = len(projects)

        for i, project in enumerate(projects, 1):
            if progress_callback:
                progress_callback(project.key, "starting", i, total_projects)

            try:
                logger.info(f"Exporting project {project.key} ({i}/{total_projects})")
                stats = self.export_project(project.key)
                results[project.key] = stats

                if progress_callback:
                    progress_callback(project.key, "completed", i, total_projects)
            except Exception as e:
                logger.error(f"Error exporting project {project.key}: {e}")
                if progress_callback:
                    progress_callback(project.key, f"error: {str(e)}", i, total_projects)

        return results
