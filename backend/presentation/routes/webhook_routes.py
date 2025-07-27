from typing import List
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from domain.models import User
from domain.schemas import WebhookCreate, WebhookResponse, WebhookLogResponse, GenericWebhookPayload
from application.use_cases.webhook_use_cases import (
    create_webhook_config, get_user_webhooks, delete_webhook, 
    get_webhook_logs, get_all_webhook_logs
)
from application.use_cases.webhook_trading_use_cases import process_generic_webhook
from infrastructure.security import get_current_user
from infrastructure.database import get_db

router = APIRouter(tags=["webhooks"])

# Rotas de configuração de webhooks
@router.get("/api/webhooks", response_model=List[WebhookResponse])
def get_webhooks(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna todos os webhooks configurados pelo usuário"""
    return get_user_webhooks(current_user, db)

@router.post("/api/webhooks")
def create_webhook(webhook_data: WebhookCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cria uma nova configuração de webhook"""
    return create_webhook_config(current_user, webhook_data, db)

@router.delete("/api/webhooks/{webhook_id}")
def remove_webhook(webhook_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Remove uma configuração de webhook"""
    return delete_webhook(current_user, webhook_id, db)

@router.get("/api/webhooks/{webhook_id}/logs", response_model=List[WebhookLogResponse])
def get_webhook_log_history(webhook_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna o histórico de logs de um webhook específico"""
    return get_webhook_logs(current_user, webhook_id, db)

@router.get("/api/webhooks/logs", response_model=List[WebhookLogResponse])
def get_all_webhook_log_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna o histórico de logs de todos os webhooks do usuário"""
    return get_all_webhook_logs(current_user, db)

# Rota de execução de webhook
@router.post("/v1/webhook")
def generic_webhook_trigger(payload: GenericWebhookPayload, request: Request, db: Session = Depends(get_db)):
    """Webhook genérico que recebe todos os ativos numa única URL"""
    return process_generic_webhook(payload, request, db)