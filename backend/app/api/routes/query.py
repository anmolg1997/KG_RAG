"""
Query API routes for RAG.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.rag.pipeline import RAGPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])

# RAG pipeline instance
_pipeline: Optional[RAGPipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    """Get or create the RAG pipeline."""
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline


class QueryRequest(BaseModel):
    """Request for a RAG query."""
    question: str = Field(..., min_length=3, description="The question to ask")
    # Schema-agnostic: accept both document_id and contract_id for backward compatibility
    document_id: Optional[str] = Field(None, description="Optional document ID to focus on")
    contract_id: Optional[str] = Field(None, description="Deprecated: use document_id instead")
    include_follow_ups: bool = Field(True, description="Generate follow-up questions")
    use_history: bool = Field(True, description="Consider conversation history")
    
    @property
    def target_document_id(self) -> Optional[str]:
        """Get the document ID, preferring document_id over contract_id."""
        return self.document_id or self.contract_id


class QueryResponse(BaseModel):
    """Response from RAG query."""
    question: str
    answer: str
    sources: list[dict]
    confidence: float
    follow_up_questions: Optional[list[str]] = None
    metadata: dict
    debug_info: Optional[dict] = None


class SummaryRequest(BaseModel):
    """Request for document summary."""
    document_id: Optional[str] = Field(None, description="Document ID to summarize")
    contract_id: Optional[str] = Field(None, description="Deprecated: use document_id instead")
    
    @property
    def target_document_id(self) -> Optional[str]:
        """Get the document ID, preferring document_id over contract_id."""
        return self.document_id or self.contract_id


class CompareRequest(BaseModel):
    """Request for document comparison."""
    document_ids: Optional[list[str]] = Field(None, min_length=2, description="Document IDs to compare")
    contract_ids: Optional[list[str]] = Field(None, description="Deprecated: use document_ids instead")
    aspect: str = Field("general", description="Aspect to compare")
    
    @property
    def target_document_ids(self) -> list[str]:
        """Get the document IDs, preferring document_ids over contract_ids."""
        return self.document_ids or self.contract_ids or []


@router.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    """
    Ask a question about the documents in the knowledge graph.
    
    The system will:
    1. Analyze the question to understand intent
    2. Retrieve relevant context from the graph
    3. Generate a natural language response
    4. Optionally suggest follow-up questions
    """
    pipeline = get_rag_pipeline()
    
    try:
        response = await pipeline.query(
            question=request.question,
            document_id=request.target_document_id,
            include_follow_ups=request.include_follow_ups,
            use_conversation_history=request.use_history,
        )
        
        return QueryResponse(
            question=response.question,
            answer=response.answer,
            sources=response.sources,
            confidence=response.confidence,
            follow_up_questions=response.follow_up_questions,
            metadata={
                "retrieval_time_ms": response.retrieval_time_ms,
                "generation_time_ms": response.generation_time_ms,
                "total_time_ms": response.total_time_ms,
                "entities_retrieved": response.entities_retrieved,
            },
            debug_info=response.debug_info,
        )
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )


@router.post("/summarize")
async def summarize_document(request: SummaryRequest):
    """
    Generate a summary of a specific document.
    """
    pipeline = get_rag_pipeline()
    
    doc_id = request.target_document_id
    if not doc_id:
        raise HTTPException(
            status_code=400,
            detail="document_id is required"
        )
    
    try:
        result = await pipeline.summarize_contract(doc_id)  # Method name kept for compatibility
        return result
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Summarization failed: {str(e)}"
        )


@router.post("/compare")
async def compare_documents(request: CompareRequest):
    """
    Compare multiple documents.
    
    Provide at least 2 document IDs and optionally specify
    which aspect to focus on.
    """
    doc_ids = request.target_document_ids
    if len(doc_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 documents required for comparison"
        )
    
    pipeline = get_rag_pipeline()
    
    try:
        result = await pipeline.compare_documents(
            document_ids=doc_ids,
            aspect=request.aspect,
        )
        return result
    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Comparison failed: {str(e)}"
        )


@router.get("/history")
async def get_conversation_history():
    """Get the conversation history."""
    pipeline = get_rag_pipeline()
    return {
        "history": pipeline.get_history(),
        "count": len(pipeline.get_history()),
    }


@router.post("/clear-history")
async def clear_conversation_history():
    """Clear the conversation history."""
    pipeline = get_rag_pipeline()
    pipeline.clear_history()
    return {"message": "Conversation history cleared"}


@router.post("/ask-with-context")
async def ask_with_additional_context(
    question: str,
    additional_context: str,
    document_id: Optional[str] = None,
):
    """
    Ask a question with additional user-provided context.
    
    Useful when you want to provide extra information
    that might not be in the knowledge graph.
    """
    pipeline = get_rag_pipeline()
    
    try:
        response = await pipeline.query_with_context(
            question=question,
            additional_context=additional_context,
            document_id=document_id,
        )
        
        return {
            "question": response.question,
            "answer": response.answer,
            "confidence": response.confidence,
            "metadata": {
                "retrieval_time_ms": response.retrieval_time_ms,
                "generation_time_ms": response.generation_time_ms,
            },
        }
    except Exception as e:
        logger.error(f"Query with context failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )
