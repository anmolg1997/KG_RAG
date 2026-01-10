# KG-RAG: Knowledge Graph-based RAG System

A **schema-agnostic** Knowledge Graph-based Retrieval Augmented Generation (RAG) system for understanding and querying documents of any type.

![Architecture](https://img.shields.io/badge/Architecture-Knowledge_Graph_RAG-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![React](https://img.shields.io/badge/React-18-blue)
![Neo4j](https://img.shields.io/badge/Neo4j-Community-green)
![Schema](https://img.shields.io/badge/Schema-Agnostic-orange)

[![Author](https://img.shields.io/badge/Author-Anmol_Jaiswal-purple?style=flat)](https://www.linkedin.com/in/anmol-8756772501/)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=flat&logo=linkedin)](https://www.linkedin.com/in/anmol-8756772501/)

---

## 📚 Learning Path

New to this project? Follow this learning path:

### 1️⃣ Understand Knowledge Graphs
Start here if you're new to knowledge graphs:
- 📖 Read [docs/KNOWLEDGE_GRAPH_GUIDE.md](docs/KNOWLEDGE_GRAPH_GUIDE.md)
- Learn what nodes, edges, and relationships are
- Understand why KG is better than simple vector search for structured data

### 2️⃣ Understand the Architecture
See how all pieces fit together:
- 📖 Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Follow the data flow from upload → extraction → storage → query
- Understand each module's responsibility

### 3️⃣ Understand the Schema System
Learn how to customize for any document type:
- 📖 Read [schemas/README.md](schemas/README.md)
- Look at `schemas/contract.yaml` as an example
- Create your own schema

### 4️⃣ Understand the Frontend (Optional)
If you want to modify the UI:
- 📖 Read [docs/FRONTEND_GUIDE.md](docs/FRONTEND_GUIDE.md)
- Learn React, Vite, and Tailwind basics
- Understand component structure

---

## 🎯 Key Feature: Schema-Agnostic Design

**What does "schema-agnostic" mean?**

Instead of hardcoding entity types (Contract, Party, Clause...), you define them in YAML:

```yaml
# schemas/contract.yaml - for legal documents
entities:
  - name: Contract
    properties:
      - name: title
        type: string
        required: true

# schemas/research_paper.yaml - for academic papers
entities:
  - name: Paper
    properties:
      - name: title
        type: string
```

**To process a different document type:**
1. Create a new YAML schema file
2. Set `ACTIVE_SCHEMA=your_schema` in `.env`
3. That's it! The system adapts automatically.

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                            │
│                  React + Vite + Tailwind                         │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐     │
│  │  Upload   │  │   Query   │  │   Graph   │  │  Extract  │     │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘     │
└──────────────────────────────────────────────────────────────────┘
                              │ REST API
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                         BACKEND                                   │
│                    FastAPI + Python                               │
│                                                                   │
│  ┌────────────────┐  ┌─────────────────┐  ┌──────────────────┐  │
│  │   INGESTION    │  │   EXTRACTION    │  │       RAG        │  │
│  │   PDF → Text   │  │  Schema-driven  │  │  Query → Answer  │  │
│  │   Chunking     │  │  LLM extraction │  │  Graph retrieval │  │
│  └────────────────┘  └─────────────────┘  └──────────────────┘  │
│                              │                    │              │
└──────────────────────────────┼────────────────────┼──────────────┘
                               │                    │
        ┌──────────────────────┘                    │
        ▼                                           ▼
┌───────────────────┐                    ┌─────────────────────┐
│   SCHEMA FILES    │                    │      NEO4J          │
│   (YAML)          │                    │   Graph Database    │
│                   │                    │                     │
│ • contract.yaml   │                    │  Nodes & Edges      │
│ • research.yaml   │                    │  Cypher Queries     │
│ • your_schema.yaml│                    │                     │
└───────────────────┘                    └─────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for Neo4j)
- [uv](https://github.com/astral-sh/uv) (fast Python package manager)

### Using Makefile (Recommended)

```bash
# One-command setup
make setup

# Start development servers
make dev

# Check health of all services
make health
```

### 1. Start Neo4j

```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:community
```

### 2. Setup Backend (using uv)

```bash
cd backend

# Create virtual environment with uv (faster than pip!)
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt

# Copy and configure environment
cp ../env.example .env
# Edit .env - add your OPENAI_API_KEY

# Run backend
uvicorn app.main:app --reload
```

> **Note**: We use [uv](https://github.com/astral-sh/uv) - a fast Python package installer.
> Install it with: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### 3. Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### 4. Access Application

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:5173 | Web interface |
| Backend API | http://localhost:8000 | REST API |
| API Docs | http://localhost:8000/docs | Interactive docs |
| Neo4j Browser | http://localhost:7474 | Database explorer |

---

## 📁 Project Structure

```
KG_RAG/
│
├── schemas/                    # 🎯 DEFINE YOUR DOCUMENT TYPES HERE
│   ├── contract.yaml           # Legal contracts schema
│   ├── research_paper.yaml     # Academic papers schema
│   └── README.md               # How to create schemas
│
├── backend/
│   └── app/
│       ├── schema/             # Schema loading system
│       ├── extraction/         # Entity extraction
│       ├── graph/              # Neo4j operations
│       ├── ingestion/          # PDF processing
│       └── rag/                # RAG pipeline
│
├── frontend/
│   └── src/
│       ├── components/         # React components
│       ├── services/           # API client
│       └── store/              # State management
│
├── docs/                       # 📖 DOCUMENTATION
│   ├── KNOWLEDGE_GRAPH_GUIDE.md
│   ├── ARCHITECTURE.md
│   ├── FRONTEND_GUIDE.md
│   └── MAKEFILE_GUIDE.md
│
└── Makefile                    # 🛠️ Development commands
```

---

## 🔧 Configuration

Create a `.env` file in the backend directory:

```bash
# Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# LLM (pick one or more)
DEFAULT_LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# OLLAMA_BASE_URL=http://localhost:11434

# Schema - change this to use different document types!
ACTIVE_SCHEMA=contract

# Processing
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

---

## 🔄 Switching Document Types

### To analyze contracts (default):
```bash
ACTIVE_SCHEMA=contract
```

### To analyze research papers:
```bash
ACTIVE_SCHEMA=research_paper
```

### To analyze your custom documents:
1. Create `schemas/my_documents.yaml`
2. Define your entities and relationships
3. Set `ACTIVE_SCHEMA=my_documents`
4. Restart the backend

---

## 📖 API Reference

### Upload Document
```bash
POST /upload/document
Content-Type: multipart/form-data

file: <PDF file>
```

### Ask Question
```bash
POST /query/ask
Content-Type: application/json

{
    "question": "What are the payment terms?",
    "contract_id": "optional-id"
}
```

### Get Graph Statistics
```bash
GET /graph/stats
```

### Health Check
```bash
GET /health           # Full health status
GET /health/ready     # Kubernetes readiness probe
GET /health/live      # Kubernetes liveness probe
GET /health/neo4j     # Neo4j specific health
GET /health/schemas   # Available schemas
```

### Extract from Text
```bash
POST /extraction/extract
Content-Type: application/json

{
    "text": "Your document text...",
    "entity_types": ["Contract", "Party"]  // optional filter
}
```

---

## 🐳 Docker Deployment

```bash
# Set API keys
export OPENAI_API_KEY=your_key

# Start all services
docker-compose up -d

# Access at http://localhost:5173
```

---

## 🎓 Understanding the Flow

### Document Processing Flow
```
PDF Upload → Parse Text → Chunk → Extract Entities → Store in Neo4j
```

### Query Flow
```
Question → Understand Intent → Query Graph → Generate Answer
```

### Schema Flow
```
YAML Schema → Load & Validate → Generate Prompts → Guide Extraction
```

---

## 🛠️ Extending the System

### Add New Entity Type

Edit your schema YAML:
```yaml
entities:
  - name: MyNewEntity
    description: "What this entity represents"
    properties:
      - name: my_property
        type: string
        required: true
```

### Add New Relationship

```yaml
relationships:
  - name: MY_RELATIONSHIP
    source: EntityA
    target: EntityB
    description: "How A relates to B"
```

### Customize Extraction

```yaml
extraction:
  system_prompt: |
    Your custom instructions for the LLM...
  domain_hints:
    - "Look for X in section Y"
    - "Z is usually mentioned with W"
```

---

## 📚 Further Reading

- [Knowledge Graph Guide](docs/KNOWLEDGE_GRAPH_GUIDE.md) - Understanding KGs
- [Architecture Guide](docs/ARCHITECTURE.md) - System design
- [Frontend Guide](docs/FRONTEND_GUIDE.md) - React/Vite/Tailwind
- [Makefile Guide](docs/MAKEFILE_GUIDE.md) - All make commands explained
- [Schema Guide](schemas/README.md) - Creating custom schemas

---

## 👨‍💻 Author

**Anmol Jaiswal** - *Principal AI Engineer*

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Anmol_Jaiswal-blue?style=flat&logo=linkedin)](https://www.linkedin.com/in/anmol-8756772501/)
[![Email](https://img.shields.io/badge/Email-the.anmol.jaiswal%40gmail.com-red?style=flat&logo=gmail)](mailto:the.anmol.jaiswal@gmail.com)

- 📧 Email: [the.anmol.jaiswal@gmail.com](mailto:the.anmol.jaiswal@gmail.com)
- 🔗 LinkedIn: [linkedin.com/in/anmol-8756772501](https://www.linkedin.com/in/anmol-8756772501/)
- 📱 Phone: +91-8756772501

---

## 🤝 Contributing

Contributions welcome! Please:
1. Read the documentation first
2. Create a feature branch
3. Add tests if applicable
4. Submit a PR with clear description

---

## 📄 License

MIT License - see LICENSE file for details.
