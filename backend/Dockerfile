FROM python:3.12-slim AS builder

# Configurações de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependências do sistema para build
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Criar virtual environment
RUN python -m venv .venv

# Copiar e instalar dependências
COPY backend/requirements.txt ./
RUN .venv/bin/pip install --no-cache-dir -r requirements.txt

# Stage final
FROM python:3.12-slim

# Instalar dependências runtime
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copiar virtual environment do builder
COPY --from=builder /app/.venv .venv/

# Copiar código do backend
COPY backend/ ./

# Criar diretório para dados e logs
RUN mkdir -p /app/instance /app/logs && \
    chown -R appuser:appuser /app

# Mudar para usuário não-root
USER appuser

# Configurar timezone
ENV TZ=America/Sao_Paulo

# Porta dinâmica do Fly.io
ENV PORT=5001

# Healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expor porta
EXPOSE ${PORT}

# Comando para iniciar a aplicação
CMD ["/bin/sh", "-c", "/app/.venv/bin/uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
