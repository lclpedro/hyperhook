from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from domain.schemas import UserCreate, UserLogin, Token
from application.use_cases.auth_use_cases import register_user, login_user
from infrastructure.database import get_db

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register")
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Registra um novo usuário"""
    return register_user(user_data, db)

@router.post("/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Autentica usuário e retorna token de acesso"""
    return login_user(user_credentials, db)