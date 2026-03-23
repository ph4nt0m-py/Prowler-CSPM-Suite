"""scan cancelled status and celery_task_id

Revision ID: 002
Revises: 001
Create Date: 2026-03-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safe on Postgres versions without ADD VALUE IF NOT EXISTS for enums
    op.execute(
        """
        DO $$ BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_enum e
            JOIN pg_type t ON e.enumtypid = t.oid
            WHERE t.typname = 'scan_status' AND e.enumlabel = 'cancelled'
          ) THEN
            ALTER TYPE scan_status ADD VALUE 'cancelled';
          END IF;
        END $$;
        """
    )
    op.add_column("scans", sa.Column("celery_task_id", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("scans", "celery_task_id")
    # PostgreSQL cannot remove enum values easily; leave 'cancelled' in type.
