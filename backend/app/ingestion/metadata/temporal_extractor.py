"""
Temporal reference extraction utilities.

NOTE: Primary temporal extraction is done via LLM in DynamicExtractor.
This utility is for pattern-based pre-processing or validation.
"""

import re
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TemporalExtractor:
    """
    Pattern-based temporal reference detection utility.
    
    Used for:
    - Pre-processing hints before LLM extraction
    - Validation of LLM-extracted temporal references
    - Low-cost pattern matching when LLM is overkill
    
    Usage:
        extractor = TemporalExtractor()
        refs = extractor.extract_all(text)
        for ref in refs:
            print(f"{ref['type']}: {ref['text']}")
    """
    
    # Date patterns
    DATE_PATTERNS = [
        # "January 15, 2024" or "Jan 15, 2024"
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[.\s]+\d{1,2}[,\s]+\d{4}\b',
        # "15 January 2024" or "15 Jan 2024"
        r'\b\d{1,2}[.\s]+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[,\s]+\d{4}\b',
        # "2024-01-15" or "2024/01/15"
        r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b',
        # "01/15/2024" or "01-15-2024" (US format)
        r'\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b',
        # "Q1 2024" or "Q4 2023"
        r'\b[Qq][1-4]\s+\d{4}\b',
        # "FY2024" or "FY 2024"
        r'\b[Ff][Yy]\s*\d{4}\b',
    ]
    
    # Duration patterns
    DURATION_PATTERNS = [
        # "30 days" or "sixty (60) days"
        r'\b(?:(?:\w+\s+)?\(?\d+\)?\s+)?(?:calendar\s+|business\s+|working\s+)?(?:days?|weeks?|months?|quarters?|years?)\b',
        # "one year" or "three months"
        r'\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(?:days?|weeks?|months?|quarters?|years?)\b',
        # "a quarter" or "a year"
        r'\ba\s+(?:day|week|month|quarter|year)\b',
    ]
    
    # Relative temporal patterns
    RELATIVE_PATTERNS = [
        r'\b(?:effective\s+date|commencement\s+date|termination\s+date|closing\s+date|execution\s+date)\b',
        r'\b(?:upon|after|before|prior\s+to|following|within)\s+(?:signing|execution|termination|closing|expiration)\b',
        r'\b(?:immediately|promptly|forthwith)\s+(?:upon|after|following)\b',
        r'\b(?:at\s+any\s+time|from\s+time\s+to\s+time)\b',
        r'\b(?:until|unless|so\s+long\s+as)\b',
    ]
    
    def __init__(
        self,
        extract_dates: bool = True,
        extract_durations: bool = True,
        extract_relative: bool = True,
    ):
        """
        Initialize with extraction options.
        
        Args:
            extract_dates: Whether to extract absolute dates
            extract_durations: Whether to extract time durations
            extract_relative: Whether to extract relative references
        """
        self.extract_dates = extract_dates
        self.extract_durations = extract_durations
        self.extract_relative = extract_relative
        
        # Compile patterns
        self._date_patterns = [re.compile(p, re.IGNORECASE) for p in self.DATE_PATTERNS]
        self._duration_patterns = [re.compile(p, re.IGNORECASE) for p in self.DURATION_PATTERNS]
        self._relative_patterns = [re.compile(p, re.IGNORECASE) for p in self.RELATIVE_PATTERNS]
    
    def extract_all(self, text: str) -> list[dict]:
        """
        Extract all temporal references from text.
        
        Returns:
            List of dicts with 'type', 'text', 'start', 'end'
        """
        results = []
        
        if self.extract_dates:
            results.extend(self._extract_by_type(text, self._date_patterns, "date"))
        
        if self.extract_durations:
            results.extend(self._extract_by_type(text, self._duration_patterns, "duration"))
        
        if self.extract_relative:
            results.extend(self._extract_by_type(text, self._relative_patterns, "relative"))
        
        # Sort by position and deduplicate overlapping
        results = sorted(results, key=lambda x: x["start"])
        return self._remove_overlapping(results)
    
    def extract_from_chunk(self, text: str) -> list[dict]:
        """
        Extract temporal references formatted for chunk metadata.
        
        Returns:
            List of dicts suitable for chunk metadata storage
        """
        raw_refs = self.extract_all(text)
        
        return [
            {
                "type": ref["type"],
                "text": ref["text"],
                "normalized": self._normalize(ref["text"], ref["type"]),
            }
            for ref in raw_refs
        ]
    
    def _extract_by_type(
        self,
        text: str,
        patterns: list[re.Pattern],
        ref_type: str,
    ) -> list[dict]:
        """Extract references of a specific type."""
        results = []
        
        for pattern in patterns:
            for match in pattern.finditer(text):
                results.append({
                    "type": ref_type,
                    "text": match.group(0).strip(),
                    "start": match.start(),
                    "end": match.end(),
                })
        
        return results
    
    def _remove_overlapping(self, refs: list[dict]) -> list[dict]:
        """Remove overlapping references, keeping longer ones."""
        if not refs:
            return []
        
        filtered = []
        for ref in refs:
            # Check if this overlaps with last added
            if filtered and ref["start"] < filtered[-1]["end"]:
                # Keep the longer one
                if len(ref["text"]) > len(filtered[-1]["text"]):
                    filtered[-1] = ref
            else:
                filtered.append(ref)
        
        return filtered
    
    def _normalize(self, text: str, ref_type: str) -> Optional[str]:
        """
        Attempt to normalize temporal reference to standard format.
        
        Returns:
            Normalized string or None if not normalizable
        """
        text = text.lower().strip()
        
        if ref_type == "date":
            return self._normalize_date(text)
        elif ref_type == "duration":
            return self._normalize_duration(text)
        else:
            return None
    
    def _normalize_date(self, text: str) -> Optional[str]:
        """Try to parse date to ISO format."""
        # Common formats to try
        formats = [
            "%B %d, %Y",      # January 15, 2024
            "%b %d, %Y",      # Jan 15, 2024
            "%d %B %Y",       # 15 January 2024
            "%d %b %Y",       # 15 Jan 2024
            "%Y-%m-%d",       # 2024-01-15
            "%Y/%m/%d",       # 2024/01/15
            "%m/%d/%Y",       # 01/15/2024
            "%m-%d-%Y",       # 01-15-2024
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(text, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        return None
    
    def _normalize_duration(self, text: str) -> Optional[str]:
        """Normalize duration to standard format."""
        # Word to number mapping
        words = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "eleven": 11, "twelve": 12, "a": 1,
        }
        
        text_lower = text.lower()
        
        # Extract number and unit
        number = 1
        unit = None
        
        # Check for word numbers
        for word, num in words.items():
            if word in text_lower:
                number = num
                break
        
        # Check for numeric values
        numeric_match = re.search(r'\d+', text)
        if numeric_match:
            number = int(numeric_match.group(0))
        
        # Extract unit
        if "year" in text_lower:
            unit = "year"
        elif "month" in text_lower:
            unit = "month"
        elif "quarter" in text_lower:
            unit = "quarter"
        elif "week" in text_lower:
            unit = "week"
        elif "day" in text_lower:
            unit = "day"
        
        if unit:
            plural = "s" if number != 1 else ""
            return f"{number} {unit}{plural}"
        
        return None
    
    def validate_temporal(self, ref: dict, text: str) -> bool:
        """
        Validate that a temporal reference appears in text.
        
        Useful for verifying LLM-extracted references.
        """
        ref_text = ref.get("text", "")
        if not ref_text:
            return False
        
        return ref_text.lower() in text.lower()
