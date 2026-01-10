"""
Schema-agnostic entity extraction.

This module provides extraction that works with ANY schema defined in YAML.
It dynamically generates prompts and parses results based on the loaded schema.
"""

import json
import logging
from typing import Any, Optional

from app.core.llm import LLMClient, get_extraction_client
from app.schema.loader import SchemaLoader, get_schema_loader
from app.schema.models import (
    Schema,
    DynamicEntity,
    DynamicRelationship,
    DynamicGraph,
)

logger = logging.getLogger(__name__)


class ExtractionResult:
    """Container for extraction result with metadata."""
    
    def __init__(
        self,
        graph: DynamicGraph,
        validation_errors: list[str] = None,
        validation_warnings: list[str] = None,
        raw_response: Optional[str] = None,
    ):
        self.graph = graph
        self.validation_errors = validation_errors or []
        self.validation_warnings = validation_warnings or []
        self.raw_response = raw_response
        self.success = len(self.validation_errors) == 0
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "schema": self.graph.schema_name,
            "entity_count": self.graph.entity_count,
            "relationship_count": self.graph.relationship_count,
            "validation": {
                "is_valid": self.success,
                "errors": self.validation_errors,
                "warnings": self.validation_warnings,
            },
        }


class DynamicExtractor:
    """
    Schema-agnostic entity extractor.
    
    This extractor works with ANY schema defined in YAML files.
    It dynamically generates extraction prompts and parses results
    based on the schema definition.
    
    Usage:
        # Use default schema from config
        extractor = DynamicExtractor()
        result = await extractor.extract(document_text)
        
        # Use specific schema
        extractor = DynamicExtractor(schema_name="research_paper")
        result = await extractor.extract(paper_text)
        
        # Access results
        for entity in result.graph.get_entities_by_type("Author"):
            print(entity.get("name"))
    """
    
    def __init__(
        self,
        schema_name: Optional[str] = None,
        schema_loader: Optional[SchemaLoader] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize the extractor.
        
        Args:
            schema_name: Name of schema to use. If None, uses active schema from config.
            schema_loader: SchemaLoader instance. If None, uses singleton.
            llm_client: LLM client for extraction. If None, uses extraction client.
        """
        self.schema_loader = schema_loader or get_schema_loader()
        self.llm = llm_client or get_extraction_client()
        
        # Load schema
        if schema_name:
            self.schema = self.schema_loader.load_schema(schema_name)
        else:
            self.schema = self.schema_loader.get_active_schema()
    
    async def extract(
        self,
        text: str,
        source_document: str = "unknown",
    ) -> ExtractionResult:
        """
        Extract entities and relationships from text.
        
        Args:
            text: Document text to process
            source_document: Identifier for source document
            
        Returns:
            ExtractionResult with dynamic graph and validation
        """
        logger.info(f"Extracting with schema: {self.schema.schema_info.name}")
        
        # Generate extraction prompt
        prompt = self.schema_loader.generate_extraction_prompt(self.schema, text)
        system_prompt = self.schema_loader.get_system_prompt(self.schema)
        
        try:
            # Call LLM
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=system_prompt,
            )
            
            # Parse response
            graph = self._parse_response(response, source_document)
            
            # Validate
            errors, warnings = self._validate_graph(graph)
            
            return ExtractionResult(
                graph=graph,
                validation_errors=errors,
                validation_warnings=warnings,
                raw_response=response,
            )
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            empty_graph = DynamicGraph(
                schema_name=self.schema.schema_info.name,
                source_document=source_document,
                extraction_model=self.llm.model,
            )
            return ExtractionResult(
                graph=empty_graph,
                validation_errors=[f"Extraction failed: {str(e)}"],
            )
    
    def _parse_response(self, response: str, source_document: str) -> DynamicGraph:
        """Parse LLM response into DynamicGraph."""
        # Clean response
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.debug(f"Raw response: {response[:500]}...")
            return DynamicGraph(
                schema_name=self.schema.schema_info.name,
                source_document=source_document,
                extraction_model=self.llm.model,
            )
        
        # Create graph
        graph = DynamicGraph(
            schema_name=self.schema.schema_info.name,
            source_document=source_document,
            extraction_model=self.llm.model,
        )
        
        # Parse entities
        entities_data = data.get("entities", {})
        for entity_type, entity_list in entities_data.items():
            # Verify entity type exists in schema
            if entity_type not in self.schema.get_entity_names():
                logger.warning(f"Unknown entity type in response: {entity_type}")
                continue
            
            for entity_data in entity_list:
                entity = self._parse_entity(entity_type, entity_data)
                graph.add_entity(entity)
        
        # Parse relationships
        relationships_data = data.get("relationships", [])
        for rel_data in relationships_data:
            rel = self._parse_relationship(rel_data)
            if rel:
                graph.add_relationship(rel)
        
        return graph
    
    def _parse_entity(self, entity_type: str, data: dict) -> DynamicEntity:
        """Parse entity data into DynamicEntity."""
        # Extract standard fields
        entity_id = data.pop("id", None)
        confidence = data.pop("confidence", 1.0)
        source_text = data.pop("source_text", None)
        
        # Remaining fields are properties
        properties = {}
        for key, value in data.items():
            if value is not None:  # Skip null values
                properties[key] = value
        
        entity = DynamicEntity(
            entity_type=entity_type,
            properties=properties,
            confidence=confidence,
            source_text=source_text,
        )
        
        # Set ID if provided
        if entity_id:
            entity.id = entity_id
        
        return entity
    
    def _parse_relationship(self, data: dict) -> Optional[DynamicRelationship]:
        """Parse relationship data into DynamicRelationship."""
        rel_type = data.get("relationship_type")
        source_id = data.get("source_id")
        target_id = data.get("target_id")
        
        if not all([rel_type, source_id, target_id]):
            logger.warning(f"Incomplete relationship data: {data}")
            return None
        
        # Verify relationship type exists in schema
        if rel_type not in self.schema.get_relationship_names():
            logger.warning(f"Unknown relationship type: {rel_type}")
            return None
        
        return DynamicRelationship(
            relationship_type=rel_type,
            source_id=source_id,
            target_id=target_id,
            confidence=data.get("confidence", 1.0),
            properties=data.get("properties", {}),
        )
    
    def _validate_graph(self, graph: DynamicGraph) -> tuple[list[str], list[str]]:
        """Validate extracted graph against schema."""
        errors = []
        warnings = []
        
        # Check required properties for each entity
        for entity_type, entities in graph.entities.items():
            entity_def = self.schema.get_entity(entity_type)
            if not entity_def:
                warnings.append(f"Unknown entity type: {entity_type}")
                continue
            
            required_props = entity_def.get_required_properties()
            
            for entity in entities:
                for prop_name in required_props:
                    if prop_name not in entity.properties or entity.properties[prop_name] is None:
                        warnings.append(
                            f"{entity_type} '{entity.display_name}' missing required property: {prop_name}"
                        )
        
        # Check relationship references
        all_entity_ids = {e.id for e in graph.get_all_entities()}
        
        for rel in graph.relationships:
            if rel.source_id not in all_entity_ids:
                errors.append(f"Relationship references unknown source: {rel.source_id}")
            if rel.target_id not in all_entity_ids:
                errors.append(f"Relationship references unknown target: {rel.target_id}")
        
        # Check that we extracted something
        if graph.entity_count == 0:
            warnings.append("No entities were extracted from the document")
        
        return errors, warnings
    
    async def extract_specific_types(
        self,
        text: str,
        entity_types: list[str],
        source_document: str = "unknown",
    ) -> ExtractionResult:
        """
        Extract only specific entity types.
        
        Useful for targeted extraction when you only need certain entities.
        """
        # Filter schema to requested types
        filtered_entities = [
            e for e in self.schema.entities
            if e.name in entity_types
        ]
        
        if not filtered_entities:
            return ExtractionResult(
                graph=DynamicGraph(
                    schema_name=self.schema.schema_info.name,
                    source_document=source_document,
                ),
                validation_errors=[f"No matching entity types found: {entity_types}"],
            )
        
        # Build targeted prompt
        entity_sections = []
        for entity in filtered_entities:
            props_desc = []
            for prop in entity.properties:
                required = "(required)" if prop.required else "(optional)"
                props_desc.append(f"    - {prop.name}: {prop.type} {required}")
            
            entity_sections.append(f"""### {entity.name}
{entity.description}
Properties:
{chr(10).join(props_desc)}""")
        
        prompt = f"""Extract the following entity types from this text:

{chr(10).join(entity_sections)}

TEXT:
{text}

Return a JSON object:
{{
    "entities": {{
        "EntityType": [{{ "id": "...", "property": "value", "confidence": 0.9 }}]
    }}
}}"""
        
        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=self.schema_loader.get_system_prompt(self.schema),
            )
            
            graph = self._parse_response(response, source_document)
            errors, warnings = self._validate_graph(graph)
            
            return ExtractionResult(
                graph=graph,
                validation_errors=errors,
                validation_warnings=warnings,
            )
            
        except Exception as e:
            logger.error(f"Targeted extraction failed: {e}")
            return ExtractionResult(
                graph=DynamicGraph(
                    schema_name=self.schema.schema_info.name,
                    source_document=source_document,
                ),
                validation_errors=[str(e)],
            )
    
    def get_schema_info(self) -> dict:
        """Get information about the current schema."""
        return {
            "name": self.schema.schema_info.name,
            "version": self.schema.schema_info.version,
            "description": self.schema.schema_info.description,
            "entity_types": self.schema.get_entity_names(),
            "relationship_types": self.schema.get_relationship_names(),
            "entity_colors": self.schema.get_entity_colors(),
        }
