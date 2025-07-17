# --- backend/app.py ---
# Instale as dependências: pip install fastapi uvicorn sqlalchemy databases python-jose[cryptography] passlib[bcrypt] python-multipart cryptography hyperliquid-python-sdk eth-account
import os
import uuid
import json
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from cryptography.fernet import Fernet
from typing import Optional, List
from sqlalchemy.ext.declarative import declarative_base
from hyperliquid_client import HyperliquidClient

# --- Configuração Inicial ---
app = FastAPI(title="Hyperliquid Trader API", version="1.1.0")

origins = [
    "http://localhost:3000",  # A origem do seu frontend React local
    "http://127.0.0.1:3000", # Outra forma de aceder ao localhost
    "https://hyperhook.fly.dev",  # Backend deployado no Fly.io
    "https://hyperhook-frontend.fly.dev",  # Frontend deployado no Fly.io (nome planejado)
    "https://frontend-morning-resonance-9520.fly.dev",  # Frontend atual deployado
    # IPs do Fly.io para comunicação interna
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

def check_tables_exist():
    """Verifica se as tabelas já existem no banco de dados"""
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        expected_tables = ['user', 'wallet', 'webhook_config', 'webhook_log']
        return all(table in tables for table in expected_tables)
    except Exception as e:
        print(f"Erro ao verificar tabelas: {e}")
        return False

def create_tables_if_needed():
    """Cria as tabelas apenas se elas não existirem"""
    if not check_tables_exist():
        print("📝 Criando tabelas do banco de dados...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tabelas criadas com sucesso!")
    else:
        print("✅ Tabelas já existem - não há necessidade de criar novamente")

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
    maxUsdValue: float
    leverage: int = 1  # NOVO: Leverage configurável
    isLiveTrading: bool = False  # NOVO: Flag para trading real

class WebhookResponse(BaseModel):
    id: int
    assetName: str
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

# --- Dependências e Funções Utilitárias ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

def analyze_trade_intent(client, user_address, asset_name, action, position_size_str, contracts_str):
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
        current_position = current_positions.get(asset_name)
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
                print(f"🔄 FECHAMENTO: Fechando posição {current_side} de {close_size} {asset_name}")
                return "FECHAMENTO", close_size, {
                    "description": f"Fechando posição {current_side} de {close_size}",
                    "current_position": current_position,
                    "action_type": "CLOSE_POSITION",
                    "original_size": current_position["abs_size"]
                }
        
        # Cenário 3: DCA - Mesma direção da posição existente
        current_side = current_position["side"]
        is_same_direction = (current_side == "LONG" and is_buy) or (current_side == "SHORT" and not is_buy)
        
        if is_same_direction:
            print(f"📊 DCA: Aumentando posição {current_side} existente de {current_position['abs_size']} com +{contracts}")
            return "DCA", contracts, {
                "description": f"DCA - Aumentando posição {current_side} de {current_position['abs_size']} para {current_position['abs_size'] + contracts}",
                "current_position": current_position,
                "action_type": "DCA",
                "original_size": current_position["abs_size"],
                "new_total_size": current_position["abs_size"] + contracts
            }
        
        # Cenário 4: REDUÇÃO DE POSIÇÃO - Direção oposta mas não position_size = 0
        if not is_same_direction:
            reduction_size = min(contracts, current_position["abs_size"])
            print(f"📉 REDUÇÃO: Reduzindo posição {current_side} de {current_position['abs_size']} em {reduction_size}")
            return "REDUCAO", reduction_size, {
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
        
        # 1. Prioridade: usar contracts do TradingView
        if contracts:
            try:
                order_size = float(contracts)
                print(f"Usando tamanho do TradingView: {order_size}")
            except (ValueError, TypeError):
                print(f"Erro ao converter contracts '{contracts}' para float")
        
        # 2. Fallback: calcular baseado no valor máximo configurado
        if order_size is None:
            order_size = client.calculate_order_size(asset_name, config.max_usd_value)
            print(f"Usando valor máximo configurado: {order_size} (baseado em ${config.max_usd_value})")
        
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
        leverage_to_use = config.leverage
        print(f"Usando leverage configurado: {leverage_to_use}x")
        
        result = client.place_order(
            secret_key=secret_key,
            asset_name=asset_name,
            is_buy=is_buy,
            size=order_size,
            limit_price=limit_price,
            stop_loss=None,  # Removido - não está no novo formato
            take_profit=None,  # Removido - não está no novo formato
            comment=user_info,  # Usando user_info como comentário
            is_live_trading=bool(config.is_live_trading)  # NOVO: Flag para trading real
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
                "symbol": symbol,
                "user_info": user_info
            }
        }
        
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
    config = db.query(WebhookConfig).filter(WebhookConfig.user_id == user.id, WebhookConfig.asset_name == asset_name).first()
    
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
        
        # NOVA FUNCIONALIDADE: Análise inteligente da intenção de trading
        print(f"\n🧠 ANALISANDO INTENÇÃO DE TRADING...")
        print(f"Action: {action}, Contracts: {contracts}, Position Size: {position_size}")
        
        try:
            # Analisar se é fechamento, DCA, nova posição, etc.
            trade_type, adjusted_size, trade_details = analyze_trade_intent(
                client=client,
                user_address=user.wallet.public_address,
                asset_name=asset_name,
                action=action,
                position_size_str=position_size,
                contracts_str=contracts
            )
            
            print(f"🎯 RESULTADO DA ANÁLISE:")
            print(f"  Tipo: {trade_type}")
            print(f"  Descrição: {trade_details['description']}")
            print(f"  Quantidade original: {contracts}")
            print(f"  Quantidade ajustada: {adjusted_size}")
            
        except Exception as analysis_error:
            print(f"⚠️ Erro na análise de trading: {analysis_error}")
            # Fallback para comportamento original
            trade_type = "ERRO"
            adjusted_size = float(contracts) if contracts else 0
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
                order_size = client.calculate_order_size(asset_name, max_usd_value)
                print(f"⚠️ Quantidade zero detectada - usando valor máximo configurado: {order_size} (baseado em ${max_usd_value})")
            else:
                raise ValueError("Quantidade da ordem é zero e não há valor máximo configurado")
        
        print(f"✅ TAMANHO FINAL DA ORDEM: {order_size}")
        
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
        leverage_to_use = config.leverage
        print(f"Usando leverage configurado: {leverage_to_use}x")
        print(f"Modo: {'🚀 REAL' if bool(config.is_live_trading) else '🔄 SIMULAÇÃO'}")
        
        result = client.place_order(
            secret_key=secret_key,
            asset_name=asset_name,
            is_buy=is_buy,
            size=order_size,
            limit_price=limit_price,
            stop_loss=None,
            take_profit=None,
            comment=f"{user_info} | {trade_type}: {trade_details['description']}",
            is_live_trading=bool(config.is_live_trading)
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
                "symbol": symbol,
                "user_info": user_info,
                "is_live_trading": bool(config.is_live_trading)
            },
            "trade_analysis": {
                "type": trade_type,
                "description": trade_details["description"],
                "original_contracts": contracts,
                "adjusted_size": order_size,
                "details": trade_details
            }
        }
        
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
            "timestamp": datetime.utcnow().isoformat(),
            "service": "hyperliquid-trader-api",
            "database": "connected"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "hyperliquid-trader-api",
                "database": "disconnected",
                "error": str(e)
            }
        )

if __name__ == "__main__":
    import uvicorn
    # Criar tabelas apenas se necessário (migrations condicionais)
    create_tables_if_needed()
    uvicorn.run(app, host="0.0.0.0", port=5001)

