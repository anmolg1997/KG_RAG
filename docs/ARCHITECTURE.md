# System Architecture Guide

This document explains the **complete architecture** of the KG-RAG system, breaking down every component and how they connect.

---

## 📚 Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Directory Structure](#directory-structure)
3. [Backend Deep Dive](#backend-deep-dive)
4. [Data Flow](#data-flow)
5. [Configuration System](#configuration-system)
6. [Schema System](#schema-system)
7. [Strategy System](#strategy-system)
8. [Chunk Storage System](#chunk-storage-system)
9. [Development Setup](#development-setup)
10. [Step-by-Step Flow Guides](#step-by-step-flow-guides) ⭐ NEW
    - [Document Ingestion Flow](#-document-ingestion-flow-backend)
    - [Query/RAG Flow](#-queryrag-flow-backend)
    - [Frontend User Interaction Flow](#️-frontend-user-interaction-flow)

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
│  │  QueryChat   │  │DocumentUpload│  │   GraphViz   │  │ HealthStatus │    │
│  │  Component   │  │  Component   │  │  Component   │  │  Component   │    │
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
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐│   │
│  │  │ /health  │  │ /upload  │  │ /query   │  │ /graph   │  │/extract││   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └────────┘│   │
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
│  │  │ • Orchestrator  │  │ • Extractor     │  │ • Orchestrator  │       │ │
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

## Directory Structure

```
KG_RAG/
│
├── schemas/                          # 🎯 SCHEMA DEFINITIONS
│   ├── contract.yaml                 # Schema for legal contracts
│   ├── research_paper.yaml           # Schema for academic papers
│   └── README.md                     # How to create custom schemas
│
├── backend/                          # 🐍 PYTHON BACKEND
│   │
│   ├── app/
│   │   │
│   │   ├── main.py                   # FastAPI app entry point
│   │   ├── config.py                 # Configuration management
│   │   │
│   │   ├── api/                      # API endpoints
│   │   │   ├── routes/
│   │   │   │   ├── health.py         # GET /health/* - Health checks
│   │   │   │   ├── strategies.py     # GET/POST /strategies/* - Strategy config
│   │   │   │   ├── upload.py         # POST /upload/* - File upload
│   │   │   │   ├── query.py          # POST /query/* - RAG queries
│   │   │   │   ├── graph.py          # GET /graph/* - Graph operations
│   │   │   │   └── extraction.py     # POST /extraction/* - Manual extraction
│   │   │   └── dependencies.py       # Shared dependencies
│   │   │
│   │   ├── core/                     # Core clients
│   │   │   ├── neo4j_client.py       # Neo4j database connection
│   │   │   └── llm.py                # LLM client (via LiteLLM)
│   │   │
│   │   ├── strategies/               # ⚡ STRATEGY SYSTEM (NEW!)
│   │   │   ├── models.py             # ExtractionStrategy, RetrievalStrategy
│   │   │   ├── presets.py            # Predefined strategy combinations
│   │   │   └── manager.py            # Strategy loading and management
│   │   │
│   │   ├── schema/                   # Schema management
│   │   │   ├── loader.py             # Loads YAML schemas, generates prompts
│   │   │   └── models.py             # DynamicEntity, DynamicGraph models
│   │   │
│   │   ├── ingestion/                # Document processing
│   │   │   ├── pdf_parser.py         # PDF → Text with page tracking
│   │   │   ├── chunker.py            # Text → Chunks with rich metadata
│   │   │   ├── pipeline.py           # Orchestrates full ingestion
│   │   │   └── metadata/             # Metadata extractors
│   │   │       ├── section_extractor.py   # Detect document sections
│   │   │       ├── temporal_extractor.py  # Extract dates, durations
│   │   │       └── term_extractor.py      # Extract key terms
│   │   │
│   │   ├── extraction/               # Entity extraction
│   │   │   └── dynamic_extractor.py  # Schema-agnostic extraction
│   │   │
│   │   ├── graph/                    # Graph operations
│   │   │   ├── dynamic_repository.py # Schema-agnostic Neo4j storage + chunks
│   │   │   └── queries.py            # Query builders
│   │   │
│   │   └── rag/                      # RAG pipeline
│   │       ├── retriever.py          # Multi-signal retrieval
│   │       ├── context_builder.py    # Context assembly with expansion
│   │       ├── generator.py          # Context → Answer generation
│   │       └── pipeline.py           # Orchestrates RAG
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
│   │   │   ├── ExtractionPanel.tsx   # Manual extraction
│   │   │   └── HealthStatus.tsx      # System health display
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
│   ├── FRONTEND_GUIDE.md             # React basics
│   └── MAKEFILE_GUIDE.md             # Make commands
│
├── Makefile                          # Development commands
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
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Automatically loads from .env file
    neo4j_uri: str = "bolt://localhost:7687"
    openai_api_key: Optional[str] = None
    active_schema: str = "contract"  # Which schema to use

# Usage anywhere in code:
from app.config import settings
print(settings.active_schema)  # "contract"
```

**Why Pydantic Settings?**
- Type validation
- Environment variable loading
- Default values
- Documentation via type hints

#### 2. Schema Loader (`schema/loader.py`)

**Purpose**: Load and manage schema definitions from YAML files.

```python
class SchemaLoader:
    def load_schema(self, name: str) -> Schema:
        # 1. Read YAML file from schemas/ directory
        # 2. Parse into Schema model
        # 3. Validate structure
        # 4. Cache for reuse
        
    def generate_extraction_prompt(self, schema, text):
        # 1. Build entity descriptions from schema
        # 2. Build relationship descriptions
        # 3. Combine into extraction prompt
        # 4. Return prompt ready for LLM

# Flow:
# YAML File → SchemaLoader → Schema Object → Prompts/Validation
```

**Why Schema-Driven?**
- **Flexibility**: Change entities without code changes
- **Maintainability**: Non-programmers can modify schemas
- **Reusability**: Same code for any document type

#### 3. Dynamic Extractor (`extraction/dynamic_extractor.py`)

**Purpose**: Extract entities using any schema.

```python
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

**Key Feature**: The same code works for contracts, research papers, invoices, etc.

#### 4. Dynamic Repository (`graph/dynamic_repository.py`)

**Purpose**: Store any entity types in Neo4j.

```python
class DynamicGraphRepository:
    async def create_entity(self, entity: DynamicEntity):
        # entity.entity_type = "Author" (from schema)
        # entity.properties = {"name": "John", "affiliation": "MIT"}
        
        query = f"""
        MERGE (n:{entity.entity_type} {{id: $id}})
        SET n += $properties
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
              │  Schema  │ ──▶ │  Neo4j   │
              │ Validate │     │ Storage  │
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
   - Input: Text chunks + active schema
   - Output: DynamicGraph (entities + relationships)
   - How: LLM with schema-generated prompt

4. **Schema Validation** (in extractor)
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

## Strategy System

The **Strategy System** provides configurable control over how documents are processed (extraction) and how information is retrieved (retrieval). This allows you to tune the system for different use cases without changing code.

### Strategy Types

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXTRACTION STRATEGY                           │
│  Controls how documents are processed during ingestion          │
│                                                                 │
│  • Chunk Storage: Store chunks as graph nodes                   │
│  • Chunk Linking: NEXT/PREV relationships between chunks        │
│  • Metadata Extraction:                                         │
│    - Page numbers                                               │
│    - Section headings                                           │
│    - Temporal references (dates, durations)                     │
│    - Key terms                                                  │
│  • Entity Linking: Link entities to source chunks               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    RETRIEVAL STRATEGY                            │
│  Controls how information is found when answering queries       │
│                                                                 │
│  • Search Methods:                                              │
│    - Graph traversal (entity relationships)                     │
│    - Chunk text search (full-text)                             │
│    - Keyword matching (extracted terms)                        │
│    - Temporal filtering (dates in query)                       │
│  • Context Expansion: Include neighboring chunks                │
│  • Scoring: Weight different signal types                      │
│  • Limits: Max chunks, entities, tokens                        │
└─────────────────────────────────────────────────────────────────┘
```

### Available Presets

| Preset | Use Case | Description |
|--------|----------|-------------|
| **minimal** | Quick testing | Entities only, no chunks |
| **balanced** | General use | Good mix of features (default) |
| **comprehensive** | Deep analysis | All features enabled, best for legal docs |
| **speed** | High volume | Minimal metadata, fast processing |
| **research** | Academic papers | Focus on sections and key terms |

### API Endpoints

```bash
# Get current strategy status
GET /strategies

# List available presets
GET /strategies/presets

# Load a preset
POST /strategies/preset
{ "name": "comprehensive" }

# Get/update extraction strategy
GET  /strategies/extraction
PATCH /strategies/extraction
{ "updates": { "metadata": { "temporal_references": { "enabled": false } } } }

# Get/update retrieval strategy
GET  /strategies/retrieval
PATCH /strategies/retrieval
{ "updates": { "search": { "graph_traversal": { "max_depth": 3 } } } }
```

### Frontend Integration

The `StrategyPanel` component in the sidebar allows real-time strategy configuration:
- Quick preset selection buttons
- Toggle switches for each feature
- Immediate effect on subsequent operations

---

## Chunk Storage System

The **Chunk Storage System** stores text chunks as nodes in Neo4j, enabling richer retrieval through source linking and context expansion.

### Graph Model

```
                    ┌──────────────┐
                    │   Document   │
                    │              │
                    │  filename    │
                    │  page_count  │
                    └──────┬───────┘
                           │ FROM_DOCUMENT
    ┌──────────────┬───────┴───────┬──────────────┐
    ▼              ▼               ▼              ▼
┌────────┐  NEXT  ┌────────┐  NEXT  ┌────────┐  NEXT  ┌────────┐
│ Chunk 0 │◀─────▶│ Chunk 1 │◀─────▶│ Chunk 2 │◀─────▶│ Chunk 3 │
│         │  PREV │         │  PREV │         │  PREV │         │
│ text    │       │ text    │       │ text    │       │ text    │
│ page: 1 │       │ page: 1 │       │ page: 2 │       │ page: 2 │
│ section │       │ section │       │ section │       │ section │
└────┬────┘       └────┬────┘       └────┬────┘       └─────────┘
     │                 │                 │
     │                 │                 │ EXTRACTED_FROM
     │                 ▼                 ▼
     │           ┌──────────┐      ┌──────────┐
     │           │  Party   │      │  Clause  │
     │           │  "Acme"  │      │ "payment"│
     │           └────┬─────┘      └────┬─────┘
     │                │                  │
     │                └────────┬─────────┘
     │                         │
     │                         ▼
     │                   ┌──────────┐
     │                   │ Contract │
     └──────────────────▶│  "NDA"   │
        EXTRACTED_FROM   └──────────┘
```

### Chunk Metadata

Each chunk stores:
- `text`: Full chunk content
- `chunk_index`: Sequential position (0, 1, 2...)
- `page_number`: Source PDF page
- `section_heading`: Detected section (e.g., "ARTICLE 5: TERMINATION")
- `temporal_refs`: Dates and durations found (JSON)
- `key_terms`: Important terms extracted (JSON)
- `word_count`, `char_count`: Statistics

### Benefits for Retrieval

1. **Source Linking**: When you find an entity, follow `EXTRACTED_FROM` to get the original text
2. **Context Expansion**: Use `NEXT_CHUNK`/`PREV_CHUNK` to get surrounding text
3. **Page Citations**: Include page numbers in answers
4. **Section Context**: Know which section content came from
5. **Multi-Signal Search**: Combine graph traversal with text search

### Example Retrieval Flow

```
User Query: "What are the payment terms?"
                    │
                    ▼
┌─────────────────────────────────────────┐
│ 1. Graph Search: Find "Clause" entities │
│    with type = "payment"                │
│                                         │
│    → Clause { id: "c1", type: "payment"}│
└────────────────────┬────────────────────┘
                     │
                     ▼ Follow EXTRACTED_FROM
┌─────────────────────────────────────────┐
│ 2. Get Source Chunk                     │
│                                         │
│    → Chunk { text: "Payment due within  │
│      30 days...", page: 5 }             │
└────────────────────┬────────────────────┘
                     │
                     ▼ Follow PREV/NEXT
┌─────────────────────────────────────────┐
│ 3. Expand Context                       │
│                                         │
│    → Chunk 4: "... ARTICLE 7: PAYMENT"  │
│    → Chunk 5: "Payment due within..."   │
│    → Chunk 6: "... invoice date."       │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│ 4. Build Rich Context for LLM          │
│                                         │
│    Section: ARTICLE 7: PAYMENT          │
│    [Page 5]                             │
│    Payment is due within 30 days of     │
│    invoice date...                      │
└─────────────────────────────────────────┘
```

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

## Step-by-Step Flow Guides

### 📤 Document Ingestion Flow (Backend)

This is what happens when a user uploads a document:

```
STEP 1: User uploads PDF file
  └─ [USER INPUT] File bytes + filename

STEP 2: Parse PDF
  └─ [LIBRARY: PyMuPDF]
  └─ Input:  PDF bytes
  └─ Output: {full_text, pages[], metadata}
  └─ Logic:  Extract text per page, track char offsets

STEP 3: Create text chunks
  └─ [LOGIC: Chunker]
  └─ Input:  full_text + strategy.chunking
  └─ Output: TextChunk[] with {id, text, start_char, end_char, page_number}
  └─ Logic:  
     ├─ IF strategy="semantic" → Split by sections, then paragraphs
     ├─ IF strategy="fixed"    → Split every N chars with overlap
     └─ IF strategy="sentence" → Split on sentence boundaries

STEP 4: For EACH chunk → Extract entities + metadata (LLM)
  └─ [LLM CALL - per chunk]
  │
  ├── STEP 4a: Build extraction prompt
  │   └─ [LOGIC: Prompt Builder]
  │   └─ Input:  Schema YAML + chunk_text + ExtractionStrategy
  │   └─ Output: Prompt string asking for entities + metadata
  │
  ├── STEP 4b: Call LLM
  │   └─ [LLM CALL: extraction_model]
  │   └─ Input:  Prompt from 4a
  │   └─ Output: JSON with {entities, relationships, metadata}
  │
  └── STEP 4c: Parse LLM response
      └─ [LOGIC: JSON Parser + Validation]
      └─ Input:  LLM JSON response
      └─ Output: DynamicGraph + ChunkMetadata
      └─ Logic:
         ├─ Parse entities → DynamicEntity[]
         ├─ Parse relationships → DynamicRelationship[]
         ├─ Parse metadata → {section_heading, temporal_refs, key_terms}
         └─ Validate against schema

STEP 5: Apply metadata to chunks
  └─ [LOGIC]
  └─ Input:  TextChunk[] + ChunkMetadata[]
  └─ Output: Enriched TextChunk[] with section, temporal refs, etc.

STEP 6: Store in Neo4j (conditional)
  │
  ├── STEP 6a: IF strategy.chunks.enabled
  │   └─ [DB WRITE: Neo4j]
  │   └─ Create Document node
  │   └─ Create Chunk nodes (with metadata)
  │   └─ IF strategy.chunk_linking.sequential → Create NEXT/PREV relationships
  │   └─ IF strategy.chunk_linking.to_document → Create FROM_DOCUMENT relationships
  │
  ├── STEP 6b: Store entities
  │   └─ [DB WRITE: Neo4j]
  │   └─ MERGE nodes by entity_type and id
  │
  ├── STEP 6c: Store relationships
  │   └─ [DB WRITE: Neo4j]
  │   └─ CREATE relationships between entities
  │
  └── STEP 6d: IF strategy.entity_linking.enabled
      └─ [DB WRITE: Neo4j]
      └─ Create EXTRACTED_FROM relationships (entity → chunk)

STEP 7: Return result
  └─ [API RESPONSE]
  └─ Output: {document_id, entity_count, relationship_count, chunk_count}
```

---

### 🔍 Query/RAG Flow (Backend)

This is what happens when a user asks a question:

```
STEP 1: User asks question
  └─ [USER INPUT] Query string (e.g., "What are the payment terms?")

STEP 2: Analyze query (LLM)
  └─ [LLM CALL: query_analysis]
  └─ Input:  User query + Schema info
  └─ Output: {
       intent: "find_clause",
       entity_types: ["Clause", "Contract"],
       relationships: ["HAS_CLAUSE"],
       filters: {"clause_type": "payment"},
       temporal_hints: []
     }

STEP 3: Multi-signal retrieval (conditional based on RetrievalStrategy)
  │
  ├── STEP 3a: IF strategy.search.graph_traversal.enabled
  │   └─ [DB READ: Neo4j]
  │   └─ Query: Find entities matching analysis
  │   └─ Query: Traverse relationships (max_depth from strategy)
  │   └─ Output: Entity[] with relationships
  │
  ├── STEP 3b: IF strategy.search.chunk_text_search.enabled
  │   └─ [DB READ: Neo4j]
  │   └─ Query: Full-text search on Chunk.text
  │   │   ├─ IF method="contains" → WHERE c.text CONTAINS $query
  │   │   ├─ IF method="fulltext" → Use Neo4j full-text index
  │   │   └─ IF method="regex"    → WHERE c.text =~ $pattern
  │   └─ Output: Chunk[] matching text
  │
  ├── STEP 3c: IF strategy.search.keyword_matching.enabled
  │   └─ [DB READ: Neo4j]
  │   └─ Query: Match query words against Chunk.key_terms
  │   └─ Logic: Score by term overlap
  │   └─ Output: Chunk[] with keyword matches
  │
  └── STEP 3d: IF strategy.search.temporal_filtering.enabled
      └─ [LOGIC + DB READ]
      └─ Logic: Detect dates in query (e.g., "in 2024")
      └─ Query: Filter chunks by temporal_refs
      └─ Output: Chunk[] within date range

STEP 4: Deduplicate and score results
  └─ [LOGIC: Scoring]
  └─ Input:  Results from 3a-3d
  └─ Logic:
     ├─ Deduplicate by entity/chunk ID
     ├─ Score = (graph_weight × graph_score) + (text_weight × text_score)
     ├─ Filter by strategy.scoring.entity_confidence_min
     └─ Sort by score descending
  └─ Output: Ranked Entity[] + Chunk[]

STEP 5: Expand context (conditional)
  └─ [DB READ: Neo4j] IF strategy.context.expand_neighbors.enabled
  └─ Query: For each matched chunk, get PREV/NEXT neighbors
  │   └─ strategy.context.expand_neighbors.before chunks before
  │   └─ strategy.context.expand_neighbors.after chunks after
  └─ Output: Expanded Chunk[] with surrounding context

STEP 6: Apply limits
  └─ [LOGIC]
  └─ Input:  All retrieved entities and chunks
  └─ Logic:
     ├─ Limit entities to strategy.limits.max_entities
     ├─ Limit chunks to strategy.limits.max_chunks
     └─ Truncate if total tokens > strategy.limits.max_context_tokens
  └─ Output: Trimmed context

STEP 7: Format context for LLM
  └─ [LOGIC: ContextBuilder]
  └─ Input:  Entities + Chunks + Relationships
  └─ Output: Formatted text string
  └─ Format:
     ```
     # Retrieved Context for Query: "What are the payment terms?"
     
     ## Relevant Document Snippets
     --- Chunk 12 (Page 5) - Section: ARTICLE 7: PAYMENT
     Payment is due within 30 days of invoice date...
     
     ## Extracted Clauses
     ### Payment (Clause)
     - type: payment
     - description: Net 30 payment terms
     
     ## Relationships
     - Contract_1 --[HAS_CLAUSE]--> Clause_payment_1
     ```

STEP 8: Generate answer (LLM)
  └─ [LLM CALL: generation_model]
  └─ Input:  Context from Step 7 + Original query
  └─ Prompt: "Based on this context, answer: {query}"
  └─ Output: Natural language answer

STEP 9: Format response
  └─ [LOGIC]
  └─ Output: {
       answer: "Payment is due within 30 days...",
       sources: [{page: 5, section: "ARTICLE 7"}],
       entities_used: ["Clause_payment_1"],
       confidence: 0.92
     }

STEP 10: Return to user
  └─ [API RESPONSE]
```

---

### 🖥️ Frontend User Interaction Flow

This shows the frontend components and their interactions:

```
═══════════════════════════════════════════════════════════════════════════════
                              APP INITIALIZATION
═══════════════════════════════════════════════════════════════════════════════

STEP 1: App loads
  └─ [REACT: main.tsx]
  └─ Renders <App /> component

STEP 2: Initialize state
  └─ [ZUSTAND: store/index.ts]
  └─ Sets initial state: {activeTab, messages[], documents[], graphData}

STEP 3: Health check
  └─ [API CALL: GET /health]
  └─ Response: {status, neo4j, llm}
  │
  └─ BRANCH on health status:
     ├─ IF all healthy    → Show green indicators
     ├─ IF neo4j unhealthy → Show warning, disable graph features
     └─ IF llm unhealthy   → Show warning, disable upload/query

═══════════════════════════════════════════════════════════════════════════════
                              DOCUMENT UPLOAD FLOW
═══════════════════════════════════════════════════════════════════════════════

STEP 1: User selects "Upload" tab
  └─ [USER CLICK]
  └─ [STATE UPDATE] activeTab = "upload"
  └─ [RENDER] <DocumentUpload /> component

STEP 2: User drops/selects PDF file
  └─ [USER INPUT: file]
  └─ [LOCAL VALIDATION]
     ├─ Check file type is PDF
     └─ Check file size < limit

STEP 3: Upload file to backend
  └─ [API CALL: POST /upload/document]
  └─ Body: FormData with file
  └─ [STATE UPDATE] uploadProgress = 0%

STEP 4: Poll for status (while processing)
  └─ [API CALL: GET /upload/status/{document_id}] (polling every 1s)
  └─ Response: {status, progress, chunks_processed}
  │
  └─ BRANCH on status:
     ├─ IF "parsing"    → Show "Parsing PDF..."
     ├─ IF "chunking"   → Show "Creating chunks..."
     ├─ IF "extracting" → Show "Extracting entities... X/Y chunks"
     ├─ IF "storing"    → Show "Storing in graph..."
     ├─ IF "completed"  → Go to STEP 5
     └─ IF "failed"     → Show error message

STEP 5: Upload complete
  └─ [API RESPONSE] {document_id, entities, relationships}
  └─ [STATE UPDATE] documents.push(new_doc)
  └─ [UI UPDATE] Show success + stats

═══════════════════════════════════════════════════════════════════════════════
                                QUERY FLOW
═══════════════════════════════════════════════════════════════════════════════

STEP 1: User selects "Query" tab
  └─ [USER CLICK]
  └─ [STATE UPDATE] activeTab = "chat"
  └─ [RENDER] <QueryChat /> component

STEP 2: User types question
  └─ [USER INPUT: text]
  └─ [LOCAL STATE] inputText = "What are the payment terms?"

STEP 3: User submits (Enter or click)
  └─ [USER CLICK/KEYPRESS]
  └─ [STATE UPDATE] messages.push({role: "user", content: inputText})
  └─ [STATE UPDATE] isLoading = true
  └─ [UI UPDATE] Show user message + loading indicator

STEP 4: Send query to backend
  └─ [API CALL: POST /query]
  └─ Body: {query: "What are the payment terms?", document_id: optional}

STEP 5: Receive response
  └─ [API RESPONSE] {answer, sources, entities_used}
  └─ [STATE UPDATE] isLoading = false
  └─ [STATE UPDATE] messages.push({role: "assistant", content: answer, sources})
  └─ [UI UPDATE] Render answer with source citations

STEP 6: User clicks source citation (optional)
  └─ [USER CLICK]
  │
  └─ BRANCH on action:
     ├─ IF page citation → Highlight in document viewer
     └─ IF entity link   → Switch to Graph tab, highlight entity

═══════════════════════════════════════════════════════════════════════════════
                              GRAPH VISUALIZATION FLOW
═══════════════════════════════════════════════════════════════════════════════

STEP 1: User selects "Graph" tab
  └─ [USER CLICK]
  └─ [STATE UPDATE] activeTab = "graph"
  └─ [RENDER] <GraphVisualization /> component

STEP 2: Fetch graph data
  └─ [API CALL: GET /graph/all]
  └─ Response: {nodes: [], edges: [], stats: {}}
  └─ [STATE UPDATE] graphData = response

STEP 3: Render graph
  └─ [LIBRARY: react-force-graph or vis-network]
  └─ Input: nodes[] with {id, label, type, color}
  └─ Input: edges[] with {source, target, relationship}
  └─ Output: Interactive force-directed graph

STEP 4: User interactions
  │
  ├─ STEP 4a: User hovers on node
  │   └─ [USER HOVER]
  │   └─ [UI UPDATE] Show tooltip with entity properties
  │
  ├─ STEP 4b: User clicks on node
  │   └─ [USER CLICK]
  │   └─ [API CALL: GET /graph/entity/{id}]
  │   └─ [UI UPDATE] Show detail panel with all properties
  │
  ├─ STEP 4c: User drags node
  │   └─ [USER DRAG]
  │   └─ [LOCAL STATE] Update node position
  │
  └─ STEP 4d: User zooms/pans
      └─ [USER SCROLL/DRAG]
      └─ [LOCAL STATE] Update viewport

STEP 5: Filter graph (optional)
  └─ [USER INPUT: filter controls]
  │
  └─ BRANCH on filter type:
     ├─ IF entity type filter → Filter nodes by type
     ├─ IF relationship filter → Filter edges by type
     └─ IF document filter → Show only entities from selected document

═══════════════════════════════════════════════════════════════════════════════
                              STRATEGY CONFIGURATION FLOW
═══════════════════════════════════════════════════════════════════════════════

STEP 1: User opens Strategy Panel
  └─ [USER CLICK] Expand strategy panel in sidebar
  └─ [API CALL: GET /strategies/extraction]
  └─ [API CALL: GET /strategies/retrieval]
  └─ [API CALL: GET /strategies/presets]
  └─ [STATE UPDATE] Load current strategies + available presets

STEP 2: User interaction options
  │
  ├─ STEP 2a: User selects preset
  │   └─ [USER CLICK] e.g., "Comprehensive" button
  │   └─ [API CALL: POST /strategies/preset] {name: "comprehensive"}
  │   └─ [STATE UPDATE] Refresh strategies
  │   └─ [UI UPDATE] Highlight active preset
  │
  ├─ STEP 2b: User toggles individual setting
  │   └─ [USER CLICK] e.g., toggle "temporal_references.enabled"
  │   └─ [API CALL: PATCH /strategies/extraction]
  │       Body: {updates: {metadata: {temporal_references: {enabled: false}}}}
  │   └─ [STATE UPDATE] Update local strategy state
  │   └─ [UI UPDATE] Mark preset as "Custom"
  │
  └─ STEP 2c: User clicks "Reset to Defaults"
      └─ [USER CLICK]
      └─ [API CALL: POST /strategies/reset]
      └─ [STATE UPDATE] Reload default strategies

STEP 3: Changes take effect
  └─ [NOTE] Strategy changes affect NEXT upload/query operations
  └─ Existing data is not re-processed
```

---

### 🔄 Quick Reference: What Calls LLM?

| Operation | LLM Calls | Model Used |
|-----------|-----------|------------|
| **Document Upload** | 1 per chunk | `extraction_model` |
| **Query** | 2 total | `query_model` (analysis) + `generation_model` (answer) |
| **Graph View** | 0 | Pure database read |
| **Strategy Change** | 0 | Configuration only |
| **Health Check** | 0-1 | Optional LLM ping |

---

### 🔄 Quick Reference: What Writes to Neo4j?

| Operation | Writes | What's Written |
|-----------|--------|----------------|
| **Document Upload** | Yes | Document, Chunks, Entities, Relationships |
| **Query** | No | Read-only |
| **Graph View** | No | Read-only |
| **Strategy Change** | No | In-memory only |

---

## What's Next?

- Read [FRONTEND_GUIDE.md](./FRONTEND_GUIDE.md) to understand the React frontend
- Read [KNOWLEDGE_GRAPH_GUIDE.md](./KNOWLEDGE_GRAPH_GUIDE.md) for graph concepts
- Read [MAKEFILE_GUIDE.md](./MAKEFILE_GUIDE.md) for all make commands
- Try creating your own schema in `schemas/`
