"""
Document ingestion pipeline orchestration.

Coordinates:
1. PDF parsing
2. Text chunking
3. Entity extraction
4. Graph population
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.ingestion.pdf_parser import PDFParser, ParsedDocument
from app.ingestion.chunker import TextChunker, TextChunk
from app.extraction.extractor import EntityExtractor, ExtractionResult
from app.extraction.ontology import ExtractedGraph
from app.graph.repository import GraphRepository

logger = logging.getLogger(__name__)


@dataclass
class IngestionStatus:
    """Status of document ingestion."""
    
    document_id: str
    filename: str
    status: str  # "pending", "parsing", "extracting", "storing", "completed", "failed"
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    # Progress metrics
    pages_parsed: int = 0
    total_pages: int = 0
    chunks_processed: int = 0
    total_chunks: int = 0
    entities_extracted: int = 0
    relationships_extracted: int = 0
    
    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "progress": {
                "pages_parsed": self.pages_parsed,
                "total_pages": self.total_pages,
                "chunks_processed": self.chunks_processed,
                "total_chunks": self.total_chunks,
                "entities_extracted": self.entities_extracted,
                "relationships_extracted": self.relationships_extracted,
            },
        }


@dataclass
class IngestionResult:
    """Result of document ingestion."""
    
    success: bool
    document_id: str
    status: IngestionStatus
    parsed_document: Optional[ParsedDocument] = None
    extraction_result: Optional[ExtractionResult] = None
    graph: Optional[ExtractedGraph] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "document_id": self.document_id,
            "status": self.status.to_dict(),
            "metrics": {
                "pages": self.parsed_document.metadata.page_count if self.parsed_document else 0,
                "characters": self.parsed_document.total_characters if self.parsed_document else 0,
                "entities": self.graph.entity_count if self.graph else 0,
                "relationships": self.graph.relationship_count if self.graph else 0,
            },
        }


class IngestionPipeline:
    """
    End-to-end document ingestion pipeline.
    
    Usage:
        pipeline = IngestionPipeline()
        result = await pipeline.ingest_file("contract.pdf")
        
        if result.success:
            print(f"Extracted {result.graph.entity_count} entities")
    """
    
    def __init__(
        self,
        pdf_parser: Optional[PDFParser] = None,
        chunker: Optional[TextChunker] = None,
        extractor: Optional[EntityExtractor] = None,
        graph_repo: Optional[GraphRepository] = None,
    ):
        self.pdf_parser = pdf_parser or PDFParser()
        self.chunker = chunker or TextChunker()
        self.extractor = extractor or EntityExtractor()
        self.graph_repo = graph_repo
        
        # Track active ingestions
        self._active_ingestions: dict[str, IngestionStatus] = {}
    
    async def ingest_file(
        self,
        file_path: str | Path,
        store_in_graph: bool = True,
    ) -> IngestionResult:
        """
        Ingest a PDF file into the knowledge graph.
        
        Args:
            file_path: Path to PDF file
            store_in_graph: Whether to store results in Neo4j
            
        Returns:
            IngestionResult with full details
        """
        file_path = Path(file_path)
        document_id = f"doc_{file_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        status = IngestionStatus(
            document_id=document_id,
            filename=file_path.name,
            status="pending",
            started_at=datetime.now(),
        )
        self._active_ingestions[document_id] = status
        
        try:
            # Step 1: Parse PDF
            status.status = "parsing"
            logger.info(f"Parsing document: {file_path}")
            
            parsed_doc = self.pdf_parser.parse(file_path)
            status.pages_parsed = parsed_doc.metadata.page_count
            status.total_pages = parsed_doc.metadata.page_count
            
            logger.info(
                f"Parsed {parsed_doc.metadata.page_count} pages, "
                f"{parsed_doc.total_characters} characters"
            )
            
            # Step 2: Extract entities
            status.status = "extracting"
            logger.info("Extracting entities and relationships")
            
            extraction_result = await self.extractor.extract(
                text=parsed_doc.full_text,
                source_document=file_path.name,
            )
            
            graph = extraction_result.graph
            status.entities_extracted = graph.entity_count
            status.relationships_extracted = graph.relationship_count
            
            logger.info(
                f"Extracted {graph.entity_count} entities, "
                f"{graph.relationship_count} relationships"
            )
            
            # Log validation results
            if not extraction_result.validation.is_valid:
                logger.warning(
                    f"Extraction validation issues: {extraction_result.validation.errors}"
                )
            
            # Step 3: Store in graph (if enabled and repo available)
            if store_in_graph and self.graph_repo:
                status.status = "storing"
                logger.info("Storing in knowledge graph")
                
                await self.graph_repo.store_extracted_graph(graph)
                
                logger.info("Successfully stored in Neo4j")
            
            # Complete
            status.status = "completed"
            status.completed_at = datetime.now()
            
            return IngestionResult(
                success=True,
                document_id=document_id,
                status=status,
                parsed_document=parsed_doc,
                extraction_result=extraction_result,
                graph=graph,
            )
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            status.status = "failed"
            status.error = str(e)
            status.completed_at = datetime.now()
            
            return IngestionResult(
                success=False,
                document_id=document_id,
                status=status,
            )
    
    async def ingest_bytes(
        self,
        data: bytes,
        filename: str,
        store_in_graph: bool = True,
    ) -> IngestionResult:
        """
        Ingest a PDF from bytes (uploaded file).
        
        Args:
            data: PDF file content as bytes
            filename: Original filename
            store_in_graph: Whether to store results in Neo4j
            
        Returns:
            IngestionResult with full details
        """
        document_id = f"doc_{Path(filename).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        status = IngestionStatus(
            document_id=document_id,
            filename=filename,
            status="pending",
            started_at=datetime.now(),
        )
        self._active_ingestions[document_id] = status
        
        try:
            # Step 1: Parse PDF from bytes
            status.status = "parsing"
            logger.info(f"Parsing uploaded document: {filename}")
            
            parsed_doc = self.pdf_parser.parse_bytes(data, filename)
            status.pages_parsed = parsed_doc.metadata.page_count
            status.total_pages = parsed_doc.metadata.page_count
            
            # Step 2: Extract entities
            status.status = "extracting"
            
            extraction_result = await self.extractor.extract(
                text=parsed_doc.full_text,
                source_document=filename,
            )
            
            graph = extraction_result.graph
            status.entities_extracted = graph.entity_count
            status.relationships_extracted = graph.relationship_count
            
            # Step 3: Store in graph
            if store_in_graph and self.graph_repo:
                status.status = "storing"
                await self.graph_repo.store_extracted_graph(graph)
            
            status.status = "completed"
            status.completed_at = datetime.now()
            
            return IngestionResult(
                success=True,
                document_id=document_id,
                status=status,
                parsed_document=parsed_doc,
                extraction_result=extraction_result,
                graph=graph,
            )
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            status.status = "failed"
            status.error = str(e)
            status.completed_at = datetime.now()
            
            return IngestionResult(
                success=False,
                document_id=document_id,
                status=status,
            )
    
    async def ingest_text(
        self,
        text: str,
        document_name: str,
        store_in_graph: bool = True,
    ) -> IngestionResult:
        """
        Ingest raw text directly (for testing or non-PDF sources).
        
        Args:
            text: Document text
            document_name: Name for the document
            store_in_graph: Whether to store results in Neo4j
            
        Returns:
            IngestionResult
        """
        document_id = f"doc_{document_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        status = IngestionStatus(
            document_id=document_id,
            filename=document_name,
            status="extracting",
            started_at=datetime.now(),
        )
        
        try:
            extraction_result = await self.extractor.extract(
                text=text,
                source_document=document_name,
            )
            
            graph = extraction_result.graph
            status.entities_extracted = graph.entity_count
            status.relationships_extracted = graph.relationship_count
            
            if store_in_graph and self.graph_repo:
                status.status = "storing"
                await self.graph_repo.store_extracted_graph(graph)
            
            status.status = "completed"
            status.completed_at = datetime.now()
            
            return IngestionResult(
                success=True,
                document_id=document_id,
                status=status,
                extraction_result=extraction_result,
                graph=graph,
            )
            
        except Exception as e:
            logger.error(f"Text ingestion failed: {e}")
            status.status = "failed"
            status.error = str(e)
            
            return IngestionResult(
                success=False,
                document_id=document_id,
                status=status,
            )
    
    def get_ingestion_status(self, document_id: str) -> Optional[IngestionStatus]:
        """Get status of an active or completed ingestion."""
        return self._active_ingestions.get(document_id)
    
    def list_ingestions(self) -> list[IngestionStatus]:
        """List all tracked ingestions."""
        return list(self._active_ingestions.values())
