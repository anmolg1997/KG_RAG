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
class CypherQuery:
    """A tracked Cypher query."""
    description: str
    query: str
    params: dict[str, Any]
    result_count: int = 0
    execution_time_ms: float = 0


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
    
    # Debug info - Cypher queries executed
    cypher_queries: list[CypherQuery] = field(default_factory=list)
    
    @property
    def entity_count(self) -> int:
        return len(self.entities)
    
    @property
    def chunk_count(self) -> int:
        return len(self.chunks)
    
    @property
    def is_empty(self) -> bool:
        return len(self.entities) == 0 and len(self.chunks) == 0
    
    def to_debug_dict(self) -> dict[str, Any]:
        """Convert retrieval context to debug dictionary."""
        return {
            "query_analysis": self.query_plan,
            "cypher_queries": [
                {
                    "description": q.description,
                    "query": q.query,
                    "params": q.params,
                    "result_count": q.result_count,
                    "execution_time_ms": q.execution_time_ms,
                }
                for q in self.cypher_queries
            ],
            "retrieval_results": {
                "entities": self.entities[:20],  # Limit for response size
                "chunks": [
                    {
                        "id": c.get("id"),
                        "text": c.get("text", "")[:300] + "..." if len(c.get("text", "")) > 300 else c.get("text", ""),
                        "page_number": c.get("page_number"),
                        "section_heading": c.get("section_heading"),
                        "key_terms": c.get("key_terms", [])[:10],
                    }
                    for c in self.chunks[:10]
                ],
                "entity_count": len(self.entities),
                "chunk_count": len(self.chunks),
            },
            "search_methods_used": self.search_methods_used,
        }


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
        except Exception as e:
            logger.debug(f"Could not load schema entity types, using default: {e}")
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
        cypher_queries: list[CypherQuery] = []
        
        # ─────────────────────────────────────────────────────────────
        # STEP 2a: Analyze query (LLM)
        # ─────────────────────────────────────────────────────────────
        logger.info("│  ├─ Analyzing query...")
        query_analysis = await self._analyze_query(query)
        
        intent = query_analysis.get("intent", "general")
        entity_types = query_analysis.get("entity_types", [])
        keywords = query_analysis.get("keywords", [])
        
        logger.info(f"│  │  Intent: {intent}")
        logger.info(f"│  │  Target entities: {', '.join(entity_types[:3]) if entity_types else 'any'}")
        logger.debug(f"│  │  Keywords: {keywords}")
        
        # ─────────────────────────────────────────────────────────────
        # STEP 2b: Execute retrieval methods
        # ─────────────────────────────────────────────────────────────
        search_config = self.strategy.search
        logger.info("│  ├─ Executing search methods:")
        
        # 2b-i: Graph traversal
        if search_config.graph_traversal.enabled:
            logger.info("│  │  ├─ Graph traversal...")
            graph_results, graph_queries = await self._retrieve_via_graph(
                query_analysis, document_id
            )
            all_results.extend(graph_results)
            cypher_queries.extend(graph_queries)
            if graph_results:
                methods_used.append("graph_traversal")
                logger.info(f"│  │  │  └─ Found {len(graph_results)} results")
        
        # 2b-ii: Chunk text search
        if search_config.chunk_text_search.enabled and self.graph_repo:
            logger.info("│  │  ├─ Chunk text search...")
            chunk_results, chunk_queries = await self._retrieve_via_chunk_text(
                query_analysis, document_id
            )
            all_results.extend(chunk_results)
            cypher_queries.extend(chunk_queries)
            if chunk_results:
                methods_used.append("chunk_text_search")
                logger.info(f"│  │  │  └─ Found {len(chunk_results)} results")
        
        # 2b-iii: Keyword matching
        if search_config.keyword_matching.enabled and self.graph_repo:
            logger.info("│  │  ├─ Keyword matching...")
            keyword_results, keyword_queries = await self._retrieve_via_keywords(
                query_analysis, document_id
            )
            all_results.extend(keyword_results)
            cypher_queries.extend(keyword_queries)
            if keyword_results:
                methods_used.append("keyword_matching")
                logger.info(f"│  │  │  └─ Found {len(keyword_results)} results")
        
        # 2b-iv: Temporal filtering
        if search_config.temporal_filtering.enabled and self.graph_repo:
            if query_analysis.get("has_temporal_aspect"):
                logger.info("│  │  ├─ Temporal filtering...")
                temporal_results, temporal_queries = await self._retrieve_via_temporal(
                    query_analysis, document_id
                )
                all_results.extend(temporal_results)
                cypher_queries.extend(temporal_queries)
                if temporal_results:
                    methods_used.append("temporal_filtering")
                    logger.info(f"│  │  │  └─ Found {len(temporal_results)} results")
        
        logger.info(f"│  │  └─ Total raw results: {len(all_results)}")
        
        # ─────────────────────────────────────────────────────────────
        # STEP 2c: Score and deduplicate
        # ─────────────────────────────────────────────────────────────
        logger.info("│  ├─ Scoring and deduplicating...")
        scored_results = self._score_results(all_results)
        entities, chunks, relationships = self._process_results(scored_results)
        
        logger.info(f"│  │  └─ After dedup: {len(entities)} entities, {len(chunks)} chunks")
        
        # ─────────────────────────────────────────────────────────────
        # STEP 2d: Format context
        # ─────────────────────────────────────────────────────────────
        logger.info("│  └─ Formatting context...")
        raw_text = self._format_context(entities, chunks, relationships, query)
        
        return RetrievalContext(
            entities=entities,
            chunks=chunks,
            relationships=relationships,
            raw_text=raw_text,
            query_plan=query_analysis,
            search_methods_used=methods_used,
            cypher_queries=cypher_queries,
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
    ) -> tuple[list[RetrievalResult], list[CypherQuery]]:
        """Retrieve via graph traversal."""
        import time
        results = []
        queries = []
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
                start_time = time.time()
                query_results = await self.neo4j.execute_query(query, params)
                exec_time = (time.time() - start_time) * 1000
                
                # Track this query
                queries.append(CypherQuery(
                    description=f"Get {entity_type} entities",
                    query=query.strip(),
                    params=params,
                    result_count=len(query_results),
                    execution_time_ms=exec_time,
                ))
                
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
                expanded, expand_queries = await self._expand_graph_context(entity_ids)
                results.extend(expanded)
                queries.extend(expand_queries)
        
        return results, queries
    
    async def _expand_graph_context(
        self, entity_ids: list[str]
    ) -> tuple[list[RetrievalResult], list[CypherQuery]]:
        """Expand context by following relationships."""
        import time
        results = []
        queries = []
        
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
        params = {"ids": entity_ids}
        
        try:
            start_time = time.time()
            query_results = await self.neo4j.execute_query(query, params)
            exec_time = (time.time() - start_time) * 1000
            
            entity_count = 0
            if query_results:
                result = query_results[0]
                for entity in result.get("entities", []):
                    if entity:
                        entity_count += 1
                        results.append(RetrievalResult(
                            source="graph",
                            item=dict(entity),
                            score=self.strategy.scoring.graph_match_weight * 0.8,  # Lower for expanded
                            item_type="entity",
                        ))
            
            queries.append(CypherQuery(
                description="Expand graph context via relationships",
                query=query.strip(),
                params=params,
                result_count=entity_count,
                execution_time_ms=exec_time,
            ))
        except Exception as e:
            logger.debug(f"Graph expansion failed: {e}")
        
        return results, queries
    
    async def _retrieve_via_chunk_text(
        self,
        query_analysis: dict[str, Any],
        document_id: Optional[str],
    ) -> tuple[list[RetrievalResult], list[CypherQuery]]:
        """Retrieve via chunk text search."""
        results = []
        queries = []
        search_text = query_analysis.get("search_text", "")
        keywords = query_analysis.get("keywords", [])
        
        # Combine search text and keywords
        search_terms = [search_text] + keywords[:3]
        
        for term in search_terms:
            if not term:
                continue
            
            try:
                chunks, cypher_info = await self.graph_repo.search_chunks_by_text(
                    search_text=term,
                    document_id=document_id,
                    limit=self.strategy.limits.max_chunks // 2,
                    return_query=True,
                )
                
                if cypher_info:
                    queries.append(CypherQuery(
                        description=f"Search chunks for '{term[:30]}...'",
                        query=cypher_info.get("query", ""),
                        params=cypher_info.get("params", {}),
                        result_count=len(chunks),
                        execution_time_ms=cypher_info.get("execution_time_ms", 0),
                    ))
                
                for chunk in chunks:
                    results.append(RetrievalResult(
                        source="chunk_text",
                        item=chunk,
                        score=self.strategy.scoring.text_match_weight,
                        item_type="chunk",
                    ))
            except Exception as e:
                logger.debug(f"Chunk text search failed for '{term}': {e}")
        
        return results, queries
    
    async def _retrieve_via_keywords(
        self,
        query_analysis: dict[str, Any],
        document_id: Optional[str],
    ) -> tuple[list[RetrievalResult], list[CypherQuery]]:
        """Retrieve via keyword matching on extracted key terms."""
        results = []
        queries = []
        keywords = query_analysis.get("keywords", [])
        
        if not keywords:
            return results, queries
        
        try:
            matches, cypher_info = await self.graph_repo.search_chunks_by_key_terms(
                terms=keywords,
                document_id=document_id,
                limit=self.strategy.limits.max_chunks // 2,
                return_query=True,
            )
            
            if cypher_info:
                queries.append(CypherQuery(
                    description=f"Match key terms: {', '.join(keywords[:3])}",
                    query=cypher_info.get("query", ""),
                    params=cypher_info.get("params", {}),
                    result_count=len(matches),
                    execution_time_ms=cypher_info.get("execution_time_ms", 0),
                ))
            
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
        
        return results, queries
    
    async def _retrieve_via_temporal(
        self,
        query_analysis: dict[str, Any],
        document_id: Optional[str],
    ) -> tuple[list[RetrievalResult], list[CypherQuery]]:
        """Retrieve chunks with temporal references."""
        results = []
        queries = []
        
        try:
            chunks, cypher_info = await self.graph_repo.get_chunks_with_temporal_refs(
                document_id=document_id,
                return_query=True,
            )
            
            if cypher_info:
                queries.append(CypherQuery(
                    description="Get chunks with temporal references",
                    query=cypher_info.get("query", ""),
                    params=cypher_info.get("params", {}),
                    result_count=len(chunks),
                    execution_time_ms=cypher_info.get("execution_time_ms", 0),
                ))
            
            for chunk in chunks:
                results.append(RetrievalResult(
                    source="temporal",
                    item=chunk,
                    score=self.strategy.scoring.text_match_weight * 0.9,
                    item_type="chunk",
                ))
        except Exception as e:
            logger.debug(f"Temporal search failed: {e}")
        
        return results, queries
    
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
