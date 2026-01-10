"""
Neo4j graph repository for knowledge graph operations.

Handles:
- Storing extracted entities and relationships
- Querying the knowledge graph
- Graph maintenance operations
"""

import logging
from typing import Any, Optional

from app.core.neo4j_client import Neo4jClient, get_neo4j_client
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

logger = logging.getLogger(__name__)


class GraphRepository:
    """
    Repository for Neo4j graph operations.
    
    Provides CRUD operations for all entity types and
    methods for storing complete extraction results.
    
    Usage:
        repo = GraphRepository()
        await repo.initialize()
        
        # Store extracted graph
        await repo.store_extracted_graph(extracted_graph)
        
        # Query
        contracts = await repo.get_all_contracts()
    """
    
    def __init__(self, client: Optional[Neo4jClient] = None):
        self.client = client or get_neo4j_client()
    
    async def initialize(self) -> None:
        """Initialize the repository and create indexes."""
        await self.client.connect()
        await self._create_indexes()
    
    async def _create_indexes(self) -> None:
        """Create indexes for common query patterns."""
        indexes = [
            "CREATE INDEX contract_id IF NOT EXISTS FOR (c:Contract) ON (c.id)",
            "CREATE INDEX party_id IF NOT EXISTS FOR (p:Party) ON (p.id)",
            "CREATE INDEX party_name IF NOT EXISTS FOR (p:Party) ON (p.name)",
            "CREATE INDEX clause_id IF NOT EXISTS FOR (c:Clause) ON (c.id)",
            "CREATE INDEX clause_type IF NOT EXISTS FOR (c:Clause) ON (c.clause_type)",
            "CREATE INDEX obligation_id IF NOT EXISTS FOR (o:Obligation) ON (o.id)",
            "CREATE INDEX date_id IF NOT EXISTS FOR (d:ContractDate) ON (d.id)",
            "CREATE INDEX amount_id IF NOT EXISTS FOR (a:Amount) ON (a.id)",
        ]
        
        for index_query in indexes:
            try:
                await self.client.execute_write(index_query)
            except Exception as e:
                logger.debug(f"Index creation note: {e}")
    
    async def store_extracted_graph(self, graph: ExtractedGraph) -> dict[str, int]:
        """
        Store a complete extracted graph in Neo4j.
        
        Args:
            graph: ExtractedGraph with all entities and relationships
            
        Returns:
            Summary of created items
        """
        counts = {
            "contracts": 0,
            "parties": 0,
            "clauses": 0,
            "obligations": 0,
            "dates": 0,
            "amounts": 0,
            "relationships": 0,
        }
        
        # Store entities
        for contract in graph.contracts:
            await self.create_contract(contract)
            counts["contracts"] += 1
        
        for party in graph.parties:
            await self.create_party(party)
            counts["parties"] += 1
        
        for clause in graph.clauses:
            await self.create_clause(clause)
            counts["clauses"] += 1
        
        for obligation in graph.obligations:
            await self.create_obligation(obligation)
            counts["obligations"] += 1
        
        for date in graph.dates:
            await self.create_date(date)
            counts["dates"] += 1
        
        for amount in graph.amounts:
            await self.create_amount(amount)
            counts["amounts"] += 1
        
        # Store relationships
        for rel in graph.relationships:
            await self.create_relationship(rel)
            counts["relationships"] += 1
        
        logger.info(f"Stored graph: {counts}")
        return counts
    
    # =========================================================================
    # Entity Creation
    # =========================================================================
    
    async def create_contract(self, contract: Contract) -> None:
        """Create a Contract node."""
        query = """
        MERGE (c:Contract {id: $id})
        SET c.title = $title,
            c.contract_type = $contract_type,
            c.effective_date = $effective_date,
            c.expiration_date = $expiration_date,
            c.status = $status,
            c.summary = $summary,
            c.source_file = $source_file,
            c.confidence = $confidence
        """
        await self.client.execute_write(query, {
            "id": contract.id,
            "title": contract.title,
            "contract_type": contract.contract_type,
            "effective_date": str(contract.effective_date) if contract.effective_date else None,
            "expiration_date": str(contract.expiration_date) if contract.expiration_date else None,
            "status": contract.status,
            "summary": contract.summary,
            "source_file": contract.source_file,
            "confidence": contract.confidence,
        })
    
    async def create_party(self, party: Party) -> None:
        """Create a Party node."""
        query = """
        MERGE (p:Party {id: $id})
        SET p.name = $name,
            p.type = $type,
            p.role = $role,
            p.address = $address,
            p.jurisdiction = $jurisdiction,
            p.registration_number = $registration_number,
            p.confidence = $confidence
        """
        await self.client.execute_write(query, {
            "id": party.id,
            "name": party.name,
            "type": party.type.value,
            "role": party.role.value,
            "address": party.address,
            "jurisdiction": party.jurisdiction,
            "registration_number": party.registration_number,
            "confidence": party.confidence,
        })
    
    async def create_clause(self, clause: Clause) -> None:
        """Create a Clause node."""
        query = """
        MERGE (c:Clause {id: $id})
        SET c.clause_type = $clause_type,
            c.title = $title,
            c.section_number = $section_number,
            c.text = $text,
            c.summary = $summary,
            c.key_terms = $key_terms,
            c.confidence = $confidence
        """
        await self.client.execute_write(query, {
            "id": clause.id,
            "clause_type": clause.clause_type.value,
            "title": clause.title,
            "section_number": clause.section_number,
            "text": clause.text,
            "summary": clause.summary,
            "key_terms": clause.key_terms,
            "confidence": clause.confidence,
        })
    
    async def create_obligation(self, obligation: Obligation) -> None:
        """Create an Obligation node."""
        query = """
        MERGE (o:Obligation {id: $id})
        SET o.obligation_type = $obligation_type,
            o.description = $description,
            o.status = $status,
            o.conditions = $conditions,
            o.trigger_event = $trigger_event,
            o.breach_consequences = $breach_consequences,
            o.confidence = $confidence
        """
        await self.client.execute_write(query, {
            "id": obligation.id,
            "obligation_type": obligation.obligation_type.value,
            "description": obligation.description,
            "status": obligation.status.value,
            "conditions": obligation.conditions,
            "trigger_event": obligation.trigger_event,
            "breach_consequences": obligation.breach_consequences,
            "confidence": obligation.confidence,
        })
    
    async def create_date(self, date: ContractDate) -> None:
        """Create a ContractDate node."""
        query = """
        MERGE (d:ContractDate {id: $id})
        SET d.date_type = $date_type,
            d.value = $value,
            d.description = $description,
            d.is_relative = $is_relative,
            d.relative_to = $relative_to,
            d.confidence = $confidence
        """
        await self.client.execute_write(query, {
            "id": date.id,
            "date_type": date.date_type.value,
            "value": str(date.value) if date.value else None,
            "description": date.description,
            "is_relative": date.is_relative,
            "relative_to": date.relative_to,
            "confidence": date.confidence,
        })
    
    async def create_amount(self, amount: Amount) -> None:
        """Create an Amount node."""
        query = """
        MERGE (a:Amount {id: $id})
        SET a.value = $value,
            a.currency = $currency,
            a.description = $description,
            a.is_percentage = $is_percentage,
            a.is_variable = $is_variable,
            a.formula = $formula,
            a.confidence = $confidence
        """
        await self.client.execute_write(query, {
            "id": amount.id,
            "value": amount.value,
            "currency": amount.currency.value,
            "description": amount.description,
            "is_percentage": amount.is_percentage,
            "is_variable": amount.is_variable,
            "formula": amount.formula,
            "confidence": amount.confidence,
        })
    
    async def create_relationship(self, rel: Relationship) -> None:
        """Create a relationship between two nodes."""
        # Dynamic relationship type requires different approach
        query = f"""
        MATCH (source {{id: $source_id}})
        MATCH (target {{id: $target_id}})
        MERGE (source)-[r:{rel.relationship_type}]->(target)
        SET r.id = $rel_id,
            r.confidence = $confidence
        """
        await self.client.execute_write(query, {
            "source_id": rel.source_id,
            "target_id": rel.target_id,
            "rel_id": rel.id,
            "confidence": rel.confidence,
        })
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    
    async def get_all_contracts(self) -> list[dict[str, Any]]:
        """Get all contracts."""
        query = "MATCH (c:Contract) RETURN c"
        results = await self.client.execute_query(query)
        return [r["c"] for r in results]
    
    async def get_contract_by_id(self, contract_id: str) -> Optional[dict[str, Any]]:
        """Get a contract by ID."""
        query = "MATCH (c:Contract {id: $id}) RETURN c"
        results = await self.client.execute_query(query, {"id": contract_id})
        return results[0]["c"] if results else None
    
    async def get_contract_with_parties(
        self, contract_id: str
    ) -> dict[str, Any]:
        """Get a contract with all its parties."""
        query = """
        MATCH (c:Contract {id: $id})
        OPTIONAL MATCH (c)-[:HAS_PARTY]->(p:Party)
        RETURN c, collect(p) as parties
        """
        results = await self.client.execute_query(query, {"id": contract_id})
        if results:
            return {
                "contract": results[0]["c"],
                "parties": results[0]["parties"],
            }
        return {}
    
    async def get_contract_full_graph(
        self, contract_id: str
    ) -> dict[str, Any]:
        """Get complete graph for a contract."""
        query = """
        MATCH (c:Contract {id: $id})
        OPTIONAL MATCH (c)-[:HAS_PARTY]->(p:Party)
        OPTIONAL MATCH (c)-[:HAS_CLAUSE]->(cl:Clause)
        OPTIONAL MATCH (cl)-[:CREATES_OBLIGATION]->(o:Obligation)
        OPTIONAL MATCH (c)-[:HAS_DATE]->(d:ContractDate)
        OPTIONAL MATCH (cl)-[:REFERENCES_AMOUNT]->(a:Amount)
        RETURN c,
               collect(DISTINCT p) as parties,
               collect(DISTINCT cl) as clauses,
               collect(DISTINCT o) as obligations,
               collect(DISTINCT d) as dates,
               collect(DISTINCT a) as amounts
        """
        results = await self.client.execute_query(query, {"id": contract_id})
        if results:
            return {
                "contract": results[0]["c"],
                "parties": results[0]["parties"],
                "clauses": results[0]["clauses"],
                "obligations": results[0]["obligations"],
                "dates": results[0]["dates"],
                "amounts": results[0]["amounts"],
            }
        return {}
    
    async def get_clauses_by_type(
        self, clause_type: str
    ) -> list[dict[str, Any]]:
        """Get all clauses of a specific type."""
        query = """
        MATCH (c:Clause {clause_type: $type})
        RETURN c
        """
        results = await self.client.execute_query(query, {"type": clause_type})
        return [r["c"] for r in results]
    
    async def get_party_obligations(
        self, party_id: str
    ) -> list[dict[str, Any]]:
        """Get all obligations for a party."""
        query = """
        MATCH (p:Party {id: $id})<-[:OBLIGATES]-(o:Obligation)
        RETURN o
        """
        results = await self.client.execute_query(query, {"id": party_id})
        return [r["o"] for r in results]
    
    async def search_parties_by_name(
        self, name_pattern: str
    ) -> list[dict[str, Any]]:
        """Search parties by name pattern."""
        query = """
        MATCH (p:Party)
        WHERE toLower(p.name) CONTAINS toLower($pattern)
        RETURN p
        """
        results = await self.client.execute_query(query, {"pattern": name_pattern})
        return [r["p"] for r in results]
    
    async def get_graph_stats(self) -> dict[str, int]:
        """Get statistics about the graph."""
        query = """
        MATCH (n)
        RETURN labels(n)[0] as label, count(*) as count
        """
        results = await self.client.execute_query(query)
        stats = {r["label"]: r["count"] for r in results}
        
        # Get relationship count
        rel_query = "MATCH ()-[r]->() RETURN count(r) as count"
        rel_results = await self.client.execute_query(rel_query)
        stats["relationships"] = rel_results[0]["count"] if rel_results else 0
        
        return stats
    
    async def get_graph_visualization_data(
        self, limit: int = 100
    ) -> dict[str, Any]:
        """
        Get graph data formatted for visualization.
        
        Returns nodes and edges in a format suitable for
        frontend graph visualization libraries.
        """
        # Get nodes
        nodes_query = """
        MATCH (n)
        RETURN n, labels(n)[0] as label
        LIMIT $limit
        """
        nodes_results = await self.client.execute_query(nodes_query, {"limit": limit})
        
        nodes = []
        for r in nodes_results:
            node = dict(r["n"])
            node["_label"] = r["label"]
            nodes.append(node)
        
        # Get relationships
        rels_query = """
        MATCH (a)-[r]->(b)
        RETURN a.id as source, b.id as target, type(r) as type
        LIMIT $limit
        """
        rels_results = await self.client.execute_query(rels_query, {"limit": limit * 2})
        
        edges = [
            {
                "source": r["source"],
                "target": r["target"],
                "type": r["type"],
            }
            for r in rels_results
        ]
        
        return {"nodes": nodes, "edges": edges}
    
    # =========================================================================
    # Maintenance
    # =========================================================================
    
    async def delete_contract_graph(self, contract_id: str) -> dict[str, int]:
        """Delete a contract and all its related entities."""
        query = """
        MATCH (c:Contract {id: $id})
        OPTIONAL MATCH (c)-[r1]->(related)
        OPTIONAL MATCH (related)-[r2]->()
        DETACH DELETE c, related
        RETURN count(c) as contracts_deleted
        """
        return await self.client.execute_write(query, {"id": contract_id})
    
    async def clear_all(self) -> dict[str, Any]:
        """Clear the entire graph. USE WITH CAUTION."""
        return await self.client.clear_database()
