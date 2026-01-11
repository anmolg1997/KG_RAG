# Knowledge Graph Guide for Beginners

Welcome! This guide will teach you **what knowledge graphs are** and **how they work** in this system, starting from absolute basics.

---

## 📚 Table of Contents

1. [What is a Knowledge Graph?](#what-is-a-knowledge-graph)
2. [Key Concepts](#key-concepts)
3. [Why Use Knowledge Graphs for RAG?](#why-use-knowledge-graphs-for-rag)
4. [How Our System Works](#how-our-system-works)
5. [Neo4j Basics](#neo4j-basics)
6. [Cypher Query Language](#cypher-query-language)
7. [Hands-on Examples](#hands-on-examples)

---

## What is a Knowledge Graph?

### Simple Explanation

Imagine you're organizing information about a **contract**:

**Traditional Database (Tables):**

```
┌─────────────────────────────────────────────┐
│ Contracts Table                             │
├──────┬───────────────┬─────────────┬────────┤
│ ID   │ Title         │ Buyer       │ Seller │
├──────┼───────────────┼─────────────┼────────┤
│ 1    │ License Deal  │ TechStart   │ Acme   │
└──────┴───────────────┴─────────────┴────────┘

┌─────────────────────────────────────────────┐
│ Clauses Table                               │
├──────┬─────────────┬────────────────────────┤
│ ID   │ Contract_ID │ Type                   │
├──────┼─────────────┼────────────────────────┤
│ 1    │ 1           │ Termination            │
│ 2    │ 1           │ Payment                │
└──────┴─────────────┴────────────────────────┘
```

**Knowledge Graph (Nodes & Edges):**

```
                    ┌─────────────────┐
                    │    Contract     │
                    │ "License Deal"  │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │ HAS_PARTY          │ HAS_CLAUSE         │ HAS_PARTY
        ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│    Party      │    │    Clause     │    │    Party      │
│  "TechStart"  │    │ "Termination" │    │    "Acme"     │
│   (buyer)     │    └───────────────┘    │   (seller)    │
└───────────────┘                         └───────────────┘
```

### The Key Difference

| Aspect                  | Traditional DB               | Knowledge Graph               |
| ----------------------- | ---------------------------- | ----------------------------- |
| **Structure**     | Fixed tables with rows       | Flexible nodes & edges        |
| **Relationships** | Foreign keys (indirect)      | First-class citizens (direct) |
| **Schema**        | Rigid, predefined            | Flexible, can evolve          |
| **Queries**       | JOINs across tables          | Graph traversal               |
| **Best for**      | Structured, predictable data | Connected, complex data       |

---

## Key Concepts

### 1. Nodes (Entities)

**Nodes** are the "things" in your graph. Each node has:

- A **label** (type): e.g., `Contract`, `Party`, `Clause`
- **Properties** (attributes): e.g., `name: "Acme"`, `amount: 50000`

```
┌─────────────────────────┐
│       Party             │  ← Label
├─────────────────────────┤
│ name: "Acme Corp"       │  ← Properties
│ type: "corporation"     │
│ role: "seller"          │
└─────────────────────────┘
```

### 2. Edges (Relationships)

**Edges** connect nodes and describe HOW they're related:

- Have a **type**: e.g., `HAS_PARTY`, `CREATES_OBLIGATION`
- Have a **direction**: from source → target
- Can have **properties** too: e.g., `since: "2024-01-01"`

```
┌────────┐                    ┌────────┐
│Contract│ ──HAS_PARTY──────▶ │ Party  │
└────────┘                    └────────┘
```

### 3. Properties

Both nodes and edges can have properties (key-value pairs):

```yaml
Node Properties:
  Contract:
    title: "Software License Agreement"
    effective_date: "2024-01-01"
    status: "active"

Edge Properties:
  HAS_PARTY:
    role: "primary"
    since: "2024-01-01"
```

### 4. Labels

Labels categorize nodes. A node can have multiple labels:

```
(:Contract:LegalDocument)  # This node is both a Contract and a LegalDocument
```

---

## Why Use Knowledge Graphs for RAG?

### The Problem with Traditional RAG

**Standard RAG** (Retrieval-Augmented Generation):

1. Document → Split into chunks
2. Chunks → Convert to vectors (embeddings)
3. Query → Find similar vectors
4. Return similar chunks to LLM

**Limitation**: Only finds **textually similar** content, misses **relationships**.

### Example: Why Relationships Matter

**Document**: "Acme Corp must pay TechStart $50,000 annually."

**User Question**: "What are Acme's payment obligations?"

**Vector Search Result**: Might find chunks about payments, but doesn't know:

- WHO is obligated (Acme)
- TO WHOM (TechStart)
- CONNECTION to specific contract

**Knowledge Graph Result**:

```
Query: Find Obligations where OBLIGATES → Party named "Acme"

Result:
  Obligation {
    type: "payment",
    amount: "$50,000",
    frequency: "annual"
  }
  Connected to:
    - Contract: "Software License Agreement"
    - Beneficiary: "TechStart"
```

### KG-RAG Advantages

| Feature             | Vector RAG | KG-RAG |
| ------------------- | ---------- | ------ |
| Semantic search     | ✅         | ✅     |
| Exact relationships | ❌         | ✅     |
| Multi-hop reasoning | ❌         | ✅     |
| Explainable results | Limited    | ✅     |
| Structured queries  | ❌         | ✅     |

---

## How Our System Works

### Step-by-Step Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER UPLOADS PDF                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: PDF PARSING                                             │
│ ─────────────────                                               │
│ • Extract text from PDF                                         │
│ • Preserve structure (sections, paragraphs)                     │
│ • Extract metadata (title, author, dates)                       │
│                                                                 │
│ Code: backend/app/ingestion/pdf_parser.py                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: TEXT CHUNKING                                           │
│ ─────────────────────                                           │
│ • Split document into manageable pieces                         │
│ • Keep context (overlap between chunks)                         │
│ • Respect boundaries (paragraphs, sections)                     │
│                                                                 │
│ Code: backend/app/ingestion/chunker.py                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: ENTITY EXTRACTION (LLM)                                 │
│ ───────────────────────────────                                 │
│ • Load schema (what entities to extract)                        │
│ • Send chunks to LLM with extraction prompt                     │
│ • LLM returns structured JSON with entities                     │
│ • Validate against schema                                       │
│                                                                 │
│ Schema: schemas/contract.yaml                                   │
│ Code: backend/app/extraction/dynamic_extractor.py               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: GRAPH STORAGE (Neo4j)                                   │
│ ─────────────────────────────                                   │
│ • Create nodes for each entity                                  │
│ • Create edges for relationships                                │
│ • Index for fast queries                                        │
│                                                                 │
│ Code: backend/app/graph/dynamic_repository.py                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         GRAPH IS READY!                         │
└─────────────────────────────────────────────────────────────────┘



┌─────────────────────────────────────────────────────────────────┐
│                      USER ASKS QUESTION                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: QUERY UNDERSTANDING                                     │
│ ───────────────────────────                                     │
│ • Analyze user's question                                       │
│ • Identify relevant entity types                                │
│ • Determine relationships to traverse                           │
│                                                                 │
│ Code: backend/app/rag/retriever.py                              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: GRAPH RETRIEVAL                                         │
│ ───────────────────────                                         │
│ • Query Neo4j for relevant nodes                                │
│ • Follow relationships to gather context                        │
│ • Format as text for LLM                                        │
│                                                                 │
│ Code: backend/app/rag/retriever.py                              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 7: RESPONSE GENERATION                                     │
│ ───────────────────────────                                     │
│ • Combine question + retrieved context                          │
│ • Send to LLM for answer generation                             │
│ • Include source citations                                      │
│                                                                 │
│ Code: backend/app/rag/generator.py                              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ANSWER RETURNED TO USER                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Neo4j Basics

### What is Neo4j?

Neo4j is a **graph database** - a database specifically designed to store and query graph data (nodes and relationships).

### Why Neo4j?

| Feature                          | Description                                            |
| -------------------------------- | ------------------------------------------------------ |
| **Native Graph Storage**   | Data stored as actual graph, not converted from tables |
| **Cypher Language**        | Intuitive query language for graphs                    |
| **Performance**            | Traversing relationships is O(1), not O(n) JOINs       |
| **ACID Compliance**        | Full transaction support                               |
| **Free Community Edition** | Open source, no cost                                   |

### Accessing Neo4j

Neo4j exposes **two ports** for different purposes:

| Port | Protocol | Purpose |
|------|----------|---------|
| **7474** | HTTP | Web-based Neo4j Browser UI for visual exploration |
| **7687** | Bolt | Binary protocol for application connections (used by our backend) |

**Ways to access your database:**

1. **Local Browser**: http://localhost:7474  
   The traditional Neo4j Browser UI running on your local Docker container.

2. **Hosted Browser**: https://browser.neo4j.io/  
   Neo4j's cloud-hosted browser interface. Connect to any Neo4j instance by entering your connection URL (`bolt://localhost:7687`). Useful when you can't access port 7474 directly.

**Login credentials:**
- Username: `neo4j`
- Password: `password` (or whatever you set in `NEO4J_AUTH`)

---

## Cypher Query Language

Cypher is Neo4j's query language. It's designed to be **visual** - queries look like the patterns you're searching for!

### Basic Syntax

```cypher
-- Find all nodes
MATCH (n) RETURN n

-- The pattern (n) represents "any node"
-- MATCH finds patterns, RETURN shows results
```

### Creating Nodes

```cypher
-- Create a Party node
CREATE (p:Party {name: "Acme Corp", type: "corporation"})
RETURN p

-- :Party is the label
-- {name: "Acme"} are properties
```

### Creating Relationships

```cypher
-- Create contract and party, then connect them
CREATE (c:Contract {title: "License Agreement"})
CREATE (p:Party {name: "Acme Corp"})
CREATE (c)-[:HAS_PARTY]->(p)
RETURN c, p

-- The arrow shows direction: (contract)-->(party)
-- [:HAS_PARTY] is the relationship type
```

### Finding Nodes

```cypher
-- Find all contracts
MATCH (c:Contract)
RETURN c

-- Find contract by title
MATCH (c:Contract {title: "License Agreement"})
RETURN c

-- Find with WHERE clause
MATCH (c:Contract)
WHERE c.status = "active"
RETURN c
```

### Following Relationships

```cypher
-- Find all parties connected to a contract
MATCH (c:Contract)-[:HAS_PARTY]->(p:Party)
RETURN c.title, p.name

-- Find clauses of type "termination"
MATCH (c:Contract)-[:HAS_CLAUSE]->(cl:Clause)
WHERE cl.clause_type = "termination"
RETURN c.title, cl.summary
```

### Multi-Hop Queries

```cypher
-- Find who is obligated by clauses in a contract
MATCH (c:Contract)-[:HAS_CLAUSE]->(cl:Clause)
      -[:CREATES_OBLIGATION]->(o:Obligation)
      -[:OBLIGATES]->(p:Party)
WHERE c.title = "License Agreement"
RETURN p.name, o.description

-- This traverses 3 relationships!
```

### Common Patterns

```cypher
-- Count nodes by type
MATCH (n)
RETURN labels(n)[0] as type, count(*) as count

-- Find shortest path
MATCH path = shortestPath(
  (a:Party {name: "Acme"})-[*]-(b:Party {name: "TechStart"})
)
RETURN path

-- Get all relationships of a node
MATCH (n {id: "some-id"})-[r]-(connected)
RETURN type(r), connected
```

---

## Hands-on Examples

### Example 1: Understanding Extraction

**Input Text:**

```
This License Agreement is between Acme Corp ("Licensor") and TechStart Inc ("Licensee").
The Licensee shall pay $50,000 annually.
```

**Extracted Entities:**

```json
{
  "entities": {
    "Contract": [{
      "id": "contract-1",
      "title": "License Agreement",
      "contract_type": "license"
    }],
    "Party": [
      {"id": "party-1", "name": "Acme Corp", "role": "licensor"},
      {"id": "party-2", "name": "TechStart Inc", "role": "licensee"}
    ],
    "Amount": [{
      "id": "amount-1",
      "value": 50000,
      "currency": "USD",
      "description": "annual payment"
    }]
  },
  "relationships": [
    {"source_id": "contract-1", "target_id": "party-1", "type": "HAS_PARTY"},
    {"source_id": "contract-1", "target_id": "party-2", "type": "HAS_PARTY"},
    {"source_id": "contract-1", "target_id": "amount-1", "type": "HAS_AMOUNT"}
  ]
}
```

### Example 2: Querying the Graph

**User Question:** "What are the payment amounts in this contract?"

**System Process:**

1. **Query Understanding:**

   ```json
   {
     "intent": "find payment information",
     "entity_types": ["Amount", "Obligation"],
     "filters": {"obligation_type": "payment"}
   }
   ```
2. **Cypher Query Generated:**

   ```cypher
   MATCH (c:Contract)-[:HAS_AMOUNT]->(a:Amount)
   RETURN c.title, a.value, a.currency, a.description

   UNION

   MATCH (c:Contract)-[:HAS_CLAUSE]->(cl:Clause)
         -[:CREATES_OBLIGATION]->(o:Obligation)
   WHERE o.obligation_type = "payment"
   RETURN c.title, o.description
   ```
3. **Retrieved Context:**

   ```
   Contract: License Agreement
   Amount: $50,000 USD (annual payment)
   ```
4. **Generated Answer:**

   > "The License Agreement specifies an annual payment of $50,000 USD."
   >

---

## Next Steps

1. **Start Everything with Makefile**:

   ```bash
   make setup    # One-time setup
   make dev      # Start all servers
   make health   # Verify everything is running
   ```
2. **Or manually start Neo4j**:

   ```bash
   docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:community
   ```
3. **Explore Browser**: Open http://localhost:7474 or https://browser.neo4j.io/ and try the Cypher examples
4. **Upload a Document**: Use the frontend to upload a PDF and see entities extracted
5. **Visualize the Graph**: Use the Graph tab to see your knowledge graph
6. **Ask Questions**: Try the Query tab to ask questions about your documents

---

## Glossary

| Term                | Definition                                             |
| ------------------- | ------------------------------------------------------ |
| **Node**      | A point in the graph representing an entity (thing)    |
| **Edge**      | A connection between nodes representing a relationship |
| **Label**     | Category/type of a node (e.g.,`Contract`, `Party`) |
| **Property**  | Attribute stored on a node or edge                     |
| **Cypher**    | Neo4j's graph query language                           |
| **Traversal** | Following edges to find connected nodes                |
| **Index**     | Structure for fast property lookups                    |
| **MATCH**     | Cypher clause to find patterns                         |
| **CREATE**    | Cypher clause to add data                              |
| **RETURN**    | Cypher clause to specify output                        |
