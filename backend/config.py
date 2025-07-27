import os
from cryptography.fernet import Fernet

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'super-secret-jwt-key-for-dev-do-not-use-in-prod')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 semana

# Database Configuration
DB_CONNECTION_STRING = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/hyperliquid_trader')

# Fix para SQLAlchemy 2.x - converter postgres:// para postgresql://
if DB_CONNECTION_STRING.startswith('postgres://'):
    DB_CONNECTION_STRING = DB_CONNECTION_STRING.replace('postgres://', 'postgresql://', 1)

# CORS Configuration
CORS_ORIGINS = [
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

# Encryption Configuration
DEFAULT_ENCRYPTION_KEY = 'TvI0pq4KaZkYQ1Zd2J7xN8rU5gM3eW9nY6sL7hT4vC0='  # Chave fixa para desenvolvimento
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', DEFAULT_ENCRYPTION_KEY).encode()
cipher_suite = Fernet(ENCRYPTION_KEY)

# FastAPI Configuration
FASTAPI_CONFIG = {
    "title": "Hyperliquid Trader API",
    "version": "1.1.0"
}

# CORS Middleware Configuration
CORS_CONFIG = {
    "allow_origins": CORS_ORIGINS,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}