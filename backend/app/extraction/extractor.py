"""
LLM-based entity and relationship extraction from documents.

This module orchestrates the extraction process:
1. Prepare document chunks
2. Run extraction prompts via LLM
3. Parse and validate results
4. Assemble final knowledge graph
"""

import json
import logging
from typing import Optional

from app.core.llm import LLMClient, get_extraction_client
from app.extraction.ontology import (
    ExtractedGraph,
    Contract,
    Party,
    Clause,
    Obligation,
    ContractDate,
    Amount,
    Relationship,
)
from app.extraction.prompts import (
    EXTRACTION_SYSTEM_PROMPT,
    FULL_EXTRACTION_PROMPT,
    CHUNK_EXTRACTION_PROMPT,
)
from app.extraction.validator import ExtractionValidator, ValidationResult

logger = logging.getLogger(__name__)


class ExtractionResult:
    """Container for extraction result with metadata."""
    
    def __init__(
        self,
        graph: ExtractedGraph,
        validation: ValidationResult,
        raw_response: Optional[str] = None,
    ):
        self.graph = graph
        self.validation = validation
        self.raw_response = raw_response
        self.success = validation.is_valid
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "entity_count": self.graph.entity_count,
            "relationship_count": self.graph.relationship_count,
            "validation": self.validation.to_dict(),
        }


class EntityExtractor:
    """
    Extracts entities and relationships from text using LLM.
    
    Supports two modes:
    1. Full document extraction (for smaller documents)
    2. Chunk-by-chunk extraction (for larger documents)
    
    Usage:
        extractor = EntityExtractor()
        result = await extractor.extract(document_text)
        
        if result.success:
            graph = result.graph
            # Process graph...
    """
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        validator: Optional[ExtractionValidator] = None,
        chunk_threshold: int = 8000,  # Characters threshold for chunking
    ):
        self.llm = llm_client or get_extraction_client()
        self.validator = validator or ExtractionValidator()
        self.chunk_threshold = chunk_threshold
    
    async def extract(
        self,
        text: str,
        source_document: str = "unknown",
        use_chunking: Optional[bool] = None,
    ) -> ExtractionResult:
        """
        Extract entities and relationships from text.
        
        Args:
            text: Document text to process
            source_document: Identifier for source document
            use_chunking: Force chunking mode (auto-detect if None)
            
        Returns:
            ExtractionResult with graph and validation
        """
        # Decide extraction strategy
        should_chunk = use_chunking if use_chunking is not None else len(text) > self.chunk_threshold
        
        if should_chunk:
            logger.info(f"Using chunked extraction for {len(text)} characters")
            return await self._extract_chunked(text, source_document)
        else:
            logger.info(f"Using full document extraction for {len(text)} characters")
            return await self._extract_full(text, source_document)
    
    async def _extract_full(
        self, text: str, source_document: str
    ) -> ExtractionResult:
        """Extract from full document in single pass."""
        prompt = FULL_EXTRACTION_PROMPT.format(text=text)
        
        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=EXTRACTION_SYSTEM_PROMPT,
            )
            
            # Parse response
            graph = self._parse_extraction_response(
                response, source_document
            )
            
            # Validate
            validation = self.validator.validate(graph)
            
            return ExtractionResult(
                graph=graph,
                validation=validation,
                raw_response=response,
            )
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            # Return empty graph with error
            empty_graph = ExtractedGraph(
                source_document=source_document,
                extraction_model=self.llm.model,
            )
            validation = ValidationResult()
            validation.add_error(f"Extraction failed: {str(e)}")
            return ExtractionResult(
                graph=empty_graph,
                validation=validation,
            )
    
    async def _extract_chunked(
        self, text: str, source_document: str
    ) -> ExtractionResult:
        """Extract from document chunk by chunk and merge results."""
        from app.ingestion.chunker import TextChunker
        
        chunker = TextChunker()
        chunks = chunker.chunk_text(text)
        
        logger.info(f"Processing {len(chunks)} chunks")
        
        # Collect entities from all chunks
        all_contracts: list[Contract] = []
        all_parties: list[Party] = []
        all_clauses: list[Clause] = []
        all_obligations: list[Obligation] = []
        all_dates: list[ContractDate] = []
        all_amounts: list[Amount] = []
        all_relationships: list[Relationship] = []
        
        # Track context for subsequent chunks
        context_summary = ""
        
        for i, chunk in enumerate(chunks):
            prompt = CHUNK_EXTRACTION_PROMPT.format(
                chunk_index=i + 1,
                total_chunks=len(chunks),
                context=context_summary,
                text=chunk.text,
            )
            
            try:
                response = await self.llm.complete(
                    prompt=prompt,
                    system_prompt=EXTRACTION_SYSTEM_PROMPT,
                )
                
                chunk_graph = self._parse_extraction_response(
                    response, source_document
                )
                
                # Merge entities
                all_contracts.extend(chunk_graph.contracts)
                all_parties.extend(chunk_graph.parties)
                all_clauses.extend(chunk_graph.clauses)
                all_obligations.extend(chunk_graph.obligations)
                all_dates.extend(chunk_graph.dates)
                all_amounts.extend(chunk_graph.amounts)
                all_relationships.extend(chunk_graph.relationships)
                
                # Update context for next chunk
                context_summary = self._build_context_summary(chunk_graph)
                
            except Exception as e:
                logger.error(f"Chunk {i+1} extraction failed: {e}")
                continue
        
        # Deduplicate entities
        merged_graph = self._merge_and_deduplicate(
            contracts=all_contracts,
            parties=all_parties,
            clauses=all_clauses,
            obligations=all_obligations,
            dates=all_dates,
            amounts=all_amounts,
            relationships=all_relationships,
            source_document=source_document,
        )
        
        # Validate merged result
        validation = self.validator.validate(merged_graph)
        
        return ExtractionResult(
            graph=merged_graph,
            validation=validation,
        )
    
    def _parse_extraction_response(
        self, response: str, source_document: str
    ) -> ExtractedGraph:
        """Parse LLM response into ExtractedGraph."""
        try:
            # Clean response - remove markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            data = json.loads(cleaned)
            
            # Parse entities
            contracts = [
                Contract.model_validate(c) 
                for c in data.get("contracts", [])
            ]
            parties = [
                Party.model_validate(p) 
                for p in data.get("parties", [])
            ]
            clauses = [
                Clause.model_validate(c) 
                for c in data.get("clauses", [])
            ]
            obligations = [
                Obligation.model_validate(o) 
                for o in data.get("obligations", [])
            ]
            dates = [
                ContractDate.model_validate(d) 
                for d in data.get("dates", [])
            ]
            amounts = [
                Amount.model_validate(a) 
                for a in data.get("amounts", [])
            ]
            relationships = [
                Relationship.model_validate(r) 
                for r in data.get("relationships", [])
            ]
            
            return ExtractedGraph(
                source_document=source_document,
                extraction_model=self.llm.model,
                contracts=contracts,
                parties=parties,
                clauses=clauses,
                obligations=obligations,
                dates=dates,
                amounts=amounts,
                relationships=relationships,
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response[:500]}...")
            return ExtractedGraph(
                source_document=source_document,
                extraction_model=self.llm.model,
            )
        except Exception as e:
            logger.error(f"Failed to parse extraction response: {e}")
            return ExtractedGraph(
                source_document=source_document,
                extraction_model=self.llm.model,
            )
    
    def _build_context_summary(self, graph: ExtractedGraph) -> str:
        """Build context summary from extracted graph for next chunk."""
        parts = []
        
        if graph.contracts:
            parts.append(f"Contract: {graph.contracts[0].title}")
        
        if graph.parties:
            party_names = [p.name for p in graph.parties[:5]]
            parts.append(f"Parties: {', '.join(party_names)}")
        
        if graph.clauses:
            clause_types = list(set(c.clause_type.value for c in graph.clauses[:5]))
            parts.append(f"Clauses found: {', '.join(clause_types)}")
        
        return "\n".join(parts) if parts else "No context from previous chunks."
    
    def _merge_and_deduplicate(
        self,
        contracts: list[Contract],
        parties: list[Party],
        clauses: list[Clause],
        obligations: list[Obligation],
        dates: list[ContractDate],
        amounts: list[Amount],
        relationships: list[Relationship],
        source_document: str,
    ) -> ExtractedGraph:
        """Merge and deduplicate entities from multiple chunks."""
        # Deduplicate parties by name
        unique_parties = {}
        for party in parties:
            key = party.name.lower().strip()
            if key not in unique_parties:
                unique_parties[key] = party
        
        # Deduplicate contracts by title
        unique_contracts = {}
        for contract in contracts:
            key = contract.title.lower().strip()
            if key not in unique_contracts:
                unique_contracts[key] = contract
        
        # Clauses - keep all but mark duplicates
        seen_clause_texts = set()
        unique_clauses = []
        for clause in clauses:
            text_key = clause.text[:100].lower().strip()
            if text_key not in seen_clause_texts:
                unique_clauses.append(clause)
                seen_clause_texts.add(text_key)
        
        # For dates and amounts, simple deduplication by description
        unique_dates = {d.description: d for d in dates}.values()
        unique_amounts = {a.description: a for a in amounts}.values()
        
        # Relationships - deduplicate by (source, target, type)
        unique_rels = {}
        for rel in relationships:
            key = (rel.source_id, rel.target_id, rel.relationship_type)
            if key not in unique_rels:
                unique_rels[key] = rel
        
        return ExtractedGraph(
            source_document=source_document,
            extraction_model=self.llm.model,
            contracts=list(unique_contracts.values()),
            parties=list(unique_parties.values()),
            clauses=unique_clauses,
            obligations=obligations,  # Keep all obligations
            dates=list(unique_dates),
            amounts=list(unique_amounts),
            relationships=list(unique_rels.values()),
        )
    
    async def extract_specific_entities(
        self,
        text: str,
        entity_types: list[str],
        source_document: str = "unknown",
    ) -> ExtractedGraph:
        """
        Extract only specific entity types from text.
        
        Useful for targeted extraction when you only need certain entities.
        
        Args:
            text: Document text
            entity_types: List of entity types to extract
            source_document: Source identifier
            
        Returns:
            ExtractedGraph with only requested entity types
        """
        # Build targeted prompt
        type_instructions = []
        if "Party" in entity_types:
            type_instructions.append("- Extract all parties (names, types, roles)")
        if "Clause" in entity_types:
            type_instructions.append("- Extract all clauses (type, text, summary)")
        if "Obligation" in entity_types:
            type_instructions.append("- Extract all obligations")
        if "Date" in entity_types:
            type_instructions.append("- Extract all significant dates")
        if "Amount" in entity_types:
            type_instructions.append("- Extract all monetary amounts")
        
        prompt = f"""Extract the following from this text:
{chr(10).join(type_instructions)}

Text:
{text}

Return a JSON object with the extracted entities."""
        
        response = await self.llm.complete(
            prompt=prompt,
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
        )
        
        return self._parse_extraction_response(response, source_document)
