# Multi-stage build for Transcendent AI System
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --only=production

COPY frontend/ ./
RUN npm run build

# Python backend stage
FROM python:3.11-slim AS backend

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY practical_ai_system.py .
COPY cursor_mcp_integration.py .
COPY web_backend.py .

# Copy built frontend
COPY --from=frontend-builder /app/frontend/build ./static

# Create non-root user
RUN useradd -m -u 1000 aiuser && chown -R aiuser:aiuser /app
USER aiuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["python", "web_backend.py"]
