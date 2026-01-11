"""
Strategy system for configurable extraction and retrieval.

This module provides a flexible strategy system that allows users to configure
how documents are processed (extraction) and how information is retrieved (retrieval).
"""

from .models import (
    ExtractionStrategy,
    RetrievalStrategy,
    ChunkStorageConfig,
    ChunkLinkingConfig,
    MetadataExtractionConfig,
    EntityLinkingConfig,
    SearchConfig,
    ContextConfig,
    ScoringConfig,
)
from .manager import StrategyManager, get_strategy_manager
from .presets import PRESETS, get_preset, list_presets

__all__ = [
    # Models
    "ExtractionStrategy",
    "RetrievalStrategy",
    "ChunkStorageConfig",
    "ChunkLinkingConfig",
    "MetadataExtractionConfig",
    "EntityLinkingConfig",
    "SearchConfig",
    "ContextConfig",
    "ScoringConfig",
    # Manager
    "StrategyManager",
    "get_strategy_manager",
    # Presets
    "PRESETS",
    "get_preset",
    "list_presets",
]
