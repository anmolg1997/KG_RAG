"""
Schema-agnostic entity and metadata extraction.

This module provides extraction that works with ANY schema defined in YAML.
It dynamically generates prompts and parses results based on the loaded schema.

Now includes LLM-based metadata extraction (sections, temporal refs, key terms)
controlled by the ExtractionStrategy.
"""

import json
import logging
from dataclasses import dataclass, field
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


@dataclass
class ChunkMetadata:
    """
    Metadata extracted for a text chunk via LLM.
    
    This replaces rule-based extraction with LLM understanding.
    """
    chunk_id: Optional[str] = None
    chunk_index: int = 0
    
    # Section context
    section_heading: Optional[str] = None
    section_level: Optional[int] = None  # 1=top level, 2=subsection, etc.
    
    # Temporal references
    temporal_refs: list[dict] = field(default_factory=list)
    # Each: {"type": "date|duration|relative", "text": "...", "normalized": "...", "context": "..."}
    
    # Key terms
    key_terms: list[str] = field(default_factory=list)
    
    # Position info (from pipeline, not LLM)
    page_number: Optional[int] = None
    
    # Statistics (computed, not LLM)
    word_count: int = 0
    char_count: int = 0
    
    def to_dict(self) -> dict:
        result = {
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "section_heading": self.section_heading,
            "section_level": self.section_level,
            "temporal_refs": self.temporal_refs,
            "key_terms": self.key_terms,
            "word_count": self.word_count,
            "char_count": self.char_count,
        }
        if self.page_number is not None:
            result["page_number"] = self.page_number
        return result


class ExtractionResult:
    """Container for extraction result with metadata."""
    
    def __init__(
        self,
        graph: DynamicGraph,
        chunk_metadata: Optional[ChunkMetadata] = None,
        validation_errors: list[str] = None,
        validation_warnings: list[str] = None,
        raw_response: Optional[str] = None,
    ):
        self.graph = graph
        self.chunk_metadata = chunk_metadata
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
            "metadata": self.chunk_metadata.to_dict() if self.chunk_metadata else None,
            "validation": {
                "is_valid": self.success,
                "errors": self.validation_errors,
                "warnings": self.validation_warnings,
            },
        }


class DynamicExtractor:
    """
    Schema-agnostic entity and metadata extractor.
    
    This extractor works with ANY schema defined in YAML files.
    It dynamically generates extraction prompts and parses results
    based on the schema definition.
    
    Now includes metadata extraction (sections, temporal, key terms)
    in the same LLM call, controlled by ExtractionStrategy.
    
    Usage:
        # Use default schema from config
        extractor = DynamicExtractor()
        result = await extractor.extract(document_text)
        
        # With custom strategy
        from app.strategies import get_strategy_manager
        strategy = get_strategy_manager().extraction
        extractor = DynamicExtractor(extraction_strategy=strategy)
        result = await extractor.extract_chunk(chunk_text, chunk_index=0)
        
        # Access results
        for entity in result.graph.get_entities_by_type("Author"):
            print(entity.get("name"))
        
        # Access metadata
        if result.chunk_metadata:
            print(f"Section: {result.chunk_metadata.section_heading}")
    """
    
    def __init__(
        self,
        schema_name: Optional[str] = None,
        schema_loader: Optional[SchemaLoader] = None,
        llm_client: Optional[LLMClient] = None,
        extraction_strategy: Optional[Any] = None,  # ExtractionStrategy
    ):
        """
        Initialize the extractor.
        
        Args:
            schema_name: Name of schema to use. If None, uses active schema from config.
            schema_loader: SchemaLoader instance. If None, uses singleton.
            llm_client: LLM client for extraction. If None, uses extraction client.
            extraction_strategy: Strategy controlling what to extract. If None, uses default.
        """
        self.schema_loader = schema_loader or get_schema_loader()
        self.llm = llm_client or get_extraction_client()
        
        # Load schema
        if schema_name:
            self.schema = self.schema_loader.load_schema(schema_name)
        else:
            self.schema = self.schema_loader.get_active_schema()
        
        # Load extraction strategy
        if extraction_strategy:
            self.strategy = extraction_strategy
        else:
            from app.strategies import get_strategy_manager
            self.strategy = get_strategy_manager().extraction
    
    async def extract(
        self,
        text: str,
        source_document: str = "unknown",
    ) -> ExtractionResult:
        """
        Extract entities and relationships from text.
        
        For full documents, use this method. It does NOT extract chunk metadata
        since the text is not a single chunk.
        
        Args:
            text: Document text to process
            source_document: Identifier for source document
            
        Returns:
            ExtractionResult with dynamic graph
        """
        logger.info(f"Extracting with schema: {self.schema.schema_info.name}")
        
        # Generate extraction prompt (entities only for full documents)
        prompt = self._generate_entity_prompt(text)
        system_prompt = self.schema_loader.get_system_prompt(self.schema)
        
        try:
            # Call LLM
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=system_prompt,
            )
            
            # Parse response
            graph, _ = self._parse_response(response, source_document)
            
            # Validate
            errors, warnings = self._validate_graph(graph)
            
            return ExtractionResult(
                graph=graph,
                chunk_metadata=None,  # No chunk metadata for full document
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
    
    async def extract_chunk(
        self,
        chunk_text: str,
        chunk_id: Optional[str] = None,
        chunk_index: int = 0,
        source_document: str = "unknown",
    ) -> ExtractionResult:
        """
        Extract entities AND metadata from a single chunk.
        
        This is the main method for chunk-by-chunk processing.
        It extracts both entities and metadata in a single LLM call.
        
        Args:
            chunk_text: Text of the chunk
            chunk_id: Unique chunk identifier
            chunk_index: Index of chunk in document
            source_document: Source document identifier
            
        Returns:
            ExtractionResult with graph and chunk metadata
        """
        logger.debug(f"Extracting chunk {chunk_index} with metadata")
        
        # Generate combined extraction prompt
        prompt = self._generate_combined_prompt(chunk_text)
        system_prompt = self._get_combined_system_prompt()
        
        try:
            # Call LLM
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=system_prompt,
            )
            
            # Parse response
            graph, metadata = self._parse_response(response, source_document, chunk_index)
            
            # Set chunk info in metadata
            if metadata:
                metadata.chunk_id = chunk_id
                metadata.chunk_index = chunk_index
                metadata.word_count = len(chunk_text.split())
                metadata.char_count = len(chunk_text)
            
            # Validate
            errors, warnings = self._validate_graph(graph)
            
            return ExtractionResult(
                graph=graph,
                chunk_metadata=metadata,
                validation_errors=errors,
                validation_warnings=warnings,
                raw_response=response,
            )
            
        except Exception as e:
            logger.error(f"Chunk extraction failed: {e}")
            empty_graph = DynamicGraph(
                schema_name=self.schema.schema_info.name,
                source_document=source_document,
                extraction_model=self.llm.model,
            )
            return ExtractionResult(
                graph=empty_graph,
                chunk_metadata=ChunkMetadata(
                    chunk_id=chunk_id,
                    chunk_index=chunk_index,
                    word_count=len(chunk_text.split()),
                    char_count=len(chunk_text),
                ),
                validation_errors=[f"Extraction failed: {str(e)}"],
            )
    
    def _generate_entity_prompt(self, text: str) -> str:
        """Generate prompt for entity extraction only."""
        return self.schema_loader.generate_extraction_prompt(self.schema, text)
    
    def _generate_combined_prompt(self, chunk_text: str) -> str:
        """
        Generate a combined prompt for entities + metadata extraction.
        
        This creates a single prompt that asks the LLM to extract both
        entities (per schema) and metadata (per strategy).
        """
        # Build entity descriptions
        entity_sections = []
        for entity in self.schema.entities:
            props_desc = []
            for prop in entity.properties:
                required = "(required)" if prop.required else "(optional)"
                if prop.type == "enum" and prop.values:
                    type_info = f"enum: {prop.values}"
                else:
                    type_info = prop.type
                props_desc.append(f"    - {prop.name}: {type_info} {required}")
            
            entity_section = f"""### {entity.name}
{entity.description}
Properties:
{chr(10).join(props_desc)}"""
            entity_sections.append(entity_section)
        
        # Build relationship descriptions
        rel_sections = []
        for rel in self.schema.relationships:
            rel_sections.append(f"- ({rel.source})-[:{rel.name}]->({rel.target}): {rel.description}")
        
        # Build metadata extraction instructions based on strategy
        metadata_instructions = self._build_metadata_instructions()
        
        # Build the combined prompt
        prompt = f"""Analyze this text excerpt and extract structured information.

## SCHEMA: {self.schema.schema_info.name}
{self.schema.schema_info.description}

## ENTITY TYPES TO EXTRACT

{chr(10).join(entity_sections)}

## RELATIONSHIP TYPES TO EXTRACT

{chr(10).join(rel_sections)}

{metadata_instructions}

## TEXT TO ANALYZE

{chunk_text}

## OUTPUT FORMAT

Return a JSON object with this exact structure:
{{
    "entities": {{
        "EntityType1": [
            {{
                "id": "unique_id",
                "property1": "value1",
                "source_text": "exact quote from text",
                "confidence": 0.95
            }}
        ]
    }},
    "relationships": [
        {{
            "source_id": "entity_id",
            "target_id": "entity_id", 
            "relationship_type": "RELATIONSHIP_NAME",
            "confidence": 0.9
        }}
    ],
    "metadata": {{
        "section_heading": "detected section or heading this text belongs to",
        "section_level": 1,
        "temporal_refs": [
            {{
                "type": "date|duration|relative",
                "text": "original text",
                "normalized": "standardized value",
                "context": "what this date/duration refers to"
            }}
        ],
        "key_terms": ["important", "domain", "terms"]
    }}
}}

RULES:
- Generate unique IDs for each entity (e.g., "contract_1", "party_acme")
- Include "source_text" with the exact quote for each entity
- Set confidence (0.0-1.0) based on how explicitly information was stated
- Only extract what is explicitly present in the text
- For metadata, analyze the text structure and content"""

        return prompt
    
    def _build_metadata_instructions(self) -> str:
        """Build metadata extraction instructions based on strategy."""
        sections = ["## METADATA TO EXTRACT"]
        
        # Section headings
        if self.strategy.metadata.section_headings.enabled:
            sections.append("""
### Section Context
Identify what section or heading this text belongs to. Look for:
- Explicit headings like "ARTICLE 5: TERMINATION" or "Section 3.1"
- Chapter titles, numbered sections, or topic headers
- If no heading is visible, infer from content context
Provide: section_heading (string) and section_level (1=top, 2=sub, 3=subsub)""")
        
        # Temporal references
        if self.strategy.metadata.temporal_references.enabled:
            temporal_types = []
            if self.strategy.metadata.temporal_references.extract_dates:
                temporal_types.append("absolute dates (e.g., 'January 1, 2024')")
            if self.strategy.metadata.temporal_references.extract_durations:
                temporal_types.append("durations (e.g., '30 days', 'six months', 'a quarter')")
            if self.strategy.metadata.temporal_references.extract_relative:
                temporal_types.append("relative references (e.g., 'upon termination', 'after signing')")
            
            if temporal_types:
                sections.append(f"""
### Temporal References
Extract all time-related information:
- {chr(10).join('- ' + t for t in temporal_types)}

For each, provide:
- type: "date", "duration", or "relative"
- text: exact text from document
- normalized: standardized format (ISO date, or "X days/months/years")
- context: what this time reference relates to""")
        
        # Key terms
        if self.strategy.metadata.key_terms.enabled:
            sections.append(f"""
### Key Terms
Extract {self.strategy.metadata.key_terms.max_terms} important domain-specific terms:
- Focus on legal/technical/domain terminology
- Exclude common words and generic terms
- Include defined terms (often in quotes or capitalized)
- Include acronyms with their meanings if present""")
        
        return chr(10).join(sections)
    
    def _get_combined_system_prompt(self) -> str:
        """Get system prompt for combined extraction."""
        base_prompt = self.schema.extraction.system_prompt or """You are an expert document analyst specializing in information extraction and knowledge graph construction.

Your task is to extract structured information from document excerpts according to a predefined schema.

EXTRACTION PRINCIPLES:
1. Extract ONLY information explicitly stated in the text
2. Do not infer or assume information not present
3. Preserve exact quotes in source_text fields
4. Assign confidence scores based on clarity of information
5. Link entities through relationships when connections are explicit

METADATA EXTRACTION:
- For section context, identify the structural position in the document
- For temporal references, capture dates, deadlines, and time periods
- For key terms, identify domain-specific vocabulary and defined terms"""
        
        # Add domain hints
        if self.schema.extraction.domain_hints:
            hints = "\n".join(f"- {hint}" for hint in self.schema.extraction.domain_hints)
            base_prompt += f"\n\nDOMAIN-SPECIFIC HINTS:\n{hints}"
        
        return base_prompt
    
    def _parse_response(
        self, 
        response: str, 
        source_document: str,
        chunk_index: int = 0,
    ) -> tuple[DynamicGraph, Optional[ChunkMetadata]]:
        """Parse LLM response into DynamicGraph and ChunkMetadata."""
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
            ), None
        
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
            
            if not isinstance(entity_list, list):
                continue
                
            for entity_data in entity_list:
                if isinstance(entity_data, dict):
                    entity = self._parse_entity(entity_type, entity_data)
                    graph.add_entity(entity)
        
        # Parse relationships
        relationships_data = data.get("relationships", [])
        if isinstance(relationships_data, list):
            for rel_data in relationships_data:
                if isinstance(rel_data, dict):
                    rel = self._parse_relationship(rel_data)
                    if rel:
                        graph.add_relationship(rel)
        
        # Parse metadata
        metadata = None
        metadata_data = data.get("metadata", {})
        if metadata_data and isinstance(metadata_data, dict):
            metadata = self._parse_metadata(metadata_data, chunk_index)
        
        return graph, metadata
    
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
    
    def _parse_metadata(self, data: dict, chunk_index: int) -> ChunkMetadata:
        """Parse metadata from LLM response."""
        # Parse temporal refs
        temporal_refs = []
        raw_temporal = data.get("temporal_refs", [])
        if isinstance(raw_temporal, list):
            for ref in raw_temporal:
                if isinstance(ref, dict):
                    temporal_refs.append({
                        "type": ref.get("type", "unknown"),
                        "text": ref.get("text", ""),
                        "normalized": ref.get("normalized"),
                        "context": ref.get("context"),
                    })
        
        # Parse key terms
        key_terms = []
        raw_terms = data.get("key_terms", [])
        if isinstance(raw_terms, list):
            key_terms = [str(t) for t in raw_terms if t]
        
        return ChunkMetadata(
            chunk_index=chunk_index,
            section_heading=data.get("section_heading"),
            section_level=data.get("section_level"),
            temporal_refs=temporal_refs,
            key_terms=key_terms,
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
            
            graph, _ = self._parse_response(response, source_document)
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
