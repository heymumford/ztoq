"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import sqlite3
import json
from datetime import datetime
from typing import Any, List, Optional, TypeVar
from pathlib import Path
import logging

from ztoq.models import (
    TestCase,
    TestCycleInfo,
    TestPlan,
    TestExecution,
    Folder,
    Status,
    Priority,
    Environment,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SQLiteStorage:
    """Storage class for saving Zephyr Scale data to SQLite database."""

    def __init__(self, db_path: Path):
        """Initialize SQLite storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def connect(self):
        """Connect to the SQLite database."""
        self.conn = sqlite3.connect(str(self.db_path))
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")
        # Use Row factory for better column access
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.close()

    def _serialize_value(self, value: Any) -> Any:
        """Serialize a value to a format suitable for SQLite."""
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        return value

    def _create_tables(self):
        """Create database tables if they don't exist."""
        # Projects table
        self.cursor.execute(
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
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS folders (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            folder_type TEXT NOT NULL,
            parent_id TEXT,
            project_key TEXT NOT NULL,
            FOREIGN KEY (parent_id) REFERENCES folders (id) ON DELETE CASCADE
        )
        """
        )

        # Statuses table
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS statuses (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            color TEXT,
            type TEXT NOT NULL,
            project_key TEXT NOT NULL
        )
        """
        )

        # Priorities table
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS priorities (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            color TEXT,
            rank INTEGER NOT NULL,
            project_key TEXT NOT NULL
        )
        """
        )

        # Environments table
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS environments (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            project_key TEXT NOT NULL
        )
        """
        )

        # Test Cases table
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS test_cases (
            id TEXT PRIMARY KEY,
            key TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            objective TEXT,
            precondition TEXT,
            description TEXT,
            status TEXT,
            priority TEXT,
            priority_name TEXT,
            folder TEXT,
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
            labels TEXT,  -- JSON array
            steps TEXT,   -- JSON array
            custom_fields TEXT,  -- JSON array
            links TEXT,   -- JSON array
            scripts TEXT,  -- JSON array
            test_versions TEXT,  -- JSON array
            project_key TEXT NOT NULL
        )
        """
        )

        # Test Cycles table
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS test_cycles (
            id TEXT PRIMARY KEY,
            key TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT,
            status_name TEXT,
            folder TEXT,
            folder_name TEXT,
            project_key TEXT NOT NULL,
            owner TEXT,
            owner_name TEXT,
            created_on TEXT,
            created_by TEXT,
            updated_on TEXT,
            updated_by TEXT,
            custom_fields TEXT,  -- JSON array
            links TEXT   -- JSON array
        )
        """
        )

        # Test Plans table
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS test_plans (
            id TEXT PRIMARY KEY,
            key TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT,
            status_name TEXT,
            folder TEXT,
            folder_name TEXT,
            project_key TEXT NOT NULL,
            owner TEXT,
            owner_name TEXT,
            created_on TEXT,
            created_by TEXT,
            updated_on TEXT,
            updated_by TEXT,
            custom_fields TEXT,  -- JSON array
            links TEXT   -- JSON array
        )
        """
        )

        # Test Executions table
        self.cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS test_executions (
            id TEXT PRIMARY KEY,
            test_case_key TEXT NOT NULL,
            cycle_id TEXT NOT NULL,
            cycle_name TEXT,
            status TEXT NOT NULL,
            status_name TEXT,
            environment TEXT,
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
            steps TEXT,  -- JSON array
            custom_fields TEXT,  -- JSON array
            links TEXT,  -- JSON array
            project_key TEXT NOT NULL,
            FOREIGN KEY (test_case_key) REFERENCES test_cases (key) ON DELETE CASCADE,
            FOREIGN KEY (cycle_id) REFERENCES test_cycles (id) ON DELETE CASCADE
        )
        """
        )

        # Create indexes
        self.cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_folders_project ON folders (project_key)"
        )
        self.cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_statuses_project ON statuses (project_key)"
        )
        self.cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_priorities_project ON priorities (project_key)"
        )
        self.cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_environments_project ON environments (project_key)"
        )
        self.cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_test_cases_project ON test_cases (project_key)"
        )
        self.cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_test_cycles_project ON test_cycles (project_key)"
        )
        self.cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_test_plans_project ON test_plans (project_key)"
        )
        self.cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_test_executions_project ON test_executions (project_key)"
        )
        self.cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_test_executions_cycle ON test_executions (cycle_id)"
        )

    def save_project(
        self,
        project_key: str,
        project_name: str,
        project_id: str,
        description: Optional[str] = None,
    ):
        """Save project information.

        Args:
            project_key: Project key
            project_name: Project name
            project_id: Project ID
            description: Project description
        """
        if self.cursor is None:
            raise ValueError(
                "Database connection not established. Use context manager or connect()."
            )
        self.cursor.execute(
            "INSERT OR REPLACE INTO projects (id, key, name, description) VALUES (?, ?, ?, ?)",
            (project_id, project_key, project_name, description),
        )

    def save_folders(self, folders: List[Folder], project_key: str):
        """Save folders for a project.

        Args:
            folders: List of folders
            project_key: Project key
        """
        if self.cursor is None:
            raise ValueError(
                "Database connection not established. Use context manager or connect()."
            )
        for folder in folders:
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO folders
                (id, name, folder_type, parent_id, project_key)
                VALUES (?, ?, ?, ?, ?)
                """,
                (folder.id, folder.name, folder.folder_type, folder.parent_id, project_key),
            )

    def save_statuses(self, statuses: List[Status], project_key: str):
        """Save statuses for a project.

        Args:
            statuses: List of statuses
            project_key: Project key
        """
        if self.cursor is None:
            raise ValueError(
                "Database connection not established. Use context manager or connect()."
            )
        for status in statuses:
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO statuses
                (id, name, description, color, type, project_key)
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

    def save_priorities(self, priorities: List[Priority], project_key: str):
        """Save priorities for a project.

        Args:
            priorities: List of priorities
            project_key: Project key
        """
        if self.cursor is None:
            raise ValueError(
                "Database connection not established. Use context manager or connect()."
            )
        for priority in priorities:
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO priorities
                (id, name, description, color, rank, project_key)
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

    def save_environments(self, environments: List[Environment], project_key: str):
        """Save environments for a project.

        Args:
            environments: List of environments
            project_key: Project key
        """
        if self.cursor is None:
            raise ValueError(
                "Database connection not established. Use context manager or connect()."
            )
        for env in environments:
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO environments
                (id, name, description, project_key)
                VALUES (?, ?, ?, ?)
                """,
                (env.id, env.name, env.description, project_key),
            )

    def save_test_case(self, test_case: TestCase, project_key: str):
        """Save a test case.

        Args:
            test_case: Test case to save
            project_key: Project key
        """
        if self.cursor is None:
            raise ValueError(
                "Database connection not established. Use context manager or connect()."
            )
        # Convert lists to JSON, using appropriate serialization method
        # (supporting both Pydantic v1's .dict() and v2's .model_dump())
        labels_json = self._serialize_value(test_case.labels)
        steps_json = self._serialize_value(
            [
                step.dict() if hasattr(step, "dict") else step.model_dump()
                for step in test_case.steps
            ]
        )
        custom_fields_json = self._serialize_value(
            [
                cf.dict() if hasattr(cf, "dict") else cf.model_dump()
                for cf in test_case.custom_fields
            ]
        )
        links_json = self._serialize_value(
            [
                link.dict() if hasattr(link, "dict") else link.model_dump()
                for link in test_case.links
            ]
        )
        scripts_json = self._serialize_value(
            [
                script.dict() if hasattr(script, "dict") else script.model_dump()
                for script in test_case.scripts
            ]
        )
        # Handle both new 'versions' field and legacy 'test_versions' field
        versions_attr = "versions" if hasattr(test_case, "versions") else "test_versions"
        versions = getattr(test_case, versions_attr, [])
        versions_json = self._serialize_value(
            [
                version.dict() if hasattr(version, "dict") else version.model_dump()
                for version in versions
            ]
        )

        # Handle the priority if it's an object
        priority_id = None
        if test_case.priority:
            if isinstance(test_case.priority, dict):
                priority_id = test_case.priority.get("id")
            else:
                priority_id = test_case.priority.id

        self.cursor.execute(
            """
            INSERT OR REPLACE INTO test_cases (
                id, key, name, objective, precondition, description, status,
                priority, priority_name, folder, folder_name, owner, owner_name,
                component, component_name, created_on, created_by, updated_on, updated_by,
                version, estimated_time, labels, steps, custom_fields, links, scripts,
                test_versions, project_key
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?
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
                project_key,
            ),
        )

    def save_test_cycle(self, test_cycle: TestCycleInfo):
        """Save a test cycle.

        Args:
            test_cycle: Test cycle to save
        """
        if self.cursor is None:
            raise ValueError(
                "Database connection not established. Use context manager or connect()."
            )
        # Convert lists to JSON
        custom_fields_json = self._serialize_value([cf.dict() for cf in test_cycle.custom_fields])
        links_json = self._serialize_value([link.dict() for link in test_cycle.links])

        self.cursor.execute(
            """
            INSERT OR REPLACE INTO test_cycles (
                id, key, name, description, status, status_name, folder, folder_name,
                project_key, owner, owner_name, created_on, created_by, updated_on,
                updated_by, custom_fields, links
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
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
                test_cycle.project_key,
                test_cycle.owner,
                test_cycle.owner_name,
                self._serialize_value(test_cycle.created_on),
                test_cycle.created_by,
                self._serialize_value(test_cycle.updated_on),
                test_cycle.updated_by,
                custom_fields_json,
                links_json,
            ),
        )

    def save_test_plan(self, test_plan: TestPlan):
        """Save a test plan.

        Args:
            test_plan: Test plan to save
        """
        if self.cursor is None:
            raise ValueError(
                "Database connection not established. Use context manager or connect()."
            )
        # Convert lists to JSON
        custom_fields_json = self._serialize_value([cf.dict() for cf in test_plan.custom_fields])
        links_json = self._serialize_value([link.dict() for link in test_plan.links])

        self.cursor.execute(
            """
            INSERT OR REPLACE INTO test_plans (
                id, key, name, description, status, status_name, folder, folder_name,
                project_key, owner, owner_name, created_on, created_by, updated_on,
                updated_by, custom_fields, links
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                test_plan.id,
                test_plan.key,
                test_plan.name,
                test_plan.description,
                test_plan.status,
                test_plan.status_name,
                test_plan.folder,
                test_plan.folder_name,
                test_plan.project_key,
                test_plan.owner,
                test_plan.owner_name,
                self._serialize_value(test_plan.created_on),
                test_plan.created_by,
                self._serialize_value(test_plan.updated_on),
                test_plan.updated_by,
                custom_fields_json,
                links_json,
            ),
        )

    def save_test_execution(self, test_execution: TestExecution, project_key: str):
        """Save a test execution.

        Args:
            test_execution: Test execution to save
            project_key: Project key
        """
        if self.cursor is None:
            raise ValueError(
                "Database connection not established. Use context manager or connect()."
            )
        # Convert lists to JSON
        steps_json = self._serialize_value([step.dict() for step in test_execution.steps])
        custom_fields_json = self._serialize_value(
            [cf.dict() for cf in test_execution.custom_fields]
        )
        links_json = self._serialize_value([link.dict() for link in test_execution.links])

        self.cursor.execute(
            """
            INSERT OR REPLACE INTO test_executions (
                id, test_case_key, cycle_id, cycle_name, status, status_name,
                environment, environment_name, executed_by, executed_by_name,
                executed_on, created_on, created_by, updated_on, updated_by,
                actual_time, comment, steps, custom_fields, links, project_key
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
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
                project_key,
            ),
        )

    def initialize_database(self):
        """Initialize the database by creating all required tables."""
        self._create_tables()
        self.conn.commit()


class JSONStorage:
    """Storage class for saving Zephyr Scale data to JSON files."""

    def __init__(self, output_dir: Path):
        """Initialize JSON storage.

        Args:
            output_dir: Directory to store JSON files
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass

    def initialize_database(self):
        """No-op for JSON storage to match SQLite interface."""
        pass

    def _serialize_object(self, obj: Any) -> Any:
        """Serialize a Pydantic object to a dictionary or other serializable format."""
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

    def save_project(
        self,
        project_key: str,
        project_name: str,
        project_id: str,
        description: Optional[str] = None,
    ):
        """Save project information.

        Args:
            project_key: Project key
            project_name: Project name
            project_id: Project ID
            description: Project description
        """
        project_data = {
            "id": project_id,
            "key": project_key,
            "name": project_name,
            "description": description,
        }

        with open(self.output_dir / "project.json", "w") as f:
            json.dump(project_data, f, indent=2)

    def save_data(self, data: List[T], filename: str):
        """Save a list of objects to a JSON file.

        Args:
            data: List of objects to save
            filename: Name of the JSON file
        """
        serialized_data = [self._serialize_object(item) for item in data]

        with open(self.output_dir / filename, "w") as f:
            json.dump(serialized_data, f, indent=2)

    def save_folders(self, folders: List[Folder], project_key: str):
        """Save folders for a project.

        Args:
            folders: List of folders
            project_key: Project key
        """
        self.save_data(folders, "folders.json")

    def save_statuses(self, statuses: List[Status], project_key: str):
        """Save statuses for a project.

        Args:
            statuses: List of statuses
            project_key: Project key
        """
        self.save_data(statuses, "statuses.json")

    def save_priorities(self, priorities: List[Priority], project_key: str):
        """Save priorities for a project.

        Args:
            priorities: List of priorities
            project_key: Project key
        """
        self.save_data(priorities, "priorities.json")

    def save_environments(self, environments: List[Environment], project_key: str):
        """Save environments for a project.

        Args:
            environments: List of environments
            project_key: Project key
        """
        self.save_data(environments, "environments.json")

    def save_test_cases(self, test_cases: List[TestCase], project_key: str):
        """Save test cases.

        Args:
            test_cases: List of test cases
            project_key: Project key
        """
        self.save_data(test_cases, "test_cases.json")

    def save_test_case(self, test_case: TestCase, project_key: str):
        """Save a test case.

        Args:
            test_case: Test case to save
            project_key: Project key
        """
        # In JSON storage, we append to an array rather than saving individually
        test_cases_file = self.output_dir / "test_cases.json"

        if test_cases_file.exists():
            with open(test_cases_file, "r") as f:
                test_cases = json.load(f)
        else:
            test_cases = []

        # Check if the test case already exists
        for i, tc in enumerate(test_cases):
            if tc["id"] == test_case.id:
                # Update existing test case
                test_cases[i] = self._serialize_object(test_case)
                break
        else:
            # Add new test case
            test_cases.append(self._serialize_object(test_case))

        with open(test_cases_file, "w") as f:
            json.dump(test_cases, f, indent=2)

    def save_test_cycles(self, test_cycles: List[TestCycleInfo], project_key: str):
        """Save test cycles.

        Args:
            test_cycles: List of test cycles
            project_key: Project key
        """
        self.save_data(test_cycles, "test_cycles.json")

    def save_test_cycle(self, test_cycle: TestCycleInfo):
        """Save a test cycle.

        Args:
            test_cycle: Test cycle to save
        """
        # Similar to save_test_case but for cycles
        test_cycles_file = self.output_dir / "test_cycles.json"

        if test_cycles_file.exists():
            with open(test_cycles_file, "r") as f:
                test_cycles = json.load(f)
        else:
            test_cycles = []

        for i, tc in enumerate(test_cycles):
            if tc["id"] == test_cycle.id:
                test_cycles[i] = self._serialize_object(test_cycle)
                break
        else:
            test_cycles.append(self._serialize_object(test_cycle))

        with open(test_cycles_file, "w") as f:
            json.dump(test_cycles, f, indent=2)

    def save_test_plans(self, test_plans: List[TestPlan], project_key: str):
        """Save test plans.

        Args:
            test_plans: List of test plans
            project_key: Project key
        """
        self.save_data(test_plans, "test_plans.json")

    def save_test_plan(self, test_plan: TestPlan):
        """Save a test plan.

        Args:
            test_plan: Test plan to save
        """
        test_plans_file = self.output_dir / "test_plans.json"

        if test_plans_file.exists():
            with open(test_plans_file, "r") as f:
                test_plans = json.load(f)
        else:
            test_plans = []

        for i, tp in enumerate(test_plans):
            if tp["id"] == test_plan.id:
                test_plans[i] = self._serialize_object(test_plan)
                break
        else:
            test_plans.append(self._serialize_object(test_plan))

        with open(test_plans_file, "w") as f:
            json.dump(test_plans, f, indent=2)

    def save_test_executions(self, test_executions: List[TestExecution], project_key: str):
        """Save test executions.

        Args:
            test_executions: List of test executions
            project_key: Project key
        """
        self.save_data(test_executions, "test_executions.json")

    def save_test_execution(self, test_execution: TestExecution, project_key: str):
        """Save a test execution.

        Args:
            test_execution: Test execution to save
            project_key: Project key
        """
        test_executions_file = self.output_dir / "test_executions.json"

        if test_executions_file.exists():
            with open(test_executions_file, "r") as f:
                test_executions = json.load(f)
        else:
            test_executions = []

        for i, te in enumerate(test_executions):
            if te["id"] == test_execution.id:
                test_executions[i] = self._serialize_object(test_execution)
                break
        else:
            test_executions.append(self._serialize_object(test_execution))

        with open(test_executions_file, "w") as f:
            json.dump(test_executions, f, indent=2)
