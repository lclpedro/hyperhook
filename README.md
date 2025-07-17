# HyperHook - Sistema de Trading Inteligente

Sistema completo de trading automatizado para Hyperliquid com análise inteligente de posições e interface web.

## 🚀 Deploy Rápido no Fly.io

```bash
# Deploy completo (backend + frontend)
./deploy.sh

# URLs após deploy:
# Frontend: https://hyperhook-frontend.fly.dev
# Backend:  https://hyperhook.fly.dev
```

## 🏗️ Arquitetura

### Backend (FastAPI + PostgreSQL)
- **API REST** para gerenciamento de usuários e webhooks
- **Sistema de Trading Inteligente** com análise automática de posições
- **Integração Hyperliquid** via SDK oficial
- **Autenticação JWT** com criptografia de chaves privadas
- **Logs de auditoria** completos

### Frontend (React + Tailwind)
- **Interface moderna** e responsiva
- **Gestão de carteira** Hyperliquid
- **Configuração de webhooks** com UUID único
- **Visualização de logs** em tempo real
- **Dashboard de posições**

## 🔧 Funcionalidades

### Trading Inteligente
- ✅ **Análise automática** de posições existentes
- ✅ **Fechamento inteligente** (detecta posições opostas)
- ✅ **DCA automático** (aumenta posições na mesma direção)
- ✅ **Redução de posições** com cálculo automático
- ✅ **Orders de mercado** forçadas para fechamentos
- ✅ **Validação de preços** (máx 5% do preço de mercado)

### Sistema de Webhooks
- ✅ **Endpoint único** `/v1/webhook` para todos os assets
- ✅ **Roteamento automático** por usuário e asset
- ✅ **Análise pré-trade** com 4 cenários
- ✅ **Comentários automáticos** com tipo de operação
- ✅ **Logs detalhados** para auditoria

### Segurança
- ✅ **Autenticação JWT** com tokens seguros
- ✅ **Criptografia Fernet** para chaves privadas
- ✅ **Usuários não-root** nos containers
- ✅ **CORS configurado** para produção
- ✅ **Health checks** automáticos

## 📱 URLs de Produção

| Serviço | URL | Health Check |
|---------|-----|--------------|
| Frontend | https://hyperhook-frontend.fly.dev | `/health` |
| Backend | https://hyperhook.fly.dev | `/health` |
| Webhook | https://hyperhook.fly.dev/v1/webhook | N/A |

## 🛠️ Desenvolvimento Local

### Backend
```bash
cd backend/
python -m venv env
source env/bin/activate
pip install -r requirements.txt

# Configurar PostgreSQL local ou usar SQLite
export DATABASE_URL="postgresql://user:pass@localhost:5432/hyperliquid_trader"

python app.py
```

### Frontend
```bash
cd frontend/
npm install

# Configurar API URL
echo "REACT_APP_API_URL=http://127.0.0.1:5001" > .env.local

npm start
```

## 🐳 Docker Local

```bash
# Backend
cd backend/
docker build -t hyperhook-backend .
docker run -p 5001:5001 hyperhook-backend

# Frontend
cd frontend/
docker build -t hyperhook-frontend --build-arg REACT_APP_API_URL=http://localhost:5001 .
docker run -p 3000:8080 hyperhook-frontend
```

## 🔐 Configuração de Produção

### Secrets Necessários (Fly.io)

```bash
# JWT Secret
fly secrets set JWT_SECRET_KEY="$(openssl rand -base64 32)" -a hyperhook

# Chave de criptografia
fly secrets set ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" -a hyperhook

# Database (PostgreSQL no Fly.io)
fly postgres create --name hyperhook-db --region gig
fly postgres attach --app hyperhook hyperhook-db
```

### Variáveis de Ambiente

#### Backend
- `DATABASE_URL`: Connection string PostgreSQL
- `JWT_SECRET_KEY`: Chave para tokens JWT
- `ENCRYPTION_KEY`: Chave Fernet para criptografia

#### Frontend
- `REACT_APP_API_URL`: URL da API backend

## 📊 Monitoramento

### Health Checks
```bash
# Backend
curl https://hyperhook.fly.dev/health

# Frontend  
curl https://hyperhook-frontend.fly.dev/health
```

### Logs
```bash
# Backend logs
fly logs -a hyperhook

# Frontend logs
fly logs -a hyperhook-frontend
```

### Métricas
- **Uptime**: Monitorado via health checks
- **Performance**: Logs de resposta HTTP
- **Errors**: Capturados em logs de aplicação
- **Trading**: Auditoria completa no database

## 🔧 Configuração TradingView

1. **Criar webhook** na interface web
2. **Copiar URL** gerada (formato UUID)
3. **Configurar no TradingView:**
   ```
   URL: https://hyperhook.fly.dev/v1/webhook
   Payload: {
     "user_uuid": "seu-uuid-aqui",
     "asset_name": "{{ticker}}",
     "direction": "{{strategy.order.action}}",
     "position_size": {{strategy.position_size}},
     "price": {{close}}
   }
   ```

## 📈 Cenários de Trading

| Cenário | Condição | Ação |
|---------|----------|------|
| **NEW_POSITION** | Sem posição atual | Abre nova posição |
| **FECHAMENTO** | Direção oposta + position_size=0 | Market order para fechar |
| **DCA** | Mesma direção | Aumenta posição |
| **REDUCAO** | Direção oposta + position_size>0 | Market order para reduzir |

## 🛡️ Backup e Recuperação

### Database Backup
```bash
fly postgres connect -a hyperhook-db
pg_dump hyperliquid_trader > backup.sql
```

### Restore
```bash
fly postgres connect -a hyperhook-db
psql hyperliquid_trader < backup.sql
```

## 📞 Suporte

- **Logs de erro**: Capturados automaticamente
- **Health checks**: Monitoramento contínuo  
- **Auditoria**: Todos os trades registrados
- **Fallbacks**: Orders de mercado para garantir execução

---

**Desenvolvido com ❤️ para trading automatizado seguro e inteligente** 