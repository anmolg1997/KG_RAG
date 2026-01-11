"""
Cypher query builders for complex graph queries.

Provides a fluent interface for building Cypher queries
based on user questions and search parameters.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class QueryIntent(str, Enum):
    """Types of query intents."""
    FIND_ENTITY = "find_entity"
    FIND_RELATIONSHIP = "find_relationship"
    AGGREGATE = "aggregate"
    COMPARE = "compare"
    TRAVERSE = "traverse"


@dataclass
class QueryPlan:
    """A planned query with parameters."""
    
    cypher: str
    parameters: dict[str, Any] = field(default_factory=dict)
    intent: QueryIntent = QueryIntent.FIND_ENTITY
    description: str = ""


class QueryBuilder:
    """
    Fluent Cypher query builder.
    
    Usage:
        builder = QueryBuilder()
        query = (builder
            .match("Contract", "c")
            .where("c.title", "contains", "License")
            .with_related("Party", "HAS_PARTY", "p")
            .return_all()
            .build())
    """
    
    def __init__(self):
        self._match_clauses: list[str] = []
        self._where_clauses: list[str] = []
        self._with_clauses: list[str] = []
        self._return_clause: str = ""
        self._order_clause: str = ""
        self._limit: Optional[int] = None
        self._parameters: dict[str, Any] = {}
        self._param_counter: int = 0
    
    def _next_param(self) -> str:
        """Generate next parameter name."""
        self._param_counter += 1
        return f"p{self._param_counter}"
    
    def match(
        self,
        label: str,
        alias: str,
        properties: Optional[dict[str, Any]] = None,
    ) -> "QueryBuilder":
        """Add a MATCH clause for a node."""
        if properties:
            props_parts = []
            for key, value in properties.items():
                param = self._next_param()
                props_parts.append(f"{key}: ${param}")
                self._parameters[param] = value
            props_str = "{" + ", ".join(props_parts) + "}"
            self._match_clauses.append(f"({alias}:{label} {props_str})")
        else:
            self._match_clauses.append(f"({alias}:{label})")
        return self
    
    def match_any(self, alias: str) -> "QueryBuilder":
        """Match any node."""
        self._match_clauses.append(f"({alias})")
        return self
    
    def with_related(
        self,
        target_label: str,
        relationship_type: str,
        target_alias: str,
        source_alias: Optional[str] = None,
        direction: str = "outgoing",
    ) -> "QueryBuilder":
        """Add a relationship pattern to the match."""
        source = source_alias or self._get_last_alias()
        
        if direction == "outgoing":
            pattern = f"({source})-[:{relationship_type}]->({target_alias}:{target_label})"
        elif direction == "incoming":
            pattern = f"({source})<-[:{relationship_type}]-({target_alias}:{target_label})"
        else:
            pattern = f"({source})-[:{relationship_type}]-({target_alias}:{target_label})"
        
        self._match_clauses.append(pattern)
        return self
    
    def optional_match(
        self,
        label: str,
        alias: str,
        relationship_type: str,
        source_alias: str,
    ) -> "QueryBuilder":
        """Add an OPTIONAL MATCH clause."""
        pattern = f"OPTIONAL MATCH ({source_alias})-[:{relationship_type}]->({alias}:{label})"
        self._match_clauses.append(pattern)
        return self
    
    def where(
        self,
        field: str,
        operator: str,
        value: Any,
    ) -> "QueryBuilder":
        """Add a WHERE condition."""
        param = self._next_param()
        self._parameters[param] = value
        
        if operator == "equals":
            self._where_clauses.append(f"{field} = ${param}")
        elif operator == "contains":
            self._where_clauses.append(f"toLower({field}) CONTAINS toLower(${param})")
        elif operator == "starts_with":
            self._where_clauses.append(f"{field} STARTS WITH ${param}")
        elif operator == "in":
            self._where_clauses.append(f"{field} IN ${param}")
        elif operator == "gt":
            self._where_clauses.append(f"{field} > ${param}")
        elif operator == "lt":
            self._where_clauses.append(f"{field} < ${param}")
        elif operator == "gte":
            self._where_clauses.append(f"{field} >= ${param}")
        elif operator == "lte":
            self._where_clauses.append(f"{field} <= ${param}")
        else:
            self._where_clauses.append(f"{field} {operator} ${param}")
        
        return self
    
    def where_raw(self, condition: str) -> "QueryBuilder":
        """Add a raw WHERE condition."""
        self._where_clauses.append(condition)
        return self
    
    def return_fields(self, *fields: str) -> "QueryBuilder":
        """Specify fields to return."""
        self._return_clause = f"RETURN {', '.join(fields)}"
        return self
    
    def return_all(self) -> "QueryBuilder":
        """Return all matched patterns."""
        aliases = self._extract_aliases()
        self._return_clause = f"RETURN {', '.join(aliases)}"
        return self
    
    def return_count(self, alias: str, as_name: str = "count") -> "QueryBuilder":
        """Return count of matches."""
        self._return_clause = f"RETURN count({alias}) as {as_name}"
        return self
    
    def return_distinct(self, *fields: str) -> "QueryBuilder":
        """Return distinct values."""
        self._return_clause = f"RETURN DISTINCT {', '.join(fields)}"
        return self
    
    def collect(self, alias: str, as_name: str) -> "QueryBuilder":
        """Add a collect aggregation."""
        self._with_clauses.append(f"collect({alias}) as {as_name}")
        return self
    
    def order_by(self, field: str, direction: str = "ASC") -> "QueryBuilder":
        """Add ORDER BY clause."""
        self._order_clause = f"ORDER BY {field} {direction}"
        return self
    
    def limit(self, count: int) -> "QueryBuilder":
        """Add LIMIT clause."""
        self._limit = count
        return self
    
    def build(self) -> QueryPlan:
        """Build the final Cypher query."""
        parts = []
        
        # MATCH clauses
        if self._match_clauses:
            # Combine match clauses intelligently
            match_str = "MATCH " + ", ".join(
                c for c in self._match_clauses if not c.startswith("OPTIONAL")
            )
            parts.append(match_str)
            
            # Add optional matches separately
            for clause in self._match_clauses:
                if clause.startswith("OPTIONAL"):
                    parts.append(clause)
        
        # WHERE clauses
        if self._where_clauses:
            parts.append("WHERE " + " AND ".join(self._where_clauses))
        
        # WITH clauses (for aggregations)
        if self._with_clauses:
            aliases = self._extract_aliases()
            with_parts = aliases + self._with_clauses
            parts.append("WITH " + ", ".join(with_parts))
        
        # RETURN clause
        if self._return_clause:
            parts.append(self._return_clause)
        
        # ORDER BY
        if self._order_clause:
            parts.append(self._order_clause)
        
        # LIMIT
        if self._limit is not None:
            parts.append(f"LIMIT {self._limit}")
        
        cypher = "\n".join(parts)
        
        return QueryPlan(
            cypher=cypher,
            parameters=self._parameters,
        )
    
    def _get_last_alias(self) -> str:
        """Get the alias from the last match clause."""
        if not self._match_clauses:
            return "n"
        last = self._match_clauses[-1]
        # Extract alias from pattern like (alias:Label)
        import re
        match = re.search(r'\((\w+)(?::\w+)?', last)
        return match.group(1) if match else "n"
    
    def _extract_aliases(self) -> list[str]:
        """Extract all aliases from match clauses."""
        import re
        aliases = []
        for clause in self._match_clauses:
            if clause.startswith("OPTIONAL"):
                clause = clause.replace("OPTIONAL MATCH ", "")
            matches = re.findall(r'\((\w+)(?::\w+)?', clause)
            aliases.extend(matches)
        return list(dict.fromkeys(aliases))  # Unique, preserve order
    
    def reset(self) -> "QueryBuilder":
        """Reset the builder for reuse."""
        self._match_clauses = []
        self._where_clauses = []
        self._with_clauses = []
        self._return_clause = ""
        self._order_clause = ""
        self._limit = None
        self._parameters = {}
        self._param_counter = 0
        return self


# =============================================================================
# Schema-Agnostic Query Templates
# =============================================================================

class QueryTemplates:
    """
    Schema-agnostic query templates for common graph operations.
    
    These templates work with any schema by accepting entity types
    and relationship types as parameters.
    """
    
    @staticmethod
    def find_entities_by_relationship(
        source_label: str,
        source_property: str,
        source_value: str,
        target_label: str,
        relationship_type: str,
        direction: str = "incoming",
    ) -> QueryPlan:
        """Find entities connected via a relationship."""
        builder = QueryBuilder()
        builder.match(source_label, "source", {source_property: source_value})
        builder.with_related(target_label, relationship_type, "target", "source", direction)
        builder.return_fields("source", "target")
        return builder.build()
    
    @staticmethod
    def find_entities_by_property(
        label: str,
        property_name: str,
        property_value: str,
        operator: str = "equals",
    ) -> QueryPlan:
        """Find all entities matching a property condition."""
        return (QueryBuilder()
            .match(label, "n")
            .where(f"n.{property_name}", operator, property_value)
            .return_fields("n")
            .build())
    
    @staticmethod
    def find_related_entities(
        label: str,
        property_name: str,
        property_value: str,
        relationship_type: str,
        related_label: str,
        direction: str = "outgoing",
    ) -> QueryPlan:
        """Find entities and their related entities."""
        return (QueryBuilder()
            .match(label, "source")
            .where(f"source.{property_name}", "contains", property_value)
            .with_related(related_label, relationship_type, "related", "source", direction)
            .return_fields("source", "related")
            .build())
    
    @staticmethod
    def document_summary(document_id: str) -> QueryPlan:
        """Get full document summary with all related entities (schema-agnostic)."""
        cypher = """
        MATCH (d:Document {id: $document_id})
        OPTIONAL MATCH (d)<-[:FROM_DOCUMENT]-(c:Chunk)
        OPTIONAL MATCH (c)<-[:EXTRACTED_FROM]-(e)
        WHERE NOT e:Chunk AND NOT e:Document
        WITH d, collect(DISTINCT c) as chunks, collect(DISTINCT e) as entities
        RETURN d as document,
               size(chunks) as chunk_count,
               size(entities) as entity_count,
               entities
        """
        return QueryPlan(
            cypher=cypher,
            parameters={"document_id": document_id},
            intent=QueryIntent.TRAVERSE,
            description="Full document summary",
        )
    
    @staticmethod
    def entities_from_chunk(chunk_id: str) -> QueryPlan:
        """Get all entities extracted from a specific chunk."""
        cypher = """
        MATCH (c:Chunk {chunk_id: $chunk_id})
        OPTIONAL MATCH (c)<-[:EXTRACTED_FROM]-(e)
        WHERE NOT e:Chunk AND NOT e:Document
        RETURN c as chunk, collect(e) as entities
        """
        return QueryPlan(
            cypher=cypher,
            parameters={"chunk_id": chunk_id},
            intent=QueryIntent.TRAVERSE,
            description="Entities from chunk",
        )
    
    @staticmethod
    def entity_neighborhood(
        label: str,
        entity_id: str,
        depth: int = 1,
    ) -> QueryPlan:
        """Get entity and its neighborhood up to specified depth."""
        cypher = f"""
        MATCH (n:{label} {{id: $entity_id}})
        CALL apoc.path.subgraphAll(n, {{
            maxLevel: {depth},
            relationshipFilter: null,
            labelFilter: '-Chunk|-Document'
        }})
        YIELD nodes, relationships
        RETURN nodes, relationships
        """
        return QueryPlan(
            cypher=cypher,
            parameters={"entity_id": entity_id},
            intent=QueryIntent.TRAVERSE,
            description=f"Entity neighborhood (depth {depth})",
        )
    
    @staticmethod
    def graph_statistics() -> QueryPlan:
        """Get graph statistics."""
        cypher = """
        CALL {
            MATCH (n) RETURN labels(n)[0] as label, count(*) as count
        }
        RETURN label, count
        ORDER BY count DESC
        """
        return QueryPlan(
            cypher=cypher,
            parameters={},
            intent=QueryIntent.AGGREGATE,
            description="Graph statistics",
        )
    
    @staticmethod
    def search_entities_fulltext(
        search_term: str,
        labels: Optional[list[str]] = None,
        limit: int = 20,
    ) -> QueryPlan:
        """Search entities across all properties."""
        if labels:
            label_filter = ":" + "|".join(labels)
        else:
            label_filter = ""
        
        cypher = f"""
        MATCH (n{label_filter})
        WHERE any(key in keys(n) WHERE 
            toString(n[key]) CONTAINS $search_term
        )
        RETURN n, labels(n)[0] as type
        LIMIT $limit
        """
        return QueryPlan(
            cypher=cypher,
            parameters={"search_term": search_term, "limit": limit},
            intent=QueryIntent.FIND_ENTITY,
            description="Fulltext entity search",
        )