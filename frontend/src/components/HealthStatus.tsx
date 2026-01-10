import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  ArrowPathIcon,
  ServerIcon,
  CircleStackIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { healthAPI, HealthResponse } from '../services/api';

interface HealthStatusProps {
  compact?: boolean;
  showDetails?: boolean;
}

export default function HealthStatus({ compact = false, showDetails = false }: HealthStatusProps) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(showDetails);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await healthAPI.check();
      setHealth(data);
    } catch (err) {
      setError('Unable to reach backend');
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    // Poll every 30 seconds
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleIcon className="w-5 h-5 text-green-400" />;
      case 'degraded':
        return <ExclamationTriangleIcon className="w-5 h-5 text-amber-400" />;
      case 'unhealthy':
        return <XCircleIcon className="w-5 h-5 text-red-400" />;
      default:
        return <ArrowPathIcon className="w-5 h-5 text-midnight-400 animate-spin" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-500/20 border-green-500/30';
      case 'degraded':
        return 'bg-amber-500/20 border-amber-500/30';
      case 'unhealthy':
        return 'bg-red-500/20 border-red-500/30';
      default:
        return 'bg-midnight-700/50 border-midnight-600/50';
    }
  };

  const getServiceIcon = (name: string) => {
    switch (name) {
      case 'neo4j':
        return <CircleStackIcon className="w-4 h-4" />;
      case 'schema':
        return <DocumentTextIcon className="w-4 h-4" />;
      default:
        return <ServerIcon className="w-4 h-4" />;
    }
  };

  if (compact) {
    return (
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 group"
      >
        {loading ? (
          <ArrowPathIcon className="w-4 h-4 text-midnight-400 animate-spin" />
        ) : error ? (
          <XCircleIcon className="w-4 h-4 text-red-400" />
        ) : (
          <div
            className={`w-2 h-2 rounded-full ${
              health?.status === 'healthy'
                ? 'bg-green-400'
                : health?.status === 'degraded'
                ? 'bg-amber-400'
                : 'bg-red-400'
            }`}
          />
        )}
        <span className="text-xs text-midnight-400 group-hover:text-midnight-200 transition-colors">
          {loading
            ? 'Checking...'
            : error
            ? 'Offline'
            : health?.status || 'Unknown'}
        </span>
      </button>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-midnight-300 uppercase tracking-wider">
          System Health
        </h3>
        <button
          onClick={fetchHealth}
          disabled={loading}
          className="p-1.5 rounded-lg hover:bg-midnight-800/50 transition-colors"
          title="Refresh"
        >
          <ArrowPathIcon
            className={`w-4 h-4 text-midnight-400 ${loading ? 'animate-spin' : ''}`}
          />
        </button>
      </div>

      {/* Overall Status */}
      <div
        className={`rounded-xl border p-4 ${
          error
            ? 'bg-red-500/10 border-red-500/30'
            : getStatusColor(health?.status || '')
        }`}
      >
        <div className="flex items-center gap-3">
          {loading ? (
            <ArrowPathIcon className="w-6 h-6 text-midnight-400 animate-spin" />
          ) : error ? (
            <XCircleIcon className="w-6 h-6 text-red-400" />
          ) : (
            getStatusIcon(health?.status || '')
          )}
          <div>
            <p className="font-medium text-midnight-100">
              {loading
                ? 'Checking health...'
                : error
                ? 'Backend Unavailable'
                : health?.status === 'healthy'
                ? 'All Systems Operational'
                : health?.status === 'degraded'
                ? 'Partial Outage'
                : 'System Unhealthy'}
            </p>
            {health && (
              <p className="text-xs text-midnight-400">
                v{health.version} • Last checked:{' '}
                {new Date(health.timestamp).toLocaleTimeString()}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Services */}
      <AnimatePresence>
        {(expanded || showDetails) && health && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="space-y-2"
          >
            {Object.entries(health.services).map(([key, service]) => (
              <div
                key={key}
                className="glass rounded-lg p-3 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <div className="text-midnight-400">{getServiceIcon(service.name)}</div>
                  <div>
                    <p className="font-medium text-sm text-midnight-100 capitalize">
                      {service.name}
                    </p>
                    {service.message && (
                      <p className="text-xs text-midnight-400">{service.message}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {service.latency_ms !== undefined && (
                    <span className="text-xs text-midnight-500">
                      {service.latency_ms}ms
                    </span>
                  )}
                  {getStatusIcon(service.status)}
                </div>
              </div>
            ))}

            {/* Schema Info */}
            {health.schema && (
              <div className="glass rounded-lg p-3">
                <p className="text-xs text-midnight-400 mb-2">Active Schema</p>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm text-electric-400">
                      {health.schema.name}
                    </p>
                    <p className="text-xs text-midnight-500">v{health.schema.version}</p>
                  </div>
                  <div className="text-right text-xs text-midnight-400">
                    <p>{health.schema.entity_count} entities</p>
                    <p>{health.schema.relationship_count} relationships</p>
                  </div>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Toggle Details */}
      {!showDetails && health && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full text-xs text-midnight-500 hover:text-midnight-300 transition-colors"
        >
          {expanded ? 'Hide details' : 'Show details'}
        </button>
      )}
    </div>
  );
}
