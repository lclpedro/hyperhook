"""add hyperliquid_symbol to webhook_configs

Revision ID: 8c056592a587
Revises: 60af4bcf54fa
Create Date: 2025-07-19 14:42:29.352021

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c056592a587'
down_revision: Union[str, Sequence[str], None] = '60af4bcf54fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('webhook_config', sa.Column('hyperliquid_symbol', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('webhook_config', 'hyperliquid_symbol')
