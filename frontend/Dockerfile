# Build stage
FROM node:18-alpine AS builder

# Configurações de ambiente para build
ENV NODE_ENV=production
ENV CI=true

WORKDIR /app

# Copiar package files para cache de dependências
COPY package*.json ./

# Instalar dependências
RUN npm install --production

# Copiar código fonte
COPY . .

# Build arguments para configuração
ARG REACT_APP_API_URL
ENV REACT_APP_API_URL=$REACT_APP_API_URL

# Build da aplicação React
RUN npm run build

# Production stage - servir com nginx
FROM nginx:alpine

# Instalar curl para health checks
RUN apk --no-cache add curl

# Copiar configuração customizada do nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copiar build da aplicação React
COPY --from=builder /app/build /usr/share/nginx/html

# Criar usuário não-root
RUN addgroup -g 1001 -S nginx-user && \
    adduser -S nginx-user -G nginx-user

# Ajustar permissões para nginx não-root
RUN chown -R nginx-user:nginx-user /usr/share/nginx/html && \
    chown -R nginx-user:nginx-user /var/cache/nginx && \
    chown -R nginx-user:nginx-user /var/log/nginx && \
    chown -R nginx-user:nginx-user /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R nginx-user:nginx-user /var/run/nginx.pid && \
    # Substituir configuração nginx para escutar na porta não-privilegiada
    sed -i 's/listen 80/listen 8080/' /etc/nginx/conf.d/default.conf

# Mudar para usuário não-root
USER nginx-user

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expor porta
EXPOSE 8080

# Comando para iniciar nginx
CMD ["nginx", "-g", "daemon off;"] 