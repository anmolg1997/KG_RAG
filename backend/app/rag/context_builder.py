"""
Context builder for RAG pipeline.

Assembles retrieved information into a coherent context string
for the LLM, with support for:
- Chunk context expansion (neighboring chunks)
- Metadata inclusion (page numbers, sections)
- Entity context formatting
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from app.strategies import get_strategy_manager, RetrievalStrategy
from app.graph.dynamic_repository import DynamicGraphRepository

logger = logging.getLogger(__name__)


@dataclass
class ContextChunk:
    """A chunk of context with metadata."""
    
    id: str
    text: str
    chunk_index: int
    page_number: Optional[int] = None
    section_heading: Optional[str] = None
    relevance_score: float = 1.0
    source: str = "chunk"  # "chunk", "entity", "expanded"
    metadata: dict = field(default_factory=dict)


@dataclass
class AssembledContext:
    """Assembled context ready for LLM."""
    
    text: str
    chunks: list[ContextChunk]
    entities: list[dict[str, Any]]
    
    total_tokens_estimate: int = 0
    truncated: bool = False
    
    @property
    def chunk_count(self) -> int:
        return len(self.chunks)
    
    @property
    def entity_count(self) -> int:
        return len(self.entities)


class ContextBuilder:
    """
    Builds context for RAG by assembling chunks and entities.
    
    Features:
    - Expands context to neighboring chunks
    - Includes page numbers and section headings
    - Formats entities with their properties
    - Respects token limits
    
    Usage:
        builder = ContextBuilder(graph_repo)
        context = await builder.build_context(
            chunks=matched_chunks,
            entities=matched_entities,
            query="What are the payment terms?"
        )
        print(context.text)
    """
    
    def __init__(
        self,
        graph_repo: DynamicGraphRepository,
        retrieval_strategy: Optional[RetrievalStrategy] = None,
    ):
        self.graph_repo = graph_repo
        self.strategy = retrieval_strategy or get_strategy_manager().retrieval
    
    async def build_context(
        self,
        chunks: list[dict[str, Any]],
        entities: list[dict[str, Any]],
        query: str,
    ) -> AssembledContext:
        """
        Build a complete context from retrieved chunks and entities.
        
        Args:
            chunks: Retrieved chunk dictionaries
            entities: Retrieved entity dictionaries
            query: Original user query
            
        Returns:
            AssembledContext with formatted text
        """
        context_chunks = []
        
        # Process chunks with optional expansion
        for chunk_data in chunks:
            chunk_id = chunk_data.get("id")
            if not chunk_id:
                continue
            
            # Create base chunk
            base_chunk = ContextChunk(
                id=chunk_id,
                text=chunk_data.get("text", ""),
                chunk_index=chunk_data.get("chunk_index", 0),
                page_number=chunk_data.get("page_number"),
                section_heading=chunk_data.get("section_heading"),
                source="chunk",
                metadata=chunk_data,
            )
            
            # Expand to neighbors if enabled
            if self.strategy.context.expand_neighbors.enabled:
                expanded = await self._expand_chunk_context(chunk_id, base_chunk)
                context_chunks.extend(expanded)
            else:
                context_chunks.append(base_chunk)
        
        # Deduplicate chunks by ID
        seen_ids = set()
        unique_chunks = []
        for chunk in context_chunks:
            if chunk.id not in seen_ids:
                seen_ids.add(chunk.id)
                unique_chunks.append(chunk)
        
        # Sort by chunk index for coherent reading order
        unique_chunks.sort(key=lambda c: c.chunk_index)
        
        # Limit to max chunks
        max_chunks = self.strategy.limits.max_chunks
        if len(unique_chunks) > max_chunks:
            unique_chunks = unique_chunks[:max_chunks]
        
        # Build the formatted text
        formatted_text = self._format_context(
            chunks=unique_chunks,
            entities=entities,
            query=query,
        )
        
        # Estimate tokens (rough: ~4 chars per token)
        token_estimate = len(formatted_text) // 4
        truncated = token_estimate > self.strategy.limits.max_context_tokens
        
        if truncated:
            # Simple truncation - could be smarter
            max_chars = self.strategy.limits.max_context_tokens * 4
            formatted_text = formatted_text[:max_chars] + "\n\n[Context truncated due to length]"
        
        return AssembledContext(
            text=formatted_text,
            chunks=unique_chunks,
            entities=entities,
            total_tokens_estimate=token_estimate,
            truncated=truncated,
        )
    
    async def _expand_chunk_context(
        self,
        chunk_id: str,
        base_chunk: ContextChunk,
    ) -> list[ContextChunk]:
        """Expand a chunk to include neighboring chunks."""
        expand_config = self.strategy.context.expand_neighbors
        
        neighbors = await self.graph_repo.get_neighboring_chunks(
            chunk_id=chunk_id,
            before=expand_config.before,
            after=expand_config.after,
        )
        
        result = []
        
        # Add before chunks
        for chunk_data in neighbors.get("before", []):
            result.append(ContextChunk(
                id=chunk_data.get("id", ""),
                text=chunk_data.get("text", ""),
                chunk_index=chunk_data.get("chunk_index", 0),
                page_number=chunk_data.get("page_number"),
                section_heading=chunk_data.get("section_heading"),
                source="expanded",
                relevance_score=0.7,  # Lower score for expanded context
                metadata=chunk_data,
            ))
        
        # Add the main chunk
        result.append(base_chunk)
        
        # Add after chunks
        for chunk_data in neighbors.get("after", []):
            result.append(ContextChunk(
                id=chunk_data.get("id", ""),
                text=chunk_data.get("text", ""),
                chunk_index=chunk_data.get("chunk_index", 0),
                page_number=chunk_data.get("page_number"),
                section_heading=chunk_data.get("section_heading"),
                source="expanded",
                relevance_score=0.7,
                metadata=chunk_data,
            ))
        
        return result
    
    def _format_context(
        self,
        chunks: list[ContextChunk],
        entities: list[dict[str, Any]],
        query: str,
    ) -> str:
        """Format chunks and entities into a context string."""
        include_config = self.strategy.context.include_metadata
        parts = []
        
        # Header
        parts.append(f"# Context for Query: {query}\n")
        
        # Group chunks by section if available
        current_section = None
        current_page = None
        
        parts.append("\n## Document Excerpts\n")
        
        for chunk in chunks:
            # Add section header if changed
            if include_config.section_heading and chunk.section_heading:
                if chunk.section_heading != current_section:
                    current_section = chunk.section_heading
                    parts.append(f"\n### {current_section}\n")
            
            # Add page indicator if changed
            if include_config.page_number and chunk.page_number:
                if chunk.page_number != current_page:
                    current_page = chunk.page_number
                    parts.append(f"\n[Page {current_page}]\n")
            
            # Add chunk text
            parts.append(f"{chunk.text}\n")
            
            # Add temporal refs if included
            if include_config.temporal_refs:
                temporal_refs = chunk.metadata.get("temporal_refs")
                if temporal_refs:
                    parts.append(f"_Temporal references: {temporal_refs}_\n")
        
        # Format entities
        if entities:
            parts.append("\n## Extracted Information\n")
            
            # Group by type
            entities_by_type: dict[str, list] = {}
            for entity in entities:
                etype = entity.get("_type", entity.get("entity_type", "Entity"))
                if etype not in entities_by_type:
                    entities_by_type[etype] = []
                entities_by_type[etype].append(entity)
            
            for etype, type_entities in entities_by_type.items():
                parts.append(f"\n### {etype}s\n")
                for entity in type_entities:
                    parts.append(self._format_entity(entity))
        
        return "\n".join(parts)
    
    def _format_entity(self, entity: dict[str, Any]) -> str:
        """Format an entity as a readable string."""
        # Priority fields to show first
        priority = ["name", "title", "description", "type", "value", "summary"]
        
        # Get entity name/title for header
        name = entity.get("name", entity.get("title", entity.get("id", "Entity")))
        lines = [f"**{name}**"]
        
        # Add priority fields first
        for field in priority:
            if field in entity and entity[field]:
                lines.append(f"  - {field}: {entity[field]}")
        
        # Add other fields (excluding internal ones)
        for key, value in entity.items():
            if key not in priority and not key.startswith("_") and value:
                if isinstance(value, (list, dict)):
                    continue  # Skip complex values
                lines.append(f"  - {key}: {value}")
        
        return "\n".join(lines) + "\n"
    
    async def get_context_for_entity(
        self,
        entity_id: str,
    ) -> Optional[AssembledContext]:
        """
        Get full context for an entity including its source chunk.
        
        Args:
            entity_id: Entity ID to get context for
            
        Returns:
            AssembledContext or None
        """
        # Get entity details
        entity = await self.graph_repo.get_entity_by_id(entity_id)
        if not entity:
            return None
        
        # Get source chunk
        source_chunk = await self.graph_repo.get_source_chunk_for_entity(entity_id)
        
        chunks = [source_chunk] if source_chunk else []
        
        return await self.build_context(
            chunks=chunks,
            entities=[entity],
            query=f"Details about {entity.get('name', entity_id)}",
        )
