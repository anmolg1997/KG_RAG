"""
Schema loader module.

Loads and validates schema definitions from YAML files.
Provides runtime access to the active schema.
"""

import logging
from pathlib import Path
from typing import Optional

import yaml

from app.config import settings
from app.schema.models import (
    Schema,
    EntityDefinition,
    RelationshipDefinition,
    PropertyDefinition,
    ExtractionConfig,
    QueryExample,
    SchemaInfo,
)

logger = logging.getLogger(__name__)


class SchemaLoader:
    """
    Loads and manages schema definitions.
    
    The schema loader:
    1. Reads YAML schema files from the schemas/ directory
    2. Validates the schema structure
    3. Provides access to entity/relationship definitions
    4. Generates extraction prompts based on schema
    
    Usage:
        loader = SchemaLoader()
        schema = loader.load_schema("contract")
        
        # Get entity definition
        party_def = schema.get_entity("Party")
        
        # Generate extraction prompt
        prompt = loader.generate_extraction_prompt(schema, document_text)
    """
    
    def __init__(self, schemas_dir: Optional[str] = None):
        """
        Initialize the schema loader.
        
        Args:
            schemas_dir: Directory containing schema YAML files.
                        Defaults to project root /schemas/
        """
        if schemas_dir:
            self.schemas_dir = Path(schemas_dir)
        else:
            # Default to project root /schemas/
            self.schemas_dir = Path(__file__).parent.parent.parent.parent / "schemas"
        
        self._schemas: dict[str, Schema] = {}
        self._active_schema: Optional[Schema] = None
    
    def load_schema(self, schema_name: str) -> Schema:
        """
        Load a schema from YAML file.
        
        Args:
            schema_name: Name of the schema (without .yaml extension)
            
        Returns:
            Loaded Schema object
        """
        # Check cache
        if schema_name in self._schemas:
            return self._schemas[schema_name]
        
        # Find schema file
        schema_path = self.schemas_dir / f"{schema_name}.yaml"
        
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {schema_path}")
        
        logger.info(f"Loading schema from {schema_path}")
        
        # Load YAML
        with open(schema_path, "r") as f:
            data = yaml.safe_load(f)
        
        # Parse into Schema model
        schema = self._parse_schema(data)
        
        # Validate schema
        self._validate_schema(schema)
        
        # Cache and return
        self._schemas[schema_name] = schema
        return schema
    
    def _parse_schema(self, data: dict) -> Schema:
        """Parse raw YAML data into Schema model."""
        # Parse schema info
        schema_info = SchemaInfo(**data.get("schema", {}))
        
        # Parse entities
        entities = []
        for entity_data in data.get("entities", []):
            properties = [
                PropertyDefinition(**prop)
                for prop in entity_data.get("properties", [])
            ]
            entity = EntityDefinition(
                name=entity_data["name"],
                description=entity_data.get("description", ""),
                color=entity_data.get("color", "#64748b"),
                properties=properties,
            )
            entities.append(entity)
        
        # Parse relationships
        relationships = []
        for rel_data in data.get("relationships", []):
            properties = [
                PropertyDefinition(**prop)
                for prop in rel_data.get("properties", [])
            ]
            rel = RelationshipDefinition(
                name=rel_data["name"],
                source=rel_data["source"],
                target=rel_data["target"],
                description=rel_data.get("description", ""),
                bidirectional=rel_data.get("bidirectional", False),
                properties=properties,
            )
            relationships.append(rel)
        
        # Parse extraction config
        extraction_data = data.get("extraction", {})
        extraction = ExtractionConfig(
            system_prompt=extraction_data.get("system_prompt", ""),
            domain_hints=extraction_data.get("domain_hints", []),
        )
        
        # Parse query examples
        query_examples = [
            QueryExample(**qe)
            for qe in data.get("query_examples", [])
        ]
        
        return Schema(
            schema=schema_info,
            entities=entities,
            relationships=relationships,
            extraction=extraction,
            query_examples=query_examples,
        )
    
    def _validate_schema(self, schema: Schema) -> None:
        """Validate schema structure and references."""
        entity_names = set(schema.get_entity_names())
        
        # Check that all relationship sources/targets exist
        for rel in schema.relationships:
            if rel.source not in entity_names:
                raise ValueError(
                    f"Relationship '{rel.name}' references unknown source entity: {rel.source}"
                )
            if rel.target not in entity_names:
                raise ValueError(
                    f"Relationship '{rel.name}' references unknown target entity: {rel.target}"
                )
        
        # Check that entities have at least one property
        for entity in schema.entities:
            if not entity.properties:
                logger.warning(f"Entity '{entity.name}' has no properties defined")
        
        logger.info(
            f"Schema '{schema.schema_info.name}' validated: "
            f"{len(schema.entities)} entities, {len(schema.relationships)} relationships"
        )
    
    def get_active_schema(self) -> Schema:
        """
        Get the currently active schema.
        
        Uses ACTIVE_SCHEMA from config, defaults to 'contract'.
        """
        if self._active_schema is None:
            schema_name = getattr(settings, "active_schema", "contract")
            self._active_schema = self.load_schema(schema_name)
        return self._active_schema
    
    def set_active_schema(self, schema_name: str) -> Schema:
        """Set the active schema."""
        self._active_schema = self.load_schema(schema_name)
        return self._active_schema
    
    def list_available_schemas(self) -> list[str]:
        """List all available schema names."""
        schemas = []
        for path in self.schemas_dir.glob("*.yaml"):
            schemas.append(path.stem)
        return schemas
    
    def generate_extraction_prompt(
        self,
        schema: Schema,
        document_text: str,
    ) -> str:
        """
        Generate an extraction prompt based on the schema.
        
        This creates a dynamic prompt that instructs the LLM
        to extract entities according to the schema definition.
        """
        # Build entity descriptions
        entity_sections = []
        for entity in schema.entities:
            props_desc = []
            for prop in entity.properties:
                required = "(required)" if prop.required else "(optional)"
                if prop.type == "enum" and prop.values:
                    type_info = f"enum: {prop.values}"
                else:
                    type_info = prop.type
                props_desc.append(f"    - {prop.name}: {type_info} {required} - {prop.description}")
            
            entity_section = f"""### {entity.name}
{entity.description}
Properties:
{chr(10).join(props_desc)}"""
            entity_sections.append(entity_section)
        
        # Build relationship descriptions
        rel_sections = []
        for rel in schema.relationships:
            rel_sections.append(f"- ({rel.source})-[:{rel.name}]->({rel.target}): {rel.description}")
        
        # Build the prompt
        prompt = f"""Analyze this document and extract a knowledge graph according to the following schema.

## SCHEMA: {schema.schema_info.name}
{schema.schema_info.description}

## ENTITY TYPES TO EXTRACT

{chr(10).join(entity_sections)}

## RELATIONSHIP TYPES TO EXTRACT

{chr(10).join(rel_sections)}

## DOCUMENT TEXT

{document_text}

## OUTPUT FORMAT

Return a JSON object with this structure:
{{
    "entities": {{
        "EntityType1": [
            {{
                "id": "unique_id",
                "property1": "value1",
                "property2": "value2",
                "confidence": 0.95
            }}
        ],
        "EntityType2": [...]
    }},
    "relationships": [
        {{
            "source_id": "entity_id",
            "target_id": "entity_id",
            "relationship_type": "RELATIONSHIP_NAME",
            "confidence": 0.9
        }}
    ]
}}

IMPORTANT:
- Generate unique IDs for each entity
- Use the exact entity type names and relationship names from the schema
- Include confidence scores (0.0-1.0) based on how clearly the information was stated
- Only extract information explicitly present in the text
- For required properties, ensure they are always filled"""
        
        return prompt
    
    def get_system_prompt(self, schema: Schema) -> str:
        """Get the system prompt for extraction."""
        base_prompt = schema.extraction.system_prompt or """You are an expert document analyst specializing in information extraction and knowledge graph construction.

Your task is to extract structured information from documents according to a predefined schema.

EXTRACTION PRINCIPLES:
1. Extract ONLY information explicitly stated in the text
2. Do not infer or assume information not present
3. Preserve exact quotes where relevant
4. Assign confidence scores based on clarity of information
5. Link entities through relationships when connections are explicit"""
        
        # Add domain hints
        if schema.extraction.domain_hints:
            hints = "\n".join(f"- {hint}" for hint in schema.extraction.domain_hints)
            base_prompt += f"\n\nDOMAIN-SPECIFIC HINTS:\n{hints}"
        
        return base_prompt
    
    def generate_query_understanding_prompt(
        self,
        schema: Schema,
        user_query: str,
    ) -> str:
        """Generate a prompt to understand user queries based on schema."""
        entity_names = schema.get_entity_names()
        relationship_names = schema.get_relationship_names()
        
        # Include query examples if available
        examples_section = ""
        if schema.query_examples:
            examples = []
            for qe in schema.query_examples[:5]:
                examples.append(
                    f"Q: {qe.question}\n"
                    f"   Entities: {qe.entity_types}\n"
                    f"   Relationships: {qe.relationships}"
                )
            examples_section = f"\n\nEXAMPLE QUERIES:\n{chr(10).join(examples)}"
        
        return f"""Analyze this user query about documents and determine what information to retrieve.

SCHEMA: {schema.schema_info.name}
AVAILABLE ENTITY TYPES: {entity_names}
AVAILABLE RELATIONSHIPS: {relationship_names}
{examples_section}

USER QUERY: {user_query}

Return a JSON object:
{{
    "intent": "what the user wants to find",
    "entity_types": ["list of relevant entity types"],
    "relationships": ["list of relevant relationships"],
    "filters": {{"property": "filter_value"}},
    "sort_by": "optional property to sort by"
}}"""


# Singleton instance
_schema_loader: Optional[SchemaLoader] = None


def get_schema_loader() -> SchemaLoader:
    """Get the singleton schema loader instance."""
    global _schema_loader
    if _schema_loader is None:
        _schema_loader = SchemaLoader()
    return _schema_loader
