"""backfill workout_details entry_source/intensity/label columns

Revision 9b079dab9585 was already applied against some databases before its
upgrade() gained the entry_source/intensity/label columns, so alembic never
re-runs it there. This migration adds them if missing, idempotently, without
touching databases where 9b079dab9585 already added them.

Revision ID: 345eab28c819
Revises: a7c3e9f1b2d4

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "345eab28c819"
down_revision: Union[str, None] = "a7c3e9f1b2d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE workout_details ADD COLUMN IF NOT EXISTS entry_source VARCHAR(32)")
    op.execute("ALTER TABLE workout_details ADD COLUMN IF NOT EXISTS intensity VARCHAR(10)")
    op.execute("ALTER TABLE workout_details ADD COLUMN IF NOT EXISTS label VARCHAR(255)")


def downgrade() -> None:
    pass
