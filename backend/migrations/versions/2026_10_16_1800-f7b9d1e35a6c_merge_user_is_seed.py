"""merge user_is_seed and existing heads

Revision ID: f7b9d1e35a6c
Revises: c4e7a1d93b52, e6a8c0d24f5b

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "f7b9d1e35a6c"
down_revision: Union[str, Sequence[str], None] = ("c4e7a1d93b52", "e6a8c0d24f5b")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
