# --- Stage 1: build the static Next.js export ---
FROM node:22-bookworm-slim AS frontend

WORKDIR /frontend

# Install deps first for layer caching.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build
# Produces /frontend/out (output: "export").

# --- Stage 2: FastAPI runtime ---
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

# Install Python dependencies first for layer caching.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

# Application code, and the exported frontend served at /.
COPY backend/app ./app
COPY --from=frontend /frontend/out ./static

EXPOSE 8000

CMD ["uv", "run", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
