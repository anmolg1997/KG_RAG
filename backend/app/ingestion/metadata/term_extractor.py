"""
Key term extraction utilities.

NOTE: Primary key term extraction is done via LLM in DynamicExtractor.
This utility is for low-cost frequency-based extraction or validation.
"""

import re
import logging
from typing import Optional
from collections import Counter

logger = logging.getLogger(__name__)


class TermExtractor:
    """
    Pattern and frequency-based key term extraction utility.
    
    Used for:
    - Pre-processing hints before LLM extraction
    - Validation of LLM-extracted terms
    - Low-cost extraction when LLM is not available/needed
    
    Usage:
        extractor = TermExtractor()
        terms = extractor.extract_from_chunk(text, max_terms=10)
        print(terms)  # ['contract', 'agreement', 'party', ...]
    """
    
    # Common stopwords (extended for legal/business documents)
    STOPWORDS = {
        # Standard English stopwords
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
        "has", "he", "in", "is", "it", "its", "of", "on", "or", "that",
        "the", "to", "was", "were", "will", "with", "this", "these",
        "those", "such", "have", "had", "been", "being", "their", "they",
        "them", "which", "who", "whom", "would", "could", "should", "may",
        "shall", "must", "can", "any", "all", "each", "every", "other",
        "some", "no", "not", "only", "same", "so", "than", "too", "very",
        "just", "also", "now", "here", "there", "when", "where", "why",
        "how", "what", "if", "then", "else", "but", "however", "therefore",
        # Legal/business stopwords
        "hereby", "herein", "hereto", "hereof", "thereof", "thereto",
        "wherein", "whereas", "whereof", "hereunder", "thereunder",
        "pursuant", "notwithstanding", "provided", "including", "without",
        "upon", "between", "among", "under", "above", "below", "during",
        "before", "after", "until", "unless", "except", "regarding",
    }
    
    # Patterns for defined terms (often quoted or capitalized)
    DEFINED_TERM_PATTERNS = [
        r'"([A-Z][^"]{2,50})"',           # "Defined Term"
        r"'([A-Z][^']{2,50})'",           # 'Defined Term'
        r"\(the\s+\"([^\"]+)\"\)",        # (the "Term")
        r"\(\"([^\"]+)\"\)",              # ("Term")
        r"(?:means|refers\s+to|shall\s+mean)\s+([A-Za-z][^\.\,]{3,50})",  # means XYZ
    ]
    
    def __init__(
        self,
        method: str = "frequency",
        additional_stopwords: Optional[set[str]] = None,
    ):
        """
        Initialize term extractor.
        
        Args:
            method: Extraction method - 'frequency' or 'tfidf'
            additional_stopwords: Extra words to exclude
        """
        self.method = method
        self.stopwords = self.STOPWORDS.copy()
        if additional_stopwords:
            self.stopwords.update(additional_stopwords)
        
        self._defined_patterns = [
            re.compile(p, re.IGNORECASE) 
            for p in self.DEFINED_TERM_PATTERNS
        ]
    
    def extract_from_chunk(
        self,
        text: str,
        max_terms: int = 10,
    ) -> list[str]:
        """
        Extract key terms from text chunk.
        
        Returns:
            List of key terms ordered by importance
        """
        terms = []
        
        # First, get defined terms (highest priority)
        defined = self._extract_defined_terms(text)
        terms.extend(defined[:max_terms // 2])
        
        # Then get frequency-based terms
        if len(terms) < max_terms:
            freq_terms = self._extract_by_frequency(
                text, 
                max_terms - len(terms),
                exclude=set(t.lower() for t in terms),
            )
            terms.extend(freq_terms)
        
        return terms[:max_terms]
    
    def _extract_defined_terms(self, text: str) -> list[str]:
        """Extract explicitly defined terms (quoted or marked)."""
        terms = []
        
        for pattern in self._defined_patterns:
            for match in pattern.finditer(text):
                term = match.group(1).strip()
                # Clean up common artifacts
                term = re.sub(r'\s+', ' ', term)
                if term and len(term) > 2 and term not in terms:
                    terms.append(term)
        
        return terms
    
    def _extract_by_frequency(
        self,
        text: str,
        max_terms: int,
        exclude: Optional[set[str]] = None,
    ) -> list[str]:
        """Extract terms by word frequency."""
        exclude = exclude or set()
        
        # Tokenize - keep multi-word capitalized phrases
        words = re.findall(r'\b[A-Za-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        
        # Filter and normalize
        filtered = []
        for word in words:
            word_lower = word.lower()
            if (
                word_lower not in self.stopwords
                and word_lower not in exclude
                and len(word) > 2
                and not word.isdigit()
            ):
                # Keep original case for proper nouns, lowercase for others
                if word[0].isupper() and len(word) > 1 and word[1].islower():
                    filtered.append(word)  # Proper noun
                else:
                    filtered.append(word_lower)
        
        # Count frequencies
        freq = Counter(filtered)
        
        # Get most common
        return [term for term, _ in freq.most_common(max_terms)]
    
    def extract_acronyms(self, text: str) -> list[dict]:
        """
        Extract acronyms and their definitions.
        
        Returns:
            List of dicts with 'acronym' and 'definition'
        """
        results = []
        
        # Pattern: "Securities and Exchange Commission (SEC)" or "(SEC)"
        pattern = r'([A-Za-z][a-z]+(?:\s+(?:and|of|the|for|to|in)\s+)?(?:[A-Za-z][a-z]+\s*)+)\s*\(([A-Z]{2,6})\)'
        
        for match in re.finditer(pattern, text):
            definition = match.group(1).strip()
            acronym = match.group(2)
            
            # Verify acronym matches definition initials
            initials = ''.join(
                word[0].upper() 
                for word in definition.split() 
                if word[0].isupper() or word in ['and', 'of', 'the', 'for', 'to', 'in']
            )
            
            if acronym in initials or len(acronym) <= len(definition.split()):
                results.append({
                    "acronym": acronym,
                    "definition": definition,
                })
        
        return results
    
    def validate_terms(self, terms: list[str], text: str) -> list[str]:
        """
        Validate that terms appear in text.
        
        Useful for verifying LLM-extracted terms.
        """
        text_lower = text.lower()
        return [t for t in terms if t.lower() in text_lower]
    
    def score_term_relevance(
        self,
        term: str,
        text: str,
        document_freq: Optional[dict] = None,
    ) -> float:
        """
        Score a term's relevance to the text.
        
        Args:
            term: Term to score
            text: Text context
            document_freq: Optional dict of term -> document frequency
            
        Returns:
            Relevance score (0-1)
        """
        term_lower = term.lower()
        text_lower = text.lower()
        
        # Count occurrences
        count = text_lower.count(term_lower)
        if count == 0:
            return 0.0
        
        # Base score from frequency
        word_count = len(text.split())
        term_freq = count / max(word_count, 1)
        
        # Boost for defined terms
        if f'"{term}"' in text or f"'{term}'" in text:
            term_freq *= 2.0
        
        # IDF adjustment if document frequencies provided
        if document_freq and term_lower in document_freq:
            idf = 1.0 / (1.0 + document_freq[term_lower])
            term_freq *= idf
        
        # Normalize to 0-1
        return min(1.0, term_freq * 10)
