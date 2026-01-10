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
# Pre-built Query Templates
# =============================================================================

class QueryTemplates:
    """Common query templates for contract analysis."""
    
    @staticmethod
    def find_contracts_by_party(party_name: str) -> QueryPlan:
        """Find all contracts involving a party."""
        return (QueryBuilder()
            .match("Party", "p", {"name": party_name})
            .with_related("Contract", "HAS_PARTY", "c", "p", "incoming")
            .return_fields("c", "p")
            .build())
    
    @staticmethod
    def find_clauses_by_type(clause_type: str) -> QueryPlan:
        """Find all clauses of a specific type."""
        return (QueryBuilder()
            .match("Clause", "c")
            .where("c.clause_type", "equals", clause_type)
            .return_fields("c")
            .build())
    
    @staticmethod
    def find_party_obligations(party_name: str) -> QueryPlan:
        """Find all obligations for a party."""
        return (QueryBuilder()
            .match("Party", "p")
            .where("p.name", "contains", party_name)
            .with_related("Obligation", "OBLIGATES", "o", "p", "incoming")
            .return_fields("p", "o")
            .build())
    
    @staticmethod
    def contract_summary(contract_id: str) -> QueryPlan:
        """Get full contract summary with all related entities."""
        builder = QueryBuilder()
        builder.match("Contract", "c", {"id": contract_id})
        
        # This is a complex query, build it manually
        cypher = """
        MATCH (c:Contract {id: $contract_id})
        OPTIONAL MATCH (c)-[:HAS_PARTY]->(p:Party)
        OPTIONAL MATCH (c)-[:HAS_CLAUSE]->(cl:Clause)
        OPTIONAL MATCH (c)-[:HAS_DATE]->(d:ContractDate)
        OPTIONAL MATCH (cl)-[:CREATES_OBLIGATION]->(o:Obligation)
        OPTIONAL MATCH (cl)-[:REFERENCES_AMOUNT]->(a:Amount)
        RETURN c,
               collect(DISTINCT p) as parties,
               collect(DISTINCT cl) as clauses,
               collect(DISTINCT d) as dates,
               collect(DISTINCT o) as obligations,
               collect(DISTINCT a) as amounts
        """
        return QueryPlan(
            cypher=cypher,
            parameters={"contract_id": contract_id},
            intent=QueryIntent.TRAVERSE,
            description="Full contract summary",
        )
    
    @staticmethod
    def find_termination_clauses() -> QueryPlan:
        """Find all termination-related clauses."""
        return (QueryBuilder()
            .match("Clause", "c")
            .where("c.clause_type", "equals", "termination")
            .with_related("Contract", "HAS_CLAUSE", "contract", "c", "incoming")
            .return_fields("c", "contract")
            .build())
    
    @staticmethod
    def payment_obligations() -> QueryPlan:
        """Find all payment obligations with amounts."""
        cypher = """
        MATCH (o:Obligation {obligation_type: 'payment'})
        OPTIONAL MATCH (o)<-[:CREATES_OBLIGATION]-(c:Clause)
        OPTIONAL MATCH (c)-[:REFERENCES_AMOUNT]->(a:Amount)
        OPTIONAL MATCH (o)-[:OBLIGATES]->(p:Party)
        RETURN o, c, a, p
        """
        return QueryPlan(
            cypher=cypher,
            parameters={},
            intent=QueryIntent.TRAVERSE,
            description="Payment obligations with amounts",
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
