from fastapi import APIRouter, Depends
from domain.models import User
from application.use_cases.trading_use_cases import get_meta_info, debug_asset_rules, list_all_assets
from infrastructure.security import get_current_user

router = APIRouter(prefix="/api", tags=["trading"])

@router.get("/meta")
def get_meta():
    """Obtém informações de metadados da Hyperliquid"""
    return get_meta_info()

@router.get("/debug/asset/{asset_name}")
def debug_asset(asset_name: str, current_user: User = Depends(get_current_user)):
    """Obtém regras específicas de um ativo para debug"""
    return debug_asset_rules(asset_name)

@router.get("/debug/assets")
def list_assets(current_user: User = Depends(get_current_user)):
    """Lista todos os ativos disponíveis com suas regras de tamanho"""
    return list_all_assets()