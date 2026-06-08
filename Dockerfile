# Stage 1: build the React frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend — serves everything
FROM python:3.13-slim AS final
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app

# Copy the built frontend so FastAPI can serve it as static files
COPY --from=frontend-builder /app/frontend/dist ./static

# Persistent data lives here — mount a Railway volume at /app/data
RUN mkdir -p data/stats_cache

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
