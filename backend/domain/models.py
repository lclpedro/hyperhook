import uuid
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from infrastructure.database import Base

class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    # UUID para URLs públicas e segredo para webhooks
    uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    webhook_secret = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    wallet = relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    webhooks = relationship("WebhookConfig", back_populates="user", cascade="all, delete-orphan")

class Wallet(Base):
    __tablename__ = "wallet"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    encrypted_secret_key = Column(String(512))
    public_address = Column(String(42), unique=True, nullable=True)
    user = relationship("User", back_populates="wallet")

class WebhookConfig(Base):
    __tablename__ = "webhook_config"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    asset_name = Column(String(20), nullable=False)
    hyperliquid_symbol = Column(String(20), nullable=True)  # Símbolo personalizado para Hyperliquid
    max_usd_value = Column(Float, nullable=False)
    leverage = Column(Integer, default=1, nullable=False)  # Leverage configurável
    is_live_trading = Column(Boolean, default=False, nullable=False)  # Flag para trading real
    user = relationship("User", back_populates="webhooks")
    logs = relationship("WebhookLog", back_populates="webhook_config", cascade="all, delete-orphan")

class WebhookLog(Base):
    __tablename__ = "webhook_log"
    id = Column(Integer, primary_key=True, index=True)
    webhook_config_id = Column(Integer, ForeignKey("webhook_config.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    request_method = Column(String(10), nullable=False)
    request_url = Column(String(255), nullable=False)
    request_headers = Column(Text, nullable=False)
    request_body = Column(Text, nullable=False)
    response_status = Column(Integer, nullable=False)
    response_headers = Column(Text, nullable=False)
    response_body = Column(Text, nullable=False)
    is_success = Column(Boolean, nullable=False, default=True)
    error_message = Column(String(255), nullable=True)
    webhook_config = relationship("WebhookConfig", back_populates="logs")

# Modelos para Sistema de PNL
class WebhookTrade(Base):
    __tablename__ = "webhook_trades"
    id = Column(Integer, primary_key=True, index=True)
    webhook_config_id = Column(Integer, ForeignKey("webhook_config.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    asset_name = Column(String(20), nullable=False)
    trade_type = Column(String(20), nullable=False)  # BUY, SELL, CLOSE, DCA, REDUCE
    side = Column(String(10), nullable=False)  # LONG, SHORT
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    usd_value = Column(Float, nullable=False)
    leverage = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    order_id = Column(String(100), nullable=True)  # ID da ordem na exchange
    fees = Column(Float, default=0.0)
    webhook_config = relationship("WebhookConfig")
    user = relationship("User")

class WebhookPosition(Base):
    __tablename__ = "webhook_positions"
    id = Column(Integer, primary_key=True, index=True)
    webhook_config_id = Column(Integer, ForeignKey("webhook_config.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    asset_name = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # LONG, SHORT
    quantity = Column(Float, nullable=False)
    avg_entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    total_fees = Column(Float, default=0.0)
    leverage = Column(Integer, nullable=False)
    is_open = Column(Boolean, default=True)
    opened_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    webhook_config = relationship("WebhookConfig")
    user = relationship("User")

class WebhookPnlSummary(Base):
    __tablename__ = "webhook_pnl_summary"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    asset_name = Column(String(20), nullable=False)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    total_realized_pnl = Column(Float, default=0.0)
    total_unrealized_pnl = Column(Float, default=0.0)
    total_fees = Column(Float, default=0.0)
    net_pnl = Column(Float, default=0.0)  # realized + unrealized - fees
    win_rate = Column(Float, default=0.0)  # percentage
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    largest_win = Column(Float, default=0.0)
    largest_loss = Column(Float, default=0.0)
    total_volume = Column(Float, default=0.0)
    last_updated = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    user = relationship("User")

class AccountSnapshot(Base):
    __tablename__ = "account_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    total_balance = Column(Float, nullable=False)
    available_balance = Column(Float, nullable=False)
    used_margin = Column(Float, nullable=False)
    total_unrealized_pnl = Column(Float, default=0.0)
    total_positions_value = Column(Float, default=0.0)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    user = relationship("User")