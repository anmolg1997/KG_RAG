import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
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
}

export interface Source {
  id: string;
  type: string;
  title?: string;
  name?: string;
  clause_type?: string;
}

export interface GraphStats {
  total_nodes: number;
  total_relationships: number;
  node_counts: Record<string, number>;
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
}

export interface Contract {
  id: string;
  title: string;
  contract_type?: string;
  effective_date?: string;
  expiration_date?: string;
  status: string;
  summary?: string;
}

export interface ExtractionResult {
  success: boolean;
  entity_count: number;
  relationship_count: number;
  validation: {
    is_valid: boolean;
    errors: string[];
    warnings: string[];
  };
  entities: {
    contracts: unknown[];
    parties: unknown[];
    clauses: unknown[];
    obligations: unknown[];
    dates: unknown[];
    amounts: unknown[];
    relationships: unknown[];
  };
}

// API functions
export const queryAPI = {
  ask: async (question: string, contractId?: string): Promise<QueryResponse> => {
    const response = await api.post('/query/ask', {
      question,
      contract_id: contractId,
      include_follow_ups: true,
      use_history: true,
    });
    return response.data;
  },

  summarize: async (contractId: string) => {
    const response = await api.post('/query/summarize', { contract_id: contractId });
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

  listContracts: async () => {
    const response = await api.get('/graph/contracts');
    return response.data;
  },

  getContract: async (contractId: string) => {
    const response = await api.get(`/graph/contracts/${contractId}`);
    return response.data;
  },

  getContractFull: async (contractId: string) => {
    const response = await api.get(`/graph/contracts/${contractId}/full`);
    return response.data;
  },

  listClauses: async (clauseType?: string) => {
    const response = await api.get('/graph/clauses', {
      params: clauseType ? { clause_type: clauseType } : {},
    });
    return response.data;
  },

  listParties: async () => {
    const response = await api.get('/graph/parties');
    return response.data;
  },

  searchParties: async (name: string) => {
    const response = await api.get('/graph/parties/search', {
      params: { name },
    });
    return response.data;
  },

  deleteContract: async (contractId: string) => {
    const response = await api.delete(`/graph/contracts/${contractId}`);
    return response.data;
  },

  clearAll: async () => {
    const response = await api.delete('/graph/all');
    return response.data;
  },

  getSchema: async () => {
    const response = await api.get('/graph/schema');
    return response.data;
  },
};

export const extractionAPI = {
  extract: async (text: string, entityTypes?: string[]): Promise<ExtractionResult> => {
    const response = await api.post('/extraction/extract', {
      text,
      entity_types: entityTypes,
    });
    return response.data;
  },

  getOntology: async () => {
    const response = await api.get('/extraction/ontology');
    return response.data;
  },

  getClauseTypes: async () => {
    const response = await api.get('/extraction/clause-types');
    return response.data;
  },

  getPartyTypes: async () => {
    const response = await api.get('/extraction/party-types');
    return response.data;
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

export default api;
