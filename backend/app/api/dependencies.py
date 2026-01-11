"""
FastAPI dependencies for dependency injection.
"""

from typing import AsyncGenerator

from app.core.neo4j_client import Neo4jClient, get_neo4j_client
from app.core.llm import LLMClient, get_llm_client
from app.graph.dynamic_repository import DynamicGraphRepository
from app.rag.pipeline import RAGPipeline


async def get_neo4j() -> AsyncGenerator[Neo4jClient, None]:
    """Dependency for Neo4j client."""
    client = get_neo4j_client()
    await client.connect()
    try:
        yield client
    finally:
        pass  # Connection pooling handles cleanup


async def get_llm() -> LLMClient:
    """Dependency for LLM client."""
    return get_llm_client()


async def get_graph_repo() -> AsyncGenerator[DynamicGraphRepository, None]:
    """Dependency for graph repository."""
    repo = DynamicGraphRepository()
    await repo.initialize()
    yield repo


async def get_rag() -> RAGPipeline:
    """Dependency for RAG pipeline."""
    return RAGPipeline()
