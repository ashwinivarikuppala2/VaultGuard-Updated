"""Add the quarantined state to the device status enum."""
from typing import Sequence, Union

from alembic import op


revision: str = "0005_device_status_quarantined"
down_revision: Union[str, None] = "0004_recovery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE device_status_enum ADD VALUE IF NOT EXISTS 'QUARANTINED'")


def downgrade() -> None:
    pass