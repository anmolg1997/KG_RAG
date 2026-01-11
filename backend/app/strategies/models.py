"""
Pydantic models for extraction and retrieval strategies.

These models define all configurable options for:
1. Extraction Strategy - How documents are processed and stored
2. Retrieval Strategy - How information is found and assembled for queries
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


# =============================================================================
# EXTRACTION STRATEGY COMPONENTS
# =============================================================================


class ChunkStorageConfig(BaseModel):
    """Configuration for how chunks are stored in the graph."""
    
    enabled: bool = Field(
        default=True,
        description="Store chunks as Neo4j nodes"
    )
    store_text: bool = Field(
        default=True,
        description="Store full chunk text in the node"
    )
    max_text_length: int = Field(
        default=0,
        ge=0,
        description="Max text length to store (0 = no limit)"
    )


class ChunkLinkingConfig(BaseModel):
    """Configuration for chunk relationships."""
    
    sequential: bool = Field(
        default=True,
        description="Create NEXT_CHUNK/PREV_CHUNK relationships"
    )
    to_document: bool = Field(
        default=True,
        description="Create FROM_DOCUMENT relationship"
    )


class PageNumberConfig(BaseModel):
    """Configuration for page number extraction."""
    
    enabled: bool = Field(
        default=True,
        description="Extract page numbers from PDF"
    )


class SectionHeadingConfig(BaseModel):
    """Configuration for section heading detection."""
    
    enabled: bool = Field(
        default=True,
        description="Detect section headings in text"
    )
    patterns: list[str] = Field(
        default=[
            r"^(ARTICLE|Article|SECTION|Section)\s+\d+",
            r"^\d+\.\s+[A-Z]",
            r"^[A-Z][A-Z\s]{3,}$",
        ],
        description="Regex patterns to detect section headings"
    )


class TemporalReferenceConfig(BaseModel):
    """Configuration for temporal reference extraction."""
    
    enabled: bool = Field(
        default=True,
        description="Extract temporal references (dates, durations)"
    )
    extract_dates: bool = Field(
        default=True,
        description="Extract absolute dates (e.g., 'January 1, 2024')"
    )
    extract_durations: bool = Field(
        default=True,
        description="Extract durations (e.g., '30 days', '6 months')"
    )
    extract_relative: bool = Field(
        default=True,
        description="Extract relative references (e.g., 'upon termination')"
    )


class KeyTermConfig(BaseModel):
    """Configuration for key term extraction."""
    
    enabled: bool = Field(
        default=True,
        description="Extract key terms from chunks"
    )
    method: Literal["llm", "tfidf", "regex", "simple"] = Field(
        default="simple",
        description="Method for extracting key terms"
    )
    max_terms: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum terms to extract per chunk"
    )


class StatisticsConfig(BaseModel):
    """Configuration for chunk statistics."""
    
    word_count: bool = Field(default=True, description="Count words")
    char_count: bool = Field(default=True, description="Count characters")
    sentence_count: bool = Field(default=False, description="Count sentences")


class MetadataExtractionConfig(BaseModel):
    """Configuration for all metadata extraction."""
    
    page_numbers: PageNumberConfig = Field(default_factory=PageNumberConfig)
    section_headings: SectionHeadingConfig = Field(default_factory=SectionHeadingConfig)
    temporal_references: TemporalReferenceConfig = Field(default_factory=TemporalReferenceConfig)
    key_terms: KeyTermConfig = Field(default_factory=KeyTermConfig)
    statistics: StatisticsConfig = Field(default_factory=StatisticsConfig)


class EntityLinkingConfig(BaseModel):
    """Configuration for entity-to-chunk linking."""
    
    enabled: bool = Field(
        default=True,
        description="Create EXTRACTED_FROM relationships between entities and chunks"
    )
    store_source_text: bool = Field(
        default=False,
        description="Also store source text directly in entity node"
    )
    store_chunk_index: bool = Field(
        default=True,
        description="Store chunk index in entity metadata"
    )


class ValidationConfig(BaseModel):
    """Configuration for schema validation behavior."""
    
    mode: Literal["strict", "warn", "store_valid", "ignore"] = Field(
        default="warn",
        description="""Validation mode:
        - strict: Block storage if ANY validation errors
        - warn: Log warnings/errors but store everything
        - store_valid: Skip storing entities with errors, store valid ones
        - ignore: No validation, store everything silently"""
    )
    log_level: Literal["debug", "info", "warning"] = Field(
        default="info",
        description="Log level for validation messages"
    )
    fail_on_missing_required: bool = Field(
        default=False,
        description="Treat missing required properties as errors (not just warnings)"
    )
    fail_on_broken_relationships: bool = Field(
        default=True,
        description="Treat relationships to non-existent entities as errors"
    )


class ChunkingConfig(BaseModel):
    """Configuration for text chunking."""
    
    strategy: Literal["fixed", "semantic", "sentence"] = Field(
        default="fixed",
        description="Chunking strategy: fixed=by char count, semantic=by sections, sentence=by sentences"
    )
    chunk_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Target chunk size in characters"
    )
    chunk_overlap: int = Field(
        default=200,
        ge=0,
        le=500,
        description="Overlap between chunks in characters"
    )


class ExtractionStrategy(BaseModel):
    """
    Complete extraction strategy configuration.
    
    Controls how documents are processed and what metadata is extracted
    during the ingestion pipeline.
    """
    
    name: str = Field(
        default="default",
        description="Strategy name for identification"
    )
    description: str = Field(
        default="Default extraction strategy",
        description="Human-readable description"
    )
    
    chunking: ChunkingConfig = Field(
        default_factory=ChunkingConfig,
        description="Text chunking settings"
    )
    chunks: ChunkStorageConfig = Field(
        default_factory=ChunkStorageConfig,
        description="Chunk storage settings"
    )
    chunk_linking: ChunkLinkingConfig = Field(
        default_factory=ChunkLinkingConfig,
        description="Chunk relationship settings"
    )
    metadata: MetadataExtractionConfig = Field(
        default_factory=MetadataExtractionConfig,
        description="Metadata extraction settings"
    )
    entity_linking: EntityLinkingConfig = Field(
        default_factory=EntityLinkingConfig,
        description="Entity-chunk linking settings"
    )
    validation: ValidationConfig = Field(
        default_factory=ValidationConfig,
        description="Schema validation settings"
    )


# =============================================================================
# RETRIEVAL STRATEGY COMPONENTS
# =============================================================================


class GraphTraversalConfig(BaseModel):
    """Configuration for graph-based retrieval."""
    
    enabled: bool = Field(
        default=True,
        description="Use knowledge graph traversal for retrieval"
    )
    max_depth: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum hops from matched entities"
    )


class ChunkTextSearchConfig(BaseModel):
    """Configuration for chunk text search."""
    
    enabled: bool = Field(
        default=True,
        description="Search chunk text content"
    )
    method: Literal["contains", "fulltext", "regex"] = Field(
        default="contains",
        description="Search method to use"
    )


class KeywordMatchingConfig(BaseModel):
    """Configuration for keyword-based matching."""
    
    enabled: bool = Field(
        default=True,
        description="Match on extracted key terms"
    )
    match_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum similarity for term matching"
    )


class TemporalFilteringConfig(BaseModel):
    """Configuration for temporal-based filtering."""
    
    enabled: bool = Field(
        default=True,
        description="Filter results by temporal references"
    )
    auto_detect: bool = Field(
        default=True,
        description="Automatically detect temporal queries"
    )


class SearchConfig(BaseModel):
    """Configuration for all search methods."""
    
    graph_traversal: GraphTraversalConfig = Field(default_factory=GraphTraversalConfig)
    chunk_text_search: ChunkTextSearchConfig = Field(default_factory=ChunkTextSearchConfig)
    keyword_matching: KeywordMatchingConfig = Field(default_factory=KeywordMatchingConfig)
    temporal_filtering: TemporalFilteringConfig = Field(default_factory=TemporalFilteringConfig)


class NeighborExpansionConfig(BaseModel):
    """Configuration for context expansion to neighboring chunks."""
    
    enabled: bool = Field(
        default=True,
        description="Expand context to neighboring chunks"
    )
    before: int = Field(
        default=1,
        ge=0,
        le=5,
        description="Number of chunks to include before"
    )
    after: int = Field(
        default=1,
        ge=0,
        le=5,
        description="Number of chunks to include after"
    )


class IncludeMetadataConfig(BaseModel):
    """Configuration for what metadata to include in context."""
    
    section_heading: bool = Field(
        default=True,
        description="Include section heading in context"
    )
    page_number: bool = Field(
        default=True,
        description="Include page number in context"
    )
    temporal_refs: bool = Field(
        default=True,
        description="Include temporal references in context"
    )
    key_terms: bool = Field(
        default=False,
        description="Include key terms in context"
    )


class ContextConfig(BaseModel):
    """Configuration for context building."""
    
    expand_neighbors: NeighborExpansionConfig = Field(default_factory=NeighborExpansionConfig)
    include_metadata: IncludeMetadataConfig = Field(default_factory=IncludeMetadataConfig)


class ScoringConfig(BaseModel):
    """Configuration for result scoring and filtering."""
    
    entity_confidence_min: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum entity confidence to include"
    )
    graph_match_weight: float = Field(
        default=1.5,
        ge=0.0,
        description="Weight multiplier for graph-based matches"
    )
    text_match_weight: float = Field(
        default=1.0,
        ge=0.0,
        description="Weight multiplier for text-based matches"
    )
    recency_boost: bool = Field(
        default=False,
        description="Boost more recent chunks (useful for news/updates)"
    )


class LimitsConfig(BaseModel):
    """Configuration for result limits."""
    
    max_chunks: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum chunks to include in context"
    )
    max_entities: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum entities to include"
    )
    max_context_tokens: int = Field(
        default=4000,
        ge=500,
        le=32000,
        description="Maximum tokens for LLM context"
    )


class RetrievalStrategy(BaseModel):
    """
    Complete retrieval strategy configuration.
    
    Controls how information is found and assembled when answering queries.
    """
    
    name: str = Field(
        default="default",
        description="Strategy name for identification"
    )
    description: str = Field(
        default="Default retrieval strategy",
        description="Human-readable description"
    )
    
    search: SearchConfig = Field(
        default_factory=SearchConfig,
        description="Search method settings"
    )
    context: ContextConfig = Field(
        default_factory=ContextConfig,
        description="Context building settings"
    )
    scoring: ScoringConfig = Field(
        default_factory=ScoringConfig,
        description="Scoring and filtering settings"
    )
    limits: LimitsConfig = Field(
        default_factory=LimitsConfig,
        description="Result limit settings"
    )


# =============================================================================
# COMBINED STRATEGY
# =============================================================================


class CombinedStrategy(BaseModel):
    """Combined extraction and retrieval strategy."""
    
    extraction: ExtractionStrategy = Field(default_factory=ExtractionStrategy)
    retrieval: RetrievalStrategy = Field(default_factory=RetrievalStrategy)
