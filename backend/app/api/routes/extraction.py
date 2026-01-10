"""
Extraction API routes for entity and relationship extraction.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.extraction.extractor import EntityExtractor
from app.extraction.ontology import OntologyRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extraction", tags=["extraction"])


class ExtractionRequest(BaseModel):
    """Request for entity extraction."""
    text: str = Field(..., min_length=50, description="Text to extract from")
    entity_types: Optional[list[str]] = Field(
        None,
        description="Specific entity types to extract (default: all)"
    )


class ExtractionResponse(BaseModel):
    """Response from extraction."""
    success: bool
    entity_count: int
    relationship_count: int
    validation: dict
    entities: dict


@router.post("/extract", response_model=ExtractionResponse)
async def extract_entities(request: ExtractionRequest):
    """
    Extract entities and relationships from text.
    
    This endpoint performs extraction without storing
    results in the knowledge graph.
    
    Use the /upload endpoint for full ingestion with storage.
    """
    extractor = EntityExtractor()
    
    try:
        if request.entity_types:
            result = await extractor.extract_specific_entities(
                text=request.text,
                entity_types=request.entity_types,
                source_document="api_request",
            )
            # For specific extraction, wrap in ExtractionResult-like format
            from app.extraction.validator import ExtractionValidator
            validator = ExtractionValidator()
            validation = validator.validate(result)
            
            return ExtractionResponse(
                success=True,
                entity_count=result.entity_count,
                relationship_count=result.relationship_count,
                validation=validation.to_dict(),
                entities={
                    "contracts": [c.model_dump() for c in result.contracts],
                    "parties": [p.model_dump() for p in result.parties],
                    "clauses": [c.model_dump() for c in result.clauses],
                    "obligations": [o.model_dump() for o in result.obligations],
                    "dates": [d.model_dump() for d in result.dates],
                    "amounts": [a.model_dump() for a in result.amounts],
                    "relationships": [r.model_dump() for r in result.relationships],
                },
            )
        else:
            result = await extractor.extract(
                text=request.text,
                source_document="api_request",
            )
            
            return ExtractionResponse(
                success=result.success,
                entity_count=result.graph.entity_count,
                relationship_count=result.graph.relationship_count,
                validation=result.validation.to_dict(),
                entities={
                    "contracts": [c.model_dump() for c in result.graph.contracts],
                    "parties": [p.model_dump() for p in result.graph.parties],
                    "clauses": [c.model_dump() for c in result.graph.clauses],
                    "obligations": [o.model_dump() for o in result.graph.obligations],
                    "dates": [d.model_dump() for d in result.graph.dates],
                    "amounts": [a.model_dump() for a in result.graph.amounts],
                    "relationships": [r.model_dump() for r in result.graph.relationships],
                },
            )
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}"
        )


@router.get("/ontology")
async def get_ontology():
    """
    Get the ontology schema.
    
    Returns all entity types, their fields, and relationship types
    used in the knowledge graph.
    """
    return {
        "entity_types": list(OntologyRegistry.ENTITY_TYPES.keys()),
        "relationship_types": OntologyRegistry.RELATIONSHIP_TYPES,
        "schemas": OntologyRegistry.get_all_schemas(),
        "description": OntologyRegistry.get_ontology_description(),
    }


@router.get("/ontology/{entity_type}")
async def get_entity_schema(entity_type: str):
    """Get the schema for a specific entity type."""
    try:
        schema = OntologyRegistry.get_entity_schema(entity_type)
        return {
            "entity_type": entity_type,
            "schema": schema,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )


@router.post("/validate")
async def validate_extraction(data: dict):
    """
    Validate extraction data against the ontology schema.
    
    Useful for validating manually created or modified extraction data.
    """
    from app.extraction.validator import ExtractionValidator
    from app.extraction.ontology import ExtractedGraph
    
    validator = ExtractionValidator()
    
    try:
        # Try to parse as ExtractedGraph
        graph = ExtractedGraph.model_validate(data)
        result = validator.validate(graph)
        
        return {
            "is_valid": result.is_valid,
            "errors": result.errors,
            "warnings": result.warnings,
            "entity_errors": result.entity_errors,
        }
    except Exception as e:
        return {
            "is_valid": False,
            "errors": [f"Failed to parse data: {str(e)}"],
            "warnings": [],
            "entity_errors": {},
        }


@router.get("/clause-types")
async def list_clause_types():
    """List all supported clause types."""
    from app.extraction.ontology import ClauseType
    return {
        "clause_types": [ct.value for ct in ClauseType],
    }


@router.get("/party-types")
async def list_party_types():
    """List all supported party types and roles."""
    from app.extraction.ontology import PartyType, PartyRole
    return {
        "party_types": [pt.value for pt in PartyType],
        "party_roles": [pr.value for pr in PartyRole],
    }


@router.get("/obligation-types")
async def list_obligation_types():
    """List all supported obligation types."""
    from app.extraction.ontology import ObligationType
    return {
        "obligation_types": [ot.value for ot in ObligationType],
    }
