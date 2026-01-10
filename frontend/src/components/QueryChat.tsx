import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  PaperAirplaneIcon, 
  SparklesIcon,
  ClockIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';
import ReactMarkdown from 'react-markdown';
import { useAppStore } from '../store';
import { queryAPI } from '../services/api';

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
    <div className="h-full flex flex-col">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 lg:p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-electric-400/20 to-electric-600/20 flex items-center justify-center mb-6">
              <SparklesIcon className="w-10 h-10 text-electric-400" />
            </div>
            <h3 className="text-xl font-semibold text-midnight-100 mb-2">
              Ask about your contracts
            </h3>
            <p className="text-midnight-400 max-w-md mb-8">
              I can help you understand contract clauses, find specific terms,
              identify parties and obligations, and much more.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl">
              {[
                "What are the main termination clauses?",
                "List all payment obligations",
                "Who are the parties involved?",
                "What confidentiality provisions exist?",
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
                <div
                  className={`max-w-3xl ${
                    message.role === 'user'
                      ? 'bg-electric-500/20 border border-electric-500/30 rounded-2xl rounded-br-md'
                      : 'glass rounded-2xl rounded-bl-md'
                  } px-5 py-4`}
                >
                  {message.role === 'assistant' ? (
                    <div className="markdown-content">
                      <ReactMarkdown>{message.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <p className="text-midnight-100">{message.content}</p>
                  )}
                  
                  {/* Metadata for assistant messages */}
                  {message.role === 'assistant' && message.metadata && (
                    <div className="mt-4 pt-4 border-t border-midnight-700/50">
                      {/* Stats */}
                      <div className="flex flex-wrap items-center gap-4 text-xs text-midnight-400 mb-3">
                        {message.metadata.confidence !== undefined && (
                          <div className="flex items-center gap-1">
                            <ChartBarIcon className="w-4 h-4" />
                            <span>Confidence: {Math.round(message.metadata.confidence * 100)}%</span>
                          </div>
                        )}
                        {message.metadata.timingMs !== undefined && (
                          <div className="flex items-center gap-1">
                            <ClockIcon className="w-4 h-4" />
                            <span>{Math.round(message.metadata.timingMs)}ms</span>
                          </div>
                        )}
                      </div>
                      
                      {/* Follow-up questions */}
                      {message.metadata.followUps && message.metadata.followUps.length > 0 && (
                        <div>
                          <p className="text-xs text-midnight-400 mb-2">Follow-up questions:</p>
                          <div className="flex flex-wrap gap-2">
                            {message.metadata.followUps.map((q, i) => (
                              <button
                                key={i}
                                onClick={() => handleFollowUp(q)}
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
                </div>
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

      {/* Input */}
      <div className="p-4 lg:p-6 border-t border-midnight-800/50">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
          <div className="glass rounded-2xl p-2 flex items-end gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your contracts..."
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
