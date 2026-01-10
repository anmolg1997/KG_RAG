"""
Graph API routes for knowledge graph operations.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.graph.repository import GraphRepository
from app.graph.queries import QueryTemplates
from app.core.neo4j_client import get_neo4j_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["graph"])

# Repository instance
_repo: Optional[GraphRepository] = None


async def get_repository() -> GraphRepository:
    """Get or create the graph repository."""
    global _repo
    if _repo is None:
        _repo = GraphRepository()
        await _repo.initialize()
    return _repo


class GraphStats(BaseModel):
    """Graph statistics."""
    total_nodes: int
    total_relationships: int
    node_counts: dict


@router.get("/stats", response_model=GraphStats)
async def get_graph_statistics():
    """Get statistics about the knowledge graph."""
    repo = await get_repository()
    
    try:
        stats = await repo.get_graph_stats()
        
        # Calculate totals
        total_nodes = sum(
            v for k, v in stats.items()
            if k != "relationships"
        )
        
        return GraphStats(
            total_nodes=total_nodes,
            total_relationships=stats.get("relationships", 0),
            node_counts=stats,
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
        data = await repo.get_graph_visualization_data(limit=limit)
        return data
    except Exception as e:
        logger.error(f"Failed to get visualization data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get visualization data: {str(e)}"
        )


@router.get("/contracts")
async def list_contracts():
    """List all contracts in the knowledge graph."""
    repo = await get_repository()
    
    try:
        contracts = await repo.get_all_contracts()
        return {
            "total": len(contracts),
            "contracts": contracts,
        }
    except Exception as e:
        logger.error(f"Failed to list contracts: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list contracts: {str(e)}"
        )


@router.get("/contracts/{contract_id}")
async def get_contract(contract_id: str):
    """Get a specific contract by ID."""
    repo = await get_repository()
    
    try:
        contract = await repo.get_contract_by_id(contract_id)
        if not contract:
            raise HTTPException(
                status_code=404,
                detail=f"Contract {contract_id} not found"
            )
        return contract
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get contract: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get contract: {str(e)}"
        )


@router.get("/contracts/{contract_id}/full")
async def get_contract_full_graph(contract_id: str):
    """Get a contract with all related entities."""
    repo = await get_repository()
    
    try:
        data = await repo.get_contract_full_graph(contract_id)
        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"Contract {contract_id} not found"
            )
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get contract graph: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get contract graph: {str(e)}"
        )


@router.get("/clauses")
async def list_clauses(
    clause_type: Optional[str] = None,
):
    """
    List clauses, optionally filtered by type.
    
    Clause types include:
    - termination
    - payment
    - confidentiality
    - indemnification
    - etc.
    """
    repo = await get_repository()
    
    try:
        if clause_type:
            clauses = await repo.get_clauses_by_type(clause_type)
        else:
            client = get_neo4j_client()
            await client.connect()
            results = await client.execute_query(
                "MATCH (c:Clause) RETURN c LIMIT 100"
            )
            clauses = [r["c"] for r in results]
        
        return {
            "total": len(clauses),
            "clause_type": clause_type,
            "clauses": clauses,
        }
    except Exception as e:
        logger.error(f"Failed to list clauses: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list clauses: {str(e)}"
        )


@router.get("/parties")
async def list_parties():
    """List all parties in the knowledge graph."""
    client = get_neo4j_client()
    await client.connect()
    
    try:
        results = await client.execute_query(
            "MATCH (p:Party) RETURN p"
        )
        parties = [r["p"] for r in results]
        
        return {
            "total": len(parties),
            "parties": parties,
        }
    except Exception as e:
        logger.error(f"Failed to list parties: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list parties: {str(e)}"
        )


@router.get("/parties/search")
async def search_parties(name: str = Query(..., min_length=2)):
    """Search parties by name."""
    repo = await get_repository()
    
    try:
        parties = await repo.search_parties_by_name(name)
        return {
            "query": name,
            "total": len(parties),
            "parties": parties,
        }
    except Exception as e:
        logger.error(f"Failed to search parties: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search parties: {str(e)}"
        )


@router.get("/parties/{party_id}/obligations")
async def get_party_obligations(party_id: str):
    """Get all obligations for a party."""
    repo = await get_repository()
    
    try:
        obligations = await repo.get_party_obligations(party_id)
        return {
            "party_id": party_id,
            "total": len(obligations),
            "obligations": obligations,
        }
    except Exception as e:
        logger.error(f"Failed to get obligations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get obligations: {str(e)}"
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


@router.delete("/contracts/{contract_id}")
async def delete_contract(contract_id: str):
    """Delete a contract and all its related entities."""
    repo = await get_repository()
    
    try:
        result = await repo.delete_contract_graph(contract_id)
        return {
            "message": f"Contract {contract_id} deleted",
            "deleted": result,
        }
    except Exception as e:
        logger.error(f"Failed to delete contract: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete contract: {str(e)}"
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
    """Get the current graph schema (labels and relationship types)."""
    client = get_neo4j_client()
    await client.connect()
    
    try:
        schema = await client.get_schema()
        return schema
    except Exception as e:
        logger.error(f"Failed to get schema: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get schema: {str(e)}"
        )
