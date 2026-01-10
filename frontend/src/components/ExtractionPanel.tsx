import { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  BeakerIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { extractionAPI, ExtractionResult } from '../services/api';

export default function ExtractionPanel() {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const [activeEntityTab, setActiveEntityTab] = useState('contracts');

  const handleExtract = async () => {
    if (!text.trim() || loading) return;
    
    setLoading(true);
    setResult(null);
    
    try {
      const response = await extractionAPI.extract(text);
      setResult(response);
    } catch (error) {
      console.error('Extraction error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadSampleText = () => {
    setText(`LICENSE AGREEMENT

This License Agreement ("Agreement") is entered into as of January 1, 2024, by and between:

LICENSOR: Acme Software Corporation, a Delaware corporation with offices at 123 Tech Drive, San Francisco, CA 94105 ("Licensor")

LICENSEE: TechStart Inc., a California corporation with offices at 456 Innovation Way, Palo Alto, CA 94301 ("Licensee")

ARTICLE I - GRANT OF LICENSE

1.1 License Grant. Subject to the terms and conditions of this Agreement, Licensor hereby grants to Licensee a non-exclusive, non-transferable license to use the Software for internal business purposes.

1.2 License Fee. Licensee shall pay Licensor an annual license fee of $50,000 USD, payable within 30 days of the effective date and each anniversary thereof.

ARTICLE II - TERM AND TERMINATION

2.1 Term. This Agreement shall commence on the Effective Date and continue for a period of three (3) years, unless earlier terminated as provided herein.

2.2 Termination for Breach. Either party may terminate this Agreement upon thirty (30) days written notice if the other party materially breaches any provision of this Agreement and fails to cure such breach within said notice period.

ARTICLE III - CONFIDENTIALITY

3.1 Confidential Information. Each party agrees to maintain the confidentiality of the other party's confidential information and not to disclose such information to any third party without prior written consent.

ARTICLE IV - LIMITATION OF LIABILITY

4.1 Limitation. In no event shall either party be liable for any indirect, incidental, special, or consequential damages arising out of this Agreement.`);
  };

  const entityTypes = ['contracts', 'parties', 'clauses', 'obligations', 'dates', 'amounts'];

  return (
    <div className="h-full overflow-y-auto p-4 lg:p-6">
      <div className="max-w-6xl mx-auto">
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
              placeholder="Paste contract text here for entity extraction..."
              className="w-full h-96 glass rounded-xl p-4 bg-midnight-900/50 border-midnight-700 focus:border-electric-500 focus:ring-1 focus:ring-electric-500 resize-none"
            />
            
            <button
              onClick={handleExtract}
              disabled={!text.trim() || loading}
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

                {/* Entity Tabs */}
                <div className="glass rounded-xl overflow-hidden">
                  <div className="flex border-b border-midnight-700/50 overflow-x-auto">
                    {entityTypes.map((type) => {
                      const count = (result.entities as any)[type]?.length || 0;
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
                          {type.charAt(0).toUpperCase() + type.slice(1)}
                          <span className="ml-2 px-1.5 py-0.5 text-xs rounded-full bg-midnight-700/50">
                            {count}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                  
                  <div className="p-4 max-h-80 overflow-y-auto">
                    {(result.entities as any)[activeEntityTab]?.length > 0 ? (
                      <div className="space-y-3">
                        {(result.entities as any)[activeEntityTab].map((entity: any, i: number) => (
                          <div key={i} className="p-3 bg-midnight-800/50 rounded-lg">
                            <div className="flex items-start gap-2">
                              <DocumentTextIcon className="w-4 h-4 text-midnight-400 mt-0.5" />
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-sm text-midnight-100">
                                  {entity.name || entity.title || entity.description || entity.id}
                                </p>
                                {entity.type && (
                                  <span className="inline-block mt-1 px-2 py-0.5 text-xs rounded bg-midnight-700 text-midnight-300">
                                    {entity.type}
                                  </span>
                                )}
                                {entity.clause_type && (
                                  <span className="inline-block mt-1 px-2 py-0.5 text-xs rounded bg-midnight-700 text-midnight-300">
                                    {entity.clause_type}
                                  </span>
                                )}
                                {entity.summary && (
                                  <p className="mt-2 text-xs text-midnight-400">{entity.summary}</p>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-midnight-500 text-center py-8">
                        No {activeEntityTab} extracted
                      </p>
                    )}
                  </div>
                </div>
              </motion.div>
            ) : (
              <div className="glass rounded-xl p-12 text-center">
                <BeakerIcon className="w-12 h-12 text-midnight-600 mx-auto mb-4" />
                <p className="text-midnight-400">
                  Paste text and click "Extract Entities" to see results
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
