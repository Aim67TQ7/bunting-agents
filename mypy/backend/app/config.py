"""Service registry and configuration for MYPY Orchestrator."""
import os
from typing import List, Dict, Any

# VPS Configuration
VPS_HOST = os.getenv("VPS_HOST", "localhost")

# Registered services on the VPS
SERVICES: List[Dict[str, Any]] = [
    {
        "id": "customer-name-cleansing",
        "name": "Customer Name Cleansing",
        "description": "ERP data standardization for AI readiness",
        "port": 8001,
        "health_endpoint": "/health",
        "docs_endpoint": None,  # No Swagger UI
    },
    {
        "id": "contract-intelligence",
        "name": "Contract Intelligence",
        "description": "Legal document analysis and risk extraction",
        "port": 8002,
        "health_endpoint": "/health",
        "docs_endpoint": None,
    },
    {
        "id": "nfl-intelligence",
        "name": "NFL Intelligence Agent",
        "description": "NFL data analysis and insights",
        "port": 8003,
        "health_endpoint": "/health",
        "docs_endpoint": None,
    },
]

# CORS origins for frontend
CORS_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",
    "https://mypy-dashboard.netlify.app",  # Production Netlify
    os.getenv("FRONTEND_URL", ""),
]

# Filter empty strings
CORS_ORIGINS = [origin for origin in CORS_ORIGINS if origin]
