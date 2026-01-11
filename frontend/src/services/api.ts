import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
export interface CypherQueryInfo {
  description: string;
  query: string;
  params: Record<string, unknown>;
  result_count: number;
  execution_time_ms: number;
}

export interface DebugInfo {
  query_analysis?: {
    intent?: string;
    entity_types?: string[];
    keywords?: string[];
    has_temporal_aspect?: boolean;
    search_text?: string;
  };
  cypher_queries: CypherQueryInfo[];
  retrieval_results: {
    entities: Array<Record<string, unknown>>;
    chunks: Array<{
      id: string;
      text: string;
      page_number?: number;
      section_heading?: string;
      key_terms?: string[];
    }>;
    entity_count: number;
    chunk_count: number;
  };
  search_methods_used: string[];
}

export interface QueryResponse {
  question: string;
  answer: string;
  sources: Source[];
  confidence: number;
  follow_up_questions?: string[];
  metadata: {
    retrieval_time_ms: number;
    generation_time_ms: number;
    total_time_ms: number;
    entities_retrieved: number;
  };
  debug_info?: DebugInfo;
}

export interface Source {
  id: string;
  type: string;
  title?: string;
  name?: string;
  [key: string]: unknown; // Schema-agnostic: allow any properties
}

export interface GraphStats {
  total_nodes: number;
  total_relationships: number;
  node_counts: Record<string, number>;
  schema_name?: string;
  
  // New structured format
  entities?: {
    total: number;
    by_type: Record<string, number>;
  };
  entity_relationships?: {
    total: number;
    by_type: Record<string, number>;
  };
  infrastructure?: {
    documents: number;
    chunks: number;
    relationships: {
      total: number;
      by_type: Record<string, number>;
    };
  };
}

export interface GraphVisualization {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphNode {
  id: string;
  _label: string;
  name?: string;
  title?: string;
  [key: string]: unknown;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

export interface UploadResponse {
  success: boolean;
  document_id: string;
  filename: string;
  message: string;
  status: string;
  schema_used?: string;
  entities_extracted: number;
  relationships_extracted: number;
  chunks_created: number;
  pages_parsed: number;
}

// Schema-agnostic entity - any entity type from any schema
export interface Entity {
  id: string;
  _label?: string;
  name?: string;
  title?: string;
  [key: string]: unknown;
}

// Schema-agnostic extraction result
export interface ExtractionResult {
  success: boolean;
  schema_name: string;
  entity_count: number;
  relationship_count: number;
  validation: {
    is_valid: boolean;
    errors: string[];
    warnings: string[];
  };
  // Dynamic entities grouped by type (keys come from schema)
  entities: Record<string, Entity[]>;
  relationships: Array<{
    id: string;
    type: string;
    source_id: string;
    target_id: string;
    [key: string]: unknown;
  }>;
}

// Schema definition from backend
export interface SchemaInfo {
  name: string;
  version: string;
  description: string;
  entity_types: string[];
  relationship_types: string[];
}

export interface EntityDefinition {
  name: string;
  description: string;
  properties: Array<{
    name: string;
    type: string;
    required: boolean;
    description?: string;
  }>;
}

// API functions
export const queryAPI = {
  ask: async (question: string, documentId?: string): Promise<QueryResponse> => {
    const response = await api.post('/query/ask', {
      question,
      document_id: documentId,  // Schema-agnostic: use document_id
      include_follow_ups: true,
      use_history: true,
    });
    return response.data;
  },

  summarize: async (documentId: string) => {
    const response = await api.post('/query/summarize', { document_id: documentId });
    return response.data;
  },

  getHistory: async () => {
    const response = await api.get('/query/history');
    return response.data;
  },

  clearHistory: async () => {
    const response = await api.post('/query/clear-history');
    return response.data;
  },
};

export const uploadAPI = {
  uploadDocument: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/upload/document', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  uploadText: async (text: string, documentName: string) => {
    const response = await api.post('/upload/text', null, {
      params: { text, document_name: documentName },
    });
    return response.data;
  },

  getStatus: async (documentId: string) => {
    const response = await api.get(`/upload/status/${documentId}`);
    return response.data;
  },

  listIngestions: async () => {
    const response = await api.get('/upload/list');
    return response.data;
  },
};

export const graphAPI = {
  getStats: async (): Promise<GraphStats> => {
    const response = await api.get('/graph/stats');
    return response.data;
  },

  getVisualization: async (limit = 100): Promise<GraphVisualization> => {
    const response = await api.get('/graph/visualization', {
      params: { limit },
    });
    return response.data;
  },

  // Schema-agnostic entity operations
  listEntities: async (entityType: string, limit = 100) => {
    const response = await api.get(`/graph/entities/${entityType}`, {
      params: { limit },
    });
    return response.data;
  },

  getEntity: async (entityType: string, entityId: string) => {
    const response = await api.get(`/graph/entities/${entityType}/${entityId}`);
    return response.data;
  },

  getEntityWithRelated: async (entityType: string, entityId: string) => {
    const response = await api.get(`/graph/entities/${entityType}/${entityId}/related`);
    return response.data;
  },

  searchEntities: async (query: string, entityType?: string, limit = 50) => {
    const response = await api.get('/graph/search', {
      params: { query, entity_type: entityType, limit },
    });
    return response.data;
  },

  deleteEntity: async (entityType: string, entityId: string) => {
    const response = await api.delete(`/graph/entities/${entityType}/${entityId}`);
    return response.data;
  },

  clearAll: async () => {
    const response = await api.delete('/graph/all');
    return response.data;
  },

  // Schema information
  getSchema: async (): Promise<{
    active_schema: string;
    schema_version: string;
    schema_description: string;
    defined_entities: string[];
    defined_relationships: string[];
    database_labels: string[];
    database_relationships: string[];
  }> => {
    const response = await api.get('/graph/schema');
    return response.data;
  },

  getSchemaEntities: async (): Promise<{
    schema_name: string;
    entities: EntityDefinition[];
  }> => {
    const response = await api.get('/graph/schema/entities');
    return response.data;
  },

  getSchemaRelationships: async () => {
    const response = await api.get('/graph/schema/relationships');
    return response.data;
  },
};

export const extractionAPI = {
  // Extract entities from text using active schema
  extract: async (text: string, entityTypes?: string[]): Promise<ExtractionResult> => {
    const response = await api.post('/extraction/extract', {
      text,
      entity_types: entityTypes,
    });
    return response.data;
  },

  // Get available entity types from the active schema
  getEntityTypes: async (): Promise<string[]> => {
    const schema = await graphAPI.getSchema();
    return schema.defined_entities;
  },

  // Get schema definition for extraction guidance
  getSchemaInfo: async () => {
    return graphAPI.getSchemaEntities();
  },
};

export interface HealthResponse {
  status: 'healthy' | 'unhealthy' | 'degraded';
  timestamp: string;
  version: string;
  services: {
    [key: string]: {
      name: string;
      status: string;
      message?: string;
      latency_ms?: number;
    };
  };
  schema?: {
    name: string;
    version: string;
    entity_count: number;
    relationship_count: number;
  };
}

export interface ReadinessResponse {
  ready: boolean;
  checks: {
    neo4j: boolean;
    schema: boolean;
  };
}

export const healthAPI = {
  // Main health check
  check: async (): Promise<HealthResponse> => {
    const response = await api.get('/health');
    return response.data;
  },

  // Kubernetes-style readiness probe
  ready: async (): Promise<ReadinessResponse> => {
    const response = await api.get('/health/ready');
    return response.data;
  },

  // Kubernetes-style liveness probe
  live: async (): Promise<{ alive: boolean; timestamp: string }> => {
    const response = await api.get('/health/live');
    return response.data;
  },

  // Neo4j specific health
  neo4j: async () => {
    const response = await api.get('/health/neo4j');
    return response.data;
  },

  // Get configuration
  getConfig: async () => {
    const response = await api.get('/health/config');
    return response.data;
  },

  // Get available schemas
  getSchemas: async () => {
    const response = await api.get('/health/schemas');
    return response.data;
  },
};

// Strategy types
export interface StrategyStatus {
  current_preset: string | null;
  extraction: {
    name: string;
    description: string;
    chunks_enabled: boolean;
    metadata_enabled: {
      page_numbers: boolean;
      section_headings: boolean;
      temporal_references: boolean;
      key_terms: boolean;
    };
    entity_linking: boolean;
    validation: {
      mode: 'ignore' | 'warn' | 'store_valid' | 'strict';
      log_level: string;
    };
  };
  retrieval: {
    name: string;
    description: string;
    search_methods: {
      graph_traversal: boolean;
      chunk_text_search: boolean;
      keyword_matching: boolean;
      temporal_filtering: boolean;
    };
    context_expansion: boolean;
  };
}

export interface PresetInfo {
  name: string;
  extraction_description: string;
  retrieval_description: string;
}

export const strategyAPI = {
  // Get current strategy status
  getStatus: async (): Promise<StrategyStatus> => {
    const response = await api.get('/strategies');
    return response.data;
  },

  // Get available presets
  getPresets: async (): Promise<PresetInfo[]> => {
    const response = await api.get('/strategies/presets');
    return response.data;
  },

  // Load a preset
  loadPreset: async (presetName: string) => {
    const response = await api.post('/strategies/preset', { name: presetName });
    return response.data;
  },

  // Get extraction strategy details
  getExtraction: async () => {
    const response = await api.get('/strategies/extraction');
    return response.data;
  },

  // Update extraction strategy
  updateExtraction: async (updates: Record<string, unknown>) => {
    const response = await api.patch('/strategies/extraction', { updates });
    return response.data;
  },

  // Get retrieval strategy details
  getRetrieval: async () => {
    const response = await api.get('/strategies/retrieval');
    return response.data;
  },

  // Update retrieval strategy
  updateRetrieval: async (updates: Record<string, unknown>) => {
    const response = await api.patch('/strategies/retrieval', { updates });
    return response.data;
  },

  // Get combined strategy
  getCombined: async () => {
    const response = await api.get('/strategies/combined');
    return response.data;
  },

  // Reset strategies to defaults
  reset: async () => {
    const response = await api.post('/strategies/reset');
    return response.data;
  },
};

export default api;
