"""
API routes for strategy management.

Provides endpoints to:
- Get current strategy configuration
- Switch between presets
- Update individual strategy settings
- List available presets
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.strategies import (
    get_strategy_manager,
    list_presets,
    ExtractionStrategy,
    RetrievalStrategy,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategies", tags=["strategies"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class PresetInfo(BaseModel):
    """Information about a strategy preset."""
    
    name: str
    extraction_description: str
    retrieval_description: str


class StrategyStatusResponse(BaseModel):
    """Current strategy status."""
    
    current_preset: Optional[str]
    extraction: dict[str, Any]
    retrieval: dict[str, Any]


class PresetRequest(BaseModel):
    """Request to load a preset."""
    
    name: str = Field(..., description="Preset name to load")


class StrategyUpdateRequest(BaseModel):
    """Request to update strategy settings."""
    
    updates: dict[str, Any] = Field(..., description="Partial updates to apply")


# =============================================================================
# ENDPOINTS - OVERVIEW
# =============================================================================


@router.get("", response_model=StrategyStatusResponse)
async def get_strategy_status():
    """
    Get current strategy status.
    
    Returns overview of active extraction and retrieval strategies.
    """
    manager = get_strategy_manager()
    return manager.get_status()


@router.get("/presets", response_model=list[PresetInfo])
async def get_available_presets():
    """
    List all available strategy presets.
    
    Returns list of preset names with descriptions.
    """
    return list_presets()


# =============================================================================
# ENDPOINTS - PRESET MANAGEMENT
# =============================================================================


@router.post("/preset")
async def load_preset(request: PresetRequest):
    """
    Load a strategy preset.
    
    Replaces both extraction and retrieval strategies with the preset values.
    
    Available presets:
    - minimal: Entities only, no chunks
    - balanced: Good mix of features (default)
    - comprehensive: All features enabled
    - speed: Optimized for fast processing
    - research: Optimized for academic papers
    """
    manager = get_strategy_manager()
    try:
        manager.load_preset(request.name)
        return {
            "status": "success",
            "message": f"Loaded preset: {request.name}",
            "current": manager.get_status(),
        }
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# ENDPOINTS - EXTRACTION STRATEGY
# =============================================================================


@router.get("/extraction")
async def get_extraction_strategy():
    """
    Get current extraction strategy configuration.
    
    Returns full configuration including:
    - Chunk storage settings
    - Chunk linking settings
    - Metadata extraction settings
    - Entity linking settings
    """
    manager = get_strategy_manager()
    return manager.extraction.model_dump()


@router.put("/extraction")
async def set_extraction_strategy(strategy: ExtractionStrategy):
    """
    Set a complete extraction strategy.
    
    Replaces the entire extraction strategy configuration.
    """
    manager = get_strategy_manager()
    manager.set_extraction_strategy(strategy)
    return {
        "status": "success",
        "message": "Extraction strategy updated",
        "strategy": manager.extraction.model_dump(),
    }


@router.patch("/extraction")
async def update_extraction_strategy(request: StrategyUpdateRequest):
    """
    Partially update extraction strategy.
    
    Only updates the specified fields, keeping others unchanged.
    
    Example request body:
    ```json
    {
        "updates": {
            "chunks": {"enabled": false},
            "metadata": {
                "temporal_references": {"enabled": false}
            }
        }
    }
    ```
    """
    manager = get_strategy_manager()
    try:
        updated = manager.update_extraction_strategy(request.updates)
        return {
            "status": "success",
            "message": "Extraction strategy updated",
            "strategy": updated.model_dump(),
        }
    except Exception as e:
        logger.error(f"Failed to update extraction strategy: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# ENDPOINTS - RETRIEVAL STRATEGY
# =============================================================================


@router.get("/retrieval")
async def get_retrieval_strategy():
    """
    Get current retrieval strategy configuration.
    
    Returns full configuration including:
    - Search method settings
    - Context building settings
    - Scoring settings
    - Limit settings
    """
    manager = get_strategy_manager()
    return manager.retrieval.model_dump()


@router.put("/retrieval")
async def set_retrieval_strategy(strategy: RetrievalStrategy):
    """
    Set a complete retrieval strategy.
    
    Replaces the entire retrieval strategy configuration.
    """
    manager = get_strategy_manager()
    manager.set_retrieval_strategy(strategy)
    return {
        "status": "success",
        "message": "Retrieval strategy updated",
        "strategy": manager.retrieval.model_dump(),
    }


@router.patch("/retrieval")
async def update_retrieval_strategy(request: StrategyUpdateRequest):
    """
    Partially update retrieval strategy.
    
    Only updates the specified fields, keeping others unchanged.
    
    Example request body:
    ```json
    {
        "updates": {
            "search": {
                "graph_traversal": {"max_depth": 3}
            },
            "context": {
                "expand_neighbors": {"before": 2, "after": 2}
            }
        }
    }
    ```
    """
    manager = get_strategy_manager()
    try:
        updated = manager.update_retrieval_strategy(request.updates)
        return {
            "status": "success",
            "message": "Retrieval strategy updated",
            "strategy": updated.model_dump(),
        }
    except Exception as e:
        logger.error(f"Failed to update retrieval strategy: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# ENDPOINTS - COMBINED
# =============================================================================


@router.get("/combined")
async def get_combined_strategy():
    """
    Get both extraction and retrieval strategies.
    
    Returns complete configuration for both strategies.
    """
    manager = get_strategy_manager()
    combined = manager.get_combined()
    return combined.model_dump()


@router.post("/reset")
async def reset_strategies():
    """
    Reset strategies to default preset (balanced).
    
    Restores both extraction and retrieval strategies to their default values.
    """
    manager = get_strategy_manager()
    manager.load_preset("balanced")
    return {
        "status": "success",
        "message": "Strategies reset to defaults (balanced preset)",
        "current": manager.get_status(),
    }
