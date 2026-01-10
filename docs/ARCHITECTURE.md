# System Architecture Guide

This document explains the **complete architecture** of the KG-RAG system, breaking down every component and how they connect.

---

## 📚 Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Directory Structure Explained](#directory-structure-explained)
3. [Backend Deep Dive](#backend-deep-dive)
4. [Data Flow](#data-flow)
5. [Configuration System](#configuration-system)
6. [Schema System](#schema-system)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  USERS                                       │
│                            (Web Browser)                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTP Requests
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                        │
│                         (React + Vite + Tailwind)                           │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  QueryChat   │  │DocumentUpload│  │   GraphViz   │  │  Extraction  │    │
│  │  Component   │  │  Component   │  │  Component   │  │   Panel      │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        State Management (Zustand)                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        API Client (Axios)                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│                         Port: 5173 (development)                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ REST API Calls
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND                                         │
│                            (FastAPI + Python)                               │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         API Layer (FastAPI)                          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐    │   │
│  │  │ /upload  │  │ /query   │  │ /graph   │  │   /extraction    │    │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│  ┌───────────────────────────────────┼───────────────────────────────────┐ │
│  │                           CORE SERVICES                                │ │
│  │                                                                        │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐       │ │
│  │  │   Ingestion     │  │   Extraction    │  │      RAG        │       │ │
│  │  │   Pipeline      │  │    Pipeline     │  │    Pipeline     │       │ │
│  │  │                 │  │                 │  │                 │       │ │
│  │  │ • PDF Parser    │  │ • Schema Loader │  │ • Retriever     │       │ │
│  │  │ • Chunker       │  │ • LLM Client    │  │ • Generator     │       │ │
│  │  │ • Orchestrator  │  │ • Validator     │  │ • Orchestrator  │       │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘       │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                      │
│                         Port: 8000                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                   │                                      │
                   │                                      │
                   ▼                                      ▼
┌──────────────────────────────┐         ┌─────────────────────────────────┐
│         NEO4J                │         │           LLM API               │
│    (Graph Database)          │         │   (OpenAI/Anthropic/Ollama)     │
│                              │         │                                 │
│  • Nodes (Entities)          │         │  • Entity Extraction            │
│  • Relationships (Edges)     │         │  • Query Understanding          │
│  • Cypher Queries            │         │  • Response Generation          │
│                              │         │                                 │
│  Ports: 7474 (HTTP)          │         │  Via LiteLLM (model agnostic)   │
│         7687 (Bolt)          │         │                                 │
└──────────────────────────────┘         └─────────────────────────────────┘
```

---

## Directory Structure Explained

```
KG_RAG/
│
├── schemas/                          # 🎯 SCHEMA DEFINITIONS
│   │                                 # This is where you define WHAT to extract
│   │
│   ├── contract.yaml                 # Schema for legal contracts
│   ├── research_paper.yaml           # Schema for academic papers
│   └── README.md                     # How to create custom schemas
│
├── backend/                          # 🐍 PYTHON BACKEND
│   │
│   ├── app/                          # Main application code
│   │   │
│   │   ├── main.py                   # FastAPI app entry point
│   │   │                             # - Creates the app
│   │   │                             # - Includes routers
│   │   │                             # - Handles startup/shutdown
│   │   │
│   │   ├── config.py                 # Configuration management
│   │   │                             # - Loads from .env
│   │   │                             # - Defines all settings
│   │   │
│   │   ├── api/                      # API endpoints
│   │   │   ├── routes/
│   │   │   │   ├── upload.py         # POST /upload/* - File upload
│   │   │   │   ├── query.py          # POST /query/* - RAG queries
│   │   │   │   ├── graph.py          # GET /graph/* - Graph data
│   │   │   │   └── extraction.py     # POST /extraction/* - Manual extraction
│   │   │   └── dependencies.py       # Shared dependencies
│   │   │
│   │   ├── core/                     # Core clients
│   │   │   ├── neo4j_client.py       # Neo4j database connection
│   │   │   │                         # - Connection pooling
│   │   │   │                         # - Query execution
│   │   │   │
│   │   │   └── llm.py                # LLM client (via LiteLLM)
│   │   │                             # - Model-agnostic
│   │   │                             # - Structured output support
│   │   │
│   │   ├── schema/                   # Schema management (NEW!)
│   │   │   ├── loader.py             # Loads YAML schemas
│   │   │   │                         # - Parses schema files
│   │   │   │                         # - Generates prompts
│   │   │   │
│   │   │   └── models.py             # Dynamic data models
│   │   │                             # - DynamicEntity
│   │   │                             # - DynamicGraph
│   │   │
│   │   ├── ingestion/                # Document processing
│   │   │   ├── pdf_parser.py         # PDF → Text
│   │   │   │                         # - Uses PyMuPDF
│   │   │   │                         # - Extracts metadata
│   │   │   │
│   │   │   ├── chunker.py            # Text → Chunks
│   │   │   │                         # - Multiple strategies
│   │   │   │                         # - Preserves context
│   │   │   │
│   │   │   └── pipeline.py           # Orchestrates ingestion
│   │   │                             # - Coordinates all steps
│   │   │                             # - Tracks progress
│   │   │
│   │   ├── extraction/               # Entity extraction
│   │   │   ├── dynamic_extractor.py  # Schema-agnostic extraction
│   │   │   │                         # - Works with ANY schema
│   │   │   │                         # - Generates prompts dynamically
│   │   │   │
│   │   │   ├── ontology.py           # (Legacy) Hardcoded models
│   │   │   ├── prompts.py            # (Legacy) Hardcoded prompts
│   │   │   └── validator.py          # Validation logic
│   │   │
│   │   ├── graph/                    # Graph operations
│   │   │   ├── dynamic_repository.py # Schema-agnostic storage
│   │   │   │                         # - Works with ANY entity types
│   │   │   │                         # - Dynamic Neo4j operations
│   │   │   │
│   │   │   ├── repository.py         # (Legacy) Hardcoded repository
│   │   │   └── queries.py            # Query builders
│   │   │
│   │   └── rag/                      # RAG pipeline
│   │       ├── retriever.py          # Graph → Context
│   │       │                         # - Query understanding
│   │       │                         # - Graph traversal
│   │       │
│   │       ├── generator.py          # Context → Answer
│   │       │                         # - Prompt construction
│   │       │                         # - LLM generation
│   │       │
│   │       └── pipeline.py           # Orchestrates RAG
│   │                                 # - Conversation history
│   │                                 # - Follow-up questions
│   │
│   ├── requirements.txt              # Python dependencies
│   └── Dockerfile                    # Container definition
│
├── frontend/                         # ⚛️ REACT FRONTEND
│   │
│   ├── src/
│   │   ├── main.tsx                  # React entry point
│   │   ├── App.tsx                   # Main app component
│   │   ├── index.css                 # Global styles (Tailwind)
│   │   │
│   │   ├── components/               # UI components
│   │   │   ├── QueryChat.tsx         # Chat interface
│   │   │   ├── DocumentUpload.tsx    # File upload
│   │   │   ├── GraphVisualization.tsx# Graph viewer
│   │   │   └── ExtractionPanel.tsx   # Manual extraction
│   │   │
│   │   ├── services/
│   │   │   └── api.ts                # API client
│   │   │
│   │   └── store/
│   │       └── index.ts              # State management
│   │
│   ├── package.json                  # Node.js dependencies
│   ├── vite.config.ts                # Vite configuration
│   ├── tailwind.config.js            # Tailwind configuration
│   └── tsconfig.json                 # TypeScript configuration
│
├── docs/                             # 📖 DOCUMENTATION
│   ├── ARCHITECTURE.md               # This file
│   ├── KNOWLEDGE_GRAPH_GUIDE.md      # KG basics
│   └── FRONTEND_GUIDE.md             # React basics
│
├── docker-compose.yml                # Multi-container setup
├── env.example                       # Environment template
└── README.md                         # Project overview
```

---

## Backend Deep Dive

### How Each Module Works

#### 1. Configuration (`config.py`)

**Purpose**: Centralized configuration management.

```python
# How it works:
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Automatically loads from .env file
    neo4j_uri: str = "bolt://localhost:7687"
    openai_api_key: Optional[str] = None
    active_schema: str = "contract"  # Which schema to use

# Usage anywhere in code:
from app.config import settings
print(settings.neo4j_uri)
```

**Why Pydantic Settings?**
- Type validation
- Environment variable loading
- Default values
- Documentation via type hints

#### 2. Schema Loader (`schema/loader.py`)

**Purpose**: Load and manage schema definitions from YAML files.

```python
# What it does:
class SchemaLoader:
    def load_schema(self, name: str) -> Schema:
        # 1. Read YAML file
        # 2. Parse into Schema model
        # 3. Validate structure
        # 4. Cache for reuse
        
    def generate_extraction_prompt(self, schema, text):
        # 1. Build entity descriptions from schema
        # 2. Build relationship descriptions
        # 3. Combine into extraction prompt
        # 4. Return prompt ready for LLM

# Flow:
YAML File → SchemaLoader → Schema Object → Prompts/Validation
```

**Why Schema-Driven?**
- **Flexibility**: Change entities without code changes
- **Maintainability**: Non-programmers can modify schemas
- **Reusability**: Same code for any document type

#### 3. Dynamic Extractor (`extraction/dynamic_extractor.py`)

**Purpose**: Extract entities using any schema.

```python
# What it does:
class DynamicExtractor:
    def __init__(self, schema_name="contract"):
        self.schema = schema_loader.load_schema(schema_name)
        
    async def extract(self, text: str) -> ExtractionResult:
        # 1. Generate prompt from schema
        prompt = self.schema_loader.generate_extraction_prompt(
            self.schema, text
        )
        
        # 2. Call LLM
        response = await self.llm.complete(prompt)
        
        # 3. Parse JSON response
        graph = self._parse_response(response)
        
        # 4. Validate against schema
        errors = self._validate_graph(graph)
        
        return ExtractionResult(graph, errors)
```

**Key Innovation**: The same code works for contracts, research papers, invoices, etc.

#### 4. Dynamic Repository (`graph/dynamic_repository.py`)

**Purpose**: Store any entity types in Neo4j.

```python
# How it creates nodes dynamically:
async def create_entity(self, entity: DynamicEntity):
    # entity.entity_type = "Author" (from schema)
    # entity.properties = {"name": "John", "affiliation": "MIT"}
    
    query = f"""
    MERGE (n:{entity.entity_type} {{id: $id}})
    SET n.name = $name, n.affiliation = $affiliation
    """
    # Executes: MERGE (n:Author {id: "..."})
```

**Key Feature**: Node labels come from schema, not hardcoded.

#### 5. RAG Pipeline (`rag/`)

**Purpose**: Answer questions using the graph.

```
User Question
      │
      ▼
┌─────────────┐
│  Retriever  │ ──── Query Neo4j
└─────────────┘
      │
      ▼ Context (entities, relationships)
┌─────────────┐
│  Generator  │ ──── Call LLM with context
└─────────────┘
      │
      ▼
   Answer
```

---

## Data Flow

### Document Upload Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│   PDF    │ ──▶ │  Parser  │ ──▶ │ Chunker  │ ──▶ │Extractor │
│   File   │     │          │     │          │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                                                        │
                     ┌──────────────────────────────────┘
                     ▼
              ┌──────────┐     ┌──────────┐
              │Validator │ ──▶ │  Neo4j   │
              │          │     │ Storage  │
              └──────────┘     └──────────┘
```

**Step by Step:**

1. **PDF Parser** (`pdf_parser.py`)
   - Input: PDF file bytes
   - Output: Text + metadata (page count, title, etc.)
   - How: Uses PyMuPDF library

2. **Chunker** (`chunker.py`)
   - Input: Full document text
   - Output: List of text chunks with overlap
   - How: Split by paragraphs/sentences, maintain overlap

3. **Extractor** (`dynamic_extractor.py`)
   - Input: Text chunks
   - Output: DynamicGraph (entities + relationships)
   - How: LLM with schema-generated prompt

4. **Validator** (in extractor)
   - Input: DynamicGraph
   - Output: Errors/warnings
   - How: Check required properties, valid relationships

5. **Storage** (`dynamic_repository.py`)
   - Input: Validated DynamicGraph
   - Output: Data in Neo4j
   - How: MERGE nodes, CREATE relationships

### Query Flow

```
┌──────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
│ Question │ ──▶ │  Query    │ ──▶ │   Graph   │ ──▶ │ Response  │
│          │     │ Analyzer  │     │ Retriever │     │ Generator │
└──────────┘     └───────────┘     └───────────┘     └───────────┘
                                                           │
                                                           ▼
                                                     ┌───────────┐
                                                     │  Answer   │
                                                     └───────────┘
```

---

## Configuration System

### Environment Variables

All configuration is via environment variables (in `.env` file):

```bash
# Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# LLM
DEFAULT_LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...

# Schema
ACTIVE_SCHEMA=contract        # Which schema to use by default

# Processing
CHUNK_SIZE=1000              # Characters per chunk
CHUNK_OVERLAP=200            # Overlap between chunks
```

### How Configuration is Loaded

```python
# In config.py:
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",    # Load from .env file
        extra="ignore",     # Ignore unknown vars
    )
    
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    active_schema: str = Field(default="contract")

# Usage:
from app.config import settings
print(settings.active_schema)  # "contract"
```

---

## Schema System

### How Schemas Work

```
┌─────────────────┐
│   YAML File     │
│ (contract.yaml) │
└────────┬────────┘
         │
         ▼ SchemaLoader.load_schema()
┌─────────────────┐
│  Schema Object  │
│                 │
│ • entities[]    │
│ • relationships │
│ • extraction    │
└────────┬────────┘
         │
         ├──────────────────┬──────────────────┐
         ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Prompt          │ │ Validation      │ │ Graph Storage   │
│ Generation      │ │ Rules           │ │ Schema          │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Schema Structure

```yaml
# schemas/contract.yaml

schema:
  name: contract           # Schema identifier
  description: "..."       # Human description

entities:                  # What to extract
  - name: Contract         # Node label in Neo4j
    properties:            # Properties of this entity
      - name: title
        type: string
        required: true

relationships:             # How entities connect
  - name: HAS_PARTY
    source: Contract
    target: Party

extraction:                # LLM instructions
  system_prompt: "..."
  domain_hints: [...]
```

### Switching Schemas

To use a different schema:

1. **Create schema file**: `schemas/my_schema.yaml`
2. **Update config**: `ACTIVE_SCHEMA=my_schema`
3. **Restart backend**

Or programmatically:
```python
extractor = DynamicExtractor(schema_name="research_paper")
```

---

---

## Development Setup

### Using uv (Recommended)

We use [uv](https://github.com/astral-sh/uv) for fast Python dependency management:

```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup backend
cd backend
uv venv                           # Create virtual environment
source .venv/bin/activate         # Activate it
uv pip install -r requirements.txt # Install dependencies
```

### Using Makefile

The Makefile provides convenient commands:

```bash
make help           # Show all commands
make setup          # Full project setup
make dev            # Start all dev servers
make health         # Check service health
make test           # Run tests
make lint           # Run linters
```

---

## What's Next?

- Read [FRONTEND_GUIDE.md](./FRONTEND_GUIDE.md) to understand the React frontend
- Read [KNOWLEDGE_GRAPH_GUIDE.md](./KNOWLEDGE_GRAPH_GUIDE.md) for graph concepts
- Try creating your own schema in `schemas/`
