"""
Multi-signal graph-based retrieval for RAG (schema-agnostic).

Retrieves relevant context from the knowledge graph using multiple signals:
1. Graph traversal - entity relationships
2. Chunk text search - full text matching
3. Keyword matching - key term matching
4. Temporal filtering - date/duration filtering

Behavior is controlled by the RetrievalStrategy.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.neo4j_client import Neo4jClient, get_neo4j_client
from app.core.llm import LLMClient, get_llm_client
from app.schema.loader import get_schema_loader
from app.graph.dynamic_repository import DynamicGraphRepository
from app.strategies import get_strategy_manager, RetrievalStrategy

logger = logging.getLogger(__name__)


# =============================================================================
# QUERY DECOMPOSITION PROMPT
# =============================================================================

QUERY_DECOMPOSITION_PROMPT = """Analyze this user query about documents and decompose it into graph query components.

USER QUERY: {query}

AVAILABLE ENTITY TYPES: {entity_types}

Identify:
1. Intent: What is the user trying to find/understand?
2. Entity types: Which entity types from the available list are relevant?
3. Keywords: Key terms to search for in the documents
4. Temporal: Any date or time-related aspects (deadlines, periods, specific dates)?
5. Filters: Any specific conditions (names, types, values)?

Return a JSON object:
{{
    "intent": "description of user intent",
    "entity_types": ["list of relevant entity types"],
    "keywords": ["key", "search", "terms"],
    "has_temporal_aspect": true/false,
    "temporal_terms": ["deadline", "30 days"],
    "filters": {{"field": "value"}},
    "search_text": "combined search string"
}}"""


@dataclass
class RetrievalResult:
    """A single retrieval result with score."""
    
    source: str  # "graph", "chunk_text", "keyword", "temporal"
    item: dict[str, Any]
    score: float = 1.0
    item_type: str = "entity"  # "entity" or "chunk"


@dataclass
class RetrievalContext:
    """Context retrieved from the knowledge graph."""
    
    entities: list[dict[str, Any]] = field(default_factory=list)
    chunks: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    raw_text: str = ""  # Formatted text for LLM
    query_plan: Optional[dict] = None
    confidence: float = 1.0
    
    # Retrieval metadata
    search_methods_used: list[str] = field(default_factory=list)
    
    @property
    def entity_count(self) -> int:
        return len(self.entities)
    
    @property
    def chunk_count(self) -> int:
        return len(self.chunks)
    
    @property
    def is_empty(self) -> bool:
        return len(self.entities) == 0 and len(self.chunks) == 0


class GraphRetriever:
    """
    Multi-signal retriever with strategy support.
    
    Uses multiple retrieval signals based on the RetrievalStrategy:
    - Graph traversal: Navigate entity relationships
    - Chunk text search: Full text search in chunks
    - Keyword matching: Match extracted key terms
    - Temporal filtering: Filter by dates/durations
    
    Usage:
        retriever = GraphRetriever(graph_repo)
        context = await retriever.retrieve("What are the termination clauses?")
        print(context.raw_text)
    """
    
    def __init__(
        self,
        graph_repo: Optional[DynamicGraphRepository] = None,
        neo4j_client: Optional[Neo4jClient] = None,
        llm_client: Optional[LLMClient] = None,
        retrieval_strategy: Optional[RetrievalStrategy] = None,
    ):
        self.graph_repo = graph_repo
        self.neo4j = neo4j_client or get_neo4j_client()
        self.llm = llm_client or get_llm_client()
        self.strategy = retrieval_strategy or get_strategy_manager().retrieval
        
        # Get available entity types from schema
        try:
            schema_loader = get_schema_loader()
            schema = schema_loader.get_active_schema()
            self.entity_types = [e.name for e in schema.entities]
        except Exception:
            self.entity_types = ["Entity"]
    
    async def retrieve(
        self,
        query: str,
        document_id: Optional[str] = None,
    ) -> RetrievalContext:
        """
        Retrieve relevant context for a query using multiple signals.
        
        Args:
            query: User's natural language query
            document_id: Optional document ID to scope search
            
        Returns:
            RetrievalContext with entities, chunks, and formatted text
        """
        methods_used = []
        all_results: list[RetrievalResult] = []
        
        # Step 1: Analyze query
        query_analysis = await self._analyze_query(query)
        logger.debug(f"Query analysis: {query_analysis}")
        
        # Step 2: Execute retrieval methods based on strategy
        search_config = self.strategy.search
        
        # 2a: Graph traversal
        if search_config.graph_traversal.enabled:
            graph_results = await self._retrieve_via_graph(
                query_analysis, document_id
            )
            all_results.extend(graph_results)
            if graph_results:
                methods_used.append("graph_traversal")
        
        # 2b: Chunk text search
        if search_config.chunk_text_search.enabled and self.graph_repo:
            chunk_results = await self._retrieve_via_chunk_text(
                query_analysis, document_id
            )
            all_results.extend(chunk_results)
            if chunk_results:
                methods_used.append("chunk_text_search")
        
        # 2c: Keyword matching
        if search_config.keyword_matching.enabled and self.graph_repo:
            keyword_results = await self._retrieve_via_keywords(
                query_analysis, document_id
            )
            all_results.extend(keyword_results)
            if keyword_results:
                methods_used.append("keyword_matching")
        
        # 2d: Temporal filtering
        if search_config.temporal_filtering.enabled and self.graph_repo:
            if query_analysis.get("has_temporal_aspect"):
                temporal_results = await self._retrieve_via_temporal(
                    query_analysis, document_id
                )
                all_results.extend(temporal_results)
                if temporal_results:
                    methods_used.append("temporal_filtering")
        
        # Step 3: Score and rank results
        scored_results = self._score_results(all_results)
        
        # Step 4: Deduplicate and limit
        entities, chunks, relationships = self._process_results(scored_results)
        
        # Step 5: Format context
        raw_text = self._format_context(entities, chunks, relationships, query)
        
        return RetrievalContext(
            entities=entities,
            chunks=chunks,
            relationships=relationships,
            raw_text=raw_text,
            query_plan=query_analysis,
            search_methods_used=methods_used,
        )
    
    async def _analyze_query(self, query: str) -> dict[str, Any]:
        """Analyze query to determine retrieval strategy."""
        try:
            prompt = QUERY_DECOMPOSITION_PROMPT.format(
                query=query,
                entity_types=", ".join(self.entity_types),
            )
            response = await self.llm.complete(prompt)
            
            # Parse JSON response
            import json
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            cleaned = cleaned.strip()
            
            return json.loads(cleaned)
        except Exception as e:
            logger.warning(f"Query analysis failed: {e}")
            # Return default analysis with keywords extracted
            keywords = [w for w in query.lower().split() if len(w) > 3]
            return {
                "intent": "general",
                "entity_types": self.entity_types[:3],
                "keywords": keywords[:5],
                "has_temporal_aspect": any(
                    t in query.lower() for t in ["date", "deadline", "days", "month", "year", "when"]
                ),
                "temporal_terms": [],
                "filters": {},
                "search_text": query,
            }
    
    async def _retrieve_via_graph(
        self,
        query_analysis: dict[str, Any],
        document_id: Optional[str],
    ) -> list[RetrievalResult]:
        """Retrieve via graph traversal."""
        results = []
        entity_types = query_analysis.get("entity_types", self.entity_types[:3])
        filters = query_analysis.get("filters", {})
        max_depth = self.strategy.search.graph_traversal.max_depth
        
        await self.neo4j.connect()
        
        # Search each relevant entity type
        for entity_type in entity_types:
            if filters:
                # Search with filters
                where_parts = []
                params = {"limit": self.strategy.limits.max_entities}
                
                for key, value in filters.items():
                    param_name = f"filter_{key}"
                    where_parts.append(f"toLower(toString(n.{key})) CONTAINS toLower(${param_name})")
                    params[param_name] = str(value)
                
                where_clause = " AND ".join(where_parts)
                query = f"""
                MATCH (n:{entity_type})
                WHERE {where_clause}
                RETURN n
                LIMIT $limit
                """
            else:
                query = f"""
                MATCH (n:{entity_type})
                RETURN n
                LIMIT $limit
                """
                params = {"limit": self.strategy.limits.max_entities}
            
            try:
                query_results = await self.neo4j.execute_query(query, params)
                for r in query_results:
                    entity = dict(r["n"])
                    entity["_type"] = entity_type
                    results.append(RetrievalResult(
                        source="graph",
                        item=entity,
                        score=self.strategy.scoring.graph_match_weight,
                        item_type="entity",
                    ))
            except Exception as e:
                logger.debug(f"Graph query failed for {entity_type}: {e}")
        
        # Expand context via relationships if we have results
        if results and max_depth > 1:
            entity_ids = [r.item.get("id") for r in results if r.item.get("id")]
            if entity_ids:
                expanded = await self._expand_graph_context(entity_ids)
                results.extend(expanded)
        
        return results
    
    async def _expand_graph_context(
        self, entity_ids: list[str]
    ) -> list[RetrievalResult]:
        """Expand context by following relationships."""
        results = []
        
        query = """
        MATCH (n)
        WHERE n.id IN $ids
        OPTIONAL MATCH (n)-[r]-(related)
        WHERE NOT 'Chunk' IN labels(related) AND NOT 'Document' IN labels(related)
        RETURN collect(DISTINCT related) as entities,
               collect(DISTINCT {
                   source: startNode(r).id,
                   target: endNode(r).id,
                   type: type(r)
               }) as relationships
        """
        
        try:
            query_results = await self.neo4j.execute_query(query, {"ids": entity_ids})
            if query_results:
                result = query_results[0]
                for entity in result.get("entities", []):
                    if entity:
                        results.append(RetrievalResult(
                            source="graph",
                            item=dict(entity),
                            score=self.strategy.scoring.graph_match_weight * 0.8,  # Lower for expanded
                            item_type="entity",
                        ))
        except Exception as e:
            logger.debug(f"Graph expansion failed: {e}")
        
        return results
    
    async def _retrieve_via_chunk_text(
        self,
        query_analysis: dict[str, Any],
        document_id: Optional[str],
    ) -> list[RetrievalResult]:
        """Retrieve via chunk text search."""
        results = []
        search_text = query_analysis.get("search_text", "")
        keywords = query_analysis.get("keywords", [])
        
        # Combine search text and keywords
        search_terms = [search_text] + keywords[:3]
        
        for term in search_terms:
            if not term:
                continue
            
            try:
                chunks = await self.graph_repo.search_chunks_by_text(
                    search_text=term,
                    document_id=document_id,
                    limit=self.strategy.limits.max_chunks // 2,
                )
                
                for chunk in chunks:
                    results.append(RetrievalResult(
                        source="chunk_text",
                        item=chunk,
                        score=self.strategy.scoring.text_match_weight,
                        item_type="chunk",
                    ))
            except Exception as e:
                logger.debug(f"Chunk text search failed for '{term}': {e}")
        
        return results
    
    async def _retrieve_via_keywords(
        self,
        query_analysis: dict[str, Any],
        document_id: Optional[str],
    ) -> list[RetrievalResult]:
        """Retrieve via keyword matching on extracted key terms."""
        results = []
        keywords = query_analysis.get("keywords", [])
        
        if not keywords:
            return results
        
        try:
            matches = await self.graph_repo.search_chunks_by_key_terms(
                terms=keywords,
                document_id=document_id,
                limit=self.strategy.limits.max_chunks // 2,
            )
            
            for match in matches:
                chunk = match.get("chunk", {})
                match_count = match.get("match_count", 1)
                
                # Score based on match count
                score = self.strategy.scoring.text_match_weight * (1 + 0.2 * match_count)
                
                results.append(RetrievalResult(
                    source="keyword",
                    item=chunk,
                    score=score,
                    item_type="chunk",
                ))
        except Exception as e:
            logger.debug(f"Keyword search failed: {e}")
        
        return results
    
    async def _retrieve_via_temporal(
        self,
        query_analysis: dict[str, Any],
        document_id: Optional[str],
    ) -> list[RetrievalResult]:
        """Retrieve chunks with temporal references."""
        results = []
        
        try:
            chunks = await self.graph_repo.get_chunks_with_temporal_refs(
                document_id=document_id,
            )
            
            for chunk in chunks:
                results.append(RetrievalResult(
                    source="temporal",
                    item=chunk,
                    score=self.strategy.scoring.text_match_weight * 0.9,
                    item_type="chunk",
                ))
        except Exception as e:
            logger.debug(f"Temporal search failed: {e}")
        
        return results
    
    def _score_results(
        self, results: list[RetrievalResult]
    ) -> list[RetrievalResult]:
        """Score and sort results."""
        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results
    
    def _process_results(
        self, results: list[RetrievalResult]
    ) -> tuple[list[dict], list[dict], list[dict]]:
        """Deduplicate and separate results by type."""
        entities = []
        chunks = []
        relationships = []
        
        seen_entity_ids = set()
        seen_chunk_ids = set()
        
        confidence_min = self.strategy.scoring.entity_confidence_min
        
        for result in results:
            item = result.item
            item_id = item.get("id")
            
            if not item_id:
                continue
            
            # Filter by confidence for entities
            if result.item_type == "entity":
                confidence = item.get("confidence", 1.0)
                if confidence < confidence_min:
                    continue
                
                if item_id not in seen_entity_ids:
                    seen_entity_ids.add(item_id)
                    entities.append(item)
                    
                    if len(entities) >= self.strategy.limits.max_entities:
                        break
            
            elif result.item_type == "chunk":
                if item_id not in seen_chunk_ids:
                    seen_chunk_ids.add(item_id)
                    chunks.append(item)
                    
                    if len(chunks) >= self.strategy.limits.max_chunks:
                        break
        
        return entities, chunks, relationships
    
    def _format_context(
        self,
        entities: list[dict[str, Any]],
        chunks: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
        original_query: str,
    ) -> str:
        """Format retrieved context as text for LLM."""
        include_config = self.strategy.context.include_metadata
        parts = [f"# Retrieved Context for Query: {original_query}\n"]
        
        # Format chunks
        if chunks:
            parts.append("\n## Relevant Document Sections\n")
            
            current_section = None
            for chunk in chunks:
                # Add section header if available and changed
                if include_config.section_heading:
                    section = chunk.get("section_heading")
                    if section and section != current_section:
                        current_section = section
                        parts.append(f"\n### {section}\n")
                
                # Add page reference if available
                if include_config.page_number:
                    page = chunk.get("page_number")
                    if page:
                        parts.append(f"[Page {page}] ")
                
                # Add chunk text
                text = chunk.get("text", "")
                parts.append(f"{text}\n")
        
        # Format entities
        if entities:
            parts.append("\n## Extracted Entities\n")
            
            # Group entities by type
            entities_by_type: dict[str, list] = {}
            for entity in entities:
                entity_type = entity.get("_type", entity.get("entity_type", "Entity"))
                if entity_type not in entities_by_type:
                    entities_by_type[entity_type] = []
                entities_by_type[entity_type].append(entity)
            
            for entity_type, type_entities in entities_by_type.items():
                parts.append(f"\n### {entity_type}s\n")
                for entity in type_entities:
                    parts.append(self._format_entity(entity))
        
        # Format relationships
        if relationships:
            parts.append("\n## Relationships\n")
            for rel in relationships:
                if rel.get("source") and rel.get("target"):
                    parts.append(
                        f"- {rel['source']} --[{rel.get('type', 'RELATED')}]--> {rel['target']}"
                    )
        
        return "\n".join(parts)
    
    def _format_entity(self, entity: dict[str, Any]) -> str:
        """Format a single entity as text."""
        priority_fields = ["name", "title", "description", "summary", "text", "type", "value"]
        
        all_fields = list(entity.keys())
        fields = [f for f in priority_fields if f in all_fields]
        fields.extend([f for f in all_fields if f not in fields and not f.startswith("_")])
        
        lines = [f"**{entity.get('name', entity.get('title', entity.get('id', 'Entity')))}**"]
        
        for field in fields[:10]:  # Limit fields shown
            if field in entity and entity[field]:
                value = entity[field]
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value[:5])
                elif isinstance(value, str) and len(value) > 200:
                    value = value[:200] + "..."
                lines.append(f"  - {field}: {value}")
        
        return "\n".join(lines) + "\n"
    
    # ==========================================================================
    # CONVENIENCE METHODS
    # ==========================================================================
    
    async def retrieve_by_keywords(
        self,
        keywords: list[str],
        document_id: Optional[str] = None,
    ) -> RetrievalContext:
        """Simple keyword-based retrieval."""
        query = " ".join(keywords)
        return await self.retrieve(query, document_id)
    
    async def retrieve_for_document(
        self,
        document_id: str,
    ) -> RetrievalContext:
        """Retrieve all context for a specific document."""
        if self.graph_repo:
            chunks = await self.graph_repo.get_chunks_for_document(document_id)
            graph_data = await self.graph_repo.get_graph_for_document(document_id)
            
            return RetrievalContext(
                entities=graph_data.get("entities", []),
                chunks=chunks,
                relationships=graph_data.get("relationships", []),
                raw_text=self._format_context(
                    graph_data.get("entities", []),
                    chunks,
                    graph_data.get("relationships", []),
                    f"Document: {document_id}",
                ),
                search_methods_used=["document_retrieval"],
            )
        
        return RetrievalContext()
