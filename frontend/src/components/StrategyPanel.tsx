import React, { useEffect, useState } from 'react';
import { strategyAPI, StrategyStatus, PresetInfo } from '../services/api';

interface StrategyPanelProps {
  onStrategyChange?: () => void;
}

const StrategyPanel: React.FC<StrategyPanelProps> = ({ onStrategyChange }) => {
  const [status, setStatus] = useState<StrategyStatus | null>(null);
  const [presets, setPresets] = useState<PresetInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [statusData, presetsData] = await Promise.all([
        strategyAPI.getStatus(),
        strategyAPI.getPresets(),
      ]);
      setStatus(statusData);
      setPresets(presetsData);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch strategy data:', err);
      setError('Failed to load strategy configuration');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handlePresetChange = async (presetName: string) => {
    try {
      setUpdating(true);
      await strategyAPI.loadPreset(presetName);
      await fetchData();
      onStrategyChange?.();
    } catch (err) {
      console.error('Failed to load preset:', err);
      setError('Failed to apply preset');
    } finally {
      setUpdating(false);
    }
  };

  const handleToggle = async (
    strategyType: 'extraction' | 'retrieval',
    path: string[],
    value: boolean
  ) => {
    try {
      setUpdating(true);
      
      // Build the nested update object
      const updates: Record<string, unknown> = {};
      let current = updates;
      for (let i = 0; i < path.length - 1; i++) {
        current[path[i]] = {};
        current = current[path[i]] as Record<string, unknown>;
      }
      current[path[path.length - 1]] = value;

      if (strategyType === 'extraction') {
        await strategyAPI.updateExtraction(updates);
      } else {
        await strategyAPI.updateRetrieval(updates);
      }
      
      await fetchData();
      onStrategyChange?.();
    } catch (err) {
      console.error('Failed to update strategy:', err);
      setError('Failed to update setting');
    } finally {
      setUpdating(false);
    }
  };

  const presetColors: Record<string, string> = {
    minimal: 'bg-gray-600 hover:bg-gray-500',
    balanced: 'bg-blue-600 hover:bg-blue-500',
    comprehensive: 'bg-purple-600 hover:bg-purple-500',
    speed: 'bg-green-600 hover:bg-green-500',
    research: 'bg-amber-600 hover:bg-amber-500',
    strict: 'bg-red-600 hover:bg-red-500',
  };

  const validationModes = [
    { value: 'ignore', label: 'Ignore', desc: 'No validation, store all' },
    { value: 'warn', label: 'Warn', desc: 'Log issues, store all' },
    { value: 'store_valid', label: 'Valid Only', desc: 'Skip invalid, store valid' },
    { value: 'strict', label: 'Strict', desc: 'Block if any errors' },
  ];

  const handleValidationModeChange = async (mode: string) => {
    try {
      setUpdating(true);
      await strategyAPI.updateExtraction({ validation: { mode } });
      await fetchData();
      onStrategyChange?.();
    } catch (err) {
      console.error('Failed to update validation mode:', err);
      setError('Failed to update validation mode');
    } finally {
      setUpdating(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
        <div className="animate-pulse flex items-center space-x-2">
          <div className="h-4 w-4 bg-slate-600 rounded"></div>
          <div className="h-4 w-32 bg-slate-600 rounded"></div>
        </div>
      </div>
    );
  }

  if (error && !status) {
    return (
      <div className="bg-red-900/30 rounded-lg p-4 border border-red-700">
        <p className="text-red-400 text-sm">{error}</p>
        <button
          onClick={fetchData}
          className="mt-2 text-xs text-red-300 hover:text-red-200"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-700/50 transition-colors"
      >
        <div className="flex items-center space-x-3">
          <svg
            className="w-5 h-5 text-indigo-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
          <span className="font-medium text-slate-200">Strategy</span>
          {status?.current_preset && (
            <span className={`px-2 py-0.5 text-xs rounded ${presetColors[status.current_preset] || 'bg-slate-600'} text-white`}>
              {status.current_preset}
            </span>
          )}
        </div>
        <svg
          className={`w-5 h-5 text-slate-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded Content */}
      {expanded && status && (
        <div className="px-4 pb-4 space-y-4">
          {/* Presets */}
          <div>
            <p className="text-xs text-slate-400 mb-2">Quick Presets</p>
            <div className="flex flex-wrap gap-2">
              {presets.map((preset) => (
                <button
                  key={preset.name}
                  onClick={() => handlePresetChange(preset.name)}
                  disabled={updating}
                  className={`px-3 py-1.5 text-xs rounded-md text-white transition-colors disabled:opacity-50 ${
                    status.current_preset === preset.name
                      ? `${presetColors[preset.name] || 'bg-slate-600'} ring-2 ring-white/30`
                      : `${presetColors[preset.name] || 'bg-slate-600'} opacity-70 hover:opacity-100`
                  }`}
                  title={`${preset.extraction_description}\n${preset.retrieval_description}`}
                >
                  {preset.name}
                </button>
              ))}
            </div>
          </div>

          {/* Extraction Settings */}
          <div>
            <p className="text-xs text-slate-400 mb-2 flex items-center">
              <span className="inline-block w-2 h-2 bg-emerald-500 rounded-full mr-2"></span>
              Extraction
            </p>
            <div className="space-y-2 pl-4">
              <ToggleOption
                label="Store chunks"
                enabled={status.extraction.chunks_enabled}
                onChange={(v) => handleToggle('extraction', ['chunks', 'enabled'], v)}
                disabled={updating}
              />
              <ToggleOption
                label="Page numbers"
                enabled={status.extraction.metadata_enabled.page_numbers}
                onChange={(v) => handleToggle('extraction', ['metadata', 'page_numbers', 'enabled'], v)}
                disabled={updating}
              />
              <ToggleOption
                label="Section headings"
                enabled={status.extraction.metadata_enabled.section_headings}
                onChange={(v) => handleToggle('extraction', ['metadata', 'section_headings', 'enabled'], v)}
                disabled={updating}
              />
              <ToggleOption
                label="Temporal references"
                enabled={status.extraction.metadata_enabled.temporal_references}
                onChange={(v) => handleToggle('extraction', ['metadata', 'temporal_references', 'enabled'], v)}
                disabled={updating}
              />
              <ToggleOption
                label="Key terms"
                enabled={status.extraction.metadata_enabled.key_terms}
                onChange={(v) => handleToggle('extraction', ['metadata', 'key_terms', 'enabled'], v)}
                disabled={updating}
              />
              <ToggleOption
                label="Entity-chunk linking"
                enabled={status.extraction.entity_linking}
                onChange={(v) => handleToggle('extraction', ['entity_linking', 'enabled'], v)}
                disabled={updating}
              />
              
              {/* Validation Mode */}
              <div className="mt-3 pt-3 border-t border-slate-600">
                <p className="text-xs text-slate-400 mb-2">Validation Mode</p>
                <div className="flex flex-wrap gap-1.5">
                  {validationModes.map((mode) => (
                    <button
                      key={mode.value}
                      onClick={() => handleValidationModeChange(mode.value)}
                      disabled={updating}
                      className={`px-2 py-1 text-xs rounded transition-colors disabled:opacity-50 ${
                        status.extraction.validation?.mode === mode.value
                          ? 'bg-indigo-600 text-white'
                          : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                      }`}
                      title={mode.desc}
                    >
                      {mode.label}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-slate-500 mt-1.5">
                  {validationModes.find(m => m.value === status.extraction.validation?.mode)?.desc || 'Log issues, store all'}
                </p>
              </div>
            </div>
          </div>

          {/* Retrieval Settings */}
          <div>
            <p className="text-xs text-slate-400 mb-2 flex items-center">
              <span className="inline-block w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
              Retrieval
            </p>
            <div className="space-y-2 pl-4">
              <ToggleOption
                label="Graph traversal"
                enabled={status.retrieval.search_methods.graph_traversal}
                onChange={(v) => handleToggle('retrieval', ['search', 'graph_traversal', 'enabled'], v)}
                disabled={updating}
              />
              <ToggleOption
                label="Chunk text search"
                enabled={status.retrieval.search_methods.chunk_text_search}
                onChange={(v) => handleToggle('retrieval', ['search', 'chunk_text_search', 'enabled'], v)}
                disabled={updating}
              />
              <ToggleOption
                label="Keyword matching"
                enabled={status.retrieval.search_methods.keyword_matching}
                onChange={(v) => handleToggle('retrieval', ['search', 'keyword_matching', 'enabled'], v)}
                disabled={updating}
              />
              <ToggleOption
                label="Temporal filtering"
                enabled={status.retrieval.search_methods.temporal_filtering}
                onChange={(v) => handleToggle('retrieval', ['search', 'temporal_filtering', 'enabled'], v)}
                disabled={updating}
              />
              <ToggleOption
                label="Context expansion"
                enabled={status.retrieval.context_expansion}
                onChange={(v) => handleToggle('retrieval', ['context', 'expand_neighbors', 'enabled'], v)}
                disabled={updating}
              />
            </div>
          </div>

          {/* Status indicator */}
          {updating && (
            <div className="flex items-center space-x-2 text-xs text-slate-400">
              <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              <span>Updating...</span>
            </div>
          )}

          {error && (
            <p className="text-xs text-red-400">{error}</p>
          )}
        </div>
      )}
    </div>
  );
};

// Toggle component
interface ToggleOptionProps {
  label: string;
  enabled: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
}

const ToggleOption: React.FC<ToggleOptionProps> = ({
  label,
  enabled,
  onChange,
  disabled,
}) => {
  return (
    <label className="flex items-center justify-between cursor-pointer group">
      <span className="text-xs text-slate-300 group-hover:text-slate-200">
        {label}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={enabled}
        onClick={() => onChange(!enabled)}
        disabled={disabled}
        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors disabled:opacity-50 ${
          enabled ? 'bg-indigo-600' : 'bg-slate-600'
        }`}
      >
        <span
          className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
            enabled ? 'translate-x-4.5' : 'translate-x-1'
          }`}
          style={{ transform: enabled ? 'translateX(18px)' : 'translateX(4px)' }}
        />
      </button>
    </label>
  );
};

export default StrategyPanel;
