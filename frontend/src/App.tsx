import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ChatBubbleLeftRightIcon, 
  CloudArrowUpIcon, 
  CircleStackIcon,
  BeakerIcon,
  Bars3Icon,
  XMarkIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline';
import { useAppStore } from './store';
import { graphAPI, GraphStats } from './services/api';
import QueryChat from './components/QueryChat';
import DocumentUpload from './components/DocumentUpload';
import GraphVisualization from './components/GraphVisualization';
import ExtractionPanel from './components/ExtractionPanel';
import HealthStatus from './components/HealthStatus';
import StrategyPanel from './components/StrategyPanel';

// Dynamic color palette - generates consistent colors for any entity type
const COLOR_PALETTE = [
  '#38b2ac', // teal
  '#f59e0b', // amber
  '#8b5cf6', // purple
  '#10b981', // emerald
  '#ef4444', // red
  '#3b82f6', // blue
  '#ec4899', // pink
  '#f97316', // orange
  '#06b6d4', // cyan
  '#84cc16', // lime
  '#a855f7', // violet
  '#14b8a6', // teal variant
];

// Infrastructure colors (muted)
const INFRA_COLORS: Record<string, string> = {
  Document: '#64748b',
  Chunk: '#475569',
  EXTRACTED_FROM: '#64748b',
  FROM_DOCUMENT: '#475569',
  NEXT_CHUNK: '#334155',
  PREV_CHUNK: '#1e293b',
};

// Cache for consistent dynamic colors
const dynamicColorCache: Record<string, string> = {};
let colorIndex = 0;

const getColor = (type: string, _category: 'nodes' | 'relationships'): string => {
  // Check infrastructure colors first
  if (INFRA_COLORS[type]) {
    return INFRA_COLORS[type];
  }
  
  // Generate/retrieve consistent color for any type
  if (!dynamicColorCache[type]) {
    dynamicColorCache[type] = COLOR_PALETTE[colorIndex % COLOR_PALETTE.length];
    colorIndex++;
  }
  return dynamicColorCache[type];
};

// Interactive Stats Panel Component
function GraphStatsPanel({ stats }: { stats: GraphStats }) {
  const [expandedSection, setExpandedSection] = useState<'nodes' | 'relationships' | null>(null);

  // Parse node distribution
  const getNodeDistribution = () => {
    if (stats.entities?.by_type) {
      const entities = { ...stats.entities.by_type };
      if (stats.infrastructure) {
        entities['Chunk'] = stats.infrastructure.chunks;
        entities['Document'] = stats.infrastructure.documents;
      }
      return entities;
    }
    return stats.node_counts || {};
  };

  // Parse relationship distribution  
  const getRelationshipDistribution = () => {
    const combined: Record<string, number> = {};
    if (stats.entity_relationships?.by_type) {
      Object.assign(combined, stats.entity_relationships.by_type);
    }
    if (stats.infrastructure?.relationships?.by_type) {
      Object.assign(combined, stats.infrastructure.relationships.by_type);
    }
    // Fallback to basic count
    if (Object.keys(combined).length === 0 && stats.total_relationships > 0) {
      combined['Relationships'] = stats.total_relationships;
    }
    return combined;
  };

  const nodeDistribution = getNodeDistribution();
  const relDistribution = getRelationshipDistribution();
  
  // Calculate entity vs infrastructure breakdown
  const infrastructureLabels = ['Chunk', 'Document'];
  const entityNodes = Object.entries(nodeDistribution)
    .filter(([k]) => !infrastructureLabels.includes(k) && k !== 'relationships')
    .reduce((sum, [_, v]) => sum + (v as number), 0);
  const infraNodes = (nodeDistribution['Chunk'] || 0) + (nodeDistribution['Document'] || 0);

  const infrastructureRels = ['EXTRACTED_FROM', 'FROM_DOCUMENT', 'NEXT_CHUNK', 'PREV_CHUNK'];
  const entityRels = Object.entries(relDistribution)
    .filter(([k]) => !infrastructureRels.includes(k))
    .reduce((sum, [_, v]) => sum + (v as number), 0);
  const infraRels = Object.entries(relDistribution)
    .filter(([k]) => infrastructureRels.includes(k))
    .reduce((sum, [_, v]) => sum + (v as number), 0);

  return (
    <div className="p-4 border-t border-midnight-800/50">
      <h3 className="text-xs font-semibold text-midnight-400 uppercase tracking-wider mb-3">
        Graph Stats
      </h3>
      
      {/* Nodes Card - Clickable */}
      <motion.div 
        className={`glass rounded-xl mb-2 overflow-hidden cursor-pointer transition-all ${
          expandedSection === 'nodes' ? 'ring-1 ring-electric-500/50' : 'hover:bg-midnight-800/30'
        }`}
        onClick={() => setExpandedSection(expandedSection === 'nodes' ? null : 'nodes')}
      >
        <div className="p-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-electric-500/20 flex items-center justify-center">
              <CircleStackIcon className="w-5 h-5 text-electric-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-electric-400">{stats.total_nodes}</p>
              <p className="text-xs text-midnight-400">Total Nodes</p>
            </div>
          </div>
          <motion.div
            animate={{ rotate: expandedSection === 'nodes' ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronDownIcon className="w-5 h-5 text-midnight-500" />
          </motion.div>
        </div>
        
        {/* Expanded Node Distribution */}
        <AnimatePresence>
          {expandedSection === 'nodes' && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="border-t border-midnight-800/50"
            >
              <div className="p-3 space-y-2">
                {/* Summary badges */}
                <div className="flex gap-2 mb-3">
                  <span className="px-2 py-0.5 rounded-full bg-electric-500/20 text-electric-300 text-xs">
                    {entityNodes} entities
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-midnight-700/50 text-midnight-300 text-xs">
                    {infraNodes} infrastructure
                  </span>
                </div>
                
                {/* Distribution bars */}
                {Object.entries(nodeDistribution)
                  .filter(([k]) => k !== 'relationships')
                  .sort((a, b) => (b[1] as number) - (a[1] as number))
                  .map(([type, count], i) => {
                    const percentage = ((count as number) / stats.total_nodes) * 100;
                    const isInfra = infrastructureLabels.includes(type);
                    return (
                      <motion.div 
                        key={type}
                        initial={{ x: -20, opacity: 0 }}
                        animate={{ x: 0, opacity: 1 }}
                        transition={{ delay: i * 0.03 }}
                        className="space-y-1"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className={isInfra ? 'text-midnight-500' : 'text-midnight-300'}>
                            {type}
                          </span>
                          <span className="text-midnight-400 font-mono">
                            {count as number}
                            <span className="text-midnight-600 ml-1">
                              ({percentage.toFixed(0)}%)
                            </span>
                          </span>
                        </div>
                        <div className="h-1.5 bg-midnight-800 rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${percentage}%` }}
                            transition={{ duration: 0.4, delay: i * 0.03 }}
                            className="h-full rounded-full"
                            style={{ backgroundColor: getColor(type, 'nodes') }}
                          />
                        </div>
                      </motion.div>
                    );
                  })}
                
                {/* Sum verification */}
                <div className="pt-2 mt-2 border-t border-midnight-800/30 flex justify-between text-xs">
                  <span className="text-midnight-500">Total</span>
                  <span className="text-electric-400 font-bold font-mono">
                    = {Object.entries(nodeDistribution).filter(([k]) => k !== 'relationships').reduce((s, [_, v]) => s + (v as number), 0)}
                  </span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
      
      {/* Relationships Card - Clickable */}
      <motion.div 
        className={`glass rounded-xl overflow-hidden cursor-pointer transition-all ${
          expandedSection === 'relationships' ? 'ring-1 ring-amber-500/50' : 'hover:bg-midnight-800/30'
        }`}
        onClick={() => setExpandedSection(expandedSection === 'relationships' ? null : 'relationships')}
      >
        <div className="p-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
              <svg className="w-5 h-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <p className="text-2xl font-bold text-amber-400">{stats.total_relationships}</p>
              <p className="text-xs text-midnight-400">Total Relations</p>
            </div>
          </div>
          <motion.div
            animate={{ rotate: expandedSection === 'relationships' ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronDownIcon className="w-5 h-5 text-midnight-500" />
          </motion.div>
        </div>
        
        {/* Expanded Relationship Distribution */}
        <AnimatePresence>
          {expandedSection === 'relationships' && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="border-t border-midnight-800/50"
            >
              <div className="p-3 space-y-2">
                {/* Summary badges */}
                <div className="flex gap-2 mb-3">
                  <span className="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 text-xs">
                    {entityRels} semantic
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-midnight-700/50 text-midnight-300 text-xs">
                    {infraRels} infrastructure
                  </span>
                </div>
                
                {/* Distribution bars */}
                {Object.entries(relDistribution)
                  .sort((a, b) => (b[1] as number) - (a[1] as number))
                  .map(([type, count], i) => {
                    const percentage = ((count as number) / stats.total_relationships) * 100;
                    const isInfra = infrastructureRels.includes(type);
                    return (
                      <motion.div 
                        key={type}
                        initial={{ x: -20, opacity: 0 }}
                        animate={{ x: 0, opacity: 1 }}
                        transition={{ delay: i * 0.03 }}
                        className="space-y-1"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className={`${isInfra ? 'text-midnight-500' : 'text-midnight-300'} truncate max-w-[120px]`}>
                            {type.replace(/_/g, ' ')}
                          </span>
                          <span className="text-midnight-400 font-mono">
                            {count as number}
                            <span className="text-midnight-600 ml-1">
                              ({percentage.toFixed(0)}%)
                            </span>
                          </span>
                        </div>
                        <div className="h-1.5 bg-midnight-800 rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${percentage}%` }}
                            transition={{ duration: 0.4, delay: i * 0.03 }}
                            className="h-full rounded-full"
                            style={{ backgroundColor: getColor(type, 'relationships') }}
                          />
                        </div>
                      </motion.div>
                    );
                  })}
                
                {/* Sum verification */}
                <div className="pt-2 mt-2 border-t border-midnight-800/30 flex justify-between text-xs">
                  <span className="text-midnight-500">Total</span>
                  <span className="text-amber-400 font-bold font-mono">
                    = {Object.values(relDistribution).reduce((s, v) => s + (v as number), 0)}
                  </span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}

const tabs = [
  { id: 'chat', name: 'Query', icon: ChatBubbleLeftRightIcon },
  { id: 'upload', name: 'Upload', icon: CloudArrowUpIcon },
  { id: 'graph', name: 'Graph', icon: CircleStackIcon },
  { id: 'extract', name: 'Extract', icon: BeakerIcon },
] as const;

export default function App() {
  const { activeTab, setActiveTab, sidebarOpen, toggleSidebar, graphStats, setGraphStats } = useAppStore();

  // Refresh stats on initial load and when switching to graph tab
  useEffect(() => {
    graphAPI.getStats().then(setGraphStats).catch(console.error);
  }, [setGraphStats]);

  // Refresh stats when switching to graph tab
  useEffect(() => {
    if (activeTab === 'graph') {
      graphAPI.getStats().then(setGraphStats).catch(console.error);
    }
  }, [activeTab, setGraphStats]);

  return (
    <div className="h-screen flex overflow-hidden">
      {/* Sidebar - Fixed position with independent scroll */}
      <AnimatePresence mode="wait">
        {sidebarOpen && (
          <motion.aside
            initial={{ x: -280, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -280, opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="w-64 glass-dark flex flex-col fixed h-screen z-50 lg:relative lg:h-screen overflow-hidden"
          >
            {/* Logo */}
            <div className="p-6 border-b border-midnight-800/50">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-electric-400 to-electric-600 flex items-center justify-center">
                  <CircleStackIcon className="w-6 h-6 text-midnight-950" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gradient">KG-RAG</h1>
                  <p className="text-xs text-midnight-400">Knowledge Graph RAG</p>
                </div>
              </div>
            </div>

            {/* Scrollable content area - Independent scroll */}
            <div className="flex-1 overflow-y-auto overflow-x-hidden overscroll-contain">
              {/* Navigation */}
              <nav className="p-4 space-y-2">
                {tabs.map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                        isActive
                          ? 'bg-electric-500/20 text-electric-300 glow-electric'
                          : 'text-midnight-300 hover:bg-midnight-800/50 hover:text-midnight-100'
                      }`}
                    >
                      <Icon className="w-5 h-5" />
                      <span className="font-medium">{tab.name}</span>
                    </button>
                  );
                })}
              </nav>

              {/* Stats */}
              {graphStats && <GraphStatsPanel stats={graphStats} />}

              {/* Strategy Panel */}
              <div className="p-4 border-t border-midnight-800/50">
                <StrategyPanel />
              </div>
            </div>

            {/* Health Status - Fixed at bottom */}
            <div className="p-4 border-t border-midnight-800/50 flex-shrink-0">
              <HealthStatus showDetails={false} />
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden" 
          onClick={toggleSidebar}
        />
      )}

      {/* Main content - Independent scroll context */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Header - Fixed */}
        <header className="h-16 glass-dark border-b border-midnight-800/50 flex items-center px-4 lg:px-6 flex-shrink-0">
          <button
            onClick={toggleSidebar}
            className="p-2 rounded-lg hover:bg-midnight-800/50 transition-colors lg:hidden mr-4"
          >
            {sidebarOpen ? (
              <XMarkIcon className="w-6 h-6" />
            ) : (
              <Bars3Icon className="w-6 h-6" />
            )}
          </button>
          
          <div className="flex-1">
            <h2 className="text-lg font-semibold capitalize">{activeTab}</h2>
            <p className="text-xs text-midnight-400">
              {activeTab === 'chat' && 'Ask questions about your documents'}
              {activeTab === 'upload' && 'Upload PDF documents for processing'}
              {activeTab === 'graph' && 'Visualize and explore the knowledge graph'}
              {activeTab === 'extract' && 'Extract entities from text'}
            </p>
          </div>
        </header>

        {/* Content - Scroll isolated */}
        <div className="flex-1 overflow-hidden overscroll-contain">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.2 }}
              className="h-full"
            >
              {activeTab === 'chat' && <QueryChat />}
              {activeTab === 'upload' && <DocumentUpload />}
              {activeTab === 'graph' && <GraphVisualization />}
              {activeTab === 'extract' && <ExtractionPanel />}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
