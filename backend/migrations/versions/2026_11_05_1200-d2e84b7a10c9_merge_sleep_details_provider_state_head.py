"""merge sleep details provider state head

Revision ID: d2e84b7a10c9
Revises: a8d3f2b61c47, 3f6b9c2d8e41

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "d2e84b7a10c9"
down_revision: Union[str, Sequence[str], None] = ("a8d3f2b61c47", "3f6b9c2d8e41")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
