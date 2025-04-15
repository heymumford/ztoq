"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
PostgreSQL implementation of the database manager for the SQL-based ETL workflow
as defined in ADR-013.

This module provides a PostgreSQL-specific implementation of the DatabaseManager
that supports all the features required for the ETL migration workflow, including
connection pooling, transaction management, and schema migrations.
"""

import json
import logging
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
import psycopg2
import sqlalchemy
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from ztoq.core.db_models import Base
from ztoq.database_manager import DatabaseManager as SQLiteDatabaseManager
from ztoq.data_fetcher import FetchResult
from ztoq.models import Case, CycleInfo, Environment, Execution, Folder, Priority, Project, Status
from ztoq.validation import ValidationIssue, ValidationLevel, ValidationPhase, ValidationScope

logger = logging.getLogger(__name__)


class PostgreSQLDatabaseManager(SQLiteDatabaseManager):
    """
    PostgreSQL implementation of the database manager.

    This class extends the base DatabaseManager to provide PostgreSQL-specific
    functionality, including connection pooling, transaction management, and
    schema migrations as specified in ADR-013.
    """

    def __init__(
        self,
        host: str,
        database: str,
        user: str,
        password: str,
        port: int = 5432,
        min_connections: int = 5,
        max_connections: int = 20,
    ):
        """
        Initialize the PostgreSQL database manager.

        Args:
            host: Database server hostname
            database: Database name
            user: Database username
            password: Database password
            port: Database server port (default: 5432)
            min_connections: Minimum number of connections in the pool
            max_connections: Maximum number of connections in the pool
        """
        self.connection_params = {
            "host": host,
            "database": database,
            "user": user,
            "password": password,
            "port": port,
        }

        # Create connection URL for SQLAlchemy
        self.db_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"

        # Initialize connection pool
        self.pool = self._create_connection_pool(min_connections, max_connections)

        # Create SQLAlchemy engine with connection pool
        self.engine = self._create_sqlalchemy_engine()

        # Create session factory
        self.Session = sessionmaker(bind=self.engine)

        logger.info(f"PostgreSQL database manager initialized for {database} on {host}:{port}")

    def _create_connection_pool(
        self, min_connections: int, max_connections: int
    ) -> pool.ThreadedConnectionPool:
        """
        Create a connection pool for PostgreSQL.

        Args:
            min_connections: Minimum number of connections in the pool
            max_connections: Maximum number of connections in the pool

        Returns:
            ThreadedConnectionPool instance
        """
        try:
            connection_pool = pool.ThreadedConnectionPool(
                minconn=min_connections, maxconn=max_connections, **self.connection_params
            )
            logger.info(
                f"Created PostgreSQL connection pool with {min_connections}-{max_connections} connections"
            )
            return connection_pool
        except Exception as e:
            logger.error(f"Failed to create connection pool: {str(e)}")
            raise

    def _create_sqlalchemy_engine(self) -> Engine:
        """
        Create a SQLAlchemy engine with connection pooling.

        Returns:
            SQLAlchemy Engine instance
        """
        try:
            # Create engine with connection pooling
            engine = create_engine(
                self.db_url,
                pool_size=10,
                max_overflow=20,
                pool_recycle=3600,  # Recycle connections after 1 hour
                pool_pre_ping=True,  # Check connection health before using
                isolation_level="READ COMMITTED",  # Default isolation level
            )
            return engine
        except Exception as e:
            logger.error(f"Failed to create SQLAlchemy engine: {str(e)}")
            raise

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections from the pool.

        This ensures that connections are properly returned to the pool after use,
            even if an error occurs.

        Yields:
            PostgreSQL connection object
        """
        conn = None
        try:
            conn = self.pool.getconn()
            # Use RealDictCursor to return dictionaries instead of tuples
            conn.cursor_factory = RealDictCursor
            yield conn
        finally:
            if conn:
                self.pool.putconn(conn)

    @contextmanager
    def get_session(self):
        """
        Context manager for SQLAlchemy sessions.

        This ensures that sessions are properly closed after use,
            even if an error occurs.

        Yields:
            SQLAlchemy Session object
        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def initialize_database(self) -> None:
        """
        Creates all necessary database tables if they don't exist.

        This method establishes the schema for storing all migration data,
            using the SQLAlchemy ORM models defined in core.db_models.
        """
        try:
            # Create all tables based on SQLAlchemy models
            Base.metadata.create_all(self.engine)

            # Create additional indexes for performance
            with self.get_session() as session:
                # Check if validation_issues table exists and create indexes if needed
                try:
                    session.execute(
                        text(
                            """
                    CREATE INDEX IF NOT EXISTS idx_validation_issues_project
                    ON validation_issues (project_key)
                    """
                        )
                    )

                    session.execute(
                        text(
                            """
                    CREATE INDEX IF NOT EXISTS idx_validation_issues_level
                    ON validation_issues (level)
                    """
                        )
                    )

                    session.execute(
                        text(
                            """
                    CREATE INDEX IF NOT EXISTS idx_validation_issues_phase
                    ON validation_issues (phase)
                    """
                        )
                    )

                    session.execute(
                        text(
                            """
                    CREATE INDEX IF NOT EXISTS idx_validation_issues_scope
                    ON validation_issues (scope)
                    """
                        )
                    )

                    session.execute(
                        text(
                            """
                    CREATE INDEX IF NOT EXISTS idx_validation_issues_resolved
                    ON validation_issues (resolved)
                    """
                        )
                    )
                except (ProgrammingError, OperationalError) as e:
                    # Table might not exist yet, which is okay during initial setup
                    logger.warning(f"Couldn't create validation_issues indexes: {str(e)}")

                # Create additional indexes for performance as defined in ADR-013
                try:
                    for index_stmt in self._get_performance_indexes():
                        session.execute(text(index_stmt))
                except Exception as e:
                    logger.warning(f"Couldn't create some indexes: {str(e)}")

            logger.info("PostgreSQL database schema initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database schema: {str(e)}")
            raise

    def _get_performance_indexes(self) -> List[str]:
        """
        Get SQL statements for creating additional performance indexes
        as defined in ADR-013.

        Returns:
            List of SQL CREATE INDEX statements
        """
        return [
            "CREATE INDEX IF NOT EXISTS idx_project_key ON projects(key)",
            "CREATE INDEX IF NOT EXISTS idx_testcase_project ON test_cases(project_key)",
            "CREATE INDEX IF NOT EXISTS idx_execution_testcycle ON test_executions(cycle_id)",
            "CREATE INDEX IF NOT EXISTS idx_attachments_related ON attachments(entity_type, entity_id)",
            "CREATE INDEX IF NOT EXISTS idx_migration_state_project ON migration_state(project_key)",
            "CREATE INDEX IF NOT EXISTS idx_entity_batch_type_status ON entity_batch_state(entity_type, status)",
            "CREATE INDEX IF NOT EXISTS idx_custom_field_entity ON custom_field_values(entity_type, entity_id)",
        ]

    def test_connection(self) -> bool:
        """
        Test the database connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    return result[0] == 1
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False

    def execute_transaction(self, statements: List[Tuple[str, Dict[str, Any]]]) -> bool:
        """
        Execute multiple SQL statements in a single transaction.

        Args:
            statements: List of tuples containing SQL statement and parameters

        Returns:
            True if transaction succeeded, False otherwise
        """
        try:
            with self.get_connection() as conn:
                # Start a transaction
                conn.autocommit = False

                with conn.cursor() as cursor:
                    for stmt, params in statements:
                        cursor.execute(stmt, params)

                # Commit the transaction
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}")
            return False
        finally:
            # Reset autocommit setting
            if conn:
                conn.autocommit = True

    def count_entities(self, project_key: str, entity_type: str) -> int:
        """
        Count entities of a specific type for a project.

        Args:
            project_key: The project key
            entity_type: The entity type to count

        Returns:
            Count of entities
        """
        # Determine table name from entity type
        table_name = self._get_table_name(entity_type)

        try:
            with self.get_session() as session:
                result = session.execute(
                    text(f"SELECT COUNT(*) FROM {table_name} WHERE project_key = :project_key"),
                    {"project_key": project_key},
                )
                return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting {entity_type} entities: {str(e)}")
            return 0

    def _get_table_name(self, entity_type: str) -> str:
        """
        Get the database table name for an entity type.

        Args:
            entity_type: The entity type

        Returns:
            Database table name
        """
        # Mapping of entity types to table names
        mapping = {
            "test_cases": "test_cases",
            "test_cycles": "test_cycles",
            "test_executions": "test_executions",
            "folders": "folders",
            "projects": "projects",
            "statuses": "statuses",
            "priorities": "priorities",
            "environments": "environments",
            "validation_issues": "validation_issues",
            "entity_batch_state": "entity_batch_state",
            "migration_state": "migration_state",
        }

        return mapping.get(entity_type, entity_type)

    def count_entity_mappings(self, project_key: str, mapping_type: str) -> int:
        """
        Count entity mappings of a specific type for a project.

        Args:
            project_key: The project key
            mapping_type: The mapping type to count

        Returns:
            Count of mappings
        """
        try:
            with self.get_session() as session:
                result = session.execute(
                    text(
                        """
                    SELECT COUNT(*)
                    FROM entity_mappings
                    WHERE project_key = :project_key
                    AND mapping_type = :mapping_type
                    """
                    ),
                    {"project_key": project_key, "mapping_type": mapping_type},
                )
                return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting {mapping_type} mappings: {str(e)}")
            # Create the entity_mappings table if it doesn't exist
            try:
                self._create_entity_mappings_table()
                return 0
            except:
                return 0

    def _create_entity_mappings_table(self) -> None:
        """Create the entity_mappings table if it doesn't exist."""
        try:
            with self.get_session() as session:
                session.execute(
                    text(
                        """
                CREATE TABLE IF NOT EXISTS entity_mappings (
                    id SERIAL PRIMARY KEY,
                        project_key TEXT NOT NULL,
                        mapping_type TEXT NOT NULL,
                        source_id TEXT NOT NULL,
                        target_id TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(project_key, mapping_type, source_id)
                )
                """
                    )
                )

                session.execute(
                    text(
                        """
                CREATE INDEX IF NOT EXISTS idx_entity_mappings_project ON entity_mappings(project_key)
                """
                    )
                )

                session.execute(
                    text(
                        """
                CREATE INDEX IF NOT EXISTS idx_entity_mappings_type ON entity_mappings(mapping_type)
                """
                    )
                )

                session.execute(
                    text(
                        """
                CREATE INDEX IF NOT EXISTS idx_entity_mappings_source ON entity_mappings(source_id)
                """
                    )
                )

                session.execute(
                    text(
                        """
                CREATE INDEX IF NOT EXISTS idx_entity_mappings_target ON entity_mappings(target_id)
                """
                    )
                )
        except Exception as e:
            logger.error(f"Error creating entity_mappings table: {str(e)}")

    def find_invalid_references(
        self,
        project_key: str,
        table_name: str,
        reference_field: str,
        target_table: str,
        target_id_field: str,
    ) -> List[str]:
        """
        Find invalid references in a table.

        Args:
            project_key: The project key
            table_name: The table to check references in
            reference_field: The field containing the reference
            target_table: The table being referenced
            target_id_field: The ID field in the target table

        Returns:
            List of entity IDs with invalid references
        """
        try:
            with self.get_session() as session:
                result = session.execute(
                    text(
                        f"""
                    SELECT a.id
                    FROM {table_name} a
                    LEFT JOIN {target_table} b
                        ON a.{reference_field} = b.{target_id_field}
                    WHERE a.project_key = :project_key
                      AND a.{reference_field} IS NOT NULL
                      AND b.{target_id_field} IS NULL
                    """
                    ),
                    {"project_key": project_key},
                )
                return [row[0] for row in result]
        except Exception as e:
            logger.error(f"Error finding invalid references: {str(e)}")
            return []

    def entity_exists(self, entity_type: str, entity_id: str) -> bool:
        """
        Check if an entity exists.

        Args:
            entity_type: The entity type
            entity_id: The entity ID

        Returns:
            True if entity exists, False otherwise
        """
        table_name = self._get_table_name(entity_type)

        try:
            with self.get_session() as session:
                result = session.execute(
                    text(f"SELECT COUNT(*) FROM {table_name} WHERE id = :id"), {"id": entity_id}
                )
                return (result.scalar() or 0) > 0
        except Exception as e:
            logger.error(f"Error checking entity existence: {str(e)}")
            return False

    def is_entity_migrated(self, project_key: str, entity_type: str, entity_id: str) -> bool:
        """
        Check if an entity has been migrated.

        Args:
            project_key: The project key
            entity_type: The entity type
            entity_id: The entity ID

        Returns:
            True if entity has been migrated, False otherwise
        """
        # Determine mapping type from entity type
        mapping_type = self._get_mapping_type(entity_type)

        try:
            with self.get_session() as session:
                result = session.execute(
                    text(
                        """
                    SELECT COUNT(*)
                    FROM entity_mappings
                    WHERE project_key = :project_key
                    AND mapping_type = :mapping_type
                    AND source_id = :source_id
                    """
                    ),
                    {
                        "project_key": project_key,
                        "mapping_type": mapping_type,
                        "source_id": entity_id,
                    },
                )
                return (result.scalar() or 0) > 0
        except Exception as e:
            logger.error(f"Error checking if entity is migrated: {str(e)}")
            return False

    def _get_mapping_type(self, entity_type: str) -> str:
        """
        Get the mapping type for an entity type.

        Args:
            entity_type: The entity type

        Returns:
            Mapping type
        """
        # Mapping of entity types to mapping types
        mapping = {
            "folders": "folder_to_module",
            "test_cases": "testcase_to_testcase",
            "test_cycles": "cycle_to_cycle",
            "test_executions": "execution_to_run",
        }

        return mapping.get(entity_type, f"{entity_type}_mapping")

    def get_mapped_entity_id(
        self, project_key: str, mapping_type: str, source_id: str
    ) -> Optional[str]:
        """
        Get the mapped target entity ID for a source entity.

        Args:
            project_key: The project key
            mapping_type: The mapping type
            source_id: The source entity ID

        Returns:
            Target entity ID or None if not mapped
        """
        try:
            with self.get_session() as session:
                result = session.execute(
                    text(
                        """
                    SELECT target_id
                    FROM entity_mappings
                    WHERE project_key = :project_key
                    AND mapping_type = :mapping_type
                    AND source_id = :source_id
                    """
                    ),
                    {
                        "project_key": project_key,
                        "mapping_type": mapping_type,
                        "source_id": source_id,
                    },
                )
                row = result.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Error getting mapped entity ID: {str(e)}")
            return None

    def get_high_priority_test_cases(self, project_key: str) -> List[Dict[str, Any]]:
        """
        Get high-priority test cases for a project.

        Args:
            project_key: The project key

        Returns:
            List of high-priority test cases
        """
        try:
            with self.get_session() as session:
                result = session.execute(
                    text(
                        """
                    SELECT tc.id, tc.name, tc.key, tc.priority_name
                    FROM test_cases tc
                    JOIN priorities p ON tc.priority_id = p.id
                    WHERE tc.project_key = :project_key
                    AND p.rank <= 2
                    ORDER BY p.rank
                    """
                    ),
                    {"project_key": project_key},
                )
                return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Error getting high-priority test cases: {str(e)}")
            return []

    def save_validation_issue(self, issue: ValidationIssue, project_key: str) -> int:
        """
        Save a validation issue to the database.

        Args:
            issue: The ValidationIssue object to save
            project_key: The project key

        Returns:
            ID of the saved issue
        """
        # Create a more detailed context that includes entity type
        context_data = issue.details or {}
        if issue.entity_type:
            context_data["entity_type"] = issue.entity_type

        context_json = json.dumps(context_data) if context_data else None

        try:
            with self.get_session() as session:
                result = session.execute(
                    text(
                        """
                    INSERT INTO validation_issues
                    (rule_id, level, message, entity_id, entity_type, scope, phase, context,
                        project_key, created_on, resolved)
                    VALUES (:rule_id, :level, :message, :entity_id, :entity_type, :scope, :phase, :context,
                        :project_key, :created_on, :resolved)
                    RETURNING id
                    """
                    ),
                    {
                        "rule_id": issue.id,
                        "level": issue.level.value,
                        "message": issue.message,
                        "entity_id": issue.entity_id,
                        "entity_type": issue.entity_type,
                        "scope": issue.scope.value,
                        "phase": issue.phase.value,
                        "context": context_json,
                        "project_key": project_key,
                        "created_on": datetime.now().isoformat(),
                        "resolved": 0,
                    },
                )
                row = result.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.error(f"Error saving validation issue: {str(e)}")
            # Attempt to create the table if it doesn't exist
            try:
                self._create_validation_tables()
                return 0
            except:
                return 0

    def _create_validation_tables(self) -> None:
        """Create validation-related tables if they don't exist."""
        try:
            with self.get_session() as session:
                # Create validation_rules table
                session.execute(
                    text(
                        """
                CREATE TABLE IF NOT EXISTS validation_rules (
                    id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT NOT NULL,
                        scope TEXT NOT NULL,
                        phase TEXT NOT NULL,
                        level TEXT NOT NULL,
                        enabled INTEGER DEFAULT 1,
                        created_on TEXT NOT NULL
                )
                """
                    )
                )

                # Create validation_issues table
                session.execute(
                    text(
                        """
                CREATE TABLE IF NOT EXISTS validation_issues (
                    id SERIAL PRIMARY KEY,
                        rule_id TEXT NOT NULL,
                        level TEXT NOT NULL,
                        message TEXT NOT NULL,
                        entity_id TEXT,
                        entity_type TEXT,
                        scope TEXT NOT NULL,
                        phase TEXT NOT NULL,
                        context TEXT,
                        project_key TEXT NOT NULL,
                        created_on TEXT NOT NULL,
                        resolved INTEGER DEFAULT 0,
                        resolved_on TEXT,
                        resolution_note TEXT
                )
                """
                    )
                )

                # Create validation_reports table
                session.execute(
                    text(
                        """
                CREATE TABLE IF NOT EXISTS validation_reports (
                    id SERIAL PRIMARY KEY,
                        project_key TEXT NOT NULL,
                        report_date TEXT NOT NULL,
                        issue_counts TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        details TEXT
                )
                """
                    )
                )

                # Create indexes
                self._create_validation_indexes(session)
        except Exception as e:
            logger.error(f"Error creating validation tables: {str(e)}")

    def _create_validation_indexes(self, session) -> None:
        """Create indexes for validation tables."""
        try:
            session.execute(
                text(
                    """
            CREATE INDEX IF NOT EXISTS idx_validation_issues_project
            ON validation_issues (project_key)
            """
                )
            )

            session.execute(
                text(
                    """
            CREATE INDEX IF NOT EXISTS idx_validation_issues_level
            ON validation_issues (level)
            """
                )
            )

            session.execute(
                text(
                    """
            CREATE INDEX IF NOT EXISTS idx_validation_issues_phase
            ON validation_issues (phase)
            """
                )
            )

            session.execute(
                text(
                    """
            CREATE INDEX IF NOT EXISTS idx_validation_issues_scope
            ON validation_issues (scope)
            """
                )
            )

            session.execute(
                text(
                    """
            CREATE INDEX IF NOT EXISTS idx_validation_issues_resolved
            ON validation_issues (resolved)
            """
                )
            )

            session.execute(
                text(
                    """
            CREATE INDEX IF NOT EXISTS idx_validation_reports_project
            ON validation_reports (project_key)
            """
                )
            )
        except Exception as e:
            logger.error(f"Error creating validation indexes: {str(e)}")

    def get_qtest_module_for_testcase(self, qtest_testcase_id: str) -> Optional[str]:
        """
        Get the qTest module ID for a test case.

        Args:
            qtest_testcase_id: The qTest test case ID

        Returns:
            qTest module ID or None if not found
        """
        # This would access the qTest table in a real implementation
        # For now, just return None as a placeholder
        return None

    def get_qtest_testcase_for_run(self, qtest_run_id: str) -> Optional[str]:
        """
        Get the qTest test case ID for a test run.

        Args:
            qtest_run_id: The qTest test run ID

        Returns:
            qTest test case ID or None if not found
        """
        # This would access the qTest table in a real implementation
        # For now, just return None as a placeholder
        return None

    def get_qtest_cycle_for_run(self, qtest_run_id: str) -> Optional[str]:
        """
        Get the qTest test cycle ID for a test run.

        Args:
            qtest_run_id: The qTest test run ID

        Returns:
            qTest test cycle ID or None if not found
        """
        # This would access the qTest table in a real implementation
        # For now, just return None as a placeholder
        return None

    def get_test_cases_with_folders(self, project_key: str) -> List[Dict[str, Any]]:
        """
        Get test cases with their folder information.

        Args:
            project_key: The project key

        Returns:
            List of test cases with folder information
        """
        try:
            with self.get_session() as session:
                result = session.execute(
                    text(
                        """
                    SELECT tc.id, tc.key, tc.name, tc.folder_id, f.name as folder_name
                    FROM test_cases tc
                    LEFT JOIN folders f ON tc.folder_id = f.id
                    WHERE tc.project_key = :project_key
                    """
                    ),
                    {"project_key": project_key},
                )
                return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Error getting test cases with folders: {str(e)}")
            return []

    def get_test_executions_with_testcases(self, project_key: str) -> List[Dict[str, Any]]:
        """
        Get test executions with their test case information.

        Args:
            project_key: The project key

        Returns:
            List of test executions with test case information
        """
        try:
            with self.get_session() as session:
                result = session.execute(
                    text(
                        """
                    SELECT e.id, e.test_case_key, tc.id as test_case_id, tc.name as test_case_name
                    FROM test_executions e
                    JOIN test_cases tc ON e.test_case_key = tc.key
                    WHERE e.project_key = :project_key
                    """
                    ),
                    {"project_key": project_key},
                )
                return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Error getting test executions with test cases: {str(e)}")
            return []

    def get_test_executions_with_cycles(self, project_key: str) -> List[Dict[str, Any]]:
        """
        Get test executions with their cycle information.

        Args:
            project_key: The project key

        Returns:
            List of test executions with cycle information
        """
        try:
            with self.get_session() as session:
                result = session.execute(
                    text(
                        """
                    SELECT e.id, e.cycle_id, c.name as cycle_name
                    FROM test_executions e
                    JOIN test_cycles c ON e.cycle_id = c.id
                    WHERE e.project_key = :project_key
                    """
                    ),
                    {"project_key": project_key},
                )
                return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Error getting test executions with cycles: {str(e)}")
            return []

    def get_test_cases_with_custom_fields(self, project_key: str) -> List[Dict[str, Any]]:
        """
        Get test cases with their custom fields.

        Args:
            project_key: The project key

        Returns:
            List of test cases with custom fields
        """
        try:
            with self.get_session() as session:
                # Directly use the JSON custom_fields column from test_cases
                result = session.execute(
                    text(
                        """
                    SELECT id, key, name, custom_fields
                    FROM test_cases
                    WHERE project_key = :project_key
                    AND custom_fields IS NOT NULL
                    """
                    ),
                    {"project_key": project_key},
                )

                test_cases = []
                for row in result:
                    test_case = dict(row)

                    # Parse custom_fields JSON
                    if test_case["custom_fields"]:
                        try:
                            custom_fields = json.loads(test_case["custom_fields"])
                            # Convert list to dictionary for easier access
                            custom_fields_dict = {}
                            for cf in custom_fields:
                                if isinstance(cf, dict) and "name" in cf and "value" in cf:
                                    custom_fields_dict[cf["name"]] = cf["value"]
                            test_case["custom_fields"] = custom_fields_dict
                        except:
                            test_case["custom_fields"] = {}
                    else:
                        test_case["custom_fields"] = {}

                    test_cases.append(test_case)

                return test_cases
        except Exception as e:
            logger.error(f"Error getting test cases with custom fields: {str(e)}")
            return []

    def get_qtest_custom_fields(self, qtest_testcase_id: str) -> Dict[str, Any]:
        """
        Get custom fields for a qTest test case.

        Args:
            qtest_testcase_id: The qTest test case ID

        Returns:
            Dictionary of custom field name-value pairs
        """
        # This would access the qTest table in a real implementation
        # For now, just return an empty dict as a placeholder
        return {}

    def get_entities_with_attachments(self, project_key: str) -> List[Dict[str, Any]]:
        """
        Get entities with their attachments.

        Args:
            project_key: The project key

        Returns:
            List of entities with attachment information
        """
        attachments_by_entity = {}

        try:
            with self.get_session() as session:
                # Get test cases with attachments
                result = session.execute(
                    text(
                        """
                    SELECT id, key, name, attachments, 'test_cases' as entity_type
                    FROM test_cases
                    WHERE project_key = :project_key
                    AND attachments IS NOT NULL
                    """
                    ),
                    {"project_key": project_key},
                )

                for row in result:
                    entity = dict(row)

                    # Parse attachments JSON
                    if entity["attachments"]:
                        try:
                            attachments = json.loads(entity["attachments"])
                            entity_key = (entity["entity_type"], entity["id"])
                            attachments_by_entity[entity_key] = {
                                "entity_type": entity["entity_type"],
                                "entity_id": entity["id"],
                                "attachments": attachments,
                            }
                        except:
                            pass

                # Get test executions with attachments
                result = session.execute(
                    text(
                        """
                    SELECT id, test_case_key, attachments, 'test_executions' as entity_type
                    FROM test_executions
                    WHERE project_key = :project_key
                    AND attachments IS NOT NULL
                    """
                    ),
                    {"project_key": project_key},
                )

                for row in result:
                    entity = dict(row)

                    # Parse attachments JSON
                    if entity["attachments"]:
                        try:
                            attachments = json.loads(entity["attachments"])
                            entity_key = (entity["entity_type"], entity["id"])
                            attachments_by_entity[entity_key] = {
                                "entity_type": entity["entity_type"],
                                "entity_id": entity["id"],
                                "attachments": attachments,
                            }
                        except:
                            pass

                # Get test cycles with attachments
                result = session.execute(
                    text(
                        """
                    SELECT id, key, name, attachments, 'test_cycles' as entity_type
                    FROM test_cycles
                    WHERE project_key = :project_key
                    AND attachments IS NOT NULL
                    """
                    ),
                    {"project_key": project_key},
                )

                for row in result:
                    entity = dict(row)

                    # Parse attachments JSON
                    if entity["attachments"]:
                        try:
                            attachments = json.loads(entity["attachments"])
                            entity_key = (entity["entity_type"], entity["id"])
                            attachments_by_entity[entity_key] = {
                                "entity_type": entity["entity_type"],
                                "entity_id": entity["id"],
                                "attachments": attachments,
                            }
                        except:
                            pass

                return list(attachments_by_entity.values())
        except Exception as e:
            logger.error(f"Error getting entities with attachments: {str(e)}")
            return []

    def get_qtest_attachments(self, entity_type: str, qtest_entity_id: str) -> List[Dict[str, Any]]:
        """
        Get attachments for a qTest entity.

        Args:
            entity_type: The entity type
            qtest_entity_id: The qTest entity ID

        Returns:
            List of attachments
        """
        # This would access the qTest table in a real implementation
        # For now, just return an empty list as a placeholder
        return []

    def close(self) -> None:
        """Close the database connection pool."""
        if hasattr(self, "pool") and self.pool:
            self.pool.closeall()
            logger.info("PostgreSQL connection pool closed")
