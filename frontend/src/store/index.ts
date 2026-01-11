import { create } from 'zustand';
import { GraphStats, GraphVisualization, DebugInfo } from '../services/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  metadata?: {
    sources?: unknown[];
    confidence?: number;
    followUps?: string[];
    timingMs?: number;
    debugInfo?: DebugInfo;
  };
}

interface AppState {
  // Chat state
  messages: Message[];
  isLoading: boolean;
  currentDocumentId: string | null;  // Schema-agnostic: generic document ID
  
  // Graph state
  graphStats: GraphStats | null;
  graphData: GraphVisualization | null;
  
  // Schema state
  activeSchema: string | null;
  entityTypes: string[];
  
  // UI state
  activeTab: 'chat' | 'upload' | 'graph' | 'extract';
  sidebarOpen: boolean;
  
  // Actions
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  setLoading: (loading: boolean) => void;
  setCurrentDocument: (documentId: string | null) => void;
  setGraphStats: (stats: GraphStats) => void;
  setGraphData: (data: GraphVisualization) => void;
  setActiveSchema: (schemaName: string) => void;
  setEntityTypes: (types: string[]) => void;
  setActiveTab: (tab: 'chat' | 'upload' | 'graph' | 'extract') => void;
  toggleSidebar: () => void;
  clearMessages: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Initial state
  messages: [],
  isLoading: false,
  currentDocumentId: null,
  graphStats: null,
  graphData: null,
  activeSchema: null,
  entityTypes: [],
  activeTab: 'chat',
  sidebarOpen: true,
  
  // Actions
  addMessage: (message) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          ...message,
          id: crypto.randomUUID(),
          timestamp: new Date(),
        },
      ],
    })),
  
  setLoading: (loading) => set({ isLoading: loading }),
  
  setCurrentDocument: (documentId) => set({ currentDocumentId: documentId }),
  
  setGraphStats: (stats) => set({ graphStats: stats }),
  
  setGraphData: (data) => set({ graphData: data }),
  
  setActiveSchema: (schemaName) => set({ activeSchema: schemaName }),
  
  setEntityTypes: (types) => set({ entityTypes: types }),
  
  setActiveTab: (tab) => set({ activeTab: tab }),
  
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  
  clearMessages: () => set({ messages: [] }),
}));
