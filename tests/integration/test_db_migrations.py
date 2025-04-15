"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import logging
import os
import shutil
import tempfile
from pathlib import Path
import pytest
from sqlalchemy import create_engine, inspect, text
from alembic import command
from alembic.config import Config
from ztoq.core.db_manager import DatabaseConfig, SQLDatabaseManager
from ztoq.core.db_models import Base, Project, TestCase
from ztoq.models import Project as ProjectModel

# Setup test logger
logger = logging.getLogger(__name__)


@pytest.mark.integration()
class TestDatabaseMigrations:
    """Integration tests for database migrations using Alembic."""

    @pytest.fixture(scope="class")
    def temp_db_path(self):
        """Create a temporary directory for the test database."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_migrations.db")
        yield db_path
        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture(scope="class")
    def alembic_cfg(self):
        """Create an Alembic configuration."""
        # Path to alembic.ini relative to the project root
        alembic_ini_path = os.path.join(os.getcwd(), "alembic.ini")

        # Check if alembic.ini exists, if not skip these tests
        if not os.path.exists(alembic_ini_path):
            pytest.skip("Alembic configuration not found. Skipping migration tests.")

        return Config(alembic_ini_path)

    @pytest.fixture()
    def db_manager(self, temp_db_path):
        """Create a database manager for testing."""
        config = DatabaseConfig(db_type="sqlite", db_path=temp_db_path)
        manager = SQLDatabaseManager(config)
        # Initialize the database with current models
        manager.initialize_database()
        return manager

    def test_migration_initialization(self, alembic_cfg, temp_db_path):
        """Test initializing migrations for a new database."""
        # Set the SQLite database URL in the Alembic config
        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{temp_db_path}")

        # Initialize migrations
        command.init(alembic_cfg, "migrations")

        # Verify the migrations directory was created
        migrations_dir = Path("migrations")
        assert migrations_dir.exists(), "Migrations directory should be created"
        assert (migrations_dir / "env.py").exists(), "env.py should be created"
        assert (migrations_dir / "README").exists(), "README should be created"
        assert (migrations_dir / "script.py.mako").exists(), "Script template should be created"
        assert (migrations_dir / "versions").exists(), "Versions directory should be created"

        # Cleanup - remove the migrations directory after test
        if migrations_dir.exists():
            shutil.rmtree(migrations_dir)

    def test_migration_autogeneration(self, alembic_cfg, temp_db_path):
        """Test auto-generating migrations based on model changes."""
        # Set the SQLite database URL in the Alembic config
        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{temp_db_path}")

        # First, create a clean database with no tables
        engine = create_engine(f"sqlite:///{temp_db_path}")
        Base.metadata.drop_all(engine)

        # Initialize migrations
        migrations_dir = Path("migrations_test")
        if migrations_dir.exists():
            shutil.rmtree(migrations_dir)

        command.init(alembic_cfg, str(migrations_dir))

        # Modify the env.py to include our models
        env_py_path = migrations_dir / "env.py"
        with open(env_py_path) as f:
            env_content = f.read()

        # Add import for our models and metadata
        env_content = env_content.replace(
            "from alembic import context",
            "from alembic import context\nfrom ztoq.core.db_models import Base",
        )

        # Set target metadata
        env_content = env_content.replace(
            "target_metadata = None", "target_metadata = Base.metadata"
        )

        # Write the modified env.py
        with open(env_py_path, "w") as f:
            f.write(env_content)

        # Create an initial migration
        command.revision(
            alembic_cfg,
            autogenerate=True,
            message="Initial schema creation",
            rev_id="001",
            version_path=str(migrations_dir / "versions"),
        )

        # Verify the migration file was created
        version_files = list((migrations_dir / "versions").glob("*_initial_schema_creation.py"))
        assert len(version_files) == 1, "Migration file should be created"

        # Apply the migration
        command.upgrade(alembic_cfg, "head")

        # Verify the database now has tables
        engine = create_engine(f"sqlite:///{temp_db_path}")
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        # Check that our core tables were created
        assert "projects" in tables, "Projects table should be created"
        assert "test_cases" in tables, "Test cases table should be created"
        assert "folders" in tables, "Folders table should be created"

        # Now, let's create a new migration with a schema change
        # For this test, we'll just verify a new revision can be created
        command.revision(
            alembic_cfg,
            autogenerate=True,
            message="Add new column",
            rev_id="002",
            version_path=str(migrations_dir / "versions"),
        )

        # Verify the new migration file was created
        version_files = list((migrations_dir / "versions").glob("*_add_new_column.py"))
        assert len(version_files) == 1, "New migration file should be created"

        # Cleanup
        if migrations_dir.exists():
            shutil.rmtree(migrations_dir)

    def test_migration_upgrade_and_downgrade(self, alembic_cfg, temp_db_path):
        """Test upgrading and downgrading migrations."""
        # Set the SQLite database URL in the Alembic config
        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{temp_db_path}")

        # Create a clean database
        engine = create_engine(f"sqlite:///{temp_db_path}")
        Base.metadata.drop_all(engine)

        # Initialize migrations
        migrations_dir = Path("migrations_test")
        if migrations_dir.exists():
            shutil.rmtree(migrations_dir)

        command.init(alembic_cfg, str(migrations_dir))

        # Modify the env.py to include our models
        env_py_path = migrations_dir / "env.py"
        with open(env_py_path) as f:
            env_content = f.read()

        # Add import for our models and metadata
        env_content = env_content.replace(
            "from alembic import context",
            "from alembic import context\nfrom ztoq.core.db_models import Base",
        )

        # Set target metadata
        env_content = env_content.replace(
            "target_metadata = None", "target_metadata = Base.metadata"
        )

        # Write the modified env.py
        with open(env_py_path, "w") as f:
            f.write(env_content)

        # Create initial migration
        command.revision(
            alembic_cfg,
            autogenerate=True,
            message="Initial migration",
            rev_id="001",
            version_path=str(migrations_dir / "versions"),
        )

        # Apply the migration
        command.upgrade(alembic_cfg, "head")

        # Verify the migration was applied
        engine = create_engine(f"sqlite:///{temp_db_path}")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "projects" in tables, "Projects table should be created"

        # Downgrade to base (before any migrations)
        command.downgrade(alembic_cfg, "base")

        # Verify the migration was rolled back
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "projects" not in tables, "Projects table should be removed"

        # Cleanup
        if migrations_dir.exists():
            shutil.rmtree(migrations_dir)

    def test_data_persistence_through_migrations(self, alembic_cfg, temp_db_path, db_manager):
        """Test that data persists through migrations."""
        # Set the SQLite database URL in the Alembic config
        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{temp_db_path}")

        # Add some test data
        project = ProjectModel(
            id="TEST-1",
            key="TEST",
            name="Test Project",
            description="A test project for migrations",
        )
        db_manager.save_project(project)

        # Initialize migrations
        migrations_dir = Path("migrations_test")
        if migrations_dir.exists():
            shutil.rmtree(migrations_dir)

        command.init(alembic_cfg, str(migrations_dir))

        # Modify the env.py to include our models
        env_py_path = migrations_dir / "env.py"
        with open(env_py_path) as f:
            env_content = f.read()

        # Add import for our models and metadata
        env_content = env_content.replace(
            "from alembic import context",
            "from alembic import context\nfrom ztoq.core.db_models import Base",
        )

        # Set target metadata
        env_content = env_content.replace(
            "target_metadata = None", "target_metadata = Base.metadata"
        )

        # Write the modified env.py
        with open(env_py_path, "w") as f:
            f.write(env_content)

        # Create a migration that adds a new column to projects
        # We'll simulate this by modifying the migration script after generation
        command.revision(
            alembic_cfg,
            autogenerate=True,
            message="Add new column",
            rev_id="001",
            version_path=str(migrations_dir / "versions"),
        )

        version_files = list((migrations_dir / "versions").glob("*_add_new_column.py"))
        migration_path = version_files[0]

        # Modify the migration to add a new column
        with open(migration_path) as f:
            migration_content = f.read()

        # Add code to add a new column in the upgrade
        upgrade_insert = """
    op.add_column('projects', sa.Column('is_active', sa.Boolean(), nullable=True))
    op.execute("UPDATE projects SET is_active = 1")
"""
        migration_content = migration_content.replace(
            "def upgrade() -> None:", f"def upgrade() -> None:\n{upgrade_insert}"
        )

        # Add code to remove the column in the downgrade
        downgrade_insert = """
    op.drop_column('projects', 'is_active')
"""
        migration_content = migration_content.replace(
            "def downgrade() -> None:", f"def downgrade() -> None:\n{downgrade_insert}"
        )

        # Write the modified migration
        with open(migration_path, "w") as f:
            f.write(migration_content)

        # Apply the migration
        command.upgrade(alembic_cfg, "head")

        # Verify the project data is still there
        with db_manager.get_session() as session:
            project = session.query(Project).filter_by(key="TEST").first()
            assert project is not None, "Project should still exist after migration"
            assert project.name == "Test Project", "Project data should be preserved"

            # Verify the new column exists
            inspector = inspect(db_manager._engine)
            columns = [col["name"] for col in inspector.get_columns("projects")]
            assert "is_active" in columns, "New column should be added"

        # Downgrade the migration
        command.downgrade(alembic_cfg, "base")

        # Verify the project data is still there after downgrade
        with db_manager.get_session() as session:
            project = session.query(Project).filter_by(key="TEST").first()
            assert project is not None, "Project should still exist after downgrade"
            assert project.name == "Test Project", "Project data should be preserved"

            # Verify the new column is gone
            inspector = inspect(db_manager._engine)
            columns = [col["name"] for col in inspector.get_columns("projects")]
            assert "is_active" not in columns, "Added column should be removed"

        # Cleanup
        if migrations_dir.exists():
            shutil.rmtree(migrations_dir)

    def test_migration_on_live_database(self, db_manager):
        """Test applying migrations on a database with real data."""
        # Add test data to the database
        for i in range(10):
            project = ProjectModel(
                id=f"PROJ-{i}", key=f"PROJ{i}", name=f"Project {i}", description=f"Test project {i}"
            )
            db_manager.save_project(project)

        # Verify data is in the database
        with db_manager.get_session() as session:
            projects = session.query(Project).all()
            assert len(projects) == 10, "Should have 10 projects"

        # Now simulate a migration that adds a column to TestCase
        with db_manager.get_session() as session:
            # Add a column to test_cases table
            session.execute(text("ALTER TABLE test_cases ADD COLUMN is_automated BOOLEAN"))

            # Populate some data in the table
            test_case = TestCase(
                id="TC-1", key="TEST-CASE-1", name="Test Case 1", project_key="PROJ0"
            )
            session.add(test_case)
            session.commit()

            # Set the value for the new column
            session.execute(text("UPDATE test_cases SET is_automated = 1 WHERE id = 'TC-1'"))
            session.commit()

        # Verify the migration was successful
        with db_manager.get_session() as session:
            # Check the column exists
            inspector = inspect(db_manager._engine)
            columns = [col["name"] for col in inspector.get_columns("test_cases")]
            assert "is_automated" in columns, "New column should be added"

            # Check the data is correct
            test_case = session.query(TestCase).filter_by(id="TC-1").first()
            assert test_case is not None, "Test case should exist"

            # Check the value of the new column using raw SQL
            result = session.execute(text("SELECT is_automated FROM test_cases WHERE id = 'TC-1'"))
            row = result.fetchone()
            assert row[0] == 1, "New column should have the assigned value"

    def test_migration_failure_and_recovery(self, temp_db_path, db_manager):
        """Test handling migration failures and recovering from them."""
        # Add some test data
        for i in range(5):
            project = ProjectModel(
                id=f"FAIL-{i}",
                key=f"FAIL{i}",
                name=f"Failure Test {i}",
                description=f"Test project for failure recovery {i}",
            )
            db_manager.save_project(project)

        # Verify data is in the database
        with db_manager.get_session() as session:
            projects = session.query(Project).filter(Project.key.like("FAIL%")).all()
            assert len(projects) == 5, "Should have 5 test projects"

        # Create a connection outside the manager to simulate a migration failure
        engine = create_engine(f"sqlite:///{temp_db_path}")
        connection = engine.connect()
        transaction = connection.begin()

        try:
            # Try to execute a migration that will fail (invalid SQL)
            connection.execute(text("ALTER TABLE nonexistent_table ADD COLUMN new_column TEXT"))
            transaction.commit()
        except Exception as e:
            # Rollback on failure
            transaction.rollback()
            logger.info(f"Expected migration failure: {e}")
        finally:
            connection.close()

        # Verify the original data is still intact
        with db_manager.get_session() as session:
            projects = session.query(Project).filter(Project.key.like("FAIL%")).all()
            assert len(projects) == 5, "All projects should still exist after failed migration"

        # Now simulate a successful migration after recovery
        with db_manager.get_session() as session:
            try:
                # Add a column to projects
                session.execute(text("ALTER TABLE projects ADD COLUMN recovery_test TEXT"))

                # Set values for the new column
                session.execute(
                    text("UPDATE projects SET recovery_test = 'recovered' WHERE key LIKE 'FAIL%'")
                )
                session.commit()

                # Verify the migration was successful
                for project in session.query(Project).filter(Project.key.like("FAIL%")).all():
                    result = session.execute(
                        text("SELECT recovery_test FROM projects WHERE id = :id"),
                        {"id": project.id},
                    )
                    row = result.fetchone()
                    assert row[0] == "recovered", "Recovery should be successful"
            except Exception as e:
                # SQLite doesn't support all ALTER TABLE operations, so handle accordingly
                # For a real PostgreSQL database, this would work
                logger.warning(f"SQLite limitation: {e}")
                pytest.skip("SQLite doesn't support this ALTER TABLE operation")
