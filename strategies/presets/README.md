# Strategy Presets

This folder contains YAML strategy preset files for the KG-RAG system.

## Available Presets

| Preset | Description | Validation | Best For |
|--------|-------------|------------|----------|
| `minimal.yaml` | Entities only, no chunks | ignore | Quick extraction, small docs |
| `balanced.yaml` | Good mix of features | warn | General purpose (default) |
| `comprehensive.yaml` | All features enabled | store_valid | Legal, research, complex docs |
| `strict.yaml` | Only validated entities | strict | Compliance, regulated data |

## Built-in Presets

The system also has built-in presets defined in Python code:
- `minimal` - Same as minimal.yaml
- `balanced` - Same as balanced.yaml  
- `comprehensive` - Same as comprehensive.yaml
- `speed` - Optimized for fast processing
- `research` - Optimized for academic papers
- `strict` - Only store fully validated entities

Load via API: `POST /strategies/preset` with `{"name": "balanced"}`

## Creating Custom Presets

1. Copy an existing YAML file as a template
2. Modify the settings as needed
3. Load via API: `POST /strategies/load-file` with the filename

## Key Configuration Sections

### Extraction Strategy
- `chunking` - Text splitting settings (size, overlap, strategy)
- `chunks` - Store text chunks as graph nodes
- `chunk_linking` - Link chunks sequentially and to documents
- `metadata` - What metadata to extract (page numbers, sections, temporal refs, key terms)
- `entity_linking` - Link extracted entities back to source chunks
- `validation` - Schema validation behavior (see below)

### Retrieval Strategy
- `search` - Which search methods to use (graph, text, keywords, temporal)
- `context` - How to expand context (neighbor chunks, metadata inclusion)
- `scoring` - Weights for different signals
- `limits` - Max results for efficiency

## Validation Modes

The `validation.mode` setting controls how schema validation is handled:

| Mode | Behavior | Use Case |
|------|----------|----------|
| `ignore` | No validation, store everything | Speed-focused, trusted sources |
| `warn` | Log issues, store everything | General use (default) |
| `store_valid` | Skip invalid entities, store valid ones | Quality-focused |
| `strict` | Block storage if ANY errors | Compliance, regulated data |

**Example validation output in logs:**
```
│  ┌─ Chunk 3/10 (Page 2)
│  │  Section: ARTICLE 5: TERMINATION
│  │  📦 Extracted: 2 Party, 1 Date
│  │  🔗 Relations: 3
│  │
│  │  ⚠️  Validation Issues:
│  │  │  ⚡ WARN: Party 'Acme Corp' missing required property: address
│  │
│  │  ✅ Stored: 3 entities, 3 relationships
│  └─ Done
```

## Example: Custom Legal Contract Preset

```yaml
extraction:
  name: "legal"
  description: "Optimized for legal contracts"
  
  chunks:
    enabled: true
    store_text: true
  
  metadata:
    page_numbers:
      enabled: true
    section_headings:
      enabled: true
      patterns:
        - "^(ARTICLE|SECTION|CLAUSE)\\s+\\d+"
        - "^\\d+\\.\\d+\\s+"
    temporal_references:
      enabled: true
      extract_dates: true
      extract_durations: true
    key_terms:
      enabled: true
      max_terms: 20

retrieval:
  name: "legal"
  search:
    graph_traversal:
      enabled: true
      max_depth: 3
    keyword_matching:
      enabled: true
      match_threshold: 0.3
  context:
    expand_neighbors:
      enabled: true
      before: 2
      after: 2
```
