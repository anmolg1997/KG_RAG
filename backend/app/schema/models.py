"""
Dynamic schema models.

These models represent the schema structure loaded from YAML files
and provide runtime entity creation without hardcoded classes.
"""

from datetime import date, datetime
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, create_model, field_validator


# =============================================================================
# SCHEMA DEFINITION MODELS
# =============================================================================
# These models represent the structure of the YAML schema file


class PropertyDefinition(BaseModel):
    """Definition of an entity property from schema."""
    
    name: str
    type: str  # string, number, date, boolean, enum, text, list
    required: bool = False
    description: str = ""
    default: Any = None
    values: Optional[list[str]] = None  # For enum type
    item_type: Optional[str] = None  # For list type
    
    def get_python_type(self) -> type:
        """Convert schema type to Python type."""
        type_mapping = {
            "string": str,
            "text": str,
            "number": float,
            "integer": int,
            "date": date,
            "datetime": datetime,
            "boolean": bool,
            "list": list,
            "enum": str,
        }
        return type_mapping.get(self.type, str)
    
    def get_pydantic_field(self) -> tuple[type, Any]:
        """Get Pydantic field definition for dynamic model creation."""
        python_type = self.get_python_type()
        
        # Handle optional fields
        if not self.required:
            python_type = Optional[python_type]
        
        # Create field with default
        if self.default is not None:
            return (python_type, Field(default=self.default, description=self.description))
        elif not self.required:
            return (python_type, Field(default=None, description=self.description))
        else:
            return (python_type, Field(..., description=self.description))


class EntityDefinition(BaseModel):
    """Definition of an entity type from schema."""
    
    name: str
    description: str = ""
    color: str = "#64748b"  # Default gray
    properties: list[PropertyDefinition] = Field(default_factory=list)
    
    def get_property_names(self) -> list[str]:
        """Get list of property names."""
        return [p.name for p in self.properties]
    
    def get_required_properties(self) -> list[str]:
        """Get list of required property names."""
        return [p.name for p in self.properties if p.required]
    
    def get_property(self, name: str) -> Optional[PropertyDefinition]:
        """Get a property definition by name."""
        for prop in self.properties:
            if prop.name == name:
                return prop
        return None


class RelationshipDefinition(BaseModel):
    """Definition of a relationship type from schema."""
    
    name: str
    source: str  # Source entity type
    target: str  # Target entity type
    description: str = ""
    bidirectional: bool = False
    properties: list[PropertyDefinition] = Field(default_factory=list)


class ExtractionConfig(BaseModel):
    """Extraction configuration from schema."""
    
    system_prompt: str = ""
    domain_hints: list[str] = Field(default_factory=list)


class QueryExample(BaseModel):
    """Example query from schema."""
    
    question: str
    entity_types: list[str] = Field(default_factory=list)
    relationships: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)


class SchemaInfo(BaseModel):
    """Schema metadata."""
    
    name: str
    version: str = "1.0"
    description: str = ""
    document_types: list[str] = Field(default_factory=list)


class Schema(BaseModel):
    """
    Complete schema definition loaded from YAML.
    
    This is the main class that represents an entire ontology.
    """
    
    schema_info: SchemaInfo = Field(alias="schema")
    entities: list[EntityDefinition] = Field(default_factory=list)
    relationships: list[RelationshipDefinition] = Field(default_factory=list)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    query_examples: list[QueryExample] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True
    
    def get_entity(self, name: str) -> Optional[EntityDefinition]:
        """Get entity definition by name."""
        for entity in self.entities:
            if entity.name == name:
                return entity
        return None
    
    def get_entity_names(self) -> list[str]:
        """Get list of all entity type names."""
        return [e.name for e in self.entities]
    
    def get_relationship(self, name: str) -> Optional[RelationshipDefinition]:
        """Get relationship definition by name."""
        for rel in self.relationships:
            if rel.name == name:
                return rel
        return None
    
    def get_relationship_names(self) -> list[str]:
        """Get list of all relationship type names."""
        return [r.name for r in self.relationships]
    
    def get_relationships_for_entity(self, entity_name: str) -> list[RelationshipDefinition]:
        """Get all relationships where entity is source or target."""
        return [
            r for r in self.relationships
            if r.source == entity_name or r.target == entity_name
        ]
    
    def get_entity_colors(self) -> dict[str, str]:
        """Get mapping of entity names to colors."""
        return {e.name: e.color for e in self.entities}


# =============================================================================
# DYNAMIC ENTITY MODELS
# =============================================================================
# These models represent actual extracted data


class DynamicEntity(BaseModel):
    """
    A dynamically created entity instance.
    
    This represents an actual extracted entity with its data.
    The schema is determined at runtime based on the loaded schema.
    """
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    entity_type: str = Field(..., description="Type of entity from schema")
    properties: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_text: Optional[str] = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    def get(self, property_name: str, default: Any = None) -> Any:
        """Get a property value."""
        return self.properties.get(property_name, default)
    
    def set(self, property_name: str, value: Any) -> None:
        """Set a property value."""
        self.properties[property_name] = value
    
    @property
    def display_name(self) -> str:
        """Get a display name for this entity."""
        # Try common name fields
        for field in ["name", "title", "description", "id"]:
            if field in self.properties and self.properties[field]:
                return str(self.properties[field])
        return self.id
    
    def to_neo4j_properties(self) -> dict[str, Any]:
        """Convert to properties dict for Neo4j."""
        props = {
            "id": self.id,
            "confidence": self.confidence,
            **self.properties,
        }
        # Convert complex types
        for key, value in props.items():
            if isinstance(value, (list, dict)):
                props[key] = str(value)
            elif isinstance(value, (date, datetime)):
                props[key] = value.isoformat()
        return props


class DynamicRelationship(BaseModel):
    """
    A dynamically created relationship instance.
    """
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    relationship_type: str = Field(..., description="Type of relationship from schema")
    source_id: str = Field(..., description="ID of source entity")
    target_id: str = Field(..., description="ID of target entity")
    properties: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class DynamicGraph(BaseModel):
    """
    Complete extraction result with dynamic entities.
    
    This replaces the hardcoded ExtractedGraph and works with any schema.
    """
    
    schema_name: str = Field(..., description="Schema used for extraction")
    source_document: str = Field(..., description="Source document identifier")
    extraction_model: str = Field(default="unknown", description="LLM used for extraction")
    
    # All entities grouped by type
    entities: dict[str, list[DynamicEntity]] = Field(default_factory=dict)
    
    # All relationships
    relationships: list[DynamicRelationship] = Field(default_factory=list)
    
    # Metadata
    extraction_metadata: dict[str, Any] = Field(default_factory=dict)
    
    def add_entity(self, entity: DynamicEntity) -> None:
        """Add an entity to the graph."""
        if entity.entity_type not in self.entities:
            self.entities[entity.entity_type] = []
        self.entities[entity.entity_type].append(entity)
    
    def add_relationship(self, relationship: DynamicRelationship) -> None:
        """Add a relationship to the graph."""
        self.relationships.append(relationship)
    
    def get_entities_by_type(self, entity_type: str) -> list[DynamicEntity]:
        """Get all entities of a specific type."""
        return self.entities.get(entity_type, [])
    
    def get_all_entities(self) -> list[DynamicEntity]:
        """Get all entities as a flat list."""
        all_entities = []
        for entity_list in self.entities.values():
            all_entities.extend(entity_list)
        return all_entities
    
    def get_entity_by_id(self, entity_id: str) -> Optional[DynamicEntity]:
        """Find an entity by ID."""
        for entity_list in self.entities.values():
            for entity in entity_list:
                if entity.id == entity_id:
                    return entity
        return None
    
    @property
    def entity_count(self) -> int:
        """Total number of entities."""
        return sum(len(entities) for entities in self.entities.values())
    
    @property
    def relationship_count(self) -> int:
        """Total number of relationships."""
        return len(self.relationships)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "schema_name": self.schema_name,
            "source_document": self.source_document,
            "entity_count": self.entity_count,
            "relationship_count": self.relationship_count,
            "entities": {
                entity_type: [e.model_dump() for e in entities]
                for entity_type, entities in self.entities.items()
            },
            "relationships": [r.model_dump() for r in self.relationships],
        }
