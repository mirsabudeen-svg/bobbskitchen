FROM node:20-slim AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# VITE_API_BASE_URL is baked into the static bundle at build time.
# Pass via --build-arg in docker-compose or override per-environment.
ARG VITE_API_BASE_URL=http://192.168.1.10:8420
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

FROM node:20-slim

WORKDIR /app
RUN npm install -g serve@14

COPY --from=builder /app/dist ./dist

EXPOSE 3000

CMD ["serve", "-s", "dist", "-l", "3000"]
