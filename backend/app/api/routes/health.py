"""
Health check API routes.

Provides endpoints for monitoring system health and readiness.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.core.neo4j_client import get_neo4j_client
from app.schema.loader import get_schema_loader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


class ServiceHealth(BaseModel):
    """Health status of a single service."""
    name: str
    status: str  # "healthy", "unhealthy", "degraded"
    message: Optional[str] = None
    latency_ms: Optional[float] = None


class HealthResponse(BaseModel):
    """Complete health check response."""
    status: str  # "healthy", "unhealthy", "degraded"
    timestamp: str
    version: str
    services: dict[str, ServiceHealth]
    schema: Optional[dict] = None


class ReadinessResponse(BaseModel):
    """Readiness check response."""
    ready: bool
    checks: dict[str, bool]


class LivenessResponse(BaseModel):
    """Liveness check response."""
    alive: bool
    timestamp: str


@router.get("", response_model=HealthResponse)
@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Comprehensive health check endpoint.
    
    Checks:
    - Neo4j database connectivity
    - Schema loader status
    - Overall system health
    
    Returns detailed status for monitoring dashboards.
    """
    services = {}
    overall_status = "healthy"
    
    # Check Neo4j
    neo4j_health = await _check_neo4j()
    services["neo4j"] = neo4j_health
    if neo4j_health.status != "healthy":
        overall_status = "degraded" if neo4j_health.status == "degraded" else "unhealthy"
    
    # Check Schema Loader
    schema_health = _check_schema()
    services["schema"] = schema_health
    if schema_health.status != "healthy":
        overall_status = "degraded"
    
    # Get schema info
    schema_info = None
    try:
        loader = get_schema_loader()
        schema = loader.get_active_schema()
        schema_info = {
            "name": schema.schema_info.name,
            "version": schema.schema_info.version,
            "entity_count": len(schema.entities),
            "relationship_count": len(schema.relationships),
        }
    except Exception:
        pass
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat() + "Z",
        version="0.1.0",
        services=services,
        schema=schema_info,
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check():
    """
    Kubernetes-style readiness probe.
    
    Returns whether the service is ready to accept traffic.
    Used by load balancers and orchestrators.
    """
    checks = {}
    
    # Neo4j must be connected
    neo4j_client = get_neo4j_client()
    try:
        neo4j_ready = await neo4j_client.health_check()
        checks["neo4j"] = neo4j_ready
    except Exception:
        checks["neo4j"] = False
    
    # Schema must be loadable
    try:
        loader = get_schema_loader()
        loader.get_active_schema()
        checks["schema"] = True
    except Exception:
        checks["schema"] = False
    
    ready = all(checks.values())
    
    return ReadinessResponse(
        ready=ready,
        checks=checks,
    )


@router.get("/live", response_model=LivenessResponse)
async def liveness_check():
    """
    Kubernetes-style liveness probe.
    
    Returns whether the service is alive (not deadlocked).
    If this fails, the container should be restarted.
    """
    return LivenessResponse(
        alive=True,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


@router.get("/neo4j")
async def neo4j_health():
    """Detailed Neo4j health check."""
    health = await _check_neo4j()
    
    # Get additional Neo4j info if healthy
    extra_info = {}
    if health.status == "healthy":
        try:
            client = get_neo4j_client()
            schema = await client.get_schema()
            extra_info["labels"] = schema.get("labels", [])
            extra_info["relationship_types"] = schema.get("relationship_types", [])
        except Exception:
            pass
    
    return {
        **health.model_dump(),
        **extra_info,
    }


@router.get("/config")
async def config_check():
    """
    Get non-sensitive configuration.
    
    Useful for debugging and verifying deployment configuration.
    """
    return {
        "neo4j_uri": settings.neo4j_uri,
        "active_schema": settings.active_schema,
        "default_llm_model": settings.default_llm_model,
        "extraction_model": settings.extraction_model,
        "rag_model": settings.rag_model,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "debug": settings.debug,
    }


@router.get("/schemas")
async def available_schemas():
    """List all available schemas."""
    try:
        loader = get_schema_loader()
        schemas = loader.list_available_schemas()
        active = settings.active_schema
        
        return {
            "active_schema": active,
            "available_schemas": schemas,
            "schemas_directory": str(loader.schemas_dir),
        }
    except Exception as e:
        return {
            "error": str(e),
            "available_schemas": [],
        }


async def _check_neo4j() -> ServiceHealth:
    """Check Neo4j health."""
    import time
    
    try:
        start = time.time()
        client = get_neo4j_client()
        healthy = await client.health_check()
        latency = (time.time() - start) * 1000
        
        if healthy:
            return ServiceHealth(
                name="neo4j",
                status="healthy",
                message="Connected",
                latency_ms=round(latency, 2),
            )
        else:
            return ServiceHealth(
                name="neo4j",
                status="unhealthy",
                message="Health check failed",
            )
    except Exception as e:
        return ServiceHealth(
            name="neo4j",
            status="unhealthy",
            message=str(e),
        )


def _check_schema() -> ServiceHealth:
    """Check schema loader health."""
    try:
        loader = get_schema_loader()
        schema = loader.get_active_schema()
        
        return ServiceHealth(
            name="schema",
            status="healthy",
            message=f"Active: {schema.schema_info.name} v{schema.schema_info.version}",
        )
    except FileNotFoundError as e:
        return ServiceHealth(
            name="schema",
            status="unhealthy",
            message=f"Schema not found: {e}",
        )
    except Exception as e:
        return ServiceHealth(
            name="schema",
            status="degraded",
            message=str(e),
        )
