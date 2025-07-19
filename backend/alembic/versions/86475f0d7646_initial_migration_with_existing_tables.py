"""Initial migration with existing tables

Revision ID: 86475f0d7646
Revises: 
Create Date: 2025-07-17 21:55:07.591792

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '86475f0d7646'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=256), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('webhook_secret', sa.String(length=36), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('webhook_secret')
    )
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)
    op.create_index(op.f('ix_user_id'), 'user', ['id'], unique=False)
    
    op.create_table('wallet',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('encrypted_secret_key', sa.String(length=512), nullable=True),
        sa.Column('public_address', sa.String(length=42), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('public_address')
    )
    op.create_index(op.f('ix_wallet_id'), 'wallet', ['id'], unique=False)
    
    op.create_table('webhook_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('asset_name', sa.String(length=20), nullable=False),
        sa.Column('max_usd_value', sa.Float(), nullable=False),
        sa.Column('leverage', sa.Integer(), nullable=False),
        sa.Column('is_live_trading', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhook_config_id'), 'webhook_config', ['id'], unique=False)
    
    op.create_table('webhook_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('webhook_config_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('request_method', sa.String(length=10), nullable=False),
        sa.Column('request_url', sa.String(length=255), nullable=False),
        sa.Column('request_headers', sa.Text(), nullable=False),
        sa.Column('request_body', sa.Text(), nullable=False),
        sa.Column('response_status', sa.Integer(), nullable=False),
        sa.Column('response_headers', sa.Text(), nullable=False),
        sa.Column('response_body', sa.Text(), nullable=False),
        sa.Column('is_success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['webhook_config_id'], ['webhook_config.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhook_log_id'), 'webhook_log', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_webhook_log_id'), table_name='webhook_log')
    op.drop_table('webhook_log')
    op.drop_index(op.f('ix_webhook_config_id'), table_name='webhook_config')
    op.drop_table('webhook_config')
    op.drop_index(op.f('ix_wallet_id'), table_name='wallet')
    op.drop_table('wallet')
    op.drop_index(op.f('ix_user_id'), table_name='user')
    op.drop_index(op.f('ix_user_email'), table_name='user')
    op.drop_table('user')
