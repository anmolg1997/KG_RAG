import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ChatBubbleLeftRightIcon, 
  CloudArrowUpIcon, 
  CircleStackIcon,
  BeakerIcon,
  Bars3Icon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { useAppStore } from './store';
import { healthAPI, graphAPI } from './services/api';
import QueryChat from './components/QueryChat';
import DocumentUpload from './components/DocumentUpload';
import GraphVisualization from './components/GraphVisualization';
import ExtractionPanel from './components/ExtractionPanel';
import HealthStatus from './components/HealthStatus';
import StrategyPanel from './components/StrategyPanel';

const tabs = [
  { id: 'chat', name: 'Query', icon: ChatBubbleLeftRightIcon },
  { id: 'upload', name: 'Upload', icon: CloudArrowUpIcon },
  { id: 'graph', name: 'Graph', icon: CircleStackIcon },
  { id: 'extract', name: 'Extract', icon: BeakerIcon },
] as const;

export default function App() {
  const { activeTab, setActiveTab, sidebarOpen, toggleSidebar, graphStats, setGraphStats } = useAppStore();

  useEffect(() => {
    // Get initial graph stats
    graphAPI.getStats().then(setGraphStats).catch(console.error);
  }, [setGraphStats]);

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <AnimatePresence mode="wait">
        {sidebarOpen && (
          <motion.aside
            initial={{ x: -280, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -280, opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="w-64 glass-dark flex flex-col fixed h-full z-50 lg:relative"
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

            {/* Navigation */}
            <nav className="flex-1 p-4 space-y-2">
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
            {graphStats && (
              <div className="p-4 border-t border-midnight-800/50">
                <h3 className="text-xs font-semibold text-midnight-400 uppercase tracking-wider mb-3">
                  Graph Stats
                </h3>
                <div className="grid grid-cols-2 gap-2">
                  <div className="glass p-3 rounded-lg">
                    <p className="text-2xl font-bold text-electric-400">{graphStats.total_nodes}</p>
                    <p className="text-xs text-midnight-400">Nodes</p>
                  </div>
                  <div className="glass p-3 rounded-lg">
                    <p className="text-2xl font-bold text-amber-400">{graphStats.total_relationships}</p>
                    <p className="text-xs text-midnight-400">Relations</p>
                  </div>
                </div>
              </div>
            )}

            {/* Strategy Panel */}
            <div className="p-4 border-t border-midnight-800/50">
              <StrategyPanel />
            </div>

            {/* Health Status */}
            <div className="p-4 border-t border-midnight-800/50">
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

      {/* Main content */}
      <main className="flex-1 flex flex-col min-h-screen">
        {/* Header */}
        <header className="h-16 glass-dark border-b border-midnight-800/50 flex items-center px-4 lg:px-6">
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
              {activeTab === 'chat' && 'Ask questions about your contracts'}
              {activeTab === 'upload' && 'Upload PDF documents for processing'}
              {activeTab === 'graph' && 'Visualize and explore the knowledge graph'}
              {activeTab === 'extract' && 'Extract entities from text'}
            </p>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
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
