"""
Response generation for RAG.

Generates natural language responses using retrieved context.
"""

import logging
from typing import Optional

from app.core.llm import LLMClient, get_rag_client
from app.rag.retriever import RetrievalContext

logger = logging.getLogger(__name__)


# Response generation prompts
RAG_SYSTEM_PROMPT = """You are an expert legal document analyst assistant. Your role is to answer questions about contracts and legal documents using the provided context.

GUIDELINES:
1. Base your answers ONLY on the provided context
2. If the context doesn't contain enough information, say so clearly
3. Quote specific text when relevant
4. Be precise about which contracts, clauses, or parties you're referring to
5. Highlight any ambiguities or uncertainties
6. Structure your response clearly with sections if needed

RESPONSE FORMAT:
- Start with a direct answer to the question
- Provide supporting details from the context
- Note any limitations or missing information
- Suggest follow-up questions if relevant"""


RAG_USER_PROMPT = """## Context from Knowledge Graph

{context}

## User Question

{question}

## Instructions

Based on the context above, provide a comprehensive answer to the user's question. If the context doesn't contain sufficient information, explain what's missing and suggest what additional information might be needed."""


SUMMARIZATION_PROMPT = """Summarize the following contract information concisely:

{context}

Provide:
1. Key parties involved
2. Main obligations and terms
3. Important dates and amounts
4. Notable clauses or provisions"""


class ResponseGenerator:
    """
    Generates natural language responses using LLM and retrieved context.
    
    Features:
    - Context-aware response generation
    - Source attribution
    - Confidence scoring
    - Response formatting
    
    Usage:
        generator = ResponseGenerator()
        response = await generator.generate(
            question="What are the termination clauses?",
            context=retrieved_context
        )
    """
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        system_prompt: Optional[str] = None,
    ):
        self.llm = llm_client or get_rag_client()
        self.system_prompt = system_prompt or RAG_SYSTEM_PROMPT
    
    async def generate(
        self,
        question: str,
        context: RetrievalContext,
        include_sources: bool = True,
    ) -> dict:
        """
        Generate a response to a question using retrieved context.
        
        Args:
            question: User's question
            context: Retrieved context from knowledge graph
            include_sources: Whether to include source references
            
        Returns:
            Dict with response, sources, and metadata
        """
        # Check if we have context
        if context.is_empty:
            return {
                "response": "I couldn't find relevant information in the knowledge graph to answer your question. Please try rephrasing your question or ensure the relevant documents have been processed.",
                "sources": [],
                "confidence": 0.0,
                "has_context": False,
            }
        
        # Build prompt
        prompt = RAG_USER_PROMPT.format(
            context=context.raw_text,
            question=question,
        )
        
        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=self.system_prompt,
            )
            
            # Extract sources if requested
            sources = []
            if include_sources:
                sources = self._extract_sources(context)
            
            # Estimate confidence based on context quality
            confidence = self._estimate_confidence(context, response)
            
            return {
                "response": response,
                "sources": sources,
                "confidence": confidence,
                "has_context": True,
                "entity_count": context.entity_count,
            }
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return {
                "response": f"I encountered an error while generating the response: {str(e)}",
                "sources": [],
                "confidence": 0.0,
                "has_context": True,
                "error": str(e),
            }
    
    async def generate_summary(
        self,
        context: RetrievalContext,
    ) -> str:
        """Generate a summary of the retrieved context."""
        if context.is_empty:
            return "No information available to summarize."
        
        prompt = SUMMARIZATION_PROMPT.format(context=context.raw_text)
        
        return await self.llm.complete(
            prompt=prompt,
            system_prompt="You are a legal document summarization assistant. Be concise and accurate.",
        )
    
    async def generate_comparison(
        self,
        question: str,
        contexts: list[RetrievalContext],
        labels: list[str],
    ) -> dict:
        """
        Generate a comparison between multiple contexts.
        
        Useful for comparing clauses across contracts.
        """
        if not contexts:
            return {
                "response": "No contexts provided for comparison.",
                "confidence": 0.0,
            }
        
        # Build comparison context
        comparison_parts = []
        for label, ctx in zip(labels, contexts):
            comparison_parts.append(f"## {label}\n{ctx.raw_text}")
        
        combined_context = "\n\n---\n\n".join(comparison_parts)
        
        prompt = f"""Compare the following contract information:

{combined_context}

## Comparison Request

{question}

Provide a structured comparison highlighting:
1. Similarities
2. Differences
3. Key distinctions
4. Recommendations (if applicable)"""
        
        response = await self.llm.complete(
            prompt=prompt,
            system_prompt=self.system_prompt,
        )
        
        return {
            "response": response,
            "contexts_compared": len(contexts),
            "labels": labels,
        }
    
    def _extract_sources(
        self, context: RetrievalContext
    ) -> list[dict]:
        """Extract source references from context."""
        sources = []
        
        for entity in context.entities:
            source = {
                "id": entity.get("id"),
                "type": entity.get("_label", "Unknown"),
            }
            
            # Add identifying info based on type
            if "title" in entity:
                source["title"] = entity["title"]
            if "name" in entity:
                source["name"] = entity["name"]
            if "clause_type" in entity:
                source["clause_type"] = entity["clause_type"]
            if "source_file" in entity:
                source["source_file"] = entity["source_file"]
            
            sources.append(source)
        
        return sources
    
    def _estimate_confidence(
        self,
        context: RetrievalContext,
        response: str,
    ) -> float:
        """Estimate confidence in the response."""
        # Base confidence on context quality
        confidence = 0.5
        
        # More entities = more context = higher confidence
        entity_factor = min(context.entity_count / 10, 0.3)
        confidence += entity_factor
        
        # Check if response indicates uncertainty
        uncertainty_phrases = [
            "i don't know",
            "not sure",
            "unclear",
            "cannot determine",
            "insufficient",
            "no information",
        ]
        
        response_lower = response.lower()
        for phrase in uncertainty_phrases:
            if phrase in response_lower:
                confidence -= 0.2
                break
        
        # Check if response is substantive
        if len(response) > 200:
            confidence += 0.1
        
        return max(0.0, min(1.0, confidence))
    
    async def generate_follow_up_questions(
        self,
        question: str,
        response: str,
        context: RetrievalContext,
    ) -> list[str]:
        """Generate suggested follow-up questions."""
        prompt = f"""Based on this Q&A exchange about contracts:

Question: {question}

Answer: {response}

Generate 3 relevant follow-up questions that would help the user understand the contracts better. 
Return only the questions, one per line."""
        
        result = await self.llm.complete(
            prompt=prompt,
            system_prompt="You are a helpful assistant generating follow-up questions.",
            max_tokens=200,
        )
        
        # Parse questions from response
        questions = [
            q.strip().lstrip("0123456789.-) ")
            for q in result.strip().split("\n")
            if q.strip()
        ]
        
        return questions[:3]
