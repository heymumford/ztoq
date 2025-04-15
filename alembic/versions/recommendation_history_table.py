"""add recommendation history table

Revision ID: 2af75c826b91
Revises: a16c4721be8a
Create Date: 2025-04-15 14:42:11.345912

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2af75c826b91"
down_revision: str | None = "a16c4721be8a"
branch_labels: str | (Sequence[str] | None) = None
depends_on: str | (Sequence[str] | None) = None


def upgrade() -> None:
    # Create recommendation_history table for tracking recommendation trends
    op.create_table(
        "recommendation_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_key", sa.String(50), nullable=False, index=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False, index=True),
        sa.Column("recommendation_id", sa.String(50), nullable=False, index=True),
        sa.Column("priority", sa.String(10), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("issue", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("implemented_at", sa.DateTime(), nullable=True),
        sa.Column("impact_score", sa.Float(), nullable=True),
        sa.Column("migration_phase", sa.String(20), nullable=True),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("meta_data", JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for frequent query patterns
    op.create_index(
        "ix_recommendation_history_project_timestamp",
        "recommendation_history",
        ["project_key", "timestamp"],
    )
    op.create_index(
        "ix_recommendation_history_priority",
        "recommendation_history",
        ["priority"],
    )
    op.create_index(
        "ix_recommendation_history_status",
        "recommendation_history",
        ["status"],
    )

    # Make recommendation_id unique within a project
    op.create_index(
        "ix_recommendation_history_project_rec_id",
        "recommendation_history",
        ["project_key", "recommendation_id"],
        unique=True,
    )


def downgrade() -> None:
    # Remove all indexes
    op.drop_index("ix_recommendation_history_project_timestamp", "recommendation_history")
    op.drop_index("ix_recommendation_history_priority", "recommendation_history")
    op.drop_index("ix_recommendation_history_status", "recommendation_history")
    op.drop_index("ix_recommendation_history_project_rec_id", "recommendation_history")

    # Drop the table
    op.drop_table("recommendation_history")
