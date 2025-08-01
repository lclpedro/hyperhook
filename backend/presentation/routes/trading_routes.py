from fastapi import APIRouter, Depends
from domain.models import User
from application.use_cases.trading_use_cases import get_meta_info, debug_asset_rules, list_all_assets, get_hyperliquid_assets
from infrastructure.security import get_current_user

router = APIRouter(prefix="/api", tags=["trading"])

@router.get("/meta")
def get_meta():
    """Obtém informações de metadados da Hyperliquid"""
    return get_meta_info()

@router.get("/debug/asset/{trading_view_symbol}")
def debug_asset(trading_view_symbol: str, current_user: User = Depends(get_current_user)):
    """Obtém regras específicas de um ativo para debug"""
    return debug_asset_rules(trading_view_symbol)

@router.get("/debug/assets")
def list_assets(current_user: User = Depends(get_current_user)):
    """Lista todos os ativos disponíveis com suas regras de tamanho"""
    return list_all_assets()

@router.get("/hyperliquid/assets")
def get_assets(current_user: User = Depends(get_current_user)):
    """Busca lista de ativos da Hyperliquid com cache de 24h"""
    return {"assets": get_hyperliquid_assets()}
