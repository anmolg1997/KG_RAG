"""
Section heading extraction utilities.

NOTE: Primary section extraction is done via LLM in DynamicExtractor.
This utility is for pattern-based pre-processing or validation.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SectionExtractor:
    """
    Pattern-based section heading detection utility.
    
    Used for:
    - Pre-processing hints before LLM extraction
    - Validation of LLM-extracted sections
    - Low-cost pattern matching when LLM is overkill
    
    Usage:
        extractor = SectionExtractor()
        section = extractor.find_heading(text)
        if section:
            print(f"Found: {section['heading']} at level {section['level']}")
    """
    
    # Default patterns for common document structures
    DEFAULT_PATTERNS = [
        # ARTICLE I: Title or Article 5. Title
        (r'^(ARTICLE|Article)\s+([IVXLCDM\d]+)[.:)]\s*(.*?)(?:\n|$)', 1),
        # SECTION 1.1: Title or Section 3.2.1 Title  
        (r'^(SECTION|Section)\s+([\d.]+)[.:)]\s*(.*?)(?:\n|$)', 2),
        # All caps heading on its own line
        (r'^([A-Z][A-Z\s]{3,50})(?:\n|$)', 2),
        # Numbered heading: "1. Title" or "1.1 Title"
        (r'^([\d.]+)\s+([A-Z][^.\n]{5,60})(?:\n|$)', 3),
        # Lettered sections: "(a) Title" or "a) Title"
        (r'^\(?([a-z])\)[.\s]+([A-Z][^.\n]{5,60})(?:\n|$)', 4),
    ]
    
    def __init__(self, patterns: Optional[list[tuple[str, int]]] = None):
        """
        Initialize with custom patterns.
        
        Args:
            patterns: List of (regex_pattern, level) tuples.
                     Level indicates hierarchy depth (1=top, 2=sub, etc.)
        """
        self.patterns = patterns or self.DEFAULT_PATTERNS
        self._compiled = [
            (re.compile(p, re.MULTILINE), level) 
            for p, level in self.patterns
        ]
    
    def find_heading(self, text: str) -> Optional[dict]:
        """
        Find the first section heading in text.
        
        Returns:
            Dict with 'heading', 'level', 'start', 'end' or None
        """
        text = text.strip()
        
        for pattern, level in self._compiled:
            match = pattern.search(text)
            if match:
                # Extract full heading text
                groups = match.groups()
                heading = " ".join(g.strip() for g in groups if g).strip()
                
                return {
                    "heading": heading,
                    "level": level,
                    "start": match.start(),
                    "end": match.end(),
                    "raw_match": match.group(0),
                }
        
        return None
    
    def find_all_headings(self, text: str) -> list[dict]:
        """
        Find all section headings in text.
        
        Returns:
            List of heading dicts sorted by position
        """
        results = []
        
        for pattern, level in self._compiled:
            for match in pattern.finditer(text):
                groups = match.groups()
                heading = " ".join(g.strip() for g in groups if g).strip()
                
                results.append({
                    "heading": heading,
                    "level": level,
                    "start": match.start(),
                    "end": match.end(),
                    "raw_match": match.group(0),
                })
        
        # Sort by position
        return sorted(results, key=lambda x: x["start"])
    
    def get_section_for_chunk(
        self,
        full_text: str,
        chunk_start: int,
        chunk_end: int,
    ) -> Optional[str]:
        """
        Find the section heading that contains a chunk position.
        
        Looks backwards from chunk_start to find the most recent heading.
        
        Args:
            full_text: Complete document text
            chunk_start: Start character position of chunk
            chunk_end: End character position of chunk
            
        Returns:
            Section heading string or None
        """
        # Get all headings before this position
        all_headings = self.find_all_headings(full_text[:chunk_start + 500])
        
        # Find the last heading before or within the chunk
        current_section = None
        for heading in all_headings:
            if heading["start"] <= chunk_start:
                current_section = heading["heading"]
        
        return current_section
    
    def validate_section(self, section: str, text: str) -> bool:
        """
        Validate that a section heading appears in text.
        
        Useful for verifying LLM-extracted sections.
        """
        if not section:
            return False
        
        # Check if section appears in text (case-insensitive)
        return section.lower() in text.lower()
