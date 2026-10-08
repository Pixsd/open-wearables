"""merge meal_details and existing heads

Revision ID: d5f7b9c13e4a
Revises: 4b9d28928ca1, c4e6a8b02d3f

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "d5f7b9c13e4a"
down_revision: Union[str, Sequence[str], None] = ("4b9d28928ca1", "c4e6a8b02d3f")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
