"""
PDF document parsing and text extraction.

Supports:
- Text extraction with layout preservation
- Metadata extraction (title, author, dates)
- Page-level processing with character offset tracking
- Table detection (basic)
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class PageContent:
    """Content extracted from a single PDF page."""
    
    page_number: int
    text: str
    start_char: int = 0  # Character offset where this page starts in full_text
    end_char: int = 0    # Character offset where this page ends in full_text
    tables: list[str] = field(default_factory=list)
    images: int = 0  # Count of images
    
    @property
    def word_count(self) -> int:
        return len(self.text.split())


@dataclass
class DocumentMetadata:
    """Metadata extracted from PDF."""
    
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    page_count: int = 0
    file_size: int = 0  # bytes
    
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "author": self.author,
            "subject": self.subject,
            "creator": self.creator,
            "producer": self.producer,
            "creation_date": self.creation_date,
            "modification_date": self.modification_date,
            "page_count": self.page_count,
            "file_size": self.file_size,
        }


@dataclass
class ParsedDocument:
    """Complete parsed PDF document."""
    
    filename: str
    metadata: DocumentMetadata
    pages: list[PageContent]
    full_text: str
    
    # Page offset index for fast lookups
    _page_offsets: list[tuple[int, int, int]] = field(default_factory=list)
    
    def __post_init__(self):
        """Build page offset index after initialization."""
        if not self._page_offsets and self.pages:
            self._page_offsets = [
                (p.page_number, p.start_char, p.end_char) for p in self.pages
            ]
    
    @property
    def total_words(self) -> int:
        return sum(p.word_count for p in self.pages)
    
    @property
    def total_characters(self) -> int:
        return len(self.full_text)
    
    def get_page_for_char_position(self, char_pos: int) -> int:
        """
        Get the page number for a given character position.
        
        Args:
            char_pos: Character position in full_text
            
        Returns:
            Page number (1-indexed)
        """
        for page_num, start, end in self._page_offsets:
            if start <= char_pos < end:
                return page_num
        
        # If position is beyond all pages, return last page
        if self._page_offsets and char_pos >= self._page_offsets[-1][2]:
            return self._page_offsets[-1][0]
        
        return 1  # Default to first page
    
    def get_page_range_for_text_span(
        self, start_char: int, end_char: int
    ) -> tuple[int, int]:
        """
        Get the page range for a text span.
        
        Args:
            start_char: Start character position
            end_char: End character position
            
        Returns:
            Tuple of (start_page, end_page) - both 1-indexed
        """
        start_page = self.get_page_for_char_position(start_char)
        end_page = self.get_page_for_char_position(end_char - 1)  # -1 to stay within span
        return (start_page, end_page)


class PDFParser:
    """
    PDF parser using PyMuPDF for robust text extraction.
    
    Features:
    - Preserves document structure
    - Extracts metadata
    - Handles multi-column layouts
    - Tracks page-level character offsets for chunk-to-page mapping
    - Detects tables (basic)
    
    Usage:
        parser = PDFParser()
        doc = parser.parse("contract.pdf")
        print(doc.full_text)
        
        # Get page number for a character position
        page = doc.get_page_for_char_position(1500)
    """
    
    def __init__(
        self,
        preserve_layout: bool = True,
        extract_images: bool = False,
        detect_tables: bool = True,
    ):
        self.preserve_layout = preserve_layout
        self.extract_images = extract_images
        self.detect_tables = detect_tables
    
    def parse(self, file_path: str | Path) -> ParsedDocument:
        """
        Parse a PDF file and extract all content.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            ParsedDocument with full content and metadata
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        if not file_path.suffix.lower() == ".pdf":
            raise ValueError(f"Not a PDF file: {file_path}")
        
        logger.info(f"Parsing PDF: {file_path}")
        
        try:
            doc = fitz.open(file_path)
            
            # Extract metadata
            metadata = self._extract_metadata(doc, file_path)
            
            # Extract pages with character offset tracking
            pages = []
            all_text_parts = []
            current_offset = 0
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_content = self._extract_page(page, page_num + 1)
                
                # Set character offsets
                page_content.start_char = current_offset
                page_content.end_char = current_offset + len(page_content.text)
                
                pages.append(page_content)
                all_text_parts.append(page_content.text)
                
                # Update offset (+2 for the "\n\n" separator between pages)
                current_offset = page_content.end_char + 2
            
            doc.close()
            
            # Combine all text with page separators
            full_text = "\n\n".join(all_text_parts)
            
            logger.info(
                f"Parsed {len(pages)} pages, {len(full_text)} characters"
            )
            
            return ParsedDocument(
                filename=file_path.name,
                metadata=metadata,
                pages=pages,
                full_text=full_text,
            )
            
        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {e}")
            raise
    
    def parse_bytes(self, data: bytes, filename: str = "document.pdf") -> ParsedDocument:
        """
        Parse PDF from bytes (e.g., uploaded file).
        
        Args:
            data: PDF file content as bytes
            filename: Name to use for the document
            
        Returns:
            ParsedDocument with full content and metadata
        """
        logger.info(f"Parsing PDF from bytes: {filename}")
        
        try:
            doc = fitz.open(stream=data, filetype="pdf")
            
            # Extract metadata
            metadata = self._extract_metadata_from_doc(doc)
            metadata.file_size = len(data)
            
            # Extract pages with character offset tracking
            pages = []
            all_text_parts = []
            current_offset = 0
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_content = self._extract_page(page, page_num + 1)
                
                # Set character offsets
                page_content.start_char = current_offset
                page_content.end_char = current_offset + len(page_content.text)
                
                pages.append(page_content)
                all_text_parts.append(page_content.text)
                
                # Update offset (+2 for the "\n\n" separator)
                current_offset = page_content.end_char + 2
            
            doc.close()
            
            full_text = "\n\n".join(all_text_parts)
            
            return ParsedDocument(
                filename=filename,
                metadata=metadata,
                pages=pages,
                full_text=full_text,
            )
            
        except Exception as e:
            logger.error(f"Failed to parse PDF bytes: {e}")
            raise
    
    def _extract_metadata(
        self, doc: fitz.Document, file_path: Path
    ) -> DocumentMetadata:
        """Extract metadata from PDF document."""
        metadata = self._extract_metadata_from_doc(doc)
        metadata.file_size = file_path.stat().st_size
        return metadata
    
    def _extract_metadata_from_doc(self, doc: fitz.Document) -> DocumentMetadata:
        """Extract metadata from fitz Document object."""
        pdf_metadata = doc.metadata
        
        return DocumentMetadata(
            title=pdf_metadata.get("title") or None,
            author=pdf_metadata.get("author") or None,
            subject=pdf_metadata.get("subject") or None,
            creator=pdf_metadata.get("creator") or None,
            producer=pdf_metadata.get("producer") or None,
            creation_date=pdf_metadata.get("creationDate") or None,
            modification_date=pdf_metadata.get("modDate") or None,
            page_count=len(doc),
        )
    
    def _extract_page(self, page: fitz.Page, page_number: int) -> PageContent:
        """Extract content from a single page."""
        # Extract text with layout preservation
        if self.preserve_layout:
            text = page.get_text("text", sort=True)
        else:
            text = page.get_text("text")
        
        # Clean up text
        text = self._clean_text(text)
        
        # Count images
        image_count = len(page.get_images()) if self.extract_images else 0
        
        # Extract tables (basic detection)
        tables = []
        if self.detect_tables:
            tables = self._detect_tables(page)
        
        return PageContent(
            page_number=page_number,
            text=text,
            tables=tables,
            images=image_count,
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove excessive whitespace
        lines = text.split("\n")
        cleaned_lines = []
        
        for line in lines:
            # Strip trailing whitespace
            line = line.rstrip()
            # Skip completely empty lines if previous was also empty
            if line or (cleaned_lines and cleaned_lines[-1]):
                cleaned_lines.append(line)
        
        # Join and normalize multiple blank lines
        text = "\n".join(cleaned_lines)
        
        # Replace multiple spaces with single space
        while "  " in text:
            text = text.replace("  ", " ")
        
        return text.strip()
    
    def _detect_tables(self, page: fitz.Page) -> list[str]:
        """
        Basic table detection using text blocks analysis.
        
        Note: For production, consider using camelot-py or tabula-py
        for more sophisticated table extraction.
        """
        tables = []
        
        # Get text blocks
        blocks = page.get_text("dict")["blocks"]
        
        # Look for aligned text blocks that might be tables
        # This is a simplified heuristic
        for block in blocks:
            if block["type"] == 0:  # Text block
                lines = block.get("lines", [])
                if len(lines) >= 3:
                    # Check if lines have similar structure (potential table)
                    span_counts = [len(line.get("spans", [])) for line in lines]
                    if len(set(span_counts)) == 1 and span_counts[0] >= 2:
                        # Might be a table - extract text
                        table_text = []
                        for line in lines:
                            row = " | ".join(
                                span.get("text", "")
                                for span in line.get("spans", [])
                            )
                            table_text.append(row)
                        if table_text:
                            tables.append("\n".join(table_text))
        
        return tables
    
    def get_page_text(
        self, file_path: str | Path, page_number: int
    ) -> str:
        """
        Get text from a specific page.
        
        Args:
            file_path: Path to PDF
            page_number: Page number (1-indexed)
            
        Returns:
            Text content of the page
        """
        file_path = Path(file_path)
        doc = fitz.open(file_path)
        
        if page_number < 1 or page_number > len(doc):
            doc.close()
            raise ValueError(f"Invalid page number: {page_number}")
        
        page = doc[page_number - 1]
        text = page.get_text("text", sort=True)
        doc.close()
        
        return self._clean_text(text)
