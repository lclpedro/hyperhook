#!/bin/bash

# Script de deploy para HyperHook no Fly.io
# Uso: ./deploy.sh [backend|frontend|all]

set -e

echo "🚀 HyperHook Deploy Script"
echo "=========================="

# Função para deploy do backend
deploy_backend() {
    echo "📦 Deploying Backend..."
    
    echo "✅ Checking backend health endpoint..."
    if ! grep -q "/health" backend/app.py; then
        echo "❌ Health endpoint not found in backend/app.py"
        exit 1
    fi
    
    echo "🚀 Deploying to Fly.io..."
    fly deploy
    
    echo "🔍 Checking deployment..."
    sleep 10
    if curl -f https://hyperhook.fly.dev/health > /dev/null 2>&1; then
        echo "✅ Backend deployed successfully!"
        echo "🌐 URL: https://hyperhook.fly.dev"
    else
        echo "⚠️  Backend deployed but health check failed"
        echo "📊 Check logs: fly logs -a hyperhook"
    fi
}

# Função para deploy do frontend
deploy_frontend() {
    echo "🎨 Deploying Frontend..."
    cd frontend/ || exit 1
    
    echo "✅ Testing React build..."
    npm run build > /dev/null
    
    echo "🚀 Deploying to Fly.io..."
    fly deploy
    
    echo "🔍 Checking deployment..."
    sleep 10
    if curl -f https://hyperhook-frontend.fly.dev/health > /dev/null 2>&1; then
        echo "✅ Frontend deployed successfully!"
        echo "🌐 URL: https://hyperhook-frontend.fly.dev"
    else
        echo "⚠️  Frontend deployed but health check failed"
        echo "📊 Check logs: fly logs -a hyperhook-frontend"
    fi
    
    cd ..
}

# Verificar se fly CLI está instalado
if ! command -v fly &> /dev/null; then
    echo "❌ Fly CLI not found. Install it first:"
    echo "   macOS: brew install flyctl"
    echo "   Other: curl -L https://fly.io/install.sh | sh"
    exit 1
fi

# Verificar se está logado
if ! fly auth whoami &> /dev/null; then
    echo "❌ Not logged in to Fly.io"
    echo "Run: fly auth login"
    exit 1
fi

case "${1:-all}" in
    "backend")
        deploy_backend
        ;;
    "frontend")
        deploy_frontend
        ;;
    "all")
        deploy_backend
        echo ""
        deploy_frontend
        echo ""
        echo "🎉 Deploy completo!"
        echo "📱 Frontend: https://hyperhook-frontend.fly.dev"
        echo "🔧 Backend:  https://hyperhook.fly.dev"
        ;;
    *)
        echo "❌ Uso: $0 [backend|frontend|all]"
        exit 1
        ;;
esac

echo "✨ Deploy finalizado!" 