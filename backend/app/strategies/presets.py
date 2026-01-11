"""
Predefined strategy presets for common use cases.

Each preset is a combination of extraction and retrieval strategies
optimized for specific scenarios.
"""

from .models import (
    ExtractionStrategy,
    RetrievalStrategy,
    CombinedStrategy,
    ChunkStorageConfig,
    ChunkLinkingConfig,
    ChunkingConfig,
    MetadataExtractionConfig,
    EntityLinkingConfig,
    ValidationConfig,
    PageNumberConfig,
    SectionHeadingConfig,
    TemporalReferenceConfig,
    KeyTermConfig,
    StatisticsConfig,
    SearchConfig,
    ContextConfig,
    ScoringConfig,
    LimitsConfig,
    GraphTraversalConfig,
    ChunkTextSearchConfig,
    KeywordMatchingConfig,
    TemporalFilteringConfig,
    NeighborExpansionConfig,
    IncludeMetadataConfig,
)


# =============================================================================
# PRESET DEFINITIONS
# =============================================================================


def _create_minimal_preset() -> CombinedStrategy:
    """
    Minimal preset - entities only, no chunks.
    
    Use case: Quick extraction, small documents, when you only need
    structured entity data without full text context.
    """
    return CombinedStrategy(
        extraction=ExtractionStrategy(
            name="minimal",
            description="Minimal extraction - entities only, no chunk storage",
            chunking=ChunkingConfig(
                strategy="fixed",
                chunk_size=1500,  # Larger chunks for speed
                chunk_overlap=100,
            ),
            chunks=ChunkStorageConfig(
                enabled=False,
                store_text=False,
            ),
            chunk_linking=ChunkLinkingConfig(
                sequential=False,
                to_document=False,
            ),
            metadata=MetadataExtractionConfig(
                page_numbers=PageNumberConfig(enabled=False),
                section_headings=SectionHeadingConfig(enabled=False),
                temporal_references=TemporalReferenceConfig(enabled=False),
                key_terms=KeyTermConfig(enabled=False),
                statistics=StatisticsConfig(
                    word_count=False,
                    char_count=False,
                    sentence_count=False,
                ),
            ),
            entity_linking=EntityLinkingConfig(
                enabled=False,
                store_source_text=True,  # Store source text in entity since no chunks
            ),
            validation=ValidationConfig(
                mode="ignore",  # Fastest, no validation
                log_level="warning",
            ),
        ),
        retrieval=RetrievalStrategy(
            name="minimal",
            description="Minimal retrieval - graph only",
            search=SearchConfig(
                graph_traversal=GraphTraversalConfig(enabled=True, max_depth=2),
                chunk_text_search=ChunkTextSearchConfig(enabled=False),
                keyword_matching=KeywordMatchingConfig(enabled=False),
                temporal_filtering=TemporalFilteringConfig(enabled=False),
            ),
            context=ContextConfig(
                expand_neighbors=NeighborExpansionConfig(enabled=False),
                include_metadata=IncludeMetadataConfig(
                    section_heading=False,
                    page_number=False,
                    temporal_refs=False,
                    key_terms=False,
                ),
            ),
            scoring=ScoringConfig(
                entity_confidence_min=0.3,
                graph_match_weight=1.0,
                text_match_weight=0.0,
            ),
            limits=LimitsConfig(
                max_chunks=5,
                max_entities=15,
                max_context_tokens=2000,
            ),
        ),
    )


def _create_balanced_preset() -> CombinedStrategy:
    """
    Balanced preset - good mix of features for general use.
    
    Use case: General purpose document processing with reasonable
    metadata extraction and retrieval capabilities.
    """
    return CombinedStrategy(
        extraction=ExtractionStrategy(
            name="balanced",
            description="Balanced extraction - chunks with basic metadata",
            chunking=ChunkingConfig(
                strategy="fixed",
                chunk_size=1000,
                chunk_overlap=200,
            ),
            chunks=ChunkStorageConfig(
                enabled=True,
                store_text=True,
            ),
            chunk_linking=ChunkLinkingConfig(
                sequential=True,
                to_document=True,
            ),
            metadata=MetadataExtractionConfig(
                page_numbers=PageNumberConfig(enabled=True),
                section_headings=SectionHeadingConfig(enabled=True),
                temporal_references=TemporalReferenceConfig(
                    enabled=True,
                    extract_dates=True,
                    extract_durations=True,
                    extract_relative=False,
                ),
                key_terms=KeyTermConfig(
                    enabled=True,
                    method="simple",
                    max_terms=8,
                ),
                statistics=StatisticsConfig(
                    word_count=True,
                    char_count=True,
                    sentence_count=False,
                ),
            ),
            entity_linking=EntityLinkingConfig(
                enabled=True,
                store_source_text=False,
            ),
            validation=ValidationConfig(
                mode="warn",  # Default: log issues but store everything
                log_level="info",
            ),
        ),
        retrieval=RetrievalStrategy(
            name="balanced",
            description="Balanced retrieval - graph + text search",
            search=SearchConfig(
                graph_traversal=GraphTraversalConfig(enabled=True, max_depth=2),
                chunk_text_search=ChunkTextSearchConfig(enabled=True, method="contains"),
                keyword_matching=KeywordMatchingConfig(enabled=True, match_threshold=0.5),
                temporal_filtering=TemporalFilteringConfig(enabled=True, auto_detect=True),
            ),
            context=ContextConfig(
                expand_neighbors=NeighborExpansionConfig(enabled=True, before=1, after=1),
                include_metadata=IncludeMetadataConfig(
                    section_heading=True,
                    page_number=True,
                    temporal_refs=False,
                    key_terms=False,
                ),
            ),
            scoring=ScoringConfig(
                entity_confidence_min=0.5,
                graph_match_weight=1.5,
                text_match_weight=1.0,
            ),
            limits=LimitsConfig(
                max_chunks=10,
                max_entities=20,
                max_context_tokens=4000,
            ),
        ),
    )


def _create_comprehensive_preset() -> CombinedStrategy:
    """
    Comprehensive preset - all features enabled.
    
    Use case: Deep analysis of complex documents like legal contracts,
    research papers, or technical specifications.
    """
    return CombinedStrategy(
        extraction=ExtractionStrategy(
            name="comprehensive",
            description="Comprehensive extraction - all metadata enabled",
            chunking=ChunkingConfig(
                strategy="fixed",
                chunk_size=800,  # Smaller chunks for better precision
                chunk_overlap=200,
            ),
            chunks=ChunkStorageConfig(
                enabled=True,
                store_text=True,
                max_text_length=0,  # No limit
            ),
            chunk_linking=ChunkLinkingConfig(
                sequential=True,
                to_document=True,
            ),
            metadata=MetadataExtractionConfig(
                page_numbers=PageNumberConfig(enabled=True),
                section_headings=SectionHeadingConfig(enabled=True),
                temporal_references=TemporalReferenceConfig(
                    enabled=True,
                    extract_dates=True,
                    extract_durations=True,
                    extract_relative=True,
                ),
                key_terms=KeyTermConfig(
                    enabled=True,
                    method="simple",  # Can be changed to "llm" for better results
                    max_terms=15,
                ),
                statistics=StatisticsConfig(
                    word_count=True,
                    char_count=True,
                    sentence_count=True,
                ),
            ),
            entity_linking=EntityLinkingConfig(
                enabled=True,
                store_source_text=True,
                store_chunk_index=True,
            ),
            validation=ValidationConfig(
                mode="store_valid",  # Only store entities that pass validation
                log_level="info",
                fail_on_missing_required=True,  # Stricter: require all required props
            ),
        ),
        retrieval=RetrievalStrategy(
            name="comprehensive",
            description="Comprehensive retrieval - all search methods",
            search=SearchConfig(
                graph_traversal=GraphTraversalConfig(enabled=True, max_depth=3),
                chunk_text_search=ChunkTextSearchConfig(enabled=True, method="contains"),
                keyword_matching=KeywordMatchingConfig(enabled=True, match_threshold=0.4),
                temporal_filtering=TemporalFilteringConfig(enabled=True, auto_detect=True),
            ),
            context=ContextConfig(
                expand_neighbors=NeighborExpansionConfig(enabled=True, before=2, after=2),
                include_metadata=IncludeMetadataConfig(
                    section_heading=True,
                    page_number=True,
                    temporal_refs=True,
                    key_terms=True,
                ),
            ),
            scoring=ScoringConfig(
                entity_confidence_min=0.4,
                graph_match_weight=1.5,
                text_match_weight=1.2,
            ),
            limits=LimitsConfig(
                max_chunks=15,
                max_entities=30,
                max_context_tokens=6000,
            ),
        ),
    )


def _create_speed_preset() -> CombinedStrategy:
    """
    Speed preset - optimized for fast processing.
    
    Use case: High-volume document processing where speed matters
    more than comprehensive metadata extraction.
    """
    return CombinedStrategy(
        extraction=ExtractionStrategy(
            name="speed",
            description="Speed optimized - minimal metadata, fast processing",
            chunking=ChunkingConfig(
                strategy="fixed",
                chunk_size=2000,  # Larger chunks for fewer LLM calls
                chunk_overlap=100,
            ),
            chunks=ChunkStorageConfig(
                enabled=True,
                store_text=True,
                max_text_length=2000,  # Limit text storage
            ),
            chunk_linking=ChunkLinkingConfig(
                sequential=True,
                to_document=True,
            ),
            metadata=MetadataExtractionConfig(
                page_numbers=PageNumberConfig(enabled=True),
                section_headings=SectionHeadingConfig(enabled=False),  # Skip regex
                temporal_references=TemporalReferenceConfig(enabled=False),  # Skip parsing
                key_terms=KeyTermConfig(enabled=False),  # Skip extraction
                statistics=StatisticsConfig(
                    word_count=True,
                    char_count=False,
                    sentence_count=False,
                ),
            ),
            entity_linking=EntityLinkingConfig(
                enabled=True,
                store_source_text=False,
            ),
            validation=ValidationConfig(
                mode="ignore",  # Skip validation for speed
                log_level="warning",
            ),
        ),
        retrieval=RetrievalStrategy(
            name="speed",
            description="Speed optimized - graph only, limited context",
            search=SearchConfig(
                graph_traversal=GraphTraversalConfig(enabled=True, max_depth=1),
                chunk_text_search=ChunkTextSearchConfig(enabled=True, method="contains"),
                keyword_matching=KeywordMatchingConfig(enabled=False),
                temporal_filtering=TemporalFilteringConfig(enabled=False),
            ),
            context=ContextConfig(
                expand_neighbors=NeighborExpansionConfig(enabled=False),
                include_metadata=IncludeMetadataConfig(
                    section_heading=False,
                    page_number=True,
                    temporal_refs=False,
                    key_terms=False,
                ),
            ),
            scoring=ScoringConfig(
                entity_confidence_min=0.6,
                graph_match_weight=1.0,
                text_match_weight=1.0,
            ),
            limits=LimitsConfig(
                max_chunks=5,
                max_entities=10,
                max_context_tokens=2000,
            ),
        ),
    )


def _create_research_preset() -> CombinedStrategy:
    """
    Research preset - optimized for academic papers.
    
    Use case: Research papers, academic documents where citations,
    key terms, and section structure are important.
    """
    return CombinedStrategy(
        extraction=ExtractionStrategy(
            name="research",
            description="Research optimized - key terms, citations, sections",
            chunking=ChunkingConfig(
                strategy="fixed",
                chunk_size=1200,
                chunk_overlap=200,
            ),
            chunks=ChunkStorageConfig(
                enabled=True,
                store_text=True,
            ),
            chunk_linking=ChunkLinkingConfig(
                sequential=True,
                to_document=True,
            ),
            metadata=MetadataExtractionConfig(
                page_numbers=PageNumberConfig(enabled=True),
                section_headings=SectionHeadingConfig(
                    enabled=True,
                    patterns=[
                        r"^(Abstract|Introduction|Methods?|Results?|Discussion|Conclusion|References)",
                        r"^\d+\.\s+[A-Z]",
                        r"^[A-Z][A-Z\s]{3,}$",
                    ],
                ),
                temporal_references=TemporalReferenceConfig(
                    enabled=True,
                    extract_dates=True,
                    extract_durations=False,
                    extract_relative=False,
                ),
                key_terms=KeyTermConfig(
                    enabled=True,
                    method="simple",
                    max_terms=15,
                ),
                statistics=StatisticsConfig(
                    word_count=True,
                    char_count=False,
                    sentence_count=True,
                ),
            ),
            entity_linking=EntityLinkingConfig(
                enabled=True,
                store_source_text=False,
            ),
            validation=ValidationConfig(
                mode="warn",  # Log issues but don't block - research docs can be messy
                log_level="info",
            ),
        ),
        retrieval=RetrievalStrategy(
            name="research",
            description="Research optimized - keyword focus, section context",
            search=SearchConfig(
                graph_traversal=GraphTraversalConfig(enabled=True, max_depth=2),
                chunk_text_search=ChunkTextSearchConfig(enabled=True, method="contains"),
                keyword_matching=KeywordMatchingConfig(enabled=True, match_threshold=0.4),
                temporal_filtering=TemporalFilteringConfig(enabled=False),
            ),
            context=ContextConfig(
                expand_neighbors=NeighborExpansionConfig(enabled=True, before=1, after=1),
                include_metadata=IncludeMetadataConfig(
                    section_heading=True,
                    page_number=True,
                    temporal_refs=False,
                    key_terms=True,
                ),
            ),
            scoring=ScoringConfig(
                entity_confidence_min=0.5,
                graph_match_weight=1.2,
                text_match_weight=1.5,  # Higher weight for text in research
            ),
            limits=LimitsConfig(
                max_chunks=12,
                max_entities=25,
                max_context_tokens=5000,
            ),
        ),
    )


def _create_strict_preset() -> CombinedStrategy:
    """
    Strict preset - high data quality focus.
    
    Use case: When data quality is paramount, only store fully 
    validated entities. Good for compliance or regulated data.
    """
    return CombinedStrategy(
        extraction=ExtractionStrategy(
            name="strict",
            description="Strict extraction - only validated entities stored",
            chunking=ChunkingConfig(
                strategy="fixed",
                chunk_size=800,
                chunk_overlap=200,
            ),
            chunks=ChunkStorageConfig(
                enabled=True,
                store_text=True,
            ),
            chunk_linking=ChunkLinkingConfig(
                sequential=True,
                to_document=True,
            ),
            metadata=MetadataExtractionConfig(
                page_numbers=PageNumberConfig(enabled=True),
                section_headings=SectionHeadingConfig(enabled=True),
                temporal_references=TemporalReferenceConfig(
                    enabled=True,
                    extract_dates=True,
                    extract_durations=True,
                    extract_relative=False,
                ),
                key_terms=KeyTermConfig(
                    enabled=True,
                    method="simple",
                    max_terms=10,
                ),
                statistics=StatisticsConfig(
                    word_count=True,
                    char_count=True,
                    sentence_count=False,
                ),
            ),
            entity_linking=EntityLinkingConfig(
                enabled=True,
                store_source_text=False,
            ),
            validation=ValidationConfig(
                mode="strict",  # Block if ANY errors
                log_level="info",
                fail_on_missing_required=True,
                fail_on_broken_relationships=True,
            ),
        ),
        retrieval=RetrievalStrategy(
            name="strict",
            description="Strict retrieval - high confidence matches only",
            search=SearchConfig(
                graph_traversal=GraphTraversalConfig(enabled=True, max_depth=2),
                chunk_text_search=ChunkTextSearchConfig(enabled=True, method="contains"),
                keyword_matching=KeywordMatchingConfig(enabled=True, match_threshold=0.6),
                temporal_filtering=TemporalFilteringConfig(enabled=True, auto_detect=True),
            ),
            context=ContextConfig(
                expand_neighbors=NeighborExpansionConfig(enabled=True, before=1, after=1),
                include_metadata=IncludeMetadataConfig(
                    section_heading=True,
                    page_number=True,
                    temporal_refs=True,
                    key_terms=False,
                ),
            ),
            scoring=ScoringConfig(
                entity_confidence_min=0.7,  # High confidence threshold
                graph_match_weight=1.5,
                text_match_weight=1.0,
            ),
            limits=LimitsConfig(
                max_chunks=10,
                max_entities=20,
                max_context_tokens=4000,
            ),
        ),
    )


# =============================================================================
# PRESET REGISTRY
# =============================================================================


PRESETS: dict[str, CombinedStrategy] = {
    "minimal": _create_minimal_preset(),
    "balanced": _create_balanced_preset(),
    "comprehensive": _create_comprehensive_preset(),
    "speed": _create_speed_preset(),
    "research": _create_research_preset(),
    "strict": _create_strict_preset(),
}


def get_preset(name: str) -> CombinedStrategy:
    """
    Get a preset by name.
    
    Args:
        name: Preset name (minimal, balanced, comprehensive, speed, research, strict)
        
    Returns:
        CombinedStrategy with both extraction and retrieval strategies
        
    Raises:
        KeyError: If preset name is not found
    """
    if name not in PRESETS:
        available = ", ".join(PRESETS.keys())
        raise KeyError(f"Unknown preset '{name}'. Available: {available}")
    return PRESETS[name].model_copy(deep=True)


def list_presets() -> list[dict]:
    """
    List all available presets with descriptions.
    
    Returns:
        List of dicts with preset name and description
    """
    return [
        {
            "name": name,
            "extraction_description": preset.extraction.description,
            "retrieval_description": preset.retrieval.description,
        }
        for name, preset in PRESETS.items()
    ]
