import json
from typing import Optional
from datetime import datetime, timezone
from fastapi import Request
from sqlalchemy.orm import Session
from domain.models import WebhookConfig, WebhookLog

def create_webhook_log(
    db: Session,
    webhook_config: WebhookConfig,
    request: Request,
    request_body: str,
    response_status: int,
    response_body: str,
    is_success: bool,
    error_message: Optional[str] = None
):
    """Cria um log de auditoria para chamadas de webhook"""
    log = WebhookLog(
        webhook_config_id=webhook_config.id,
        timestamp=datetime.now(timezone.utc),
        request_method=request.method,
        request_url=str(request.url),
        request_headers=json.dumps(dict(request.headers)),
        request_body=request_body,
        response_status=response_status,
        response_headers=json.dumps({"Content-Type": "application/json"}),
        response_body=response_body,
        is_success=is_success,
        error_message=error_message
    )
    db.add(log)
    db.commit()
    return log