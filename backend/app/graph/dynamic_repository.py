"""
Schema-agnostic graph repository.

This repository works with ANY schema - it dynamically creates
nodes and relationships based on the schema definition.

Now includes chunk node operations for enhanced retrieval.
"""

import logging
from typing import Any, Optional, TYPE_CHECKING

from app.core.neo4j_client import Neo4jClient, get_neo4j_client
from app.schema.loader import SchemaLoader, get_schema_loader
from app.schema.models import (
    Schema,
    DynamicEntity,
    DynamicRelationship,
    DynamicGraph,
)

if TYPE_CHECKING:
    from app.ingestion.chunker import TextChunk

logger = logging.getLogger(__name__)


class DynamicGraphRepository:
    """
    Schema-agnostic graph repository.
    
    This repository dynamically handles any entity and relationship types
    defined in the loaded schema. It creates Neo4j nodes and relationships
    based on the schema definition, not hardcoded classes.
    
    Now also supports:
    - Chunk nodes for storing text chunks
    - Document nodes for document-level information
    - Chunk-to-chunk sequential linking (NEXT_CHUNK, PREV_CHUNK)
    - Entity-to-chunk linking (EXTRACTED_FROM)
    
    Usage:
        repo = DynamicGraphRepository()
        await repo.initialize()
        
        # Store extracted graph
        await repo.store_graph(dynamic_graph)
        
        # Store chunks
        await repo.store_chunks(chunks, document_id)
        
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
        
        # Create indexes for all entity types and chunks
        await self._create_indexes()
    
    async def _create_indexes(self) -> None:
        """
        Create indexes for all entity types in schema and infrastructure nodes.
        
        Uses enterprise-level approach: checks existing indexes first,
        then only creates what's missing. No noisy "already exists" logs.
        """
        # Build list of all required indexes: (index_name, label, property)
        indexes_to_ensure: list[tuple[str, str, str]] = [
            # Infrastructure: Chunk indexes
            ("chunk_id", "Chunk", "id"),
            ("chunk_document", "Chunk", "document_id"),
            ("chunk_index", "Chunk", "chunk_index"),
            # Infrastructure: Document indexes
            ("document_id", "Document", "id"),
            ("document_filename", "Document", "filename"),
        ]
        
        # Schema entity indexes
        for entity in self.schema.entities:
            # Primary index on id
            indexes_to_ensure.append((
                f"{entity.name.lower()}_id",
                entity.name,
                "id"
            ))
            
            # Indexes on common searchable properties
            for prop in entity.properties:
                if prop.name in ["name", "title"]:
                    indexes_to_ensure.append((
                        f"{entity.name.lower()}_{prop.name}",
                        entity.name,
                        prop.name
                    ))
        
        # Use batch operation for efficiency
        result = await self.client.ensure_indexes_batch(indexes_to_ensure)
        
        # Log summary (not individual operations)
        if result["created"] > 0:
            logger.info(f"Indexes: {result['created']} created, {result['existed']} already existed")
        elif result["existed"] > 0:
            logger.debug(f"All {result['existed']} indexes already exist")
        
        if result["failed"] > 0:
            logger.warning(f"Index creation failures: {result['failed']}")
    
    # =========================================================================
    # DOCUMENT OPERATIONS
    # =========================================================================
    
    async def create_document_node(
        self,
        document_id: str,
        filename: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Create a document node.
        
        Args:
            document_id: Unique document identifier
            filename: Original filename
            metadata: Additional document metadata
        """
        props = {
            "id": document_id,
            "filename": filename,
            **(metadata or {}),
        }
        
        prop_sets = [f"n.{key} = ${key}" for key in props.keys()]
        set_clause = ", ".join(prop_sets)
        
        query = f"""
        MERGE (n:Document {{id: $id}})
        SET {set_clause}
        """
        
        await self.client.execute_write(query, props)
        logger.debug(f"Created Document node: {document_id}")
    
    # =========================================================================
    # CHUNK OPERATIONS
    # =========================================================================
    
    async def store_chunks(
        self,
        chunks: list["TextChunk"],
        document_id: str,
        link_sequential: bool = True,
        link_to_document: bool = True,
    ) -> dict[str, int]:
        """
        Store chunks as nodes in Neo4j.
        
        Args:
            chunks: List of TextChunk objects
            document_id: Document ID to link chunks to
            link_sequential: Create NEXT_CHUNK/PREV_CHUNK relationships
            link_to_document: Create FROM_DOCUMENT relationships
            
        Returns:
            Summary of created items
        """
        counts = {"chunks": 0, "sequential_links": 0, "document_links": 0}
        
        # Create all chunk nodes
        for chunk in chunks:
            await self.create_chunk_node(chunk, document_id)
            counts["chunks"] += 1
        
        # Create sequential links
        if link_sequential and len(chunks) > 1:
            for i in range(len(chunks) - 1):
                await self.link_chunks_sequential(chunks[i].id, chunks[i + 1].id)
                counts["sequential_links"] += 1
        
        # Create document links
        if link_to_document:
            for chunk in chunks:
                await self.link_chunk_to_document(chunk.id, document_id)
                counts["document_links"] += 1
        
        logger.info(f"Stored {counts['chunks']} chunks for document {document_id}")
        return counts
    
    async def create_chunk_node(
        self,
        chunk: "TextChunk",
        document_id: str,
    ) -> None:
        """
        Create a single chunk node.
        
        Args:
            chunk: TextChunk object
            document_id: Parent document ID
        """
        # Build properties from chunk
        props = {
            "id": chunk.id,
            "document_id": document_id,
            "chunk_index": chunk.chunk_index,
            "start_char": chunk.start_char,
            "end_char": chunk.end_char,
            "text": chunk.text,
            "char_count": chunk.char_count,
            "word_count": chunk.word_count,
        }
        
        # Add metadata properties
        for key, value in chunk.metadata.items():
            if value is not None:
                # Flatten complex types to strings
                if isinstance(value, (list, dict)):
                    import json
                    props[key] = json.dumps(value)
                else:
                    props[key] = value
        
        prop_sets = [f"n.{key} = ${key}" for key in props.keys()]
        set_clause = ", ".join(prop_sets)
        
        query = f"""
        MERGE (n:Chunk {{id: $id}})
        SET {set_clause}
        """
        
        await self.client.execute_write(query, props)
    
    async def link_chunks_sequential(
        self,
        chunk_id: str,
        next_chunk_id: str,
    ) -> None:
        """Create NEXT_CHUNK and PREV_CHUNK relationships."""
        query = """
        MATCH (a:Chunk {id: $id1})
        MATCH (b:Chunk {id: $id2})
        MERGE (a)-[:NEXT_CHUNK]->(b)
        MERGE (b)-[:PREV_CHUNK]->(a)
        """
        await self.client.execute_write(query, {
            "id1": chunk_id,
            "id2": next_chunk_id,
        })
    
    async def link_chunk_to_document(
        self,
        chunk_id: str,
        document_id: str,
    ) -> None:
        """Create FROM_DOCUMENT relationship."""
        query = """
        MATCH (c:Chunk {id: $chunk_id})
        MATCH (d:Document {id: $doc_id})
        MERGE (c)-[:FROM_DOCUMENT]->(d)
        """
        await self.client.execute_write(query, {
            "chunk_id": chunk_id,
            "doc_id": document_id,
        })
    
    async def link_entity_to_chunk(
        self,
        entity_id: str,
        chunk_id: str,
    ) -> None:
        """Create EXTRACTED_FROM relationship from entity to chunk."""
        query = """
        MATCH (e {id: $entity_id})
        MATCH (c:Chunk {id: $chunk_id})
        MERGE (e)-[:EXTRACTED_FROM]->(c)
        """
        await self.client.execute_write(query, {
            "entity_id": entity_id,
            "chunk_id": chunk_id,
        })
    
    async def get_chunk_by_id(self, chunk_id: str) -> Optional[dict[str, Any]]:
        """Get a chunk by ID."""
        query = """
        MATCH (c:Chunk {id: $id})
        RETURN c
        """
        results = await self.client.execute_query(query, {"id": chunk_id})
        return dict(results[0]["c"]) if results else None
    
    async def get_chunks_for_document(
        self,
        document_id: str,
        include_text: bool = True,
    ) -> list[dict[str, Any]]:
        """Get all chunks for a document, ordered by index."""
        if include_text:
            query = """
            MATCH (c:Chunk {document_id: $doc_id})
            RETURN c
            ORDER BY c.chunk_index
            """
        else:
            query = """
            MATCH (c:Chunk {document_id: $doc_id})
            RETURN c.id as id, c.chunk_index as chunk_index, 
                   c.page_number as page_number, c.section_heading as section_heading,
                   c.word_count as word_count
            ORDER BY c.chunk_index
            """
        
        results = await self.client.execute_query(query, {"doc_id": document_id})
        
        if include_text:
            return [dict(r["c"]) for r in results]
        else:
            return [dict(r) for r in results]
    
    async def get_neighboring_chunks(
        self,
        chunk_id: str,
        before: int = 1,
        after: int = 1,
    ) -> dict[str, Any]:
        """
        Get a chunk with its neighboring chunks for context expansion.
        
        Args:
            chunk_id: Target chunk ID
            before: Number of chunks before
            after: Number of chunks after
            
        Returns:
            Dict with 'before', 'current', 'after' chunks
        """
        # Build dynamic pattern based on before/after counts
        query = """
        MATCH (current:Chunk {id: $id})
        OPTIONAL MATCH path_before = (current)<-[:NEXT_CHUNK*1..""" + str(before) + """]-(before:Chunk)
        OPTIONAL MATCH path_after = (current)-[:NEXT_CHUNK*1..""" + str(after) + """]->(after:Chunk)
        WITH current, 
             collect(DISTINCT before) as before_chunks,
             collect(DISTINCT after) as after_chunks
        RETURN current,
               before_chunks,
               after_chunks
        """
        
        results = await self.client.execute_query(query, {"id": chunk_id})
        
        if not results:
            return {"before": [], "current": None, "after": []}
        
        result = results[0]
        
        # Sort before chunks by index (descending distance from current)
        before_list = [dict(c) for c in result["before_chunks"] if c]
        before_list.sort(key=lambda x: x.get("chunk_index", 0))
        
        # Sort after chunks by index
        after_list = [dict(c) for c in result["after_chunks"] if c]
        after_list.sort(key=lambda x: x.get("chunk_index", 0))
        
        return {
            "before": before_list,
            "current": dict(result["current"]) if result["current"] else None,
            "after": after_list,
        }
    
    async def search_chunks_by_text(
        self,
        search_text: str,
        document_id: Optional[str] = None,
        limit: int = 10,
        return_query: bool = False,
    ) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], dict[str, Any]]:
        """
        Search chunks by text content.
        
        Args:
            search_text: Text to search for
            document_id: Optional document to limit search
            limit: Maximum results
            return_query: If True, return (results, query_info) tuple
            
        Returns:
            List of matching chunks, or (chunks, query_info) if return_query=True
        """
        import time
        
        if document_id:
            query = """
            MATCH (c:Chunk {document_id: $doc_id})
            WHERE toLower(c.text) CONTAINS toLower($search)
            RETURN c
            ORDER BY c.chunk_index
            LIMIT $limit
            """
            params = {"doc_id": document_id, "search": search_text, "limit": limit}
        else:
            query = """
            MATCH (c:Chunk)
            WHERE toLower(c.text) CONTAINS toLower($search)
            RETURN c
            LIMIT $limit
            """
            params = {"search": search_text, "limit": limit}
        
        start_time = time.time()
        results = await self.client.execute_query(query, params)
        exec_time = (time.time() - start_time) * 1000
        
        chunks = [dict(r["c"]) for r in results]
        
        if return_query:
            query_info = {
                "query": query.strip(),
                "params": params,
                "execution_time_ms": exec_time,
            }
            return chunks, query_info
        return chunks
    
    async def search_chunks_by_key_terms(
        self,
        terms: list[str],
        document_id: Optional[str] = None,
        limit: int = 10,
        return_query: bool = False,
    ) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], dict[str, Any]]:
        """
        Search chunks by key terms.
        
        Args:
            terms: List of terms to match
            document_id: Optional document to limit search
            limit: Maximum results
            return_query: If True, return (results, query_info) tuple
            
        Returns:
            List of matching chunks with match counts
        """
        import time
        
        # Convert terms to lowercase for matching
        terms_lower = [t.lower() for t in terms]
        
        if document_id:
            query = """
            MATCH (c:Chunk {document_id: $doc_id})
            WHERE c.key_terms IS NOT NULL
            WITH c, [term IN $terms WHERE toLower(c.key_terms) CONTAINS term] as matches
            WHERE size(matches) > 0
            RETURN c, size(matches) as match_count
            ORDER BY match_count DESC, c.chunk_index
            LIMIT $limit
            """
            params = {"doc_id": document_id, "terms": terms_lower, "limit": limit}
        else:
            query = """
            MATCH (c:Chunk)
            WHERE c.key_terms IS NOT NULL
            WITH c, [term IN $terms WHERE toLower(c.key_terms) CONTAINS term] as matches
            WHERE size(matches) > 0
            RETURN c, size(matches) as match_count
            ORDER BY match_count DESC
            LIMIT $limit
            """
            params = {"terms": terms_lower, "limit": limit}
        
        start_time = time.time()
        results = await self.client.execute_query(query, params)
        exec_time = (time.time() - start_time) * 1000
        
        matches = [{"chunk": dict(r["c"]), "match_count": r["match_count"]} for r in results]
        
        if return_query:
            query_info = {
                "query": query.strip(),
                "params": params,
                "execution_time_ms": exec_time,
            }
            return matches, query_info
        return matches
    
    async def get_chunks_by_page(
        self,
        document_id: str,
        page_number: int,
    ) -> list[dict[str, Any]]:
        """Get all chunks on a specific page."""
        query = """
        MATCH (c:Chunk {document_id: $doc_id})
        WHERE c.page_number = $page
        RETURN c
        ORDER BY c.chunk_index
        """
        results = await self.client.execute_query(query, {
            "doc_id": document_id,
            "page": page_number,
        })
        return [dict(r["c"]) for r in results]
    
    async def get_chunks_with_temporal_refs(
        self,
        document_id: Optional[str] = None,
        temporal_type: Optional[str] = None,
        return_query: bool = False,
    ) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], dict[str, Any]]:
        """
        Get chunks that have temporal references.
        
        Args:
            document_id: Optional document to filter
            temporal_type: Optional type filter (date, duration, relative)
            return_query: If True, return (results, query_info) tuple
            
        Returns:
            List of chunks with temporal_refs
        """
        import time
        
        conditions = ["c.temporal_refs IS NOT NULL"]
        params = {}
        
        if document_id:
            conditions.append("c.document_id = $doc_id")
            params["doc_id"] = document_id
        
        if temporal_type:
            conditions.append(f"c.temporal_refs CONTAINS '{temporal_type}'")
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
        MATCH (c:Chunk)
        WHERE {where_clause}
        RETURN c
        ORDER BY c.chunk_index
        """
        
        start_time = time.time()
        results = await self.client.execute_query(query, params)
        exec_time = (time.time() - start_time) * 1000
        
        chunks = [dict(r["c"]) for r in results]
        
        if return_query:
            query_info = {
                "query": query.strip(),
                "params": params,
                "execution_time_ms": exec_time,
            }
            return chunks, query_info
        return chunks
    
    async def get_source_chunk_for_entity(
        self,
        entity_id: str,
    ) -> Optional[dict[str, Any]]:
        """Get the source chunk for an entity."""
        query = """
        MATCH (e {id: $entity_id})-[:EXTRACTED_FROM]->(c:Chunk)
        RETURN c
        """
        results = await self.client.execute_query(query, {"entity_id": entity_id})
        return dict(results[0]["c"]) if results else None
    
    async def get_entities_from_chunk(
        self,
        chunk_id: str,
    ) -> list[dict[str, Any]]:
        """Get all entities extracted from a chunk."""
        query = """
        MATCH (e)-[:EXTRACTED_FROM]->(c:Chunk {id: $chunk_id})
        RETURN e, labels(e)[0] as entity_type
        """
        results = await self.client.execute_query(query, {"chunk_id": chunk_id})
        return [
            {**dict(r["e"]), "_type": r["entity_type"]}
            for r in results
        ]
    
    # =========================================================================
    # ENTITY OPERATIONS (existing)
    # =========================================================================
    
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
        include_chunks: bool = False,
    ) -> dict[str, Any]:
        """Get graph data for visualization."""
        # Exclude chunks from visualization by default (too many nodes)
        label_filter = "WHERE NOT 'Chunk' IN labels(n) AND NOT 'Document' IN labels(n)" if not include_chunks else ""
        
        nodes_query = f"""
        MATCH (n)
        {label_filter}
        RETURN n, labels(n)[0] as label
        LIMIT $limit
        """
        nodes_results = await self.client.execute_query(nodes_query, {"limit": limit})
        
        nodes = []
        for r in nodes_results:
            node = dict(r["n"])
            node["_label"] = r["label"]
            nodes.append(node)
        
        # Get relationships (excluding chunk relationships by default)
        rel_filter = "WHERE NOT type(r) IN ['NEXT_CHUNK', 'PREV_CHUNK', 'FROM_DOCUMENT', 'EXTRACTED_FROM']" if not include_chunks else ""
        
        rels_query = f"""
        MATCH (a)-[r]->(b)
        {rel_filter}
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
        """
        Get graph statistics with clear breakdown.
        
        Returns:
            - entity_nodes: Count of actual schema entities (Contract, Party, etc.)
            - infrastructure_nodes: Count of Document + Chunk nodes
            - entity_relationships: Schema-defined relationships between entities
            - infrastructure_relationships: EXTRACTED_FROM, FROM_DOCUMENT, NEXT_CHUNK, etc.
        """
        # Get node counts by label
        node_query = """
        MATCH (n)
        RETURN labels(n)[0] as label, count(*) as count
        """
        node_results = await self.client.execute_query(node_query)
        node_counts: dict[str, int] = {}
        for r in node_results:
            label = r.get("label")
            count = r.get("count", 0)
            if label and isinstance(count, int):
                node_counts[label] = count
        
        # Separate infrastructure nodes from entity nodes
        infrastructure_labels = {"Document", "Chunk"}
        entity_counts: dict[str, int] = {}
        infrastructure_count = 0
        
        for label, count in node_counts.items():
            if label in infrastructure_labels:
                infrastructure_count += count
            else:
                entity_counts[label] = count
        
        # Get relationship counts by type
        rel_query = """
        MATCH ()-[r]->()
        RETURN type(r) as rel_type, count(r) as count
        """
        rel_results = await self.client.execute_query(rel_query)
        rel_counts: dict[str, int] = {}
        for r in rel_results:
            rel_type = r.get("rel_type")
            count = r.get("count", 0)
            if rel_type and isinstance(count, int):
                rel_counts[rel_type] = count
        
        # Separate infrastructure relationships from entity relationships
        infrastructure_rel_types = {"EXTRACTED_FROM", "FROM_DOCUMENT", "NEXT_CHUNK", "PREV_CHUNK"}
        entity_rel_count = 0
        infrastructure_rel_count = 0
        entity_rel_breakdown: dict[str, int] = {}
        infrastructure_rel_breakdown: dict[str, int] = {}
        
        for rel_type, count in rel_counts.items():
            if rel_type in infrastructure_rel_types:
                infrastructure_rel_count += count
                infrastructure_rel_breakdown[rel_type] = count
            else:
                entity_rel_count += count
                entity_rel_breakdown[rel_type] = count
        
        total_entities = sum(entity_counts.values())
        total_nodes = total_entities + infrastructure_count
        total_relationships = entity_rel_count + infrastructure_rel_count
        
        return {
            # Summary totals
            "total_nodes": total_nodes,
            "total_relationships": total_relationships,
            
            # Entity breakdown (what users care about)
            "entities": {
                "total": total_entities,
                "by_type": entity_counts,
            },
            "entity_relationships": {
                "total": entity_rel_count,
                "by_type": entity_rel_breakdown,
            },
            
            # Infrastructure breakdown (chunks, documents, links)
            "infrastructure": {
                "documents": node_counts.get("Document", 0),
                "chunks": node_counts.get("Chunk", 0),
                "relationships": {
                    "total": infrastructure_rel_count,
                    "by_type": infrastructure_rel_breakdown,
                },
            },
            
            # Legacy format for backward compatibility
            "node_counts": node_counts,
            "schema_name": self.schema.schema_info.name if self.schema else None,
        }
    
    async def delete_document_graph(self, source_document: str) -> dict[str, int]:
        """Delete all entities and chunks from a specific document."""
        # Delete chunks first
        chunk_query = """
        MATCH (c:Chunk {document_id: $doc})
        DETACH DELETE c
        RETURN count(c) as deleted_chunks
        """
        chunk_results = await self.client.execute_query(chunk_query, {"doc": source_document})
        
        # Delete document node
        doc_query = """
        MATCH (d:Document {id: $doc})
        DETACH DELETE d
        """
        await self.client.execute_write(doc_query, {"doc": source_document})
        
        # Delete entities
        entity_query = """
        MATCH (n)
        WHERE n.source_document = $doc OR n.source_file = $doc
        DETACH DELETE n
        RETURN count(n) as deleted
        """
        entity_results = await self.client.execute_query(entity_query, {"doc": source_document})
        
        return {
            "deleted_entities": entity_results[0]["deleted"] if entity_results else 0,
            "deleted_chunks": chunk_results[0]["deleted_chunks"] if chunk_results else 0,
        }
    
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
            "chunks": stats.get("Chunk", 0),
            "documents": stats.get("Document", 0),
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
