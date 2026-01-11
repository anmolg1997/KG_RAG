"""
Document ingestion pipeline orchestration.

Coordinates:
1. PDF parsing
2. Text chunking
3. LLM-based entity + metadata extraction per chunk
4. Graph population (entities + chunks with metadata)

All extraction (entities + metadata) happens via LLM in a single call per chunk.
Behavior is controlled by ExtractionStrategy - no fallbacks, strategy-driven only.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.ingestion.pdf_parser import PDFParser, ParsedDocument
from app.ingestion.chunker import TextChunker, TextChunk
from app.extraction.dynamic_extractor import DynamicExtractor, ExtractionResult, ChunkMetadata
from app.schema.models import DynamicGraph, DynamicEntity
from app.graph.dynamic_repository import DynamicGraphRepository
from app.strategies import get_strategy_manager, ExtractionStrategy

logger = logging.getLogger(__name__)


@dataclass
class IngestionStatus:
    """Status of document ingestion."""
    
    document_id: str
    filename: str
    status: str  # "pending", "parsing", "chunking", "extracting", "storing", "completed", "failed"
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    # Progress metrics
    pages_parsed: int = 0
    total_pages: int = 0
    chunks_created: int = 0
    chunks_processed: int = 0
    total_chunks: int = 0
    entities_extracted: int = 0
    relationships_extracted: int = 0
    
    # Strategy info
    extraction_strategy: str = "default"
    
    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "extraction_strategy": self.extraction_strategy,
            "progress": {
                "pages_parsed": self.pages_parsed,
                "total_pages": self.total_pages,
                "chunks_created": self.chunks_created,
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
    chunks: list[TextChunk] = field(default_factory=list)
    chunk_metadata: list[ChunkMetadata] = field(default_factory=list)
    extraction_result: Optional[ExtractionResult] = None
    graph: Optional[DynamicGraph] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "document_id": self.document_id,
            "status": self.status.to_dict(),
            "metrics": {
                "pages": self.parsed_document.metadata.page_count if self.parsed_document else 0,
                "characters": self.parsed_document.total_characters if self.parsed_document else 0,
                "chunks": len(self.chunks),
                "entities": self.graph.entity_count if self.graph else 0,
                "relationships": self.graph.relationship_count if self.graph else 0,
            },
        }


class IngestionPipeline:
    """
    End-to-end document ingestion pipeline (schema-agnostic, strategy-driven).
    
    This pipeline:
    1. Parses PDF documents
    2. Creates text chunks
    3. For each chunk, extracts entities AND metadata via LLM (single call)
    4. Stores chunks with LLM-extracted metadata
    5. Links entities to source chunks
    
    All metadata (section headings, temporal refs, key terms) is extracted via LLM,
    not rule-based. The ExtractionStrategy controls what metadata to request.
    
    Usage:
        pipeline = IngestionPipeline()
        result = await pipeline.ingest_file("document.pdf")
        
        if result.success:
            print(f"Extracted {result.graph.entity_count} entities")
            print(f"Created {len(result.chunks)} chunks")
            for meta in result.chunk_metadata:
                print(f"  Chunk {meta.chunk_index}: {meta.section_heading}")
    """
    
    def __init__(
        self,
        pdf_parser: Optional[PDFParser] = None,
        chunker: Optional[TextChunker] = None,
        extractor: Optional[DynamicExtractor] = None,
        graph_repo: Optional[DynamicGraphRepository] = None,
        schema_name: Optional[str] = None,
        extraction_strategy: Optional[ExtractionStrategy] = None,
    ):
        self.pdf_parser = pdf_parser or PDFParser()
        self.chunker = chunker or TextChunker()
        self.graph_repo = graph_repo
        self.schema_name = schema_name
        
        # Get extraction strategy from manager if not provided
        self.extraction_strategy = extraction_strategy or get_strategy_manager().extraction
        
        # Create extractor with strategy
        self.extractor = extractor or DynamicExtractor(
            schema_name=schema_name,
            extraction_strategy=self.extraction_strategy,
        )
        
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
            extraction_strategy=getattr(self.extraction_strategy, 'name', 'custom'),
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
            
            # Step 2: Create chunks
            status.status = "chunking"
            chunks = self.chunker.chunk_document(
                parsed_doc,
                document_id=document_id,
            )
            status.chunks_created = len(chunks)
            status.total_chunks = len(chunks)
            
            logger.info(f"Created {len(chunks)} chunks")
            
            # Step 3: Extract entities + metadata per chunk via LLM
            status.status = "extracting"
            logger.info("Extracting entities and metadata from chunks via LLM")
            
            merged_graph, all_chunk_metadata = await self._extract_from_chunks(
                chunks, file_path.name, status
            )
            
            logger.info(
                f"Extracted {merged_graph.entity_count} entities, "
                f"{merged_graph.relationship_count} relationships"
            )
            
            # Apply LLM-extracted metadata to chunks
            self._apply_metadata_to_chunks(chunks, all_chunk_metadata)
            
            # Step 4: Store in graph
            if store_in_graph and self.graph_repo:
                status.status = "storing"
                logger.info("Storing in knowledge graph")
                
                # Store document and chunks first
                if self.extraction_strategy.chunks.enabled:
                    await self._store_document_and_chunks(
                        document_id, file_path.name, parsed_doc, chunks
                    )
                
                # Store entities and relationships
                await self.graph_repo.store_graph(merged_graph)
                
                # Link entities to chunks
                if self.extraction_strategy.entity_linking.enabled and chunks:
                    await self._link_entities_to_chunks(merged_graph, chunks)
                
                logger.info("Successfully stored in Neo4j")
            
            # Complete
            status.status = "completed"
            status.completed_at = datetime.now()
            
            return IngestionResult(
                success=True,
                document_id=document_id,
                status=status,
                parsed_document=parsed_doc,
                chunks=chunks,
                chunk_metadata=all_chunk_metadata,
                graph=merged_graph,
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
        """
        document_id = f"doc_{Path(filename).stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        status = IngestionStatus(
            document_id=document_id,
            filename=filename,
            status="pending",
            started_at=datetime.now(),
            extraction_strategy=getattr(self.extraction_strategy, 'name', 'custom'),
        )
        self._active_ingestions[document_id] = status
        
        try:
            # Step 1: Parse PDF from bytes
            status.status = "parsing"
            logger.info(f"Parsing uploaded document: {filename}")
            
            parsed_doc = self.pdf_parser.parse_bytes(data, filename)
            status.pages_parsed = parsed_doc.metadata.page_count
            status.total_pages = parsed_doc.metadata.page_count
            
            # Step 2: Create chunks
            status.status = "chunking"
            chunks = self.chunker.chunk_document(
                parsed_doc,
                document_id=document_id,
            )
            status.chunks_created = len(chunks)
            status.total_chunks = len(chunks)
            
            # Step 3: Extract entities + metadata per chunk via LLM
            status.status = "extracting"
            merged_graph, all_chunk_metadata = await self._extract_from_chunks(
                chunks, filename, status
            )
            
            # Apply metadata to chunks
            self._apply_metadata_to_chunks(chunks, all_chunk_metadata)
            
            # Step 4: Store in graph
            if store_in_graph and self.graph_repo:
                status.status = "storing"
                
                if self.extraction_strategy.chunks.enabled:
                    await self._store_document_and_chunks(
                        document_id, filename, parsed_doc, chunks
                    )
                
                await self.graph_repo.store_graph(merged_graph)
                
                if self.extraction_strategy.entity_linking.enabled and chunks:
                    await self._link_entities_to_chunks(merged_graph, chunks)
            
            status.status = "completed"
            status.completed_at = datetime.now()
            
            return IngestionResult(
                success=True,
                document_id=document_id,
                status=status,
                parsed_document=parsed_doc,
                chunks=chunks,
                chunk_metadata=all_chunk_metadata,
                graph=merged_graph,
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
        """
        document_id = f"doc_{document_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        status = IngestionStatus(
            document_id=document_id,
            filename=document_name,
            status="extracting",
            started_at=datetime.now(),
            extraction_strategy=getattr(self.extraction_strategy, 'name', 'custom'),
        )
        
        try:
            # For raw text, treat as single chunk
            chunk = TextChunk(
                id=f"{document_id}_chunk_0",
                text=text,
                chunk_index=0,
                start_char=0,
                end_char=len(text),
            )
            
            # Extract via LLM
            result = await self.extractor.extract_chunk(
                chunk_text=text,
                chunk_id=chunk.id,
                chunk_index=0,
                source_document=document_name,
            )
            
            graph = result.graph
            chunk_metadata = [result.chunk_metadata] if result.chunk_metadata else []
            
            status.entities_extracted = graph.entity_count
            status.relationships_extracted = graph.relationship_count
            
            # Apply metadata
            if result.chunk_metadata:
                chunk.metadata.update(result.chunk_metadata.to_dict())
            
            if store_in_graph and self.graph_repo:
                status.status = "storing"
                await self.graph_repo.store_graph(graph)
            
            status.status = "completed"
            status.completed_at = datetime.now()
            
            return IngestionResult(
                success=True,
                document_id=document_id,
                status=status,
                chunks=[chunk],
                chunk_metadata=chunk_metadata,
                extraction_result=result,
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
    
    async def _extract_from_chunks(
        self,
        chunks: list[TextChunk],
        source_document: str,
        status: IngestionStatus,
    ) -> tuple[DynamicGraph, list[ChunkMetadata]]:
        """
        Extract entities and metadata from each chunk via LLM.
        
        Returns:
            Tuple of (merged_graph, list_of_chunk_metadata)
        """
        strategy = self.extraction_strategy
        
        # Create merged graph
        merged_graph = DynamicGraph(
            schema_name=self.extractor.schema.schema_info.name,
            source_document=source_document,
            extraction_model=self.extractor.llm.model,
        )
        
        all_chunk_metadata: list[ChunkMetadata] = []
        
        for i, chunk in enumerate(chunks):
            # Extract entities + metadata via LLM
            result = await self.extractor.extract_chunk(
                chunk_text=chunk.text,
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                source_document=source_document,
            )
            
            # Merge entities into main graph
            for entity_type, entities in result.graph.entities.items():
                for entity in entities:
                    # Tag entity with chunk info
                    entity.metadata["source_chunk_id"] = chunk.id
                    entity.metadata["source_chunk_index"] = chunk.chunk_index
                    merged_graph.add_entity(entity)
            
            # Merge relationships
            for rel in result.graph.relationships:
                merged_graph.add_relationship(rel)
            
            # Collect metadata
            if result.chunk_metadata:
                # Add page number from chunk
                result.chunk_metadata.page_number = chunk.metadata.get("page_number")
                all_chunk_metadata.append(result.chunk_metadata)
            
            # Update progress
            status.chunks_processed = i + 1
            status.entities_extracted = merged_graph.entity_count
            status.relationships_extracted = merged_graph.relationship_count
            
            logger.debug(
                f"Chunk {i+1}/{len(chunks)}: "
                f"{result.graph.entity_count} entities, "
                f"section='{result.chunk_metadata.section_heading if result.chunk_metadata else 'N/A'}'"
            )
        
        return merged_graph, all_chunk_metadata
    
    def _apply_metadata_to_chunks(
        self,
        chunks: list[TextChunk],
        metadata_list: list[ChunkMetadata],
    ) -> None:
        """Apply LLM-extracted metadata to chunk objects."""
        # Create lookup by chunk index
        metadata_by_index = {m.chunk_index: m for m in metadata_list}
        
        for chunk in chunks:
            meta = metadata_by_index.get(chunk.chunk_index)
            if meta:
                # Apply LLM-extracted metadata
                if meta.section_heading:
                    chunk.metadata["section_heading"] = meta.section_heading
                if meta.section_level:
                    chunk.metadata["section_level"] = meta.section_level
                if meta.temporal_refs:
                    chunk.metadata["temporal_refs"] = meta.temporal_refs
                if meta.key_terms:
                    chunk.metadata["key_terms"] = meta.key_terms
                
                # Statistics
                chunk.metadata["word_count"] = meta.word_count
                chunk.metadata["char_count"] = meta.char_count
    
    async def _store_document_and_chunks(
        self,
        document_id: str,
        filename: str,
        parsed_doc: ParsedDocument,
        chunks: list[TextChunk],
    ) -> None:
        """Store document node and chunk nodes in Neo4j."""
        strategy = self.extraction_strategy
        
        # Create document node
        await self.graph_repo.create_document_node(
            document_id=document_id,
            filename=filename,
            metadata={
                "page_count": parsed_doc.metadata.page_count,
                "total_characters": parsed_doc.total_characters,
                "title": parsed_doc.metadata.title,
                "author": parsed_doc.metadata.author,
            },
        )
        
        # Store chunks
        await self.graph_repo.store_chunks(
            chunks=chunks,
            document_id=document_id,
            link_sequential=strategy.chunk_linking.sequential,
            link_to_document=strategy.chunk_linking.to_document,
        )
    
    async def _link_entities_to_chunks(
        self,
        graph: DynamicGraph,
        chunks: list[TextChunk],
    ) -> None:
        """Link extracted entities to their source chunks."""
        # Create lookup
        chunk_by_id = {c.id: c for c in chunks}
        
        for entity_type, entities in graph.entities.items():
            for entity in entities:
                # Entity should have source_chunk_id from extraction
                chunk_id = entity.metadata.get("source_chunk_id")
                if chunk_id:
                    await self.graph_repo.link_entity_to_chunk(entity.id, chunk_id)
    
    def get_ingestion_status(self, document_id: str) -> Optional[IngestionStatus]:
        """Get status of an active or completed ingestion."""
        return self._active_ingestions.get(document_id)
    
    def list_ingestions(self) -> list[IngestionStatus]:
        """List all tracked ingestions."""
        return list(self._active_ingestions.values())
