from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import CORS_CONFIG
from infrastructure.database import Base, engine
from presentation.routes import (
    auth_routes,
    user_routes,
    wallet_routes,
    trading_routes,
    webhook_routes,
    pnl_routes
)

# Criar tabelas do banco de dados
Base.metadata.create_all(bind=engine)

# Inicializar FastAPI
app = FastAPI(
    title="HyperHook API",
    version="2.0.0",
    description="API refatorada com arquitetura limpa para automação de trading na Hyperliquid"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    **CORS_CONFIG
)

# Registrar rotas
app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(wallet_routes.router)
app.include_router(trading_routes.router)
app.include_router(webhook_routes.router)
app.include_router(pnl_routes.router)

@app.get("/")
def root():
    return {
        "message": "HyperHook API v2.0 - Arquitetura Limpa",
        "status": "online",
        "version": "2.0.0"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)