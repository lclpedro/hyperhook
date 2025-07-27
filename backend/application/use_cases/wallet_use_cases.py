from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from domain.models import User, Wallet
from domain.schemas import WalletCreate
from infrastructure.security import encrypt_data
from infrastructure.external.hyperliquid_client import HyperliquidClient

def get_user_wallet(user: User) -> dict:
    """Retorna os dados da carteira do usuário (apenas endereço público)"""
    if not user.wallet:
        return {"publicAddress": None}
    
    return {
        "publicAddress": user.wallet.public_address,
        "hasSecretKey": bool(user.wallet.encrypted_secret_key)
    }

def create_or_update_wallet(user: User, wallet_data: WalletCreate, db: Session) -> dict:
    """Cria ou atualiza a carteira do usuário"""
    # Validação básica
    if not wallet_data.publicAddress or not wallet_data.publicAddress.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endereço público é obrigatório"
        )
    
    # Criar carteira se não existir
    if not user.wallet:
        user.wallet = Wallet(user_id=user.id)
        db.add(user.wallet)
    
    # Salvar secret key se fornecida
    if wallet_data.secretKey and wallet_data.secretKey.strip():
        user.wallet.encrypted_secret_key = encrypt_data(wallet_data.secretKey.strip())
    
    # Sempre salvar/atualizar o endereço público
    user.wallet.public_address = wallet_data.publicAddress.strip()
    
    db.commit()
    
    return {"message": "Carteira salva com sucesso"}

def get_user_positions(user: User) -> dict:
    """Obtém as posições do usuário na Hyperliquid"""
    if not user.wallet or not user.wallet.public_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endereço público da carteira não configurado"
        )
    
    client = HyperliquidClient()
    user_state = client.get_user_state(user.wallet.public_address)
    
    if user_state:
        return user_state
    
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Não foi possível buscar as posições"
    )