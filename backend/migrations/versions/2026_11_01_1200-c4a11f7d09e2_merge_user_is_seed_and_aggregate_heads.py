"""merge user_is_seed and aggregate migration heads

Revision ID: c4a11f7d09e2
Revises: f7b9d1e35a6c, 9ffc050235bd

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "c4a11f7d09e2"
down_revision: Union[str, Sequence[str], None] = ("f7b9d1e35a6c", "9ffc050235bd")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
