# --- Build Stage 1: Build Frontend ---
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps
COPY frontend/ ./
# We set this to blank so that the frontend uses relative paths (/api) 
# instead of hardcoding localhost:8000
ENV VITE_API_URL=/api
RUN npm run build

# --- Build Stage 2: Backend + Final Image ---
FROM python:3.11-slim
WORKDIR /app

# Install dependencies for Google SDK (some libs might need it)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Ensure gunicorn and GCP libs are present
RUN pip install --no-cache-dir gunicorn google-cloud-secret-manager google-cloud-storage

# Copy backend code
COPY backend/ ./backend/
# config.yaml is handled by Secret Manager in production

# Copy static frontend build from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./static

# Ensure data directory exists for persistence
RUN mkdir -p data/

# Container environment
ENV PORT=8080
ENV ENABLE_GCP_SECRETS=true
ENV PYTHONUNBUFFERED=1

# Run the app. 
# We use uvicorn with gunicorn for production.
# The static files are served via FastAPI's StaticFiles.
CMD exec gunicorn --bind :$PORT --workers 1 --worker-class uvicorn.workers.UvicornWorker  --threads 8 backend.main:app
