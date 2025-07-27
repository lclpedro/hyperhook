from typing import Optional, List
from pydantic import BaseModel

# User Schemas
class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    uuid: str
    webhook_secret: str

# Wallet Schemas
class WalletCreate(BaseModel):
    secretKey: str
    publicAddress: str

# Webhook Schemas
class WebhookCreate(BaseModel):
    assetName: str
    hyperliquidSymbol: Optional[str] = None  # Símbolo personalizado para Hyperliquid
    maxUsdValue: float
    leverage: int = 1  # Leverage configurável
    isLiveTrading: bool = False  # Flag para trading real

class WebhookResponse(BaseModel):
    id: int
    assetName: str
    hyperliquidSymbol: Optional[str] = None  # Símbolo personalizado para Hyperliquid
    maxUsdValue: float
    leverage: int  # Leverage no response
    isLiveTrading: bool  # Flag no response

class WebhookLogResponse(BaseModel):
    id: int
    timestamp: str
    request_method: str
    request_url: str
    request_headers: str
    request_body: str
    response_status: int
    response_headers: str
    response_body: str
    is_success: bool
    error_message: Optional[str] = None

# Token Schema
class Token(BaseModel):
    access_token: str
    token_type: str

# Webhook Payload Schemas
class WebhookDataPayload(BaseModel):
    action: str  # "buy" ou "sell"
    contracts: str  # Tamanho da posição
    position_size: str  # Tamanho atual da posição

class WebhookTriggerPayload(BaseModel):
    # Estrutura específica do TradingView
    data: WebhookDataPayload
    price: str  # Preço de execução
    user_info: str  # Info da estratégia
    symbol: str  # Par de trading (ex: NEARUSDT)
    time: str  # Timestamp ISO
    secret: str  # Segredo de autenticação

class GenericWebhookPayload(BaseModel):
    # Estrutura genérica para webhook único
    data: WebhookDataPayload
    price: str  # Preço de execução
    user_info: str  # Info da estratégia
    symbol: str  # Par de trading (ex: NEARUSDT)
    time: str  # Timestamp ISO
    user_uuid: str  # UUID do usuário
    secret: str  # Segredo de autenticação

# PNL System Schemas
class WebhookTradeResponse(BaseModel):
    id: int
    webhook_config_id: int
    asset_name: str
    trade_type: str
    side: str
    quantity: float
    price: float
    usd_value: float
    leverage: int
    timestamp: str
    order_id: Optional[str] = None
    fees: float

class WebhookPositionResponse(BaseModel):
    id: int
    webhook_config_id: int
    asset_name: str
    side: str
    quantity: float
    avg_entry_price: float
    current_price: Optional[float] = None
    unrealized_pnl: float
    realized_pnl: float
    total_fees: float
    leverage: int
    is_open: bool
    opened_at: str
    closed_at: Optional[str] = None
    last_updated: str

class WebhookPnlSummaryResponse(BaseModel):
    id: int
    asset_name: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_realized_pnl: float
    total_unrealized_pnl: float
    total_fees: float
    net_pnl: float
    win_rate: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    total_volume: float
    last_updated: str

class AccountSnapshotResponse(BaseModel):
    id: int
    total_balance: float
    available_balance: float
    used_margin: float
    total_unrealized_pnl: float
    total_positions_value: float
    timestamp: str

class PnlPeriodRequest(BaseModel):
    start_date: str  # ISO format
    end_date: str    # ISO format

class DashboardSummaryResponse(BaseModel):
    account_balance: AccountSnapshotResponse
    period_pnl: float
    period_trades: int
    assets_pnl: List[WebhookPnlSummaryResponse]