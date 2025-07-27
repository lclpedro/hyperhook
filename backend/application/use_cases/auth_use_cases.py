from datetime import timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from domain.models import User
from domain.schemas import UserCreate, UserLogin, Token
from infrastructure.security import get_password_hash, verify_password, create_access_token
from config import ACCESS_TOKEN_EXPIRE_MINUTES

def register_user(user_data: UserCreate, db: Session) -> dict:
    """Registra um novo usuário"""
    # Verificar se o email já está cadastrado
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email já cadastrado")
    
    # Criar hash da senha
    hashed_password = get_password_hash(user_data.password)
    
    # Criar usuário
    db_user = User(email=user_data.email, password_hash=hashed_password)
    db.add(db_user)
    db.commit()
    
    return {"message": "Usuário criado com sucesso"}

def login_user(credentials: UserLogin, db: Session) -> Token:
    """Autentica um usuário e retorna token de acesso"""
    # Buscar usuário
    user = db.query(User).filter(User.email == credentials.email).first()
    
    # Verificar credenciais
    if not user or not verify_password(credentials.password, str(user.password_hash)):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ou senha inválidos")
    
    # Criar token de acesso
    access_token = create_access_token(
        data={"sub": str(user.id)}, 
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return Token(access_token=access_token, token_type="bearer")