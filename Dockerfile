# Unified Dockerfile for LeetLoop (API + Web)
# Build from monorepo root: docker build -t leetloop .

# ====================
# Stage 1: Build Next.js web app
# ====================
FROM node:20-alpine AS web-builder

WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy monorepo config
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

# Copy workspace packages
COPY clients/web ./clients/web
COPY packages ./packages

# Install dependencies
RUN pnpm install --frozen-lockfile

# Build web client with standalone output
ENV BUILD_STANDALONE=true
ENV NEXT_TELEMETRY_DISABLED=1

RUN pnpm --filter @leetloop/web build

# ====================
# Stage 2: Build Python API dependencies
# ====================
FROM python:3.11-slim AS api-builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ====================
# Stage 3: Final runtime image
# ====================
FROM python:3.11-slim

WORKDIR /app

# Install Node.js and supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    supervisor \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from api-builder
COPY --from=api-builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy API code
COPY api /app/api

# Copy built Next.js app (standalone preserves monorepo structure)
COPY --from=web-builder /app/clients/web/.next/standalone /app/web
COPY --from=web-builder /app/clients/web/.next/static /app/web/clients/web/.next/static
COPY --from=web-builder /app/clients/web/public /app/web/clients/web/public

# Create supervisor config
RUN mkdir -p /var/log/supervisor
COPY <<EOF /etc/supervisor/conf.d/leetloop.conf
[supervisord]
nodaemon=true
user=root

[program:api]
command=gunicorn -c gunicorn_conf.py app.main:app
directory=/app/api
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:web]
command=node server.js
directory=/app/web/clients/web
environment=NODE_ENV="production",PORT="3001",HOSTNAME="0.0.0.0"
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
EOF

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Expose ports
EXPOSE 3001 8080

# Health check for API
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health && curl -f http://localhost:3001 || exit 1

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
