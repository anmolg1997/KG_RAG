"""
Graph API routes for knowledge graph operations (schema-agnostic).
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.graph.dynamic_repository import DynamicGraphRepository
from app.graph.queries import QueryTemplates
from app.core.neo4j_client import get_neo4j_client
from app.schema.loader import get_schema_loader
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["graph"])

# Repository instance
_repo: Optional[DynamicGraphRepository] = None


async def get_repository() -> DynamicGraphRepository:
    """Get or create the graph repository."""
    global _repo
    if _repo is None:
        _repo = DynamicGraphRepository()
        await _repo.initialize()
    return _repo


class GraphStats(BaseModel):
    """Graph statistics."""
    total_nodes: int
    total_relationships: int
    node_counts: dict
    schema_name: str


@router.get("/stats", response_model=GraphStats)
async def get_graph_statistics():
    """Get statistics about the knowledge graph."""
    repo = await get_repository()
    
    try:
        stats = await repo.get_stats()
        
        # Calculate totals
        total_nodes = sum(
            v for k, v in stats.items()
            if k != "relationships"
        )
        
        return GraphStats(
            total_nodes=total_nodes,
            total_relationships=stats.get("relationships", 0),
            node_counts=stats,
            schema_name=settings.active_schema,
        )
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )


@router.get("/visualization")
async def get_visualization_data(
    limit: int = Query(100, ge=1, le=500),
):
    """
    Get graph data formatted for visualization.
    
    Returns nodes and edges suitable for graph visualization
    libraries like vis.js, d3, or cytoscape.
    """
    repo = await get_repository()
    
    try:
        data = await repo.get_visualization_data(limit=limit)
        return data
    except Exception as e:
        logger.error(f"Failed to get visualization data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get visualization data: {str(e)}"
        )


@router.get("/entities/{entity_type}")
async def list_entities_by_type(
    entity_type: str,
    limit: int = Query(100, ge=1, le=500),
):
    """
    List entities of a specific type.
    
    Entity types are defined in the active schema.
    Use /graph/schema to see available types.
    """
    repo = await get_repository()
    
    try:
        entities = await repo.get_entities_by_type(entity_type, limit=limit)
        return {
            "entity_type": entity_type,
            "total": len(entities),
            "entities": entities,
        }
    except Exception as e:
        logger.error(f"Failed to list entities: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list entities: {str(e)}"
        )


@router.get("/entities/{entity_type}/{entity_id}")
async def get_entity(entity_type: str, entity_id: str):
    """Get a specific entity by type and ID."""
    repo = await get_repository()
    
    try:
        entity = await repo.get_entity_by_id(entity_type, entity_id)
        if not entity:
            raise HTTPException(
                status_code=404,
                detail=f"{entity_type} {entity_id} not found"
            )
        return entity
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get entity: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get entity: {str(e)}"
        )


@router.get("/entities/{entity_type}/{entity_id}/related")
async def get_related_entities(entity_type: str, entity_id: str):
    """Get an entity with all its related entities."""
    repo = await get_repository()
    
    try:
        data = await repo.get_entity_with_relationships(entity_type, entity_id)
        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"{entity_type} {entity_id} not found"
            )
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get related entities: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get related entities: {str(e)}"
        )


@router.get("/search")
async def search_entities(
    query: str = Query(..., min_length=2),
    entity_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    """
    Search entities by property values.
    
    Searches across name and title properties.
    Optionally filter by entity type.
    """
    repo = await get_repository()
    
    try:
        results = await repo.search_entities(
            search_term=query,
            entity_type=entity_type,
            limit=limit,
        )
        return {
            "query": query,
            "entity_type": entity_type,
            "total": len(results),
            "results": results,
        }
    except Exception as e:
        logger.error(f"Failed to search entities: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search entities: {str(e)}"
        )


@router.post("/query/cypher")
async def execute_cypher_query(
    query: str,
    parameters: Optional[dict] = None,
):
    """
    Execute a raw Cypher query.
    
    WARNING: This endpoint is for advanced users.
    Use with caution - read operations only recommended.
    """
    client = get_neo4j_client()
    await client.connect()
    
    # Basic safety check - prevent destructive operations
    query_upper = query.upper()
    destructive_keywords = ["DELETE", "REMOVE", "DROP", "CREATE", "SET", "MERGE"]
    
    for keyword in destructive_keywords:
        if keyword in query_upper:
            raise HTTPException(
                status_code=400,
                detail=f"Destructive operations ({keyword}) not allowed via this endpoint"
            )
    
    try:
        results = await client.execute_query(query, parameters or {})
        return {
            "query": query,
            "result_count": len(results),
            "results": results,
        }
    except Exception as e:
        logger.error(f"Cypher query failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Query failed: {str(e)}"
        )


@router.delete("/entities/{entity_type}/{entity_id}")
async def delete_entity(entity_type: str, entity_id: str):
    """Delete an entity and its relationships."""
    repo = await get_repository()
    
    try:
        result = await repo.delete_entity(entity_type, entity_id)
        return {
            "message": f"{entity_type} {entity_id} deleted",
            "deleted": result,
        }
    except Exception as e:
        logger.error(f"Failed to delete entity: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete entity: {str(e)}"
        )


@router.delete("/all")
async def clear_graph():
    """
    Clear the entire knowledge graph.
    
    WARNING: This will delete ALL data. Use with extreme caution.
    """
    repo = await get_repository()
    
    try:
        result = await repo.clear_all()
        return {
            "message": "Graph cleared",
            "deleted": result,
        }
    except Exception as e:
        logger.error(f"Failed to clear graph: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear graph: {str(e)}"
        )


@router.get("/schema")
async def get_graph_schema():
    """
    Get the current graph schema.
    
    Shows:
    - Active schema name
    - Entity types defined in the schema
    - Relationship types defined in the schema
    - Labels and relationships actually in the database
    """
    client = get_neo4j_client()
    await client.connect()
    
    try:
        # Get database schema
        db_schema = await client.get_schema()
        
        # Get YAML schema info
        loader = get_schema_loader()
        schema = loader.get_active_schema()
        
        return {
            "active_schema": schema.schema_info.name,
            "schema_version": schema.schema_info.version,
            "schema_description": schema.schema_info.description,
            "defined_entities": [e.name for e in schema.entities],
            "defined_relationships": [r.name for r in schema.relationships],
            "database_labels": db_schema.get("labels", []),
            "database_relationships": db_schema.get("relationship_types", []),
        }
    except Exception as e:
        logger.error(f"Failed to get schema: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get schema: {str(e)}"
        )


@router.get("/schema/entities")
async def get_schema_entities():
    """Get detailed entity definitions from the active schema."""
    loader = get_schema_loader()
    schema = loader.get_active_schema()
    
    return {
        "schema_name": schema.schema_info.name,
        "entities": [
            {
                "name": e.name,
                "description": e.description,
                "properties": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "required": p.required,
                        "description": p.description,
                    }
                    for p in e.properties
                ],
            }
            for e in schema.entities
        ],
    }


@router.get("/schema/relationships")
async def get_schema_relationships():
    """Get detailed relationship definitions from the active schema."""
    loader = get_schema_loader()
    schema = loader.get_active_schema()
    
    return {
        "schema_name": schema.schema_info.name,
        "relationships": [
            {
                "name": r.name,
                "source": r.source,
                "target": r.target,
                "description": r.description,
                "properties": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                    }
                    for p in (r.properties or [])
                ],
            }
            for r in schema.relationships
        ],
    }
