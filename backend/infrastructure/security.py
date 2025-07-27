from typing import Optional
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from config import SECRET_KEY, ALGORITHM, cipher_suite
from infrastructure.database import get_db

# Security instances
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Encryption functions
def encrypt_data(data: str) -> Optional[str]:
    """Criptografa dados usando Fernet"""
    if not data: 
        return None
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> Optional[str]:
    """Descriptografa dados usando Fernet"""
    if not encrypted_data: 
        return None
    return cipher_suite.decrypt(encrypted_data.encode()).decode()

# Password functions
def get_password_hash(password: str) -> str:
    """Gera hash da senha"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha corresponde ao hash"""
    return pwd_context.verify(plain_password, hashed_password)

# JWT functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Cria token de acesso JWT"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Obtém o usuário atual a partir do token JWT"""
    # Import here to avoid circular imports
    from domain.models import User
    
    credentials_exception = HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError, TypeError):
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user