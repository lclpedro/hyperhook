from typing import List, Optional
from datetime import date, datetime, timezone, timedelta
from fastapi import HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from domain.models import User, WebhookTrade, WebhookPosition, WebhookConfig, AccountSnapshot
from domain.schemas import (
    DashboardSummaryResponse, WebhookPnlSummaryResponse, WebhookTradeResponse, 
    WebhookPositionResponse, PnlPeriodRequest, AccountSnapshotResponse
)
from infrastructure.external.hyperliquid_client import HyperliquidClient
from application.services.dashboard_service import DashboardService

def get_dashboard_summary(user: User, period: str, db: Session) -> dict:
    """Obtém resumo completo do dashboard"""
    dashboard_service = DashboardService(db)
    summary = dashboard_service.get_dashboard_summary(user.id, period)
    return summary

def get_assets_performance(user: User, period: str, db: Session) -> List[WebhookPnlSummaryResponse]:
    """Obtém performance por ativo"""
    dashboard_service = DashboardService(db)
    assets_data = dashboard_service.get_assets_performance(user.id, period)
    
    # Converter para o formato correto do WebhookPnlSummaryResponse
    return [
        WebhookPnlSummaryResponse(
            id=0,  # Placeholder ID
            trading_view_symbol=asset["asset_name"],
            total_trades=asset["total_trades"],
            winning_trades=asset["winning_trades"],
            losing_trades=asset["losing_trades"],
            total_realized_pnl=asset["realized_pnl"],
            total_unrealized_pnl=asset["unrealized_pnl"],
            total_fees=asset["total_fees"],
            net_pnl=asset["net_pnl"],
            win_rate=asset["win_rate"],
            avg_win=asset["avg_win"],
            avg_loss=asset["avg_loss"],
            largest_win=asset["largest_win"],
            largest_loss=asset["largest_loss"],
            total_volume=asset["total_volume"],
            last_updated=asset["last_updated"] or datetime.now(timezone.utc).isoformat()
        )
        for asset in assets_data
    ]

def get_asset_detailed_performance(user: User, trading_view_symbol: str, period: str, 
                                 start_date: Optional[date], end_date: Optional[date], db: Session) -> dict:
    """Obtém performance detalhada de um ativo específico"""
    from dashboard_service import DashboardService
    dashboard_service = DashboardService(db)
    
    start_datetime = None
    end_datetime = None
    
    # Apenas aplicar filtros de data se start_date ou end_date foram explicitamente fornecidos
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
    
    detailed_data = dashboard_service.get_asset_detailed_performance(
        user.id, trading_view_symbol, start_datetime, end_datetime
    )
    return detailed_data

def get_asset_webhook_executions(user: User, trading_view_symbol: str, page: int, limit: int, db: Session) -> dict:
    """Obtém execuções de webhooks paginadas para um ativo específico"""
    # Calcular offset
    offset = (page - 1) * limit
    
    # Buscar trades com paginação
    trades = db.query(WebhookTrade).filter(
        and_(
            WebhookTrade.user_id == user.id,
            WebhookTrade.asset_name == trading_view_symbol
        )
    ).order_by(desc(WebhookTrade.timestamp)).offset(offset).limit(limit).all()
    
    # Contar total de trades
    total_count = db.query(WebhookTrade).filter(
        and_(
            WebhookTrade.user_id == user.id,
            WebhookTrade.asset_name == trading_view_symbol
        )
    ).count()
    
    # Calcular informações de paginação
    total_pages = (total_count + limit - 1) // limit
    has_next = page < total_pages
    has_prev = page > 1
    
    return {
        "webhooks": [
            {
                "id": trade.id,
                "asset_name": trade.asset_name,
                "trade_type": trade.trade_type,
                "side": trade.side,
                "quantity": trade.quantity,
                "price": trade.price,
                "usd_value": trade.usd_value,
                "leverage": trade.leverage,
                "fees": trade.fees,
                "timestamp": trade.timestamp.isoformat(),
                "order_id": trade.order_id,
                "webhook_config_id": trade.webhook_config_id
            }
            for trade in trades
        ],
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "total_items": total_count,
            "items_per_page": limit,
            "has_next": has_next,
            "has_prev": has_prev
        }
    }

def get_webhook_execution_details(user: User, webhook_id: int, db: Session) -> dict:
    """Obtém detalhes completos de uma execução de webhook específica"""
    # Buscar o trade
    trade = db.query(WebhookTrade).filter(
        and_(
            WebhookTrade.id == webhook_id,
            WebhookTrade.user_id == user.id
        )
    ).first()
    
    if not trade:
        raise HTTPException(status_code=404, detail="Webhook execution not found")
    
    # Buscar configuração do webhook
    webhook_config = db.query(WebhookConfig).filter(
        WebhookConfig.id == trade.webhook_config_id
    ).first()
    
    # Buscar posição relacionada (se existir)
    position = db.query(WebhookPosition).filter(
        and_(
            WebhookPosition.webhook_config_id == trade.webhook_config_id,
            WebhookPosition.user_id == trade.user_id,
            WebhookPosition.asset_name == trade.asset_name
        )
    ).order_by(desc(WebhookPosition.opened_at)).first()
    
    return {
        "webhook_execution": {
            "id": trade.id,
            "asset_name": trade.asset_name,
            "trade_type": trade.trade_type,
            "side": trade.side,
            "quantity": trade.quantity,
            "price": trade.price,
            "usd_value": trade.usd_value,
            "leverage": trade.leverage,
            "fees": trade.fees,
            "timestamp": trade.timestamp.isoformat(),
            "order_id": trade.order_id
        },
        "webhook_config": {
            "id": webhook_config.id if webhook_config else None,
            "trading_view_symbol": webhook_config.trading_view_symbol if webhook_config else "Unknown",
            "max_usd_value": webhook_config.max_usd_value if webhook_config else 0,
            "leverage": webhook_config.leverage if webhook_config else 1,
            "is_live_trading": webhook_config.is_live_trading if webhook_config else False,
            "hyperliquid_symbol": webhook_config.hyperliquid_symbol if webhook_config else None
        } if webhook_config else None,
        "position": {
            "id": position.id if position else None,
            "side": position.side if position else None,
            "quantity": position.quantity if position else 0,
            "avg_entry_price": position.avg_entry_price if position else 0,
            "realized_pnl": position.realized_pnl if position else 0,
            "unrealized_pnl": position.unrealized_pnl if position else 0,
            "is_open": position.is_open if position else False,
            "opened_at": position.opened_at.isoformat() if position and position.opened_at else None,
            "closed_at": position.closed_at.isoformat() if position and position.closed_at else None
        } if position else None
    }

def get_pnl_by_period(user: User, period_request: PnlPeriodRequest, db: Session) -> dict:
    """Obtém PNL por período específico"""
    from infrastructure.services.pnl_calculator import PnlCalculator
    pnl_calculator = PnlCalculator(db)
    
    start_datetime = datetime.combine(period_request.start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_datetime = datetime.combine(period_request.end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
    
    period_pnl = pnl_calculator.get_pnl_by_period(user.id, start_datetime, end_datetime)
    return period_pnl

def get_user_trades(user: User, limit: int, offset: int, trading_view_symbol: Optional[str], db: Session) -> List[WebhookTradeResponse]:
    """Obtém histórico de trades do usuário"""
    filters = [WebhookTrade.user_id == user.id]
    
    if trading_view_symbol:
        filters.append(WebhookTrade.asset_name == trading_view_symbol)
    
    trades = db.query(WebhookTrade).filter(
        and_(*filters)
    ).order_by(desc(WebhookTrade.timestamp)).offset(offset).limit(limit).all()
    
    return [
        WebhookTradeResponse(
            id=trade.id,
            webhook_config_id=trade.webhook_config_id,
            user_id=trade.user_id,
            asset_name=trade.asset_name,
            trade_type=trade.trade_type,
            side=trade.side,
            quantity=trade.quantity,
            price=trade.price,
            usd_value=trade.usd_value,
            leverage=trade.leverage,
            order_id=trade.order_id,
            fees=trade.fees,
            timestamp=trade.timestamp
        )
        for trade in trades
    ]

def get_user_positions(user: User, only_open: bool, trading_view_symbol: Optional[str], db: Session) -> List[WebhookPositionResponse]:
    """Obtém posições do usuário"""
    filters = [WebhookPosition.user_id == user.id]
    
    if only_open:
        filters.append(WebhookPosition.is_open == True)
    
    if trading_view_symbol:
        filters.append(WebhookPosition.asset_name == trading_view_symbol)
    
    positions = db.query(WebhookPosition).filter(
        and_(*filters)
    ).order_by(desc(WebhookPosition.last_updated)).all()
    
    return [
        WebhookPositionResponse(
            id=position.id,
            webhook_config_id=position.webhook_config_id,
            user_id=position.user_id,
            asset_name=position.asset_name,
            trading_view_symbol=position.asset_name,
            side=position.side,
            quantity=position.quantity,
            avg_entry_price=position.avg_entry_price,
            current_price=position.current_price,
            leverage=position.leverage,
            realized_pnl=position.realized_pnl,
            unrealized_pnl=position.unrealized_pnl,
            total_fees=position.total_fees,
            is_open=position.is_open,
            opened_at=position.opened_at.isoformat() if position.opened_at else None,
            closed_at=position.closed_at.isoformat() if position.closed_at else None,
            last_updated=position.last_updated.isoformat() if position.last_updated else None
        )
        for position in positions
    ]

def update_unrealized_pnl(user: User, db: Session) -> dict:
    """Atualiza PNL não realizado de todas as posições abertas"""
    if not user.wallet or not user.wallet.public_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endereço público da carteira não configurado"
        )
    
    try:
        client = HyperliquidClient()
        from pnl_calculator import PnlCalculator
        pnl_calculator = PnlCalculator(db)
        
        pnl_calculator.update_unrealized_pnl(user.id, client)
        
        return {"message": "PNL não realizado atualizado com sucesso"}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar PNL: {str(e)}"
        )

def create_account_snapshot(user: User, db: Session) -> dict:
    """Cria um snapshot da conta"""
    if not user.wallet or not user.wallet.public_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endereço público da carteira não configurado"
        )
    
    try:
        client = HyperliquidClient()
        from pnl_calculator import PnlCalculator
        pnl_calculator = PnlCalculator(db)
        
        snapshot = pnl_calculator.create_account_snapshot(user.id, client)
        
        return {
            "message": "Snapshot criado com sucesso",
            "snapshot_id": snapshot.id,
            "timestamp": snapshot.timestamp.isoformat()
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar snapshot: {str(e)}"
        )

def get_account_snapshots(user: User, limit: int, db: Session) -> List[AccountSnapshotResponse]:
    """Obtém histórico de snapshots da conta"""
    snapshots = db.query(AccountSnapshot).filter(
        AccountSnapshot.user_id == user.id
    ).order_by(desc(AccountSnapshot.timestamp)).limit(limit).all()
    
    return [
        AccountSnapshotResponse(
            id=snapshot.id,
            user_id=snapshot.user_id,
            total_account_value=snapshot.total_account_value,
            total_realized_pnl=snapshot.total_realized_pnl,
            total_unrealized_pnl=snapshot.total_unrealized_pnl,
            total_fees=snapshot.total_fees,
            net_pnl=snapshot.net_pnl,
            total_trades=snapshot.total_trades,
            winning_trades=snapshot.winning_trades,
            losing_trades=snapshot.losing_trades,
            win_rate=snapshot.win_rate,
            timestamp=snapshot.timestamp
        )
        for snapshot in snapshots
    ]

def recalculate_user_pnl(user: User, db: Session) -> dict:
    """Recalcula todos os PNLs do usuário para corrigir trades que não foram calculados corretamente"""
    try:
        from infrastructure.services.pnl_calculator import PnlCalculator
        pnl_calculator = PnlCalculator(db)
        
        # Recalcula todos os resumos de PNL
        pnl_calculator.recalculate_all_pnl_summaries(user.id)
        
        return {"message": "PNL recalculado com sucesso"}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao recalcular PNL: {str(e)}"
        )