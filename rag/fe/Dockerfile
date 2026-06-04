# syntax=docker/dockerfile:1.7

FROM oven/bun:1-alpine AS builder

ARG VITE_RAG_API_BASE_URL=http://127.0.0.1:8010
ARG VITE_RAG_API_TIMEOUT_MS=1500
ARG VITE_RAG_ENABLE_MOCK_FALLBACK=false
ARG VITE_MEMGRAPH_LAB_URL=http://127.0.0.1:3000

ENV VITE_RAG_API_BASE_URL=$VITE_RAG_API_BASE_URL \
    VITE_RAG_API_TIMEOUT_MS=$VITE_RAG_API_TIMEOUT_MS \
    VITE_RAG_ENABLE_MOCK_FALLBACK=$VITE_RAG_ENABLE_MOCK_FALLBACK \
    VITE_MEMGRAPH_LAB_URL=$VITE_MEMGRAPH_LAB_URL

WORKDIR /app

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY . .
RUN bun run build

FROM nginx:1.27-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=5 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
