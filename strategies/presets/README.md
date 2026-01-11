# Strategy Presets

This folder contains YAML strategy preset files for the KG-RAG system.

## Available Presets

| Preset | Description | Best For |
|--------|-------------|----------|
| `minimal.yaml` | Entities only, no chunks | Quick extraction, small docs |
| `balanced.yaml` | Good mix of features | General purpose (default) |
| `comprehensive.yaml` | All features enabled | Legal, research, complex docs |

## Built-in Presets

The system also has built-in presets defined in Python code:
- `minimal` - Same as minimal.yaml
- `balanced` - Same as balanced.yaml  
- `comprehensive` - Same as comprehensive.yaml
- `speed` - Optimized for fast processing
- `research` - Optimized for academic papers

Load via API: `POST /strategies/preset` with `{"name": "balanced"}`

## Creating Custom Presets

1. Copy an existing YAML file as a template
2. Modify the settings as needed
3. Load via API: `POST /strategies/load-file` with the filename

## Key Configuration Sections

### Extraction Strategy
- `chunks` - Store text chunks as graph nodes
- `chunk_linking` - Link chunks sequentially and to documents
- `metadata` - What metadata to extract (page numbers, sections, temporal refs, key terms)
- `entity_linking` - Link extracted entities back to source chunks

### Retrieval Strategy
- `search` - Which search methods to use (graph, text, keywords, temporal)
- `context` - How to expand context (neighbor chunks, metadata inclusion)
- `scoring` - Weights for different signals
- `limits` - Max results for efficiency

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
