"""
Neo4j database client with connection pooling and async support.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import ServiceUnavailable, AuthError

from app.config import settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """
    Async Neo4j client wrapper with connection management.
    
    Usage:
        client = Neo4jClient()
        await client.connect()
        
        async with client.session() as session:
            result = await session.run("MATCH (n) RETURN n LIMIT 10")
            records = await result.data()
        
        await client.close()
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password
        self._driver: Optional[AsyncDriver] = None

    async def connect(self) -> None:
        """Establish connection to Neo4j."""
        if self._driver is not None:
            return

        try:
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_pool_size=50,
            )
            # Verify connectivity
            await self._driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")
        except AuthError as e:
            logger.error(f"Neo4j authentication failed: {e}")
            raise
        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable at {self.uri}: {e}")
            raise

    async def close(self) -> None:
        """Close the Neo4j connection."""
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")

    @asynccontextmanager
    async def session(self, database: str = "neo4j"):
        """
        Get an async session context manager.
        
        Usage:
            async with client.session() as session:
                result = await session.run(query)
        """
        if self._driver is None:
            await self.connect()
        
        session = self._driver.session(database=database)
        try:
            yield session
        finally:
            await session.close()

    async def execute_query(
        self,
        query: str,
        parameters: Optional[dict[str, Any]] = None,
        database: str = "neo4j",
    ) -> list[dict[str, Any]]:
        """
        Execute a Cypher query and return results as list of dicts.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Database name
            
        Returns:
            List of result records as dictionaries
        """
        async with self.session(database=database) as session:
            result = await session.run(query, parameters or {})
            return await result.data()

    async def execute_write(
        self,
        query: str,
        parameters: Optional[dict[str, Any]] = None,
        database: str = "neo4j",
    ) -> dict[str, Any]:
        """
        Execute a write query and return summary.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Database name
            
        Returns:
            Query execution summary
        """
        async with self.session(database=database) as session:
            result = await session.run(query, parameters or {})
            summary = await result.consume()
            return {
                "nodes_created": summary.counters.nodes_created,
                "nodes_deleted": summary.counters.nodes_deleted,
                "relationships_created": summary.counters.relationships_created,
                "relationships_deleted": summary.counters.relationships_deleted,
                "properties_set": summary.counters.properties_set,
            }

    async def health_check(self) -> bool:
        """Check if Neo4j is healthy and accessible."""
        try:
            if self._driver is None:
                await self.connect()
            await self._driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return False

    async def clear_database(self, database: str = "neo4j") -> dict[str, Any]:
        """
        Clear all nodes and relationships from the database.
        USE WITH CAUTION - this deletes all data!
        
        Returns:
            Summary of deleted items
        """
        query = "MATCH (n) DETACH DELETE n"
        return await self.execute_write(query, database=database)

    async def get_schema(self, database: str = "neo4j") -> dict[str, Any]:
        """
        Get the current database schema (labels, relationship types, properties).
        
        Returns:
            Schema information
        """
        labels_query = "CALL db.labels()"
        rel_types_query = "CALL db.relationshipTypes()"
        
        async with self.session(database=database) as session:
            labels_result = await session.run(labels_query)
            labels = [record["label"] async for record in labels_result]
            
            rel_result = await session.run(rel_types_query)
            rel_types = [record["relationshipType"] async for record in rel_result]
        
        return {
            "labels": labels,
            "relationship_types": rel_types,
        }


# Singleton instance
_neo4j_client: Optional[Neo4jClient] = None


def get_neo4j_client() -> Neo4jClient:
    """Get the singleton Neo4j client instance."""
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
    return _neo4j_client
