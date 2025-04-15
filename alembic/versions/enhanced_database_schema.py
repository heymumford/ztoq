"""enhance database schema with additional features

Revision ID: 3da7f9236c51
Revises: 2af75c826b91
Create Date: 2025-04-15 15:30:12.345678

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3da7f9236c51"
down_revision: str | None = "2af75c826b91"
branch_labels: str | (Sequence[str] | None) = None
depends_on: str | (Sequence[str] | None) = None


def upgrade() -> None:
    # Enhanced indexing for migration performance
    op.create_index(
        "idx_test_case_created_on",
        "test_cases",
        ["created_on"],
        unique=False,
    )
    op.create_index(
        "idx_test_case_updated_on",
        "test_cases",
        ["updated_on"],
        unique=False,
    )
    op.create_index(
        "idx_test_execution_executed_on",
        "test_executions",
        ["executed_on"],
        unique=False,
    )

    # Create performance stats table
    op.create_table(
        "migration_performance_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_key", sa.String(50), nullable=False, index=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False, index=True),
        sa.Column("phase", sa.String(20), nullable=False),  # extraction, transformation, loading
        sa.Column("operation", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_count", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=True),
        sa.Column("error_count", sa.Integer(), nullable=True),
        sa.Column("batch_size", sa.Integer(), nullable=True),
        sa.Column("cpu_percent", sa.Float(), nullable=True),
        sa.Column("memory_mb", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("meta_data", postgresql.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for performance stats queries
    op.create_index(
        "idx_perf_stats_project_phase",
        "migration_performance_stats",
        ["project_key", "phase"],
    )
    op.create_index(
        "idx_perf_stats_operation",
        "migration_performance_stats",
        ["operation"],
    )

    # Create migration checkpoint table for resume capability
    op.create_table(
        "migration_checkpoints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_key", sa.String(50), nullable=False, index=True),
        sa.Column("checkpoint_id", sa.String(50), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("phase", sa.String(20), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("last_processed_id", sa.String(50), nullable=True),
        sa.Column("processed_count", sa.Integer(), nullable=True),
        sa.Column("total_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("checkpoint_data", postgresql.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create unique index on checkpoint_id
    op.create_index(
        "idx_checkpoint_id_unique",
        "migration_checkpoints",
        ["checkpoint_id"],
        unique=True,
    )

    # Create index for checkpoint lookup by project and phase
    op.create_index(
        "idx_checkpoint_project_phase",
        "migration_checkpoints",
        ["project_key", "phase"],
    )


def downgrade() -> None:
    # Drop migration checkpoint table and indexes
    op.drop_index("idx_checkpoint_project_phase", table_name="migration_checkpoints")
    op.drop_index("idx_checkpoint_id_unique", table_name="migration_checkpoints")
    op.drop_table("migration_checkpoints")

    # Drop performance stats table and indexes
    op.drop_index("idx_perf_stats_operation", table_name="migration_performance_stats")
    op.drop_index("idx_perf_stats_project_phase", table_name="migration_performance_stats")
    op.drop_table("migration_performance_stats")

    # Remove enhanced indexes
    op.drop_index("idx_test_execution_executed_on", table_name="test_executions")
    op.drop_index("idx_test_case_updated_on", table_name="test_cases")
    op.drop_index("idx_test_case_created_on", table_name="test_cases")
