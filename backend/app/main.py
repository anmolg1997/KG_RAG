"""
KG-RAG Backend Application

FastAPI application for Knowledge Graph-based RAG system.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.core.neo4j_client import get_neo4j_client
from app.api.routes import (
    upload_router,
    query_router,
    graph_router,
    extraction_router,
    health_router,
    strategies_router,
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting KG-RAG Backend...")
    
    # Initialize Neo4j connection
    neo4j_client = get_neo4j_client()
    try:
        await neo4j_client.connect()
        logger.info("Connected to Neo4j")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        logger.warning("Application starting without Neo4j connection")
    
    # Create upload directory
    upload_path = Path(settings.upload_path)
    upload_path.mkdir(exist_ok=True)
    
    yield
    
    # Shutdown
    logger.info("Shutting down KG-RAG Backend...")
    await neo4j_client.close()


# Create FastAPI app
app = FastAPI(
    title="KG-RAG API",
    description="""
    Knowledge Graph-based Retrieval Augmented Generation API.
    
    ## Features
    
    - **Document Upload**: Upload PDF documents for processing
    - **Entity Extraction**: Extract structured entities from contracts
    - **Knowledge Graph**: Store and query entities in Neo4j
    - **RAG Queries**: Ask questions about your documents
    
    ## Getting Started
    
    1. Upload a document via `/upload/document`
    2. Query the knowledge graph via `/query/ask`
    3. Explore the graph via `/graph/visualization`
    """,
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(strategies_router)
app.include_router(upload_router)
app.include_router(query_router)
app.include_router(graph_router)
app.include_router(extraction_router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "KG-RAG API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "strategies": "/strategies",
            "upload": "/upload",
            "query": "/query",
            "graph": "/graph",
            "extraction": "/extraction",
        },
    }




if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug,
    )
