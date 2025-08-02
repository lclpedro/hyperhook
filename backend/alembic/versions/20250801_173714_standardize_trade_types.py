"""Standardize trade types from Portuguese to English

Revision ID: 20250801_173714
Revises: 
Create Date: 2025-08-01 17:37:14.795961

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250801_173714'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create backup table
    op.execute("""
        CREATE TABLE IF NOT EXISTS webhook_trades_backup AS 
        SELECT * FROM webhook_trades WHERE 1=0
    """)
    
    # Insert current data into backup
    op.execute("""
        INSERT INTO webhook_trades_backup 
        SELECT * FROM webhook_trades
    """)
    
    # Update FECHAMENTO to CLOSE
    op.execute("""
        UPDATE webhook_trades 
        SET trade_type = 'CLOSE' 
        WHERE trade_type = 'FECHAMENTO'
    """)
    
    # Update REDUCAO to REDUCE
    op.execute("""
        UPDATE webhook_trades 
        SET trade_type = 'REDUCE' 
        WHERE trade_type = 'REDUCAO'
    """)
    
    # Update NOVA_POSICAO to BUY for LONG positions
    op.execute("""
        UPDATE webhook_trades 
        SET trade_type = 'BUY' 
        WHERE trade_type = 'NOVA_POSICAO' AND side = 'LONG'
    """)
    
    # Update NOVA_POSICAO to SELL for SHORT positions
    op.execute("""
        UPDATE webhook_trades 
        SET trade_type = 'SELL' 
        WHERE trade_type = 'NOVA_POSICAO' AND side = 'SHORT'
    """)
    
    # Update remaining NOVA_POSICAO to BUY (default)
    op.execute("""
        UPDATE webhook_trades 
        SET trade_type = 'BUY' 
        WHERE trade_type = 'NOVA_POSICAO' AND (side IS NULL OR side = '')
    """)
    
    # Update any remaining NOVA_ENTRADA to BUY
    op.execute("""
        UPDATE webhook_trades 
        SET trade_type = 'BUY' 
        WHERE trade_type = 'NOVA_ENTRADA'
    """)


def downgrade():
    # Restore from backup if needed
    op.execute("""
        DELETE FROM webhook_trades
    """)
    
    op.execute("""
        INSERT INTO webhook_trades 
        SELECT * FROM webhook_trades_backup
    """)
    
    # Drop backup table
    op.execute("""
        DROP TABLE IF EXISTS webhook_trades_backup
    """)
