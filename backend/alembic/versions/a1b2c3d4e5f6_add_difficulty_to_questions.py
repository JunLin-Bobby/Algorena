"""add difficulty to questions

Revision ID: a1b2c3d4e5f6
Revises: db36be828cbe
Create Date: 2026-06-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "db36be828cbe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite cannot ALTER COLUMN to drop server_default; keep default for safety.
    op.add_column(
        "questions",
        sa.Column("difficulty", sa.Text(), nullable=False, server_default="easy"),
    )


def downgrade() -> None:
    op.drop_column("questions", "difficulty")
