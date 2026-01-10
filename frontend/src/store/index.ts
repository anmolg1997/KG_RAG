import { create } from 'zustand';
import { QueryResponse, GraphStats, GraphVisualization } from '../services/api';

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
  };
}

interface AppState {
  // Chat state
  messages: Message[];
  isLoading: boolean;
  currentContractId: string | null;
  
  // Graph state
  graphStats: GraphStats | null;
  graphData: GraphVisualization | null;
  
  // UI state
  activeTab: 'chat' | 'upload' | 'graph' | 'extract';
  sidebarOpen: boolean;
  
  // Actions
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  setLoading: (loading: boolean) => void;
  setCurrentContract: (contractId: string | null) => void;
  setGraphStats: (stats: GraphStats) => void;
  setGraphData: (data: GraphVisualization) => void;
  setActiveTab: (tab: 'chat' | 'upload' | 'graph' | 'extract') => void;
  toggleSidebar: () => void;
  clearMessages: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Initial state
  messages: [],
  isLoading: false,
  currentContractId: null,
  graphStats: null,
  graphData: null,
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
  
  setCurrentContract: (contractId) => set({ currentContractId: contractId }),
  
  setGraphStats: (stats) => set({ graphStats: stats }),
  
  setGraphData: (data) => set({ graphData: data }),
  
  setActiveTab: (tab) => set({ activeTab: tab }),
  
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  
  clearMessages: () => set({ messages: [] }),
}));
