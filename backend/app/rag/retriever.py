"""
Graph-based retrieval for RAG.

Retrieves relevant context from the knowledge graph
based on user queries.
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional

from app.core.neo4j_client import Neo4jClient, get_neo4j_client
from app.core.llm import LLMClient, get_llm_client
from app.extraction.prompts import QUERY_DECOMPOSITION_PROMPT

logger = logging.getLogger(__name__)


@dataclass
class RetrievalContext:
    """Context retrieved from the knowledge graph."""
    
    entities: list[dict[str, Any]]
    relationships: list[dict[str, Any]]
    raw_text: str  # Formatted text for LLM
    query_plan: Optional[str] = None
    confidence: float = 1.0
    
    @property
    def entity_count(self) -> int:
        return len(self.entities)
    
    @property
    def is_empty(self) -> bool:
        return len(self.entities) == 0


class GraphRetriever:
    """
    Retrieves relevant context from the knowledge graph.
    
    Strategies:
    1. Query decomposition - understand user intent
    2. Entity matching - find relevant nodes
    3. Graph traversal - expand context via relationships
    4. Context formatting - prepare for LLM
    
    Usage:
        retriever = GraphRetriever()
        context = await retriever.retrieve("What are the termination clauses?")
        print(context.raw_text)
    """
    
    def __init__(
        self,
        neo4j_client: Optional[Neo4jClient] = None,
        llm_client: Optional[LLMClient] = None,
        max_entities: int = 20,
        max_depth: int = 2,
    ):
        self.neo4j = neo4j_client or get_neo4j_client()
        self.llm = llm_client or get_llm_client()
        self.max_entities = max_entities
        self.max_depth = max_depth
    
    async def retrieve(
        self,
        query: str,
        contract_id: Optional[str] = None,
    ) -> RetrievalContext:
        """
        Retrieve relevant context for a query.
        
        Args:
            query: User's natural language query
            contract_id: Optional contract ID to scope search
            
        Returns:
            RetrievalContext with entities and formatted text
        """
        # Step 1: Decompose query to understand intent
        query_analysis = await self._analyze_query(query)
        
        # Step 2: Build and execute retrieval queries
        entities, relationships = await self._execute_retrieval(
            query_analysis, contract_id
        )
        
        # Step 3: Format context for LLM
        raw_text = self._format_context(entities, relationships, query)
        
        return RetrievalContext(
            entities=entities,
            relationships=relationships,
            raw_text=raw_text,
            query_plan=query_analysis.get("cypher_hints"),
        )
    
    async def _analyze_query(self, query: str) -> dict[str, Any]:
        """Analyze query to determine retrieval strategy."""
        try:
            prompt = QUERY_DECOMPOSITION_PROMPT.format(query=query)
            response = await self.llm.complete(prompt)
            
            # Parse JSON response
            import json
            # Clean response
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            cleaned = cleaned.strip()
            
            return json.loads(cleaned)
        except Exception as e:
            logger.warning(f"Query analysis failed: {e}")
            # Return default analysis
            return {
                "intent": "general",
                "entity_types": ["Contract", "Clause", "Party"],
                "relationship_types": [],
                "filters": {},
            }
    
    async def _execute_retrieval(
        self,
        query_analysis: dict[str, Any],
        contract_id: Optional[str],
    ) -> tuple[list[dict], list[dict]]:
        """Execute retrieval queries based on analysis."""
        entities = []
        relationships = []
        
        entity_types = query_analysis.get("entity_types", [])
        filters = query_analysis.get("filters", {})
        
        # If contract_id specified, start from that contract
        if contract_id:
            contract_context = await self._get_contract_context(contract_id)
            entities.extend(contract_context.get("entities", []))
            relationships.extend(contract_context.get("relationships", []))
        else:
            # Search based on entity types and filters
            for entity_type in entity_types:
                type_entities = await self._search_entity_type(
                    entity_type, filters
                )
                entities.extend(type_entities)
        
        # Expand context via relationships
        if entities and self.max_depth > 0:
            expanded = await self._expand_context(
                [e.get("id") for e in entities if e.get("id")]
            )
            entities.extend(expanded.get("entities", []))
            relationships.extend(expanded.get("relationships", []))
        
        # Deduplicate
        seen_ids = set()
        unique_entities = []
        for e in entities:
            eid = e.get("id")
            if eid and eid not in seen_ids:
                seen_ids.add(eid)
                unique_entities.append(e)
        
        return unique_entities[:self.max_entities], relationships
    
    async def _get_contract_context(
        self, contract_id: str
    ) -> dict[str, Any]:
        """Get full context for a specific contract."""
        query = """
        MATCH (c:Contract {id: $id})
        OPTIONAL MATCH (c)-[r1]->(related)
        OPTIONAL MATCH (related)-[r2]->(nested)
        RETURN c, 
               collect(DISTINCT related) as related_entities,
               collect(DISTINCT {
                   source: startNode(r1).id,
                   target: endNode(r1).id,
                   type: type(r1)
               }) as relationships
        """
        await self.neo4j.connect()
        results = await self.neo4j.execute_query(query, {"id": contract_id})
        
        if not results:
            return {"entities": [], "relationships": []}
        
        result = results[0]
        entities = [dict(result["c"])] if result["c"] else []
        entities.extend([dict(e) for e in result.get("related_entities", []) if e])
        
        return {
            "entities": entities,
            "relationships": result.get("relationships", []),
        }
    
    async def _search_entity_type(
        self,
        entity_type: str,
        filters: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Search for entities of a specific type."""
        # Build query based on type
        label = entity_type
        
        # Start with base query
        if filters:
            where_parts = []
            params = {"limit": self.max_entities}
            
            for key, value in filters.items():
                param_name = f"filter_{key}"
                where_parts.append(f"toLower(n.{key}) CONTAINS toLower(${param_name})")
                params[param_name] = value
            
            where_clause = " AND ".join(where_parts)
            query = f"""
            MATCH (n:{label})
            WHERE {where_clause}
            RETURN n
            LIMIT $limit
            """
        else:
            query = f"""
            MATCH (n:{label})
            RETURN n
            LIMIT $limit
            """
            params = {"limit": self.max_entities}
        
        await self.neo4j.connect()
        results = await self.neo4j.execute_query(query, params)
        return [dict(r["n"]) for r in results]
    
    async def _expand_context(
        self, entity_ids: list[str]
    ) -> dict[str, Any]:
        """Expand context by following relationships."""
        if not entity_ids:
            return {"entities": [], "relationships": []}
        
        query = """
        MATCH (n)
        WHERE n.id IN $ids
        OPTIONAL MATCH (n)-[r]-(related)
        RETURN collect(DISTINCT related) as entities,
               collect(DISTINCT {
                   source: startNode(r).id,
                   target: endNode(r).id,
                   type: type(r)
               }) as relationships
        """
        await self.neo4j.connect()
        results = await self.neo4j.execute_query(query, {"ids": entity_ids})
        
        if not results:
            return {"entities": [], "relationships": []}
        
        result = results[0]
        return {
            "entities": [dict(e) for e in result.get("entities", []) if e],
            "relationships": [r for r in result.get("relationships", []) if r.get("source")],
        }
    
    def _format_context(
        self,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
        original_query: str,
    ) -> str:
        """Format retrieved context as text for LLM."""
        parts = [f"# Retrieved Context for Query: {original_query}\n"]
        
        # Group entities by type
        entities_by_type: dict[str, list] = {}
        for entity in entities:
            entity_type = entity.get("_label", entity.get("type", "Unknown"))
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity)
        
        # Format each entity type
        for entity_type, type_entities in entities_by_type.items():
            parts.append(f"\n## {entity_type}s\n")
            
            for entity in type_entities:
                parts.append(self._format_entity(entity, entity_type))
        
        # Format relationships
        if relationships:
            parts.append("\n## Relationships\n")
            for rel in relationships:
                if rel.get("source") and rel.get("target"):
                    parts.append(
                        f"- {rel['source']} --[{rel.get('type', 'RELATED')}]--> {rel['target']}"
                    )
        
        return "\n".join(parts)
    
    def _format_entity(
        self, entity: dict[str, Any], entity_type: str
    ) -> str:
        """Format a single entity as text."""
        # Key fields to highlight based on type
        key_fields = {
            "Contract": ["title", "contract_type", "effective_date", "summary"],
            "Party": ["name", "type", "role"],
            "Clause": ["clause_type", "title", "summary", "text"],
            "Obligation": ["obligation_type", "description", "conditions"],
            "ContractDate": ["date_type", "value", "description"],
            "Amount": ["value", "currency", "description"],
        }
        
        fields = key_fields.get(entity_type, list(entity.keys()))
        
        lines = [f"### {entity.get('name', entity.get('title', entity.get('id', 'Entity')))}"]
        
        for field in fields:
            if field in entity and entity[field]:
                value = entity[field]
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                lines.append(f"- **{field}**: {value}")
        
        return "\n".join(lines) + "\n"
    
    async def retrieve_by_keywords(
        self,
        keywords: list[str],
        entity_types: Optional[list[str]] = None,
    ) -> RetrievalContext:
        """
        Retrieve context using keyword search.
        
        Simpler alternative to full query decomposition.
        """
        types = entity_types or ["Contract", "Clause", "Party", "Obligation"]
        
        entities = []
        for keyword in keywords:
            for entity_type in types:
                query = f"""
                MATCH (n:{entity_type})
                WHERE any(prop in keys(n) WHERE 
                    n[prop] IS NOT NULL AND 
                    toString(n[prop]) CONTAINS $keyword
                )
                RETURN n
                LIMIT 10
                """
                await self.neo4j.connect()
                results = await self.neo4j.execute_query(
                    query, {"keyword": keyword.lower()}
                )
                entities.extend([dict(r["n"]) for r in results])
        
        # Deduplicate
        seen = set()
        unique = []
        for e in entities:
            eid = e.get("id")
            if eid and eid not in seen:
                seen.add(eid)
                unique.append(e)
        
        raw_text = self._format_context(unique, [], f"Keywords: {', '.join(keywords)}")
        
        return RetrievalContext(
            entities=unique,
            relationships=[],
            raw_text=raw_text,
        )
