"""
RAG pipeline orchestration.

Combines retrieval and generation into a complete
question-answering pipeline.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from app.config import settings
from app.rag.retriever import GraphRetriever, RetrievalContext
from app.rag.generator import ResponseGenerator

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """Complete RAG response with all metadata."""
    
    question: str
    answer: str
    sources: list[dict]
    confidence: float
    
    # Metadata
    retrieval_time_ms: float
    generation_time_ms: float
    total_time_ms: float
    entities_retrieved: int
    
    # Optional
    follow_up_questions: list[str] = None
    context_preview: str = None
    
    # Debug info - Cypher queries and raw results
    debug_info: Optional[dict] = None
    
    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "sources": self.sources,
            "confidence": self.confidence,
            "metadata": {
                "retrieval_time_ms": self.retrieval_time_ms,
                "generation_time_ms": self.generation_time_ms,
                "total_time_ms": self.total_time_ms,
                "entities_retrieved": self.entities_retrieved,
            },
            "follow_up_questions": self.follow_up_questions,
            "debug_info": self.debug_info,
        }


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    
    question: str
    answer: str
    timestamp: datetime
    sources: list[dict]


class RAGPipeline:
    """
    Complete RAG pipeline for question answering.
    
    Orchestrates:
    1. Query understanding
    2. Context retrieval from knowledge graph
    3. Response generation
    4. Follow-up question generation
    
    Usage:
        pipeline = RAGPipeline()
        response = await pipeline.query("What are the payment terms?")
        print(response.answer)
    """
    
    def __init__(
        self,
        retriever: Optional[GraphRetriever] = None,
        generator: Optional[ResponseGenerator] = None,
    ):
        self.retriever = retriever or GraphRetriever()
        self.generator = generator or ResponseGenerator()
        
        # Conversation history for context
        self._conversation_history: list[ConversationTurn] = []
        self._max_history = settings.rag_max_conversation_history
    
    async def query(
        self,
        question: str,
        document_id: Optional[str] = None,
        include_follow_ups: bool = True,
        use_conversation_history: bool = True,
    ) -> RAGResponse:
        """
        Process a question through the RAG pipeline.
        
        Args:
            question: User's question
            document_id: Optional document to focus on
            include_follow_ups: Generate follow-up questions
            use_conversation_history: Consider conversation context
            
        Returns:
            RAGResponse with answer and metadata
        """
        import time
        start_time = time.time()
        
        # ═══════════════════════════════════════════════════════════════
        # QUERY/RAG FLOW
        # ═══════════════════════════════════════════════════════════════
        logger.info("")
        logger.info("═" * 60)
        logger.info(f"🔍 QUERY: {question[:60]}{'...' if len(question) > 60 else ''}")
        logger.info("═" * 60)
        
        # ─────────────────────────────────────────────────────────────
        # STEP 1: Prepare query
        # ─────────────────────────────────────────────────────────────
        logger.info("")
        logger.info("┌─ STEP 1: Prepare query")
        
        # Augment question with conversation history if enabled
        if use_conversation_history and self._conversation_history:
            augmented_question = self._augment_with_history(question)
            logger.info(f"│  History: {len(self._conversation_history)} previous turns included")
        else:
            augmented_question = question
            logger.info("│  History: None (fresh query)")
        
        logger.info("└─ ✓ Query prepared")
        
        # ─────────────────────────────────────────────────────────────
        # STEP 2: Multi-signal retrieval
        # ─────────────────────────────────────────────────────────────
        logger.info("")
        logger.info("┌─ STEP 2: Multi-signal retrieval")
        
        retrieval_start = time.time()
        context = await self.retriever.retrieve(
            query=augmented_question,
            document_id=document_id,
        )
        retrieval_time = (time.time() - retrieval_start) * 1000
        
        logger.info(f"│  Methods used: {', '.join(context.search_methods_used) if context.search_methods_used else 'default'}")
        logger.info(f"│  Entities: {context.entity_count} | Chunks: {context.chunk_count}")
        logger.info(f"└─ ✓ Retrieval complete ({retrieval_time:.0f}ms)")
        
        # ─────────────────────────────────────────────────────────────
        # STEP 3: Generate response (LLM)
        # ─────────────────────────────────────────────────────────────
        logger.info("")
        logger.info("┌─ STEP 3: Generate response (LLM)")
        logger.info(f"│  Context size: {len(context.raw_text)} chars")
        
        generation_start = time.time()
        generation_result = await self.generator.generate(
            question=question,
            context=context,
            include_sources=True,
        )
        generation_time = (time.time() - generation_start) * 1000
        
        confidence = generation_result.get("confidence", 0)
        logger.info(f"│  Confidence: {confidence:.0%}")
        logger.info(f"└─ ✓ Generation complete ({generation_time:.0f}ms)")
        
        # ─────────────────────────────────────────────────────────────
        # STEP 4: Generate follow-ups (optional)
        # ─────────────────────────────────────────────────────────────
        follow_ups = None
        if include_follow_ups and generation_result.get("has_context"):
            logger.info("")
            logger.info("┌─ STEP 4: Generate follow-up questions")
            try:
                follow_ups = await self.generator.generate_follow_up_questions(
                    question=question,
                    response=generation_result["response"],
                    context=context,
                )
                logger.info(f"│  Generated: {len(follow_ups) if follow_ups else 0} follow-ups")
                logger.info("└─ ✓ Follow-ups complete")
            except Exception as e:
                logger.warning(f"│  Follow-up generation failed: {e}")
                logger.info("└─ ⚠ Skipped")
                follow_ups = []
        
        # ─────────────────────────────────────────────────────────────
        # COMPLETE
        # ─────────────────────────────────────────────────────────────
        total_time = (time.time() - start_time) * 1000
        
        logger.info("")
        logger.info("═" * 60)
        logger.info(f"✅ QUERY COMPLETE")
        logger.info(f"   Answer length: {len(generation_result['response'])} chars")
        logger.info(f"   Sources: {len(generation_result.get('sources', []))} | Time: {total_time:.0f}ms")
        logger.info("═" * 60)
        logger.info("")
        
        # Store in conversation history
        self._add_to_history(
            question=question,
            answer=generation_result["response"],
            sources=generation_result.get("sources", []),
        )
        
        return RAGResponse(
            question=question,
            answer=generation_result["response"],
            sources=generation_result.get("sources", []),
            confidence=generation_result.get("confidence", 0.5),
            retrieval_time_ms=retrieval_time,
            generation_time_ms=generation_time,
            total_time_ms=total_time,
            entities_retrieved=context.entity_count,
            follow_up_questions=follow_ups,
            context_preview=context.raw_text[:500] if context.raw_text else None,
            debug_info=context.to_debug_dict(),
        )
    
    async def query_with_context(
        self,
        question: str,
        additional_context: str,
        document_id: Optional[str] = None,
    ) -> RAGResponse:
        """
        Query with additional user-provided context.
        
        Useful when user wants to provide extra information.
        """
        import time
        start_time = time.time()
        
        # Retrieve from graph
        retrieval_start = time.time()
        graph_context = await self.retriever.retrieve(
            query=question,
            document_id=document_id,
        )
        retrieval_time = (time.time() - retrieval_start) * 1000
        
        # Augment context with user-provided info
        augmented_raw_text = f"{graph_context.raw_text}\n\n## Additional Context\n{additional_context}"
        
        augmented_context = RetrievalContext(
            entities=graph_context.entities,
            relationships=graph_context.relationships,
            raw_text=augmented_raw_text,
        )
        
        # Generate response
        generation_start = time.time()
        generation_result = await self.generator.generate(
            question=question,
            context=augmented_context,
        )
        generation_time = (time.time() - generation_start) * 1000
        
        total_time = (time.time() - start_time) * 1000
        
        return RAGResponse(
            question=question,
            answer=generation_result["response"],
            sources=generation_result.get("sources", []),
            confidence=generation_result.get("confidence", 0.5),
            retrieval_time_ms=retrieval_time,
            generation_time_ms=generation_time,
            total_time_ms=total_time,
            entities_retrieved=graph_context.entity_count,
        )
    
    async def summarize_document(
        self, document_id: str
    ) -> dict[str, Any]:
        """Generate a summary of a specific document."""
        context = await self.retriever.retrieve(
            query="Provide a complete summary of this document",
            document_id=document_id,
        )
        
        if context.is_empty:
            return {
                "summary": "Document not found or has no extracted information.",
                "document_id": document_id,
            }
        
        summary = await self.generator.generate_summary(context)
        
        return {
            "summary": summary,
            "document_id": document_id,
            "entities_count": context.entity_count,
        }
    
    async def compare_documents(
        self,
        document_ids: list[str],
        aspect: str = "general",
    ) -> dict[str, Any]:
        """Compare multiple documents."""
        contexts = []
        labels = []
        
        for doc_id in document_ids:
            ctx = await self.retriever.retrieve(
                query=f"Get information about {aspect}",
                document_id=doc_id,
            )
            contexts.append(ctx)
            
            # Get document title for label
            for entity in ctx.entities:
                if entity.get("title") or entity.get("name"):
                    labels.append(entity.get("title") or entity.get("name"))
                    break
            else:
                labels.append(f"Document {doc_id}")
        
        comparison = await self.generator.generate_comparison(
            question=f"Compare these documents focusing on {aspect}",
            contexts=contexts,
            labels=labels,
        )
        
        return {
            "comparison": comparison["response"],
            "documents_compared": labels,
            "aspect": aspect,
        }
    
    def _augment_with_history(self, question: str) -> str:
        """Augment question with conversation history context."""
        if not self._conversation_history:
            return question
        
        # Include last few exchanges
        history_context = []
        for turn in self._conversation_history[-3:]:
            history_context.append(f"Q: {turn.question}")
            history_context.append(f"A: {turn.answer[:200]}...")
        
        return f"""Previous conversation:
{chr(10).join(history_context)}

Current question: {question}"""
    
    def _add_to_history(
        self,
        question: str,
        answer: str,
        sources: list[dict],
    ) -> None:
        """Add a turn to conversation history."""
        turn = ConversationTurn(
            question=question,
            answer=answer,
            timestamp=datetime.now(),
            sources=sources,
        )
        
        self._conversation_history.append(turn)
        
        # Trim history if too long
        if len(self._conversation_history) > self._max_history:
            self._conversation_history = self._conversation_history[-self._max_history:]
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self._conversation_history = []
    
    def get_history(self) -> list[dict]:
        """Get conversation history as dicts."""
        return [
            {
                "question": turn.question,
                "answer": turn.answer,
                "timestamp": turn.timestamp.isoformat(),
            }
            for turn in self._conversation_history
        ]
