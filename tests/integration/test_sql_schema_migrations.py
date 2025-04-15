"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, inspect, text
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from ztoq.core.db_manager import DatabaseConfig, SQLDatabaseManager
from ztoq.core.db_models import Base, Project, RecommendationHistory, TestCase
from ztoq.models import Project as ProjectModel

# Setup test logger
logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.db
class TestSQLSchemaMigrations:
    """Integration tests for SQL database schema and Alembic migrations."""

    @pytest.fixture(scope="class")
    def test_project_key(self):
        """Generate a unique project key for testing."""
        return f"TEST-{uuid.uuid4().hex[:8]}"

    @pytest.fixture(scope="function")
    def temp_db_path(self):
        """Create a temporary directory and SQLite database file for testing."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_migrations.db")
        yield db_path
        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture(scope="function")
    def alembic_config(self):
        """Create an Alembic configuration for testing."""
        # Find the alembic.ini file
        project_root = Path(__file__).parent.parent.parent
        alembic_ini_path = project_root / "config" / "alembic.ini"

        if not alembic_ini_path.exists():
            # Try alternative location
            alembic_ini_path = project_root / "alembic.ini"

        if not alembic_ini_path.exists():
            pytest.skip("Alembic configuration not found. Skipping migration tests.")

        return Config(str(alembic_ini_path))

    @pytest.fixture(scope="function")
    def sqlite_db_manager(self, temp_db_path):
        """Create an SQLite database manager for testing."""
        config = DatabaseConfig(db_type="sqlite", db_path=temp_db_path)
        manager = SQLDatabaseManager(config)
        return manager

    @pytest.fixture(scope="function")
    def sqlite_test_db(self, alembic_config, temp_db_path):
        """Create a configured SQLite database with migrations applied."""
        db_url = f"sqlite:///{temp_db_path}"
        alembic_config.set_main_option("sqlalchemy.url", db_url)

        # Create the database engine
        engine = create_engine(db_url)

        # Apply all migrations
        command.upgrade(alembic_config, "head")

        return engine

    def test_alembic_revision_history(self, alembic_config):
        """Test that Alembic revision history is properly structured with dependencies."""
        # Get the script directory
        script_dir = ScriptDirectory.from_config(alembic_config)

        # Get all revisions
        revisions = list(script_dir.walk_revisions())

        # Check that we have at least one revision
        assert len(revisions) >= 1, "Should have at least one migration revision"

        # Check that the initial revision has no dependencies
        initial_revision = revisions[-1]  # Last in the walk is the first chronologically
        assert initial_revision.down_revision is None, "Initial revision should have no down revision"

        # Check that subsequent revisions have correct dependencies
        for i in range(len(revisions) - 1):
            current = revisions[i]
            next_rev = revisions[i + 1]
            assert current.down_revision == next_rev.revision, f"Revision {current.revision} should depend on {next_rev.revision}"

    def test_sqlite_schema_creation(self, sqlite_test_db):
        """Test that the SQLite schema is correctly created with all necessary tables."""
        inspector = inspect(sqlite_test_db)
        tables = inspector.get_table_names()

        # Check core tables
        essential_tables = [
            "projects", "test_cases", "test_cycles", "test_executions",
            "folders", "attachments", "migration_state", "entity_batch_state",
        ]

        for table in essential_tables:
            assert table in tables, f"Table {table} should exist in the schema"

        # Check relationships through foreign keys
        for table in ["test_cases", "test_cycles", "test_executions"]:
            fks = inspector.get_foreign_keys(table)
            assert any(fk["referred_table"] == "projects" for fk in fks), f"{table} should have foreign key to projects"

    def test_recommendation_history_table(self, sqlite_test_db):
        """Test that the recommendation_history table was properly added by migrations."""
        inspector = inspect(sqlite_test_db)
        tables = inspector.get_table_names()

        # Check recommendation_history table exists
        assert "recommendation_history" in tables, "recommendation_history table should exist"

        # Check columns
        columns = {col["name"] for col in inspector.get_columns("recommendation_history")}
        required_columns = {
            "id", "project_key", "timestamp", "recommendation_id",
            "priority", "category", "issue", "action", "status",
        }

        for col in required_columns:
            assert col in columns, f"Column {col} should exist in recommendation_history table"

        # Check indexes
        indexes = inspector.get_indexes("recommendation_history")
        index_names = {idx["name"] for idx in indexes}

        assert any("project_timestamp" in idx_name for idx_name in index_names), "Should have index on project_key and timestamp"
        assert any("priority" in idx_name for idx_name in index_names), "Should have index on priority"
        assert any("status" in idx_name for idx_name in index_names), "Should have index on status"

    def test_insert_and_query_recommendation(self, sqlite_test_db, test_project_key):
        """Test inserting and querying data from the recommendation_history table."""
        # Create a recommendation entry
        timestamp = datetime.now().isoformat()
        recommendation_id = f"REC-{uuid.uuid4().hex[:8]}"

        with Session(sqlite_test_db) as session:
            # Create a project first
            project = Project(
                id=f"PROJ-{uuid.uuid4().hex[:8]}",
                key=test_project_key,
                name="Test Project",
                description="Test project for recommendation history",
            )
            session.add(project)
            session.commit()

            # Create a recommendation
            recommendation = RecommendationHistory(
                project_key=test_project_key,
                timestamp=datetime.now(),
                recommendation_id=recommendation_id,
                priority="high",
                category="performance",
                issue="Slow database queries detected",
                action="Add index to frequently queried column",
                status="open",
                meta_data={"details": "Query took 500ms, should be <100ms"},
            )
            session.add(recommendation)
            session.commit()

            # Query the recommendation
            result = session.query(RecommendationHistory).filter_by(
                recommendation_id=recommendation_id,
            ).first()

            # Verify data was stored and retrieved correctly
            assert result is not None, "Should retrieve the created recommendation"
            assert result.project_key == test_project_key, "Project key should match"
            assert result.priority == "high", "Priority should match"
            assert result.category == "performance", "Category should match"
            assert result.status == "open", "Status should match"

            # Verify JSON data was stored correctly
            assert isinstance(result.meta_data, dict), "meta_data should be deserialized to dict"
            assert result.meta_data.get("details") == "Query took 500ms, should be <100ms", "JSON data should be preserved"

    def test_downgrade_and_upgrade(self, alembic_config, temp_db_path):
        """Test downgrading and upgrading migrations by going to specific versions."""
        db_url = f"sqlite:///{temp_db_path}"
        alembic_config.set_main_option("sqlalchemy.url", db_url)

        # Create the database engine
        engine = create_engine(db_url)

        # First, upgrade to head
        command.upgrade(alembic_config, "head")

        # Check that all tables exist
        inspector = inspect(engine)
        tables_before = set(inspector.get_table_names())
        assert "recommendation_history" in tables_before, "recommendation_history table should exist after upgrade to head"

        # Get the script directory
        script_dir = ScriptDirectory.from_config(alembic_config)
        revisions = list(script_dir.walk_revisions())

        if len(revisions) >= 2:
            # Downgrade one revision
            command.downgrade(alembic_config, revisions[0].down_revision)

            # Check tables after downgrade
            inspector = inspect(engine)
            tables_after_downgrade = set(inspector.get_table_names())

            # The recommendation_history table should be gone if it was added in the latest migration
            initial_has_recommendation = False
            with engine.connect() as conn:
                # Check if recommendation_history is in the current version
                migration_context = MigrationContext.configure(conn)
                if migration_context.get_current_revision() == "a16c4721be8a":  # Initial schema
                    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='recommendation_history'"))
                    initial_has_recommendation = bool(result.fetchone())

            if not initial_has_recommendation:
                assert "recommendation_history" not in tables_after_downgrade, "recommendation_history should be removed after downgrade"

            # Upgrade again
            command.upgrade(alembic_config, "head")

            # Check tables are back
            inspector = inspect(engine)
            tables_after_upgrade = set(inspector.get_table_names())
            assert tables_before == tables_after_upgrade, "All tables should be restored after upgrading again"
            assert "recommendation_history" in tables_after_upgrade, "recommendation_history should exist after upgrade"

    def test_data_integrity_during_migrations(self, alembic_config, temp_db_path, test_project_key):
        """Test that data remains intact during migration operations."""
        db_url = f"sqlite:///{temp_db_path}"
        alembic_config.set_main_option("sqlalchemy.url", db_url)

        # Create the database engine
        engine = create_engine(db_url)

        # First, upgrade to head
        command.upgrade(alembic_config, "head")

        # Add test data
        with Session(engine) as session:
            # Create projects
            for i in range(5):
                project = Project(
                    id=f"PROJ-{i}",
                    key=f"{test_project_key}-{i}",
                    name=f"Test Project {i}",
                    description=f"Test project {i} for migration data integrity",
                )
                session.add(project)

                # Create test cases linked to projects
                for j in range(3):
                    test_case = TestCase(
                        id=f"TC-{i}-{j}",
                        key=f"{test_project_key}-TC-{i}-{j}",
                        name=f"Test Case {i}-{j}",
                        project_key=project.key,
                    )
                    session.add(test_case)

            session.commit()

        # Downgrade one revision
        script_dir = ScriptDirectory.from_config(alembic_config)
        revisions = list(script_dir.walk_revisions())

        if len(revisions) >= 2:
            command.downgrade(alembic_config, revisions[0].down_revision)

            # Verify data is still intact
            with Session(engine) as session:
                projects = session.query(Project).all()
                assert len(projects) == 5, "All projects should remain after downgrade"

                test_cases = session.query(TestCase).all()
                assert len(test_cases) == 15, "All test cases should remain after downgrade"

            # Upgrade again
            command.upgrade(alembic_config, "head")

            # Verify data is still intact
            with Session(engine) as session:
                projects = session.query(Project).all()
                assert len(projects) == 5, "All projects should remain after upgrade"

                test_cases = session.query(TestCase).all()
                assert len(test_cases) == 15, "All test cases should remain after upgrade"

    def test_schema_matches_models(self, sqlite_test_db):
        """Test that the database schema matches the SQLAlchemy models."""
        # Get the SQLAlchemy metadata
        metadata = Base.metadata

        # Get the database schema
        inspector = inspect(sqlite_test_db)

        # Check each table in the metadata
        for table_name, table in metadata.tables.items():
            assert table_name in inspector.get_table_names(), f"Table {table_name} should exist in database"

            # Check columns
            db_columns = {col["name"]: col for col in inspector.get_columns(table_name)}
            model_columns = {col.name: col for col in table.columns}

            for col_name in model_columns:
                assert col_name in db_columns, f"Column {col_name} in {table_name} should exist in database"

    def test_alembic_current_and_history(self, alembic_config, sqlite_test_db, temp_db_path):
        """Test that Alembic can correctly report current version and migration history."""
        db_url = f"sqlite:///{temp_db_path}"
        alembic_config.set_main_option("sqlalchemy.url", db_url)

        # Get the current revision
        with sqlite_test_db.connect() as conn:
            migration_context = MigrationContext.configure(conn)
            current_rev = migration_context.get_current_revision()

        # Get the script directory
        script_dir = ScriptDirectory.from_config(alembic_config)

        # Get the head revision
        head_rev = script_dir.get_current_head()

        # Verify we're at the head revision
        assert current_rev == head_rev, f"Current revision ({current_rev}) should match head revision ({head_rev})"

        # Get the complete history
        with sqlite_test_db.connect() as conn:
            # Check that alembic_version table exists
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"))
            assert result.fetchone(), "alembic_version table should exist"

            # Check version table content
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version_num = result.fetchone()[0]
            assert version_num == head_rev, "Version in database should match head revision"

    def test_raw_sql_operations(self, sqlite_test_db, test_project_key):
        """Test executing raw SQL operations against the migrated schema."""
        # Insert data using raw SQL
        with sqlite_test_db.connect() as conn:
            # Insert a project
            conn.execute(
                text("""
                INSERT INTO projects (id, key, name, description)
                VALUES (:id, :key, :name, :description)
                """),
                {
                    "id": f"SQL-{uuid.uuid4().hex[:8]}",
                    "key": test_project_key,
                    "name": "SQL Test Project",
                    "description": "Project created with raw SQL",
                },
            )

            # Insert a test case
            conn.execute(
                text("""
                INSERT INTO test_cases (id, key, name, project_key)
                VALUES (:id, :key, :name, :project_key)
                """),
                {
                    "id": f"SQL-TC-{uuid.uuid4().hex[:8]}",
                    "key": f"{test_project_key}-TC-1",
                    "name": "SQL Test Case",
                    "project_key": test_project_key,
                },
            )

            conn.commit()

        # Query data using SQLAlchemy ORM
        with Session(sqlite_test_db) as session:
            project = session.query(Project).filter_by(key=test_project_key).first()
            assert project is not None, "Project should be queryable via ORM after raw SQL insert"
            assert project.name == "SQL Test Project", "Project data should match raw SQL insert"

            test_case = session.query(TestCase).filter_by(project_key=test_project_key).first()
            assert test_case is not None, "Test case should be queryable via ORM after raw SQL insert"
            assert test_case.name == "SQL Test Case", "Test case data should match raw SQL insert"

    def test_create_table_with_alembic_autogenerate(self, alembic_config, temp_db_path):
        """Test creating a new table with Alembic autogenerate."""
        db_url = f"sqlite:///{temp_db_path}"
        alembic_config.set_main_option("sqlalchemy.url", db_url)

        # Create a temporary migration environment
        migrations_dir = Path("migrations_test")
        if migrations_dir.exists():
            shutil.rmtree(migrations_dir)

        try:
            # Initialize migrations directory
            command.init(alembic_config, str(migrations_dir))

            # Update env.py to include our models
            env_py_path = migrations_dir / "env.py"
            with open(env_py_path) as f:
                env_content = f.read()

            # Update imports and metadata
            env_content = env_content.replace(
                "from alembic import context",
                "from alembic import context\nfrom ztoq.core.db_models import Base",
            )
            env_content = env_content.replace(
                "target_metadata = None",
                "target_metadata = Base.metadata",
            )

            with open(env_py_path, "w") as f:
                f.write(env_content)

            # Create a database engine
            engine = create_engine(db_url)

            # Create a new model dynamically
            metadata = MetaData()
            test_table = Table(
                "alembic_test_table",
                metadata,
                Column("id", String(50), primary_key=True),
                Column("name", String(100), nullable=False),
                Column("value", Integer),
            )

            # Create the table directly
            metadata.create_all(engine)

            # Generate migration to detect the new table
            command.revision(
                alembic_config,
                autogenerate=True,
                message="detect_new_table",
                rev_id="test001",
                version_path=str(migrations_dir / "versions"),
            )

            # Check that the migration file contains the new table
            version_files = list((migrations_dir / "versions").glob("*_detect_new_table.py"))
            assert len(version_files) == 1, "Migration file should be created"

            with open(version_files[0]) as f:
                migration_content = f.read()
                assert "alembic_test_table" in migration_content, "Migration should detect the new table"

        finally:
            # Cleanup
            if migrations_dir.exists():
                shutil.rmtree(migrations_dir)

    def test_migration_with_sqlite_constraints(self, sqlite_db_manager, test_project_key):
        """Test migration behavior with SQLite constraints."""
        # Add test data
        project = ProjectModel(
            id=f"PROJ-{uuid.uuid4().hex[:8]}",
            key=test_project_key,
            name="Constraint Test Project",
            description="Test project for SQLite constraints",
        )
        sqlite_db_manager.save_project(project)

        # Verify data was saved
        with sqlite_db_manager.get_session() as session:
            projects = session.query(Project).all()
            assert len(projects) > 0, "Should have at least one project"

            # Test foreign key constraints
            # This should fail because SQLite enforces constraints
            with pytest.raises(Exception):
                # Create a test case with non-existent project key
                test_case = TestCase(
                    id=f"TC-{uuid.uuid4().hex[:8]}",
                    key=f"{test_project_key}-TC-INVALID",
                    name="Invalid Test Case",
                    project_key="NONEXISTENT",  # This project doesn't exist
                )
                session.add(test_case)
                session.commit()

            # This should succeed
            test_case = TestCase(
                id=f"TC-{uuid.uuid4().hex[:8]}",
                key=f"{test_project_key}-TC-VALID",
                name="Valid Test Case",
                project_key=test_project_key,  # This project exists
            )
            session.add(test_case)
            session.commit()

            # Verify the test case was added
            test_cases = session.query(TestCase).filter_by(project_key=test_project_key).all()
            assert len(test_cases) == 1, "Should have one test case"

    def test_migration_idempotency(self, alembic_config, temp_db_path):
        """Test that running migrations multiple times is idempotent."""
        db_url = f"sqlite:///{temp_db_path}"
        alembic_config.set_main_option("sqlalchemy.url", db_url)

        # Create engine
        engine = create_engine(db_url)

        # Run migrations once
        command.upgrade(alembic_config, "head")

        # Get schema state after first migration
        inspector1 = inspect(engine)
        tables1 = set(inspector1.get_table_names())

        # Run migrations again
        command.upgrade(alembic_config, "head")

        # Get schema state after second migration
        inspector2 = inspect(engine)
        tables2 = set(inspector2.get_table_names())

        # Verify schema is identical
        assert tables1 == tables2, "Running migrations multiple times should be idempotent"

        # Check that alembic_version hasn't changed
        with engine.connect() as conn:
            version1 = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()[0]

        # Run migrations a third time
        command.upgrade(alembic_config, "head")

        with engine.connect() as conn:
            version2 = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()[0]

        assert version1 == version2, "Alembic version should not change when rerunning migrations at head"
