"""
Schema-agnostic graph repository.

This repository works with ANY schema - it dynamically creates
nodes and relationships based on the schema definition.
"""

import logging
from typing import Any, Optional

from app.core.neo4j_client import Neo4jClient, get_neo4j_client
from app.schema.loader import SchemaLoader, get_schema_loader
from app.schema.models import (
    Schema,
    DynamicEntity,
    DynamicRelationship,
    DynamicGraph,
)

logger = logging.getLogger(__name__)


class DynamicGraphRepository:
    """
    Schema-agnostic graph repository.
    
    This repository dynamically handles any entity and relationship types
    defined in the loaded schema. It creates Neo4j nodes and relationships
    based on the schema definition, not hardcoded classes.
    
    Usage:
        repo = DynamicGraphRepository()
        await repo.initialize()
        
        # Store extracted graph
        await repo.store_graph(dynamic_graph)
        
        # Query entities
        entities = await repo.get_entities_by_type("Author")
    """
    
    def __init__(
        self,
        client: Optional[Neo4jClient] = None,
        schema_loader: Optional[SchemaLoader] = None,
    ):
        self.client = client or get_neo4j_client()
        self.schema_loader = schema_loader or get_schema_loader()
        self.schema: Optional[Schema] = None
    
    async def initialize(self, schema_name: Optional[str] = None) -> None:
        """Initialize repository with schema."""
        await self.client.connect()
        
        # Load schema
        if schema_name:
            self.schema = self.schema_loader.load_schema(schema_name)
        else:
            self.schema = self.schema_loader.get_active_schema()
        
        # Create indexes for all entity types
        await self._create_indexes()
    
    async def _create_indexes(self) -> None:
        """Create indexes for all entity types in schema."""
        for entity in self.schema.entities:
            # Index on id
            index_query = f"CREATE INDEX {entity.name.lower()}_id IF NOT EXISTS FOR (n:{entity.name}) ON (n.id)"
            try:
                await self.client.execute_write(index_query)
            except Exception as e:
                logger.debug(f"Index creation note: {e}")
            
            # Index on common searchable properties
            for prop in entity.properties:
                if prop.name in ["name", "title"]:
                    prop_index = f"CREATE INDEX {entity.name.lower()}_{prop.name} IF NOT EXISTS FOR (n:{entity.name}) ON (n.{prop.name})"
                    try:
                        await self.client.execute_write(prop_index)
                    except Exception:
                        pass
    
    async def store_graph(self, graph: DynamicGraph) -> dict[str, int]:
        """
        Store a complete dynamic graph in Neo4j.
        
        Args:
            graph: DynamicGraph with entities and relationships
            
        Returns:
            Summary of created items
        """
        counts = {"entities": 0, "relationships": 0}
        
        # Store all entities
        for entity_type, entities in graph.entities.items():
            for entity in entities:
                await self.create_entity(entity)
                counts["entities"] += 1
        
        # Store all relationships
        for rel in graph.relationships:
            await self.create_relationship(rel)
            counts["relationships"] += 1
        
        logger.info(f"Stored graph: {counts}")
        return counts
    
    async def create_entity(self, entity: DynamicEntity) -> None:
        """Create an entity node in Neo4j."""
        # Build properties
        props = entity.to_neo4j_properties()
        
        # Build property set clause
        prop_sets = [f"n.{key} = ${key}" for key in props.keys()]
        set_clause = ", ".join(prop_sets)
        
        query = f"""
        MERGE (n:{entity.entity_type} {{id: $id}})
        SET {set_clause}
        """
        
        await self.client.execute_write(query, props)
    
    async def create_relationship(self, rel: DynamicRelationship) -> None:
        """Create a relationship in Neo4j."""
        # Dynamic relationship type requires string interpolation (careful with injection!)
        # The relationship type comes from our validated schema, so it's safe
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
    
    async def get_entities_by_type(
        self,
        entity_type: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get all entities of a specific type."""
        query = f"""
        MATCH (n:{entity_type})
        RETURN n
        LIMIT $limit
        """
        results = await self.client.execute_query(query, {"limit": limit})
        return [dict(r["n"]) for r in results]
    
    async def get_entity_by_id(
        self,
        entity_id: str,
    ) -> Optional[dict[str, Any]]:
        """Get an entity by ID."""
        query = """
        MATCH (n {id: $id})
        RETURN n, labels(n)[0] as type
        """
        results = await self.client.execute_query(query, {"id": entity_id})
        if results:
            entity = dict(results[0]["n"])
            entity["_type"] = results[0]["type"]
            return entity
        return None
    
    async def search_entities(
        self,
        entity_type: str,
        search_property: str,
        search_value: str,
    ) -> list[dict[str, Any]]:
        """Search entities by property value."""
        query = f"""
        MATCH (n:{entity_type})
        WHERE toLower(toString(n.{search_property})) CONTAINS toLower($value)
        RETURN n
        LIMIT 50
        """
        results = await self.client.execute_query(query, {"value": search_value})
        return [dict(r["n"]) for r in results]
    
    async def get_entity_relationships(
        self,
        entity_id: str,
    ) -> dict[str, Any]:
        """Get an entity with all its relationships."""
        query = """
        MATCH (n {id: $id})
        OPTIONAL MATCH (n)-[r]->(related)
        OPTIONAL MATCH (n)<-[r2]-(incoming)
        RETURN n,
               collect(DISTINCT {
                   direction: 'outgoing',
                   type: type(r),
                   target: related
               }) as outgoing,
               collect(DISTINCT {
                   direction: 'incoming',
                   type: type(r2),
                   source: incoming
               }) as incoming
        """
        results = await self.client.execute_query(query, {"id": entity_id})
        
        if not results:
            return {}
        
        result = results[0]
        return {
            "entity": dict(result["n"]) if result["n"] else None,
            "outgoing": [r for r in result["outgoing"] if r.get("target")],
            "incoming": [r for r in result["incoming"] if r.get("source")],
        }
    
    async def get_graph_for_document(
        self,
        source_document: str,
    ) -> dict[str, Any]:
        """Get all entities from a specific document."""
        query = """
        MATCH (n)
        WHERE n.source_document = $doc OR n.source_file = $doc
        OPTIONAL MATCH (n)-[r]-(related)
        RETURN collect(DISTINCT n) as entities,
               collect(DISTINCT {
                   source: startNode(r).id,
                   target: endNode(r).id,
                   type: type(r)
               }) as relationships
        """
        results = await self.client.execute_query(query, {"doc": source_document})
        
        if not results:
            return {"entities": [], "relationships": []}
        
        result = results[0]
        return {
            "entities": [dict(e) for e in result["entities"]],
            "relationships": [r for r in result["relationships"] if r.get("source")],
        }
    
    async def get_visualization_data(
        self,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Get graph data for visualization."""
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
    
    async def get_stats(self) -> dict[str, Any]:
        """Get graph statistics."""
        query = """
        MATCH (n)
        RETURN labels(n)[0] as label, count(*) as count
        """
        results = await self.client.execute_query(query)
        
        stats = {r["label"]: r["count"] for r in results if r["label"]}
        
        # Get relationship count
        rel_query = "MATCH ()-[r]->() RETURN count(r) as count"
        rel_results = await self.client.execute_query(rel_query)
        stats["_relationships"] = rel_results[0]["count"] if rel_results else 0
        
        return stats
    
    async def delete_document_graph(self, source_document: str) -> dict[str, int]:
        """Delete all entities from a specific document."""
        query = """
        MATCH (n)
        WHERE n.source_document = $doc OR n.source_file = $doc
        DETACH DELETE n
        RETURN count(n) as deleted
        """
        results = await self.client.execute_query(query, {"doc": source_document})
        return {"deleted": results[0]["deleted"] if results else 0}
    
    async def clear_all(self) -> dict[str, Any]:
        """Clear the entire graph."""
        return await self.client.clear_database()
    
    async def get_schema_stats(self) -> dict[str, Any]:
        """Get statistics aligned with the current schema."""
        stats = await self.get_stats()
        
        # Organize by schema entity types
        schema_stats = {
            "schema": self.schema.schema_info.name,
            "entities": {},
            "total_nodes": 0,
            "total_relationships": stats.get("_relationships", 0),
        }
        
        for entity_def in self.schema.entities:
            count = stats.get(entity_def.name, 0)
            schema_stats["entities"][entity_def.name] = {
                "count": count,
                "color": entity_def.color,
                "description": entity_def.description,
            }
            schema_stats["total_nodes"] += count
        
        return schema_stats
