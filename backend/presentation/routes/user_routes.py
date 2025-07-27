from fastapi import APIRouter, Depends
from domain.models import User
from domain.schemas import UserResponse
from application.use_cases.user_use_cases import get_current_user_info
from infrastructure.security import get_current_user

router = APIRouter(prefix="/api", tags=["user"])

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Retorna informações do usuário logado"""
    return get_current_user_info(current_user)