"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Responsible for managing the SQL database operations for Zephyr test data.

This module handles database schema creation, data insertion, and data retrieval
using a functional approach where possible. It focuses on creating and maintaining
a relational database that properly represents the Zephyr Scale data model.
"""

import sqlite3
import json
import logging
from typing import Dict, Any, Union
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from ztoq.models import (
    Project, Case, CycleInfo, Execution, Folder, Status,
        Priority, Environment, CustomField, CaseStep, Attachment
)
from ztoq.data_fetcher import FetchResult

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Manages SQL database operations for Zephyr test data.

    This class provides methods for creating database schema, inserting data,
        and retrieving data from a SQL database. It uses SQLite by default but
    can be extended to support other SQL databases.
    """

    def __init__(self, db_path: Union[str, Path]):
        """
        Initialize the database manager.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path) if isinstance(db_path, str) else db_path
        self._ensure_parent_dir_exists()

    def _ensure_parent_dir_exists(self) -> None:
        """Ensures the parent directory for the database file exists."""
        parent_dir = self.db_path.parent
        parent_dir.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        This ensures that connections are properly closed after use,
            even if an error occurs.

        Yields:
            SQLite connection object
        """
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            # Return dictionaries instead of tuples for query results
            conn.row_factory = sqlite3.Row
            yield conn
        finally:
            if conn:
                conn.close()

    def initialize_database(self) -> None:
        """
        Creates all necessary database tables if they don't exist.

        This method establishes the schema for storing all Zephyr test data,
            including tables for projects, test cases, test cycles, test executions,
            folders, statuses, priorities, environments, and their relationships.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Projects table
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                    key TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT
            )
            """
            )

            # Folders table
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS folders (
                id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    folder_type TEXT NOT NULL,
                    parent_id TEXT,
                    project_key TEXT NOT NULL,
                    FOREIGN KEY (parent_id) REFERENCES folders(id) ON DELETE CASCADE,
                    FOREIGN KEY (project_key) REFERENCES projects(key) ON DELETE CASCADE
            )
            """
            )

            # Statuses table
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS statuses (
                id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    color TEXT,
                    type TEXT NOT NULL,
                    project_key TEXT NOT NULL,
                    FOREIGN KEY (project_key) REFERENCES projects(key) ON DELETE CASCADE
            )
            """
            )

            # Priorities table
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS priorities (
                id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    color TEXT,
                    rank INTEGER NOT NULL,
                    project_key TEXT NOT NULL,
                    FOREIGN KEY (project_key) REFERENCES projects(key) ON DELETE CASCADE
            )
            """
            )

            # Environments table
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS environments (
                id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    project_key TEXT NOT NULL,
                    FOREIGN KEY (project_key) REFERENCES projects(key) ON DELETE CASCADE
            )
            """
            )

            # Test cases table
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS test_cases (
                id TEXT PRIMARY KEY,
                    key TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    objective TEXT,
                    precondition TEXT,
                    description TEXT,
                    status TEXT,
                    priority_id TEXT,
                    priority_name TEXT,
                    folder_id TEXT,
                    folder_name TEXT,
                    owner TEXT,
                    owner_name TEXT,
                    component TEXT,
                    component_name TEXT,
                    created_on TEXT,
                    created_by TEXT,
                    updated_on TEXT,
                    updated_by TEXT,
                    version TEXT,
                    estimated_time INTEGER,
                    labels TEXT, -- JSON array
                steps TEXT, -- JSON array
                custom_fields TEXT, -- JSON array
                links TEXT, -- JSON array
                scripts TEXT, -- JSON array
                versions TEXT, -- JSON array
                attachments TEXT, -- JSON array
                project_key TEXT NOT NULL,
                    FOREIGN KEY (priority_id) REFERENCES priorities(id) ON DELETE SET NULL,
                    FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET NULL,
                    FOREIGN KEY (project_key) REFERENCES projects(key) ON DELETE CASCADE
            )
            """
            )

            # Test cycles table
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS test_cycles (
                id TEXT PRIMARY KEY,
                    key TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT,
                    status_name TEXT,
                    folder_id TEXT,
                    folder_name TEXT,
                    owner TEXT,
                    owner_name TEXT,
                    created_on TEXT,
                    created_by TEXT,
                    updated_on TEXT,
                    updated_by TEXT,
                    custom_fields TEXT, -- JSON array
                links TEXT, -- JSON array
                attachments TEXT, -- JSON array
                project_key TEXT NOT NULL,
                    FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET NULL,
                    FOREIGN KEY (project_key) REFERENCES projects(key) ON DELETE CASCADE
            )
            """
            )

            # Test plans table
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS test_plans (
                id TEXT PRIMARY KEY,
                    key TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT,
                    status_name TEXT,
                    folder_id TEXT,
                    folder_name TEXT,
                    owner TEXT,
                    owner_name TEXT,
                    created_on TEXT,
                    created_by TEXT,
                    updated_on TEXT,
                    updated_by TEXT,
                    custom_fields TEXT, -- JSON array
                links TEXT, -- JSON array
                project_key TEXT NOT NULL,
                    FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET NULL,
                    FOREIGN KEY (project_key) REFERENCES projects(key) ON DELETE CASCADE
            )
            """
            )

            # Test executions table
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS test_executions (
                id TEXT PRIMARY KEY,
                    test_case_key TEXT NOT NULL,
                    cycle_id TEXT NOT NULL,
                    cycle_name TEXT,
                    status TEXT NOT NULL,
                    status_name TEXT,
                    environment_id TEXT,
                    environment_name TEXT,
                    executed_by TEXT,
                    executed_by_name TEXT,
                    executed_on TEXT,
                    created_on TEXT,
                    created_by TEXT,
                    updated_on TEXT,
                    updated_by TEXT,
                    actual_time INTEGER,
                    comment TEXT,
                    steps TEXT, -- JSON array
                custom_fields TEXT, -- JSON array
                links TEXT, -- JSON array
                attachments TEXT, -- JSON array
                project_key TEXT NOT NULL,
                    FOREIGN KEY (test_case_key) REFERENCES test_cases(key) ON DELETE CASCADE,
                    FOREIGN KEY (cycle_id) REFERENCES test_cycles(id) ON DELETE CASCADE,
                    FOREIGN KEY (environment_id) REFERENCES environments(id) ON DELETE SET NULL,
                    FOREIGN KEY (project_key) REFERENCES projects(key) ON DELETE CASCADE
            )
            """
            )

            # Create indexes for better query performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_test_cases_project ON test_cases (project_key)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_test_cycles_project ON test_cycles (project_key)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_test_plans_project ON test_plans (project_key)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_test_executions_project ON test_executions (project_key)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_test_executions_cycle ON test_executions (cycle_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_test_executions_case ON test_executions (test_case_key)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_folders_project ON folders (project_key)"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_folders_parent ON folders (parent_id)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_statuses_project ON statuses (project_key)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_priorities_project ON priorities (project_key)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_environments_project ON environments (project_key)"
            )

            conn.commit()

    def _serialize_object(self, obj: Any) -> Any:
        """
        Serialize an object for database storage.

        This function handles serialization of Pydantic models, datetime objects,
            lists, and dictionaries to JSON-compatible formats.

        Args:
            obj: The object to serialize

        Returns:
            Serialized version of the object suitable for database storage
        """
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        elif hasattr(obj, "dict"):  # For backward compatibility
            return obj.dict()
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, list):
            return [self._serialize_object(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: self._serialize_object(v) for k, v in obj.items()}
        return obj

    def _serialize_value(self, value: Any) -> Any:
        """
        Serialize a value for database storage.

        This function handles conversion of Python objects to database-friendly formats,
            including JSON serialization for complex objects.

        Args:
            value: The value to serialize

        Returns:
            Database-friendly representation of the value
        """
        if value is None:
            return None
        elif isinstance(value, (dict, list)):
            return json.dumps(self._serialize_object(value))
        elif isinstance(value, datetime):
            return value.isoformat()
        return value

    def save_project(self, project: Project) -> None:
        """
        Save a project to the database.

        Args:
            project: The project to save
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO projects (id, key, name, description)
                VALUES (?, ?, ?, ?)
                """,
                    (project.id, project.key, project.name, project.description),
                )
            conn.commit()

    def save_folder(self, folder: Folder, project_key: str) -> None:
        """
        Save a folder to the database.

        Args:
            folder: The folder to save
            project_key: The project key the folder belongs to
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO folders (id, name, folder_type, parent_id, project_key)
                VALUES (?, ?, ?, ?, ?)
                """,
                    (folder.id, folder.name, folder.folder_type, folder.parent_id, project_key),
                )
            conn.commit()

    def save_status(self, status: Status, project_key: str) -> None:
        """
        Save a status to the database.

        Args:
            status: The status to save
            project_key: The project key the status belongs to
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO statuses (id, name, description, color, type, project_key)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                    status.id,
                        status.name,
                        status.description,
                        status.color,
                        status.type,
                        project_key,
                    ),
                )
            conn.commit()

    def save_priority(self, priority: Priority, project_key: str) -> None:
        """
        Save a priority to the database.

        Args:
            priority: The priority to save
            project_key: The project key the priority belongs to
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO priorities (id, name, description, color, rank, project_key)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                    priority.id,
                        priority.name,
                        priority.description,
                        priority.color,
                        priority.rank,
                        project_key,
                    ),
                )
            conn.commit()

    def save_environment(self, environment: Environment, project_key: str) -> None:
        """
        Save an environment to the database.

        Args:
            environment: The environment to save
            project_key: The project key the environment belongs to
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO environments (id, name, description, project_key)
                VALUES (?, ?, ?, ?)
                """,
                    (environment.id, environment.name, environment.description, project_key),
                )
            conn.commit()

    def save_test_case(self, test_case: Case, project_key: str) -> None:
        """
        Save a test case to the database.

        This method handles serialization of complex objects like arrays and nested
        objects into JSON strings for database storage.

        Args:
            test_case: The test case to save
            project_key: The project key the test case belongs to
        """
        # Handle complex objects by serializing to JSON
        labels_json = self._serialize_value(test_case.labels)

        # Serialize steps
        steps_json = self._serialize_value(
            [
                step.model_dump() if hasattr(step, "model_dump") else step.dict()
                for step in test_case.steps
            ]
        )

        # Serialize custom fields
        custom_fields_json = self._serialize_value(
            [
                cf.model_dump() if hasattr(cf, "model_dump") else cf.dict()
                for cf in test_case.custom_fields
            ]
        )

        # Serialize links
        links_json = self._serialize_value(
            [
                link.model_dump() if hasattr(link, "model_dump") else link.dict()
                for link in test_case.links
            ]
        )

        # Serialize scripts
        scripts_json = self._serialize_value(
            [
                script.model_dump() if hasattr(script, "model_dump") else script.dict()
                for script in test_case.scripts
            ]
        )

        # Serialize versions
        versions_attr = "versions" if hasattr(test_case, "versions") else "test_versions"
        versions = getattr(test_case, versions_attr, [])
        versions_json = self._serialize_value(
            [
                version.model_dump() if hasattr(version, "model_dump") else version.dict()
                for version in versions
            ]
        )

        # Serialize attachments
        attachments_json = self._serialize_value(
            [
                attachment.model_dump() if hasattr(attachment, "model_dump") else attachment.dict()
                for attachment in test_case.attachments
            ]
        )

        # Handle priority - it could be an object or a dict
        priority_id = None
        if test_case.priority:
            if isinstance(test_case.priority, dict):
                priority_id = test_case.priority.get("id")
            else:
                priority_id = test_case.priority.id

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO test_cases (
                    id, key, name, objective, precondition, description, status,
                        priority_id, priority_name, folder_id, folder_name, owner, owner_name,
                        component, component_name, created_on, created_by, updated_on, updated_by,
                        version, estimated_time, labels, steps, custom_fields, links, scripts,
                        versions, attachments, project_key
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                    (
                    test_case.id,
                        test_case.key,
                        test_case.name,
                        test_case.objective,
                        test_case.precondition,
                        test_case.description,
                        test_case.status,
                        priority_id,
                        test_case.priority_name,
                        test_case.folder,
                        test_case.folder_name,
                        test_case.owner,
                        test_case.owner_name,
                        test_case.component,
                        test_case.component_name,
                        self._serialize_value(test_case.created_on),
                        test_case.created_by,
                        self._serialize_value(test_case.updated_on),
                        test_case.updated_by,
                        test_case.version,
                        test_case.estimated_time,
                        labels_json,
                        steps_json,
                        custom_fields_json,
                        links_json,
                        scripts_json,
                        versions_json,
                        attachments_json,
                        project_key,
                    ),
                )
            conn.commit()

    def save_test_cycle(self, test_cycle: CycleInfo, project_key: str) -> None:
        """
        Save a test cycle to the database.

        Args:
            test_cycle: The test cycle to save
            project_key: The project key the test cycle belongs to
        """
        # Serialize custom fields
        custom_fields_json = self._serialize_value(
            [
                cf.model_dump() if hasattr(cf, "model_dump") else cf.dict()
                for cf in test_cycle.custom_fields
            ]
        )

        # Serialize links
        links_json = self._serialize_value(
            [
                link.model_dump() if hasattr(link, "model_dump") else link.dict()
                for link in test_cycle.links
            ]
        )

        # Serialize attachments
        attachments_json = self._serialize_value(
            [
                attachment.model_dump() if hasattr(attachment, "model_dump") else attachment.dict()
                for attachment in test_cycle.attachments
            ]
        )

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO test_cycles (
                    id, key, name, description, status, status_name, folder_id, folder_name,
                        owner, owner_name, created_on, created_by, updated_on, updated_by,
                        custom_fields, links, attachments, project_key
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                    (
                    test_cycle.id,
                        test_cycle.key,
                        test_cycle.name,
                        test_cycle.description,
                        test_cycle.status,
                        test_cycle.status_name,
                        test_cycle.folder,
                        test_cycle.folder_name,
                        test_cycle.owner,
                        test_cycle.owner_name,
                        self._serialize_value(test_cycle.created_on),
                        test_cycle.created_by,
                        self._serialize_value(test_cycle.updated_on),
                        test_cycle.updated_by,
                        custom_fields_json,
                        links_json,
                        attachments_json,
                        project_key,
                    ),
                )
            conn.commit()

    def save_test_execution(self, test_execution: Execution, project_key: str) -> None:
        """
        Save a test execution to the database.

        Args:
            test_execution: The test execution to save
            project_key: The project key the test execution belongs to
        """
        # Serialize steps
        steps_json = self._serialize_value(
            [
                step.model_dump() if hasattr(step, "model_dump") else step.dict()
                for step in test_execution.steps
            ]
        )

        # Serialize custom fields
        custom_fields_json = self._serialize_value(
            [
                cf.model_dump() if hasattr(cf, "model_dump") else cf.dict()
                for cf in test_execution.custom_fields
            ]
        )

        # Serialize links
        links_json = self._serialize_value(
            [
                link.model_dump() if hasattr(link, "model_dump") else link.dict()
                for link in test_execution.links
            ]
        )

        # Serialize attachments
        attachments_json = self._serialize_value(
            [
                attachment.model_dump() if hasattr(attachment, "model_dump") else attachment.dict()
                for attachment in test_execution.attachments
            ]
        )

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO test_executions (
                    id, test_case_key, cycle_id, cycle_name, status, status_name,
                        environment_id, environment_name, executed_by, executed_by_name,
                        executed_on, created_on, created_by, updated_on, updated_by,
                        actual_time, comment, steps, custom_fields, links, attachments,
                        project_key
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                    (
                    test_execution.id,
                        test_execution.test_case_key,
                        test_execution.cycle_id,
                        test_execution.cycle_name,
                        test_execution.status,
                        test_execution.status_name,
                        test_execution.environment,
                        test_execution.environment_name,
                        test_execution.executed_by,
                        test_execution.executed_by_name,
                        self._serialize_value(test_execution.executed_on),
                        self._serialize_value(test_execution.created_on),
                        test_execution.created_by,
                        self._serialize_value(test_execution.updated_on),
                        test_execution.updated_by,
                        test_execution.actual_time,
                        test_execution.comment,
                        steps_json,
                        custom_fields_json,
                        links_json,
                        attachments_json,
                        project_key,
                    ),
                )
            conn.commit()

    def save_project_data(
        self, project_key: str, fetch_results: Dict[str, FetchResult]
    ) -> Dict[str, int]:
        """
        Save all fetched data for a project.

        This method coordinates saving different entity types to their respective tables.
        It handles the relationships between entities and ensures proper insertion order.

        Args:
            project_key: The project key
            fetch_results: Dictionary of fetched data results

        Returns:
            Dictionary with counts of inserted records by entity type
        """
        counts = {}

        # Save project first if available
        # This is usually fetched separately, so we may need to create a placeholder
        if "project" in fetch_results:
            project_result = fetch_results["project"]
            if project_result.success and project_result.items:
                self.save_project(project_result.items[0])
                counts["project"] = 1
        else:
            # Create a minimal project entry to satisfy foreign key constraints
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO projects (id, key, name, description)
                    VALUES (?, ?, ?, ?)
                    """,
                        (
                        f"placeholder_{project_key}",
                            project_key,
                            f"Project {project_key}",
                            f"Placeholder project for {project_key}",
                        ),
                    )
                conn.commit()
                counts["project"] = 1

        # Save different entity types in the correct order to satisfy foreign key constraints

        # 1. Folders (with self-references)
        if "folders" in fetch_results:
            folder_result = fetch_results["folders"]
            if folder_result.success:
                # Sort folders to handle parent-child relationships
                folders = sorted(folder_result.items, key=lambda f: len(f.id))
                for folder in folders:
                    self.save_folder(folder, project_key)
                counts["folders"] = len(folders)

        # 2. Statuses
        if "statuses" in fetch_results:
            status_result = fetch_results["statuses"]
            if status_result.success:
                for status in status_result.items:
                    self.save_status(status, project_key)
                counts["statuses"] = len(status_result.items)

        # 3. Priorities
        if "priorities" in fetch_results:
            priority_result = fetch_results["priorities"]
            if priority_result.success:
                for priority in priority_result.items:
                    self.save_priority(priority, project_key)
                counts["priorities"] = len(priority_result.items)

        # 4. Environments
        if "environments" in fetch_results:
            environment_result = fetch_results["environments"]
            if environment_result.success:
                for environment in environment_result.items:
                    self.save_environment(environment, project_key)
                counts["environments"] = len(environment_result.items)

        # 5. Test cases
        if "test_cases" in fetch_results:
            test_case_result = fetch_results["test_cases"]
            if test_case_result.success:
                for test_case in test_case_result.items:
                    self.save_test_case(test_case, project_key)
                counts["test_cases"] = len(test_case_result.items)

        # 6. Test cycles
        if "test_cycles" in fetch_results:
            test_cycle_result = fetch_results["test_cycles"]
            if test_cycle_result.success:
                for test_cycle in test_cycle_result.items:
                    self.save_test_cycle(test_cycle, project_key)
                counts["test_cycles"] = len(test_cycle_result.items)

        # 7. Test executions
        if "test_executions" in fetch_results:
            test_execution_result = fetch_results["test_executions"]
            if test_execution_result.success:
                for test_execution in test_execution_result.items:
                    self.save_test_execution(test_execution, project_key)
                counts["test_executions"] = len(test_execution_result.items)

        return counts

    def save_all_projects_data(
        self, all_projects_data: Dict[str, Dict[str, FetchResult]]
    ) -> Dict[str, Dict[str, int]]:
        """
        Save all fetched data for multiple projects.

        Args:
            all_projects_data: Dictionary mapping project keys to their fetch results

        Returns:
            Dictionary mapping project keys to counts of inserted records by entity type
        """
        # Initialize database first
        self.initialize_database()

        # Save data for each project
        results = {}
        for project_key, project_data in all_projects_data.items():
            results[project_key] = self.save_project_data(project_key, project_data)

        return results
