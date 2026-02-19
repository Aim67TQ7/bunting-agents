"""MYPY Orchestrator API - Service health monitoring and workflow execution."""
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .routers import health

app = FastAPI(
    title="MYPY Orchestrator",
    description="Service monitoring and workflow orchestration for VPS deployments",
    version="1.0.0",
    docs_url=None,  # Disable Swagger UI
    redoc_url=None,  # Disable ReDoc
    openapi_url=None,  # Disable OpenAPI schema
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)


@app.get("/health")
async def orchestrator_health():
    """Health check for the orchestrator itself."""
    return {
        "status": "healthy",
        "service": "mypy-orchestrator",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "MYPY Orchestrator API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "services": "/api/v1/services",
            "service_health": "/api/v1/services/{port}/health",
            "service_metrics": "/api/v1/services/{port}/metrics",
        },
    }
