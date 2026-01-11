"""
Extraction API routes for schema-agnostic entity and relationship extraction.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.extraction.dynamic_extractor import DynamicExtractor
from app.schema.loader import get_schema_loader
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extraction", tags=["extraction"])


class ExtractionRequest(BaseModel):
    """Request for entity extraction."""
    text: str = Field(..., min_length=50, description="Text to extract from")
    schema_name: Optional[str] = Field(
        None,
        description="Schema to use for extraction (default: active schema from config)"
    )
    entity_types: Optional[list[str]] = Field(
        None,
        description="Specific entity types to extract (default: all from schema)"
    )


class ExtractionResponse(BaseModel):
    """Response from extraction."""
    success: bool
    schema_used: str
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
    
    The extraction uses the active schema (or specified schema)
    to determine what entity and relationship types to extract.
    
    Use the /upload endpoint for full ingestion with storage.
    """
    try:
        extractor = DynamicExtractor(schema_name=request.schema_name)
        
        if request.entity_types:
            result = await extractor.extract(
                text=request.text,
                source_document="api_request",
                entity_types=request.entity_types,
            )
        else:
            result = await extractor.extract(
                text=request.text,
                source_document="api_request",
            )
        
        # Format entities for response
        entities_dict = {}
        for entity_type, entities in result.graph.entities.items():
            entities_dict[entity_type] = entities
        
        return ExtractionResponse(
            success=result.success,
            schema_used=result.graph.schema_name,
            entity_count=result.graph.entity_count,
            relationship_count=result.graph.relationship_count,
            validation={
                "is_valid": result.success,
                "errors": result.validation_errors,
                "warnings": result.validation_warnings,
            },
            entities={
                **entities_dict,
                "relationships": result.graph.relationships,
            },
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Schema not found: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}"
        )


@router.get("/schema")
async def get_active_schema():
    """
    Get the active extraction schema.
    
    Returns all entity types, their fields, and relationship types
    that will be used for extraction.
    """
    try:
        loader = get_schema_loader()
        schema = loader.get_active_schema()
        
        return {
            "schema_name": schema.schema_info.name,
            "version": schema.schema_info.version,
            "description": schema.schema_info.description,
            "entity_types": [e.name for e in schema.entities],
            "relationship_types": [r.name for r in schema.relationships],
            "entities": [
                {
                    "name": e.name,
                    "description": e.description,
                    "properties": [
                        {"name": p.name, "type": p.type, "required": p.required}
                        for p in e.properties
                    ],
                }
                for e in schema.entities
            ],
            "relationships": [
                {
                    "name": r.name,
                    "source": r.source,
                    "target": r.target,
                    "description": r.description,
                }
                for r in schema.relationships
            ],
        }
    except Exception as e:
        logger.error(f"Failed to get schema: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get schema: {str(e)}"
        )


@router.get("/schema/{schema_name}")
async def get_schema(schema_name: str):
    """Get a specific schema by name."""
    try:
        loader = get_schema_loader()
        schema = loader.load_schema(schema_name)
        
        return {
            "schema_name": schema.schema_info.name,
            "version": schema.schema_info.version,
            "description": schema.schema_info.description,
            "entity_types": [e.name for e in schema.entities],
            "relationship_types": [r.name for r in schema.relationships],
            "entities": [
                {
                    "name": e.name,
                    "description": e.description,
                    "properties": [
                        {"name": p.name, "type": p.type, "required": p.required}
                        for p in e.properties
                    ],
                }
                for e in schema.entities
            ],
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Schema '{schema_name}' not found"
        )
    except Exception as e:
        logger.error(f"Failed to get schema: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get schema: {str(e)}"
        )


@router.get("/schemas")
async def list_schemas():
    """List all available schemas."""
    try:
        loader = get_schema_loader()
        schemas = loader.list_available_schemas()
        
        return {
            "active_schema": settings.active_schema,
            "available_schemas": schemas,
        }
    except Exception as e:
        logger.error(f"Failed to list schemas: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list schemas: {str(e)}"
        )


@router.get("/entity-types")
async def list_entity_types(schema_name: Optional[str] = None):
    """
    List all entity types in a schema.
    
    If no schema_name is provided, uses the active schema.
    """
    try:
        loader = get_schema_loader()
        
        if schema_name:
            schema = loader.load_schema(schema_name)
        else:
            schema = loader.get_active_schema()
        
        return {
            "schema_name": schema.schema_info.name,
            "entity_types": [
                {
                    "name": e.name,
                    "description": e.description,
                    "property_count": len(e.properties),
                }
                for e in schema.entities
            ],
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Schema '{schema_name}' not found"
        )
    except Exception as e:
        logger.error(f"Failed to list entity types: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list entity types: {str(e)}"
        )


@router.get("/relationship-types")
async def list_relationship_types(schema_name: Optional[str] = None):
    """
    List all relationship types in a schema.
    
    If no schema_name is provided, uses the active schema.
    """
    try:
        loader = get_schema_loader()
        
        if schema_name:
            schema = loader.load_schema(schema_name)
        else:
            schema = loader.get_active_schema()
        
        return {
            "schema_name": schema.schema_info.name,
            "relationship_types": [
                {
                    "name": r.name,
                    "source": r.source,
                    "target": r.target,
                    "description": r.description,
                }
                for r in schema.relationships
            ],
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Schema '{schema_name}' not found"
        )
    except Exception as e:
        logger.error(f"Failed to list relationship types: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list relationship types: {str(e)}"
        )


@router.post("/validate")
async def validate_extraction(data: dict, schema_name: Optional[str] = None):
    """
    Validate extraction data against a schema.
    
    Useful for validating manually created or modified extraction data.
    """
    try:
        loader = get_schema_loader()
        
        if schema_name:
            schema = loader.load_schema(schema_name)
        else:
            schema = loader.get_active_schema()
        
        errors = []
        warnings = []
        
        # Get expected entity types
        expected_entity_types = {e.name for e in schema.entities}
        expected_rel_types = {r.name for r in schema.relationships}
        
        # Check entities
        entities = data.get("entities", {})
        for entity_type, entity_list in entities.items():
            if entity_type == "relationships":
                continue
            if entity_type not in expected_entity_types:
                errors.append(f"Unknown entity type: {entity_type}")
            elif not isinstance(entity_list, list):
                errors.append(f"Entity type {entity_type} should be a list")
            else:
                for i, entity in enumerate(entity_list):
                    if not isinstance(entity, dict):
                        errors.append(f"{entity_type}[{i}] should be an object")
                    elif "id" not in entity:
                        warnings.append(f"{entity_type}[{i}] missing 'id' field")
        
        # Check relationships
        relationships = data.get("relationships", entities.get("relationships", []))
        for i, rel in enumerate(relationships):
            if not isinstance(rel, dict):
                errors.append(f"relationships[{i}] should be an object")
            else:
                if "relationship_type" in rel:
                    if rel["relationship_type"] not in expected_rel_types:
                        warnings.append(f"Unknown relationship type: {rel['relationship_type']}")
                if "source_id" not in rel:
                    errors.append(f"relationships[{i}] missing 'source_id'")
                if "target_id" not in rel:
                    errors.append(f"relationships[{i}] missing 'target_id'")
        
        return {
            "is_valid": len(errors) == 0,
            "schema_validated_against": schema.schema_info.name,
            "errors": errors,
            "warnings": warnings,
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Schema '{schema_name}' not found"
        )
    except Exception as e:
        return {
            "is_valid": False,
            "errors": [f"Validation failed: {str(e)}"],
            "warnings": [],
        }
