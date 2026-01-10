"""
Schema management module.

This module provides schema-agnostic document processing by loading
ontology definitions from YAML configuration files.
"""

from .loader import SchemaLoader, get_schema_loader
from .models import (
    Schema,
    EntityDefinition,
    PropertyDefinition,
    RelationshipDefinition,
    DynamicEntity,
    DynamicGraph,
)

__all__ = [
    "SchemaLoader",
    "get_schema_loader",
    "Schema",
    "EntityDefinition",
    "PropertyDefinition",
    "RelationshipDefinition",
    "DynamicEntity",
    "DynamicGraph",
]
