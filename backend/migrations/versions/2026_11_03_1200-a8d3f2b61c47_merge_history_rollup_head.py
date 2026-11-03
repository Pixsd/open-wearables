"""merge history rollup head

Revision ID: a8d3f2b61c47
Revises: c4a11f7d09e2, e9413ac05e3b

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "a8d3f2b61c47"
down_revision: Union[str, Sequence[str], None] = ("c4a11f7d09e2", "e9413ac05e3b")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
