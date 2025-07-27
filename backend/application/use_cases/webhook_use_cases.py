from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from domain.models import User, WebhookConfig, WebhookLog
from domain.schemas import WebhookCreate, WebhookResponse, WebhookLogResponse

def create_webhook_config(user: User, webhook_data: WebhookCreate, db: Session) -> dict:
    """Cria uma nova configuração de webhook"""
    # Verificar se já existe configuração para este ativo
    existing = db.query(WebhookConfig).filter(
        and_(
            WebhookConfig.user_id == user.id,
            WebhookConfig.asset_name == webhook_data.assetName
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe uma configuração para o ativo {webhook_data.assetName}"
        )
    
    # Criar nova configuração
    webhook_config = WebhookConfig(
        user_id=user.id,
        asset_name=webhook_data.assetName,
        hyperliquid_symbol=webhook_data.hyperliquidSymbol,
        max_usd_value=webhook_data.maxUsdValue,
        leverage=webhook_data.leverage,
        is_live_trading=webhook_data.isLiveTrading
    )
    
    db.add(webhook_config)
    db.commit()
    db.refresh(webhook_config)
    
    return {"message": "Webhook configurado com sucesso", "id": webhook_config.id}

def get_user_webhooks(user: User, db: Session) -> List[WebhookResponse]:
    """Obtém todas as configurações de webhook do usuário"""
    webhooks = db.query(WebhookConfig).filter(WebhookConfig.user_id == user.id).all()
    
    return [
        WebhookResponse(
            id=webhook.id,
            assetName=webhook.asset_name,
            hyperliquidSymbol=webhook.hyperliquid_symbol,
            maxUsdValue=webhook.max_usd_value,
            leverage=webhook.leverage,
            isLiveTrading=webhook.is_live_trading
        )
        for webhook in webhooks
    ]

def delete_webhook(user: User, webhook_id: int, db: Session) -> dict:
    """Remove uma configuração de webhook"""
    webhook = db.query(WebhookConfig).filter(
        and_(
            WebhookConfig.id == webhook_id,
            WebhookConfig.user_id == user.id
        )
    ).first()
    
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook não encontrado"
        )
    
    db.delete(webhook)
    db.commit()
    
    return {"message": "Webhook removido com sucesso"}

def get_webhook_logs(user: User, webhook_id: int, db: Session, limit: int = 50) -> List[WebhookLogResponse]:
    """Obtém o histórico de logs de um webhook específico"""
    # Verificar se o webhook pertence ao usuário
    webhook = db.query(WebhookConfig).filter(
        and_(
            WebhookConfig.id == webhook_id,
            WebhookConfig.user_id == user.id
        )
    ).first()
    
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook não encontrado"
        )
    
    # Buscar logs
    logs = db.query(WebhookLog).filter(
        WebhookLog.webhook_config_id == webhook_id
    ).order_by(desc(WebhookLog.timestamp)).limit(limit).all()
    
    return [
        WebhookLogResponse(
            id=log.id,
            timestamp=log.timestamp.isoformat(),
            request_method=log.request_method,
            request_url=log.request_url,
            request_headers=log.request_headers,
            request_body=log.request_body,
            response_status=log.response_status,
            response_headers=log.response_headers,
            response_body=log.response_body,
            is_success=log.is_success,
            error_message=log.error_message
        )
        for log in logs
    ]

def get_all_webhook_logs(user: User, db: Session, limit: int = 100) -> List[WebhookLogResponse]:
    """Obtém o histórico de logs de todos os webhooks do usuário"""
    # Buscar todos os webhooks do usuário
    webhook_ids = db.query(WebhookConfig.id).filter(WebhookConfig.user_id == user.id).all()
    webhook_ids = [w[0] for w in webhook_ids]
    
    if not webhook_ids:
        return []
    
    # Buscar logs
    logs = db.query(WebhookLog).filter(
        WebhookLog.webhook_config_id.in_(webhook_ids)
    ).order_by(desc(WebhookLog.timestamp)).limit(limit).all()
    
    return [
        WebhookLogResponse(
            id=log.id,
            timestamp=log.timestamp.isoformat(),
            request_method=log.request_method,
            request_url=log.request_url,
            request_headers=log.request_headers,
            request_body=log.request_body,
            response_status=log.response_status,
            response_headers=log.response_headers,
            response_body=log.response_body,
            is_success=log.is_success,
            error_message=log.error_message
        )
        for log in logs
    ]