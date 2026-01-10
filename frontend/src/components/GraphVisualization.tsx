import { useState, useEffect, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import { 
  ArrowPathIcon,
  MagnifyingGlassMinusIcon,
  MagnifyingGlassPlusIcon,
  ArrowsPointingOutIcon,
} from '@heroicons/react/24/outline';
import ForceGraph2D from 'react-force-graph-2d';
import { graphAPI, GraphNode, GraphEdge } from '../services/api';
import { useAppStore } from '../store';

interface GraphData {
  nodes: GraphNode[];
  links: { source: string; target: string; type: string }[];
}

const nodeColors: Record<string, string> = {
  Contract: '#38b2ac',
  Party: '#f59e0b',
  Clause: '#8b5cf6',
  Obligation: '#ef4444',
  ContractDate: '#10b981',
  Amount: '#3b82f6',
  default: '#64748b',
};

export default function GraphVisualization() {
  const { graphStats, setGraphStats, setGraphData } = useAppStore();
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [nodeLimit, setNodeLimit] = useState(100);
  const graphRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height: containerRef.current.offsetHeight - 60,
        });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  const fetchGraphData = useCallback(async () => {
    setLoading(true);
    try {
      const [vizData, stats] = await Promise.all([
        graphAPI.getVisualization(nodeLimit),
        graphAPI.getStats(),
      ]);

      setData({
        nodes: vizData.nodes,
        links: vizData.edges.map((e) => ({
          source: e.source,
          target: e.target,
          type: e.type,
        })),
      });
      setGraphStats(stats);
      setGraphData(vizData);
    } catch (error) {
      console.error('Failed to fetch graph data:', error);
    } finally {
      setLoading(false);
    }
  }, [nodeLimit, setGraphStats, setGraphData]);

  useEffect(() => {
    fetchGraphData();
  }, [fetchGraphData]);

  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node);
    if (graphRef.current) {
      graphRef.current.centerAt(node.x, node.y, 500);
      graphRef.current.zoom(2, 500);
    }
  }, []);

  const handleZoomIn = () => {
    if (graphRef.current) {
      graphRef.current.zoom(graphRef.current.zoom() * 1.5, 300);
    }
  };

  const handleZoomOut = () => {
    if (graphRef.current) {
      graphRef.current.zoom(graphRef.current.zoom() / 1.5, 300);
    }
  };

  const handleFit = () => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(400, 50);
    }
  };

  return (
    <div ref={containerRef} className="h-full flex flex-col">
      {/* Controls */}
      <div className="p-4 border-b border-midnight-800/50 flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <select
            value={nodeLimit}
            onChange={(e) => setNodeLimit(Number(e.target.value))}
            className="glass px-3 py-2 rounded-lg text-sm bg-midnight-900 border-midnight-700"
          >
            <option value={50}>50 nodes</option>
            <option value={100}>100 nodes</option>
            <option value={200}>200 nodes</option>
            <option value={500}>500 nodes</option>
          </select>
          
          <button
            onClick={fetchGraphData}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 rounded-lg glass hover:bg-midnight-800/50 transition-colors"
          >
            <ArrowPathIcon className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span className="text-sm">Refresh</span>
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleZoomOut}
            className="p-2 rounded-lg glass hover:bg-midnight-800/50 transition-colors"
          >
            <MagnifyingGlassMinusIcon className="w-5 h-5" />
          </button>
          <button
            onClick={handleZoomIn}
            className="p-2 rounded-lg glass hover:bg-midnight-800/50 transition-colors"
          >
            <MagnifyingGlassPlusIcon className="w-5 h-5" />
          </button>
          <button
            onClick={handleFit}
            className="p-2 rounded-lg glass hover:bg-midnight-800/50 transition-colors"
          >
            <ArrowsPointingOutIcon className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Graph + Details */}
      <div className="flex-1 flex overflow-hidden">
        {/* Graph */}
        <div className="flex-1 relative">
          {loading && !data ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="flex flex-col items-center gap-4">
                <ArrowPathIcon className="w-8 h-8 text-electric-400 animate-spin" />
                <p className="text-midnight-400">Loading graph...</p>
              </div>
            </div>
          ) : data && data.nodes.length > 0 ? (
            <ForceGraph2D
              ref={graphRef}
              graphData={data}
              width={dimensions.width - (selectedNode ? 320 : 0)}
              height={dimensions.height}
              backgroundColor="transparent"
              nodeId="id"
              nodeLabel={(node: any) => node.name || node.title || node.id}
              nodeColor={(node: any) => nodeColors[node._label] || nodeColors.default}
              nodeRelSize={6}
              linkColor={() => 'rgba(100, 116, 139, 0.3)'}
              linkWidth={1}
              linkDirectionalArrowLength={4}
              linkDirectionalArrowRelPos={1}
              onNodeClick={(node: any) => handleNodeClick(node)}
              cooldownTicks={100}
              onEngineStop={() => graphRef.current?.zoomToFit(400, 50)}
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <p className="text-midnight-400 mb-4">No graph data available</p>
                <p className="text-sm text-midnight-500">Upload some documents to populate the graph</p>
              </div>
            </div>
          )}

          {/* Legend */}
          <div className="absolute bottom-4 left-4 glass rounded-xl p-4">
            <h4 className="text-xs font-semibold text-midnight-400 uppercase tracking-wider mb-3">
              Node Types
            </h4>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(nodeColors)
                .filter(([key]) => key !== 'default')
                .map(([label, color]) => (
                  <div key={label} className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: color }}
                    />
                    <span className="text-xs text-midnight-300">{label}</span>
                  </div>
                ))}
            </div>
          </div>
        </div>

        {/* Node Details Panel */}
        {selectedNode && (
          <motion.div
            initial={{ x: 320, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            className="w-80 glass-dark border-l border-midnight-800/50 overflow-y-auto"
          >
            <div className="p-4 border-b border-midnight-800/50 flex items-center justify-between">
              <h3 className="font-semibold">Node Details</h3>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-midnight-400 hover:text-midnight-200"
              >
                ✕
              </button>
            </div>
            
            <div className="p-4 space-y-4">
              <div>
                <span
                  className="inline-block px-2 py-1 rounded text-xs font-medium"
                  style={{ backgroundColor: nodeColors[selectedNode._label] + '20', color: nodeColors[selectedNode._label] }}
                >
                  {selectedNode._label}
                </span>
              </div>
              
              <div>
                <h4 className="text-lg font-semibold text-midnight-100">
                  {selectedNode.name || selectedNode.title || selectedNode.id}
                </h4>
              </div>
              
              <div className="space-y-3">
                {Object.entries(selectedNode)
                  .filter(([key]) => !['id', '_label', 'x', 'y', 'vx', 'vy', 'fx', 'fy', 'index'].includes(key))
                  .map(([key, value]) => (
                    <div key={key}>
                      <p className="text-xs text-midnight-400 uppercase tracking-wider">{key}</p>
                      <p className="text-sm text-midnight-200 mt-1">
                        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                      </p>
                    </div>
                  ))}
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
