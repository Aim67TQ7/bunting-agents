"""Health check and service monitoring endpoints."""
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import SERVICES, VPS_HOST

router = APIRouter(prefix="/api/v1", tags=["services"])

# In-memory metrics (reset on restart - could persist to Redis later)
service_metrics: Dict[str, Dict[str, Any]] = {}


class ServiceStatus(BaseModel):
    id: str
    name: str
    description: str
    port: int
    status: str  # "healthy", "unhealthy", "unknown"
    response_time_ms: Optional[float] = None
    last_checked: str
    error: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


class ServiceListResponse(BaseModel):
    services: List[ServiceStatus]
    orchestrator_status: str
    timestamp: str


async def check_service_health(service: Dict[str, Any]) -> ServiceStatus:
    """Check health of a single service."""
    service_id = service["id"]
    url = f"http://{VPS_HOST}:{service['port']}{service['health_endpoint']}"

    start_time = datetime.now(timezone.utc)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            if response.status_code == 200:
                # Update metrics
                if service_id not in service_metrics:
                    service_metrics[service_id] = {
                        "total_checks": 0,
                        "successful_checks": 0,
                        "total_response_time_ms": 0,
                    }

                service_metrics[service_id]["total_checks"] += 1
                service_metrics[service_id]["successful_checks"] += 1
                service_metrics[service_id]["total_response_time_ms"] += response_time

                return ServiceStatus(
                    id=service_id,
                    name=service["name"],
                    description=service["description"],
                    port=service["port"],
                    status="healthy",
                    response_time_ms=round(response_time, 2),
                    last_checked=datetime.now(timezone.utc).isoformat(),
                    metrics=_get_service_metrics(service_id),
                )
            else:
                return ServiceStatus(
                    id=service_id,
                    name=service["name"],
                    description=service["description"],
                    port=service["port"],
                    status="unhealthy",
                    last_checked=datetime.now(timezone.utc).isoformat(),
                    error=f"HTTP {response.status_code}",
                )
    except httpx.TimeoutException:
        return ServiceStatus(
            id=service_id,
            name=service["name"],
            description=service["description"],
            port=service["port"],
            status="unhealthy",
            last_checked=datetime.now(timezone.utc).isoformat(),
            error="Connection timeout",
        )
    except httpx.ConnectError:
        return ServiceStatus(
            id=service_id,
            name=service["name"],
            description=service["description"],
            port=service["port"],
            status="unhealthy",
            last_checked=datetime.now(timezone.utc).isoformat(),
            error="Connection refused",
        )
    except Exception as e:
        return ServiceStatus(
            id=service_id,
            name=service["name"],
            description=service["description"],
            port=service["port"],
            status="unknown",
            last_checked=datetime.now(timezone.utc).isoformat(),
            error=str(e),
        )


def _get_service_metrics(service_id: str) -> Dict[str, Any]:
    """Calculate metrics for a service."""
    if service_id not in service_metrics:
        return {"uptime_percent": 0, "avg_response_ms": 0, "total_checks": 0}

    m = service_metrics[service_id]
    uptime = (m["successful_checks"] / m["total_checks"] * 100) if m["total_checks"] > 0 else 0
    avg_response = (m["total_response_time_ms"] / m["successful_checks"]) if m["successful_checks"] > 0 else 0

    return {
        "uptime_percent": round(uptime, 1),
        "avg_response_ms": round(avg_response, 2),
        "total_checks": m["total_checks"],
    }


@router.get("/services", response_model=ServiceListResponse)
async def get_all_services():
    """Get status of all registered services."""
    tasks = [check_service_health(service) for service in SERVICES]
    results = await asyncio.gather(*tasks)

    return ServiceListResponse(
        services=results,
        orchestrator_status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/services/{port}/health", response_model=ServiceStatus)
async def get_service_health(port: int):
    """Get health status of a specific service by port."""
    service = next((s for s in SERVICES if s["port"] == port), None)
    if not service:
        raise HTTPException(status_code=404, detail=f"No service registered on port {port}")

    return await check_service_health(service)


@router.get("/services/{port}/metrics")
async def get_service_metrics(port: int):
    """Get metrics for a specific service."""
    service = next((s for s in SERVICES if s["port"] == port), None)
    if not service:
        raise HTTPException(status_code=404, detail=f"No service registered on port {port}")

    return {
        "service_id": service["id"],
        "service_name": service["name"],
        "port": port,
        "metrics": _get_service_metrics(service["id"]),
    }
