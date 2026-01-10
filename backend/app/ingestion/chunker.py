"""
Text chunking strategies for document processing.

Provides multiple chunking approaches:
- Fixed-size chunking with overlap
- Semantic chunking (paragraph/section aware)
- Token-based chunking
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """A chunk of text with metadata."""
    
    text: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: dict = field(default_factory=dict)
    
    @property
    def char_count(self) -> int:
        return len(self.text)
    
    @property
    def word_count(self) -> int:
        return len(self.text.split())


class TextChunker:
    """
    Text chunking for document processing.
    
    Supports multiple strategies:
    - "fixed": Fixed character count with overlap
    - "sentence": Split on sentence boundaries
    - "paragraph": Split on paragraph boundaries
    - "semantic": Smart splitting based on content structure
    
    Usage:
        chunker = TextChunker(chunk_size=1000, overlap=200)
        chunks = chunker.chunk_text(document_text)
        
        for chunk in chunks:
            print(f"Chunk {chunk.chunk_index}: {chunk.word_count} words")
    """
    
    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        strategy: str = "semantic",
    ):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.strategy = strategy
        
        # Sentence splitting pattern
        self.sentence_pattern = re.compile(
            r'(?<=[.!?])\s+(?=[A-Z])|(?<=\.)\s*\n'
        )
        
        # Section header pattern (for contracts)
        self.section_pattern = re.compile(
            r'^(?:ARTICLE|SECTION|Article|Section)\s+[IVXLCDM\d]+[.:)]?\s*',
            re.MULTILINE
        )
    
    def chunk_text(
        self,
        text: str,
        metadata: Optional[dict] = None,
    ) -> list[TextChunk]:
        """
        Split text into chunks using configured strategy.
        
        Args:
            text: Full text to chunk
            metadata: Optional metadata to attach to all chunks
            
        Returns:
            List of TextChunk objects
        """
        if not text or not text.strip():
            return []
        
        metadata = metadata or {}
        
        if self.strategy == "fixed":
            return self._chunk_fixed(text, metadata)
        elif self.strategy == "sentence":
            return self._chunk_by_sentence(text, metadata)
        elif self.strategy == "paragraph":
            return self._chunk_by_paragraph(text, metadata)
        elif self.strategy == "semantic":
            return self._chunk_semantic(text, metadata)
        else:
            logger.warning(f"Unknown strategy '{self.strategy}', using fixed")
            return self._chunk_fixed(text, metadata)
    
    def _chunk_fixed(
        self, text: str, metadata: dict
    ) -> list[TextChunk]:
        """Fixed-size chunking with overlap."""
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            # Calculate end position
            end = start + self.chunk_size
            
            # If not at the end, try to break at a word boundary
            if end < len(text):
                # Look for last space within chunk
                last_space = text.rfind(" ", start, end)
                if last_space > start:
                    end = last_space
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunks.append(TextChunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    start_char=start,
                    end_char=end,
                    metadata=metadata.copy(),
                ))
                chunk_index += 1
            
            # Move start, accounting for overlap
            start = end - self.chunk_overlap
            if start <= chunks[-1].start_char if chunks else 0:
                start = end  # Prevent infinite loop
        
        return chunks
    
    def _chunk_by_sentence(
        self, text: str, metadata: dict
    ) -> list[TextChunk]:
        """Split into chunks at sentence boundaries."""
        sentences = self.sentence_pattern.split(text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_index = 0
        start_char = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_length = len(sentence)
            
            # If adding this sentence would exceed limit, finalize chunk
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append(TextChunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    start_char=start_char,
                    end_char=start_char + len(chunk_text),
                    metadata=metadata.copy(),
                ))
                chunk_index += 1
                start_char += len(chunk_text) + 1
                
                # Keep overlap sentences
                overlap_sentences = []
                overlap_length = 0
                for s in reversed(current_chunk):
                    if overlap_length + len(s) <= self.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_length += len(s)
                    else:
                        break
                
                current_chunk = overlap_sentences
                current_length = overlap_length
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(TextChunk(
                text=chunk_text,
                chunk_index=chunk_index,
                start_char=start_char,
                end_char=start_char + len(chunk_text),
                metadata=metadata.copy(),
            ))
        
        return chunks
    
    def _chunk_by_paragraph(
        self, text: str, metadata: dict
    ) -> list[TextChunk]:
        """Split into chunks at paragraph boundaries."""
        # Split on double newlines
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_index = 0
        start_char = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_length = len(para)
            
            # If single paragraph exceeds limit, split it
            if para_length > self.chunk_size:
                # Finalize current chunk first
                if current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    chunks.append(TextChunk(
                        text=chunk_text,
                        chunk_index=chunk_index,
                        start_char=start_char,
                        end_char=start_char + len(chunk_text),
                        metadata=metadata.copy(),
                    ))
                    chunk_index += 1
                    start_char += len(chunk_text) + 2
                    current_chunk = []
                    current_length = 0
                
                # Split large paragraph using sentence chunking
                sub_chunks = self._chunk_by_sentence(para, metadata)
                for sub in sub_chunks:
                    sub.chunk_index = chunk_index
                    sub.start_char = start_char + sub.start_char
                    sub.end_char = start_char + sub.end_char
                    chunks.append(sub)
                    chunk_index += 1
                
                start_char += para_length + 2
                continue
            
            # If adding this paragraph would exceed limit, finalize chunk
            if current_length + para_length > self.chunk_size and current_chunk:
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(TextChunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    start_char=start_char,
                    end_char=start_char + len(chunk_text),
                    metadata=metadata.copy(),
                ))
                chunk_index += 1
                start_char += len(chunk_text) + 2
                current_chunk = []
                current_length = 0
            
            current_chunk.append(para)
            current_length += para_length
        
        # Add final chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(TextChunk(
                text=chunk_text,
                chunk_index=chunk_index,
                start_char=start_char,
                end_char=start_char + len(chunk_text),
                metadata=metadata.copy(),
            ))
        
        return chunks
    
    def _chunk_semantic(
        self, text: str, metadata: dict
    ) -> list[TextChunk]:
        """
        Smart semantic chunking for contracts.
        
        Tries to:
        1. Keep sections together
        2. Respect paragraph boundaries
        3. Fall back to sentence splitting for large sections
        """
        # First, try to split by sections
        section_splits = self.section_pattern.split(text)
        section_headers = self.section_pattern.findall(text)
        
        # Reconstruct sections with headers
        sections = []
        for i, split in enumerate(section_splits):
            if i > 0 and i - 1 < len(section_headers):
                sections.append(section_headers[i - 1] + split)
            else:
                sections.append(split)
        
        chunks = []
        chunk_index = 0
        start_char = 0
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            # If section fits in a chunk, add it
            if len(section) <= self.chunk_size:
                chunks.append(TextChunk(
                    text=section,
                    chunk_index=chunk_index,
                    start_char=start_char,
                    end_char=start_char + len(section),
                    metadata={**metadata, "is_complete_section": True},
                ))
                chunk_index += 1
                start_char += len(section) + 2
            else:
                # Section too large - use paragraph chunking
                sub_chunks = self._chunk_by_paragraph(section, metadata)
                for sub in sub_chunks:
                    sub.chunk_index = chunk_index
                    sub.start_char = start_char + sub.start_char
                    sub.end_char = start_char + sub.end_char
                    sub.metadata["is_complete_section"] = False
                    chunks.append(sub)
                    chunk_index += 1
                start_char += len(section) + 2
        
        # If no sections found, fall back to paragraph chunking
        if not chunks:
            return self._chunk_by_paragraph(text, metadata)
        
        return chunks
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Uses rough heuristic: ~4 characters per token for English.
        For accurate counting, use tiktoken.
        """
        return len(text) // 4
    
    def chunk_by_tokens(
        self,
        text: str,
        max_tokens: int = 500,
        overlap_tokens: int = 50,
        metadata: Optional[dict] = None,
    ) -> list[TextChunk]:
        """
        Chunk text by token count.
        
        Requires tiktoken for accurate token counting.
        """
        try:
            import tiktoken
            encoder = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            logger.warning("tiktoken not available, using character-based chunking")
            # Fall back to character-based with estimated sizes
            char_size = max_tokens * 4
            char_overlap = overlap_tokens * 4
            original_size = self.chunk_size
            original_overlap = self.chunk_overlap
            self.chunk_size = char_size
            self.chunk_overlap = char_overlap
            result = self._chunk_fixed(text, metadata or {})
            self.chunk_size = original_size
            self.chunk_overlap = original_overlap
            return result
        
        metadata = metadata or {}
        tokens = encoder.encode(text)
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(tokens):
            end = min(start + max_tokens, len(tokens))
            
            chunk_tokens = tokens[start:end]
            chunk_text = encoder.decode(chunk_tokens)
            
            # Find character positions
            char_start = len(encoder.decode(tokens[:start]))
            char_end = char_start + len(chunk_text)
            
            chunks.append(TextChunk(
                text=chunk_text,
                chunk_index=chunk_index,
                start_char=char_start,
                end_char=char_end,
                metadata={**metadata, "token_count": len(chunk_tokens)},
            ))
            
            chunk_index += 1
            start = end - overlap_tokens
            
            if start <= 0:
                start = end
        
        return chunks
