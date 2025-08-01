from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from domain.models import User
from domain.schemas import (
    DashboardSummaryResponse, WebhookPnlSummaryResponse, WebhookTradeResponse,
    WebhookPositionResponse, PnlPeriodRequest, AccountSnapshotResponse
)
from application.use_cases.pnl_use_cases import (
    get_dashboard_summary, get_assets_performance, get_asset_detailed_performance,
    get_asset_webhook_executions, get_webhook_execution_details, get_pnl_by_period,
    get_user_trades, get_user_positions, update_unrealized_pnl, create_account_snapshot,
    get_account_snapshots, recalculate_user_pnl
)
from infrastructure.security import get_current_user
from infrastructure.database import get_db

router = APIRouter(prefix="/api/dashboard", tags=["pnl"])

@router.get("/")
def dashboard_data(
    period: str = Query("7d", description="Período para análise (1d, 7d, 30d, 90d)"),
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Obtém dados completos do dashboard (summary + assets)"""
    summary = get_dashboard_summary(current_user, period, db)
    assets = get_assets_performance(current_user, period, db)
    return {
        "summary": summary,
        "asset_performance": assets
    }

@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(
    period: str = Query("7d", description="Período para análise (1d, 7d, 30d, 90d)"),
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Obtém resumo completo do dashboard"""
    summary = get_dashboard_summary(current_user, period, db)
    return DashboardSummaryResponse(**summary)

@router.get("/assets", response_model=List[WebhookPnlSummaryResponse])
def assets_performance(
    period: str = Query("7d", description="Período para análise (1d, 7d, 30d, 90d)"),
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Obtém performance por ativo"""
    return get_assets_performance(current_user, period, db)

@router.get("/assets/{trading_view_symbol}")
def asset_detailed_performance(
    trading_view_symbol: str,
    period: str = Query("7d", description="Período para análise (1d, 7d, 30d, 90d)"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém performance detalhada de um ativo específico"""
    return get_asset_detailed_performance(current_user, trading_view_symbol, period, start_date, end_date, db)

@router.get("/assets/{trading_view_symbol}/webhooks")
def asset_webhook_executions(
    trading_view_symbol: str,
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(10, ge=1, le=100, description="Itens por página"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém execuções de webhooks paginadas para um ativo específico"""
    return get_asset_webhook_executions(current_user, trading_view_symbol, page, limit, db)

@router.get("/webhooks/{webhook_id}")
def webhook_execution_details(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém detalhes completos de uma execução de webhook específica"""
    return get_webhook_execution_details(current_user, webhook_id, db)

@router.post("/pnl-period")
def pnl_by_period(
    period_request: PnlPeriodRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém PNL por período específico"""
    return get_pnl_by_period(current_user, period_request, db)

@router.get("/trades", response_model=List[WebhookTradeResponse])
def user_trades(
    limit: int = 50,
    offset: int = 0,
    trading_view_symbol: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém histórico de trades do usuário"""
    return get_user_trades(current_user, limit, offset, trading_view_symbol, db)

@router.get("/positions", response_model=List[WebhookPositionResponse])
def user_positions(
    only_open: bool = True,
    trading_view_symbol: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém posições do usuário do banco de dados"""
    return get_user_positions(current_user, only_open, trading_view_symbol, db)

@router.get("/positions/live")
def live_positions(
    current_user: User = Depends(get_current_user)
):
    """Obtém posições reais da Hyperliquid com preços atuais"""
    from infrastructure.external.hyperliquid_client import HyperliquidClient
    from fastapi import HTTPException, status
    
    if not current_user.wallet or not current_user.wallet.public_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endereço público da carteira não configurado"
        )
    
    client = HyperliquidClient()
    user_state = client.get_user_state(current_user.wallet.public_address)
    
    if not user_state:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível buscar as posições"
        )
    
    positions = []
    all_mids = client.get_all_mids()
    
    if "assetPositions" in user_state:
        for asset_pos in user_state["assetPositions"]:
            if "position" in asset_pos:
                pos = asset_pos["position"]
                coin = pos.get("coin", "")
                size = float(pos.get("szi", "0"))
                
                if size != 0:
                    current_price = float(all_mids.get(coin, 0))
                    entry_price = float(pos.get("entryPx", "0"))
                    unrealized_pnl = float(pos.get("unrealizedPnl", "0"))
                    
                    positions.append({
                        "asset_name": coin,
                        "side": "LONG" if size > 0 else "SHORT",
                        "size": abs(size),
                        "entry_price": entry_price,
                        "current_price": current_price,
                        "unrealized_pnl": unrealized_pnl,
                        "leverage": float(pos.get("leverage", {}).get("value", 1)),
                        "margin_used": float(pos.get("marginUsed", "0")),
                        "return_on_equity": float(pos.get("returnOnEquity", "0"))
                    })
    
    return {
        "positions": positions,
        "account_value": float(user_state.get("marginSummary", {}).get("accountValue", "0")),
        "total_margin_used": float(user_state.get("marginSummary", {}).get("totalMarginUsed", "0")),
        "total_unrealized_pnl": sum(pos["unrealized_pnl"] for pos in positions)
    }

@router.post("/update-prices")
def update_prices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Atualiza PNL não realizado de todas as posições abertas"""
    return update_unrealized_pnl(current_user, db)

@router.post("/snapshot")
def account_snapshot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cria um snapshot da conta"""
    return create_account_snapshot(current_user, db)

@router.get("/snapshots", response_model=List[AccountSnapshotResponse])
def account_snapshots(
    limit: int = Query(10, ge=1, le=100, description="Número de snapshots a retornar"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém histórico de snapshots da conta"""
    return get_account_snapshots(current_user, limit, db)

@router.post("/recalculate-pnl")
def recalculate_pnl(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Recalcula todos os PNLs do usuário para corrigir trades que não foram calculados corretamente"""
    return recalculate_user_pnl(current_user, db)