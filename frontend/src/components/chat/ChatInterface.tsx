'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Sparkles, ChevronDown } from 'lucide-react';
import type { ChatMessage } from '@/types';
import { DEMO_QUERIES } from '@/types';
import MessageBubble from './MessageBubble';
import { TypingIndicator } from '@/components/shared/LoadingSpinner';

interface ChatInterfaceProps {
  messages: ChatMessage[];
  isProcessing: boolean;
  onSendMessage: (message: string) => void;
  suggestedQueries?: string[];
  className?: string;
}

export default function ChatInterface({
  messages,
  isProcessing,
  onSendMessage,
  suggestedQueries = DEMO_QUERIES.map((q) => q.query),
  className = '',
}: ChatInterfaceProps) {
  const [inputValue, setInputValue] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && !isProcessing) {
      onSendMessage(inputValue.trim());
      setInputValue('');
      setShowSuggestions(false);
    }
  };

  const handleSuggestionClick = (query: string) => {
    setInputValue(query);
    inputRef.current?.focus();
  };

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <motion.div
            className="flex flex-col items-center justify-center h-full text-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-[#667EEA] to-[#764BA2] flex items-center justify-center mb-6">
              <Sparkles className="w-10 h-10 text-white" />
            </div>
            <h3 className="text-2xl font-bold text-[#1D1D1F] mb-2">
              OpMech-GraphRAG
            </h3>
            <p className="text-[#6E6E73] max-w-md mb-8">
              Ask questions about Apple&apos;s SEC filings. Watch dual operators explore the
              knowledge graph in real-time.
            </p>
          </motion.div>
        ) : (
          <>
            {messages.map((message, index) => (
              <MessageBubble
                key={message.id}
                message={message}
                isLatest={index === messages.length - 1}
              />
            ))}
          </>
        )}

        {/* Typing indicator */}
        <AnimatePresence>
          {isProcessing && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="flex items-start gap-3"
            >
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#667EEA] to-[#764BA2] flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div className="glass-card-heavy p-4 rounded-2xl rounded-bl-sm">
                <TypingIndicator />
                <span className="text-xs text-[#86868B] mt-2 block">
                  Analyzing with dual operators...
                </span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div ref={messagesEndRef} />
      </div>

      {/* Suggestions */}
      <AnimatePresence>
        {showSuggestions && messages.length === 0 && (
          <motion.div
            className="px-6 pb-4"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            <p className="text-sm text-[#6E6E73] mb-3">Try asking:</p>
            <div className="flex flex-wrap gap-2">
              {suggestedQueries.slice(0, 4).map((query, index) => (
                <motion.button
                  key={index}
                  onClick={() => handleSuggestionClick(query)}
                  className="px-4 py-2 text-sm bg-white/60 hover:bg-white/80 border border-black/5 rounded-full text-[#1D1D1F] transition-all hover:shadow-md"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  {query.length > 50 ? query.slice(0, 50) + '...' : query}
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input area */}
      <div className="p-4 border-t border-black/5 bg-white/50 backdrop-blur-xl">
        <form onSubmit={handleSubmit} className="relative">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask about Apple's SEC filings..."
            disabled={isProcessing}
            className="w-full px-5 py-4 pr-14 rounded-2xl bg-white/80 border border-black/10 focus:border-[#667EEA] focus:ring-4 focus:ring-[#667EEA]/10 outline-none transition-all text-[#1D1D1F] placeholder:text-[#86868B] disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || isProcessing}
            className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-xl bg-gradient-to-r from-[#667EEA] to-[#764BA2] flex items-center justify-center text-white disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:shadow-lg hover:scale-105"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>
    </div>
  );
}
