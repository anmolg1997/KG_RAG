import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  BeakerIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  DocumentTextIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';
import { extractionAPI, graphAPI, ExtractionResult, EntityDefinition } from '../services/api';

export default function ExtractionPanel() {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const [activeEntityTab, setActiveEntityTab] = useState<string>('');
  
  // Schema-agnostic: dynamically loaded from backend
  const [entityTypes, setEntityTypes] = useState<string[]>([]);
  const [schemaName, setSchemaName] = useState<string>('');
  const [schemaEntities, setSchemaEntities] = useState<EntityDefinition[]>([]);
  const [loadingSchema, setLoadingSchema] = useState(true);

  // Load schema information on mount
  useEffect(() => {
    const loadSchema = async () => {
      try {
        const [schema, entities] = await Promise.all([
          graphAPI.getSchema(),
          graphAPI.getSchemaEntities(),
        ]);
        
        setSchemaName(schema.active_schema);
        setEntityTypes(schema.defined_entities);
        setSchemaEntities(entities.entities);
        
        // Set first entity type as active tab
        if (schema.defined_entities.length > 0) {
          setActiveEntityTab(schema.defined_entities[0]);
        }
      } catch (error) {
        console.error('Failed to load schema:', error);
      } finally {
        setLoadingSchema(false);
      }
    };
    
    loadSchema();
  }, []);

  const handleExtract = async () => {
    if (!text.trim() || loading) return;
    
    setLoading(true);
    setResult(null);
    
    try {
      const response = await extractionAPI.extract(text);
      setResult(response);
      
      // Set active tab to first entity type with results
      const typesWithResults = Object.entries(response.entities)
        .filter(([, entities]) => Array.isArray(entities) && entities.length > 0)
        .map(([type]) => type);
      
      if (typesWithResults.length > 0) {
        setActiveEntityTab(typesWithResults[0]);
      }
    } catch (error) {
      console.error('Extraction error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadSampleText = () => {
    // Generic sample text that works with any schema
    setText(`AGREEMENT

This Agreement is entered into as of January 15, 2024.

PARTIES:
1. First Party: Acme Corporation, located at 123 Business Ave, New York, NY 10001
2. Second Party: TechStart Inc., located at 456 Innovation Drive, San Francisco, CA 94102

TERMS:

Section 1 - Purpose
This agreement establishes the terms and conditions for collaboration between the parties.

Section 2 - Duration
The term of this agreement shall be two (2) years from the effective date, unless terminated earlier in accordance with Section 5.

Section 3 - Financial Terms
The total value of this agreement is $150,000 USD, payable in quarterly installments of $18,750 each.
Payment is due within 30 days of invoice receipt.

Section 4 - Confidentiality
Both parties agree to maintain strict confidentiality regarding all proprietary information exchanged during the course of this agreement.

Section 5 - Termination
Either party may terminate this agreement with 60 days written notice. In case of material breach, termination may be immediate upon written notice.

Section 6 - Governing Law
This agreement shall be governed by the laws of the State of Delaware.

SIGNATURES:
_____________________
John Smith, CEO
Acme Corporation
Date: January 15, 2024

_____________________
Jane Doe, President
TechStart Inc.
Date: January 15, 2024`);
  };

  // Get the count for a specific entity type from results
  const getEntityCount = (type: string): number => {
    if (!result?.entities) return 0;
    const entities = result.entities[type];
    return Array.isArray(entities) ? entities.length : 0;
  };

  // Get entities for the active tab
  const getActiveEntities = (): unknown[] => {
    if (!result?.entities || !activeEntityTab) return [];
    const entities = result.entities[activeEntityTab];
    return Array.isArray(entities) ? entities : [];
  };

  // Get display name for an entity (tries common properties)
  const getEntityDisplayName = (entity: Record<string, unknown>): string => {
    return String(
      entity.name || 
      entity.title || 
      entity.description || 
      entity.text ||
      entity.id || 
      'Unnamed'
    );
  };

  // Get a preview of entity properties
  const getEntityPreview = (entity: Record<string, unknown>): string | null => {
    const previewProps = ['summary', 'description', 'text', 'value', 'content'];
    for (const prop of previewProps) {
      if (entity[prop] && prop !== getEntityDisplayName(entity)) {
        const value = String(entity[prop]);
        return value.length > 150 ? value.slice(0, 150) + '...' : value;
      }
    }
    return null;
  };

  return (
    <div className="h-full overflow-y-auto p-4 lg:p-6">
      <div className="max-w-6xl mx-auto">
        {/* Schema Info Banner */}
        {schemaName && (
          <div className="mb-6 glass rounded-xl p-4 flex items-center gap-3">
            <InformationCircleIcon className="w-5 h-5 text-electric-400 flex-shrink-0" />
            <div>
              <span className="text-sm text-midnight-400">Active Schema: </span>
              <span className="text-sm font-medium text-electric-400">{schemaName}</span>
              <span className="text-sm text-midnight-500 ml-2">
                ({entityTypes.length} entity types)
              </span>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Input */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Input Text</h3>
              <button
                onClick={loadSampleText}
                className="text-sm text-electric-400 hover:text-electric-300 transition-colors"
              >
                Load sample
              </button>
            </div>
            
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste document text here for entity extraction..."
              className="w-full h-96 glass rounded-xl p-4 bg-midnight-900/50 border-midnight-700 focus:border-electric-500 focus:ring-1 focus:ring-electric-500 resize-none"
            />
            
            <button
              onClick={handleExtract}
              disabled={!text.trim() || loading || loadingSchema}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-electric-500 text-midnight-950 font-medium hover:bg-electric-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <>
                  <BeakerIcon className="w-5 h-5 animate-pulse" />
                  Extracting...
                </>
              ) : (
                <>
                  <BeakerIcon className="w-5 h-5" />
                  Extract Entities
                </>
              )}
            </button>
            
            {/* Schema Entity Types Preview */}
            {schemaEntities.length > 0 && (
              <div className="glass rounded-xl p-4">
                <h4 className="text-sm font-medium text-midnight-300 mb-3">
                  Entity Types in Schema
                </h4>
                <div className="flex flex-wrap gap-2">
                  {schemaEntities.map((entity) => (
                    <span
                      key={entity.name}
                      className="px-2 py-1 text-xs rounded bg-midnight-800 text-midnight-300"
                      title={entity.description}
                    >
                      {entity.name}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Results */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Extraction Results</h3>
            
            {result ? (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-4"
              >
                {/* Summary */}
                <div className="glass rounded-xl p-4">
                  <div className="flex items-center gap-3 mb-4">
                    {result.validation.is_valid ? (
                      <CheckCircleIcon className="w-6 h-6 text-green-400" />
                    ) : (
                      <ExclamationTriangleIcon className="w-6 h-6 text-amber-400" />
                    )}
                    <div>
                      <p className="font-medium">
                        {result.validation.is_valid ? 'Extraction Successful' : 'Extraction Complete with Warnings'}
                      </p>
                      <p className="text-sm text-midnight-400">
                        {result.entity_count} entities, {result.relationship_count} relationships
                        {result.schema_name && (
                          <span className="ml-2 text-electric-400">({result.schema_name})</span>
                        )}
                      </p>
                    </div>
                  </div>
                  
                  {result.validation.errors.length > 0 && (
                    <div className="mt-3 p-3 bg-red-500/10 rounded-lg">
                      <p className="text-xs font-medium text-red-400 mb-1">Errors:</p>
                      <ul className="text-xs text-red-300 space-y-1">
                        {result.validation.errors.map((err, i) => (
                          <li key={i}>• {err}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {result.validation.warnings.length > 0 && (
                    <div className="mt-3 p-3 bg-amber-500/10 rounded-lg">
                      <p className="text-xs font-medium text-amber-400 mb-1">Warnings:</p>
                      <ul className="text-xs text-amber-300 space-y-1">
                        {result.validation.warnings.map((warn, i) => (
                          <li key={i}>• {warn}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {/* Entity Tabs - Dynamically generated from results */}
                <div className="glass rounded-xl overflow-hidden">
                  <div className="flex border-b border-midnight-700/50 overflow-x-auto">
                    {Object.keys(result.entities).map((type) => {
                      const count = getEntityCount(type);
                      return (
                        <button
                          key={type}
                          onClick={() => setActiveEntityTab(type)}
                          className={`px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors ${
                            activeEntityTab === type
                              ? 'text-electric-400 border-b-2 border-electric-400'
                              : 'text-midnight-400 hover:text-midnight-200'
                          }`}
                        >
                          {type}
                          <span className={`ml-2 px-1.5 py-0.5 text-xs rounded-full ${
                            count > 0 ? 'bg-electric-500/20 text-electric-400' : 'bg-midnight-700/50'
                          }`}>
                            {count}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                  
                  <div className="p-4 max-h-80 overflow-y-auto">
                    {getActiveEntities().length > 0 ? (
                      <div className="space-y-3">
                        {getActiveEntities().map((entity: unknown, i: number) => {
                          const e = entity as Record<string, unknown>;
                          return (
                            <div key={i} className="p-3 bg-midnight-800/50 rounded-lg">
                              <div className="flex items-start gap-2">
                                <DocumentTextIcon className="w-4 h-4 text-midnight-400 mt-0.5" />
                                <div className="flex-1 min-w-0">
                                  <p className="font-medium text-sm text-midnight-100">
                                    {getEntityDisplayName(e)}
                                  </p>
                                  
                                  {/* Show type/category if present */}
                                  {(e.type || e.category || e.entity_type) && (
                                    <span className="inline-block mt-1 px-2 py-0.5 text-xs rounded bg-midnight-700 text-midnight-300">
                                      {String(e.type || e.category || e.entity_type)}
                                    </span>
                                  )}
                                  
                                  {/* Show preview of content */}
                                  {getEntityPreview(e) && (
                                    <p className="mt-2 text-xs text-midnight-400">
                                      {getEntityPreview(e)}
                                    </p>
                                  )}
                                  
                                  {/* Show all properties as collapsible */}
                                  <details className="mt-2">
                                    <summary className="text-xs text-midnight-500 cursor-pointer hover:text-midnight-300">
                                      View all properties
                                    </summary>
                                    <pre className="mt-2 text-xs text-midnight-400 bg-midnight-900/50 p-2 rounded overflow-x-auto">
                                      {JSON.stringify(e, null, 2)}
                                    </pre>
                                  </details>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <p className="text-sm text-midnight-500 text-center py-8">
                        No {activeEntityTab} extracted
                      </p>
                    )}
                  </div>
                </div>
                
                {/* Relationships Section */}
                {result.relationships && result.relationships.length > 0 && (
                  <div className="glass rounded-xl p-4">
                    <h4 className="text-sm font-medium text-midnight-300 mb-3">
                      Relationships ({result.relationships.length})
                    </h4>
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {result.relationships.map((rel, i) => (
                        <div key={i} className="text-xs bg-midnight-800/50 p-2 rounded flex items-center gap-2">
                          <span className="text-midnight-300 truncate">{rel.source_id}</span>
                          <span className="text-electric-400 flex-shrink-0">→ {rel.type} →</span>
                          <span className="text-midnight-300 truncate">{rel.target_id}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            ) : (
              <div className="glass rounded-xl p-12 text-center">
                <BeakerIcon className="w-12 h-12 text-midnight-600 mx-auto mb-4" />
                <p className="text-midnight-400">
                  Paste text and click "Extract Entities" to see results
                </p>
                <p className="text-xs text-midnight-500 mt-2">
                  Entities will be extracted based on the active schema
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
