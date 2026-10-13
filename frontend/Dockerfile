# ── Stage 1: Build ───────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# ── Stage 2: Production ─────────────────────────────────────────────────────
FROM node:20-alpine

WORKDIR /app

# Runtime dependencies only; build tooling stays in the builder stage
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev && npm cache clean --force

COPY --from=builder /app/dist ./dist

ENV HOST=0.0.0.0
ENV PORT=3000

# The node image ships an unprivileged "node" user
USER node

EXPOSE 3000

CMD ["node", "./dist/server/entry.mjs"]
