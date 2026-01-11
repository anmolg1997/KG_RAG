"""
Strategy manager for loading, saving, and applying strategies.

The strategy manager maintains the current active strategies and provides
methods to switch between presets or custom configurations.
"""

import logging
from pathlib import Path
from typing import Optional

import yaml

from app.config import settings
from .models import ExtractionStrategy, RetrievalStrategy, CombinedStrategy
from .presets import PRESETS, get_preset

logger = logging.getLogger(__name__)


class StrategyManager:
    """
    Manages extraction and retrieval strategies.
    
    Maintains current active strategies and provides methods to:
    - Load strategies from presets or files
    - Save custom strategies
    - Get current active strategies
    - Update strategies at runtime
    """
    
    def __init__(self, default_preset: str = "balanced"):
        """
        Initialize the strategy manager.
        
        Args:
            default_preset: Name of the default preset to use
        """
        self._extraction_strategy: Optional[ExtractionStrategy] = None
        self._retrieval_strategy: Optional[RetrievalStrategy] = None
        self._current_preset: Optional[str] = None
        
        # Load default preset
        self.load_preset(default_preset)
    
    @property
    def extraction(self) -> ExtractionStrategy:
        """Get current extraction strategy."""
        if self._extraction_strategy is None:
            self.load_preset("balanced")
        return self._extraction_strategy
    
    @property
    def retrieval(self) -> RetrievalStrategy:
        """Get current retrieval strategy."""
        if self._retrieval_strategy is None:
            self.load_preset("balanced")
        return self._retrieval_strategy
    
    @property
    def current_preset(self) -> Optional[str]:
        """Get name of current preset (None if custom)."""
        return self._current_preset
    
    def load_preset(self, name: str) -> CombinedStrategy:
        """
        Load a preset by name.
        
        Args:
            name: Preset name (minimal, balanced, comprehensive, speed, research)
            
        Returns:
            The loaded CombinedStrategy
        """
        preset = get_preset(name)
        self._extraction_strategy = preset.extraction
        self._retrieval_strategy = preset.retrieval
        self._current_preset = name
        logger.info(f"Loaded preset: {name}")
        return preset
    
    def set_extraction_strategy(self, strategy: ExtractionStrategy) -> None:
        """
        Set a custom extraction strategy.
        
        Args:
            strategy: ExtractionStrategy instance
        """
        self._extraction_strategy = strategy
        self._current_preset = None  # Custom strategy
        logger.info(f"Set custom extraction strategy: {strategy.name}")
    
    def set_retrieval_strategy(self, strategy: RetrievalStrategy) -> None:
        """
        Set a custom retrieval strategy.
        
        Args:
            strategy: RetrievalStrategy instance
        """
        self._retrieval_strategy = strategy
        self._current_preset = None  # Custom strategy
        logger.info(f"Set custom retrieval strategy: {strategy.name}")
    
    def update_extraction_strategy(self, updates: dict) -> ExtractionStrategy:
        """
        Update current extraction strategy with partial updates.
        
        Args:
            updates: Dictionary of updates to apply
            
        Returns:
            Updated ExtractionStrategy
        """
        current_dict = self._extraction_strategy.model_dump()
        self._deep_update(current_dict, updates)
        self._extraction_strategy = ExtractionStrategy(**current_dict)
        self._current_preset = None  # Now custom
        return self._extraction_strategy
    
    def update_retrieval_strategy(self, updates: dict) -> RetrievalStrategy:
        """
        Update current retrieval strategy with partial updates.
        
        Args:
            updates: Dictionary of updates to apply
            
        Returns:
            Updated RetrievalStrategy
        """
        current_dict = self._retrieval_strategy.model_dump()
        self._deep_update(current_dict, updates)
        self._retrieval_strategy = RetrievalStrategy(**current_dict)
        self._current_preset = None  # Now custom
        return self._retrieval_strategy
    
    def save_to_file(self, filepath: Path) -> None:
        """
        Save current strategies to a YAML file.
        
        Args:
            filepath: Path to save the file
        """
        combined = CombinedStrategy(
            extraction=self._extraction_strategy,
            retrieval=self._retrieval_strategy,
        )
        
        with open(filepath, "w") as f:
            yaml.dump(combined.model_dump(), f, default_flow_style=False)
        
        logger.info(f"Saved strategies to: {filepath}")
    
    def load_from_file(self, filepath: Path) -> CombinedStrategy:
        """
        Load strategies from a YAML file.
        
        Args:
            filepath: Path to the YAML file
            
        Returns:
            Loaded CombinedStrategy
        """
        with open(filepath) as f:
            data = yaml.safe_load(f)
        
        combined = CombinedStrategy(**data)
        self._extraction_strategy = combined.extraction
        self._retrieval_strategy = combined.retrieval
        self._current_preset = None  # Custom from file
        
        logger.info(f"Loaded strategies from: {filepath}")
        return combined
    
    def get_combined(self) -> CombinedStrategy:
        """
        Get current strategies as a CombinedStrategy.
        
        Returns:
            CombinedStrategy with current extraction and retrieval strategies
        """
        return CombinedStrategy(
            extraction=self._extraction_strategy,
            retrieval=self._retrieval_strategy,
        )
    
    def get_status(self) -> dict:
        """
        Get current strategy status for API responses.
        
        Returns:
            Dictionary with current strategy information
        """
        return {
            "current_preset": self._current_preset,
            "extraction": {
                "name": self._extraction_strategy.name,
                "description": self._extraction_strategy.description,
                "chunks_enabled": self._extraction_strategy.chunks.enabled,
                "metadata_enabled": {
                    "page_numbers": self._extraction_strategy.metadata.page_numbers.enabled,
                    "section_headings": self._extraction_strategy.metadata.section_headings.enabled,
                    "temporal_references": self._extraction_strategy.metadata.temporal_references.enabled,
                    "key_terms": self._extraction_strategy.metadata.key_terms.enabled,
                },
                "entity_linking": self._extraction_strategy.entity_linking.enabled,
            },
            "retrieval": {
                "name": self._retrieval_strategy.name,
                "description": self._retrieval_strategy.description,
                "search_methods": {
                    "graph_traversal": self._retrieval_strategy.search.graph_traversal.enabled,
                    "chunk_text_search": self._retrieval_strategy.search.chunk_text_search.enabled,
                    "keyword_matching": self._retrieval_strategy.search.keyword_matching.enabled,
                    "temporal_filtering": self._retrieval_strategy.search.temporal_filtering.enabled,
                },
                "context_expansion": self._retrieval_strategy.context.expand_neighbors.enabled,
            },
        }
    
    @staticmethod
    def _deep_update(base: dict, updates: dict) -> None:
        """
        Recursively update a dictionary.
        
        Args:
            base: Base dictionary to update
            updates: Updates to apply
        """
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                StrategyManager._deep_update(base[key], value)
            else:
                base[key] = value


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================


_strategy_manager: Optional[StrategyManager] = None


def get_strategy_manager() -> StrategyManager:
    """
    Get the singleton StrategyManager instance.
    
    Returns:
        StrategyManager singleton
    """
    global _strategy_manager
    if _strategy_manager is None:
        default_preset = getattr(settings, "default_strategy_preset", "balanced")
        _strategy_manager = StrategyManager(default_preset=default_preset)
    return _strategy_manager


def reset_strategy_manager() -> None:
    """Reset the singleton for testing purposes."""
    global _strategy_manager
    _strategy_manager = None
