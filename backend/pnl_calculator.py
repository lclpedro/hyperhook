# --- pnl_calculator.py ---
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, timezone
from typing import Optional, Dict, List
from app import (
    WebhookTrade, WebhookPosition, WebhookPnlSummary, 
    User, WebhookConfig
)
from hyperliquid_client import HyperliquidClient

class PnlCalculator:
    def __init__(self, db: Session):
        self.db = db
    
    def record_trade(
        self,
        webhook_config_id: int,
        user_id: int,
        asset_name: str,
        trade_type: str,  # BUY, SELL, CLOSE, DCA, REDUCE
        side: str,        # LONG, SHORT
        quantity: float,
        price: float,
        usd_value: float,
        leverage: int,
        order_id: Optional[str] = None,
        fees: float = 0.0
    ) -> WebhookTrade:
        """Registra um novo trade e atualiza posições e PNL"""
        
        # Criar registro do trade
        trade = WebhookTrade(
            webhook_config_id=webhook_config_id,
            user_id=user_id,
            asset_name=asset_name,
            trade_type=trade_type,
            side=side,
            quantity=quantity,
            price=price,
            usd_value=usd_value,
            leverage=leverage,
            order_id=order_id,
            fees=fees,
            timestamp=datetime.now(timezone.utc)
        )
        
        self.db.add(trade)
        self.db.commit()
        
        # Atualizar posição
        self._update_position(trade)
        
        # Atualizar resumo PNL
        self._update_pnl_summary(user_id, asset_name)
        
        return trade
    
    def _update_position(self, trade: WebhookTrade):
        """Atualiza a posição baseada no trade"""
        
        # Buscar posição existente
        position = self.db.query(WebhookPosition).filter(
            and_(
                WebhookPosition.webhook_config_id == trade.webhook_config_id,
                WebhookPosition.asset_name == trade.asset_name,
                WebhookPosition.is_open == True
            )
        ).first()
        
        if trade.trade_type == "CLOSE" or trade.trade_type == "FECHAMENTO":
            # Fechar posição existente
            if position:
                position.is_open = False
                position.closed_at = trade.timestamp
                position.realized_pnl = self._calculate_realized_pnl(
                    position.quantity, position.avg_entry_price, 
                    trade.quantity, trade.price, position.side
                )
                position.total_fees += trade.fees
                self.db.commit()
        
        elif trade.trade_type in ["BUY", "SELL"]:
            # Nova posição
            if not position:
                position = WebhookPosition(
                    webhook_config_id=trade.webhook_config_id,
                    user_id=trade.user_id,
                    asset_name=trade.asset_name,
                    side=trade.side,
                    quantity=trade.quantity,
                    avg_entry_price=trade.price,
                    leverage=trade.leverage,
                    total_fees=trade.fees,
                    opened_at=trade.timestamp,
                    last_updated=trade.timestamp
                )
                self.db.add(position)
            else:
                # Atualizar posição existente (DCA)
                self._update_position_dca(position, trade)
        
        elif trade.trade_type == "DCA":
            # Dollar Cost Average - aumentar posição
            if position:
                self._update_position_dca(position, trade)
            else:
                # Se não há posição, criar nova (DCA pode ser entrada inicial)
                position = WebhookPosition(
                    webhook_config_id=trade.webhook_config_id,
                    user_id=trade.user_id,
                    asset_name=trade.asset_name,
                    side=trade.side,
                    quantity=trade.quantity,
                    avg_entry_price=trade.price,
                    leverage=trade.leverage,
                    total_fees=trade.fees,
                    opened_at=trade.timestamp,
                    last_updated=trade.timestamp
                )
                self.db.add(position)
        
        elif trade.trade_type == "REDUCE" or trade.trade_type == "REDUCAO":
            # Reduzir posição
            if position:
                self._reduce_position(position, trade)
            else:
                # Se não há posição para reduzir, tratar como fechamento de posição implícita
                # Criar uma posição temporária para calcular o PNL
                position = WebhookPosition(
                    webhook_config_id=trade.webhook_config_id,
                    user_id=trade.user_id,
                    asset_name=trade.asset_name,
                    side=trade.side,
                    quantity=trade.quantity,
                    avg_entry_price=trade.price,  # Assumir preço atual como base
                    leverage=trade.leverage,
                    total_fees=trade.fees,
                    realized_pnl=0.0,  # Sem PNL se não há histórico
                    is_open=False,  # Já fechada
                    opened_at=trade.timestamp,
                    closed_at=trade.timestamp,
                    last_updated=trade.timestamp
                )
                self.db.add(position)
        
        self.db.commit()
    
    def _update_position_dca(self, position: WebhookPosition, trade: WebhookTrade):
        """Atualiza posição com DCA (Dollar Cost Average)"""
        
        # Calcular novo preço médio
        total_value_old = position.quantity * position.avg_entry_price
        total_value_new = trade.quantity * trade.price
        new_quantity = position.quantity + trade.quantity
        
        if new_quantity > 0:
            position.avg_entry_price = (total_value_old + total_value_new) / new_quantity
            position.quantity = new_quantity
        
        position.total_fees += trade.fees
        position.last_updated = trade.timestamp
    
    def _reduce_position(self, position: WebhookPosition, trade: WebhookTrade):
        """Reduz uma posição existente"""
        
        # Calcular PNL realizado da parte fechada
        realized_pnl = self._calculate_realized_pnl(
            trade.quantity, position.avg_entry_price,
            trade.quantity, trade.price, position.side
        )
        
        position.realized_pnl += realized_pnl
        position.quantity -= trade.quantity
        position.total_fees += trade.fees
        position.last_updated = trade.timestamp
        
        # Se quantidade chegou a zero, fechar posição
        if position.quantity <= 0:
            position.is_open = False
            position.closed_at = trade.timestamp
    
    def _calculate_realized_pnl(
        self, 
        quantity: float, 
        entry_price: float, 
        exit_quantity: float, 
        exit_price: float, 
        side: str
    ) -> float:
        """Calcula PNL realizado"""
        
        if side == "LONG":
            return exit_quantity * (exit_price - entry_price)
        else:  # SHORT
            return exit_quantity * (entry_price - exit_price)
    
    def _update_pnl_summary(self, user_id: int, asset_name: str):
        """Atualiza o resumo de PNL para um ativo"""
        
        # Buscar ou criar resumo
        summary = self.db.query(WebhookPnlSummary).filter(
            and_(
                WebhookPnlSummary.user_id == user_id,
                WebhookPnlSummary.asset_name == asset_name
            )
        ).first()
        
        if not summary:
            summary = WebhookPnlSummary(
                user_id=user_id,
                asset_name=asset_name
            )
            self.db.add(summary)
        
        # Calcular estatísticas dos trades
        trades = self.db.query(WebhookTrade).filter(
            and_(
                WebhookTrade.user_id == user_id,
                WebhookTrade.asset_name == asset_name
            )
        ).all()
        
        # Calcular PNL das posições
        positions = self.db.query(WebhookPosition).filter(
            and_(
                WebhookPosition.user_id == user_id,
                WebhookPosition.asset_name == asset_name
            )
        ).all()
        
        # Estatísticas básicas
        summary.total_trades = len(trades)
        summary.total_realized_pnl = sum(p.realized_pnl for p in positions)
        summary.total_unrealized_pnl = sum(p.unrealized_pnl for p in positions if p.is_open)
        summary.total_fees = sum(t.fees for t in trades)
        summary.total_volume = sum(t.usd_value for t in trades)
        
        # Calcular trades vencedores e perdedores
        closed_positions = [p for p in positions if not p.is_open]
        winning_positions = [p for p in closed_positions if p.realized_pnl > 0]
        losing_positions = [p for p in closed_positions if p.realized_pnl < 0]
        
        summary.winning_trades = len(winning_positions)
        summary.losing_trades = len(losing_positions)
        
        # Calcular métricas
        if summary.total_trades > 0:
            summary.win_rate = (summary.winning_trades / len(closed_positions)) * 100 if closed_positions else 0
        
        if winning_positions:
            summary.avg_win = sum(p.realized_pnl for p in winning_positions) / len(winning_positions)
            summary.largest_win = max(p.realized_pnl for p in winning_positions)
        
        if losing_positions:
            summary.avg_loss = sum(p.realized_pnl for p in losing_positions) / len(losing_positions)
            summary.largest_loss = min(p.realized_pnl for p in losing_positions)
        
        # PNL líquido
        summary.net_pnl = summary.total_realized_pnl + summary.total_unrealized_pnl - summary.total_fees
        summary.last_updated = datetime.now(timezone.utc)
        
        self.db.commit()
    
    def update_unrealized_pnl(self, user_id: int, client: HyperliquidClient):
        """Atualiza PNL não realizado de todas as posições abertas"""
        
        open_positions = self.db.query(WebhookPosition).filter(
            and_(
                WebhookPosition.user_id == user_id,
                WebhookPosition.is_open == True
            )
        ).all()
        
        for position in open_positions:
            try:
                # Obter preço atual
                current_price = client.get_asset_price(position.asset_name)
                if current_price:
                    position.current_price = current_price
                    
                    # Calcular PNL não realizado
                    if position.side == "LONG":
                        position.unrealized_pnl = position.quantity * (current_price - position.avg_entry_price)
                    else:  # SHORT
                        position.unrealized_pnl = position.quantity * (position.avg_entry_price - current_price)
                    
                    position.last_updated = datetime.now(timezone.utc)
            
            except Exception as e:
                print(f"Erro ao atualizar preço para {position.asset_name}: {e}")
        
        self.db.commit()
        
        # Atualizar resumos PNL
        assets = set(p.asset_name for p in open_positions)
        for asset in assets:
            self._update_pnl_summary(user_id, asset)
    
    def get_pnl_by_period(
        self, 
        user_id: int, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict:
        """Obtém PNL por período"""
        
        trades = self.db.query(WebhookTrade).filter(
            and_(
                WebhookTrade.user_id == user_id,
                WebhookTrade.timestamp >= start_date,
                WebhookTrade.timestamp <= end_date
            )
        ).all()
        
        positions_closed = self.db.query(WebhookPosition).filter(
            and_(
                WebhookPosition.user_id == user_id,
                WebhookPosition.closed_at >= start_date,
                WebhookPosition.closed_at <= end_date,
                WebhookPosition.is_open == False
            )
        ).all()
        
        total_realized_pnl = sum(p.realized_pnl for p in positions_closed)
        total_fees = sum(t.fees for t in trades)
        total_trades = len(trades)
        
        return {
            "period_pnl": total_realized_pnl - total_fees,
            "period_trades": total_trades,
            "total_fees": total_fees,
            "realized_pnl": total_realized_pnl
        }
    
    def get_assets_pnl_summary(self, user_id: int) -> List[WebhookPnlSummary]:
        """Obtém resumo de PNL por ativo"""
        
        return self.db.query(WebhookPnlSummary).filter(
            WebhookPnlSummary.user_id == user_id
        ).all()