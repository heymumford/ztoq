"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Main application module for importing Zephyr Scale test data into a SQL database.

This module provides a high-level interface for the entire import process,
from authentication to data fetching to database storage.
"""

import logging
import argparse
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime

from ztoq.models import ZephyrConfig
from ztoq.data_fetcher import create_authenticated_client, fetch_projects, fetch_all_projects_data
from ztoq.database_manager import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("zephyr_import.log")],
)
logger = logging.getLogger(__name__)


@dataclass
class ImportConfig:
    """Configuration for the import process."""

    base_url: str
    api_token: str
    project_keys: Optional[List[str]] = None
    db_path: str = "zephyr_data.db"
    concurrency: int = 5
    verbose: bool = False


class ImportProgress:
    """
    Tracks and reports progress during the import process.

    This class maintains state about the current import operation and provides
    callback functions for progress reporting.
    """

    def __init__(self, verbose: bool = False):
        """
        Initialize progress tracking.

        Args:
            verbose: Whether to print detailed progress information
        """
        self.start_time = datetime.now()
        self.verbose = verbose
        self.projects_total = 0
        self.projects_completed = 0
        self.entities_total = 0
        self.entities_completed = 0
        self.entities_failed = 0
        self.current_project: Optional[str] = None

    def set_projects_total(self, count: int) -> None:
        """Set the total number of projects to import."""
        self.projects_total = count

    def project_callback(self, event_type: str, project_key: str, success: bool) -> None:
        """
        Callback function for project-level events.

        Args:
            event_type: Type of event (project_start, project_complete)
            project_key: The project key
            success: Whether the operation was successful
        """
        if event_type == "project_start":
            self.current_project = project_key
            if self.verbose:
                logger.info(f"Starting import for project: {project_key}")
        elif event_type == "project_complete":
            self.projects_completed += 1
            if self.verbose:
                logger.info(f"Completed import for project: {project_key}")
            else:
                # Print progress percent without logging prefix
                progress = (self.projects_completed / self.projects_total) * 100
                print(
                    f"\rProjects: {self.projects_completed}/{self.projects_total} ({progress:.1f}%)",
                    end="",
                )

    def entity_callback(self, entity_type: str, project_key: str, success: bool) -> None:
        """
        Callback function for entity-level events.

        Args:
            entity_type: Type of entity (test_cases, test_cycles, etc.)
            project_key: The project key
            success: Whether the operation was successful
        """
        if entity_type not in ("project_start", "project_complete"):
            if success:
                self.entities_completed += 1
            else:
                self.entities_failed += 1

            if self.verbose:
                status = "Success" if success else "Failed"
                logger.info(f"{status}: {entity_type} for project {project_key}")

    def callback(self, entity_type: str, project_key: str, success: bool) -> None:
        """
        Combined callback function for all events.

        Args:
            entity_type: Type of entity or event
            project_key: The project key
            success: Whether the operation was successful
        """
        if entity_type in ("project_start", "project_complete"):
            self.project_callback(entity_type, project_key, success)
        else:
            self.entity_callback(entity_type, project_key, success)

    def print_summary(self) -> Dict[str, Any]:
        """
        Print a summary of the import operation.

        Returns:
            Dictionary containing summary statistics
        """
        end_time = datetime.now()
        duration = end_time - self.start_time

        logger.info("-" * 50)
        logger.info("Import Summary:")
        logger.info(f"Duration: {duration}")
        logger.info(f"Projects Processed: {self.projects_completed}/{self.projects_total}")
        logger.info(f"Entities Completed: {self.entities_completed}")
        logger.info(f"Entities Failed: {self.entities_failed}")
        logger.info("-" * 50)

        return {
            "duration": duration,
            "projects_total": self.projects_total,
            "projects_completed": self.projects_completed,
            "entities_completed": self.entities_completed,
            "entities_failed": self.entities_failed,
        }


def import_zephyr_data(config: ImportConfig) -> Dict[str, Any]:
    """
    Import all Zephyr Scale test data into a SQL database.

    This function coordinates the entire import process:
    1. Authentication
    2. Fetching projects (if needed)
    3. Fetching test data for each project
    4. Storing data in the database
    5. Tracking and reporting progress

    Args:
        config: Import configuration object

    Returns:
        Dictionary containing import summary statistics
    """
    # Configure progress tracking
    progress = ImportProgress(config.verbose)

    # Create Zephyr configuration
    zephyr_config = ZephyrConfig(
        base_url=config.base_url,
        api_token=config.api_token,
        project_key="" if config.project_keys else "placeholder",
    )

    # Create authenticated client
    client = create_authenticated_client(zephyr_config)

    # Determine which projects to process
    project_keys = config.project_keys
    if not project_keys:
        logger.info("No project keys specified. Fetching all available projects...")
        projects = fetch_projects(client)
        if not projects:
            logger.error("No projects found. Please check your API token and URL.")
            return {"error": "No projects found"}

        project_keys = [project.key for project in projects]

    # Set total projects for progress tracking
    progress.set_projects_total(len(project_keys))
    logger.info(f"Starting import for {len(project_keys)} projects...")

    # Fetch data for all projects
    all_projects_data = fetch_all_projects_data(
        client, project_keys, progress_callback=progress.callback
    )

    # Initialize database manager
    db_path = Path(config.db_path)
    db_manager = DatabaseManager(db_path)

    # Save all data to the database
    logger.info("Storing data in database...")
    results = db_manager.save_all_projects_data(all_projects_data)

    # Generate and print summary
    summary = progress.print_summary()
    summary["results"] = results

    return summary


def parse_args() -> ImportConfig:
    """
    Parse command line arguments.

    Returns:
        ImportConfig object with parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Import Zephyr Scale test data into a SQL database"
    )

    parser.add_argument(
        "--base-url",
        type=str,
        default="https://api.zephyrscale.smartbear.com/v2",
        help="Zephyr Scale API base URL",
    )

    parser.add_argument("--api-token", type=str, required=True, help="Zephyr Scale API token")

    parser.add_argument(
        "--project-keys",
        type=str,
        nargs="*",
        help="List of project keys to import (omit to import all projects)",
    )

    parser.add_argument(
        "--db-path", type=str, default="zephyr_data.db", help="Path to SQLite database file"
    )

    parser.add_argument(
        "--concurrency", type=int, default=5, help="Number of concurrent operations"
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    return ImportConfig(
        base_url=args.base_url,
        api_token=args.api_token,
        project_keys=args.project_keys,
        db_path=args.db_path,
        concurrency=args.concurrency,
        verbose=args.verbose,
    )


def main() -> int:
    """
    Main entry point for the Zephyr importer.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Parse command line arguments
        config = parse_args()

        # Run the import
        results = import_zephyr_data(config)

        # Check for errors
        if "error" in results:
            logger.error(f"Import failed: {results['error']}")
            return 1

        logger.info("Import completed successfully.")
        return 0
    except KeyboardInterrupt:
        logger.info("Import cancelled by user.")
        return 1
    except Exception as e:
        logger.exception(f"Import failed with error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
