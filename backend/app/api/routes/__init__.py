"""API route modules."""

from .upload import router as upload_router
from .query import router as query_router
from .graph import router as graph_router
from .extraction import router as extraction_router
from .health import router as health_router
from .strategies import router as strategies_router

__all__ = [
    "upload_router",
    "query_router",
    "graph_router",
    "extraction_router",
    "health_router",
    "strategies_router",
]
