"""merge upstream data_migration head and existing heads

Revision ID: e6a8c0d24f5b
Revises: b679f6226f99, d5f7b9c13e4a

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "e6a8c0d24f5b"
down_revision: Union[str, Sequence[str], None] = ("b679f6226f99", "d5f7b9c13e4a")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
