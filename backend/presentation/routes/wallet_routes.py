from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from domain.models import User
from domain.schemas import WalletCreate
from application.use_cases.wallet_use_cases import get_user_wallet, create_or_update_wallet, get_user_positions
from infrastructure.security import get_current_user
from infrastructure.database import get_db

router = APIRouter(prefix="/api", tags=["wallet"])

@router.get("/wallet")
def get_wallet(current_user: User = Depends(get_current_user)):
    """Retorna dados da carteira do usuário"""
    return get_user_wallet(current_user)

@router.post("/wallet")
def save_wallet(wallet_data: WalletCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Salva ou atualiza dados da carteira"""
    return create_or_update_wallet(current_user, wallet_data, db)

@router.get("/positions")
def get_positions(current_user: User = Depends(get_current_user)):
    """Obtém posições do usuário na Hyperliquid"""
    return get_user_positions(current_user)