"""rename asset_name to trading_view_symbol and populate hyperliquid_symbol

Revision ID: 9a8b7c6d5e4f
Revises: 584fd16da70d
Create Date: 2025-08-01 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9a8b7c6d5e4f'
down_revision: Union[str, Sequence[str], None] = '8c056592a587'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Copy asset_name values to hyperliquid_symbol
    op.execute("UPDATE webhook_config SET hyperliquid_symbol = asset_name WHERE hyperliquid_symbol IS NULL")
    
    # Rename asset_name column to trading_view_symbol
    op.alter_column('webhook_config', 'asset_name', new_column_name='trading_view_symbol')


def downgrade() -> None:
    """Downgrade schema."""
    # Rename trading_view_symbol back to asset_name
    op.alter_column('webhook_config', 'trading_view_symbol', new_column_name='asset_name')
    
    # Clear hyperliquid_symbol values
    op.execute("UPDATE webhook_config SET hyperliquid_symbol = NULL")