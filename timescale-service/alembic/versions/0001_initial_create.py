"""InitialCreate — таблицы Values и Results (аналог 20250802195334_InitialCreate.cs)

Revision ID: 0001
Revises:
Create Date: 2025-08-02
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "Results",
        sa.Column("Id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("FileName", sa.Text(), nullable=False),
        sa.Column("TimeDeltaSec", sa.Double(), nullable=False),
        sa.Column("StartDate", sa.DateTime(timezone=True), nullable=False),
        sa.Column("AvgExecutionTime", sa.Double(), nullable=False),
        sa.Column("AvgValue", sa.Double(), nullable=False),
        sa.Column("MedianValue", sa.Double(), nullable=False),
        sa.Column("MaxValue", sa.Double(), nullable=False),
        sa.Column("MinValue", sa.Double(), nullable=False),
        sa.PrimaryKeyConstraint("Id", name="PK_Results"),
    )
    op.create_table(
        "Values",
        sa.Column("Id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("Date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ExecutionTime", sa.Double(), nullable=False),
        sa.Column("Value", sa.Double(), nullable=False),
        sa.Column("FileName", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("Id", name="PK_Values"),
    )


def downgrade() -> None:
    op.drop_table("Values")
    op.drop_table("Results")
