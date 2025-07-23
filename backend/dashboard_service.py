# --- dashboard_service.py ---
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from app import (
    WebhookTrade, WebhookPosition, WebhookPnlSummary, 
    AccountSnapshot, User, WebhookConfig
)
from pnl_calculator import PnlCalculator
from hyperliquid_client import HyperliquidClient

class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.pnl_calculator = PnlCalculator(db)
    
    def get_dashboard_summary(self, user_id: int, period: str = "7d") -> Dict:
        """Obtém resumo completo do dashboard"""
        
        # Snapshot da conta mais recente
        latest_snapshot = self.db.query(AccountSnapshot).filter(
            AccountSnapshot.user_id == user_id
        ).order_by(desc(AccountSnapshot.timestamp)).first()
        
        # Se não há snapshot, criar um padrão
        if not latest_snapshot:
            account_balance = {
                "id": 0,
                "total_balance": 0.0,
                "available_balance": 0.0,
                "used_margin": 0.0,
                "total_unrealized_pnl": 0.0,
                "total_positions_value": 0.0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            account_balance = {
                "id": latest_snapshot.id,
                "total_balance": latest_snapshot.total_balance,
                "available_balance": latest_snapshot.available_balance,
                "used_margin": latest_snapshot.used_margin,
                "total_unrealized_pnl": latest_snapshot.total_unrealized_pnl,
                "total_positions_value": latest_snapshot.total_positions_value,
                "timestamp": latest_snapshot.timestamp.isoformat()
            }
        
        # PNL do período baseado no parâmetro
        today = datetime.now(timezone.utc).date()
        days_map = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}
        days = days_map.get(period, 7)
        period_start = today - timedelta(days=days)
        period_pnl_data = self._get_period_pnl(user_id, period_start, today)
        period_pnl = period_pnl_data.get("period_pnl", 0.0)
        
        # Trades do período
        period_trades = period_pnl_data.get("period_trades", 0)
        
        # Performance por ativo
        assets_pnl = self.get_assets_performance(user_id)
        
        # Converter para formato WebhookPnlSummaryResponse
        assets_pnl_formatted = []
        for asset in assets_pnl:
            assets_pnl_formatted.append({
                "id": 0,  # Placeholder
                "asset_name": asset["asset_name"],
                "total_trades": asset["total_trades"],
                "winning_trades": asset["winning_trades"],
                "losing_trades": asset["losing_trades"],
                "total_realized_pnl": asset["realized_pnl"],
                "total_unrealized_pnl": asset["unrealized_pnl"],
                "total_fees": asset["total_fees"],
                "net_pnl": asset["net_pnl"],
                "win_rate": asset["win_rate"],
                "avg_win": asset["avg_win"],
                "avg_loss": asset["avg_loss"],
                "largest_win": asset["largest_win"],
                "largest_loss": asset["largest_loss"],
                "total_volume": asset["total_volume"],
                "last_updated": asset["last_updated"]
            })
        
        return {
            "account_balance": account_balance,
            "period_pnl": period_pnl,
            "period_trades": period_trades,
            "assets_pnl": assets_pnl_formatted
        }
    
    def get_assets_performance(self, user_id: int, period: str = "7d") -> List[Dict]:
        """Obtém performance por ativo"""
        
        pnl_summaries = self.db.query(WebhookPnlSummary).filter(
            WebhookPnlSummary.user_id == user_id
        ).all()
        
        assets_data = []
        for summary in pnl_summaries:
            # Posição atual
            current_position = self.db.query(WebhookPosition).filter(
                and_(
                    WebhookPosition.user_id == user_id,
                    WebhookPosition.asset_name == summary.asset_name,
                    WebhookPosition.is_open == True
                )
            ).first()
            
            assets_data.append({
                "asset_name": summary.asset_name,
                "total_trades": summary.total_trades,
                "realized_pnl": summary.total_realized_pnl,
                "unrealized_pnl": summary.total_unrealized_pnl,
                "net_pnl": summary.net_pnl,
                "total_fees": summary.total_fees,
                "win_rate": summary.win_rate,
                "winning_trades": summary.winning_trades,
                "losing_trades": summary.losing_trades,
                "avg_win": summary.avg_win,
                "avg_loss": summary.avg_loss,
                "largest_win": summary.largest_win,
                "largest_loss": summary.largest_loss,
                "total_volume": summary.total_volume,
                "has_open_position": current_position is not None,
                "current_position": {
                    "side": current_position.side if current_position else None,
                    "quantity": current_position.quantity if current_position else 0,
                    "avg_entry_price": current_position.avg_entry_price if current_position else 0,
                    "current_price": current_position.current_price if current_position else 0,
                    "unrealized_pnl": current_position.unrealized_pnl if current_position else 0
                } if current_position else None,
                "last_updated": summary.last_updated.isoformat() if summary.last_updated else None
            })
        
        # Ordenar por PNL líquido (maior para menor)
        assets_data.sort(key=lambda x: x["net_pnl"], reverse=True)
        
        return assets_data
    
    def get_asset_detailed_performance(
        self, 
        user_id: int, 
        asset_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Obtém performance detalhada de um ativo específico"""
        
        # Filtros de data
        trade_filters = [WebhookTrade.user_id == user_id, WebhookTrade.asset_name == asset_name]
        position_filters = [WebhookPosition.user_id == user_id, WebhookPosition.asset_name == asset_name]
        
        if start_date:
            trade_filters.append(WebhookTrade.timestamp >= start_date)
            position_filters.append(WebhookPosition.opened_at >= start_date)
        
        if end_date:
            trade_filters.append(WebhookTrade.timestamp <= end_date)
            position_filters.append(WebhookPosition.opened_at <= end_date)
        
        # Trades do ativo
        trades = self.db.query(WebhookTrade).filter(
            and_(*trade_filters)
        ).order_by(desc(WebhookTrade.timestamp)).all()
        
        # Posições do ativo
        positions = self.db.query(WebhookPosition).filter(
            and_(*position_filters)
        ).order_by(desc(WebhookPosition.opened_at)).all()
        
        # Resumo PNL
        pnl_summary = self.db.query(WebhookPnlSummary).filter(
            and_(
                WebhookPnlSummary.user_id == user_id,
                WebhookPnlSummary.asset_name == asset_name
            )
        ).first()
        
        # Posição atual
        current_position = self.db.query(WebhookPosition).filter(
            and_(
                WebhookPosition.user_id == user_id,
                WebhookPosition.asset_name == asset_name,
                WebhookPosition.is_open == True
            )
        ).first()
        
        # Histórico de preços (simulado - seria obtido de API externa)
        price_history = self._get_price_history(asset_name, start_date, end_date)
        
        return {
            "asset_name": asset_name,
            "total_trades": len(trades),
            "winning_trades": pnl_summary.winning_trades if pnl_summary else 0,
            "losing_trades": pnl_summary.losing_trades if pnl_summary else 0,
            "total_realized_pnl": pnl_summary.total_realized_pnl if pnl_summary else 0,
            "total_unrealized_pnl": pnl_summary.total_unrealized_pnl if pnl_summary else 0,
            "total_pnl": pnl_summary.net_pnl if pnl_summary else 0,
            "net_pnl": pnl_summary.net_pnl if pnl_summary else 0,
            "total_fees": pnl_summary.total_fees if pnl_summary else 0,
            "win_rate": pnl_summary.win_rate if pnl_summary else 0,
            "total_volume": pnl_summary.total_volume if pnl_summary else 0,
            "summary": {
                "total_trades": len(trades),
                "realized_pnl": pnl_summary.total_realized_pnl if pnl_summary else 0,
                "unrealized_pnl": pnl_summary.total_unrealized_pnl if pnl_summary else 0,
                "net_pnl": pnl_summary.net_pnl if pnl_summary else 0,
                "total_fees": pnl_summary.total_fees if pnl_summary else 0,
                "win_rate": pnl_summary.win_rate if pnl_summary else 0,
                "total_volume": pnl_summary.total_volume if pnl_summary else 0
            },
            "current_position": {
                "side": current_position.side if current_position else None,
                "quantity": current_position.quantity if current_position else 0,
                "avg_entry_price": current_position.avg_entry_price if current_position else 0,
                "current_price": current_position.current_price if current_position else 0,
                "unrealized_pnl": current_position.unrealized_pnl if current_position else 0,
                "leverage": current_position.leverage if current_position else 1,
                "opened_at": current_position.opened_at.isoformat() if current_position and current_position.opened_at else None
            } if current_position else None,
            "trades": [
                {
                    "id": trade.id,
                    "trade_type": trade.trade_type,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "usd_value": trade.usd_value,
                    "leverage": trade.leverage,
                    "fees": trade.fees,
                    "timestamp": trade.timestamp.isoformat() if trade.timestamp else None
                }
                for trade in trades
            ],
            "positions_history": [
                {
                    "id": pos.id,
                    "side": pos.side,
                    "quantity": pos.quantity,
                    "avg_entry_price": pos.avg_entry_price,
                    "leverage": pos.leverage,
                    "realized_pnl": pos.realized_pnl,
                    "unrealized_pnl": pos.unrealized_pnl,
                    "total_fees": pos.total_fees,
                    "is_open": pos.is_open,
                    "opened_at": pos.opened_at.isoformat() if pos.opened_at else None,
                    "closed_at": pos.closed_at.isoformat() if pos.closed_at else None
                }
                for pos in positions
            ],
            "price_history": price_history
        }
    
    def _get_period_pnl(self, user_id: int, start_date, end_date) -> Dict:
        """Calcula PNL para um período específico"""
        
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
        
        return self.pnl_calculator.get_pnl_by_period(user_id, start_datetime, end_datetime)
    
    def _get_price_history(self, asset_name: str, start_date: Optional[datetime], end_date: Optional[datetime]) -> List[Dict]:
        """Obtém histórico de preços (placeholder - implementar com API externa)"""
        
        # Placeholder - em produção, buscar de API externa como CoinGecko, Binance, etc.
        # Por enquanto, retorna dados simulados
        
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)
        
        # Simular dados de preço (substituir por API real)
        price_points = []
        current_date = start_date
        base_price = 100.0  # Preço base simulado
        
        while current_date <= end_date:
            # Simular variação de preço
            import random
            price_change = random.uniform(-5, 5)
            base_price += price_change
            
            price_points.append({
                "timestamp": current_date.isoformat(),
                "price": round(base_price, 2),
                "volume": random.uniform(1000, 10000)
            })
            
            current_date += timedelta(hours=1)
        
        return price_points
    
    def update_account_snapshot(self, user_id: int, client: HyperliquidClient):
        """Cria snapshot da conta"""
        
        try:
            # Atualizar PNL não realizado primeiro
            self.pnl_calculator.update_unrealized_pnl(user_id, client)
            
            # Calcular valores totais
            pnl_summaries = self.db.query(WebhookPnlSummary).filter(
                WebhookPnlSummary.user_id == user_id
            ).all()
            
            total_realized_pnl = sum(s.total_realized_pnl for s in pnl_summaries)
            total_unrealized_pnl = sum(s.total_unrealized_pnl for s in pnl_summaries)
            total_fees = sum(s.total_fees for s in pnl_summaries)
            
            # Obter saldo da conta (se disponível via API)
            account_balance = 0.0
            try:
                account_balance = client.get_account_balance() or 0.0
            except:
                pass
            
            # Criar snapshot
            snapshot = AccountSnapshot(
                user_id=user_id,
                account_balance=account_balance,
                total_realized_pnl=total_realized_pnl,
                total_unrealized_pnl=total_unrealized_pnl,
                net_pnl=total_realized_pnl + total_unrealized_pnl - total_fees,
                total_fees=total_fees,
                timestamp=datetime.now(timezone.utc)
            )
            
            self.db.add(snapshot)
            self.db.commit()
            
            return snapshot
            
        except Exception as e:
            print(f"Erro ao criar snapshot da conta: {e}")
            return None
    
    def get_account_snapshots(
        self, 
        user_id: int, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AccountSnapshot]:
        """Obtém snapshots da conta"""
        
        filters = [AccountSnapshot.user_id == user_id]
        
        if start_date:
            filters.append(AccountSnapshot.timestamp >= start_date)
        
        if end_date:
            filters.append(AccountSnapshot.timestamp <= end_date)
        
        return self.db.query(AccountSnapshot).filter(
            and_(*filters)
        ).order_by(desc(AccountSnapshot.timestamp)).limit(limit).all()