import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  PaperAirplaneIcon, 
  SparklesIcon,
  ClockIcon,
  ChartBarIcon,
  CodeBracketIcon,
  CircleStackIcon,
  ChatBubbleLeftRightIcon,
} from '@heroicons/react/24/outline';
import ReactMarkdown from 'react-markdown';
import { useAppStore } from '../store';
import { queryAPI, DebugInfo } from '../services/api';

// Tab types for message response
type ResponseTab = 'answer' | 'queries' | 'results';

// Component for displaying Cypher queries
function CypherQueriesTab({ debugInfo }: { debugInfo: DebugInfo }) {
  const [expandedQuery, setExpandedQuery] = useState<number | null>(null);
  
  if (!debugInfo.cypher_queries || debugInfo.cypher_queries.length === 0) {
    return (
      <div className="text-midnight-400 text-sm py-4 text-center">
        No Cypher queries were executed for this response.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Query Analysis Summary */}
      {debugInfo.query_analysis && (
        <div className="bg-midnight-800/30 rounded-lg p-3 mb-4">
          <h4 className="text-xs font-semibold text-electric-400 uppercase tracking-wider mb-2">
            Query Analysis
          </h4>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-midnight-500">Intent:</span>
              <span className="text-midnight-200 ml-2">{debugInfo.query_analysis.intent || 'general'}</span>
            </div>
            <div>
              <span className="text-midnight-500">Methods:</span>
              <span className="text-midnight-200 ml-2">{debugInfo.search_methods_used?.join(', ') || 'none'}</span>
            </div>
            {debugInfo.query_analysis.entity_types && debugInfo.query_analysis.entity_types.length > 0 && (
              <div className="col-span-2">
                <span className="text-midnight-500">Target Entities:</span>
                <span className="text-midnight-200 ml-2">
                  {debugInfo.query_analysis.entity_types.join(', ')}
                </span>
              </div>
            )}
            {debugInfo.query_analysis.keywords && debugInfo.query_analysis.keywords.length > 0 && (
              <div className="col-span-2">
                <span className="text-midnight-500">Keywords:</span>
                <span className="text-midnight-200 ml-2">
                  {debugInfo.query_analysis.keywords.slice(0, 5).join(', ')}
                </span>
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Cypher Queries List */}
      <h4 className="text-xs font-semibold text-electric-400 uppercase tracking-wider">
        Executed Queries ({debugInfo.cypher_queries.length})
      </h4>
      
      {debugInfo.cypher_queries.map((q, index) => (
        <div key={index} className="bg-midnight-900/50 rounded-lg overflow-hidden">
          {/* Query Header */}
          <button
            onClick={() => setExpandedQuery(expandedQuery === index ? null : index)}
            className="w-full px-3 py-2 flex items-center justify-between text-left hover:bg-midnight-800/30 transition-colors"
          >
            <div className="flex items-center gap-2">
              <CodeBracketIcon className="w-4 h-4 text-electric-400" />
              <span className="text-sm text-midnight-200">{q.description}</span>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="text-amber-400">{q.result_count} results</span>
              <span className="text-midnight-500">{q.execution_time_ms.toFixed(0)}ms</span>
            </div>
          </button>
          
          {/* Expanded Query Content */}
          <AnimatePresence>
            {expandedQuery === index && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="border-t border-midnight-700/50"
              >
                <div className="p-3 space-y-2">
                  <div>
                    <span className="text-xs text-midnight-500 block mb-1">Cypher Query:</span>
                    <pre className="bg-midnight-950 rounded p-2 text-xs text-electric-300 overflow-x-auto whitespace-pre-wrap font-mono">
                      {q.query}
                    </pre>
                  </div>
                  {Object.keys(q.params).length > 0 && (
                    <div>
                      <span className="text-xs text-midnight-500 block mb-1">Parameters:</span>
                      <pre className="bg-midnight-950 rounded p-2 text-xs text-amber-300 overflow-x-auto whitespace-pre-wrap font-mono">
                        {JSON.stringify(q.params, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ))}
    </div>
  );
}

// Component for displaying retrieval results
function RetrievalResultsTab({ debugInfo }: { debugInfo: DebugInfo }) {
  const [showEntities, setShowEntities] = useState(true);
  const { retrieval_results } = debugInfo;
  
  if (!retrieval_results) {
    return (
      <div className="text-midnight-400 text-sm py-4 text-center">
        No retrieval results available.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="flex gap-4 text-sm">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-electric-500"></span>
          <span className="text-midnight-300">
            {retrieval_results.entity_count} Entities
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-amber-500"></span>
          <span className="text-midnight-300">
            {retrieval_results.chunk_count} Chunks
          </span>
        </div>
      </div>
      
      {/* Toggle */}
      <div className="flex gap-2">
        <button
          onClick={() => setShowEntities(true)}
          className={`px-3 py-1 rounded-lg text-xs transition-colors ${
            showEntities 
              ? 'bg-electric-500/20 text-electric-300' 
              : 'bg-midnight-800/50 text-midnight-400 hover:text-midnight-200'
          }`}
        >
          Entities ({retrieval_results.entities?.length || 0})
        </button>
        <button
          onClick={() => setShowEntities(false)}
          className={`px-3 py-1 rounded-lg text-xs transition-colors ${
            !showEntities 
              ? 'bg-amber-500/20 text-amber-300' 
              : 'bg-midnight-800/50 text-midnight-400 hover:text-midnight-200'
          }`}
        >
          Chunks ({retrieval_results.chunks?.length || 0})
        </button>
      </div>
      
      {/* Content */}
      <div className="space-y-2 max-h-[400px] overflow-y-auto overscroll-contain">
        {showEntities ? (
          retrieval_results.entities && retrieval_results.entities.length > 0 ? (
            retrieval_results.entities.map((entity, i) => (
              <div key={i} className="bg-midnight-900/50 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <span className="px-2 py-0.5 rounded bg-electric-500/20 text-electric-300 text-xs">
                    {String(entity._type || entity._label || 'Entity')}
                  </span>
                  <span className="text-sm text-midnight-200 font-medium">
                    {String(entity.name || entity.title || entity.id || 'Unknown')}
                  </span>
                </div>
                <div className="text-xs text-midnight-400 space-y-1">
                  {Object.entries(entity)
                    .filter(([k]) => !k.startsWith('_') && !['id', 'name', 'title'].includes(k))
                    .slice(0, 4)
                    .map(([key, value]) => (
                      <div key={key} className="truncate">
                        <span className="text-midnight-500">{key}:</span>{' '}
                        <span className="text-midnight-300">
                          {typeof value === 'object' ? JSON.stringify(value) : String(value).slice(0, 100)}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            ))
          ) : (
            <div className="text-midnight-400 text-sm py-4 text-center">
              No entities retrieved.
            </div>
          )
        ) : (
          retrieval_results.chunks && retrieval_results.chunks.length > 0 ? (
            retrieval_results.chunks.map((chunk, i) => (
              <div key={i} className="bg-midnight-900/50 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  {chunk.page_number && (
                    <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 text-xs">
                      Page {chunk.page_number}
                    </span>
                  )}
                  {chunk.section_heading && (
                    <span className="text-xs text-midnight-400 truncate max-w-[200px]">
                      {chunk.section_heading}
                    </span>
                  )}
                </div>
                <p className="text-sm text-midnight-200 leading-relaxed">
                  {chunk.text}
                </p>
                {chunk.key_terms && chunk.key_terms.length > 0 && (
                  <div className="mt-2 flex gap-1 flex-wrap">
                    {chunk.key_terms.map((term, j) => (
                      <span key={j} className="px-1.5 py-0.5 rounded bg-midnight-800 text-midnight-400 text-xs">
                        {term}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))
          ) : (
            <div className="text-midnight-400 text-sm py-4 text-center">
              No chunks retrieved.
            </div>
          )
        )}
      </div>
    </div>
  );
}

// Message with tabs component
function AssistantMessage({ 
  content, 
  metadata,
  onFollowUp,
}: { 
  content: string;
  metadata?: {
    sources?: unknown[];
    confidence?: number;
    followUps?: string[];
    timingMs?: number;
    debugInfo?: DebugInfo;
  };
  onFollowUp: (question: string) => void;
}) {
  const [activeTab, setActiveTab] = useState<ResponseTab>('answer');
  const hasDebugInfo = metadata?.debugInfo && (
    metadata.debugInfo.cypher_queries?.length > 0 || 
    metadata.debugInfo.retrieval_results
  );

  const tabs: { id: ResponseTab; label: string; icon: typeof ChatBubbleLeftRightIcon }[] = [
    { id: 'answer', label: 'Answer', icon: ChatBubbleLeftRightIcon },
    { id: 'queries', label: 'Queries', icon: CodeBracketIcon },
    { id: 'results', label: 'Results', icon: CircleStackIcon },
  ];

  return (
    <div className="glass rounded-2xl rounded-bl-md overflow-hidden max-w-3xl">
      {/* Tabs - Only show if debug info exists */}
      {hasDebugInfo && (
        <div className="flex border-b border-midnight-700/50 bg-midnight-900/30">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-4 py-2 text-xs font-medium transition-colors ${
                  isActive
                    ? 'text-electric-300 border-b-2 border-electric-400 -mb-px bg-midnight-800/30'
                    : 'text-midnight-400 hover:text-midnight-200'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>
      )}
      
      {/* Tab Content */}
      <div className="px-5 py-4">
        <AnimatePresence mode="wait">
          {activeTab === 'answer' && (
            <motion.div
              key="answer"
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              transition={{ duration: 0.15 }}
            >
              <div className="markdown-content">
                <ReactMarkdown>{content}</ReactMarkdown>
              </div>
              
              {/* Metadata */}
              {metadata && (
                <div className="mt-4 pt-4 border-t border-midnight-700/50">
                  {/* Stats */}
                  <div className="flex flex-wrap items-center gap-4 text-xs text-midnight-400 mb-3">
                    {metadata.confidence !== undefined && (
                      <div className="flex items-center gap-1">
                        <ChartBarIcon className="w-4 h-4" />
                        <span>Confidence: {Math.round(metadata.confidence * 100)}%</span>
                      </div>
                    )}
                    {metadata.timingMs !== undefined && (
                      <div className="flex items-center gap-1">
                        <ClockIcon className="w-4 h-4" />
                        <span>{Math.round(metadata.timingMs)}ms</span>
                      </div>
                    )}
                  </div>
                  
                  {/* Follow-up questions */}
                  {metadata.followUps && metadata.followUps.length > 0 && (
                    <div>
                      <p className="text-xs text-midnight-400 mb-2">Follow-up questions:</p>
                      <div className="flex flex-wrap gap-2">
                        {metadata.followUps.map((q, i) => (
                          <button
                            key={i}
                            onClick={() => onFollowUp(q)}
                            className="text-xs px-3 py-1.5 rounded-full bg-midnight-800/50 text-electric-300 hover:bg-midnight-700/50 transition-colors"
                          >
                            {q}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          )}
          
          {activeTab === 'queries' && metadata?.debugInfo && (
            <motion.div
              key="queries"
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              transition={{ duration: 0.15 }}
            >
              <CypherQueriesTab debugInfo={metadata.debugInfo} />
            </motion.div>
          )}
          
          {activeTab === 'results' && metadata?.debugInfo && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              transition={{ duration: 0.15 }}
            >
              <RetrievalResultsTab debugInfo={metadata.debugInfo} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default function QueryChat() {
  const { messages, addMessage, isLoading, setLoading, clearMessages } = useAppStore();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const question = input.trim();
    setInput('');
    
    // Add user message
    addMessage({ role: 'user', content: question });
    setLoading(true);

    try {
      const response = await queryAPI.ask(question);
      
      addMessage({
        role: 'assistant',
        content: response.answer,
        metadata: {
          sources: response.sources,
          confidence: response.confidence,
          followUps: response.follow_up_questions,
          timingMs: response.metadata.total_time_ms,
          debugInfo: response.debug_info,
        },
      });
    } catch (error) {
      addMessage({
        role: 'assistant',
        content: 'Sorry, I encountered an error while processing your question. Please try again.',
      });
      console.error('Query error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFollowUp = (question: string) => {
    setInput(question);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Messages - Isolated scroll container */}
      <div className="flex-1 overflow-y-auto overscroll-contain p-4 lg:p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-electric-400/20 to-electric-600/20 flex items-center justify-center mb-6">
              <SparklesIcon className="w-10 h-10 text-electric-400" />
            </div>
            <h3 className="text-xl font-semibold text-midnight-100 mb-2">
              Ask about your documents
            </h3>
            <p className="text-midnight-400 max-w-md mb-8">
              I can help you understand your documents, find specific information,
              identify entities and relationships, and answer questions based on the knowledge graph.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl">
              {[
                "What are the key entities in the documents?",
                "Summarize the main information",
                "Who are the parties involved?",
                "What relationships exist between entities?",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => handleFollowUp(suggestion)}
                  className="glass px-4 py-3 rounded-xl text-left text-sm text-midnight-200 hover:bg-midnight-800/70 transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {message.role === 'user' ? (
                  <div className="max-w-3xl bg-electric-500/20 border border-electric-500/30 rounded-2xl rounded-br-md px-5 py-4">
                    <p className="text-midnight-100">{message.content}</p>
                  </div>
                ) : (
                  <AssistantMessage
                    content={message.content}
                    metadata={message.metadata}
                    onFollowUp={handleFollowUp}
                  />
                )}
              </motion.div>
            ))}
            
            {/* Loading indicator */}
            {isLoading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-start"
              >
                <div className="glass rounded-2xl rounded-bl-md px-5 py-4">
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-electric-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-electric-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-electric-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span className="text-sm text-midnight-400">Thinking...</span>
                  </div>
                </div>
              </motion.div>
            )}
            
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input - Fixed at bottom */}
      <div className="p-4 lg:p-6 border-t border-midnight-800/50 flex-shrink-0">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
          <div className="glass rounded-2xl p-2 flex items-end gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your documents..."
              rows={1}
              className="flex-1 bg-transparent border-0 resize-none focus:ring-0 focus:outline-none p-3 text-midnight-100 placeholder-midnight-500"
              style={{ minHeight: '48px', maxHeight: '200px' }}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="p-3 rounded-xl bg-electric-500 text-midnight-950 hover:bg-electric-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <PaperAirplaneIcon className="w-5 h-5" />
            </button>
          </div>
          
          {messages.length > 0 && (
            <div className="mt-2 flex justify-center">
              <button
                type="button"
                onClick={clearMessages}
                className="text-xs text-midnight-500 hover:text-midnight-300 transition-colors"
              >
                Clear conversation
              </button>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
