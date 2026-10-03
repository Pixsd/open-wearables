"""merge extended_device_types and mcp/telemetry merge heads

Revision ID: c4e6a8b02d3f
Revises: a18e054b6e0f, b3d5f7a91c2e

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "c4e6a8b02d3f"
down_revision: Union[str, Sequence[str], None] = ("a18e054b6e0f", "b3d5f7a91c2e")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
