#!/bin/bash
# MYPY Orchestrator Deployment Script
# Run this on VPS: 89.116.157.23

set -e

echo "==> Deploying MYPY Orchestrator..."

# Navigate to deployment directory
cd /opt/mypy-orchestrator || mkdir -p /opt/mypy-orchestrator && cd /opt/mypy-orchestrator

# Pull latest code (or copy files)
echo "==> Copying backend files..."

# Build and start container
echo "==> Building Docker container..."
docker-compose down --remove-orphans || true
docker-compose build --no-cache
docker-compose up -d

# Verify deployment
echo "==> Waiting for service to start..."
sleep 5

if curl -s http://localhost:8010/health | grep -q "healthy"; then
    echo "==> MYPY Orchestrator deployed successfully!"
    echo "==> Health endpoint: http://89.116.157.23:8010/health"
    echo "==> Services endpoint: http://89.116.157.23:8010/api/v1/services"
else
    echo "==> Warning: Health check failed. Check logs with: docker logs mypy-orchestrator"
fi
