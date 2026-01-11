"""
Document upload API routes.
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.config import settings
from app.ingestion.pipeline import IngestionPipeline, IngestionResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

# Pipeline instance
_pipeline: Optional[IngestionPipeline] = None


def get_pipeline() -> IngestionPipeline:
    """Get or create the ingestion pipeline."""
    global _pipeline
    if _pipeline is None:
        from app.graph.dynamic_repository import DynamicGraphRepository
        repo = DynamicGraphRepository()
        _pipeline = IngestionPipeline(graph_repo=repo)
    return _pipeline


class UploadResponse(BaseModel):
    """Response for document upload."""
    success: bool
    document_id: str
    filename: str
    message: str
    status: str
    schema_used: Optional[str] = None
    # Extraction metrics
    entities_extracted: int = 0
    relationships_extracted: int = 0
    chunks_created: int = 0
    pages_parsed: int = 0


class IngestionStatusResponse(BaseModel):
    """Response for ingestion status check."""
    document_id: str
    filename: str
    status: str
    error: Optional[str] = None
    progress: dict


@router.post("/document", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    process_immediately: bool = True,
):
    """
    Upload a PDF document for processing.
    
    The document will be:
    1. Parsed to extract text
    2. Processed through entity extraction (using active schema)
    3. Stored in the knowledge graph
    
    Set process_immediately=False to just upload without processing.
    """
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )
    
    # Read file content
    content = await file.read()
    
    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty file uploaded"
        )
    
    pipeline = get_pipeline()
    
    if process_immediately:
        # Process synchronously (for smaller files)
        try:
            result = await pipeline.ingest_bytes(
                data=content,
                filename=file.filename,
                store_in_graph=True,
            )
            
            schema_name = result.graph.schema_name if result.graph else settings.active_schema
            entity_count = result.graph.entity_count if result.graph else 0
            rel_count = result.graph.relationship_count if result.graph else 0
            
            return UploadResponse(
                success=result.success,
                document_id=result.document_id,
                filename=file.filename,
                message=f"Extracted {entity_count} entities, {rel_count} relationships",
                status=result.status.status,
                schema_used=schema_name,
                entities_extracted=entity_count,
                relationships_extracted=rel_count,
                chunks_created=len(result.chunks) if result.chunks else 0,
                pages_parsed=result.status.pages_parsed,
            )
        except Exception as e:
            logger.error(f"Upload processing failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Processing failed: {str(e)}"
            )
    else:
        # Queue for background processing
        # For now, just acknowledge upload
        return UploadResponse(
            success=True,
            document_id="pending",
            filename=file.filename,
            message="Document uploaded, processing queued",
            status="pending",
            schema_used=settings.active_schema,
        )


@router.post("/text")
async def upload_text(
    text: str,
    document_name: str = "uploaded_text",
):
    """
    Upload raw text for processing.
    
    Useful for:
    - Testing extraction
    - Processing non-PDF content
    - API integrations
    """
    if not text or len(text.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Text too short (minimum 50 characters)"
        )
    
    pipeline = get_pipeline()
    
    try:
        result = await pipeline.ingest_text(
            text=text,
            document_name=document_name,
            store_in_graph=True,
        )
        
        return {
            "success": result.success,
            "document_id": result.document_id,
            "schema_used": result.graph.schema_name if result.graph else settings.active_schema,
            "entities_extracted": result.graph.entity_count if result.graph else 0,
            "relationships_extracted": result.graph.relationship_count if result.graph else 0,
        }
    except Exception as e:
        logger.error(f"Text processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )


@router.get("/status/{document_id}", response_model=IngestionStatusResponse)
async def get_ingestion_status(document_id: str):
    """Get the status of a document ingestion."""
    pipeline = get_pipeline()
    status = pipeline.get_ingestion_status(document_id)
    
    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"Document {document_id} not found"
        )
    
    return IngestionStatusResponse(
        document_id=status.document_id,
        filename=status.filename,
        status=status.status,
        error=status.error,
        progress={
            "pages_parsed": status.pages_parsed,
            "total_pages": status.total_pages,
            "entities_extracted": status.entities_extracted,
            "relationships_extracted": status.relationships_extracted,
        },
    )


@router.get("/list")
async def list_ingestions():
    """List all tracked ingestions."""
    pipeline = get_pipeline()
    ingestions = pipeline.list_ingestions()
    
    return {
        "total": len(ingestions),
        "ingestions": [
            {
                "document_id": s.document_id,
                "filename": s.filename,
                "status": s.status,
                "started_at": s.started_at.isoformat(),
            }
            for s in ingestions
        ],
    }


@router.post("/from-path")
async def process_local_file(file_path: str):
    """
    Process a PDF file from the local filesystem.
    
    Useful for processing files already on the server.
    """
    path = Path(file_path)
    
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {file_path}"
        )
    
    if not path.suffix.lower() == ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )
    
    pipeline = get_pipeline()
    
    try:
        result = await pipeline.ingest_file(
            file_path=path,
            store_in_graph=True,
        )
        
        return {
            "success": result.success,
            "document_id": result.document_id,
            "filename": path.name,
            "schema_used": result.graph.schema_name if result.graph else settings.active_schema,
            "metrics": result.to_dict().get("metrics", {}),
        }
    except Exception as e:
        logger.error(f"File processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )
