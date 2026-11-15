# ==============================================================================
# Multi-stage Dockerfile for React TypeScript Frontend
# ==============================================================================

# Stage 1: Build production static bundle
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies using clean install
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code and build config
COPY . .
RUN npm run build

# Stage 2: High-performance Nginx web server
FROM nginx:alpine AS runner

# Copy compiled static HTML/CSS/JS assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration with API reverse proxy & SSE streaming support
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
