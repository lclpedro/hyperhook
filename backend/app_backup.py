# --- backend/app.py ---
# Instale as dependências: pip install fastapi uvicorn sqlalchemy databases python-jose[cryptography] passlib[bcrypt] python-multipart cryptography hyperliquid-python-sdk eth-account
import os
import uuid
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Text, Boolean, and_, desc
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from cryptography.fernet import Fernet
from typing import Optional, List
from hyperliquid_client import HyperliquidClient

app = FastAPI(title="Hyperliquid Trader API", version="1.1.0")

origins = [
    "http://localhost:3000",  # A origem do seu frontend React local
    "http://127.0.0.1:3000", # Outra forma de aceder ao localhost
    "http://localhost:3001",  # Caso o React esteja em outra porta
    "http://127.0.0.1:3001",
    "https://hyperhook.fly.dev",  # Backend deployado no Fly.io
    "https://hyperhook-frontend.fly.dev",  # Frontend deployado no Fly.io
    
    # IPs do Fly.io e Trading View para comunicação interna
    "http://52.89.214.238",
    "http://34.212.75.30", 
    "http://54.218.53.128",
    "http://52.32.178.7",
    "https://52.89.214.238",
    "https://34.212.75.30", 
    "https://54.218.53.128",
    "https://52.32.178.7",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # ATUALIZADO: Usamos a lista de origens permitidas
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurações
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'super-secret-jwt-key-for-dev-do-not-use-in-prod')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 1 semana

# Database - PostgreSQL com connection string
DB_CONNECTION_STRING = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/hyperliquid_trader')

# Fix para SQLAlchemy 2.x - converter postgres:// para postgresql://
if DB_CONNECTION_STRING.startswith('postgres://'):
    DB_CONNECTION_STRING = DB_CONNECTION_STRING.replace('postgres://', 'postgresql://', 1)

engine = create_engine(DB_CONNECTION_STRING)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Autenticação
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# --- Criptografia para as Chaves de API ---
# Usar uma chave fixa para desenvolvimento (em produção, use variável de ambiente)
DEFAULT_ENCRYPTION_KEY = 'TvI0pq4KaZkYQ1Zd2J7xN8rU5gM3eW9nY6sL7hT4vC0='  # Chave fixa para desenvolvimento
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', DEFAULT_ENCRYPTION_KEY).encode()
cipher_suite = Fernet(ENCRYPTION_KEY)

def encrypt_data(data: str) -> Optional[str]:
    if not data: return None
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> Optional[str]:
    if not encrypted_data: return None
    return cipher_suite.decrypt(encrypted_data.encode()).decode()

def extract_asset_from_symbol(symbol: str) -> str:
    """Extrai o nome do ativo do símbolo de trading (ex: BTCUSDT -> BTC)"""
    # Remove sufixos comuns como USDT, USDC, USD, etc.
    suffixes = ['USDT', 'USDC', 'USD', 'BTC', 'ETH']
    for suffix in suffixes:
        if symbol.endswith(suffix):
            asset = symbol[:-len(suffix)]
            if asset:  # Garantir que sobrou algo após remover o sufixo
                return asset
    # Se não encontrou sufixo conhecido, retorna o símbolo original
    return symbol

# --- Modelos do Banco de Dados (SQLAlchemy) ---
class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    # NOVO: UUID para URLs públicas e segredo para webhooks
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
    hyperliquid_symbol = Column(String(20), nullable=True)  # NOVO: Símbolo personalizado para Hyperliquid
    max_usd_value = Column(Float, nullable=False)
    leverage = Column(Integer, default=1, nullable=False)  # NOVO: Leverage configurável
    is_live_trading = Column(Boolean, default=False, nullable=False)  # NOVO: Flag para trading real
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

# --- Novos Modelos para Sistema de PNL ---
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

# --- Schemas Pydantic ---
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

class WalletCreate(BaseModel):
    secretKey: str
    publicAddress: str

class WebhookCreate(BaseModel):
    assetName: str
    hyperliquidSymbol: Optional[str] = None  # NOVO: Símbolo personalizado para Hyperliquid
    maxUsdValue: float
    leverage: int = 1  # NOVO: Leverage configurável
    isLiveTrading: bool = False  # NOVO: Flag para trading real

class WebhookResponse(BaseModel):
    id: int
    assetName: str
    hyperliquidSymbol: Optional[str] = None  # NOVO: Símbolo personalizado para Hyperliquid
    maxUsdValue: float
    leverage: int  # NOVO: Leverage no response
    isLiveTrading: bool  # NOVO: Flag no response

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

class Token(BaseModel):
    access_token: str
    token_type: str

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

# --- Schemas para Sistema de PNL ---
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

# --- Dependências e Funções Utilitárias ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def calculate_quantity_multiplier(tradingview_asset, hyperliquid_asset, client):
    """
    Calcula o multiplicador de quantidade necessário quando há diferença de preços
    entre TradingView e Hyperliquid (ex: PEPE vs kPEPE com fator 1000x)
    """
    if tradingview_asset == hyperliquid_asset:
        return 1.0
    
    try:
        # Para ativos com prefixo 'k', aplicar multiplicador baseado na diferença de escala
        if hyperliquid_asset.startswith('k') and hyperliquid_asset[1:] == tradingview_asset:
            # Buscar apenas o preço do ativo da Hyperliquid
            hl_price = client.get_asset_price(hyperliquid_asset)
            
            if hl_price > 0:
                # Para ativos k*, geralmente há uma diferença de escala de 1000x
                # Exemplo: PEPE (0.00001) vs kPEPE (0.01) = 1000x diferença
                # Então precisamos dividir a quantidade por 1000
                multiplier = 1.0 / 1000.0
                print(f"💰 ATIVO PERSONALIZADO: {hyperliquid_asset}=${hl_price:.8f}")
                print(f"🔢 APLICANDO MULTIPLICADOR PADRÃO k*: {multiplier:.6f} (1/1000)")
                return multiplier
        
        # Para outros casos, tentar calcular baseado nos preços
        try:
            tv_price = client.get_asset_price(tradingview_asset)
            hl_price = client.get_asset_price(hyperliquid_asset)
            
            if tv_price > 0 and hl_price > 0:
                price_ratio = hl_price / tv_price
                
                if price_ratio >= 100:
                    multiplier = 1.0 / price_ratio
                    print(f"💰 PREÇOS: {tradingview_asset}=${tv_price:.8f}, {hyperliquid_asset}=${hl_price:.8f}")
                    print(f"🔢 RATIO: {price_ratio:.0f}x, MULTIPLICADOR: {multiplier:.6f}")
                    return multiplier
        except:
            pass
        
        return 1.0
        
    except Exception as e:
        print(f"⚠️ Erro ao calcular multiplicador: {e}")
        return 1.0

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

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
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

def analyze_trade_intent(client, user_address, hyperliquid_asset, action, position_size_str, contracts_str):
    """
    Analisa a intenção de trading para determinar se é:
    - Fechamento de posição (position_size = 0)
    - DCA (Dollar Cost Average) - aumentar posição existente
    - Nova posição
    
    Retorna: (tipo_operacao, quantidade_ajustada, detalhes)
    """
    try:
        # Obter posições atuais do usuário
        user_state = client.get_user_state(user_address)
        current_positions = {}
        
        if user_state and "assetPositions" in user_state:
            for pos in user_state["assetPositions"]:
                if "position" in pos:
                    position_data = pos["position"]
                    coin = position_data.get("coin", "")
                    size = float(position_data.get("szi", "0"))
                    if size != 0:  # Apenas posições abertas
                        current_positions[coin] = {
                            "size": size,
                            "side": "LONG" if size > 0 else "SHORT",
                            "abs_size": abs(size),
                            "unrealized_pnl": float(position_data.get("unrealizedPnl", "0"))
                        }
        
        print(f"🔍 Posições atuais: {current_positions}")
        
        # Verificar se já tem posição no ativo
        current_position = current_positions.get(hyperliquid_asset)
        is_buy = action.lower() in ['buy', 'long']
        position_size = float(position_size_str) if position_size_str and position_size_str.strip() else 0
        contracts = float(contracts_str) if contracts_str and contracts_str.strip() else 0
        
        # Cenário 1: SEM POSIÇÃO ATUAL - Nova posição
        if not current_position:
            print("📈 NOVA POSIÇÃO: Nenhuma posição existente encontrada")
            return "NOVA_POSICAO", contracts, {
                "description": "Abrindo nova posição",
                "current_position": None,
                "action_type": "NEW_POSITION"
            }
        
        # Cenário 2: FECHAMENTO DE POSIÇÃO - position_size = 0 e direção oposta
        if position_size == 0:
            current_side = current_position["side"]
            is_opposite_direction = (current_side == "LONG" and not is_buy) or (current_side == "SHORT" and is_buy)
            
            if is_opposite_direction:
                # Fechar a posição inteira
                close_size = current_position["abs_size"]
                # FORÇAR casas decimais corretas para fechamento
                forced_close_size = client.force_valid_order_size(hyperliquid_asset, close_size)
                print(f"🔄 FECHAMENTO: Fechando posição {current_side} de {close_size} → {forced_close_size} {hyperliquid_asset}")
                return "FECHAMENTO", forced_close_size, {
                    "description": f"Fechando posição {current_side} de {close_size}",
                    "current_position": current_position,
                    "action_type": "CLOSE_POSITION",
                    "original_size": current_position["abs_size"]
                }
        
        # Cenário 3: DCA - Mesma direção da posição existente
        current_side = current_position["side"]
        is_same_direction = (current_side == "LONG" and is_buy) or (current_side == "SHORT" and not is_buy)
        
        if is_same_direction:
            # FORÇAR casas decimais corretas para DCA
            forced_contracts = client.force_valid_order_size(hyperliquid_asset, contracts)
            print(f"📊 DCA: Aumentando posição {current_side} existente de {current_position['abs_size']} com +{contracts} → +{forced_contracts}")
            return "DCA", forced_contracts, {
                "description": f"DCA - Aumentando posição {current_side} de {current_position['abs_size']} para {current_position['abs_size'] + contracts}",
                "current_position": current_position,
                "action_type": "DCA",
                "original_size": current_position["abs_size"],
                "new_total_size": current_position["abs_size"] + contracts
            }
        
        # Cenário 4: REDUÇÃO DE POSIÇÃO - Direção oposta mas não position_size = 0
        if not is_same_direction:
            reduction_size = min(contracts, current_position["abs_size"])
            # FORÇAR casas decimais corretas para redução
            forced_reduction_size = client.force_valid_order_size(hyperliquid_asset, reduction_size)
            print(f"📉 REDUÇÃO: Reduzindo posição {current_side} de {current_position['abs_size']} em {reduction_size} → {forced_reduction_size}")
            return "REDUCAO", forced_reduction_size, {
                "description": f"Reduzindo posição {current_side} de {current_position['abs_size']} em {reduction_size}",
                "current_position": current_position,
                "action_type": "REDUCE_POSITION",
                "original_size": current_position["abs_size"],
                "reduction_amount": reduction_size,
                "remaining_size": current_position["abs_size"] - reduction_size
            }
        
        # Fallback - usar quantidade original
        return "PADRAO", contracts, {
            "description": "Usando quantidade padrão do payload",
            "current_position": current_position,
            "action_type": "DEFAULT"
        }
        
    except Exception as e:
        print(f"⚠️ Erro ao analisar intenção de trading: {e}")
        # Em caso de erro, usar quantidade original
        contracts = float(contracts_str) if contracts_str and contracts_str.strip() else 0
        return "ERRO", contracts, {
            "description": f"Erro na análise - usando quantidade original: {str(e)}",
            "current_position": None,
            "action_type": "ERROR"
        }

# --- Rotas ---
@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email já cadastrado")
    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, password_hash=hashed_password)
    db.add(db_user)
    db.commit()
    return {"message": "Usuário criado com sucesso"}

@app.post("/login", response_model=Token)
def login(form_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.email).first()
    if not user or not verify_password(form_data.password, str(user.password_hash)):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ou senha inválidos")
    access_token = create_access_token(
        data={"sub": str(user.id)}, 
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    """NOVO: Retorna os detalhes do usuário logado, incluindo UUID e segredo."""
    return current_user


@app.get("/api/wallet")
def get_wallet(current_user: User = Depends(get_current_user)):
    """Retorna os dados da carteira do usuário (apenas endereço público)"""
    if not current_user.wallet:
        return {"publicAddress": None}
    
    return {
        "publicAddress": current_user.wallet.public_address,
        "hasSecretKey": bool(current_user.wallet.encrypted_secret_key)
    }

@app.post("/api/wallet")
def create_wallet(wallet_data: WalletCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Validação básica
    if not wallet_data.publicAddress or not wallet_data.publicAddress.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endereço público é obrigatório"
        )
    
    if not current_user.wallet:
        current_user.wallet = Wallet(user_id=current_user.id)
        db.add(current_user.wallet)
    
    # Salvar secret key se fornecida
    if wallet_data.secretKey and wallet_data.secretKey.strip():
        current_user.wallet.encrypted_secret_key = encrypt_data(wallet_data.secretKey.strip())
    
    # Sempre salvar/atualizar o endereço público
    current_user.wallet.public_address = wallet_data.publicAddress.strip()
    
    db.commit()
    
    return {"message": "Carteira salva com sucesso"}

@app.get("/api/positions")
def get_positions(current_user: User = Depends(get_current_user)):
    if not current_user.wallet or not current_user.wallet.public_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Endereço público da carteira não configurado"
        )
    
    client = HyperliquidClient()
    user_state = client.get_user_state(current_user.wallet.public_address)
    
    if user_state:
        return user_state
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Não foi possível buscar as posições"
    )

@app.get("/api/meta")
def get_meta():
    client = HyperliquidClient()
    meta = client.info.meta()
    
    try:
        all_mids = client.get_all_mids()
        contexts = []
        
        if meta and 'universe' in meta:
            for asset in meta['universe']:
                asset_name = asset.get('name')
                mark_price = all_mids.get(asset_name, 0.0)
                contexts.append({
                    'markPx': str(mark_price)
                })
        
        return {
            'universe': meta.get('universe', []),
            'contexts': contexts
        }
    except Exception as e:
        print(f"Error fetching meta with prices: {e}")
        return meta


@app.post("/webhook/trigger/{user_uuid}/{asset_name}")
def webhook_trigger(user_uuid: str, asset_name: str, payload: WebhookTriggerPayload, request: Request, db: Session = Depends(get_db)):
    """ATUALIZADO: Processa webhooks do TradingView com diferentes formatos de payload e registra logs de auditoria."""
    
    # Serializar o payload para logs
    request_body = payload.model_dump_json()
    
    # Encontrar usuário
    user = db.query(User).filter(User.uuid == user_uuid).first()
    if not user:
        error_msg = "URL de Webhook inválida (usuário não encontrado)"
        return HTTPException(status_code=404, detail=error_msg)

    # Validação do segredo
    if payload.secret != user.webhook_secret:
        error_msg = "Segredo de webhook inválido"
        return HTTPException(status_code=403, detail=error_msg)

    # Encontrar configuração do webhook
    config = db.query(WebhookConfig).filter(WebhookConfig.user_id == user.id, WebhookConfig.asset_name == asset_name).first()
    if not config or not user.wallet:
        error_msg = f"Configuração de webhook ou carteira inválida para este ativo '{asset_name}'"
        return HTTPException(status_code=404, detail=error_msg)

    print(f"ORDEM RECEBIDA: Usuário {user.id}, Ativo {asset_name}")
    print(f"Payload completo: {payload.model_dump()}")
    print(f"Config encontrada: ID={config.id}, Leverage={config.leverage}, Max=${config.max_usd_value}")
    
    try:
        secret_key = decrypt_data(user.wallet.encrypted_secret_key)
        if not secret_key:
            error_msg = "Chave privada não configurada"
            create_webhook_log(db, config, request, request_body, 500, "", False, error_msg)
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        client = HyperliquidClient()
        
        # Extrair dados do payload TradingView (formato único)
        action = payload.data.action
        contracts = payload.data.contracts
        symbol = payload.symbol
        price_data = payload.price
        user_info = payload.user_info
        
        # Determinar o tamanho da ordem
        order_size = None
        
        # 1. Prioridade: usar contracts do TradingView (FORÇAR casas decimais corretas)
        if contracts:
            try:
                tv_size = float(contracts)
                # FORÇA as casas decimais corretas para o ativo
                order_size = client.force_valid_order_size(hyperliquid_asset, tv_size)
                print(f"📺 TradingView: {tv_size} → {order_size} (forçado para {hyperliquid_asset})")
            except (ValueError, TypeError):
                print(f"Erro ao converter contracts '{contracts}' para float")
        
        # 2. Fallback: calcular baseado no valor máximo configurado
        if order_size is None:
            order_size = client.calculate_order_size(hyperliquid_asset, config.max_usd_value)
            print(f"Usando valor máximo configurado: {order_size} (baseado em ${config.max_usd_value})")
        
        # Validar e ajustar o tamanho da ordem para as regras da Hyperliquid
        order_size = client.validate_and_fix_order_size(hyperliquid_asset, order_size)
        print(f"✅ TAMANHO VALIDADO: {order_size}")
        
        is_buy = action.lower() in ['buy', 'long']
        
        # Determinar o preço
        limit_price = None
        if price_data and str(price_data).strip():
            try:
                limit_price = float(price_data)
                print(f"Usando preço do TradingView: {limit_price}")
            except (ValueError, TypeError):
                print(f"Erro ao converter price '{price_data}' para float")
        
        # Usar o leverage configurado no webhook
        leverage_to_use = getattr(config, 'leverage', 1)
        print(f"Usando leverage configurado: {leverage_to_use}x")
        
        result = client.place_order(
            secret_key=secret_key,
            asset_name=hyperliquid_asset,
            is_buy=is_buy,
            size=order_size,
            limit_price=limit_price,
            stop_loss=None,  # Removido - não está no novo formato
            take_profit=None,  # Removido - não está no novo formato
            comment=user_info,  # Usando user_info como comentário
            is_live_trading=bool(config.is_live_trading),  # NOVO: Flag para trading real
            leverage=leverage_to_use  # NOVO: Aplicar leverage configurado
        )
        
        print(f"Resultado da Hyperliquid: {result}")
        
        response_data = {
            "status": "sucesso", 
            "details": result,
            "processed_data": {
                "action": action,
                "size": order_size,
                "price": limit_price,
                "leverage": leverage_to_use,
                "asset": hyperliquid_asset,
                "original_asset": asset_name,
                "symbol": symbol,
                "user_info": user_info
            }
        }
        
        # NOVO: Registrar trade no sistema de PNL
        try:
            from pnl_calculator import PnlCalculator
            pnl_calculator = PnlCalculator(db)
            
            # Usar o tipo de trade da análise inteligente
            side = "LONG" if is_buy else "SHORT"
            
            # Calcular valor USD
            usd_value = order_size * (limit_price if limit_price else 0)
            
            # Registrar trade
            pnl_calculator.record_trade(
                webhook_config_id=config.id,
                user_id=user.id,
                asset_name=asset_name,
                trade_type=action, # Use action from payload
                side=side,
                quantity=order_size,
                price=limit_price if limit_price else 0,
                usd_value=usd_value,
                leverage=leverage_to_use,
                order_id=result.get('order_id') if isinstance(result, dict) else None,
                fees=0.0  # Será atualizado posteriormente quando disponível
            )
            
            print(f"✅ Trade registrado no sistema de PNL (tipo: {action})")
            
        except Exception as pnl_error:
            print(f"⚠️ Erro ao registrar trade no PNL: {pnl_error}")
            # Não falhar o webhook por erro no PNL
        
        # Log de sucesso
        create_webhook_log(db, config, request, request_body, 200, json.dumps(response_data), True)
        
        return response_data
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        error_msg = f"Falha ao executar ordem: {str(e) if str(e) else 'Erro desconhecido'}"
        print(f"ERRO AO PROCESSAR ORDEM: {e}")
        print(f"TRACEBACK COMPLETO: {error_details}")
        
        # Log de erro
        create_webhook_log(db, config, request, request_body, 500, "", False, error_msg)
        
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

@app.post("/v1/webhook")
def generic_webhook_trigger(payload: GenericWebhookPayload, request: Request, db: Session = Depends(get_db)):
    """NOVO: Webhook genérico que recebe todos os ativos numa única URL."""
    
    # Serializar o payload para logs
    request_body = payload.model_dump_json()
    
    # Extrair asset name do symbol (ex: BTCUSDT -> BTC)
    asset_name = extract_asset_from_symbol(payload.symbol)
    
    # Encontrar usuário
    user = db.query(User).filter(User.uuid == payload.user_uuid).first()
    if not user:
        error_msg = "UUID de usuário inválido"
        return HTTPException(status_code=404, detail=error_msg)

    # Validação do segredo
    if payload.secret != user.webhook_secret:
        error_msg = "Segredo de webhook inválido"
        return HTTPException(status_code=403, detail=error_msg)

    # Encontrar configuração do webhook para este ativo
    # Primeiro tenta buscar pelo asset_name (ativo da Hyperliquid)
    config = db.query(WebhookConfig).filter(WebhookConfig.user_id == user.id, WebhookConfig.asset_name == asset_name).first()
    
    # Se não encontrou, tenta buscar pelo hyperliquid_symbol (símbolo do TradingView)
    if not config:
        config = db.query(WebhookConfig).filter(
            WebhookConfig.user_id == user.id, 
            WebhookConfig.hyperliquid_symbol == asset_name
        ).first()
    
    if not config or not user.wallet:
        error_msg = f"Configuração de webhook não encontrada para o ativo '{asset_name}' (extraído de '{payload.symbol}'). Configure este ativo na interface primeiro."
        return HTTPException(status_code=404, detail=error_msg)

    print(f"🔥 WEBHOOK GENÉRICO: Usuário {user.id}, Symbol {payload.symbol} → Ativo {asset_name}")
    print(f"Payload completo: {payload.model_dump()}")
    print(f"Config encontrada: ID={config.id}, Leverage={config.leverage}, Max=${config.max_usd_value}, Live={config.is_live_trading}")
    
    try:
        secret_key = decrypt_data(user.wallet.encrypted_secret_key)
        if not secret_key:
            error_msg = "Chave privada não configurada"
            create_webhook_log(db, config, request, request_body, 500, "", False, error_msg)
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        client = HyperliquidClient()
        
        # Extrair dados do payload TradingView (formato único)
        action = payload.data.action
        contracts = payload.data.contracts
        symbol = payload.symbol
        price_data = payload.price
        user_info = payload.user_info
        position_size = payload.data.position_size
        
        # NOVO: Determinar se é ativo personalizado e fazer mapeamento correto
        # Primeiro verificar se há configuração manual
        if config.hyperliquid_symbol and config.hyperliquid_symbol != asset_name:
            # Ativo personalizado: usar símbolo configurado manualmente
            hyperliquid_asset = config.hyperliquid_symbol
            is_custom_asset = True
            print(f"🔄 ATIVO PERSONALIZADO (manual): {asset_name} → {hyperliquid_asset}")
        else:
            # Verificar se o ativo existe na Hyperliquid diretamente
            try:
                client.get_asset_info(asset_name)
                # Se chegou aqui, o ativo existe diretamente
                hyperliquid_asset = asset_name
                is_custom_asset = False
                print(f"🔄 ATIVO ORIGINAL: {asset_name} (existe na Hyperliquid)")
            except:
                # Ativo não existe diretamente, tentar com prefixo 'k' minúsculo
                try:
                    k_asset = f"k{asset_name}"
                    client.get_asset_info(k_asset)
                    # Se chegou aqui, o ativo existe com prefixo 'k'
                    hyperliquid_asset = k_asset
                    is_custom_asset = True
                    print(f"🔄 ATIVO PERSONALIZADO (auto-detectado): {asset_name} → {hyperliquid_asset}")
                except:
                    # Nenhuma das opções funcionou, usar o original mesmo
                    hyperliquid_asset = asset_name
                    is_custom_asset = False
                    print(f"⚠️ ATIVO NÃO ENCONTRADO: usando {asset_name} (pode falhar)")
        
        # NOVO: Ajustar quantidade apenas para ativos personalizados
        if is_custom_asset:
            quantity_multiplier = calculate_quantity_multiplier(asset_name, hyperliquid_asset, client)
            print(f"📊 MULTIPLICADOR DE QUANTIDADE (personalizado): {quantity_multiplier}x")
        else:
            quantity_multiplier = 1.0
            print(f"📊 MULTIPLICADOR DE QUANTIDADE (original): {quantity_multiplier}x")
        
        # NOVO: Aplicar multiplicador de quantidade apenas para ativos personalizados
        original_contracts = contracts
        original_position_size = position_size
        
        if is_custom_asset and quantity_multiplier != 1.0:
            try:
                adjusted_contracts = float(contracts) * quantity_multiplier if contracts else 0
                adjusted_position_size = float(position_size) * quantity_multiplier if position_size else 0
                contracts = str(adjusted_contracts)
                position_size = str(adjusted_position_size)
                print(f"🔄 AJUSTE DE QUANTIDADE (ativo personalizado):")
                print(f"  Contracts: {original_contracts} → {contracts}")
                print(f"  Position Size: {original_position_size} → {position_size}")
            except (ValueError, TypeError) as e:
                print(f"⚠️ Erro ao aplicar multiplicador: {e}")
        else:
            print(f"📋 USANDO DADOS ORIGINAIS (ativo original): Contracts={contracts}, Position Size={position_size}")
        
        # NOVA FUNCIONALIDADE: Análise inteligente da intenção de trading
        print(f"\n🧠 ANALISANDO INTENÇÃO DE TRADING...")
        print(f"Action: {action}, Contracts: {contracts}, Position Size: {position_size}")
        
        try:
            # Analisar se é fechamento, DCA, nova posição, etc.
            trade_type, adjusted_size, trade_details = analyze_trade_intent(
                client=client,
                user_address=user.wallet.public_address,
                hyperliquid_asset=hyperliquid_asset,
                action=action,
                position_size_str=position_size,
                contracts_str=contracts
            )
            
            print(f"🎯 RESULTADO DA ANÁLISE:")
            print(f"  Tipo: {trade_type}")
            print(f"  Descrição: {trade_details['description']}")
            print(f"  Quantidade original: {contracts}")
            print(f"  Quantidade ajustada pela análise: {adjusted_size}")
            
            # FORÇAR casas decimais corretas no resultado da análise
            if adjusted_size > 0:
                forced_adjusted_size = client.force_valid_order_size(hyperliquid_asset, adjusted_size)
                print(f"🔧 Quantidade final forçada: {adjusted_size} → {forced_adjusted_size}")
                adjusted_size = forced_adjusted_size
            
        except Exception as analysis_error:
            print(f"⚠️ Erro na análise de trading: {analysis_error}")
            # Fallback para comportamento original
            trade_type = "ERRO"
            fallback_size = float(contracts) if contracts else 0
            # FORÇAR casas decimais corretas no fallback também
            adjusted_size = client.force_valid_order_size(hyperliquid_asset, fallback_size) if fallback_size > 0 else 0
            trade_details = {
                "description": f"Erro na análise - usando quantidade original: {str(analysis_error)}",
                "action_type": "ERROR"
            }
        
        # Determinar o tamanho da ordem (usar o ajustado pela análise)
        order_size = adjusted_size
        
        # Se a análise resultou em tamanho 0, usar fallback
        if order_size == 0:
            max_usd_value = getattr(config, 'max_usd_value', 0)
            if max_usd_value and max_usd_value > 0:
                order_size = client.calculate_order_size(hyperliquid_asset, max_usd_value)
                print(f"⚠️ Quantidade zero detectada - usando valor máximo configurado: {order_size} (baseado em ${max_usd_value})")
            else:
                raise ValueError("Quantidade da ordem é zero e não há valor máximo configurado")
        
        # Validar e ajustar o tamanho da ordem para as regras da Hyperliquid
        order_size = client.validate_and_fix_order_size(hyperliquid_asset, order_size)
        print(f"✅ TAMANHO FINAL DA ORDEM (validado): {order_size}")
        
        is_buy = action.lower() in ['buy', 'long']
        
        # Determinar o preço
        limit_price = None
        if price_data and str(price_data).strip():
            try:
                limit_price = float(price_data)
                print(f"Usando preço do TradingView: {limit_price}")
            except (ValueError, TypeError):
                print(f"Erro ao converter price '{price_data}' para float")
        
        # Usar o leverage configurado no webhook
        leverage_to_use = getattr(config, 'leverage', 1)
        print(f"Usando leverage configurado: {leverage_to_use}x")
        print(f"Modo: {'🚀 REAL' if bool(config.is_live_trading) else '🔄 SIMULAÇÃO'}")
        
        result = client.place_order(
            secret_key=secret_key,
            asset_name=hyperliquid_asset,
            is_buy=is_buy,
            size=order_size,
            limit_price=limit_price,
            stop_loss=None,
            take_profit=None,
            comment=f"{user_info} | {trade_type}: {trade_details['description']}",
            is_live_trading=bool(config.is_live_trading),
            leverage=leverage_to_use
        )
        
        print(f"Resultado da Hyperliquid: {result}")
        
        response_data = {
            "status": "sucesso", 
            "details": result,
            "processed_data": {
                "action": action,
                "size": order_size,
                "price": limit_price,
                "leverage": leverage_to_use,
                "asset": asset_name,
                "hyperliquid_asset": hyperliquid_asset,
                "symbol": symbol,
                "user_info": user_info,
                "is_live_trading": bool(config.is_live_trading)
            },
            "quantity_adjustment": {
                "multiplier": quantity_multiplier,
                "original_contracts": original_contracts,
                "adjusted_contracts": contracts,
                "original_position_size": original_position_size,
                "adjusted_position_size": position_size
            },
            "trade_analysis": {
                "type": trade_type,
                "description": trade_details["description"],
                "original_contracts": original_contracts,
                "adjusted_size": order_size,
                "details": trade_details
            }
        }
        
        # NOVO: Registrar trade no sistema de PNL
        try:
            from pnl_calculator import PnlCalculator
            pnl_calculator = PnlCalculator(db)
            
            # Usar o tipo de trade da análise inteligente
            side = "LONG" if is_buy else "SHORT"
            
            # Calcular valor USD
            usd_value = order_size * (limit_price if limit_price else 0)
            
            # Registrar trade
            pnl_calculator.record_trade(
                webhook_config_id=config.id,
                user_id=user.id,
                asset_name=asset_name,
                trade_type=trade_type,  # Usar tipo da análise inteligente
                side=side,
                quantity=order_size,
                price=limit_price if limit_price else 0,
                usd_value=usd_value,
                leverage=leverage_to_use,
                order_id=result.get('order_id') if isinstance(result, dict) else None,
                fees=0.0  # Será atualizado posteriormente quando disponível
            )
            
            print(f"✅ Trade registrado no sistema de PNL (tipo: {trade_type})")
            
        except Exception as pnl_error:
            print(f"⚠️ Erro ao registrar trade no PNL: {pnl_error}")
            # Não falhar o webhook por erro no PNL
        
        # Log de sucesso
        create_webhook_log(db, config, request, request_body, 200, json.dumps(response_data), True)
        
        return response_data
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        error_msg = f"Falha ao executar ordem: {str(e) if str(e) else 'Erro desconhecido'}"
        print(f"ERRO AO PROCESSAR ORDEM: {e}")
        print(f"TRACEBACK COMPLETO: {error_details}")
        
        # Log de erro
        create_webhook_log(db, config, request, request_body, 500, "", False, error_msg)
        
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

@app.get("/api/webhooks", response_model=List[WebhookResponse])
def get_webhooks(current_user: User = Depends(get_current_user)):
    """Retorna todos os webhooks configurados pelo usuário"""
    webhooks = []
    for webhook in current_user.webhooks:
        webhooks.append(WebhookResponse(
            id=webhook.id,
            assetName=webhook.asset_name,
            hyperliquidSymbol=webhook.hyperliquid_symbol,
            maxUsdValue=webhook.max_usd_value,
            leverage=webhook.leverage,
            isLiveTrading=webhook.is_live_trading
        ))
    return webhooks

@app.post("/api/webhooks")
def create_webhook(webhook_data: WebhookCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cria uma nova configuração de webhook"""
    # Verifica se já existe um webhook para este ativo
    existing = db.query(WebhookConfig).filter(
        WebhookConfig.user_id == current_user.id,
        WebhookConfig.asset_name == webhook_data.assetName
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Webhook para este ativo já existe"
        )
    
    webhook_config = WebhookConfig(
        user_id=current_user.id,
        asset_name=webhook_data.assetName,
        hyperliquid_symbol=webhook_data.hyperliquidSymbol,
        max_usd_value=webhook_data.maxUsdValue,
        leverage=webhook_data.leverage,
        is_live_trading=webhook_data.isLiveTrading
    )
    
    db.add(webhook_config)
    db.commit()
    db.refresh(webhook_config)
    
    return {"message": "Webhook criado com sucesso", "id": webhook_config.id}

@app.delete("/api/webhooks/{webhook_id}")
def delete_webhook(webhook_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Remove uma configuração de webhook"""
    webhook = db.query(WebhookConfig).filter(
        WebhookConfig.id == webhook_id,
        WebhookConfig.user_id == current_user.id
    ).first()
    
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook não encontrado"
        )
    
    db.delete(webhook)
    db.commit()
    
    return {"message": "Webhook removido com sucesso"}

@app.get("/api/webhooks/{webhook_id}/logs", response_model=List[WebhookLogResponse])
def get_webhook_logs(webhook_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna o histórico de logs de um webhook específico"""
    webhook = db.query(WebhookConfig).filter(
        WebhookConfig.id == webhook_id,
        WebhookConfig.user_id == current_user.id
    ).first()
    
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook não encontrado"
        )
    
    logs = db.query(WebhookLog).filter(
        WebhookLog.webhook_config_id == webhook_id
    ).order_by(WebhookLog.timestamp.desc()).limit(50).all()
    
    log_responses = []
    for log in logs:
        log_responses.append(WebhookLogResponse(
            id=log.id,  # type: ignore
            timestamp=log.timestamp.isoformat(),  # type: ignore
            request_method=log.request_method,  # type: ignore
            request_url=log.request_url,  # type: ignore
            request_headers=log.request_headers,  # type: ignore
            request_body=log.request_body,  # type: ignore
            response_status=log.response_status,  # type: ignore
            response_headers=log.response_headers,  # type: ignore
            response_body=log.response_body,  # type: ignore
            is_success=log.is_success,  # type: ignore
            error_message=log.error_message  # type: ignore
        ))
    return log_responses

@app.get("/api/webhooks/logs", response_model=List[WebhookLogResponse])
def get_all_webhook_logs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retorna o histórico de logs de todos os webhooks do usuário"""
    webhook_ids = [webhook.id for webhook in current_user.webhooks]
    
    if not webhook_ids:
        return []
    
    logs = db.query(WebhookLog).filter(
        WebhookLog.webhook_config_id.in_(webhook_ids)
    ).order_by(WebhookLog.timestamp.desc()).limit(100).all()
    
    log_responses = []
    for log in logs:
        log_responses.append(WebhookLogResponse(
            id=log.id,  # type: ignore
            timestamp=log.timestamp.isoformat(),  # type: ignore
            request_method=log.request_method,  # type: ignore
            request_url=log.request_url,  # type: ignore
            request_headers=log.request_headers,  # type: ignore
            request_body=log.request_body,  # type: ignore
            response_status=log.response_status,  # type: ignore
            response_headers=log.response_headers,  # type: ignore
            response_body=log.response_body,  # type: ignore
            is_success=log.is_success,  # type: ignore
            error_message=log.error_message  # type: ignore
        ))
    return log_responses

# --- Debug Asset Rules ---
@app.get("/api/debug/asset/{asset_name}")
async def debug_asset_rules(asset_name: str, current_user: dict = Depends(get_current_user)):
    """Debug: Mostra as regras específicas de um ativo na Hyperliquid"""
    try:
        client = HyperliquidClient()
        asset_info = client.debug_asset_rules(asset_name)
        
        if asset_info:
            return {
                "asset_name": asset_name,
                "sz_decimals": asset_info["szDecimals"],
                "min_increment": 10 ** (-asset_info["szDecimals"]),
                "index": asset_info.get("index", "N/A"),
                "max_leverage": asset_info.get("maxLeverage", "N/A"),
                "examples": {
                    "valid_sizes": [
                        round(1.0, asset_info["szDecimals"]),
                        round(0.1, asset_info["szDecimals"]),
                        round(0.01, asset_info["szDecimals"]),
                        10 ** (-asset_info["szDecimals"])  # Menor incremento
                    ]
                }
            }
        else:
            raise HTTPException(status_code=404, detail=f"Asset {asset_name} não encontrado")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar regras do asset: {str(e)}")

# --- Listar Todos os Assets ---
@app.get("/api/debug/assets")
async def list_all_assets(current_user: dict = Depends(get_current_user)):
    """Lista todos os assets disponíveis com suas regras de tamanho"""
    try:
        client = HyperliquidClient()
        meta = client.info.meta()
        universe = meta["universe"]
        
        assets = []
        for asset_info in universe:
            assets.append({
                "name": asset_info["name"],
                "sz_decimals": asset_info["szDecimals"],
                "min_increment": 10 ** (-asset_info["szDecimals"]),
                "index": asset_info.get("index", "N/A"),
                "max_leverage": asset_info.get("maxLeverage", "N/A")
            })
        
        # Ordenar por nome
        assets.sort(key=lambda x: x["name"])
        
        return {
            "total_assets": len(assets),
            "assets": assets
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar assets: {str(e)}")

# --- PNL System Routes ---
from datetime import date
from fastapi.responses import StreamingResponse
import io

@app.get("/api/dashboard/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    period: str = Query("7d", description="Período para análise (1d, 7d, 30d, 90d)"),
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Obtém resumo completo do dashboard"""
    from dashboard_service import DashboardService
    dashboard_service = DashboardService(db)
    summary = dashboard_service.get_dashboard_summary(current_user.id, period)
    return DashboardSummaryResponse(**summary)

@app.get("/api/dashboard/assets", response_model=List[WebhookPnlSummaryResponse])
def get_assets_performance(
    period: str = Query("7d", description="Período para análise (1d, 7d, 30d, 90d)"),
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Obtém performance por ativo"""
    from dashboard_service import DashboardService
    dashboard_service = DashboardService(db)
    assets_data = dashboard_service.get_assets_performance(current_user.id, period)
    
    # Converter para o formato correto do WebhookPnlSummaryResponse
    return [
        WebhookPnlSummaryResponse(
            id=0,  # Placeholder ID
            asset_name=asset["asset_name"],
            total_trades=asset["total_trades"],
            winning_trades=asset["winning_trades"],
            losing_trades=asset["losing_trades"],
            total_realized_pnl=asset["realized_pnl"],
            total_unrealized_pnl=asset["unrealized_pnl"],
            total_fees=asset["total_fees"],
            net_pnl=asset["net_pnl"],
            win_rate=asset["win_rate"],
            avg_win=asset["avg_win"],
            avg_loss=asset["avg_loss"],
            largest_win=asset["largest_win"],
            largest_loss=asset["largest_loss"],
            total_volume=asset["total_volume"],
            last_updated=asset["last_updated"] or datetime.now(timezone.utc).isoformat()
        )
        for asset in assets_data
    ]

@app.get("/api/dashboard/assets/{asset_name}")
def get_asset_detailed_performance(
    asset_name: str,
    period: str = Query("7d", description="Período para análise (1d, 7d, 30d, 90d)"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém performance detalhada de um ativo específico"""
    from dashboard_service import DashboardService
    dashboard_service = DashboardService(db)
    
    start_datetime = None
    end_datetime = None
    
    # Se período foi especificado, calcular datas
    if not start_date and not end_date:
        today = date.today()
        days_map = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}
        days = days_map.get(period, 7)
        start_date = today - timedelta(days=days)
        end_date = today
    
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
    
    detailed_data = dashboard_service.get_asset_detailed_performance(
        current_user.id, asset_name, start_datetime, end_datetime
    )
    return detailed_data

@app.get("/api/dashboard/assets/{asset_name}/webhooks")
def get_asset_webhook_executions(
    asset_name: str,
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(10, ge=1, le=100, description="Itens por página"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém execuções de webhooks paginadas para um ativo específico"""
    
    # Calcular offset
    offset = (page - 1) * limit
    
    # Buscar trades com paginação
    trades = db.query(WebhookTrade).filter(
        and_(
            WebhookTrade.user_id == current_user.id,
            WebhookTrade.asset_name == asset_name
        )
    ).order_by(desc(WebhookTrade.timestamp)).offset(offset).limit(limit).all()
    
    # Contar total de trades
    total_count = db.query(WebhookTrade).filter(
        and_(
            WebhookTrade.user_id == current_user.id,
            WebhookTrade.asset_name == asset_name
        )
    ).count()
    
    # Calcular informações de paginação
    total_pages = (total_count + limit - 1) // limit
    has_next = page < total_pages
    has_prev = page > 1
    
    return {
        "webhooks": [
            {
                "id": trade.id,
                "asset_name": trade.asset_name,
                "trade_type": trade.trade_type,
                "side": trade.side,
                "quantity": trade.quantity,
                "price": trade.price,
                "usd_value": trade.usd_value,
                "leverage": trade.leverage,
                "fees": trade.fees,
                "timestamp": trade.timestamp.isoformat(),
                "order_id": trade.order_id,
                "webhook_config_id": trade.webhook_config_id
            }
            for trade in trades
        ],
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "total_items": total_count,
            "items_per_page": limit,
            "has_next": has_next,
            "has_prev": has_prev
        }
    }

@app.get("/api/dashboard/webhooks/{webhook_id}")
def get_webhook_execution_details(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém detalhes completos de uma execução de webhook específica"""
    
    # Buscar o trade
    trade = db.query(WebhookTrade).filter(
        and_(
            WebhookTrade.id == webhook_id,
            WebhookTrade.user_id == current_user.id
        )
    ).first()
    
    if not trade:
        raise HTTPException(status_code=404, detail="Webhook execution not found")
    
    # Buscar configuração do webhook
    webhook_config = db.query(WebhookConfig).filter(
        WebhookConfig.id == trade.webhook_config_id
    ).first()
    
    # Buscar posição relacionada (se existir)
    position = db.query(WebhookPosition).filter(
        and_(
            WebhookPosition.webhook_config_id == trade.webhook_config_id,
            WebhookPosition.user_id == trade.user_id,
            WebhookPosition.asset_name == trade.asset_name
        )
    ).order_by(desc(WebhookPosition.opened_at)).first()
    
    return {
        "webhook_execution": {
            "id": trade.id,
            "asset_name": trade.asset_name,
            "trade_type": trade.trade_type,
            "side": trade.side,
            "quantity": trade.quantity,
            "price": trade.price,
            "usd_value": trade.usd_value,
            "leverage": trade.leverage,
            "fees": trade.fees,
            "timestamp": trade.timestamp.isoformat(),
            "order_id": trade.order_id
        },
        "webhook_config": {
            "id": webhook_config.id if webhook_config else None,
            "asset_name": webhook_config.asset_name if webhook_config else "Unknown",
            "max_usd_value": webhook_config.max_usd_value if webhook_config else 0,
            "leverage": webhook_config.leverage if webhook_config else 1,
            "is_live_trading": webhook_config.is_live_trading if webhook_config else False,
            "hyperliquid_symbol": webhook_config.hyperliquid_symbol if webhook_config else None
        } if webhook_config else None,
        "position": {
            "id": position.id if position else None,
            "side": position.side if position else None,
            "quantity": position.quantity if position else 0,
            "avg_entry_price": position.avg_entry_price if position else 0,
            "realized_pnl": position.realized_pnl if position else 0,
            "unrealized_pnl": position.unrealized_pnl if position else 0,
            "is_open": position.is_open if position else False,
            "opened_at": position.opened_at.isoformat() if position and position.opened_at else None,
            "closed_at": position.closed_at.isoformat() if position and position.closed_at else None
        } if position else None
    }

@app.post("/api/dashboard/pnl-period")
def get_pnl_by_period(
    period_request: PnlPeriodRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém PNL por período específico"""
    from pnl_calculator import PnlCalculator
    pnl_calculator = PnlCalculator(db)
    
    start_datetime = datetime.combine(period_request.start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_datetime = datetime.combine(period_request.end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
    
    period_pnl = pnl_calculator.get_pnl_by_period(current_user.id, start_datetime, end_datetime)
    return period_pnl

@app.get("/api/dashboard/trades", response_model=List[WebhookTradeResponse])
def get_user_trades(
    limit: int = 50,
    offset: int = 0,
    asset_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém histórico de trades do usuário"""
    filters = [WebhookTrade.user_id == current_user.id]
    
    if asset_name:
        filters.append(WebhookTrade.asset_name == asset_name)
    
    trades = db.query(WebhookTrade).filter(
        and_(*filters)
    ).order_by(desc(WebhookTrade.timestamp)).offset(offset).limit(limit).all()
    
    return [
        WebhookTradeResponse(
            id=trade.id,
            webhook_config_id=trade.webhook_config_id,
            user_id=trade.user_id,
            asset_name=trade.asset_name,
            trade_type=trade.trade_type,
            side=trade.side,
            quantity=trade.quantity,
            price=trade.price,
            usd_value=trade.usd_value,
            leverage=trade.leverage,
            order_id=trade.order_id,
            fees=trade.fees,
            timestamp=trade.timestamp
        )
        for trade in trades
    ]

@app.get("/api/dashboard/positions", response_model=List[WebhookPositionResponse])
def get_user_positions(
    only_open: bool = True,
    asset_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém posições do usuário"""
    filters = [WebhookPosition.user_id == current_user.id]
    
    if only_open:
        filters.append(WebhookPosition.is_open == True)
    
    if asset_name:
        filters.append(WebhookPosition.asset_name == asset_name)
    
    positions = db.query(WebhookPosition).filter(
        and_(*filters)
    ).order_by(desc(WebhookPosition.last_updated)).all()
    
    return [
        WebhookPositionResponse(
            id=position.id,
            webhook_config_id=position.webhook_config_id,
            user_id=position.user_id,
            asset_name=position.asset_name,
            side=position.side,
            quantity=position.quantity,
            avg_entry_price=position.avg_entry_price,
            current_price=position.current_price,
            leverage=position.leverage,
            realized_pnl=position.realized_pnl,
            unrealized_pnl=position.unrealized_pnl,
            total_fees=position.total_fees,
            is_open=position.is_open,
            opened_at=position.opened_at,
            closed_at=position.closed_at,
            last_updated=position.last_updated
        )
        for position in positions
    ]

@app.post("/api/dashboard/update-prices")
def update_unrealized_pnl(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Atualiza PNL não realizado de todas as posições abertas"""
    try:
        if not current_user.wallet or not current_user.wallet.public_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Endereço público da carteira não configurado"
            )
        
        client = HyperliquidClient()
        pnl_calculator = PnlCalculator(db)
        
        pnl_calculator.update_unrealized_pnl(current_user.id, client)
        
        return {"message": "PNL não realizado atualizado com sucesso"}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar PNL: {str(e)}"
        )

@app.post("/api/dashboard/snapshot")
def create_account_snapshot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cria um snapshot da conta"""
    try:
        if not current_user.wallet or not current_user.wallet.public_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Endereço público da carteira não configurado"
            )
        
        client = HyperliquidClient()
        from dashboard_service import DashboardService
        dashboard_service = DashboardService(db)
        
        snapshot = dashboard_service.update_account_snapshot(current_user.id, client)
        
        if snapshot:
            return {
                "message": "Snapshot criado com sucesso",
                "snapshot": AccountSnapshotResponse(
                    id=snapshot.id,
                    user_id=snapshot.user_id,
                    account_balance=snapshot.account_balance,
                    total_realized_pnl=snapshot.total_realized_pnl,
                    total_unrealized_pnl=snapshot.total_unrealized_pnl,
                    net_pnl=snapshot.net_pnl,
                    total_fees=snapshot.total_fees,
                    timestamp=snapshot.timestamp
                )
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao criar snapshot"
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar snapshot: {str(e)}"
        )

@app.get("/api/dashboard/snapshots", response_model=List[AccountSnapshotResponse])
def get_account_snapshots(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém snapshots da conta"""
    from dashboard_service import DashboardService
    dashboard_service = DashboardService(db)
    
    start_datetime = None
    end_datetime = None
    
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
    
    snapshots = dashboard_service.get_account_snapshots(
        current_user.id, start_datetime, end_datetime, limit
    )
    
    return [
        AccountSnapshotResponse(
            id=snapshot.id,
            user_id=snapshot.user_id,
            account_balance=snapshot.account_balance,
            total_realized_pnl=snapshot.total_realized_pnl,
            total_unrealized_pnl=snapshot.total_unrealized_pnl,
            net_pnl=snapshot.net_pnl,
            total_fees=snapshot.total_fees,
            timestamp=snapshot.timestamp
        )
        for snapshot in snapshots
    ]

# --- Health Check ---
@app.get("/health")
async def health_check():
    """Health check endpoint for Docker/Fly.io monitoring"""
    try:
        # Test database connection
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "hyperliquid-trader-api",
            "database": "connected"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "hyperliquid-trader-api",
                "database": "disconnected",
                "error": str(e)
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)

