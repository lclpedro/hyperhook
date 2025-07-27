from sqlalchemy.orm import Session
from domain.models import User
from domain.schemas import UserResponse

def get_current_user_info(user: User) -> UserResponse:
    """Retorna as informações do usuário atual"""
    return UserResponse(
        id=user.id,
        email=user.email,
        uuid=user.uuid,
        webhook_secret=user.webhook_secret
    )