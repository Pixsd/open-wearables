"""merge telemetry_state and mcp_client heads

Revision ID: b3d5f7a91c2e
Revises: ef6ff24def41, 8f2c4a91d6e7

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "b3d5f7a91c2e"
down_revision: Union[str, Sequence[str], None] = ("ef6ff24def41", "8f2c4a91d6e7")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
