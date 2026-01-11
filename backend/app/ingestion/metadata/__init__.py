"""
Metadata extraction utilities.

NOTE: Primary metadata extraction (sections, temporal refs, key terms)
is now done via LLM in DynamicExtractor.extract_chunk().

These utilities are kept for:
- Pre-processing hints to help LLM
- Validation/verification of LLM output
- Low-cost pattern matching when LLM is not needed
"""

from .section_extractor import SectionExtractor
from .temporal_extractor import TemporalExtractor
from .term_extractor import TermExtractor

__all__ = [
    "SectionExtractor",
    "TemporalExtractor",
    "TermExtractor",
]
