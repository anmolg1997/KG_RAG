# Strategies

This folder contains configuration files for the KG-RAG strategy system.

## Folder Structure

```
strategies/
├── README.md           # This file
└── presets/            # Strategy preset YAML files
    ├── README.md       # Preset documentation
    ├── minimal.yaml    # Minimal extraction preset
    ├── balanced.yaml   # Balanced preset (default)
    └── comprehensive.yaml  # Full-featured preset
```

## What are Strategies?

Strategies control how the KG-RAG system processes documents and retrieves information:

### Extraction Strategy
Controls **document ingestion**:
- Whether to store text chunks as graph nodes
- What metadata to extract (pages, sections, dates, terms)
- How to link entities to source chunks

### Retrieval Strategy  
Controls **query answering**:
- Which search methods to use (graph traversal, text search, keywords)
- How much context to retrieve (neighbor chunks, metadata)
- Scoring weights for ranking results

## Usage

### Via API

```bash
# List available presets
curl http://localhost:8000/strategies/presets

# Load a preset
curl -X POST http://localhost:8000/strategies/preset \
  -H "Content-Type: application/json" \
  -d '{"name": "comprehensive"}'

# Get current strategy
curl http://localhost:8000/strategies

# Update extraction strategy
curl -X PATCH http://localhost:8000/strategies/extraction \
  -H "Content-Type: application/json" \
  -d '{"metadata": {"key_terms": {"enabled": true, "max_terms": 20}}}'
```

### Via Makefile

```bash
# Show current strategy status
make strategy

# List available presets
make strategy-presets

# Load a preset
make strategy-load PRESET=comprehensive

# Reset to default
make strategy-reset
```

### Via Frontend

The Strategy Panel in the frontend UI allows you to:
1. Select from predefined presets
2. Toggle individual features
3. See current configuration

## Creating Custom Strategies

1. Copy an existing preset from `presets/` folder
2. Modify settings as needed
3. Save with a descriptive name
4. Load via API or configure as default

See `presets/README.md` for detailed configuration options.
