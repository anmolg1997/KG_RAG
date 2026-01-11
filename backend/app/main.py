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
# DEBUG mode: full details with timestamps and module names
# INFO mode: clean output for progress visibility
if settings.debug:
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_level = logging.DEBUG
else:
    log_format = "%(message)s"  # Clean output for INFO logs
    log_level = logging.INFO

logging.basicConfig(level=log_level, format=log_format)


class ThirdPartyNoiseFilter(logging.Filter):
    """
    Smart filter for third-party library logs.
    
    Instead of blanket suppression (which hides critical info),
    this filter selectively removes known noisy patterns while
    preserving warnings, errors, and useful info messages.
    """
    
    # Patterns that are known to be noisy/repetitive at INFO level
    NOISE_PATTERNS = [
        # httpx/httpcore connection pool messages
        "HTTP Request:",
        "load_ssl_context",
        "connect_tcp.started",
        "connect_tcp.complete",
        "send_request_headers",
        "receive_response_headers",
        "receive_response_body",
        "close.started",
        "close.complete",
        # urllib3 pool messages
        "Starting new HTTP",
        "Resetting dropped connection",
        # Generic connection noise
        "connection_acquired",
        "connection_released",
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Always allow warnings, errors, and critical
        if record.levelno >= logging.WARNING:
            return True
        
        message = record.getMessage()
        
        # Filter out known noisy patterns at DEBUG/INFO
        for pattern in self.NOISE_PATTERNS:
            if pattern in message:
                return False
        
        return True


# Apply smart filter to third-party loggers (instead of blanket level suppression)
_noise_filter = ThirdPartyNoiseFilter()
for third_party_logger in ["httpx", "httpcore", "urllib3"]:
    logging.getLogger(third_party_logger).addFilter(_noise_filter)

# Note: openai and litellm are handled separately in llm.py with API key masking

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
